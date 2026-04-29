"""咕咕嘎嘎 Web 服务器模块

本模块提供 HTTP 和 WebSocket 两种服务器,负责:
- 前端静态文件服务(HTML/CSS/JS)
- 音频文件播放(训练音频、TTS 输出)
- WebSocket 实时通信(文本对话、实时语音、流式 TTS)
- 记忆管理、历史记录、文件管理
- 视觉/OCR/LLM 工具调用
- GPT-SoVITS 训练管理

[架构概述]
- WebServer (HTTP): 提供静态文件访问、音频文件 URL 映射、训练音频上传
- WebSocketServer (WebSocket): 处理所有实时请求(STT/TTS/LLM/视觉/训练)

[WebSocket 消息类型]
  STT 系列:
    - stt              : 语音转文本
    - realtime_mode     : 开启/关闭实时语音模式
    - realtime_audio    : 实时音频流处理
    - realtime_interrupt: 用户打断 AI 说话
    - realtime_interrupt_fast: 快速打断(全双工增强)

  TTS 系列:
    - tts                : 文本转语音
    - stream             : 流式 TTS 测试
    - update_tts_config   : 更新 TTS 引擎/音色选择

  对话系列:
    - text           : 普通文本对话
    - multimodal     : 多模态对话(图片+文字)
    - memory         : 记忆 CRUD
    - history        : 对话历史

  视觉系列:
    - vision         : 视觉理解/OCR
    - ocr            : 实时屏幕 OCR

  其他:
    - get_projects   : 获取 GPT-SoVITS 项目列表
    - get_providers  : 获取 ASR/TTS Provider 列表
    - files          : 文件管理
    - train          : 训练管理
    - config         : 配置更新
    - tool           : 工具执行
    - system_stats   : 系统状态(GPU/内存)

[实时语音 Pipeline(方案C)]
  用户说话 → VAD检测结束 → ASR识别 → LLM流式推理 → 逐句TTS → 发送音频chunk

  v1.8 改进:
  - Generation ID 替代 cancel Event 竞态窗口
  - TTS 异步化:独立 worker 线程 + 句子队列,LLM 输出和 TTS 合成完全并行
  - 语义判停:检测句子是否完整,不完整则继续等待
  - 情感检测:Live2D 表情联动

[端口配置]
  - HTTP: config.web.port (默认 12393)
  - WebSocket: config.web.ws_port (默认 12394)

[依赖模块]
  - app.llm: LLM 对话模块
  - app.tts: TTS 语音合成模块
  - app.asr: ASR 语音识别模块
  - app.vision: 视觉理解模块
  - app.memory: 记忆系统
  - trainer.manager: 训练管理

版本历史:
- v1.6.0: TTS分句优化(MAX_CHARS 40→80+智能断点)+修复tempfile未导入+修复EdgeTTS参数+WebSocket断连处理
- v1.5.0: LLM模块重构 - PromptInjector模块化注入系统 + MemoryRAGInjector长期记忆注入 + 去掉history硬截断 + max_tokens从512→2048
- v1.5.9: fix realtime pipeline中engine是字符串不是对象('str' object has no attribute 'speak'),放宽fallback阈值(40→60字,1.5s→2.5s),加Markdown剥离,加realtime ASR重复词过滤(hellohello→hello)
- v1.5.8: 基于jieba分词的语义词边界切分(fallback+尾buffer)+fallback剩余部分保留到下一轮累积
- v1.5.7: fix首句(engine,voice顺序反)+fix speak_streaming/speak未传project参数(音色切换失效)+增强no_split/非流式/fallback乱码验证+清理_handle_stt重复fallback代码
- v1.5.5: fix实时语音TTS崩溃(_realtime_tts_single/engine参数顺序全反)+fix流式on_chunk np未import+fix speak_streaming的engine类型判断
- v1.5.4: fix实时语音Invalid voice='default'崩溃(_get_tts_for_client直接返回app.tts)+fix重建逻辑set_project('default')崩溃+fix录音模式工具调用文本进TTS(TOOL:/ARG:/```过滤)
- v1.5.3: 分句策略优化(只按句号/感叹/问号)+感叹词合并扩展20+模式+speak()逗号分句修复+emoji清理+GPU串行TTS
- v1.5.2: fix ASR provider参数错误+fix speak()缺少default检查+fix前端状态卡住
- v1.5.1: TTS音色回退(fix voice='default'崩溃)+pipeline状态重置(fix录音失效)+感叹句合并(fix语调割裂)+流式打断修复+多音色预热
- v1.5: 流式TTS chunk传输(GPT-SoVITS逐chunk立即发送+Web Audio API实时解码)+TTS引擎预热+首句优先策略
- v1.4.71: 记忆系统v2.1:遗忘机制+滑动窗口摘要压缩+混合检索
- v1.4.70: TTS流式分句并行合成(ThreadPoolExecutor) + 音量GainNode放大(0-300%)
- v1.4.69: 实时语音面对面对话重构(新请求打断旧请求) + seed=42固定音色

作者: 咕咕嘎嘎
日期: 2026-04-01
"""
import http.server
import socketserver
import threading
import json
import os
import glob
import time
import re
import tempfile
import uuid
import mimetypes
from queue import Queue

# 注册 .mjs / .wasm MIME 类型（Python 3.11 默认不识别 .mjs）
# onnxruntime-web 1.22+ 用 ES Module 动态 import .mjs 文件
mimetypes.add_type('application/javascript', '.mjs')
mimetypes.add_type('application/wasm', '.wasm')

try:
    import jieba_fast as jieba
except ImportError:
    try:
        import jieba
    except ImportError:
        jieba = None
from pathlib import Path

try:
    import websocket_server as wslib
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False


# =============================================================================
# 静态文件处理器
# =============================================================================
class _StaticFileHandler(http.server.SimpleHTTPRequestHandler):
    """
    HTTP 静态文件处理器.

    支持的路径:
    - GET /audio/{filename}     : 访问 app/cache/ 和 static/audio/ 目录的音频文件
    - GET /audio/train/{project}/{filename}: 访问 GPT-SoVITS 训练音频(32k 目录)
    - GET /train/upload          : 训练音频上传页面
    - GET /api/sandbox/status    : 沙盒状态查询
    - POST /train/upload         : 上传训练音频(multipart/form-data)
    - POST /api/sandbox/*        : 沙盒路径管理 API

    [安全设计]
    - 音频文件: 白名单扩展名检查 (.wav/.mp3/.flac/.m4a/.ogg)
    - 路径遍历检测: 禁止路径中出现 ".." 或 "/"
    - 项目目录: 只允许访问 GPT-SoVITS data/web_projects/{project}/ 目录
    """

    _cache_dir = None  # 由 WebServer 注入,提供 app/cache 目录路径

    def __init__(self, *args, directory=None, **kwargs):
        """初始化静态文件处理器"""
        self._static_dir = directory
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, fmt, *args):
        """静默日志(不输出请求日志)"""
        pass  # 静默日志

    def end_headers(self):
        """注入跨域隔离头，使 ONNX Runtime WASM 多线程模式可用
        
        COEP 使用 credentialless 而非 require-corp，
        避免阻止外部 CDN 资源（Google Fonts、unpkg 等）加载
        同时禁用缓存，确保前端始终加载最新代码
        """
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "credentialless")
        # 强制不缓存，确保前端 JS/CSS/HTML 更新立即生效
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        """
        [功能说明]处理 GET 请求,提供静态文件和音频资源

        [路由]
            /audio/train/{project}/{filename} : GPT-SoVITS 训练音频(32k采样率)
            /audio/{filename}                 : 缓存音频/TTS输出(白名单扩展名)
            /train/upload                    : 训练音频上传页面
            /api/sandbox/status              : 沙盒状态查询
            其他                              : 静态文件服务(SimpleHTTPRequestHandler默认行为)

        [返回值]
            无(直接写入响应)
        """
        # 处理训练音频播放 /audio/train/{project}/{filename}
        if self.path.startswith("/audio/train/"):
            # 解析路径: /audio/train/{project}/{filename}
            parts = self.path.split("/")
            if len(parts) >= 5:
                project_name = parts[3]
                filename = parts[4].split("?")[0]
            else:
                self.send_error(400, "Bad Request")
                return
            
            # 安全检查
            if ".." in project_name or "/" in project_name or ".." in filename or "\\" in filename:
                self.send_error(403, "Forbidden")
                return
            
            # 查找训练音频文件 (32k 目录)
            try:
                from pathlib import Path
                app_dir = Path(__file__).parent
                project_root = app_dir.parent.parent
                audio_path = project_root / "GPT-SoVITS" / "data" / "web_projects" / project_name / "32k" / filename
                
                if audio_path.exists():
                    with open(audio_path, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "audio/wav")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self.send_error(404, "Audio Not Found")
            except Exception:
                self.send_error(500, "Internal Server Error")
            return
        
        if self.path.startswith("/audio/"):
            filename = os.path.basename(self.path.split("?")[0])
            # 安全检查:只允许常见音频格式
            allowed_exts = (".wav", ".mp3", ".flac", ".m4a", ".ogg")
            if not any(filename.lower().endswith(ext) for ext in allowed_exts) or ".." in filename or "/" in filename:
                self.send_error(403, "Forbidden")
                return
            # 查找文件:先找 cache 目录,再找 static/audio
            cache_dir = _StaticFileHandler._cache_dir
            candidates = []
            if cache_dir:
                candidates.append(os.path.join(cache_dir, filename))
            if self._static_dir:
                candidates.append(os.path.join(self._static_dir, "audio", filename))
            for fpath in candidates:
                if os.path.exists(fpath):
                    try:
                        with open(fpath, "rb") as f:
                            data = f.read()
                        self.send_response(200)
                        self.send_header("Content-Type", "audio/wav")
                        self.send_header("Content-Length", str(len(data)))
                        self.send_header("Cache-Control", "no-cache")
                        self.end_headers()
                        self.wfile.write(data)
                    except Exception:
                        self.send_error(500, "Internal Server Error")
                    return
            self.send_error(404, "Audio Not Found")
            return
        
        # 处理训练音频上传
        if self.path.startswith("/train/upload"):
            self._handle_train_upload()
            return
        
        # 沙盒状态 API
        if self.path == "/api/sandbox/status":
            self._handle_sandbox_status()
            return

        # 布局存储 API（支持带查询参数如 ?t=xxx）
        if self.path.startswith("/api/layout"):
            self._handle_layout_api()
            return

        # 其他请求走默认处理
        super().do_GET()
    
    def do_POST(self):
        """
        [功能说明]处理 POST 请求(训练音频上传、沙盒路径管理)

        [返回值]
            无(直接写入响应)
        """
        # 处理训练音频上传
        if self.path.startswith("/train/upload"):
            self._handle_train_upload()
            return
        
        # 沙盒路径管理 API
        if self.path.startswith("/api/sandbox/"):
            self._handle_sandbox_api()
            return

        # 布局存储 API（支持带查询参数）
        if self.path.startswith("/api/layout"):
            self._handle_layout_api()
            return
        
        # L2修复: 健康检查端点，用于部署监控和启动器检测后端就绪
        if self.path == "/api/health":
            self.send_json({"status": "ok", "version": "1.9.38"})
            return

        # 其他请求返回 405 Method Not Allowed
        self.send_error(405, "Method Not Allowed")
    
    def _handle_sandbox_api(self):
        """
        处理沙盒路径管理 API.

        API 端点:
        - POST /api/sandbox/add_path    : 添加沙盒路径
        - POST /api/sandbox/remove_path : 移除沙盒路径
        - POST /api/sandbox/toggle      : 启用/禁用沙盒

        请求体: {"path": "...", "enabled": bool}
        响应: {"success": bool, "error"?: str}
        """
        try:
            import uuid
            
            # 获取请求数据
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else '{}'
            data = json.loads(body) if body else {}
            
            path = self.path
            
            # 获取 App 实例(包含 subagent)
            app = getattr(self, '_app', None)
            if not app:
                self.send_json({"success": False, "error": "应用未初始化"})
                return
            
            # 获取 subagent
            subagent = getattr(app, 'subagent', None)
            if not subagent:
                self.send_json({"success": False, "error": "SubAgent 未启用"})
                return
            
            # 根据路径分发
            if path == "/api/sandbox/add_path":
                p = data.get('path', '').strip()
                if not p:
                    self.send_json({"success": False, "error": "路径为空"})
                    return
                success = subagent.sandbox_add_path(p)
                self.send_json({"success": success})
                
            elif path == "/api/sandbox/remove_path":
                p = data.get('path', '').strip()
                success = subagent.sandbox_remove_path(p)
                self.send_json({"success": success})
                
            elif path == "/api/sandbox/toggle":
                enabled = data.get('enabled')
                if enabled is not None:
                    if enabled:
                        subagent.sandbox_enable()
                    else:
                        subagent.sandbox_disable()
                self.send_json({"enabled": subagent.sandbox_is_enabled()})
                
            else:
                self.send_json({"success": False, "error": "未知API"})
                
        except Exception as e:
            print(f"[SANDBOX] API错误: {e}")
            import traceback
            traceback.print_exc()
            self.send_json({"success": False, "error": str(e)})
    
    def _handle_train_upload(self):
        """
        处理训练音频上传(multipart/form-data).

        流程:
        1. 解析 multipart form data 获取 project 名称和音频文件
        2. 安全检查: 文件名不能包含路径分隔符
        3. 保存到 GPT-SoVITS data/web_projects/{project}/raw/ 目录
        4. 如果是项目第一个音频,自动创建 config.json 并设为参考音频

        字段:
        - project (str)       : 项目名称
        - audio (file)        : 音频文件

        响应: {"success": bool, "filename": str, "path": str, "size": int}
        """
        try:
            import cgi
            import sys
            from pathlib import Path
            
            # 解析 multipart form data
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    'REQUEST_METHOD': 'POST',
                    'CONTENT_TYPE': self.headers.get('Content-Type', '')
                }
            )
            
            # 获取项目名称
            project_name = form.getvalue('project', '')
            if not project_name:
                self.send_json({"success": False, "error": "缺少项目名称"})
                return
            
            # 获取音频文件 (使用兼容方式)
            if 'audio' not in form:
                self.send_json({"success": False, "error": "缺少音频文件"})
                return
            
            audio_item = form['audio']
            if not audio_item.filename:
                self.send_json({"success": False, "error": "缺少音频文件"})
                return
            
            # 获取项目根目录 (需要向上两级: web -> app -> ai-vtuber-fixed)
            app_dir = Path(__file__).parent
            project_root = app_dir.parent.parent
            projects_dir = project_root / "GPT-SoVITS" / "data" / "web_projects"
            project_dir = projects_dir / project_name
            raw_dir = project_dir / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            filename = os.path.basename(audio_item.filename)
            if '/' in filename or '\\' in filename:
                filename = os.path.basename(filename.replace('\\', '/'))
            
            audio_path = raw_dir / filename
            audio_data = audio_item.file.read()
            
            with open(audio_path, 'wb') as f:
                f.write(audio_data)
            
            # 确保 config.json 存在
            config_file = project_dir / "config.json"
            if not config_file.exists():
                import json as json_module
                default_config = {
                    "ref_audio": str(audio_path),  # 第一个音频自动设为参考
                    "ref_text": "",
                    "trained_gpt": None,
                    "trained_sovits": None,
                    "created_at": __import__('datetime').datetime.now().isoformat()
                }
                with open(config_file, 'w', encoding='utf-8') as f:
                    json_module.dump(default_config, f, ensure_ascii=False, indent=2)
                print(f"[TRAIN] 创建项目配置: {project_name}/config.json")
            
            print(f"[TRAIN] 上传成功: {project_name}/{filename} ({len(audio_data)} bytes)")
            self.send_json({
                "success": True,
                "filename": filename,
                "path": str(audio_path),
                "size": len(audio_data)
            })
            
        except Exception as e:
            print(f"[TRAIN] 上传失败: {e}")
            import traceback
            traceback.print_exc()
            self.send_json({"success": False, "error": str(e)})

    def _handle_layout_api(self):
        """
        处理布局存储 API.

        GET /api/layout  : 获取布局数据
        POST /api/layout : 保存布局数据

        存储位置: app/cache/layout.json
        """
        import os as _os

        # 获取缓存目录
        cache_dir = _StaticFileHandler._cache_dir
        if not cache_dir:
            self.send_json({"success": False, "error": "缓存目录未初始化"})
            return

        layout_file = _os.path.join(cache_dir, "layout.json")

        # GET: 读取布局数据
        if self.command == "GET":
            try:
                if _os.path.exists(layout_file):
                    with open(layout_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self.send_json({"success": True, "data": data})
                else:
                    self.send_json({"success": True, "data": None})
            except json.JSONDecodeError:
                self.send_json({"success": True, "data": None})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)})
            return

        # POST: 保存布局数据
        if self.command == "POST":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length == 0:
                    self.send_json({"success": False, "error": "请求体为空"})
                    return

                body = self.rfile.read(content_length).decode("utf-8")
                data = json.loads(body) if body else {}

                # H3修复: 原子写入，先写临时文件再重命名，防止崩溃时数据丢失
                import tempfile as _tempfile
                cache_dir_path = _os.path.dirname(layout_file)
                _os.makedirs(cache_dir_path, exist_ok=True)
                fd, tmp_path = _tempfile.mkstemp(dir=cache_dir_path, suffix=".tmp")
                try:
                    with _os.fdopen(fd, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    # Windows: os.rename 不能覆盖已存在文件，用 os.replace
                    _os.replace(tmp_path, layout_file)
                except Exception:
                    # 清理临时文件
                    try:
                        _os.unlink(tmp_path)
                    except OSError:
                        pass
                    raise

                print(f"[Layout] 已保存布局到 {layout_file}")
                self.send_json({"success": True})
            except json.JSONDecodeError as e:
                self.send_json({"success": False, "error": f"JSON 解析失败: {e}"})
            except Exception as e:
                print(f"[Layout] 保存失败: {e}")
                self.send_json({"success": False, "error": str(e)})
            return

        # 其他方法
        self.send_error(405, "Method Not Allowed")

    def _handle_sandbox_status(self):
        """
        获取沙盒状态.

        响应: {"enabled": bool, "paths": list[str], "error"?: str}
        """
        try:
            # 获取 App 实例
            app = getattr(self, '_app', None)
            if not app:
                self.send_json({"success": False, "error": "应用未初始化"})
                return
            
            subagent = getattr(app, 'subagent', None)
            if not subagent:
                self.send_json({
                    "enabled": False,
                    "paths": [],
                    "error": "SubAgent 未启用"
                })
                return
            
            self.send_json({
                "enabled": subagent.sandbox_is_enabled(),
                "paths": subagent.sandbox_get_paths()
            })
            
        except Exception as e:
            print(f"[SANDBOX] 状态错误: {e}")
            self.send_json({"success": False, "error": str(e)})
    
    def send_json(self, data):
        """
        [功能说明]发送 JSON 响应(统一封装)

        [参数说明]
            data: 要序列化为 JSON 并发送的数据

        [返回值]
            无(直接写入响应)

        [自动设置]
            Content-Type: application/json
            Access-Control-Allow-Origin: * (CORS)
            Content-Length
        """


        """自动设置:
        - Content-Type: application/json
        - Access-Control-Allow-Origin: * (CORS)
        - Content-Length
        """
        response = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response)


# =============================================================================
# Web 服务器
# =============================================================================
class WebServer:
    """
    HTTP 静态文件服务器.

    提供前端静态文件(HTML/CSS/JS)访问服务,并管理音频缓存目录.
    同时在启动时预热 TTS 引擎以消除冷启动延迟.


    [端口]config.web.port(默认 12393)
    [静态目录]app/web/static/
    [音频缓存]app/cache/(存放 TTS 生成的音频文件)

    [TTS 预热机制]
    WebServer 启动时异步预热所有已训练的音色:
    1. 预热默认音色
    2. 并行预热所有已训练的 GPT-SoVITS 项目音色
    这样首次实时语音时 TTS pipeline 已加载完毕,消除 200ms 冷启动延迟.
    """

    def __init__(self, config, app=None):
        """
        [功能说明]初始化 Web HTTP 服务器

        [参数说明]
            config (dict): 完整配置字典,读取 config.web.port
            app: App 实例引用(用于访问 TTS 引擎进行预热)

        [返回值]
            无
        """
        web_config = config.get("web", {})
        self.port = web_config.get("port", 12393)
        self.server = None
        self.thread = None
        self._app = app  # 保存 App 实例引用用于访问 subagent

    def start(self):
        """
        [功能说明]启动 HTTP 服务器

        [设置]
            1. 静态文件目录: app/web/static/
            2. 音频缓存目录: app/cache/
            3. 注入 App 引用到 Handler(用于沙盒状态查询)
            4. 启动后台 TTS 预热线程

        [返回值]
            无
        """
        app_dir = os.path.dirname(os.path.abspath(__file__))
        static = os.path.join(app_dir, "static")
        # 注入 cache 目录到 handler(用于 /audio/ 路径映射)
        # app_dir = .../app/web/  →  cache 在 .../app/cache/
        cache_dir = os.path.normpath(os.path.join(app_dir, "..", "cache"))
        _StaticFileHandler._cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        print(f"[WebServer] Audio cache dir: {cache_dir}")

        def handler_factory(*args, **kwargs):
            """
            【功能说明】HTTP静态文件处理器工厂,为每个请求创建注入App引用的Handler实例

            【参数说明】
                *args: 可变位置参数,传递给_StaticFileHandler
                **kwargs: 可变关键字参数,传递给_StaticFileHandler

            【返回值】
                _StaticFileHandler: 配置好的静态文件处理器,已注入_app引用
            """
            handler = _StaticFileHandler(*args, directory=static, **kwargs)
            handler._app = self._app  # 注入 App 引用
            return handler

        socketserver.TCPServer.allow_reuse_address = True
        self.server = socketserver.TCPServer(("", self.port), handler_factory)


        print(f"[WEB] HTTP server started: http://localhost:{self.port}")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

        # ===== v1.5: TTS 引擎预热 =====
        # 参照 RealtimeVoiceChat:启动时合成一个短音频,消除冷启动延迟
        # 这样第一次实时语音时,TTS pipeline 已经加载好了
        self._prewarm_tts()

    def _prewarm_tts(self):
        """
        TTS 引擎预热:WebServer 启动后在后台合成短音频.

        v1.9.1 修复:
        多音色串行预热(不再并行)——GPT-SoVITS 推理非线程安全,
        并行 set_project 会互相覆盖共享状态,导致日志重复/推理混乱.
        串行预热仅多几秒,但保证正确性.
        效果:首次实时语音时 TTS 已加载完毕,消除 200ms 冷启动延迟.

        [注意]如果项目没有参考音频(ref_audio 为空),跳过预热避免报错.
        """
        def prewarm_single_voice(voice_name, tts):
            """预热单个音色(独立线程)"""
            try:
                # v1.6.7: 检查是否有有效的参考音频,没有则跳过(避免报错刷屏)
                if hasattr(tts, '_project_config'):
                    ref_audio = tts._project_config.get('ref_audio', '')
                    if not ref_audio:
                        print(f"[TTS Prewarm] {voice_name} 无参考音频,跳过预热")
                        return
                warm_text = "你好."
                path = tts.speak(warm_text)
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except OSError:
                        pass
                    print(f"[TTS Prewarm] 预热完成: {voice_name}")
                else:
                    print(f"[TTS Prewarm] {voice_name} 预热返回空(不影响使用)")
            except Exception as e:
                print(f"[TTS Prewarm] {voice_name} 预热失败: {e}")

        def do_prewarm():
            """后台预热主逻辑（串行，避免并发推理冲突）"""
            try:
                if not self._app or not self._app.tts:
                    return
                tts = self._app.tts

                # 1. 先预热默认音色
                print("[TTS Prewarm] 预热默认音色...")
                prewarm_single_voice("default", tts)

                # 2. 只预热上次使用的音色（而非全部已训练音色）
                #    全部预热会导致启动时加载 mansui 等不常用的音色，浪费时间
                #    上次使用的音色保存在 app/cache/last_tts_project.json
                last_project = None
                if hasattr(tts, '_load_last_project'):
                    last_project = tts._load_last_project()

                if last_project and hasattr(tts, 'set_project'):
                    print(f"[TTS Prewarm] 预热上次使用的音色: {last_project}")
                    tts.set_project(last_project)
                    prewarm_single_voice(last_project, tts)
                elif hasattr(tts, 'get_available_projects'):
                    # 没有记录上次音色 → 预热第一个已训练音色
                    try:
                        projects = tts.get_available_projects()
                        trained = [p['name'] for p in projects if p.get('has_trained')]
                        if trained:
                            first = trained[0]
                            print(f"[TTS Prewarm] 无上次记录，预热首个已训练音色: {first}")
                            tts.set_project(first)
                            prewarm_single_voice(first, tts)
                    except Exception as proj_err:
                        print(f"[TTS Prewarm] 获取音色列表失败: {proj_err}")

            except Exception as e:
                print(f"[TTS Prewarm] 预热失败(不影响使用): {e}")

        threading.Thread(target=do_prewarm, daemon=True).start()

    def stop(self):
        """停止 HTTP 服务器"""
        if self.server:
            self.server.shutdown()

    def shutdown(self):
        """关闭服务器(别名)"""
        self.stop()


