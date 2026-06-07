"""
HTTP Web 服务器

提供静态文件服务和 TTS 预热功能。
"""

import os
import threading
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 延迟导入
try:
    from tts import TTSFactory
except ImportError:
    TTSFactory = None

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
        # KI-002 FIX: 默认端口从 shared_config 统一读取
        try:
            from app.shared_config import HTTP_PORT as _DEFAULT_HTTP_PORT
        except ImportError:
            _DEFAULT_HTTP_PORT = 12393
        self.port = web_config.get("port", _DEFAULT_HTTP_PORT)
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
        logger.info(f"Audio cache dir: {cache_dir}")

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


        logger.info(f"HTTP server started: http://localhost:{self.port}")
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
                        logger.debug(f"{voice_name} 无参考音频,跳过预热")
                        return
                warm_text = "你好."
                path = tts.speak(warm_text)
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except OSError:
                        pass
                    logger.info(f"预热完成: {voice_name}")
                else:
                    logger.warning(f"{voice_name} 预热返回空(不影响使用)")
            except Exception as e:
                logger.error(f"{voice_name} 预热失败: {e}")

        def do_prewarm():
            """后台预热主逻辑（串行，避免并发推理冲突）"""
            try:
                if not self._app or not self._app.tts:
                    return
                tts = self._app.tts

                # 1. 先预热默认音色
                logger.info("预热默认音色...")
                prewarm_single_voice("default", tts)

                # 2. 只预热上次使用的音色（而非全部已训练音色）
                #    全部预热会导致启动时加载 mansui 等不常用的音色，浪费时间
                #    上次使用的音色保存在 app/cache/last_tts_project.json
                last_project = None
                if hasattr(tts, '_load_last_project'):
                    last_project = tts._load_last_project()

                if last_project and hasattr(tts, 'set_project'):
                    logger.info(f"预热上次使用的音色: {last_project}")
                    tts.set_project(last_project)
                    prewarm_single_voice(last_project, tts)
                elif hasattr(tts, 'get_available_projects'):
                    # 没有记录上次音色 → 预热第一个已训练音色
                    try:
                        projects = tts.get_available_projects()
                        trained = [p['name'] for p in projects if p.get('has_trained')]
                        if trained:
                            first = trained[0]
                            logger.info(f"无上次记录，预热首个已训练音色: {first}")
                            tts.set_project(first)
                            prewarm_single_voice(first, tts)
                    except Exception as proj_err:
                        logger.error(f"获取音色列表失败: {proj_err}")

            except Exception as e:
                logger.warning(f"预热失败(不影响使用): {e}")

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
