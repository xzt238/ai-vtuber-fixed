"""
HTTP 静态文件处理器

支持静态文件服务、音频文件访问、训练音频上传等功能。
"""

import http.server
import json
import os
import logging
import mimetypes
from pathlib import Path

logger = logging.getLogger(__name__)

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

    def __init__(self, *args, directory=None, **kwargs) -> None:
        """初始化静态文件处理器"""
        self._static_dir = directory
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, fmt, *args) -> None:
        """静默日志(不输出请求日志)"""
        pass  # 静默日志

    def end_headers(self) -> None:
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

    def do_GET(self) -> None:
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
            except Exception as e:
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
                candidates.append(Path(cache_dir) / filename)
            if self._static_dir:
                candidates.append(Path(self._static_dir) / "audio", filename)
            for fpath in candidates:
                if Path(fpath).exists():
                    try:
                        with open(fpath, "rb") as f:
                            data = f.read()
                        self.send_response(200)
                        self.send_header("Content-Type", "audio/wav")
                        self.send_header("Content-Length", str(len(data)))
                        self.send_header("Cache-Control", "no-cache")
                        self.end_headers()
                        self.wfile.write(data)
                    except Exception as e:
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

        # KI-001 FIX: 动态生成 config.js，从 shared_config.py 单一数据源
        # 前端通过 <script src="/api/config.js"> 加载，彻底消除 JS-Python 手动同步
        if self.path.startswith("/api/config.js"):
            self._serve_config_js()
            return

        # 其他请求走默认处理
        super().do_GET()
    
    def do_POST(self) -> None:
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
            from app.version import VERSION
            self.send_json({"status": "ok", "version": VERSION})
            return

        # 其他请求返回 405 Method Not Allowed
        self.send_error(405, "Method Not Allowed")
    
    def _handle_sandbox_api(self) -> None:
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
            logger.error(f"API错误: {e}")
            import traceback
            traceback.print_exc()
            self.send_json({"success": False, "error": "操作失败，请查看服务端日志"})
    
    def _handle_train_upload(self) -> None:
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
                logger.info(f"[TRAIN] 创建项目配置: {project_name}/config.json")
            
            logger.info(f"上传成功: {project_name}/{filename} ({len(audio_data)} bytes)")
            self.send_json({
                "success": True,
                "filename": filename,
                "path": str(audio_path),
                "size": len(audio_data)
            })
            
        except Exception as e:
            logger.error(f"上传失败: {e}")
            import traceback
            traceback.print_exc()
            self.send_json({"success": False, "error": "操作失败，请查看服务端日志"})

    def _serve_config_js(self) -> None:
        """KI-001 FIX: 动态生成 config.js，从 shared_config.py 单一数据源

        前端通过 <script src="/api/config.js"> 加载此文件，
        消除 index.html 中 JS 配置与 Python shared_config.py 的手动同步问题。
        每次页面加载时自动获取最新的 Python 端配置数据。
        """
        from app.shared_config import PROVIDER_CONFIG, EDGE_VOICES, EXPRESSION_KEYWORDS, EXPRESSION_MAP

        js_code = f"""// Auto-generated from app/shared_config.py — DO NOT EDIT MANUALLY
// KI-001: 此文件由服务器动态生成，修改配置请编辑 app/shared_config.py

const _providerConfig = {json.dumps(PROVIDER_CONFIG, ensure_ascii=False, indent=2)};

const voiceOptions = {{
    edge: {json.dumps([{{"label": v[1], "value": v[0]}} for v in EDGE_VOICES], ensure_ascii=False)}
}};

const expressionKeywords = {json.dumps(EXPRESSION_KEYWORDS, ensure_ascii=False)};
const expressionMap = {json.dumps(EXPRESSION_MAP, ensure_ascii=False)};
"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/javascript')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(js_code.encode('utf-8'))

    def _handle_layout_api(self) -> None:
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

        layout_file = _Path(cache_dir) / "layout.json"

        # GET: 读取布局数据
        if self.command == "GET":
            try:
                if _Path(layout_file).exists():
                    with open(layout_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self.send_json({"success": True, "data": data})
                else:
                    self.send_json({"success": True, "data": None})
            except json.JSONDecodeError:
                self.send_json({"success": True, "data": None})
            except Exception as e:
                self.send_json({"success": False, "error": "操作失败，请查看服务端日志"})
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
                except Exception as e:
                    # 清理临时文件
                    try:
                        _os.unlink(tmp_path)
                    except OSError:
                        pass
                    raise

                logger.info(f"已保存布局到 {layout_file}")
                self.send_json({"success": True})
            except json.JSONDecodeError as e:
                self.send_json({"success": False, "error": "JSON 解析失败"})
            except Exception as e:
                logger.error(f"保存布局失败: {e}")
                self.send_json({"success": False, "error": "操作失败，请查看服务端日志"})
            return

        # 其他方法
        self.send_error(405, "Method Not Allowed")

    def _handle_sandbox_status(self) -> None:
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
            logger.error(f"状态错误: {e}")
            self.send_json({"success": False, "error": "操作失败，请查看服务端日志"})
    
    def send_json(self, data) -> None:
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
        # v1.12.0 AUDIT-3-3: CORS 收紧 — 限制为 localhost
        self.send_header("Access-Control-Allow-Origin", "http://localhost:12393")
        self.end_headers()
        self.wfile.write(response)


# =============================================================================
# Web 服务器
# =============================================================================