# =============================================================================
# WebSocket 服务器
# =============================================================================
class WebSocketServer:
    """
    WebSocket 实时通信服务器.

    处理所有实时请求(STT/TTS/LLM/视觉/训练),采用异步处理模式:
    - 每个请求都在独立线程中处理,避免阻塞 WebSocket 事件循环
    - 支持多个客户端并发连接
    - 实时语音Pipeline采用 Generation ID 替代 cancel Event 竞态窗口

    [客户端状态跟踪]
    - _client_tts_engine : client_id → TTS 引擎名
    - _client_tts_voice  : client_id → 音色名
    - _client_asr_provider: client_id → ASR Provider 名
    - _vision_monitors   : client_id → 视觉监控状态

    [音频文件自动清理]
    每5分钟清理超过10分钟的 response_*.wav 文件.

    [WebSocket 分帧支持]
    通过 patch read_next_message 支持 Continuation Frame,
    确保大消息(如长文本流式输出)不被截断.

    [端口]config.web.ws_port(默认 12394)
    """

    def __init__(self, config, app=None):
        """
        [功能说明]初始化 WebSocket 服务器

        [参数说明]
            config (dict): 配置字典,读取 config.web.ws_port
            app: App 实例引用(用于访问各子模块)

        [返回值]
            无
        """
        self.config = config.get("web", {})
        self.port = self.config.get("ws_port", 12394)
        self.app = app
        self.server = None
        self.thread = None
        
        # 优化:请求队列(避免并发冲突)
        self.request_queue = Queue(maxsize=10)
        self.worker_thread = None
        
        # 跟踪每个客户端的 TTS 引擎/声音选择
        self._client_tts_engine = {}  # client_id -> engine_name
        self._client_tts_voice = {}   # client_id -> voice_name
        self._client_tts_no_split = {} # client_id -> bool (True=整段合成, False=流式分句)
        
        # 跟踪每个客户端的 ASR Provider 选择
        self._client_asr_provider = {}  # client_id -> provider_name
        
        # v1.8: ASR fallback 模型懒加载锁(防止多线程重复加载)
        self._fallback_whisper_lock = threading.Lock()
        
        # 音频清理
        self._audio_cleanup_thread = None
        self._start_audio_cleanup()
        
        # 视觉监控状态(每个客户端一个)
        self._vision_monitors = {}  # client_id -> {running, thread, interval, provider, callback}

    def _start_audio_cleanup(self):
        """启动音频文件自动清理线程(每5分钟清理一次超过10分钟的音频文件)"""
        # H4修复: 启动时立即清理一次堆积的旧音频文件（上次崩溃可能遗留）
        self._cleanup_old_audio()
        
        def cleanup_worker():
            """
            【功能说明】音频文件自动清理工作线程,每5分钟执行一次旧音频清理

            【参数说明】无参数

            【返回值】无返回值(守护线程,无限循环运行)
            """
            while True:
                try:
                    time.sleep(300)  # 每5分钟清理一次
                    self._cleanup_old_audio()
                except Exception as e:
                    print(f"️ 音频清理错误: {e}")

        self._audio_cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self._audio_cleanup_thread.start()
    
    def _cleanup_old_audio(self):
        """
        清理音频文件(response_*.wav).
        策略:
        1. 超过10分钟的文件 → 删除
        2. 文件总数超过 MAX_AUDIO_FILES(120) 时 → 按修改时间从旧到新删除，直到数量降到上限
        
        v1.9.22: 新增文件数量上限机制，避免缓存无限增长
        """
        MAX_AUDIO_FILES = 120  # v1.9.22: 音频缓存文件上限
        
        if not self.app:
            return

        try:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            audio_dir = Path(app_dir) / "web" / "static" / "audio"

            if not audio_dir.exists():
                return

            now = time.time()
            count = 0

            # 策略1: 清理超过10分钟的文件
            for audio_file in audio_dir.glob("response_*.wav"):
                if now - audio_file.stat().st_mtime > 600:  # 10分钟
                    try:
                        audio_file.unlink()
                        count += 1
                    except OSError:
                        pass

            # 策略2: 文件数量上限（v1.9.22）
            # 收集剩余的 response_*.wav 文件
            remaining = list(audio_dir.glob("response_*.wav"))
            if len(remaining) > MAX_AUDIO_FILES:
                # 按修改时间排序，最旧的在前
                remaining.sort(key=lambda f: f.stat().st_mtime)
                # 删除最旧的文件，直到数量降到上限
                to_delete = len(remaining) - MAX_AUDIO_FILES
                for audio_file in remaining[:to_delete]:
                    try:
                        audio_file.unlink()
                        count += 1
                    except OSError:
                        pass

            if count > 0:
                print(f"[AUDIO] Cleaned up {count} audio files (time+quota)")
        except Exception as e:
            print(f"️ 清理音频失败: {e}")

    def start(self):
        """
        启动 WebSocket 服务器.

        主要步骤:
        1. Patch websocket_server 以支持 Continuation Frame(大消息分帧)
        2. 创建 WebsocketServer 实例
        3. 注册消息处理回调(on_new/on_message/on_left)
        4. 启动后台线程运行服务器

        [Continuation Frame 修复]
        原始 websocket_server 收到 OPCODE_CONTINUATION 时会丢弃 payload,
        导致大消息被截断.Patch 后累积所有分帧,在 FIN=1 时组装完整消息并处理.
        """
        if not WEBSOCKET_AVAILABLE:
            print(f"️ WebSocket库不可用,跳过 ws://localhost:{self.port}")
            return

        try:
            # ============================================================
            # 修复:让 websocket_server 支持 Continuation Frame(大消息分帧)
            # 原本:收到 OPCODE_CONTINUATION → 丢弃 payload → return
            #      → 大消息被截断 → 前端收不到完整数据 → 客户端断连重连
            # 修复:累积所有分帧,FIN=1 时才组装完整消息并处理
            # ============================================================
            import struct as _struct
            _ws = wslib
            _ws_handler = _ws.websocket_server.WebSocketHandler

            _orig_read_next = _ws_handler.read_next_message

            def patched_read_next_message(self_handler):
                """
                【功能说明】修复WebSocket大消息分帧问题,支持Continuation Frame实现完整消息组装

                【参数说明】
                    self_handler: WebSocketHandler实例,用于访问分帧缓冲区

                【返回值】无返回值,处理完成后直接返回
                """
                # 复用 pip 包里的常量
                FIN             = _ws.websocket_server.FIN
                OPCODE          = _ws.websocket_server.OPCODE
                MASKED          = _ws.websocket_server.MASKED
                PAYLOAD_LEN     = _ws.websocket_server.PAYLOAD_LEN
                PAYLOAD_LEN_EXT16 = _ws.websocket_server.PAYLOAD_LEN_EXT16
                PAYLOAD_LEN_EXT64 = _ws.websocket_server.PAYLOAD_LEN_EXT64
                OPCODE_CONTINUATION = _ws.websocket_server.OPCODE_CONTINUATION
                OPCODE_TEXT         = _ws.websocket_server.OPCODE_TEXT
                OPCODE_CLOSE_CONN  = _ws.websocket_server.OPCODE_CLOSE_CONN

                # 初始化分帧缓冲区(per-handler 实例)
                if not hasattr(self_handler, '_ws_frag_buf'):
                    self_handler._ws_frag_buf = None

                frag_buf = self_handler._ws_frag_buf

                while True:
                    try:
                        b1, b2 = self_handler.read_bytes(2)
                    except _ws.websocket_server.SocketError as e:
                        if e.errno == _ws.websocket_server.errno.ECONNRESET:
                            self_handler.keep_alive = 0
                            return
                        b1, b2 = 0, 0
                    except ValueError:
                        b1, b2 = 0, 0

                    fin     = b1 & FIN
                    opcode  = b1 & OPCODE
                    masked  = b2 & MASKED
                    paylen  = b2 & PAYLOAD_LEN

                    # OPCLOSE → 关闭连接
                    if opcode == OPCODE_CLOSE_CONN:
                        self_handler.keep_alive = 0
                        return

                    # 客户端必须掩码,不掩码则断开
                    if not masked:
                        self_handler.keep_alive = 0
                        return

                    # 扩展 payload 长度
                    if paylen == PAYLOAD_LEN_EXT16:
                        paylen = _struct.unpack(">H", self_handler.read_bytes(2))[0]
                    elif paylen == PAYLOAD_LEN_EXT64:
                        paylen = _struct.unpack(">Q", self_handler.read_bytes(8))[0]

                    masks = self_handler.read_bytes(4)

                    # --- 处理分帧 ---
                    if opcode == OPCODE_CONTINUATION:
                        # 累积片段到 buffer
                        raw_pieces = []
                        for byte in self_handler.read_bytes(paylen):
                            raw_pieces.append(byte ^ masks[len(raw_pieces) % 4])
                        if frag_buf is None:
                            return  # 无起始帧,丢弃
                        frag_buf += bytes(raw_pieces)
                        self_handler._ws_frag_buf = frag_buf  # 写回,跨调用持久化
                    elif opcode == OPCODE_TEXT:
                        # 起始帧 → 开始新 buffer
                        raw_pieces = []
                        for byte in self_handler.read_bytes(paylen):
                            raw_pieces.append(byte ^ masks[len(raw_pieces) % 4])
                        msg_bytes = bytes(raw_pieces)
                        if fin:
                            self_handler.server._message_received_(
                                self_handler, msg_bytes.decode('utf8'))
                            self_handler._ws_frag_buf = None
                            return
                        else:
                            frag_buf = msg_bytes
                            self_handler._ws_frag_buf = frag_buf  # 写回
                            continue  # 等待后续 CONTINUATION 帧
                    else:
                        # 不支持的 opcode(Ping/Pong/Binary),读取并丢弃
                        self_handler.read_bytes(paylen)
                        if opcode == OPCODE_TEXT and fin:
                            return  # 已处理完一个非分帧文本消息
                        continue

                    # 收到 FIN=1 的 CONTINUATION → 组装完整消息并处理
                    if fin and frag_buf is not None:
                        self_handler.server._message_received_(
                            self_handler, frag_buf.decode('utf8'))
                        self_handler._ws_frag_buf = None
                        return

            _ws_handler.read_next_message = patched_read_next_message
            print("[WS] Continuation Frame 支持已启用(支持大消息分帧)")

            self.server = wslib.WebsocketServer("localhost", self.port)

            def on_new(client, server):
                """
                【功能说明】WebSocket新客户端连接回调,打印连接日志

                【参数说明】
                    client (dict): 客户端信息,包含id等属性
                    server: WebSocket服务器实例

                【返回值】无返回值
                """
                print(f" 新客户端: {client['id']}")

            def on_message(client, server, msg):
                """
                【功能说明】WebSocket消息接收回调,根据消息type字段分发到不同处理器

                【参数说明】
                    client (dict): 客户端信息字典
                    server: WebSocket服务器实例
                    msg (str): 接收到的原始消息字符串

                【返回值】无返回值,根据msg_type分发处理
                """
                try:
                    data = json.loads(msg)
                except Exception:
                    data = {"type": "text", "text": msg}

                msg_type = data.get("type")

                # ---------- STT ----------
                if msg_type == "stt":
                    self._handle_stt(client, data)
                    return

                # ---------- TTS ----------
                elif msg_type == "tts":
                    self._handle_tts(client, data)
                    return
                
                # ---------- 获取 GPT-SoVITS 项目列表 ----------
                elif msg_type == "get_projects":
                    self._handle_get_projects(client, data)
                    return

                # ---------- 普通文本 ----------
                elif msg_type == "text":
                    self._handle_text(client, data)
                    return
                
                # ---------- 文件管理 ----------
                elif msg_type == "files":
                    self._handle_files(client, data)
                    return
                
                # ---------- 记忆功能 ----------
                elif msg_type == "memory":
                    self._handle_memory(client, data)
                    return
                
                # ---------- 历史功能 ----------
                elif msg_type == "history":
                    self._handle_history(client, data)
                    return

                # ---------- 多模态对话 ----------
                elif msg_type == "multimodal":
                    self._handle_multimodal(client, data)
                    return

                # ---------- 视觉功能 ----------
                elif msg_type == "vision":
                    self._handle_vision(client, data)
                    return

                # ---------- OCR 实时屏幕分析 ----------
                elif msg_type == "ocr":
                    self._handle_ocr(client, data)
                    return

                # ---------- 系统统计 ----------
                elif msg_type == "system_stats":
                    self._handle_system_stats(client)
                    return

                # ---------- 配置更新 ----------
                elif msg_type == "config":
                    self._handle_config(client, data)
                    return

                # ---------- API Key 管理 ----------
                elif msg_type == "set_api_key":
                    self._handle_set_api_key(client, data)
                    return

                # ---------- API Key 查询 ----------
                elif msg_type == "get_api_key_status":
                    self._handle_get_api_key_status(client, data)
                    return

                # ---------- 工具执行 ----------
                elif msg_type == "tool":
                    self._handle_tool(client, data)
                    return

                # ---------- 训练模块 ----------
                elif msg_type == "train":
                    self._handle_train(client, data)
                    return

                # ---------- 实时语音对话 (方案C) ----------
                elif msg_type == "realtime_mode":
                    self._handle_realtime_mode(client, data)
                    return

                elif msg_type == "realtime_audio":
                    self._handle_realtime_audio(client, data)
                    return

                elif msg_type == "realtime_interrupt":
                    self._handle_realtime_interrupt(client, data)
                    return

                elif msg_type == "realtime_interrupt_fast":
                    # [全双工增强]快速打断:用户开始说话时立即通知后端
                    # 比普通打断更激进:立即取消 LLM 调用,不等 pipeline 完
                    self._handle_realtime_interrupt_fast(client, data)
                    return

                elif msg_type == "stream":
                    # P0-2: 流式 TTS 测试接口(直接发句子,看流式音频效果)
                    sentence = data.get("text", "")
                    client_id = client['id']
                    state = self._get_realtime_state(client_id)
                    engine = self._client_tts_engine.get(client_id, "edge")
                    voice = self._client_tts_voice.get(client_id, "default")
                    self._realtime_streaming_tts(client, state, sentence, engine, voice)
                    return

                # ---------- TTS 配置实时更新 ----------
                elif msg_type == "update_tts_config":
                    engine = data.get("engine", "edge")
                    voice = data.get("voice", "default")
                    self._client_tts_engine[client['id']] = engine
                    self._client_tts_voice[client['id']] = voice
                    print(f"[WS] TTS 配置更新: {engine}/{voice} (client {client['id']})")
                    return

                # ---------- TTS 模式切换（流式/整段） ----------
                elif msg_type == "update_tts_mode":
                    no_split = data.get("no_split", False)
                    self._client_tts_no_split[client['id']] = no_split
                    print(f"[WS] TTS 模式更新: {'整段' if no_split else '流式分句'} (client {client['id']})")
                    return
                
                # ---------- ASR Provider 配置实时更新 ----------
                elif msg_type == "update_asr_config":
                    provider = data.get("provider", "funasr")
                    self._client_asr_provider[client['id']] = provider
                    print(f"[WS] ASR Provider 更新: {provider} (client {client['id']})")
                    return
                
                # ---------- 诊断端点（v1.9.22）----------
                elif msg_type == "diag":
                    self._handle_diag(client, data)
                    return
                
                # ---------- 获取可用的 ASR/TTTS Provider 列表 ----------
                elif msg_type == "get_providers":
                    self._handle_get_providers(client)
                    return

            def on_left(client, server):
                """
                【功能说明】WebSocket客户端断开连接回调,打印日志并清理客户端状态

                【参数说明】
                    client (dict): 断开的客户端信息字典
                    server: WebSocket服务器实例

                【返回值】无返回值
                """
                client_id = client['id'] if client else 'unknown'
                print(f"[WS] Client disconnected: {client_id}")
                # H2修复: 清理该客户端的后端状态dict，防止长期运行内存膨胀
                self._client_tts_engine.pop(client_id, None)
                self._client_tts_voice.pop(client_id, None)
                self._client_asr_provider.pop(client_id, None)
                if client_id in self._vision_monitors:
                    del self._vision_monitors[client_id]

            self.server.set_fn_new_client(on_new)
            self.server.set_fn_message_received(on_message)
            self.server.set_fn_client_left(on_left)

            self.thread = threading.Thread(target=self.server.run_forever, daemon=True)
            self.thread.start()
            print(f"[WS] WebSocket server started: ws://localhost:{self.port}")
        except Exception as e:
            print(f"️ WebSocket启动失败: {e}")

    def _handle_stt(self, client, data):
        """
        处理 STT(语音转文本)请求.

        输入:
          - audio (base64): WAV 格式音频数据
        输出:
          - stt_result: {"type": "stt_result", "text": str}
       
        处理流程:
        1. Base64 解码音频
        2. 保存为临时 WAV 文件
        3. 调用 ASR 识别(优先 ASRManager,回退 faster-whisper)
        4. 去空格 + 噪音过滤(重复词、常见噪音词)
        5. 有效文本通过 WebSocket 发送给前端
        
        [噪音过滤规则]
        - 单字重复(如"没有没有")→ 过滤
        - 词组重复(如"你好你好")→ 去重后半段
        - 常见噪音词("嗯嗯"、"啊啊"等)→ 过滤
        - 有效字符少于2个的短文本 → 过滤
        """
        import base64
        import tempfile

        audio_b64 = data.get("audio", "")
        if not audio_b64:
            return

        # 获取客户端选择的 ASR Provider
        client_id = client['id']
        asr_provider = self._client_asr_provider.get(client_id, "funasr")

        def stt_worker():
            """
            【功能说明】语音识别工作线程,将接收的Base64音频解码后执行ASR识别并返回文本

            【参数说明】无参数(闭包捕获audio_b64和client)

            【返回值】无返回值,识别完成后通过server.send_message推送stt_result
            """
            audio_bytes = base64.b64decode(audio_b64)
            tmp_path = None

            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp.write(audio_bytes)
                    tmp_path = tmp.name

                text = ""
                
                # 优先使用 ASRManager(支持动态切换)
                # v1.5.2 修复:不传 provider 参数,FunASRASR.recognize() 不接受 provider
                if self.app and hasattr(self.app, 'asr'):
                    try:
                        if hasattr(self.app.asr, 'recognize'):
                            text = self.app.asr.recognize(tmp_path) or ""
                    except Exception as e:
                        print(f"[STT] 识别错误: {e}")
                
                # 如果没有识别出文本,尝试 fallback
                if not text:
                    try:
                        from faster_whisper import WhisperModel
                        if not hasattr(self, '_fallback_whisper'):
                            self._fallback_whisper = WhisperModel("base", device="cpu")
                            print("[STT] 已切换到 faster-whisper fallback")
                        segments, _ = self._fallback_whisper.transcribe(tmp_path, language="zh")
                        texts = [s.text for s in segments]
                        text = "".join(texts).replace(" ", "")
                    except Exception as e2:
                        print(f"[STT] Fallback whisper 也失败: {e2}")
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass

            # 去掉 FunASR 输出中的空格(模型会在每字间加空格)
            text = text.replace(" ", "").strip()

            # ===== 噪音过滤:过滤无意义的短文本(如"没有没有没有"、"嗯嗯嗯"、"你好你好你好")=====
            # 统计有效字符(汉字+字母+数字)
            valid_chars = sum(1 for c in text if ('\u4e00' <= c <= '\u9fff') or c.isalpha() or c.isdigit())
            # 无意义内容检测
            import re
            # 单字重复:没有没有没有
            is_repetitive_noise = bool(re.fullmatch(r'([\u4e00-\u9fff])(\1)+', text))
            # 多字重复检测:你好你好你好、你说什么你说什么
            # 匹配连续2次及以上重复的词组(如"你好"、"什么")
            is_word_repeat_noise = False
            for seg_len in range(2, 5):  # 2-4字的重复
                if len(text) >= seg_len * 2:
                    seg = text[:seg_len]
                    if text == seg * (len(text) // seg_len):
                        is_word_repeat_noise = True
                        break
            is_short_noise = len(text) <= 4 and valid_chars <= 2  # 太短且有效字符少
            # 常见噪音词
            noise_words = ['没有', '嗯嗯', '嗯', '啊啊', '呃呃', '呃', '哦哦', '对对', '对对对']
            is_common_noise = text in noise_words

            if is_repetitive_noise or is_short_noise or is_common_noise:
                print(f"[STT] 过滤噪音: {repr(text)} (valid={valid_chars}, repetitive={is_repetitive_noise})")
                text = ""
            # ===== 噪音过滤结束 =====

            if text:  # 只有有效文本才发送
                try:
                    self.server.send_message(
                        client, json.dumps({"type": "stt_result", "text": text})
                    )
                except Exception:
                    pass
            else:
                # v1.9.2: 空结果也要通知前端，避免 UI 卡在"处理中..."
                try:
                    self.server.send_message(
                        client, json.dumps({"type": "stt_result", "text": ""})
                    )
                except Exception:
                    pass

        threading.Thread(target=stt_worker, daemon=True).start()

    def _handle_get_projects(self, client, data):
        """
        获取 GPT-SoVITS 项目列表(音色列表).

        输出: projects_list: {"projects": [{"value": str, "label": str}]}
        """
        try:
            voices = []
            
            # 尝试从当前 TTS 引擎获取
            if self.app and hasattr(self.app, 'tts') and self.app.tts:
                tts = self.app.tts
                if hasattr(tts, 'get_voices'):
                    voices = tts.get_voices()
            
            # 如果当前 TTS 没有 get_voices,尝试直接导入 GPT-SoVITS
            if not voices:
                try:
                    from tts.gptsovits import get_engine
                    gpt_tts = get_engine()
                    voices = gpt_tts.get_voices()
                except Exception:
                    pass
            
            self.server.send_message(client, json.dumps({
                "type": "projects_list",
                "projects": voices or [{"value": "default", "label": "默认音色"}]
            }))
        except Exception as e:
            print(f"[PROJECTS] 获取失败: {e}")
            import traceback
            traceback.print_exc()
            self.server.send_message(client, json.dumps({
                "type": "projects_list",
                "projects": [{"value": "default", "label": "默认音色"}],
                "error": str(e)
            }))

    def _handle_get_providers(self, client):
        """
        获取可用的 ASR 和 TTS Provider 列表.
        输出: providers_list: {"providers": {"asr": [...], "tts": [...]}}
        """
        try:
            providers = {
                "asr": [],
                "tts": []
            }
            
            # ASR Providers
            asr_providers = ["funasr", "faster_whisper"]
            for prov in asr_providers:
                providers["asr"].append({
                    "value": prov,
                    "label": {
                        "funasr": "FunASR (阿里)",
                        "faster_whisper": "Faster-Whisper"
                    }.get(prov, prov)
                })
            
            # TTS Providers
            tts_providers = ["gptsovits", "edge"]
            for prov in tts_providers:
                providers["tts"].append({
                    "value": prov,
                    "label": {
                        "gptsovits": "GPT-SoVITS (本地音色克隆)",
                        "edge": "Edge TTS (微软)"
                    }.get(prov, prov)
                })
            
            self.server.send_message(client, json.dumps({
                "type": "providers_list",
                "providers": providers
            }))
        except Exception as e:
            print(f"[PROVIDERS] 获取失败: {e}")
            self.server.send_message(client, json.dumps({
                "type": "providers_list",
                "providers": {
                    "asr": [{"value": "funasr", "label": "FunASR"}],
                    "tts": [{"value": "edge", "label": "Edge TTS"}]
                },
                "error": str(e)
            }))

    def _handle_tts(self, client, data):
        """
        处理 TTS(文本转语音)请求.

        输入:
          - text (str)  : 要转换的文本
          - engine (str): TTS 引擎(edge/gptsovits)
          - voice (str) : 音色/项目名
          - no_split (bool): True=整段合成, False=流式分句(默认)
        输出:
          - tts_chunk: {"type": "tts_chunk", "audio": str, "sentence_idx": int} (流式模式,逐句)
          - tts_done:  {"type": "tts_done",  "audio": str}  (完成标记/整段模式)
        
        [客户端选择记忆]
        每次 TTS 请求会记住客户端的 engine/voice 选择,
        后续 _handle_text / _handle_realtime_audio 会自动使用这些选择.
        """
        text = data.get("text", "")
        engine = data.get("engine", "edge")
        voice = data.get("voice", "default")
        no_split = data.get("no_split", False)
        
        # 记住客户端的 TTS 引擎/声音/模式选择(供 _handle_text 使用)
        self._client_tts_engine[client['id']] = engine
        self._client_tts_voice[client['id']] = voice
        self._client_tts_no_split[client['id']] = no_split
        
        print(f"[TTS] 请求: {text[:40]} | 引擎: {engine} | 声音: {voice} | 模式: {'整段' if no_split else '流式分句'}")
        
        # 异步处理 TTS
        def tts_worker():
            """
            【功能说明】TTS合成工作线程,根据传入文本调用TTS引擎合成语音并推送音频URL

            【参数说明】无参数(闭包捕获text/engine/voice/no_split和client)

            【返回值】无返回值,完成后通过server.send_message发送tts_done消息
            """
            if not self.app or not text:
                return

            try:
                tts = self._get_tts_for_client(engine, voice)
                if not tts:
                    print(f"[TTS] ❌ 引擎为空,provider={engine}")
                    # v1.9.28: 通知前端 TTS 错误
                    self._safe_send(client, {"type": "tts_error", "error": f"TTS引擎不可用: {engine}"})
                    return
                print(f"[TTS] 使用引擎: {type(tts).__name__}")

                if engine == "gptsovits" and hasattr(tts, 'set_project'):
                    tts.set_project(voice)

                # v1.9.28: 通知前端 TTS 开始
                self._safe_send(client, {"type": "tts_start", "engine": engine})

                if not no_split:
                    # ========== 流式分句模式 ==========
                    # 用正则一次性把文本切成句子
                    sentences = WebSocketServer._SENTENCE_END.split(text)
                    sentences = [s.strip() for s in sentences if s.strip()]
                    
                    if not sentences:
                        # 没有句号结尾的文本,整段作为一句
                        sentences = [text.strip()]
                    
                    print(f"[TTS] 流式分句: 共 {len(sentences)} 句")

                    # v1.8.4: 使用 speak_streaming 逐句流式合成
                    # 改进前: tts.speak(sentence) 同步阻塞，每句 1-3 秒
                    # 改进后: speak_streaming() 逐 chunk 发送，前端立即开始播放
                    supports_streaming = hasattr(tts, 'speak_streaming')
                    import numpy as np

                    for idx, sentence in enumerate(sentences):
                        if not sentence:
                            continue
                        print(f"[TTS] 合成第 {idx+1}/{len(sentences)} 句: {sentence[:30]}...")
                        # v1.9.28: 发送每句的合成进度
                        self._safe_send(client, {
                            "type": "tts_progress",
                            "sentence_idx": idx,
                            "total_sentences": len(sentences),
                            "text_preview": sentence[:30],
                        })

                        if supports_streaming:
                            # 流式模式：逐 chunk 发送 realtime_audio_chunk
                            try:
                                chunk_count = [0]
                                def on_panel_chunk(chunk_sr, audio_float, chunk_idx):
                                    """TTS 面板流式 chunk 回调"""
                                    try:
                                        import soundfile as sf
                                        import base64 as b64
                                        import io
                                        audio_int16 = (audio_float * 32767).astype(np.int16)
                                        buf = io.BytesIO()
                                        sf.write(buf, audio_int16, chunk_sr, format='WAV')
                                        audio_b64 = b64.b64encode(buf.getvalue()).decode('ascii')
                                        self.server.send_message(client, json.dumps({
                                            "type": "realtime_audio_chunk",
                                            "audio": audio_b64,
                                            "text": sentence,
                                            "chunk_idx": chunk_count[0],
                                            "is_panel": True,  # 标记来自 TTS 面板
                                        }))
                                        chunk_count[0] += 1
                                    except Exception as e:
                                        print(f"[TTS] chunk 发送失败: {e}")

                                if engine == "gptsovits" and hasattr(tts, 'set_project'):
                                    tts.set_project(voice)
                                tts.speak_streaming(sentence, project=voice, on_chunk=on_panel_chunk)

                                # 发送句子完成标记
                                self.server.send_message(client, json.dumps({
                                    "type": "realtime_audio_done",
                                    "text": sentence,
                                    "sentence_idx": idx,
                                    "total_sentences": len(sentences),
                                    "is_panel": True,
                                }))
                                print(f"[TTS] 第 {idx+1} 句流式发送完成 ({chunk_count[0]} chunks)")
                            except Exception as e:
                                print(f"[TTS] 流式合成失败，回退到同步: {e}")
                                # 回退到同步模式
                                audio_path = tts.speak(sentence)
                                if audio_path and os.path.exists(audio_path):
                                    audio_url = "/audio/" + os.path.basename(audio_path)
                                    try:
                                        self.server.send_message(client, json.dumps({
                                            "type": "tts_chunk",
                                            "audio": audio_url,
                                            "sentence_idx": idx,
                                            "sentence_text": sentence,
                                            "total_sentences": len(sentences),
                                        }))
                                    except Exception:
                                        pass
                        else:
                            # 非流式模式（edge）：保持原有同步逻辑
                            audio_path = tts.speak(sentence)
                            if audio_path and os.path.exists(audio_path):
                                audio_url = "/audio/" + os.path.basename(audio_path)
                                try:
                                    self.server.send_message(client, json.dumps({
                                        "type": "tts_chunk",
                                        "audio": audio_url,
                                        "sentence_idx": idx,
                                        "sentence_text": sentence,
                                        "total_sentences": len(sentences),
                                    }))
                                except Exception:
                                    pass
                                print(f"[TTS] 第 {idx+1} 句发送: {audio_url}")
                    
                    # 所有句子合成完毕,发送完成标记
                    try:
                        self.server.send_message(client, json.dumps({
                            "type": "tts_done",
                            "audio": None,
                            "streaming": True,
                            "total_sentences": len(sentences),
                        }))
                    except Exception:
                        pass
                else:
                    # ========== 整段合成模式 ==========
                    # v1.9.28: 发送进度
                    self._safe_send(client, {
                        "type": "tts_progress",
                        "sentence_idx": 0,
                        "total_sentences": 1,
                        "text_preview": text[:30],
                    })
                    audio_path = tts.speak(text)
                    print(f"[TTS] 整段生成: {audio_path}")
                    if audio_path and os.path.exists(audio_path):
                        audio_url = "/audio/" + os.path.basename(audio_path)
                        try:
                            self.server.send_message(client, json.dumps({
                                "type": "tts_done", "audio": audio_url
                            }))
                        except Exception:
                            pass
            except Exception as e:
                print(f"[TTS] 错误: {e}")
                import traceback
                traceback.print_exc()
                # v1.9.28: 通知前端 TTS 异常
                self._safe_send(client, {"type": "tts_error", "error": str(e)[:100]})
        
        threading.Thread(target=tts_worker, daemon=True).start()

    def _handle_text(self, client, data):
        """
        [功能说明]处理普通文本对话请求

        [参数说明]
            client: WebSocket 客户端对象
            data (dict): 消息数据,包含 type 和 text 字段

        [返回值]
            无(通过 WebSocket 发送响应)
        """
        """
        处理普通文本对话请求(流式版 - 逐chunk发送 + TTS).


        输入:
          - text (str)  : 用户输入文本
          - engine (str): TTS 引擎
          - voice (str) : 音色
        输出:
          - text_chunk   : 流式文本片段(逐chunk发送)
          - text_done    : 流式结束标记(包含完整回复)
          - tts_done     : TTS 完成(包含音频 URL)
        
        [流式模式]
        优先使用 LLM.stream_chat()(MiniMax 支持),逐chunk发送给前端.
        如果 LLM 不支持流式,回退到非流式 llm.chat().
        
        [记忆更新]
        回复完成后更新记忆系统 (app.memory.add_interaction).
        """
        if not self.app:
            return

        text = data.get("text", "")
        print(f"[WS] 处理: {text[:30]}")

        # 获取客户端选择的 TTS 引擎、声音和模式
        client_id = client['id']
        client_engine = data.get("engine") or self._client_tts_engine.get(client_id, "edge")
        client_voice = data.get("voice") or self._client_tts_voice.get(client_id, "default")
        client_no_split = self._client_tts_no_split.get(client_id, False)

        # 记住客户端的选择
        self._client_tts_engine[client_id] = client_engine
        self._client_tts_voice[client_id] = client_voice

        # 在后台线程中处理 LLM + TTS,避免阻塞 WebSocket 事件循环
        def text_worker():
            """
            【功能说明】文本处理工作线程,处理LLM对话请求并触发TTS合成,支持流式输出

            【参数说明】无参数(闭包捕获text/client/engine/voice)

            【返回值】无返回值,流式输出text_chunk,完成后发送text_done消息
            """
            def _filter_reply(reply):
                """过滤内部提示词泄露和工具调用格式"""
                if "non-text content:" in reply:
                    reply = reply.split("non-text content:")[0]
                if "[non-text" in reply:
                    reply = reply.split("[non-text")[0]
                if "toolCall" in reply:
                    reply = reply.split("toolCall")[0]
                if "tool_result" in reply:
                    reply = reply.split("tool_result")[0]
                # v1.5.4 修复:过滤工具调用格式(TOOL:/ARG:/代码块),防止被 TTS 念出来
                import re as _re
                # 过滤 ``` 代码块(包含 TOOL: ARG: 等格式)
                reply = _re.sub(r'```[\s\S]*?```', '', reply)
                # 过滤行内 TOOL:/ARG: 整行
                lines_filtered = []
                for line in reply.split('\n'):
                    stripped = line.strip()
                    if stripped.startswith('TOOL:') or stripped.startswith('ARG:') or stripped.startswith('<tool') or stripped.startswith('{') or stripped.startswith('</tool'):
                        continue
                    lines_filtered.append(line)
                reply = '\n'.join(lines_filtered)
                # 过滤思考链等
                lines = [l for l in reply.split('\n') if not any(kw in l for kw in ['我应该', '符合我的人设', '用户只是', '应该用', '简单地', '活泼可爱', '方式回应'])]
                return '\n'.join(lines).strip()

            # 尝试使用流式接口(仅 MiniMax 支持)
            llm = self.app.llm
            memory = getattr(self.app, 'memory', None)  # v2.0: 传递记忆系统
            has_stream = hasattr(llm, 'stream_chat')

            if has_stream:
                # ========== 流式模式 ==========
                full_text = ""

                def on_chunk(chunk_text):
                    """
                    【功能说明】流式文本块回调,累积完整文本并实时推送text_chunk给客户端

                    【参数说明】
                        chunk_text (str): LLM流式返回的文本片段

                    【返回值】无返回值
                    """
                    nonlocal full_text
                    full_text += chunk_text
                    try:
                        self.server.send_message(client, json.dumps({
                            "type": "text_chunk", "text": chunk_text
                        }))
                    except Exception:
                        pass

                # v2.0: 传递 memory_system 支持 RAG 注入
                result = llm.stream_chat(text, callback=on_chunk, chunk_size=5, memory_system=memory)
                reply = result.get("text", full_text)
                reply = _filter_reply(reply)

                # 如果流式过程中没过滤掉任何内容,直接用 full_text
                # 否则用过滤后的 reply
                filtered = _filter_reply(full_text)
                if len(filtered) < len(full_text):
                    # 有内容被过滤,通知前端用完整文本替换
                    try:
                        self.server.send_message(client, json.dumps({
                            "type": "text_replace", "text": filtered
                        }))
                    except Exception:
                        pass
                    reply = filtered

                # 发送流结束标记
                try:
                    self.server.send_message(client, json.dumps({
                        "type": "text_done", "text": reply
                    }))
                except Exception:
                    pass
            else:
                # ========== 非流式回退 ==========
                result = llm.chat(text)
                reply = result.get("text", "")
                reply = _filter_reply(reply)

                try:
                    self.server.send_message(client, json.dumps({
                        "type": "text", "text": reply
                    }))
                except Exception:
                    pass

            # ========== 记忆写入（独立于 TTS，确保不因 TTS 异常丢失） ==========
            if reply:
                try:
                    mem = getattr(self.app, 'memory', None)
                    if mem is not None:
                        mem.add_interaction("user", text)
                        mem.add_interaction("assistant", reply)
                    else:
                        # 记忆系统不可用时，仅在首次打印警告
                        if not getattr(self, '_memory_warned', False):
                            print("[WS] ⚠️ 记忆系统不可用，对话将不会被记忆（查看启动日志排查原因）")
                            self._memory_warned = True
                except Exception as mem_err:
                    print(f"[WS] 记忆写入错误: {mem_err}")

            # ========== 历史记录更新（确保历史面板能看到完整对话） ==========
            if reply and hasattr(self.app, 'history'):
                try:
                    self.app.history.append({"role": "user", "content": text})
                    self.app.history.append({"role": "assistant", "content": reply})
                    # 限制历史长度
                    max_history = getattr(self.app, 'MAX_HISTORY', 50)
                    if len(self.app.history) > max_history * 2:
                        self.app.history = self.app.history[-(max_history * 2):]
                except Exception as hist_err:
                    print(f"[WS] 历史更新错误: {hist_err}")

            # ========== TTS 合成（独立 try，失败不影响记忆） ==========
            try:
                if reply:
                    tts_engine = self._get_tts_for_client(client_engine, client_voice)
                    if not tts_engine:
                        print(f"[TTS] 引擎创建失败,使用默认引擎")
                        tts_engine = self.app.tts

                    # GPT-SoVITS 确保切换到正确的项目
                    if client_engine == 'gptsovits' and client_voice and client_voice != 'default':
                        if hasattr(tts_engine, 'set_project'):
                            tts_engine.set_project(client_voice)

                    # v1.9.28: 发送 TTS 开始消息（让前端知道语音合成已开始）
                    self._safe_send(client, {
                        "type": "tts_start",
                        "engine": client_engine,
                    })

                    # v1.8.5: 区分流式分句 / 整段合成模式
                    if client_no_split:
                        # ========== 整段合成模式 ==========
                        # 把完整回复一次性合成为一段音频，不切分
                        reply_clean = reply.replace('\n', ' ').replace('\r', '').strip()
                        print(f"[TTS text] 整段合成模式: {len(reply_clean)} 字符")
                        # v1.9.28: 发送进度（整段合成只有1句）
                        self._safe_send(client, {
                            "type": "tts_progress",
                            "sentence_idx": 0,
                            "total_sentences": 1,
                            "text_preview": reply_clean[:30],
                        })
                        tts_path = tts_engine.speak(reply_clean)
                        if tts_path and os.path.exists(tts_path):
                            url = "/audio/" + os.path.basename(tts_path)
                            print(f"[TTS text] 整段合成完成: {url}")
                            try:
                                self.server.send_message(client, json.dumps({
                                    "type": "tts_done", "audio": url
                                }))
                            except (BrokenPipeError, ConnectionResetError, OSError) as send_err:
                                print(f"[WS] 客户端已断开,忽略发送: {send_err}")
                        else:
                            print(f"[TTS text] 整段合成失败: 无路径返回")
                            # v1.9.28: 通知前端合成失败
                            self._safe_send(client, {
                                "type": "tts_error",
                                "error": "整段合成失败",
                            })
                    else:
                        # ========== 流式分句模式 ==========
                        # 逐句调用 speak_streaming(sentence) → 返回 WAV 路径
                        # 通过 tts_chunk 推送 URL，前端 enqueueTtsChunk 队列播放
                        supports_streaming = hasattr(tts_engine, 'speak_streaming')
                        if supports_streaming:
                            import re as _re_split
                            # 分句前先清理换行，避免换行把句子切成碎片
                            reply_clean = reply.replace('\n', ' ').replace('\r', '').strip()
                            _SENT_SPLIT = _re_split.compile(r'(?<=[。！？.!?])')
                            text_sentences = [s.strip() for s in _SENT_SPLIT.split(reply_clean) if s.strip()]
                            # 过滤纯标点/纯符号/过短的无效句子（至少2个中文字符或3个字符）
                            _MIN_SENT_LEN = 3
                            text_sentences = [s for s in text_sentences
                                              if len(s) >= _MIN_SENT_LEN
                                              and any('\u4e00' <= c <= '\u9fff' for c in s)]
                            if not text_sentences:
                                text_sentences = [reply_clean]
                            total_sents = len(text_sentences)
                            for s_idx, sentence in enumerate(text_sentences):
                                try:
                                    # v1.9.28: 发送每句的合成进度
                                    self._safe_send(client, {
                                        "type": "tts_progress",
                                        "sentence_idx": s_idx,
                                        "total_sentences": total_sents,
                                        "text_preview": sentence[:30],
                                    })
                                    # 逐句合成（不传 on_chunk，直接用返回的 WAV 路径）
                                    tts_path = tts_engine.speak_streaming(sentence, project=client_voice)
                                    if tts_path and os.path.exists(tts_path):
                                        url = "/audio/" + os.path.basename(tts_path)
                                        print(f"[TTS text] 句子 {s_idx+1}/{total_sents} 就绪: {url}")
                                        try:
                                            self.server.send_message(client, json.dumps({
                                                "type": "tts_chunk",
                                                "audio": url,
                                                "sentence_idx": s_idx,
                                                "total_sentences": total_sents,
                                            }))
                                        except Exception as send_err:
                                            print(f"[TTS text] 发送 chunk 失败: {send_err}")
                                    else:
                                        print(f"[TTS text] 句子 {s_idx+1} 合成失败: 无路径返回")
                                except Exception as e:
                                    print(f"[TTS text] 句子 {s_idx+1} 合成异常: {e}")
                            # 全部完成发 tts_done（audio=None 表示不触发整段播放）
                            try:
                                self.server.send_message(client, json.dumps({
                                    "type": "tts_done", "audio": None, "streaming": True
                                }))
                            except Exception:
                                pass
                        else:
                            # 非流式引擎（edge）：整段合成
                            # v1.9.28: 发送进度
                            self._safe_send(client, {
                                "type": "tts_progress",
                                "sentence_idx": 0,
                                "total_sentences": 1,
                                "text_preview": reply[:30],
                            })
                            tts_path = tts_engine.speak(reply)
                            if tts_path and os.path.exists(tts_path):
                                url = "/audio/" + os.path.basename(tts_path)
                                try:
                                    self.server.send_message(client, json.dumps({
                                        "type": "tts_done", "audio": url
                                    }))
                                except (BrokenPipeError, ConnectionResetError, OSError) as send_err:
                                    print(f"[WS] 客户端已断开,忽略发送: {send_err}")
                            else:
                                # v1.9.28: 通知前端合成失败
                                self._safe_send(client, {
                                    "type": "tts_error",
                                    "error": "语音合成失败",
                                })
            except Exception as e:
                print(f"[WS] TTS 错误: {e}")
                import traceback
                traceback.print_exc()
                # v1.9.28: 通知前端 TTS 异常
                self._safe_send(client, {
                    "type": "tts_error",
                    "error": str(e)[:100],
                })

        threading.Thread(target=text_worker, daemon=True).start()

    def _get_tts_for_client(self, engine: str, voice: str):
        """
        根据客户端选择获取 TTS 引擎实例(全局缓存,同 voice 共享同一个引擎).

        缓存策略:
        - GPT-SoVITS: 按 project(voice) 缓存,避免重复加载 pipeline
        - Edge: 无状态,每次创建

        Args:
            engine (str): TTS 引擎名(edge/gptsovits)
            voice (str): 音色名或项目名
        Returns:
            TTS 引擎实例,或 None(引擎不可用)
        """
        if engine == 'edge':
            # Edge TTS 是无状态的,每次创建新实例即可
            try:
                from tts import TTSFactory
                tts_config = self.app.config.config.get("tts", {}).copy()
                tts_config['provider'] = 'edge'
                # v1.7.5 修复: voice='default' 时从 config 读取实际语音名,而非传 'default' 导致 Invalid voice 错误
                default_voice = self.app.config.config.get("tts", {}).get("edge", {}).get("voice", "zh-CN-XiaoxiaoNeural")
                tts_config['edge'] = {'voice': voice if voice != 'default' else default_voice}
                return TTSFactory.create(tts_config)
            except Exception:
                return None

        # GPT-SoVITS:全局缓存,按 voice(项目名)共享同一个实例
        if engine != 'gptsovits':
            return None

        # v1.5.4 修复: voice='default' 时直接使用全局 app.tts 引擎
        # 不能创建新实例,否则 current_project='default' 找不到参考音频 → Invalid voice 'default'
        if not voice or voice == 'default':
            if self.app and self.app.tts:
                print(f"[TTS] voice='default',使用全局 app.tts 引擎 (project={getattr(self.app.tts, 'current_project', '?')})")
                return self.app.tts
            return None

        cache_key = f"gptsovits:{voice}"
        if not hasattr(self, '_tts_engine_cache'):
            self._tts_engine_cache = {}

        # 检查缓存:voice 相同时直接返回已有实例,避免重复加载 pipeline
        if cache_key in self._tts_engine_cache:
            tts_instance = self._tts_engine_cache[cache_key]
            # 如果项目变化才切换;同项目不重新加载
            if (hasattr(tts_instance, 'current_project') and
                    tts_instance.current_project != voice):
                try:
                    tts_instance.set_project(voice)
                except Exception:
                    pass
            return tts_instance

        try:
            from tts import TTSFactory

            tts_config = self.app.config.config.get("tts", {}).copy()
            tts_config['provider'] = 'gptsovits'
            tts_config['gptsovits'] = {
                'device': 'cuda',
                'is_half': True,
                'project': voice,
            }

            print(f"[TTS] 创建引擎: provider=gptsovits, voice={voice}")
            tts_instance = TTSFactory.create(tts_config)
            self._tts_engine_cache[cache_key] = tts_instance
            print(f"[TTS] 引擎创建成功: {type(tts_instance).__name__}")
            return tts_instance
        except Exception as e:
            print(f"[TTS] 创建引擎失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _handle_files(self, client, data):
        """
        [功能说明]处理文件管理请求

        [参数说明]
            client: WebSocket 客户端对象
            data (dict): 消息数据

        [返回值]
            无(通过 WebSocket 发送响应)
        """
        """处理文件管理请求(安全版本 - 白名单路径).支持 list/delete/write 操作."""
        import glob
        import os
        import shutil
        from pathlib import Path
        
        action = data.get("action", "list")
        target = data.get("path", "")
        
        # 安全白名单:允许访问项目目录、临时目录和沙盒允许的路径
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_dir = os.path.dirname(app_dir)  # 项目根目录 (ai-vtuber-fixed/)
        allowed_dirs = [
            Path(project_dir),                     # 项目根目录 (ai-vtuber-fixed/)
            Path(app_dir),                          # app/ 根目录
            Path(app_dir) / "web" / "static",       # web/static/ 目录
            Path(tempfile.gettempdir()),            # 系统临时目录
        ]
        
        # v1.9.2: 沙盒允许的路径也加入白名单（用户可浏览沙盒允许的本地路径）
        subagent = getattr(self.app, 'subagent', None) if self.app else None
        if subagent and hasattr(subagent, 'sandbox') and subagent.sandbox.is_enabled():
            for p in subagent.sandbox.get_paths():
                allowed_dirs.append(Path(p))
        
        # 解析并验证路径
        full_path = Path(target) if os.path.isabs(target) else None
        
        # 如果是相对路径,从白名单中寻找可用的 base_path
        if full_path is None and action == "list":
            for base in allowed_dirs:
                candidate = base / target if target else base
                if candidate.exists():
                    full_path = candidate
                    break
        
        if full_path is None:
            self.server.send_message(client, json.dumps({
                "type": "files", "error": "路径不在白名单内"
            }))
            return
        
        # 验证路径在白名单内(防止 .. 逃逸)
        if not any(full_path.is_relative_to(b) for b in allowed_dirs):
            self.server.send_message(client, json.dumps({
                "type": "files", "error": "禁止访问: 路径遍历检测"
            }))
            return
        
        base_path = str(full_path)
        
        try:
            if action == "list":
                # 列出目录文件 - 限制50个
                if os.path.isdir(base_path):
                    items = []
                    for item in os.listdir(base_path)[:50]:
                        full_path = os.path.join(base_path, item)
                        items.append({
                            "name": item,
                            "type": "dir" if os.path.isdir(full_path) else "file",
                            "size": os.path.getsize(full_path) if os.path.isfile(full_path) else 0
                        })
                    self.server.send_message(client, json.dumps({
                        "type": "files", "data": items, "path": base_path
                    }))
                elif os.path.isfile(base_path):
                    # 读取文件内容-限制10KB
                    with open(base_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(10240)
                    self.server.send_message(client, json.dumps({
                        "type": "files", "content": content, "path": base_path
                    }))
                else:
                    self.server.send_message(client, json.dumps({
                        "type": "files", "error": "路径不存在: " + base_path
                    }))
            elif action == "delete":
                # 删除文件或目录(需要完整路径)
                full_delete_path = data.get("full_path")
                if not full_delete_path:
                    raise ValueError("缺少full_path参数")
                delete_path = Path(full_delete_path)
                # 验证路径在白名单内
                if not any(delete_path.is_relative_to(b) for b in allowed_dirs):
                    raise ValueError("禁止删除: 路径遍历检测")
                if not delete_path.exists():
                    raise FileNotFoundError(f"不存在")
                if delete_path.is_dir():
                    shutil.rmtree(delete_path)
                else:
                    os.remove(delete_path)
                self.server.send_message(client, json.dumps({
                    "type": "files", "success": "已删除", "action": "delete"
                }))
            elif action == "write":
                # 写入文件(需要完整路径)
                full_write_path = data.get("full_path")
                content = data.get("content", "")
                if not full_write_path:
                    raise ValueError("缺少full_path参数")
                write_path = Path(full_write_path)
                # 验证路径在白名单内
                if not any(write_path.is_relative_to(b) for b in allowed_dirs):
                    raise ValueError("禁止写入: 路径遍历检测")
                write_path.parent.mkdir(parents=True, exist_ok=True)
                with open(write_path, 'w', encoding='utf-8') as f:
                    f.write(content[:102400])  # 限制100KB
                self.server.send_message(client, json.dumps({
                    "type": "files", "success": "已保存", "action": "write"
                }))
        except Exception as e:
            self.server.send_message(client, json.dumps({
                "type": "files", "error": str(e)
            }))

    def _handle_memory(self, client, data):
        """处理记忆功能请求 - 适配 v3.0 记忆系统"""
        action = data.get("action", "list")
        
        if not self.app:
            self.server.send_message(client, json.dumps({
                "type": "memory", "error": "App not available"
            }))
            return
        
        memory = getattr(self.app, 'memory', None)
        if memory is None:
            self.server.send_message(client, json.dumps({
                "type": "memory", "error": "记忆系统不可用（初始化失败，请查看后端日志）"
            }))
            return
        
        def _item_to_dict(item, layer_name):
            """MemoryItem → 前端友好的 dict（含遗忘详情）"""
            hours_old = (time.time() - getattr(item, 'timestamp', time.time())) / 3600
            retention = getattr(item, 'get_retention_score', None)
            retention_score = retention() if callable(retention) else 0
            return {
                "role": getattr(item, 'role', '?'),
                "content": getattr(item, 'content', str(item)),
                "layer": layer_name,
                "importance": getattr(item, 'importance', 0),
                "timestamp": getattr(item, 'timestamp', None),
                "is_summary": getattr(item, 'is_summary', False),
                "tags": getattr(item, 'tags', []),
                "facts": getattr(item, 'facts', []),
                "summary_text": getattr(item, 'summary_text', ""),
                # v3.0: 遗忘详情
                "retention_score": round(retention_score, 3),
                "access_count": getattr(item, 'access_count', 1),
                "connectivity": getattr(item, 'connectivity', 0),
                "is_forgotten": getattr(item, 'is_forgotten', False),
                "hours_old": round(hours_old, 1),
            }
        
        try:
            if action == "list":
                memories = []
                # 工作记忆
                for item in memory.working_memory[-30:]:
                    memories.append(_item_to_dict(item, "工作记忆"))
                # 情景记忆
                for item in memory.episodic_memory[-20:]:
                    memories.append(_item_to_dict(item, "情景记忆"))
                # 事实库
                facts = getattr(memory, 'facts', [])
                for fact in facts:
                    memories.append({
                        "role": "fact",
                        "content": fact.content,
                        "layer": "事实库",
                        "importance": 4,
                        "timestamp": fact.timestamp,
                        "is_summary": False,
                        "tags": fact.tags,
                        "source": fact.source,
                        "confidence": fact.confidence,
                    })
                self.server.send_message(client, json.dumps({
                    "type": "memory", "sub_type": "list", "data": memories
                }))
            
            elif action == "stats":
                stats = memory.get_stats()
                stats["working_count"] = len(memory.working_memory)
                stats["episodic_count"] = len(memory.episodic_memory)
                vs = getattr(memory, 'vector_store', None)
                stats["vector_count"] = vs.get_stats()["total_docs"] if vs and hasattr(vs, 'get_stats') else 0
                fs = getattr(memory, 'file_storage', None)
                stats["program_count"] = len(fs.list_daily_files()) if fs and hasattr(fs, 'list_daily_files') else 0
                stats["facts_count"] = len(getattr(memory, 'facts', []))
                self.server.send_message(client, json.dumps({
                    "type": "memory", "sub_type": "stats", "data": stats
                }))
            
            elif action == "summary":
                summary = memory.summarize()
                self.server.send_message(client, json.dumps({
                    "type": "memory", "sub_type": "summary", "data": [{"summary": summary}]
                }))
            
            elif action == "timeline":
                timeline = []
                for item in memory.working_memory:
                    timeline.append(_item_to_dict(item, "工作记忆"))
                for item in memory.episodic_memory:
                    timeline.append(_item_to_dict(item, "情景记忆"))
                # 事实也加入时间线
                for fact in getattr(memory, 'facts', []):
                    timeline.append({
                        "role": "fact",
                        "content": fact.content,
                        "importance": 4,
                        "timestamp": fact.timestamp,
                        "is_summary": False,
                        "layer": "事实库",
                        "tags": fact.tags,
                    })
                timeline.sort(key=lambda x: x.get("timestamp") or 0, reverse=True)
                self.server.send_message(client, json.dumps({
                    "type": "memory_timeline", "data": timeline
                }))
            
            elif action == "search":
                query = data.get("query", "")
                results = memory.search(query, top_k=5)
                adapted = [r if isinstance(r, dict) else {"content": str(r), "role": "system"} for r in results]
                self.server.send_message(client, json.dumps({
                    "type": "memory", "sub_type": "search", "data": adapted
                }))
            
            elif action == "delete":
                # v3.0: 删除记忆
                index = data.get("index", -1)
                layer = data.get("layer", "working")
                ok = memory.delete_memory(index, layer)
                self.server.send_message(client, json.dumps({
                    "type": "memory", "sub_type": "delete", "success": ok
                }))
            
            elif action == "edit":
                # v3.0: 编辑记忆内容
                index = data.get("index", -1)
                content = data.get("content", "")
                layer = data.get("layer", "working")
                ok = memory.edit_memory(index, content, layer)
                self.server.send_message(client, json.dumps({
                    "type": "memory", "sub_type": "edit", "success": ok
                }))
            
            elif action == "set_importance":
                # v3.0: 手动设置重要性
                index = data.get("index", -1)
                importance = data.get("importance", 0)
                layer = data.get("layer", "working")
                ok = memory.set_importance(index, importance, layer)
                self.server.send_message(client, json.dumps({
                    "type": "memory", "sub_type": "set_importance", "success": ok
                }))
            
            elif action == "facts":
                # v3.0: 获取事实列表
                source = data.get("source", None)
                facts = memory.get_facts(source)
                self.server.send_message(client, json.dumps({
                    "type": "memory", "sub_type": "facts", "data": facts
                }))
            
            elif action == "delete_fact":
                # v3.0: 删除事实
                index = data.get("index", -1)
                ok = memory.delete_fact(index)
                self.server.send_message(client, json.dumps({
                    "type": "memory", "sub_type": "delete_fact", "success": ok
                }))
            
            elif action == "consolidate":
                # v3.0: 记忆重整
                result = memory.consolidate()
                self.server.send_message(client, json.dumps({
                    "type": "memory", "sub_type": "consolidate", "data": result
                }))
            
            elif action == "clear":
                memory.clear_all()
                self.server.send_message(client, json.dumps({
                    "type": "memory", "success": True
                }))
            
            elif action == "export":
                exported = memory.export()
                self.server.send_message(client, json.dumps({
                    "type": "memory", "data": [{"export": exported}],
                    "exported": exported[:1000]
                }))
            
            elif action == "import":
                content = data.get("content", "")
                if content:
                    memory.import_backup(content)
                    self.server.send_message(client, json.dumps({
                        "type": "memory", "success": True
                    }))
                else:
                    self.server.send_message(client, json.dumps({
                        "type": "memory", "error": "No content"
                    }))
            
            elif action == "decay_preview":
                # v3.0: 衰减预览
                preview = memory.get_decay_preview()
                self.server.send_message(client, json.dumps({
                    "type": "memory", "sub_type": "decay_preview", "data": preview
                }))
            
            elif action == "search_by_time":
                # v3.0: 按时间范围搜索文件记录
                days = data.get("days", 7)
                results = memory.search_by_time(days)
                self.server.send_message(client, json.dumps({
                    "type": "memory", "sub_type": "search_by_time", "data": results
                }))
        except Exception as e:
            self.server.send_message(client, json.dumps({
                "type": "memory", "error": str(e)
            }))

    def _handle_history(self, client, data):
        """
        [功能说明]处理对话历史请求

        [参数说明]
            client: WebSocket 客户端对象
            data (dict): 消息数据

        [返回值]
            无(通过 WebSocket 发送响应)
        """
        """处理历史功能请求 - 优先从 app.history 获取完整对话历史，回退到记忆系统."""
        action = data.get("action", "list")
        
        if not self.app:
            self.server.send_message(client, json.dumps({
                "type": "history", "error": "App not available"
            }))
            return
        
        try:
            if action == "list":
                history_list = []
                
                # 优先从 app.history 获取完整对话历史（包含所有轮次的 user + assistant）
                app_history = getattr(self.app, 'history', None)
                if app_history and len(app_history) > 0:
                    for item in app_history[-40:]:  # 最近20轮对话（每轮2条）
                        history_list.append({
                            "role": item.get("role", "?"),
                            "content": item.get("content", str(item))
                        })
                else:
                    # 回退：从记忆系统获取
                    memory = getattr(self.app, 'memory', None)
                    if memory:
                        if hasattr(memory, 'working_memory'):
                            for item in memory.working_memory[-20:]:
                                history_list.append({
                                    "role": getattr(item, 'role', '?'),
                                    "content": getattr(item, 'content', str(item))
                                })
                        if hasattr(memory, 'episodic_memory'):
                            for item in memory.episodic_memory[-5:]:
                                history_list.append({
                                    "role": getattr(item, 'role', '?'),
                                    "content": getattr(item, 'content', str(item))
                                })
                
                self.server.send_message(client, json.dumps({
                    "type": "history", "history": history_list
                }))
            elif action == "clear":
                # 清空 app.history 和记忆系统
                app_history = getattr(self.app, 'history', None)
                if app_history is not None:
                    app_history.clear()
                memory = getattr(self.app, 'memory', None)
                if memory:
                    if hasattr(memory, 'working_memory'):
                        memory.working_memory.clear()
                    if hasattr(memory, 'episodic_memory'):
                        memory.episodic_memory.clear()
                self.server.send_message(client, json.dumps({
                    "type": "history", "success": True
                }))
        except Exception as e:
            self.server.send_message(client, json.dumps({
                "type": "history", "error": str(e)
            }))

    def _handle_multimodal(self, client, data):
        """
        [功能说明]处理多模态对话请求(图片+文字)

        [参数说明]
            client: WebSocket 客户端对象
            data (dict): 消息数据,包含 text 和可选的 image 数据

        [返回值]
            无(通过 WebSocket 发送响应)
        """
        """处理多模态对话(图片+文字).目前仅作占位响应(功能开发中)."""
        if not self.app:
            return

        text = data.get("text", "")
        image_b64 = data.get("image")

        print(f"[MULTIMODAL] 文本: {text[:30] if text else '(无)'} | 图片: {'有' if image_b64 else '无'}")

        # TODO: 调用支持多模态的 LLM
        # 目前暂时回复提示
        if image_b64:
            reply = "收到图片了!让我看看...(多模态功能开发中)"
        else:
            reply = "收到消息了!(多模态功能开发中)"

        # 发送回复
        self.server.send_message(client, json.dumps({
            "type": "text", "text": reply
        }))

        # TTS
        if hasattr(self.app, 'tts'):
            try:
                from tts import TTSFactory
                tts = TTSFactory.create(self.app.config.config.get("tts", {}))
                if tts:
                    tts_path = tts.speak(reply)
                    if tts_path and os.path.exists(tts_path):
                        url = "/audio/" + os.path.basename(tts_path)
                        self.server.send_message(client, json.dumps({
                            "type": "tts_done", "audio": url
                        }))
            except Exception as e:
                print(f"[MULTIMODAL] TTS错误: {e}")


    def _handle_vision(self, client, data):
        """
        [功能说明]处理视觉理解请求

        [参数说明]
            client: WebSocket 客户端对象
            data (dict): 消息数据,包含 image 和 prompt

        [返回值]
            无(通过 WebSocket 发送响应)
        """
        """处理视觉功能请求(OCR、理解)"""
        action = data.get("action", "")
        image_b64 = data.get("image")
        provider = data.get("provider")  # 可选:指定 provider

        print(f"[VISION] 动作: {action}")

        # 获取 VisionManager
        vision = getattr(self.app, 'vision', None)
        if not vision:
            self.server.send_message(client, json.dumps({
                "type": "vision_result",
                "error": "Vision 系统未初始化"
            }))
            return

        # 切换 Provider
        if provider and provider != vision.current_provider_name:
            vision.set_provider(provider)
            print(f"[VISION] 切换到: {vision.current_provider_description}")

        try:
            if action == "ocr":
                # OCR 文字识别
                import base64
                image_bytes = base64.b64decode(image_b64) if image_b64 else None
                if image_bytes:
                    # 保存临时图片
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        tmp.write(image_bytes)
                        tmp_path = tmp.name

                    try:
                        result = vision.recognize_text(tmp_path)
                        self.server.send_message(client, json.dumps({
                            "type": "vision_result",
                            "action": "ocr",
                            "text": result or "未识别到文字",
                            "provider": vision.current_provider_name
                        }))
                    finally:
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                else:
                    self.server.send_message(client, json.dumps({
                        "type": "vision_result",
                        "action": "ocr",
                        "text": "未提供图片"
                    }))

            elif action == "understand":
                # 图片理解
                import base64
                image_bytes = base64.b64decode(image_b64) if image_b64 else None
                if image_bytes:
                    # 保存临时图片
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        tmp.write(image_bytes)
                        tmp_path = tmp.name

                    try:
                        result = vision.understand(tmp_path)
                        # 先发送 vision 结果给前端
                        self.server.send_message(client, json.dumps({
                            "type": "vision_result",
                            "action": "understand",
                            "text": result or "无法理解图片",
                            "provider": vision.current_provider_name
                        }))

                        # 自动 TTS 语音播报理解结果
                        if result:
                            self._speak_vision_result(client, result)
                    finally:
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                else:
                    self.server.send_message(client, json.dumps({
                        "type": "vision_result",
                        "action": "understand",
                        "text": "未提供图片"
                    }))

            elif action == "camera_capture":
                # 摄像头捕获
                import base64
                image_bytes = base64.b64decode(image_b64) if image_b64 else None
                if image_bytes:
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        tmp.write(image_bytes)
                        tmp_path = tmp.name

                    try:
                        result = vision.understand(tmp_path)
                        self.server.send_message(client, json.dumps({
                            "type": "vision_result",
                            "action": "camera_capture",
                            "text": result or "无法理解图片",
                            "provider": vision.current_provider_name
                        }))
                        # v1.8.4: 摄像头捕获结果自动 TTS 播报（之前遗漏了）
                        if result:
                            self._speak_vision_result(client, result)
                    finally:
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)

            elif action == "list_providers":
                # 获取可用 Provider 列表
                providers = vision.get_available_providers()
                self.server.send_message(client, json.dumps({
                    "type": "vision_result",
                    "action": "list_providers",
                    "providers": providers,
                    "current": vision.current_provider_name
                }))

            elif action == "set_provider":
                # 切换 Provider
                target = data.get("provider", "auto")
                vision.set_provider(target)
                self.server.send_message(client, json.dumps({
                    "type": "vision_result",
                    "action": "set_provider",
                    "provider": vision.current_provider_name,
                    "description": vision.current_provider_description
                }))

            elif action == "start_monitor":
                # 启动视觉实时监控
                client_id = client['id']
                interval = float(data.get("interval", 2.0))
                monitor_provider = data.get("provider", vision.current_provider_name)
                
                # 切换到指定provider
                if monitor_provider != vision.current_provider_name:
                    vision.set_provider(monitor_provider)
                
                # 如果已在运行,先停止
                if client_id in self._vision_monitors and self._vision_monitors[client_id]['running']:
                    self._stop_vision_monitor(client_id)
                
                # 创建事件回调
                def vision_monitor_callback(result_data):
                    """
                    【功能说明】视觉监控结果回调,将监控数据实时推送给WebSocket客户端

                    【参数说明】
                        result_data (dict): 视觉识别结果,包含图像描述等信息

                    【返回值】无返回值
                    """
                    try:
                        self.server.send_message(client, json.dumps({
                            "type": "vision_monitor",
                            "provider": vision.current_provider_name,
                            **result_data
                        }))
                    except Exception as e:
                        print(f"[VISION_MONITOR] 推送失败: {e}")
                
                # 启动监控线程
                self._vision_monitors[client_id] = {
                    'running': True,
                    'thread': None,
                    'interval': interval,
                    'provider': monitor_provider,
                    'callback': vision_monitor_callback
                }
                
                monitor_thread = threading.Thread(
                    target=self._vision_monitor_worker,
                    args=(client_id, interval),
                    daemon=True
                )
                self._vision_monitors[client_id]['thread'] = monitor_thread
                monitor_thread.start()
                
                self.server.send_message(client, json.dumps({
                    "type": "vision_result",
                    "action": "start_monitor",
                    "running": True,
                    "interval": interval,
                    "provider": vision.current_provider_name
                }))

            elif action == "stop_monitor":
                # 停止视觉监控
                client_id = client['id']
                self._stop_vision_monitor(client_id)
                
                self.server.send_message(client, json.dumps({
                    "type": "vision_result",
                    "action": "stop_monitor",
                    "running": False
                }))

            elif action == "monitor_status":
                # 获取监控状态
                client_id = client['id']
                monitor = self._vision_monitors.get(client_id, {})
                
                self.server.send_message(client, json.dumps({
                    "type": "vision_result",
                    "action": "monitor_status",
                    "running": monitor.get('running', False),
                    "interval": monitor.get('interval', 2.0),
                    "provider": monitor.get('provider', '')
                }))

        except Exception as e:
            print(f"[VISION] 错误: {e}")
            self.server.send_message(client, json.dumps({
                "type": "vision_result",
                "error": str(e)
            }))

    def _speak_vision_result(self, client, text: str):
        """将 Vision 理解结果通过 TTS 语音播报(后台线程)"""
        threading.Thread(
            target=self._speak_vision_result_worker,
            args=(client, text),
            daemon=True
        ).start()

    def _speak_vision_result_worker(self, client, text: str):
        """TTS 播报工作线程(避免阻塞 WebSocket 事件循环)
        
        v1.9.2: 尊重客户端 TTS 面板的流式/整段设置,与聊天对话走同样路径
        """
        try:
            client_id = client.get('id', '')

            # 读取客户端面板选择的 TTS 引擎/音色/模式
            client_engine = self._client_tts_engine.get(client_id, 'gptsovits')
            client_voice = self._client_tts_voice.get(client_id, 'default')
            no_split = self._client_tts_no_split.get(client_id, False)

            tts_engine = None
            if client_engine and client_voice != 'default':
                tts_engine = self._get_tts_for_client(client_engine, client_voice)
                if tts_engine and client_engine == 'gptsovits':
                    if hasattr(tts_engine, 'set_project'):
                        tts_engine.set_project(client_voice)

            if not tts_engine:
                tts_engine = getattr(self.app, 'tts', None)

            if not tts_engine:
                print("[Vision TTS] TTS 不可用,跳过语音播报")
                return

            speak_text = text
            mode_str = '整段' if no_split else '流式分句'
            print(f"[Vision TTS] 播报({len(speak_text)}字, {mode_str}): {speak_text[:80]}...")

            if not no_split:
                # ========== 流式分句模式(与 _handle_tts 相同逻辑) ==========
                import numpy as np
                sentences = WebSocketServer._SENTENCE_END.split(speak_text)
                sentences = [s.strip() for s in sentences if s.strip()]
                if not sentences:
                    sentences = [speak_text.strip()]

                supports_streaming = hasattr(tts_engine, 'speak_streaming')

                for idx, sentence in enumerate(sentences):
                    if not sentence:
                        continue
                    if supports_streaming and client_engine == 'gptsovits':
                        try:
                            chunk_count = [0]
                            def on_vision_chunk(chunk_sr, audio_float, chunk_idx, _sentence=sentence, _count=chunk_count):
                                try:
                                    import soundfile as sf
                                    import base64 as b64
                                    import io
                                    audio_int16 = (audio_float * 32767).astype(np.int16)
                                    buf = io.BytesIO()
                                    sf.write(buf, audio_int16, chunk_sr, format='WAV')
                                    audio_b64 = b64.b64encode(buf.getvalue()).decode('ascii')
                                    self.server.send_message(client, json.dumps({
                                        "type": "realtime_audio_chunk",
                                        "audio": audio_b64,
                                        "text": _sentence,
                                        "chunk_idx": _count[0],
                                        "is_panel": True,
                                    }))
                                    _count[0] += 1
                                except Exception as e:
                                    print(f"[Vision TTS] chunk 发送失败: {e}")

                            if hasattr(tts_engine, 'set_project'):
                                tts_engine.set_project(client_voice)
                            tts_engine.speak_streaming(sentence, project=client_voice, on_chunk=on_vision_chunk)

                            self.server.send_message(client, json.dumps({
                                "type": "realtime_audio_done",
                                "text": sentence,
                                "sentence_idx": idx,
                                "total_sentences": len(sentences),
                                "is_panel": True,
                            }))
                        except Exception as e:
                            print(f"[Vision TTS] 流式失败,回退同步: {e}")
                            audio_path = tts_engine.speak(sentence)
                            if audio_path and os.path.exists(audio_path):
                                audio_url = "/audio/" + os.path.basename(audio_path)
                                self.server.send_message(client, json.dumps({
                                    "type": "tts_chunk",
                                    "audio": audio_url,
                                    "sentence_idx": idx,
                                    "sentence_text": sentence,
                                    "total_sentences": len(sentences),
                                }))
                    else:
                        # 非流式引擎（edge）
                        audio_path = tts_engine.speak(sentence)
                        if audio_path and os.path.exists(audio_path):
                            audio_url = "/audio/" + os.path.basename(audio_path)
                            self.server.send_message(client, json.dumps({
                                "type": "tts_chunk",
                                "audio": audio_url,
                                "sentence_idx": idx,
                                "sentence_text": sentence,
                                "total_sentences": len(sentences),
                            }))

                # 流式完成标记
                self.server.send_message(client, json.dumps({
                    "type": "tts_done",
                    "audio": None,
                    "streaming": True,
                    "total_sentences": len(sentences),
                }))
                print(f"[Vision TTS] 流式播报完成: {len(sentences)} 句")
            else:
                # ========== 整段合成模式 ==========
                audio_path = tts_engine.speak(speak_text)
                if audio_path and os.path.exists(audio_path):
                    url = "/audio/" + os.path.basename(audio_path)
                    self.server.send_message(client, json.dumps({
                        "type": "tts_done",
                        "audio": url
                    }))
                    print(f"[Vision TTS] 整段播报完成: {audio_path}")
                else:
                    print(f"[Vision TTS] speak() 返回无效路径: {audio_path}")
        except Exception as e:
            print(f"[Vision TTS] 播报失败: {e}")
            import traceback
            traceback.print_exc()

    def _stop_vision_monitor(self, client_id):
        """停止视觉监控"""
        if client_id in self._vision_monitors:
            self._vision_monitors[client_id]['running'] = False
            self._vision_monitors[client_id]['thread'] = None

    def _vision_monitor_worker(self, client_id, interval):
        """视觉监控工作线程"""
        import base64
        import tempfile
        
        vision = getattr(self.app, 'vision', None)
        if not vision:
            print(f"[VISION_MONITOR] Vision系统未初始化")
            return
        
        ocr_system = self._get_ocr_system()
        
        while True:
            try:
                # 检查是否停止
                if not self._vision_monitors.get(client_id, {}).get('running', False):
                    print(f"[VISION_MONITOR] client {client_id} 监控已停止")
                    break
                
                # 截取屏幕
                screenshot_b64 = ocr_system.get_screenshot_base64()
                if not screenshot_b64:
                    time.sleep(interval)
                    continue
                
                # 保存临时图片
                image_bytes = base64.b64decode(screenshot_b64)
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp.write(image_bytes)
                    tmp_path = tmp.name
                
                try:
                    # 调用视觉理解
                    start_time = time.time()
                    result = vision.understand(tmp_path)
                    elapsed = (time.time() - start_time) * 1000
                    
                    # 回调通知前端
                    callback = self._vision_monitors.get(client_id, {}).get('callback')
                    if callback:
                        callback({
                            "action": "vision_frame",
                            "text": result or "",
                            "screenshot": screenshot_b64,
                            "elapsed_ms": round(elapsed, 1),
                            "error": None if result else "理解失败"
                        })

                    # 监控模式下也自动 TTS 播报
                    if result:
                        # 找到对应 client 对象发送 TTS
                        for c in self.server.clients:
                            if c.get('id') == client_id:
                                self._speak_vision_result(c, result)
                                break
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                
                # 等待下次
                time.sleep(interval)
                
            except Exception as e:
                print(f"[VISION_MONITOR] 错误: {e}")
                callback = self._vision_monitors.get(client_id, {}).get('callback')
                if callback:
                    callback({
                        "action": "vision_error",
                        "error": str(e)
                    })
                time.sleep(interval)

    def _handle_ocr(self, client, data):
        """
        [功能说明]处理实时屏幕 OCR 请求

        [参数说明]
            client: WebSocket 客户端对象
            data (dict): 消息数据

        [返回值]
            无(通过 WebSocket 发送响应)
        """
        """
        处理 OCR 实时屏幕分析请求

        动作:
        - start: 启动定时监控
        - stop: 停止监控
        - capture: 单次截取 OCR
        - analyze: 分析当前屏幕 (LLM)
        - status: 获取状态
        - tool_call: LLM 工具调用
        """
        action = data.get("action", "")
        client_id = client['id']

        print(f"[OCR] 动作: {action}, client: {client_id}")

        try:
            # 获取或初始化 OCR 系统
            ocr_system = self._get_ocr_system()

            if action == "start":
                # 启动定时监控
                interval = float(data.get("interval", 1.0))
                ocr_system.interval = max(0.5, interval)

                # 设置事件回调
                def ocr_event_callback(event_type, event_data):
                    """
                    【功能说明】OCR事件回调,将识别到的事件数据推送给WebSocket客户端

                    【参数说明】
                        event_type (str): 事件类型
                        event_data (dict): 事件相关数据

                    【返回值】无返回值
                    """
                    try:
                        self.server.send_message(client, json.dumps({
                            "type": "ocr_event",
                            "event": event_type,
                            "data": event_data
                        }))
                    except Exception as e:
                        print(f"[OCR] 事件推送失败: {e}")

                ocr_system.set_event_callback(ocr_event_callback)

                if not ocr_system.is_running():
                    ocr_system.start_monitor(interval)

                self.server.send_message(client, json.dumps({
                    "type": "ocr_status",
                    "running": True,
                    "interval": ocr_system.interval
                }))

            elif action == "stop":
                # 停止监控
                ocr_system.stop_monitor()
                ocr_system.set_event_callback(None)

                self.server.send_message(client, json.dumps({
                    "type": "ocr_status",
                    "running": False
                }))

            elif action == "capture":
                # 单次截取 OCR
                result = ocr_system.capture_and_ocr()

                if result:
                    # 读取截图
                    screenshot_b64 = None
                    try:
                        with open(result.screenshot_path, "rb") as f:
                            import base64
                            screenshot_b64 = base64.b64encode(f.read()).decode()
                    except:
                        pass

                    self.server.send_message(client, json.dumps({
                        "type": "ocr_result",
                        "text": result.text,
                        "timestamp": result.timestamp,
                        "screenshot": screenshot_b64
                    }))
                else:
                    self.server.send_message(client, json.dumps({
                        "type": "ocr_result",
                        "text": "",
                        "error": "截图失败"
                    }))

            elif action == "capture_for_vision":
                # 截取屏幕并返回 base64(供 Vision Provider 使用)
                screenshot_b64 = ocr_system.get_screenshot_base64()
                if screenshot_b64:
                    self.server.send_message(client, json.dumps({
                        "type": "screenshot_captured",
                        "screenshot": screenshot_b64
                    }))
                else:
                    self.server.send_message(client, json.dumps({
                        "type": "screenshot_captured",
                        "error": "截图失败"
                    }))
                return

            elif action == "analyze":
                # LLM 分析当前屏幕(纯文字模式,不使用 Vision Provider)
                # ⚠️ 注意:前端"快速分析"/"详细分析"已改为使用 Vision Provider
                # 此 action 仅作纯 OCR+LLM 文字分析回退使用
                analysis_type = data.get("analysis_type", "quick")  # quick / detailed

                if analysis_type == "quick":
                    prompt = """分析当前屏幕内容,简洁回答:
1. 这是什么应用/游戏
2. 当前状态
3. 是否有需要关注的点"""
                else:
                    prompt = """详细分析当前屏幕:
1. 识别所有文字内容
2. 分析界面元素
3. 判断当前状态
4. 如果是游戏,给出策略建议"""

                # 获取截图和 OCR 结果
                screenshot_b64 = ocr_system.get_screenshot_base64()
                last_result = ocr_system.get_last_ocr()
                ocr_text = last_result.text if last_result else ""

                if not screenshot_b64:
                    self.server.send_message(client, json.dumps({
                        "type": "ocr_analysis",
                        "error": "截图失败"
                    }))
                    return

                # 使用 LLM 分析
                try:
                    # 构造分析文本:prompt + OCR 文字
                    if ocr_text:
                        analysis_prompt = f"{prompt}\n\n屏幕上的文字:\n{ocr_text}"
                    else:
                        analysis_prompt = f"{prompt}\n\n(屏幕无文字内容)"

                    # 调用 LLM
                    if hasattr(self.app, 'llm'):
                        result = self.app.llm.chat(message=analysis_prompt)
                        analysis = result.get("text", "分析失败")
                    else:
                        analysis = f"OCR识别: {ocr_text[:200]}..." if ocr_text else "未识别到文字"

                    self.server.send_message(client, json.dumps({
                        "type": "ocr_analysis",
                        "analysis": analysis,
                        "ocr_text": ocr_text
                    }))

                except Exception as e:
                    print(f"[OCR] LLM分析失败: {e}")
                    self.server.send_message(client, json.dumps({
                        "type": "ocr_analysis",
                        "error": str(e),
                        "ocr_text": ocr_text
                    }))

            elif action == "status":
                # 获取状态
                status = ocr_system.get_status()

                self.server.send_message(client, json.dumps({
                    "type": "ocr_status",
                    **status
                }))

            elif action == "tool_call":
                # LLM 工具调用: 查看屏幕
                tool_name = data.get("tool_name", "")

                if tool_name in ["screen_ocr", "查看屏幕", "screen"]:
                    result = ocr_system.capture_and_ocr()

                    if result:
                        # 读取截图
                        screenshot_b64 = None
                        try:
                            with open(result.screenshot_path, "rb") as f:
                                import base64
                                screenshot_b64 = base64.b64encode(f.read()).decode()
                        except:
                            pass

                        self.server.send_message(client, json.dumps({
                            "type": "ocr_tool_result",
                            "tool_name": tool_name,
                            "text": result.text,
                            "screenshot": screenshot_b64,
                            "timestamp": result.timestamp
                        }))
                    else:
                        self.server.send_message(client, json.dumps({
                            "type": "ocr_tool_result",
                            "tool_name": tool_name,
                            "text": "",
                            "error": "截图失败"
                        }))

            else:
                self.server.send_message(client, json.dumps({
                    "type": "ocr_error",
                    "error": f"未知动作: {action}"
                }))

        except Exception as e:
            print(f"[OCR] 错误: {e}")
            import traceback
            traceback.print_exc()
            self.server.send_message(client, json.dumps({
                "type": "ocr_error",
                "error": str(e)
            }))

    def _create_dummy_ocr(error_msg="OCR 不可用"):
        """创建一个空的 OCR 系统替代(当真实 OCR 初始化失败时使用)
        实现 OCRSystem 的完整接口,避免调用方 AttributeError
        """
        class DummyOCRSystem:
            """空的 OCR 系统替代(当真实 OCR 初始化失败时使用)"""
            def set_event_callback(self, callback):
                """设置事件回调函数"""
                self._event_callback = callback
            def start_monitor(self, interval=1.0):
                """启动监控(空实现)"""
                print(f"[OCR Dummy] OCR 不可用,无法启动监控: {error_msg}")
            def stop_monitor(self):
                """停止监控(空实现)"""
                pass
            def capture_and_ocr(self):
                """截取屏幕并 OCR(空实现)"""
                return None
            def get_screenshot_base64(self):
                """获取屏幕截图 base64(空实现)"""
                return None
            def get_last_ocr(self):
                """获取最近一次 OCR 结果(空实现)"""
                return None
            def get_history(self, limit=10):
                """获取 OCR 历史(空实现)"""
                return []
            def analyze_screen(self, prompt=None):
                """分析屏幕(空实现)"""
                return None
            def is_running(self):
                """检查是否在运行"""
                return False
            def get_status(self):
                """获取状态"""
                return {"error": error_msg, "running": False}
            def close(self):
                """关闭(空实现)"""
                pass
        return DummyOCRSystem()

    def _get_ocr_system(self):
        """获取 OCR 系统实例"""
        client_id = id(self)

        # 使用 app 级别的 OCR 系统
        if not hasattr(self.app, '_ocr_system'):
            try:
                from app.ocr import get_ocr_system
                # 传入 LLM 配置
                llm_config = {}
                if hasattr(self.app, 'config'):
                    llm_config = self.app.config.config.get('llm', {})

                ocr_config = self.app.config.config.get('ocr', {})
                ocr_config['analyzer'] = {'llm_config': llm_config}

                self.app._ocr_system = get_ocr_system(ocr_config)
                print("[OCR] OCR 系统初始化完成")
            except ImportError as e:
                print(f"[OCR] OCR 模块导入失败: {e}")
                # 返回一个空壳(实现 OCRSystem 的完整接口)
                self.app._ocr_system = self._create_dummy_ocr("OCR 模块未安装")
            except Exception as e:
                print(f"[OCR] OCR 系统初始化失败: {e}")
                self.app._ocr_system = self._create_dummy_ocr(str(e))

        return self.app._ocr_system

    def _handle_system_stats(self, client):
        """
        [功能说明]处理系统状态查询请求(GPU/内存)

        [参数说明]
            client: WebSocket 客户端对象

        [返回值]
            无(通过 WebSocket 发送响应)
        """
        """处理系统统计请求"""
        try:
            stats = {}

            # GPU 内存
            try:
                import subprocess
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=memory.used,memory.total,temperature.gpu', '--format=csv,noheader,nounits'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split(',')
                    if len(parts) >= 3:
                        stats['vram_used'] = int(parts[0].strip())
                        stats['vram_total'] = int(parts[1].strip())
                        stats['gpu_temp'] = int(parts[2].strip())
                        stats['gpu_memory'] = round(stats['vram_used'] / stats['vram_total'] * 100, 1)
            except Exception as e:
                print(f"[STATS] GPU获取失败: {e}")

            # 系统内存
            try:
                import psutil
                mem = psutil.virtual_memory()
                stats['ram_used'] = int(mem.used)
                stats['ram_total'] = int(mem.total)
            except ImportError:
                # psutil 未安装,使用默认值
                stats['ram_used'] = 0
                stats['ram_total'] = 0

            self.server.send_message(client, json.dumps({
                "type": "system_stats",
                **stats
            }))
        except Exception as e:
            print(f"[STATS] 错误: {e}")
            # v1.9.22: 即使出错也返回空数据（避免前端一直等不到响应）
            try:
                self.server.send_message(client, json.dumps({
                    "type": "system_stats",
                    "error": str(e)
                }))
            except Exception:
                pass

    def _handle_config(self, client, data):
        """
        [功能说明]处理配置更新请求

        [参数说明]
            client: WebSocket 客户端对象
            data (dict): 消息数据,包含要更新的配置项

        [返回值]
            无(通过 WebSocket 发送响应)
        """
        """处理配置更新请求"""
        action = data.get("action", "")
        config = data.get("config", {})

        print(f"[CONFIG] 动作: {action}")

        if action == "update":
            # 保存配置到文件或内存
            try:
                if self.app and hasattr(self.app, 'config'):
                    # 更新内存配置
                    if 'tts' in config:
                        self.app.config.config.setdefault('tts', {}).update(config['tts'])
                    if 'llm' in config:
                        self.app.config.config.setdefault('llm', {}).update(config['llm'])
                    if 'asr' in config:
                        self.app.config.config.setdefault('asr', {}).update(config['asr'])
                    if 'memory' in config:
                        mem_cfg = config['memory']
                        self.app.config.config.setdefault('memory', {}).update(mem_cfg)
                        # v3.0: 实时应用到记忆系统
                        mem = getattr(self.app, 'memory', None)
                        if mem is not None:
                            if 'short_limit' in mem_cfg or 'working_memory_limit' in mem_cfg:
                                mem.working_memory_limit = mem_cfg.get('working_memory_limit', mem_cfg.get('short_limit', mem.working_memory_limit))
                            if 'summarize_threshold' in mem_cfg:
                                mem.summarize_threshold = mem_cfg['summarize_threshold']
                            if 'forgetting_threshold' in mem_cfg or 'importance_threshold' in mem_cfg:
                                from memory import RetentionScorer
                                RetentionScorer.RETENTION_THRESHOLD = mem_cfg.get('forgetting_threshold', mem_cfg.get('importance_threshold', 0.15))
                            if 'decay_lambda' in mem_cfg:
                                RetentionScorer.DECAY_LAMBDA = float(mem_cfg['decay_lambda'])
                            if 'grace_period_hours' in mem_cfg:
                                from memory import RetentionScorer
                                RetentionScorer.GRACE_PERIOD_HOURS = float(mem_cfg['grace_period_hours'])
                            if 'auto_store' in mem_cfg:
                                mem.auto_store = bool(mem_cfg['auto_store'])

                self.server.send_message(client, json.dumps({
                    "type": "config_result",
                    "success": True
                }))
            except Exception as e:
                self.server.send_message(client, json.dumps({
                    "type": "config_result",
                    "error": str(e)
                }))
        else:
            self.server.send_message(client, json.dumps({
                "type": "config_result",
                "error": "未知操作"
            }))

    def _handle_set_api_key(self, client, data):
        """
        [功能说明]处理API Key设置请求，动态更新LLM和Vision模块的API Key

        [参数说明]
            client: WebSocket 客户端对象
            data (dict): 消息数据，包含:
                - provider (str): 提供商标识，如 "minimax"
                - api_key (str): 新的API Key

        [设计意图]
            用户在前端输入API Key后，自动传播到LLM和Vision模块，
            无需重启服务即可生效。Key保存到 app/cache/api_keys.json，
            下次启动时自动加载。
        """
        provider = data.get("provider", "minimax")
        api_key = data.get("api_key", "")

        if not api_key:
            self.server.send_message(client, json.dumps({
                "type": "api_key_result",
                "success": False,
                "error": "API Key 不能为空"
            }))
            return

        try:
            # 1. 持久化到 app/cache/api_keys.json
            import tempfile
            cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
            os.makedirs(cache_dir, exist_ok=True)
            keys_file = os.path.join(cache_dir, "api_keys.json")
            
            # 读取已有的keys
            existing_keys = {}
            if os.path.exists(keys_file):
                try:
                    with open(keys_file, "r", encoding="utf-8") as f:
                        existing_keys = json.load(f)
                except Exception:
                    pass
            
            # 更新key（只存key的前4位+后4位用于显示确认）
            existing_keys[provider] = api_key
            
            # 原子写入
            fd, tmp_path = tempfile.mkstemp(dir=cache_dir, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(existing_keys, f, ensure_ascii=False)
                os.replace(tmp_path, keys_file)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise

            # 2. 先更新内存中的config对象（必须在懒加载之前！）
            if self.app and hasattr(self.app, 'config'):
                try:
                    if hasattr(self.app.config, 'config'):
                        llm_section = self.app.config.config.setdefault('llm', {})
                        provider_section = llm_section.setdefault(provider, {})
                        provider_section['api_key'] = api_key
                        # 同步更新vision的minimax_vl配置
                        vision_section = self.app.config.config.setdefault('vision', {})
                        minimax_vl = vision_section.setdefault('minimax_vl', {})
                        minimax_vl['api_key'] = api_key
                        print(f"[API Key] 内存配置已更新")
                except Exception as e:
                    print(f"[API Key] 更新内存配置失败: {e}")

            # 3. 动态更新LLM模块的API Key
            llm_updated = False
            if self.app and hasattr(self.app, '_lazy_modules'):
                llm = self.app._lazy_modules.get('llm')
                if llm is None:
                    # LLM 还没懒加载，通过 property 触发加载（此时 config 已更新，会用新 key）
                    try:
                        llm = self.app.llm
                    except Exception as e:
                        print(f"[API Key] 加载 LLM 失败: {e}")
                        llm = None
                if llm is not None and hasattr(llm, 'api_key'):
                    llm.api_key = api_key
                    # 更新HTTP Session的认证头
                    if hasattr(llm, '_session'):
                        if hasattr(llm, '_is_anthropic') and llm._is_anthropic:
                            llm._session.headers["x-api-key"] = api_key
                        else:
                            llm._session.headers["Authorization"] = f"Bearer {api_key}"
                    llm_updated = True
                    # 清除缓存（API Key 变更后旧缓存无效）
                    if hasattr(llm, '_cache'):
                        with llm._cache_lock:
                            llm._cache.clear()
                    print(f"[API Key] LLM [{llm.name}] 已更新")

            # 4. 动态更新Vision模块的API Key
            vision_updated = False
            if self.app and hasattr(self.app, '_lazy_modules'):
                vision = self.app._lazy_modules.get('vision')
                if vision is None:
                    # Vision 还没懒加载，通过 property 触发加载（此时 config 已更新）
                    try:
                        vision = self.app.vision
                    except Exception as e:
                        print(f"[API Key] 加载 Vision 失败: {e}")
                        vision = None
                if vision is not None and hasattr(vision, '_providers'):
                    for provider_type, vp in vision._providers.items():
                        if hasattr(vp, 'api_key') and 'minimax' in str(provider_type).lower():
                            vp.api_key = api_key
                            vision_updated = True
                            print(f"[API Key] Vision provider {provider_type} 已更新")

            key_preview = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
            print(f"[API Key] {provider} 已更新: {key_preview} (LLM={llm_updated}, Vision={vision_updated})")

            self.server.send_message(client, json.dumps({
                "type": "api_key_result",
                "success": True,
                "provider": provider,
                "key_preview": key_preview,
                "llm_updated": llm_updated,
                "vision_updated": vision_updated
            }))

        except Exception as e:
            print(f"[API Key] 设置失败: {e}")
            self.server.send_message(client, json.dumps({
                "type": "api_key_result",
                "success": False,
                "error": str(e)
            }))

    def _handle_get_api_key_status(self, client, data):
        """查询API Key配置状态（不返回key本身，只返回是否已配置和预览）"""
        provider = data.get("provider", "minimax")
        
        configured = False
        key_preview = ""
        
        # v1.9.38: 先获取当前活跃的 provider（从 config 的 llm.provider 字段）
        active_provider = provider
        if self.app and hasattr(self.app, 'config'):
            llm_cfg = self.app.config.config.get('llm', {})
            active_provider = llm_cfg.get('provider', provider)
        
        # 如果前端传的 provider 与活跃 provider 不一致，用活跃 provider
        if provider != active_provider:
            provider = active_provider
        
        # 检查LLM模块（通过 _lazy_modules 字典访问）
        if self.app and hasattr(self.app, '_lazy_modules'):
            llm = self.app._lazy_modules.get('llm')
            if llm is None:
                # LLM 还没加载，尝试从 config 中检查
                try:
                    llm_config = self.app.config.config.get('llm', {}).get(provider, {})
                    config_key = llm_config.get('api_key', '')
                    if config_key and config_key != '${MINIMAX_API_KEY}':
                        configured = True
                        key_preview = config_key[:4] + "..." + config_key[-4:] if len(config_key) > 8 else "***"
                except Exception:
                    pass
            elif hasattr(llm, 'api_key') and llm.api_key:
                configured = True
                key_preview = llm.api_key[:4] + "..." + llm.api_key[-4:] if len(llm.api_key) > 8 else "***"
        
        self.server.send_message(client, json.dumps({
            "type": "api_key_status",
            "provider": provider,
            "configured": configured,
            "key_preview": key_preview
        }))

    def _handle_tool(self, client, data):
        """
        [功能说明]处理工具执行请求

        [参数说明]
            client: WebSocket 客户端对象
            data (dict): 消息数据,包含 tool_name 和参数

        [返回值]
            无(通过 WebSocket 发送响应)
        """
        """处理工具执行请求"""
        tool = data.get("tool", "")
        args = data.get("args", {})
        tool_id = data.get("id", "")

        print(f"[TOOL] 执行: {tool} | 参数: {args}")

        try:
            # 导入工具系统
            from app.tools import ToolFactory

            # 检查工具是否存在
            tool_instance = ToolFactory.create(tool)
            if not tool_instance:
                self.server.send_message(client, json.dumps({
                    "type": "tool_result",
                    "tool_id": tool_id,
                    "tool": tool,
                    "success": False,
                    "error": f"未知工具: {tool}"
                }))
                return

            # 执行工具
            result = tool_instance.execute(**args)

            # 发送结果
            self.server.send_message(client, json.dumps({
                "type": "tool_result",
                "tool_id": tool_id,
                "tool": tool,
                "success": result.get("success", False),
                "result": result
            }))

            print(f"[TOOL] {tool} 执行完成: {result.get('success', False)}")

        except Exception as e:
            print(f"[TOOL] 错误: {e}")
            self.server.send_message(client, json.dumps({
                "type": "tool_result",
                "tool_id": tool_id,
                "tool": tool,
                "success": False,
                "error": str(e)
            }))

    def stop(self):
        """停止 WebSocket 服务器"""
        if self.server:
            try:
                self.server.shutdown()
            except Exception:
                pass

    def shutdown(self):
        """关闭 WebSocket 服务器"""
        self.stop()

    # ========== 训练模块 ==========
    def _handle_train(self, client, data):
        """
        [功能说明]处理训练管理请求

        [参数说明]
            client: WebSocket 客户端对象
            data (dict): 消息数据,包含训练相关操作

        [返回值]
            无(通过 WebSocket 发送响应)
        """
        """处理训练相关请求"""
        action = data.get("action", "")

        print(f"[TRAIN] 动作: {action}")

        try:
            # 直接导入 trainer.manager(app/ 在 sys.path 中)
            from trainer.manager import TrainingManager
            
            # 使用全局单例
            if not hasattr(self, '_train_manager'):
                self._train_manager = TrainingManager()
            manager = self._train_manager

            # 设置进度回调
            def progress_callback(progress_info):
                """
                【功能说明】训练进度回调,将训练进度信息推送给WebSocket客户端

                【参数说明】
                    progress_info (dict): 训练进度信息字典

                【返回值】无返回值
                """
                self.server.send_message(client, json.dumps({
                    "type": "train_progress",
                    **progress_info
                }))

            manager.set_progress_callback(progress_callback)

            if action == "list_projects":
                # 列出所有项目
                projects = manager.list_projects()
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "list_projects",
                    "success": True,
                    "projects": projects
                }))

            elif action == "create_project":
                # 创建新项目
                project_name = data.get("project_name", "")
                if not project_name:
                    raise ValueError("项目名称不能为空")
                result = manager.create_project(project_name)
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "create_project",
                    **result
                }))

            elif action == "get_project":
                # 获取项目信息
                project_name = data.get("project_name", "")
                result = manager.get_project_info(project_name)
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "get_project",
                    **result
                }))

            elif action == "switch_checkpoint":
                # 切换模型
                project_name = data.get("project_name", "")
                checkpoint_name = data.get("checkpoint_name", "")
                result = manager.switch_checkpoint(project_name, checkpoint_name)
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "switch_checkpoint",
                    **result
                }))

            elif action == "delete_audio":
                # 删除单个音频
                project_name = data.get("project_name", "")
                filename = data.get("filename", "")
                if not project_name or not filename:
                    self.server.send_message(client, json.dumps({
                        "type": "train_result",
                        "action": "delete_audio",
                        "success": False,
                        "error": "缺少项目名称或文件名"
                    }))
                else:
                    result = manager.delete_audio(project_name, filename)
                    self.server.send_message(client, json.dumps({
                        "type": "train_result",
                        "action": "delete_audio",
                        **result
                    }))

            elif action == "reset_project":
                # 重置项目
                project_name = data.get("project_name", "")
                delete_all = data.get("delete_all", False)
                if not project_name:
                    raise ValueError("项目名称不能为空")
                result = manager.reset_project(project_name, delete_all)
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "reset_project",
                    **result
                }))

            elif action == "upload_audio":
                # 上传音频文件
                import base64
                project_name = data.get("project_name", "")
                filename = data.get("filename", "")
                audio_b64 = data.get("audio_data", "")

                if not all([project_name, filename, audio_b64]):
                    raise ValueError("缺少必要参数")

                audio_bytes = base64.b64decode(audio_b64)
                result = manager.save_audio(project_name, filename, audio_bytes)
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "upload_audio",
                    **result
                }))

            elif action == "upload_text":
                # 上传文本
                project_name = data.get("project_name", "")
                audio_filename = data.get("audio_filename", "")
                text = data.get("text", "")

                if not all([project_name, audio_filename, text]):
                    raise ValueError("缺少必要参数")

                result = manager.save_text(project_name, audio_filename, text)
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "upload_text",
                    **result
                }))
            
            elif action == "recognize_audio":
                # 使用 STT 识别音频文本
                project_name = data.get("project_name", "")
                audio_filename = data.get("audio_filename", "")

                if not all([project_name, audio_filename]):
                    raise ValueError("缺少必要参数")

                result = manager.recognize_audio_text(project_name, audio_filename)
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "recognize_audio",
                    **result
                }))

            elif action == "preprocess":
                # 预处理音频
                project_name = data.get("project_name", "")
                result = manager.preprocess_audio(project_name)
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "preprocess",
                    **result
                }))

            elif action == "extract_features":
                # 提取特征
                project_name = data.get("project_name", "")
                result = manager.extract_features(project_name)
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "extract_features",
                    **result
                }))

            elif action == "start_training":
                # 开始训练
                project_name = data.get("project_name", "")
                config = data.get("config", {})
                result = manager.start_training(project_name, config)
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "start_training",
                    **result
                }))

            elif action == "get_status":
                # 获取训练状态
                status = manager.get_training_status()
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "get_status",
                    **status
                }))

            elif action == "stop_training":
                # 停止训练
                result = manager.stop_training()
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "stop_training",
                    **result
                }))

            elif action == "prepare_s2_data":
                # 准备 S2 训练数据
                project_name = data.get("project_name", "")
                result = manager.prepare_s2_data(project_name)
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "prepare_s2_data",
                    **result
                }))

            elif action == "start_s2_training":
                # 开始 S2 训练
                project_name = data.get("project_name", "")
                config = data.get("config", {})
                result = manager.start_s2_training(project_name, config)
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "start_s2_training",
                    **result
                }))

            elif action == "get_train_defaults":
                # 获取训练参数默认值
                project_name = data.get("project_name", "")
                result = manager.get_train_defaults(project_name)
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "get_train_defaults",
                    **result
                }))

            elif action == "save_train_defaults":
                # 保存训练参数默认值
                project_name = data.get("project_name", "")
                s1_config = data.get("s1_config", {})
                s2_config = data.get("s2_config", {})
                result = manager.save_train_defaults(project_name, s1_config, s2_config)
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "save_train_defaults",
                    **result
                }))

            elif action == "delete_s1_training":
                # 单独删除 S1 训练产物
                project_name = data.get("project_name", "")
                result = manager.delete_s1_training(project_name)
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "delete_s1_training",
                    **result
                }))

            elif action == "delete_s2_training":
                # 单独删除 S2 训练产物
                project_name = data.get("project_name", "")
                result = manager.delete_s2_training(project_name)
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "action": "delete_s2_training",
                    **result
                }))

            else:
                self.server.send_message(client, json.dumps({
                    "type": "train_result",
                    "success": False,
                    "error": f"未知动作: {action}"
                }))

        except Exception as e:
            print(f"[TRAIN] 错误: {e}")
            import traceback
            traceback.print_exc()
            self.server.send_message(client, json.dumps({
                "type": "train_result",
                "success": False,
                "error": str(e)
            }))

    # ========== 实时语音对话 (方案 C) ==========

    # ============================================================
    # 增强分句器(参照 RealtimeVoiceChat 优化)
    # 关键:更智能的分句 = 更快的首句检测 = 更低的 TTS 首响延迟
    # ============================================================
    # v1.5.3 优化:分句策略调整
    # 只保留句号作为主要分句点(逗号不切)
    # 感叹号和问号要恢复,作为实时语音 LLM 输出的分句点
    _SENTENCE_END = re.compile(r'[.!?.!?]+')

    # 次要停顿点(用于 buffer 积压时的 fallback,不主动分句)
    _SECONDARY_END = re.compile(r'[,,;;\n]+')

    # LLM "思考中" 模式检测(检测到这些模式时,不要急着切句)
    # 参考 RealtimeVoiceChat 的 DistilBERT 句子完成度判断
    _THINKING_PATTERNS = re.compile(
        r'(让我想想|让我想一想|嗯|呃|这个嘛|等一下|稍等|我看看|我查一下|'
        r'根据|按照|根据上下文|从|关于|首先|第一|其实|也就是说|'
        r'也就是说|换句话说|总的来说|总的来说|简单来说|简单说)'
    )

    # 句子开头不完整模式(句首有这些词时,整句可能不完整)
    _INCOMPLETE_START = re.compile(
        r'^(但是|不过|然而|所以|然后|而且|或者|因为|虽然|如果|'
        r'虽然说|既然|因此|虽然|只是|只是说|尤其是)'
    )

    @staticmethod
    def _split_sentences_streaming(buffer: str, new_text: str, is_first_sentence: bool = False):
        """
        增量分句:将新追加的文本与 buffer 合并后,提取出完整句子.

        v1.5.3 优化(解决分句过碎问题):
        1. 感叹问候合并:短感叹句(< 15字)且后面还有内容 → 合并到下一句
           防止 "喵~" "早上好" 被单独发送,导致语调割裂
        2. 短句合并:15字以内的句子(感叹/称呼类)→ 合并到下一句
        3. 首句优先:第一个完整句子立即返回,不等待后续
        4. 句末感叹词保护:句末是 ~ 喵 啊 呀 的句子不主动拆分

        Args:
            buffer: 当前累积的未分句文本
            new_text: 新追加的文本
            is_first_sentence: 是否是首个句子(首个句子用更激进的策略)
        Returns:
            (sentences_list, remaining_buffer)
        """
        buffer += new_text
        sentences = []

        # 找所有分句点(只按句号、感叹号、问号分句)
        matches = list(WebSocketServer._SENTENCE_END.finditer(buffer))

        if not matches:
            return sentences, buffer

        # 分析每个分句点
        last_end = 0
        for i, m in enumerate(matches):
            sent = buffer[last_end:m.end()].strip()
            last_end = m.end()

            if not sent:
                continue

            # === v1.5.3 简化: 感叹/问候合并策略 ===
            # 只合并真正无意义的超短感叹词(< 5字且纯感叹),避免误过滤有效句子
            # 注意:嗨嗨~喵!这样的句子 = 有意义的问候,不能跳过
            EXCLAMATORY_PATTERNS = [
                r'^喵[~!.]*$',                    # 纯"喵" 无内容
                r'^嗯嗯?[!.]*$',                 # 嗯/嗯嗯
                r'^哦[!.~]*$',                   # 哦!/哦.
                r'^啊[!.]*$',                    # 啊!/啊.
                r'^呀[!.]*$',                    # 呀!
                r'^嘿[!.]*$',                    # 嘿!
            ]
            is_short_exclamatory = len(sent) < 5 and any(
                re.match(p, sent) for p in EXCLAMATORY_PATTERNS
            )
            # 检查后面是否还有内容(不是最后一个分句点)
            has_more_after = last_end < len(buffer.strip())
            if is_short_exclamatory and has_more_after:
                # 合并到下一句:跳过这个句子,等下一个完整句子
                print(f"[REALTIME] 分句优化: 合并感叹句 '{sent}' 到下一句")
                continue
            # === v1.5.3 感叹合并结束 ===

            # === 思考模式检测 ===
            if WebSocketServer._THINKING_PATTERNS.match(sent):
                continue

            # === 句首不完整检测 ===
            if WebSocketServer._INCOMPLETE_START.match(sent):
                if len(sent) < 10:
                    continue  # 可能是半句话,跳过

            # === 首句优先策略 ===
            if is_first_sentence and i == 0:
                pass  # 首句:只要有明确的句子结束符,就立即返回

            # 句子有效,加入列表
            sentences.append(sent)

        # 剩余的 buffer
        remaining = buffer[last_end:] if last_end > 0 else buffer

        return sentences, remaining

    def __init_realtime_state(self):
        """确保实时对话状态存在"""
        if not hasattr(self, '_realtime'):
            self._realtime = {}
        # 每个 client_id 的状态
        # {client_id: {"active": bool, "speaking": bool, "cancel": threading.Event,
        #               "audio_buffer": bytes, "audio_lock": threading.Lock,
        #               "tts_thread": threading.Thread, "sentence_buffer": str,
        #               "current_gen": str, "tts_queue": Queue}}

    def _get_realtime_state(self, client_id):
        """获取或创建客户端的实时对话状态"""
        self.__init_realtime_state()
        if client_id not in self._realtime:
            self._realtime[client_id] = {
                "active": False,
                "speaking": False,
                "cancel": threading.Event(),  # 保留用于快速打断
                "audio_buffer": b"",
                "audio_lock": threading.Lock(),
                "tts_thread": None,
                "sentence_buffer": "",
                "running": False,
                "current_gen": None,  # v1.8: Generation ID,消除 cancel 竞态窗口
                "tts_queue": Queue(),  # 并行 TTS 任务队列(每句一个 worker 异步合成)
                "streaming_audio_path": None,  # 流式 TTS 临时文件路径(P0-2)
                "tts_worker_active": False,  # v1.8: TTS worker 线程是否活跃
                "tts_sentence_queue": None,  # v1.8: 异步 TTS 句子队列
            }
        return self._realtime[client_id]

    def _safe_send(self, client, message_dict):
        """v1.8: 安全发送 WebSocket 消息(统一异常保护)"""
        try:
            self.server.send_message(client, json.dumps(message_dict))
            return True
        except Exception as e:
            print(f"[WS] 发送失败: {e}")
            return False

    def _handle_realtime_mode(self, client, data):
        """
        [功能说明]处理实时语音模式开启/关闭请求

        [参数说明]
            client: WebSocket 客户端对象
            data (dict): 消息数据,包含 enabled 字段

        [返回值]
            无(通过 WebSocket 发送响应)
        """
        """开启/关闭实时语音对话模式"""
        action = data.get("action", "")
        client_id = client['id']

        if action == "start":
            state = self._get_realtime_state(client_id)
            state["active"] = True
            state["cancel"].clear()
            state["current_gen"] = None
            print(f"[REALTIME] Client {client_id} 开启实时模式")
            self._safe_send(client, {
                "type": "realtime_mode",
                "status": "active"
            })

        elif action == "stop":
            state = self._get_realtime_state(client_id)
            state["active"] = False
            state["cancel"].set()  # 通知停止
            state["current_gen"] = None  # v1.8: 使所有旧 pipeline 失效
            print(f"[REALTIME] Client {client_id} 关闭实时模式")
            self._safe_send(client, {
                "type": "realtime_mode",
                "status": "inactive"
            })

    def _handle_realtime_audio(self, client, data):
        """
        [功能说明]处理实时音频流请求(实时语音对话 Pipeline)

        [参数说明]
            client: WebSocket 客户端对象
            data (dict): 消息数据,包含音频数据

        [返回值]
            无(通过 WebSocket 发送响应)

        [调用时机]
            用户按下录音键开始说话时触发
        """
        """
        接收实时音频流(VAD 检测到用户说完后发送).
        流程:ASR识别 → LLM流式推理 → 逐句TTS → 发送音频片段给前端
        
        v1.8: Generation ID 替代 cancel 竞态窗口 + TTS 异步化
        """
        if not self.app:
            return

        client_id = client['id']
        state = self._get_realtime_state(client_id)

        if not state["active"]:
            return

        # v1.8: 分配新 Generation ID(原子赋值,Python GIL 保证)
        # 所有旧 pipeline 检查到 current_gen != 自己的 gen_id 时自动退出
        gen_id = str(uuid.uuid4())[:8]
        state["current_gen"] = gen_id
        state["speaking"] = False
        state["running"] = True
        state["pipeline_start_time"] = time.time()  # v1.8.4: 记录 pipeline 启动时间（打断保护窗口用）

        # v1.8: 原子化清空 TTS 队列
        tts_queue = state["tts_queue"]
        with tts_queue.mutex:
            tts_queue.queue.clear()

        print(f"[REALTIME] 新 pipeline gen={gen_id}")

        # ASR 开始识别时立即通知前端
        self._safe_send(client, {"type": "realtime_stt_start"})

        import base64
        audio_b64 = data.get("audio", "")
        if not audio_b64:
            return

        audio_bytes = base64.b64decode(audio_b64)
        if len(audio_bytes) < 1000:  # 太短的音频忽略
            return

        # 获取客户端 TTS 配置
        client_engine = self._client_tts_engine.get(client_id, "edge")
        client_voice = self._client_tts_voice.get(client_id, "default")

        # v1.5.1 修复: 如果 engine 是 gptsovits 但 voice 是 'default',
        # 保持当前已加载的音色(避免切换到不存在的 'default' 项目)
        effective_voice = client_voice
        if client_engine == 'gptsovits' and client_voice == 'default':
            if self.app and hasattr(self.app.tts, 'get_available_projects'):
                try:
                    projects = self.app.tts.get_available_projects()
                    trained = [p['name'] for p in projects if p.get('has_trained')]
                    if trained:
                        effective_voice = trained[0]
                        print(f"[REALTIME] voice='default' 回退到 '{effective_voice}'")
                except Exception:
                    pass
            if effective_voice == 'default':
                print("[REALTIME] 警告: gptsovits 无有效音色,使用默认")

        # 在后台线程中处理完整链路
        def realtime_pipeline():
            """
            【功能说明】实时语音聊天流水线,处理ASR识别→LLM对话→TTS合成的完整链路

            【参数说明】无参数(闭包捕获audio_bytes/client/voice/no_split等)

            【返回值】无返回值,流水线完成后重置状态并清理资源
            """
            try:
                # ===== v1.8: 每个关键节点检查 generation =====
                def is_current():
                    """检查当前 pipeline 是否仍是最新 generation"""
                    return state.get("current_gen") == gen_id

                # 1. ASR 识别
                import tempfile
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                        tmp.write(audio_bytes)
                        tmp_path = tmp.name

                    text = ""
                    if not self.app:
                        print("[REALTIME] 错误: self.app 为 None")
                        return
                    if not hasattr(self.app, 'asr'):
                        print("[REALTIME] 错误: self.app 没有 asr 属性")
                        return
                    
                    if self.app.asr.is_available():
                        text = self.app.asr.recognize(tmp_path) or ""
                    else:
                        print("[REALTIME] 警告: ASR 不可用,跳过识别")

                    # Bug B 修复:FunASR CNHuBERT 维度错误时 recognize 返回 None/空,
                    # 此时 fallback 到 faster-whisper(如果有)
                    if not text:
                        try:
                            # v1.8: 加锁保护 fallback 懒加载
                            with self._fallback_whisper_lock:
                                if not hasattr(self, '_fallback_whisper'):
                                    from faster_whisper import WhisperModel
                                    self._fallback_whisper = WhisperModel("base", device="cpu")
                                    print("[ASR] 已切换到 faster-whisper fallback")
                            segments, _ = self._fallback_whisper.transcribe(tmp_path, language="zh")
                            texts = [s.text for s in segments]
                            text = "".join(texts).replace(" ", "")
                        except Exception as e:
                            print(f"[ASR] Fallback whisper 也失败: {e}")

                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        try:
                            os.unlink(tmp_path)
                        except OSError:
                            pass


                # 去空格
                text = text.replace(" ", "").strip()

                # v1.5.9 噪音过滤:检测 ASR 重复词(如 "hellohello", "你好你好")
                if text:
                    import re
                    # 检测前半段==后半段(如 "AB"+"AB" = "ABAB",len=4, half=2, "AB"+"AB")
                    half = len(text) // 2
                    if half >= 2 and len(text) >= 4 and text == text[:half] * 2:
                        # 去掉重复的后半部分
                        text = text[:half]
                        print(f"[STT] 去重: hellohello→{text}")
                    # 单字重复过滤:没有没有没有
                    if re.fullmatch(r'([\u4e00-\u9fff])\1+', text):
                        text = ""
                    # 常见噪音词
                    if text in ['没有', '嗯嗯', '嗯', '啊啊', '呃呃', '呃', '哦哦', '对对', '对对对']:
                        text = ""

                # v1.8.3 P1-3: 增强噪音过滤规则
                if text:
                    # 纯语气词/无意义词组合
                    noise_patterns = [
                        r'^[嗯啊呃哦嘿哈呀哇哎嘿]+$',
                        r'^[对是好的行没错啦]+$',
                        r'^(那|这|然后|就是|那个|这个|所以说|就是说)+$',
                        r'^(什么|怎么|哪|嗯对|呃对|那个那个|这个这个)+$',
                        r'^[\u4e00-\u9fff]{1,2}$',  # 1-2字（太短，大概率是噪音）
                    ]
                    for pat in noise_patterns:
                        if re.fullmatch(pat, text):
                            text = ""
                            break
                    # 重复模式: 同一片段重复3次以上（如"好好好好好"）
                    if text and re.search(r'(.{1,3})\1{2,}', text):
                        # 但保留有意义的重复如"哈哈哈哈哈"→仍为噪音
                        if not re.search(r'[\u4e00-\u9fff]{4,}', text.replace('哈', '').replace('呵', '').replace('嘿', '').replace('嘻', '')):
                            text = ""
                    if text == "":
                        print(f"[REALTIME] 噪音过滤: 文本被过滤为空")
                    else:
                        print(f"[REALTIME] 噪音过滤通过: '{text[:30]}'")

                # v1.8: ASR 后检查 generation
                if not is_current():
                    print("[REALTIME] 在 ASR 后被新请求取代")
                    return

                # [语义判停增强]检测句子是否完整
                if self._is_incomplete_utterance(text):
                    print(f"[REALTIME] 语义判停:句子不完整 '{text[:30]}...',继续等待")
                    self._safe_send(client, {
                        "type": "realtime_stt",
                        "text": text,
                        "complete": False
                    })
                    state["speaking"] = False
                    state["running"] = False
                    return

                if not text:
                    self._safe_send(client, {"type": "realtime_stt", "text": ""})
                    return

                print(f"[REALTIME] 识别: {text[:50]}")
                self._safe_send(client, {"type": "realtime_stt", "text": text})

                # v1.8: LLM 前检查 generation
                if not is_current():
                    print("[REALTIME] 在 LLM 前被新请求取代")
                    return

                # 2. LLM 流式推理 + 逐句 TTS
                state["speaking"] = True  # 标记 AI 正在回复
                
                if not self.app:
                    print("[REALTIME] 错误: self.app 为 None,无法获取 LLM")
                    state["speaking"] = False
                    state["running"] = False
                    return
                
                llm = self.app.llm
                if not llm:
                    print("[REALTIME] 错误: LLM 为 None")
                    state["speaking"] = False
                    state["running"] = False
                    return
                
                has_stream = hasattr(llm, 'stream_chat')
                llm_available = llm.is_available() if hasattr(llm, 'is_available') else True
                
                print(f"[REALTIME] LLM 检查: has_stream={has_stream}, llm.available={llm_available}")

                # no_split: 从客户端保存的偏好读取（随前端 toggleTtsStreaming 实时同步）
                no_split = self._client_tts_no_split.get(client_id, False)
                print(f"[REALTIME] no_split={no_split}")

                if has_stream:
                    try:
                        # v1.5.1 修复: 使用 effective_voice(处理了无效音色回退)
                        realtime_reply = self._realtime_stream_pipeline(client, state, text, llm, client_engine, effective_voice, no_split=no_split, gen_id=gen_id)
                    except Exception as e:
                        print(f"[REALTIME] 流式 Pipeline 错误: {e}")
                        import traceback
                        traceback.print_exc()
                        realtime_reply = None
                else:
                    # 非流式回退(本身就不分句)
                    result = llm.chat(text)
                    reply = result.get("text", "")
                    reply = self._realtime_filter(reply)

                    print(f"[REALTIME] 非流式回复: {reply[:50] if reply else '(空)'}")

                    # v1.5.7 增强: 非流式也要乱码验证
                    if reply and self._is_valid_sentence(reply) and is_current():
                        self._realtime_tts_single(client, state, reply, client_voice, client_engine, gen_id=gen_id)
                    realtime_reply = reply

                # 3. 记忆（独立 try，不影响 TTS/LLM）
                if realtime_reply:
                    try:
                        mem = getattr(self.app, 'memory', None)
                        if mem is not None:
                            mem.add_interaction("user", text)
                            mem.add_interaction("assistant", realtime_reply)
                    except Exception as mem_err:
                        print(f"[REALTIME] 记忆写入错误: {mem_err}")

            except Exception as e:
                print(f"[REALTIME] Pipeline 错误: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # v1.8: 只有当前 generation 才清理状态
                if state.get("current_gen") == gen_id:
                    state["speaking"] = False
                    state["running"] = False

        threading.Thread(target=realtime_pipeline, daemon=True).start()

    def _realtime_stream_pipeline(self, client, state, text, llm, engine, voice, no_split=False, gen_id=None):
        """
        流式 LLM + TTS 流水线.

        v1.8 重构:
        - Generation ID 检查替代 cancel Event 竞态
        - TTS 异步化:独立 worker 线程 + 句子队列,不阻塞 LLM 流接收
        - LLM 输出和 TTS 合成完全并行

        Args:
            no_split: True 时,等 LLM 完全回答完再整段 TTS(不分句),
                      用户在 TTS 设置里开启"整段合成"时生效.
            gen_id: 当前 pipeline 的 Generation ID
        """
        # v1.5.3 调试日志
        print(f"[REALTIME Pipeline] 开始: text='{text[:50]}...' no_split={no_split} gen={gen_id}")
        
        # v2.0: 获取记忆系统用于 RAG 注入
        memory = getattr(self.app, 'memory', None)
        
        sentence_buffer = ""
        cancel = state["cancel"]
        client_id = client['id']

        def is_current():
            """检查当前 pipeline 是否仍是最新 generation"""
            return state.get("current_gen") == gen_id

        # v1.5.9 修复: engine 是字符串(如 "gptsovits"),需要转为真正的 TTS 对象
        tts_engine_obj = self._get_tts_for_client(engine, voice)
        if not tts_engine_obj:
            print(f"[REALTIME] TTS 引擎创建失败 engine={engine} voice={voice}")
            tts_engine_obj = self.app.tts if self.app else None
        else:
            if engine == 'gptsovits' and voice and voice != 'default':
                if hasattr(tts_engine_obj, 'set_project'):
                    tts_engine_obj.set_project(voice)
            print(f"[REALTIME] TTS 引擎就绪: {type(tts_engine_obj).__name__}")

        # ===== v1.8: TTS 异步化 -- 独立 worker 线程 + 句子队列 =====
        from queue import Queue as TTSQueue
        tts_sentence_queue = TTSQueue()
        tts_worker_active = [True]  # 列表包装允许闭包修改
        tts_worker_error = [None]  # 捕获 TTS worker 异常

        def tts_worker():
            """
            【功能说明】异步TTS消费工作线程,从句子队列取出句子执行TTS合成并发送

            【参数说明】无参数(闭包捕获tts_sentence_queue/tts_worker_active等)

            【返回值】无返回值,队列为空或worker停止时结束
            """
            """独立的 TTS 消费线程 -- 不阻塞 LLM 流接收"""
            while tts_worker_active[0] or not tts_sentence_queue.empty():
                try:
                    item = tts_sentence_queue.get(timeout=0.5)
                except Exception:
                    continue  # 队列空,继续等待
                
                item_gen, sentence = item
                
                # 检查 generation -- 旧 pipeline 的句子被丢弃
                if state.get("current_gen") != item_gen:
                    print(f"[TTS Worker] 丢弃过期句子 (gen {item_gen} != {state.get('current_gen')})")
                    tts_sentence_queue.task_done()
                    continue
                
                # 执行 TTS 合成
                try:
                    if not sentence:
                        tts_sentence_queue.task_done()
                        continue
                    print(f"[TTS Worker] 开始合成: {repr(sentence[:30])}")
                    self._tts_do_and_send(client, state, sentence, voice, tts_engine_obj)
                    print(f"[TTS Worker] 完成: {repr(sentence[:30])}")
                except Exception as e:
                    print(f"[TTS Worker] 错误: {e}")
                    tts_worker_error[0] = e
                finally:
                    tts_sentence_queue.task_done()
        
        # 启动 TTS worker(仅分句模式下)
        if not no_split:
            tts_thread = threading.Thread(target=tts_worker, daemon=True)
            tts_thread.start()
            state["tts_worker_active"] = True
            state["tts_sentence_queue"] = tts_sentence_queue

        # no_split 模式下,先收集完整文本,最后再 TTS
        if no_split:
            def on_chunk_no_split(chunk_text):
                """
                【功能说明】无分割模式的流式文本回调,累积完整文本用于整段TTS

                【参数说明】
                    chunk_text (str): LLM流式输出的文本片段

                【返回值】无返回值
                """
                nonlocal sentence_buffer
                if not is_current():
                    return
                chunk_text = self._strip_tool_calls(chunk_text)
                sentence_buffer += chunk_text
                # 发打字机效果给前端
                self._safe_send(client, {
                    "type": "text_chunk",
                    "text": chunk_text
                })

            # v2.0: 传递 memory_system 支持 RAG 注入
            result = llm.stream_chat(text, callback=on_chunk_no_split, chunk_size=5, memory_system=memory)
            full_text = result.get("text", "")
            state["sentence_buffer"] = self._realtime_filter(full_text)

            # 发流结束标记(让前端显示气泡)
            self._safe_send(client, {
                "type": "text_done",
                "text": state["sentence_buffer"],
                "role": "ai"
            })

            # 整段 TTS(取消标点末尾也强制发)
            final_text = self._realtime_filter(sentence_buffer).strip()
            # v1.5.7 增强: no_split 模式也要做乱码验证,防止垃圾文本进 TTS
            if final_text and self._is_valid_sentence(final_text) and is_current():
                try:
                    self._realtime_tts_single(client, state, final_text, voice, tts_engine_obj, gen_id=gen_id)
                except Exception as e:
                    print(f"[REALTIME] No-split TTS 错误: {e}")

            # v1.5.1 修复: no_split 模式也要重置状态
            state["speaking"] = False
            state["running"] = False
            state["cancel"].clear()
            print(f"[REALTIME] Pipeline 完成 (no_split, client {client_id})")
            return state["sentence_buffer"]  # 返回完整回复供记忆写入使用

        # ===== 以下是分句模式(TTS 异步化)=====

        # ===== P1-3: LLM 预判停 =====
        last_sentence_time = time.time()
        chunk_count_since_last_sentence = 0
        last_buffer_len = 0
        # ===== P1-3 结束 =====

        # ===== v1.5 新增: 首句状态 =====
        first_sentence_sent = False
        first_sentence_time = None
        # ===== v1.5 新增结束 =====

        def on_chunk(chunk_text):
            """
            【功能说明】分句模式的流式文本回调,实时检测句子边界并触发TTS合成

            【参数说明】
                chunk_text (str): LLM流式输出的文本片段

            【返回值】无返回值,检测到完整句子时通过queue触发TTS
            """
            nonlocal sentence_buffer, last_sentence_time, chunk_count_since_last_sentence, last_buffer_len
            nonlocal first_sentence_sent, first_sentence_time
            # v1.8: Generation ID 检查(替代 cancel.is_set())
            if not is_current():
                return

            # ===== P1-3: LLM 预判停(检测思考模式) =====
            current_time = time.time()
            chunk_count_since_last_sentence += 1
            # ===== P1-3 结束 =====

            # ===== 关键修复:工具调用文本不能进 TTS =====
            # LLM 流式输出时可能输出 TOOL: xxx ARG: xxx 等格式,
            # 按标点分句后(如 "今天天气怎么?")工具前缀被切掉,
            # 导致单独的句子进入 TTS.
            # 正确做法:在分句前先过滤掉所有工具调用格式.
            chunk_text = self._strip_tool_calls(chunk_text)

            # ===== P2-1: 情感检测 =====
            # 检测当前文本的情感类型,发送给前端用于 Live2D 表情联动
            emotion = self._detect_emotion(chunk_text)
            # ===== P2-1 结束 =====

            # 发送打字机效果给前端(用原始文本,不影响展示)
            self._safe_send(client, {
                "type": "text_chunk",
                "text": chunk_text,
                "emotion": emotion  # P2-1: 附带情感标签
            })

            # 增量分句(v1.5 增强:首句优先策略)
            sentences, sentence_buffer = self._split_sentences_streaming(
                sentence_buffer, chunk_text,
                is_first_sentence=not first_sentence_sent  # 首个句子用激进策略
            )

            # 检测是否有新句子发送
            if sentences:
                last_sentence_time = current_time
                chunk_count_since_last_sentence = 0

                # ===== v1.5 新增: 首句快速发送 =====
                if not first_sentence_sent:
                    first_sentence = sentences[0]
                    valid = self._is_valid_sentence(first_sentence)
                    if valid:
                        first_sentence_sent = True
                        first_sentence_time = current_time
                        print(f"[REALTIME] 首句立即发送: {repr(first_sentence[:40])}")
                        # v1.8: 放入 TTS 队列(不阻塞 LLM 流)
                        tts_sentence_queue.put((gen_id, first_sentence))

                        # 如果还有其他句子(LLM 输出很快时)
                        for sent in sentences[1:]:
                            if not is_current():
                                return
                            valid = self._is_valid_sentence(sent)
                            if not valid:
                                continue
                            tts_sentence_queue.put((gen_id, sent))
                        sentences = []  # 已处理完

                        if first_sentence_time:
                            ttft = (current_time - first_sentence_time) * 1000
                            print(f"[REALTIME] 首句延迟统计: TTFT={ttft:.0f}ms (LLM输出时间)")
                    return  # 首句已发送,等待后续 chunk
                # ===== v1.5 首句策略结束 =====

                print(f"[REALTIME] chunk={repr(chunk_text[:40])} sentences={len(sentences)} buffer_len={len(sentence_buffer)} (新句子) emotion={emotion}")
            else:
                print(f"[REALTIME] chunk={repr(chunk_text[:40])} sentences=0 buffer_len={len(sentence_buffer)}")

            # v1.8: 每积累到一个完整句子就放入 TTS 队列(异步,不阻塞)
            for sent in sentences:
                if not is_current():
                    return
                valid = self._is_valid_sentence(sent)
                print(f"[REALTIME] 句子: {repr(sent[:40])} valid={valid}")
                if not valid:
                    continue
                tts_sentence_queue.put((gen_id, sent))

            # ===== P1-3: LLM 预判停增强 =====
            # 如果满足以下任一条件,强制发送积压的 buffer:
            # 1. buffer 积压超过 60 字符且无标点(v1.5.9 放宽:避免碎片化)
            # 2. LLM 思考超过 2.5 秒且 buffer 有内容(v1.5.9 放宽:给 LLM 更多时间)
            # 3. LLM 输出变慢(多个 chunk buffer 长度没变化)且超过 30 字符
            time_since_last_sentence = current_time - last_sentence_time
            buffer_has_end_punct = sentence_buffer and WebSocketServer._SENTENCE_END.search(sentence_buffer)
            buffer_len = len(sentence_buffer)

            # 条件1: 原有 fallback(放宽到 60,避免碎片化)
            force_send = sentence_buffer and buffer_len >= 60 and not buffer_has_end_punct

            # 条件2: LLM 思考超过 2.5 秒(放宽,减少误触发)
            if time_since_last_sentence > 2.5 and buffer_len >= 25:
                print(f"[REALTIME] P1-3 预判停: 思考 {time_since_last_sentence:.1f}s, buffer={buffer_len}")
                force_send = True

            # 条件3: 输出变慢(连续 3 个 chunk buffer 没增长)
            if chunk_count_since_last_sentence >= 3 and buffer_len == last_buffer_len and buffer_len >= 30 and not buffer_has_end_punct:
                print(f"[REALTIME] P1-3 预判停: 输出变慢 {chunk_count_since_last_sentence} chunks, buffer={buffer_len}")
                force_send = True
            last_buffer_len = buffer_len

            if force_send:
                # v1.5.8 改进: 不再发整个 buffer,而是在最后一个词边界处切分
                split_pos = self._find_last_word_boundary(sentence_buffer, lookback=30)
                part_to_send = sentence_buffer[:split_pos]
                sentence_buffer = sentence_buffer[split_pos:]  # 剩余留到下一轮

                print(f"[REALTIME] Fallback词边界切分: split={split_pos} '{repr(part_to_send[:40])}' remain={len(sentence_buffer)}")

                # v1.5.7 增强: fallback 强制发送前再做一次清理和验证
                cleaned = self._realtime_filter(part_to_send).strip()
                if cleaned and self._is_valid_sentence(cleaned) and is_current():
                    # v1.8: 放入 TTS 队列(异步)
                    tts_sentence_queue.put((gen_id, cleaned))
                # 重置预判停状态
                last_sentence_time = current_time
                chunk_count_since_last_sentence = 0
            # ===== P1-3 结束 =====

        # v2.0: 传递 memory_system 支持 RAG 注入
        result = llm.stream_chat(text, callback=on_chunk, chunk_size=5, memory_system=memory)
        full_text = result.get("text", "")

        # v1.8: LLM 完成后检查 generation
        if not is_current():
            print(f"[REALTIME] LLM 完成但 pipeline 已过期 gen={gen_id}")
            tts_worker_active[0] = False
            return

        # 处理 buffer 中最后一段(可能没有标点结尾)
        raw = self._realtime_filter(sentence_buffer).strip()
        if not raw:
            # 等待 TTS 队列清空再结束
            tts_sentence_queue.join()
            tts_worker_active[0] = False
            state["speaking"] = False
            state["running"] = False
            return self._realtime_filter(full_text) if full_text else ""

        # 有结束标点 → 直接发
        has_end_punct = any(raw.endswith(p) for p in '.!?.!?')
        if has_end_punct:
            if self._is_valid_sentence(raw) and is_current():
                tts_sentence_queue.put((gen_id, raw))
        else:
            # 无结束标点且较长(>=15字)→ 按词边界切分后发
            if len(raw) >= 15:
                split_pos = self._find_last_word_boundary(raw, lookback=50)
                part = raw[:split_pos]
                rest = raw[split_pos:]
                if self._is_valid_sentence(part) and is_current():
                    print(f"[REALTIME] 尾buffer词边界切分: split={split_pos} '{repr(part[:40])}'")
                    tts_sentence_queue.put((gen_id, part))
                # 剩余部分(如果还有且够长)也发
                if rest and self._is_valid_sentence(rest) and is_current():
                    tts_sentence_queue.put((gen_id, rest))
            else:
                # < 15 字且无标点 → 可能是半句话,跳过避免音色割裂
                print(f"[REALTIME] 尾buffer过短/不完整,跳过: '{repr(raw[:30])}'")

        # 保存完整回复用于记忆（作为返回值传给调用方）
        filtered_reply = self._realtime_filter(full_text)
        state["sentence_buffer"] = filtered_reply

        # 发送流结束标记
        self._safe_send(client, {
            "type": "text_done",
            "text": filtered_reply,
            "role": "ai"
        })

        # v1.8: 等待 TTS 队列中所有句子合成完毕
        print(f"[REALTIME] 等待 TTS 队列清空... (gen={gen_id})")
        tts_sentence_queue.join()
        tts_worker_active[0] = False
        state["tts_worker_active"] = False

        if tts_worker_error[0]:
            print(f"[REALTIME] TTS worker 有错误: {tts_worker_error[0]}")

        # v1.5.1 修复: pipeline 完成后重置状态,允许下次请求
        state["speaking"] = False
        state["running"] = False
        print(f"[REALTIME] Pipeline 完成 (client {client_id}, gen={gen_id})")
        return filtered_reply  # 返回完整回复文本供记忆写入使用

    def _realtime_tts_single(self, client, state, sentence, voice, engine, gen_id=None):
        """
        TTS 合成:直接调用,不使用线程池.

        v1.5.3 优化:GPT-SoVITS 是 GPU 密集型任务,多线程并发会竞争 GPU 资源,
        导致实际性能反而下降.改为直接调用,让 GPU 串行处理更稳定.

        v1.8: 支持 gen_id 检查(用于 no_split 模式)
        """
        if not sentence:
            return

        # v1.8: Generation ID 检查
        if gen_id and state.get("current_gen") != gen_id:
            print(f"[REALTIME TTS] 跳过(已过期 gen={gen_id}): {repr(sentence[:30])}")
            return

        cancel = state["cancel"]
        if cancel.is_set():
            print(f"[REALTIME TTS] 跳过(已取消): {repr(sentence[:30])}")
            return

        print(f"[REALTIME TTS] 开始合成: {repr(sentence[:30])}")
        self._tts_do_and_send(client, state, sentence, voice, engine)
        print(f"[REALTIME TTS] 完成: {repr(sentence[:30])}")

    def _tts_do_and_send(self, client, state, sentence, voice, engine):
        """
        同步完成 TTS 合成 + 发送音频给前端.

        v1.5 优化(参照 RealtimeVoiceChat 流式传输):
        - GPT-SoVITS 使用 speak_streaming(),每个 chunk 生成完立即发送
        - 前端收到 chunk 后立即解码播放,不等完整句子
        - 效果:用户能更早听到声音,降低感知延迟  about 300-500ms

        v1.8: on_chunk 中检查 running 状态,支持 Generation ID 过期检测
        """
        cancel = state["cancel"]

        # ===== P2-2: 动态语速调节 =====
        speech_rate = 0
        char_count = len(sentence)
        has_numbers = any(c.isdigit() for c in sentence)
        has_complex_words = any(w in sentence for w in ['首先', '其次', '然后', '但是', '因为', '所以', '如果', '虽然'])
        if char_count > 50 or (has_numbers and char_count > 20) or (has_complex_words and char_count > 30):
            speech_rate = -1
        if char_count > 80:
            speech_rate = -2
        # ===== P2-2 结束 =====

        import numpy as np  # v1.5.4 修复: on_chunk 里用到 np,必须在函数内 import

        try:
            # v1.5.4 修复: voice 是字符串,engine 是 TTS 对象
            # _get_tts_for_client(engine, voice) 需要 (provider_str, voice_name)
            tts_engine = engine  # 直接用传入的 engine 对象,跳过 _get_tts_for_client
            if not tts_engine:
                tts_engine = self.app.tts

            # voice 是字符串(如 'hongkong'),engine 是 TTS 对象
            # 检查 engine 类型来判断是否支持 speak_streaming
            engine_is_gptsovits = (
                hasattr(engine, 'speak_streaming') or
                (hasattr(engine, '__class__') and 'gpt' in engine.__class__.__name__.lower())
            )

            # ===== v1.5: 流式 TTS chunk 传输 =====
            # 检查是否支持流式(GPT-SoVITS 有 speak_streaming)
            supports_streaming = engine_is_gptsovits and hasattr(tts_engine, 'speak_streaming')

            if supports_streaming:
                # 流式模式:每个 chunk 生成完立即发送
                chunk_count = [0]

                def on_chunk(chunk_sr, audio_float, chunk_idx):
                    """
                    【功能说明】实时音频流块回调，处理TTS流式合成的音频块
                    
                    【参数说明】
                        chunk_sr (int): 音频采样率
                        audio_float (np.ndarray): 音频数据（float32数组）
                        chunk_idx (int): 块索引序号
                    """
                    # v1.5.1 修复: 检查 pipeline 是否已失效
                    # 如果 pipeline 已被新请求打断(cancel 被设置或 running 变为 False),
                    # 停止发送音频,避免旧音频被当作新音频播放
                    if cancel.is_set() or not state.get("running", False):
                        return
                    try:
                        import soundfile as sf
                        import base64
                        import io

                        # 转换为 int16 PCM
                        audio_int16 = (audio_float * 32767).astype(np.int16)

                        # 写入 WAV 到内存 buffer
                        buf = io.BytesIO()
                        sf.write(buf, audio_int16, chunk_sr, format='WAV')
                        wav_bytes = buf.getvalue()

                        audio_b64 = base64.b64encode(wav_bytes).decode('ascii')

                        self.server.send_message(client, json.dumps({
                            "type": "realtime_audio_chunk",
                            "audio": audio_b64,
                            "text": sentence,
                            "chunk_idx": chunk_idx,
                            "chunk_count": chunk_idx + 1,
                        }))
                        chunk_count[0] = chunk_idx + 1
                        print(f"[REALTIME STREAM] chunk {chunk_idx}: {len(wav_bytes)} bytes")
                    except Exception as e:
                        print(f"[REALTIME STREAM] chunk {chunk_idx} error: {e}")

                try:
                    final_path = tts_engine.speak_streaming(
                        sentence,
                        project=voice,
                        on_chunk=on_chunk,
                    )

                    if not cancel.is_set():
                        self.server.send_message(client, json.dumps({
                            "type": "realtime_audio_done",
                            "text": sentence,
                            "chunk_total": chunk_count[0],
                        }))

                    print(f"[REALTIME] TTS 流式完成: {sentence[:30]}... ({chunk_count[0]} chunks)")
                    return

                except Exception as stream_err:
                    print(f"[REALTIME] speak_streaming 失败,回退: {stream_err}")

            # ===== 回退:整句合成(原有逻辑)=====
            audio_path = tts_engine.speak(sentence, project=voice)

            if cancel.is_set():
                return

            if not audio_path:
                print(f"[REALTIME] TTS 返回空路径 (sentence={repr(sentence[:20])})")
                audio_path = None
            elif not os.path.exists(audio_path):
                print(f"[REALTIME] TTS 文件不存在: {audio_path}")
                audio_path = None

            if audio_path is None:
                print(f"[REALTIME] TTS pipeline 可能损坏,尝试重建...")
                try:
                    # v1.5.4 修复: 直接用 engine 对象重建,不再调用 _get_tts_for_client
                    # voice 是字符串,engine 是 TTS 对象
                    tts_engine = engine
                    if voice and voice != 'default' and hasattr(tts_engine, 'set_project'):
                        tts_engine.set_project(voice)
                    audio_path = tts_engine.speak(sentence, project=voice)
                except Exception as rebuild_err:
                    print(f"[REALTIME] TTS pipeline 重建失败: {rebuild_err}")
                    audio_path = None

            if audio_path and os.path.exists(audio_path):
                with open(audio_path, 'rb') as f:
                    audio_data = f.read()

                import base64
                audio_b64 = base64.b64encode(audio_data).decode('ascii')
                self.server.send_message(client, json.dumps({
                    "type": "realtime_audio",
                    "audio": audio_b64,
                    "text": sentence
                }))
                print(f"[REALTIME] TTS 发送: {sentence[:30]}... ({len(audio_data)} bytes)")

        except Exception as e:
            print(f"[REALTIME] TTS 错误: {e}")

    def _realtime_streaming_tts(self, client, state, sentence, engine, voice):
        """
        [功能说明]实时流式 TTS 处理

        [参数说明]
            client: WebSocket 客户端对象
            state: 实时对话状态对象
            sentence (str): 要合成的句子
            engine (str): TTS 引擎名称
            voice (str): 音色名称

        [返回值]
            无

        [说明]
            P0-2: 流式 TTS 测试接口(直接发句子,看流式音频效果)
        """
        """
        流式 TTS:逐 chunk 合成、写入文件、立即发送给前端.
        不等完整合成,GPT-SoVITS 每出一个 chunk 就转发给前端.

        P1-2 优化:第一个 chunk 带完整 WAV header,后续 chunk 只带音频数据.
        前端收到后会合并 chunk 后再播放,实现"边合成边播放"效果.
        """
        if not sentence:
            return

        cancel = state["cancel"]

        # 用于累积音频数据,第一个 chunk 之后只累积 PCM 数据
        accumulated_pcm = bytearray()
        first_chunk_sent = False

        def on_chunk(chunk_sr, audio_float, chunk_idx):
            """每个 chunk 合成完毕后的回调(GPT-SoVITS run() 内部触发)"""
            nonlocal accumulated_pcm, first_chunk_sent
            if cancel.is_set():
                raise Exception("canceled")

            # 将 float32 音频数据转为 PCM bytes
            import numpy as np
            audio_int16 = (audio_float * 32767).astype(np.int16)
            pcm_bytes = audio_int16.tobytes()

            # 第一个 chunk:累积到 200ms 音频后再发送(给前端足够的数据播放)
            # 后续 chunk:只累积,等够了再发
            if not first_chunk_sent:
                accumulated_pcm.extend(pcm_bytes)
                # 等待累积到 200ms 音频(采样率 chunk_sr, 16bit = 2字节/样本)
                target_samples = int(chunk_sr * 0.2)  # 200ms
                if len(accumulated_pcm) // 2 >= target_samples:
                    # 第一个 chunk:带完整 WAV header
                    import soundfile as sf
                    from io import BytesIO
                    buf = BytesIO()
                    sf.write(buf, np.array(accumulated_pcm).astype(np.int16), chunk_sr, format='WAV')
                    wav_bytes = buf.getvalue()
                    first_chunk_sent = True
                    accumulated_pcm = bytearray()  # 清空,开始累积后续 chunk
                else:
                    return  # 还没够,继续累积
            else:
                accumulated_pcm.extend(pcm_bytes)
                # 后续 chunk:累积到 200ms 再发送
                target_samples = int(chunk_sr * 0.1)  # 100ms
                if len(accumulated_pcm) // 2 < target_samples:
                    return  # 还没够,继续累积
                # 只发送 PCM 数据(不带 header)
                import base64
                audio_b64 = base64.b64encode(bytes(accumulated_pcm)).decode('ascii')
                accumulated_pcm = bytearray()  # 清空
                self.server.send_message(client, json.dumps({
                    "type": "realtime_audio",
                    "audio": audio_b64,
                    "text": sentence,
                    "chunk_idx": chunk_idx,
                    "streaming": True,
                    "is_pcm_only": True,  # 告诉前端这是纯 PCM 数据
                    "sample_rate": chunk_sr
                }))
                print(f"[REALTIME STREAM] chunk {chunk_idx}: PCM {len(audio_b64)} chars")
                return

            # 发送第一个 chunk(带 WAV header)
            import base64
            audio_b64 = base64.b64encode(wav_bytes).decode('ascii')
            self.server.send_message(client, json.dumps({
                "type": "realtime_audio",
                "audio": audio_b64,
                "text": sentence,
                "chunk_idx": chunk_idx,
                "streaming": True,
                "is_pcm_only": False,
                "sample_rate": chunk_sr
            }))
            print(f"[REALTIME STREAM] chunk {chunk_idx}: WAV {len(wav_bytes)} bytes")

        try:
            tts_engine = self._get_tts_for_client(engine, voice)
            if not tts_engine:
                tts_engine = self.app.tts

            if engine == 'gptsovits' and voice and voice != 'default':
                if hasattr(tts_engine, 'set_project'):
                    tts_engine.set_project(voice)

            # 调用流式合成(不等待完整文件,返回路径供后续使用)
            audio_path = tts_engine.speak_streaming(
                sentence,
                project=voice,
                on_chunk=on_chunk
            )
            # 发送剩余的累积数据
            if accumulated_pcm and not cancel.is_set():
                import numpy as np
                import base64
                audio_b64 = base64.b64encode(bytes(accumulated_pcm)).decode('ascii')
                self.server.send_message(client, json.dumps({
                    "type": "realtime_audio",
                    "audio": audio_b64,
                    "text": sentence,
                    "chunk_idx": -1,
                    "streaming": True,
                    "is_pcm_only": True,
                    "sample_rate": 32000
                }))
            print(f"[REALTIME STREAM] 完成: {audio_path}")

        except Exception as e:
            if "canceled" in str(e):
                print(f"[REALTIME STREAM] 取消: {sentence[:30]}...")
            else:
                print(f"[REALTIME STREAM] 错误: {e}")


        """过滤内部提示词泄露 + 乱码句子过滤(实时版本)"""
        import re
        if "non-text content:" in reply:
            reply = reply.split("non-text content:")[0]
        if "[non-text" in reply:
            reply = reply.split("[non-text")[0]
        if "toolCall" in reply:
            reply = reply.split("toolCall")[0]
        if "tool_result" in reply:
            reply = reply.split("tool_result")[0]
        # 过滤工具调用格式
        reply = re.sub(r'TOOL:\s*\S+\s+ARG:\s*\S+', '', reply, flags=re.IGNORECASE)
        reply = re.sub(r'"tool"\s*:\s*"[^"]*"', '', reply)
        reply = re.sub(r'<tool_call>.*?</tool_call>', '', reply, flags=re.DOTALL)
        reply = re.sub(r'```[\s\S]*?```', '', reply)
        lines = [l for l in reply.split('\n')
                if not any(kw in l for kw in ['我应该', '符合我的人设', '用户只是', '应该用', '简单地', '活泼可爱', '方式回应', 'toolCall', 'tool_result'])]
        reply = '\n'.join(lines)
        # 过滤乱码句子(如 "✨."、"."、全emoji等)
        lines2 = []
        for line in reply.split('\n'):
            line = line.strip()
            if not line:
                continue
            # 统计有效字符(汉字、字母、数字、常用标点)
            valid = sum(1 for c in line if ('\u4e00' <= c <= '\u9fff' or  # 汉字
                                            c.isalnum() or                 # 字母数字
                                            c in ',.!?、;:''""()[]…--~.,!?;:\'\"()[]~-'))
            # 标点/emoji/符号
            total = len(line)
            if valid < total * 0.3 or valid == 0:
                # 整句都是乱码,跳过
                print(f"[REALTIME] 过滤乱码: {repr(line[:30])}")
                continue
            lines2.append(line)
        return '\n'.join(lines2)

    # ===== P2-1: 情感检测 =====
    @staticmethod
    def _detect_emotion(text: str) -> str:
        """
        根据文本内容检测情感类型.
        返回情感标签:happy, sad, angry, surprised, smile, neutral
        """
        if not text:
            return "neutral"

        text_lower = text.lower()

        # 情感关键词映射(与前端的 expressionKeywords 保持一致)
        emotion_keywords = {
            "happy": ["开心", "高兴", "快乐", "好开心", "哈哈", "笑", "太棒", "太好了", "棒", "赞", "爱你", "喜欢", "么么哒", "可爱", "萌", "嘿嘿", "嘻嘻", "开心", "happy"],
            "sad": ["难过", "伤心", "哭", "悲伤", "遗憾", "可惜", "唉", "郁闷", "烦", "讨厌", "sad"],
            "angry": ["生气", "愤怒", "哼", "气死", "可恶", "滚", "烦死了", "angry", "怒"],
            "surprised": ["惊讶", "震惊", "什么", "怎么", "为什么", "啥", "啥情况", "哇", "啊", "surprised", "天哪", "真的假的"],
            "smile": ["微笑", "嗯", "好的", "可以", "行", "没问题", "了解", "知道", "明白", "懂", "是", "对", "smile"],
        }

        # 检测情感
        max_score = 0
        detected = "neutral"
        for emotion, keywords in emotion_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > max_score:
                max_score = score
                detected = emotion

        return detected
    # ===== P2-1 结束 =====

    @staticmethod
    def _is_valid_sentence(text: str) -> bool:
        """
        判断一个句子是否有效(非乱码、无意义).
        返回 True 表示有效,应该送 TTS.
        
        v1.5.3 优化:增加最小字数过滤
        - 超短句(< 4个汉字)音色质量差,容易出现音色不稳定
        - 过滤掉 "看法"、"啦," 等孤立片段
        """
        if not text or not text.strip():
            return False
        text = text.strip()
        # 太短(小于1个汉字或2个字母)→ 无效
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        alpha_chars = sum(1 for c in text if c.isalpha())
        if chinese_chars < 1 and alpha_chars < 2:
            return False
        # v1.5.3 新增: 超短句过滤(< 4个中文字符)
        # 防止 "看法"、"啦,"、"," 等片段产生音色不稳定
        if chinese_chars < 4 and alpha_chars < 8:
            print(f"[REALTIME] 过滤超短句: '{text}' (中文={chinese_chars}字)")
            return False
        # 有效字符比例 < 30% → 乱码
        # v1.5.3 修复: 把 emoji 排除在外,不计入总长度比例
        # emoji 是 Unicode 表情(U+1F000 以上),不是汉字,但也不是乱码
        emoji_chars = sum(1 for c in text if ord(c) > 0x2000)
        effective_len = len(text) - emoji_chars
        if effective_len > 0:
            valid = sum(1 for c in text if ('\u4e00' <= c <= '\u9fff' or
                                              c.isalnum() or
                                              c in ',.!?、;:.,!?;:\'\"()[]~-…--~'))
            if valid < effective_len * 0.3:
                return False
        return True

    @staticmethod
    def _find_last_word_boundary(text: str, lookback: int = 35) -> int:
        """
        [v1.5.8 新增]基于 jieba 分词找最后一个完整词边界.

        问题:fallback 强制发送时,如果只看字符数不看词边界,
              "我准备睡觉了" 会被切在"我准备睡"(后半截"觉了"语义割裂).
        解决:往前 lookback 个字符,在词边界处切分,保证发送的每个片段都语义完整.

        Args:
            text: 要切分的文本
            lookback: 往前回溯的最大字符数(越小越早切,越大越完整)
        Returns:
            切分位置(只发 [0:pos],pos 之后留到下一轮).
            如果找不到合适边界,返回 len(text)(发全部).
        """
        if not text or len(text) < 5:
            return len(text)

        # 如果没有 jieba,回退到找最后一个标点/空格
        if jieba is None:
            # 回退:找最后一个逗号/空格/顿号
            for sep in [',', '、', ',', ' ', ';', ';', '.']:
                pos = text.rfind(sep)
                if pos > 0:
                    return pos + 1
            return len(text)

        # 往前 lookback 范围内找分词边界
        start = max(0, len(text) - lookback)

        # 候选边界集合:标点 + 空格
        punct = set(',.!?、;:.,!?;:"\'()[]()[]{}~~…-----')
        candidates = set()
        for i in range(start, len(text)):
            if text[i] in punct:
                candidates.add(i + 1)  # 标点后一位是边界

        # jieba 分词边界
        try:
            words = jieba.lcut(text)
        except Exception:
            words = []

        cum = 0
        for w in words:
            pos = start + cum + len(w)
            if pos > start:
                candidates.add(pos)
            cum += len(w)

        # 找最后一个候选边界(但不能太靠前,至少保留 start 个字符)
        valid = [c for c in candidates if c > start and c < len(text)]
        if valid:
            return max(valid)

        return len(text)

    @staticmethod
    def _strip_tool_calls(text: str) -> str:
        """
        从 LLM 输出中剥离工具调用格式,防止工具调用文本泄露进 TTS.

        覆盖格式:
        - TOOL: xxx ARG: xxx(OpenClaw 工具调用格式)
        - toolCall / tool_call JSON 格式
        - ```...``` 代码块
        - ##awaiya## 等特殊标记
        """
        if not text:
            return text

        import re
        # OpenClaw 工具调用:TOOL: <name> ARG: <args>
        text = re.sub(r'TOOL:\s*\S+\s+ARG:\s*\S+', '', text, flags=re.IGNORECASE)
        # JSON 工具调用字段
        text = re.sub(r'"tool"\s*:\s*"[^"]*"', '', text)
        text = re.sub(r'"tool_call"\s*:', '', text)
        text = re.sub(r'"function_call"\s*:', '', text)
        # 工具调用的方括号格式
        text = re.sub(r'<tool_call>.*?</tool_call>', '', text, flags=re.DOTALL)
        text = re.sub(r'<tool>.*?</tool>', '', text, flags=re.DOTALL)
        # 工具名称关键字
        for kw in ['openclaw', 'open_claw', 'weather', 'search', 'calculator']:
            text = re.sub(rf'\b{kw}_skill\b', '', text, flags=re.IGNORECASE)
        # 代码块(```...```)整块移除
        text = re.sub(r'```[\s\S]*?```', '', text)
        # 特殊标记
        for tag in ['##awaiya##', '##tool##', '##TOOL##']:
            text = text.replace(tag, '')
        # 清理残留空白
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @staticmethod
    def _realtime_filter(text: str) -> str:
        """
        实时语音文本过滤器:
        1. 剥离工具调用格式(TOOL/ARG/JSON/codeblock等)
        2. 剥离 Markdown 格式(**bold**, *italic*, - 列表, ## 标题等)
        3. 过滤乱码和无意义内容
        4. 清理多余空白
        """
        if not text:
            return text
        # 先剥离工具调用
        text = WebSocketServer._strip_tool_calls(text)
        # v1.5.9 剥离 Markdown 格式(**bold** → text, - 列表项 → 内容)
        import re
        # **text** 或 *text* 或 _text_ → text(去掉加粗/斜体标记)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **bold**
        text = re.sub(r'\*(.+?)\*', r'\1', text)       # *italic*
        text = re.sub(r'_(.+?)_', r'\1', text)         # _italic_
        # ## 标题 → 内容
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # - 列表项开头的短横线(只处理开头的)
        text = re.sub(r'^-\s+', '', text, flags=re.MULTILINE)
        # `code` → code
        text = re.sub(r'`(.+?)`', r'\1', text)
        # 过滤乱码(emoji过多、有效字符<30%、纯标点)
        import re
        # 移除所有 emoji(保留 ~ 喵 等装饰符)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U0001F700-\U0001F77F"  # alchemical symbols
            "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
            "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            "\U0001FA00-\U0001FA6F"  # Chess Symbols
            "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            "\U00002702-\U000027B0"  # Dingbats
            "\U000024C2-\U0001F251"  # enclosed characters
            "]+", flags=re.UNICODE)
        text = emoji_pattern.sub('', text)
        # 清理残留空白
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _handle_diag(self, client, data):
        """
        v1.9.22: 诊断端点 — 返回后端运行状态，帮助排查 GuguGaga.exe 等环境问题
        """
        import sys as _sys
        import os as _os
        result = {
            "type": "diag",
            "python": _sys.executable,
            "python_version": _sys.version,
            "frozen": getattr(_sys, 'frozen', False),
            "cwd": _os.getcwd(),
            "pid": _os.getpid(),
            "modules": {},
            "app_status": {},
        }
        
        # 检查关键模块
        for mod_name in ['torch', 'funasr', 'faster_whisper', 'sounddevice', 'mss', 'psutil', 'rapidocr_onnxruntime', 'yaml', 'websockets', 'numpy']:
            try:
                m = __import__(mod_name)
                ver = getattr(m, '__version__', '?')
                result["modules"][mod_name] = f"OK ({ver})"
            except ImportError as e:
                result["modules"][mod_name] = f"MISSING ({e})"
        
        # 检查 App 模块状态
        if self.app:
            for attr in ['asr', 'tts', 'llm', 'vision', 'memory']:
                mod = getattr(self.app, attr, None)
                result["app_status"][attr] = "loaded" if mod is not None else "not_loaded"
        else:
            result["app_status"] = "app is None"
        
        # sys.path 前10项
        result["sys_path_top10"] = _sys.path[:10]
        
        self.server.send_message(client, json.dumps(result))

    def _handle_realtime_interrupt(self, client, data):
        """
        [功能说明]处理用户打断 AI 说话请求

        [参数说明]
            client: WebSocket 客户端对象
            data (dict): 消息数据

        [返回值]
            无

        [调用时机]
            用户在 AI 说话时按下打断键触发
        """
        client_id = client['id']
        state = self._get_realtime_state(client_id)
        # 只在 AI 正在说话时设置 cancel,避免影响正常的新语音处理
        if state.get("speaking"):
            state["cancel"].set()
            state["speaking"] = False
            print(f"[REALTIME] 用户打断 AI 说话 (client {client_id})")
        else:
            print(f"[REALTIME] 收到打断信号,但 AI 未在说话 (client {client_id})")
        self._safe_send(client, {
            "type": "realtime_interrupt",
            "status": "ok"
        })

    def _handle_realtime_interrupt_fast(self, client, data):
        """
        [全双工增强]快速打断:用户开始说话时立即通知后端
        比普通打断更激进:
        1. 立即取消 LLM 调用
        2. 清空 TTS 队列
        3. 立即响应前端(不等 cancel 处理完)
        
        v1.8: Generation ID 在 _handle_realtime_audio 中更新,
        这里通过 cancel + running 控制快速响应.
        """
        client_id = client['id']
        state = self._get_realtime_state(client_id)

        # v1.8.4: 首回复保护窗口
        # pipeline 启动后 2 秒内，通常是 ASR 识别中 + LLM 思考中，
        # 此时用户没有真正说话（只是环境噪声/呼吸声），不应触发快速打断
        pipeline_start = state.get("pipeline_start_time", 0)
        PROTECTION_WINDOW = 2.0  # 秒
        if pipeline_start and (time.time() - pipeline_start) < PROTECTION_WINDOW:
            print(f"[REALTIME-FAST] 保护窗口内 ({time.time() - pipeline_start:.1f}s < {PROTECTION_WINDOW}s)，忽略打断")
            return
        
        # 立即取消当前 pipeline
        state["cancel"].set()
        state["speaking"] = False
        state["running"] = False  # 标记 pipeline 不在运行
        
        # v1.8: 原子化清空 TTS 队列
        tts_queue = state["tts_queue"]
        with tts_queue.mutex:
            tts_queue.queue.clear()
        # 也清空异步句子队列
        if state.get("tts_sentence_queue"):
            sq = state["tts_sentence_queue"]
            with sq.mutex:
                sq.queue.clear()
        
        print(f"[REALTIME-FAST] 快速打断 (client {client_id})")
        
        # 立即响应前端,让前端知道打断已被处理
        self._safe_send(client, {
            "type": "realtime_interrupt_fast_ack",
            "status": "ok"
        })

    def _is_incomplete_utterance(self, text: str) -> bool:
        """
        [语义判停增强]检测句子是否完整
        参考豆包"短停顿继续倾听"机制:
        - 如果句子不完整(只有半句话),返回 True,继续等待更多输入
        - 如果句子完整(有完整谓语),返回 False,触发 LLM
        """
        if not text:
            return True
        
        # 检查是否有结束标点(有标点通常是完整的句子)
        ending_punctuations = ['.', '?', '!', '.', '?', '!']
        if any(text.endswith(p) for p in ending_punctuations):
            return False  # 有结束标点,句子完整
        
        # 没有结束标点时,检查句子完整性
        
        # 短句白名单:这些是完整的短表达,VAD已判定说完,直接送LLM
        complete_short = [
            '你好', '好的', '好的呀', '好的吧', '好的呢',
            '嗯嗯', '嗯', '是啊', '对的', '没错',
            '可以', '好吧', '行', '行吧', '行呀',
            '喵', '喵~', '喵~', '嘿嘿', '哈哈', '哈哈哈',
            '知道了', '了解', '明白', '谢谢', '谢谢啊',
            '没事', '没关系', '不好意思', '打扰了',
            '再见', '拜拜', '晚安', '早安',
            '稍等', '等一下', '等会', '马上',
            '请问', '你好呀', '你好啊',
        ]
        if text in complete_short:
            return False
        
        # 太短的句子(< 4字)且不在白名单:可能不完整
        if len(text) < 4:
            return True
        
        # 不完整模式1:特定不完整开头
        incomplete_patterns = [
            r'^我[想说要觉知]',  # 我想/我要/我觉(未说完)
            r'^我[的]?$',        # 只有"我"
            r'^[对对嗯啊呃那个这个嘛哈]+$',  # 只有语气词
            r'^[要不要是不是算](?![\u4e00-\u9fa5]+)',  # 疑问词/连词开头
            r'^[那这](?![\u4e00-\u9fa5]+[是为在有说想做的呢啊呀])',  # 指示词后无动词
        ]
        for pattern in incomplete_patterns:
            if re.match(pattern, text):
                return True
        
        # 不完整模式2:只有连词或前置词
        leading_connectors = ['因为', '虽然', '如果', '但是', '所以', '然后', '而且', '或者']
        for conn in leading_connectors:
            if text.startswith(conn):
                rest = text[len(conn):]
                if len(rest) < 5 or not any(p in rest for p in ending_punctuations):
                    return True
        
        # 不完整模式3:括号未闭合
        if text.count('(') > text.count(')') or text.count('(') > text.count(')'):
            return True
        
        # 不完整模式4:有从句连接词但句子没结束(常见于 VAD 早停)
        incomplete_subordinates = [
            '但是', '不过', '然而', '虽然', '因为', '所以', '如果', '要是',
            '就算', '即使', '哪怕', '只要', '只有', '除非'
        ]
        for sub in incomplete_subordinates:
            if sub in text and not any(text.endswith(p) for p in ending_punctuations):
                return True
        
        return False  # 默认认为句子完整
