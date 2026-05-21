"""
Live2D Web 渲染组件

基于 QWebEngineView + oh-my-live2d + pixi.js v7 实现 Live2D 模型渲染，
替代原有的 live2d-py + QOpenGLWidget 方案。

核心思路:
  WebUI 和桌面宠物模式都使用 oh-my-live2d + pixi.js v7 在浏览器中渲染 Live2D，
  效果完美（透明背景、正确的鼠标跟踪、稳定的渲染）。
  本组件将同一技术栈嵌入到原生桌面应用的 QWebEngineView 中，
  彻底解决 QOpenGLWidget 方案的白色背景和眼神跟踪问题。

架构:
  ┌──────────────────────────────────────┐
  │  Live2DWebWidget (QWidget)           │
  │  ┌────────────────────────────────┐  │
  │  │  QWebEngineView                │  │
  │  │  ┌──────────────────────────┐  │  │
  │  │  │  oh-my-live2d + pixi.js  │  │  │
  │  │  │  (WebGL 渲染 Live2D)     │  │  │
  │  │  └──────────────────────────┘  │  │
  │  └────────────────────────────────┘  │
  │  ↕ QWebChannel (Python ↔ JS 通信)   │
  │  ↕ Local HTTP Server (模型文件服务)  │
  └──────────────────────────────────────┘

特性:
- 透明背景（深色主题下无白色底色）
- 鼠标跟踪由 oh-my-live2d 自动处理
- 表情切换、动作播放、口型同步
- 模型热切换
- 完全离线可用（JS 库使用本地文件 libs/pixi.min.js + libs/oh-my-live2d.min.js）
- 无需 WASM 文件路径 hack（v6 的 document.currentScript patch 确保 Emscripten 能正确解析脚本目录）
- 与 WebUI 使用完全相同的 JS 库和版本，保证兼容性

兼容性:
- 与原 Live2DWidget 完全相同的 API（signals、methods、attributes）
- chat_page.py、desktop_pet.py、animation_controller.py 无需修改

v5 修复说明 (WASM 路径解析失败 → CubismCore 初始化失败):
- ★ 核心根因：QWebEngineView 中 document.currentScript 为 null（deferred script 限制）
- oh-my-live2d 内部的 Emscripten 模块用 document.currentScript.src 确定脚本目录(nr)
- nr 为空 → WASM 路径变成 _em_module.wasm（缺少 libs/ 前缀）→ fetch 404
- WASM 加载失败 → g.asm 为 null → 所有 CubismCore 方法失败 → 模型无法创建
- 修复：HTTP 服务器将根路径的 _em_module.wasm 请求重定向到 libs/_em_module.wasm
- 不再预配置 window.Live2DCubismCore（v4 教训：会阻断内置 CubismCore 初始化）
- 使用 setTimeout(2500) 等待模型就绪（与 index.html 一致）
- 简化守护定时器（与 index.html 一致，只检测 slide-out）

v14 修复说明 (canvas 0x0 → 模型无法加载):
- ★ 核心根因：stageStyle: { height: 480 } 让 oh-my-live2d 创建固定高度的 stage，
  与 CSS #oml2d-stage 的 height: 100% !important 冲突
- oh-my-live2d 在创建 stage 时会用 inline style 设置 height:480px，
  而 PixiJS 的 resizeTo: stage.element 机制依赖 stage 的实际尺寸来调整 canvas
- CSS !important 覆盖了 inline height，但 PixiJS 内部可能仍读取 inline 值
- 最终 canvas 的 offsetWidth/offsetHeight 始终为 0，模型无法渲染
- 修复：移除 stageStyle: { height: 480 } 参数（让 stage 完全由 CSS 控制尺寸）
- 修复：改进 ready-check 逻辑，不仅检查 canvas 尺寸，也检查 pixiApp.model 是否就绪
- 修复：在 loadOml2d 返回后主动设置 stage 的 inline style 尺寸为 100%，
  确保 PixiJS 的 resizeTo 机制能正确计算 canvas 尺寸

v18 修复说明 (竞态条件 + stage transform 双重修复):

修复 A — _on_page_loaded 与 resizeEvent 竞态条件 → 模型永不加载:
- ★ 核心根因：Live2DWidget 初始化时，若 widget 尺寸过小 (< 50x50)，
  load_model() 设置 _waiting_for_resize=True。随后 resizeEvent 可能先触发
  （此时 _js_ready=False → 跳过模型加载），_on_page_loaded 后触发
  （此时 _waiting_for_resize=True → 也跳过加载）。
  两条路径都被阻塞，模型永远不会开始加载，用户看到"正在加载 Live2D..."永久停留。
- 修复：_on_page_loaded 在 _waiting_for_resize=True 时，主动检查 widget
  尺寸是否已就绪（≥ 50x50），若就绪则立即清除 _waiting_for_resize 并加载模型。
  打破 resizeEvent 与 _on_page_loaded 之间的等待循环。

修复 B — stage translateY(130%) + _loadState 不触发 → 模型加载完成但未报告就绪:
- ★ 核心根因（3个）:
  1. oh-my-live2d 默认 translateY(130%) 将 stage 推到容器下方不可见，
     _forceStageVisible 只检查 translateX 遗漏 translateY
  2. _forceStageVisible 过早重置 stage.style.animation='none'，打断了 slideIn 动画
  3. _loadState='loaded' 只在 events.add("load") 中设置，但 oh-my-live2d v0.19.3
     的 "load" 事件未触发，导致 ready-check 永远等不到 loaded 状态
- 修复：(1) _forceStageVisible 不再重置 animation（只修 position/size）
  (2) stageSlideIn 回调中同时设置 _loadState='loaded'（可靠的备选信号）
  (3) ready-check 条件放宽为 (hasModel && hasDimensions) || _loadState==='loaded'
  (4) 6秒安全网兜底

v17 修复说明 (javaScriptConsoleMessage 签名错误 → 所有 JS 日志丢失):
- ★ 核心根因：PySide6 QWebEnginePage.javaScriptConsoleMessage 的签名为
  (self, level, message, lineNumber, sourceID)，共 5 个参数。
  v16 错误地将签名改为 4 参数 (self, level, message, source)，移除了 lineNumber。
  导致 TypeError: takes 4 positional arguments but 5 were given，
  所有 JS 控制台消息都无法捕获——这也是 v16 无法看到任何 oh-my-live2d
  加载诊断日志的根本原因。
- 修复：恢复 lineNumber 参数到正确位置 (message 和 source 之间)
- 修复：日志输出增加行号信息 (L{lineNumber})

v16 修复说明 (models.model=undefined → 模型永远"正在加载"):
- ★ 核心根因：CSS animation-name: none !important 阻止了 oh-my-live2d 的
  slideOut/slideIn CSS 动画。slideOut 时 stage 被 translateX(-100%) 移出，
  然后 slideIn 应该把它移回来，但因为 animation 被禁用，slideIn 的动画不执行，
  stage 停在 translateX(-100%) 位置（不可见）。
- 同时，oh-my-live2d 的 loadModel() 流程依赖 slideIn 的 animationend 事件
  来判断动画完成。animation 被禁用后，虽然 setTimeout 仍会 resolve Promise，
  但 stage 的视觉位置不会恢复。
- 修复：不再用 animation-name: none !important 禁止动画
- 修复：监听 oh-my-live2d 的 events（"load" success/fail）检测模型加载状态
- 修复：ready-check 超时时不再误报成功（models.model=undefined 时报告失败）
- 修复：添加模型重载机制（加载失败或超时后自动重试）
- 修复：_forceStageVisible() 在模型加载后强制修复 stage 位置
- 修复：不再隐藏 statusBar（让加载错误信息可见）

"""

import os
import json
import logging
import threading
import http.server
import socketserver
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QColor

_logger = logging.getLogger('Live2DWeb')

# QWebEngineView 是可选依赖
# 注意：此模块应该延迟导入（通过 live2d_widget.py 的工厂函数），
# 因为 PySide6.QtWebEngineWidgets 的导入会触发 Chromium 初始化，
# 而 Chromium 需要 QCoreApplication.arguments()，
# 必须在 QApplication 创建之后才能导入此模块。
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtCore import QObject, Slot
    WEBENGINE_AVAILABLE = True
except ImportError:
    QWebEngineView = None
    QWebEnginePage = None
    QWebEngineSettings = None
    QWebChannel = None
    WEBENGINE_AVAILABLE = False

# 项目根目录
from app.shared_config import PROJECT_DIR

# 静态文件根目录（包含 libs/ 和 assets/）
_STATIC_DIR = os.path.join(PROJECT_DIR, "app", "web", "static")


# ============ 本地 HTTP 服务器 ============

class _StaticFileServer:
    """本地静态文件 HTTP 服务器，为 QWebEngineView 提供模型文件和 JS 库"""

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get(cls):
        """获取单例实例（懒启动）"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._server = None
        self._thread = None
        self._port = None
        self._start()

    def _start(self):
        """启动 HTTP 服务器"""
        if not os.path.isdir(_STATIC_DIR):
            _logger.info(f"静态文件目录不存在: {_STATIC_DIR}")
            return

        try:
            root_dir = _STATIC_DIR

            class Handler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=root_dir, **kwargs)

                def log_message(self, format, *args):
                    pass  # 抑制日志

                def do_GET(self):
                    """处理 GET 请求

                    ★ v5 修复：当 QWebEngineView 中 document.currentScript 为 null 时，
                    oh-my-live2d 内部的 Emscripten 模块会将 WASM 路径解析为
                    _em_module.wasm（相对于页面根目录），而非正确的 libs/_em_module.wasm。
                    这是因为 Emscripten 用 document.currentScript.src 来确定脚本目录，
                    而 QWebEngineView 对 deferred script 不设置 document.currentScript。

                    修复：当请求根路径的 _em_module.wasm 时，重定向到 libs/ 下。
                    """
                    if self.path == '/_em_module.wasm':
                        # 重定向到正确路径
                        self.path = '/libs/_em_module.wasm'
                    super().do_GET()

                def end_headers(self):
                    # 允许所有来源访问（本地服务器，无安全风险）
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Cache-Control", "no-cache")
                    # WASM 需要正确的 Content-Type
                    # 注意：SimpleHTTPRequestHandler 通过 mimetypes.guess_type() 已经
                    # 设置了 Content-Type，Python 3.11+ 对 .wasm 返回 application/wasm
                    # 所以这里不需要重复设置，否则会导致重复 Content-Type header，
                    # 可能导致 WebAssembly.instantiateStreaming() 失败
                    super().end_headers()

            socketserver.TCPServer.allow_reuse_address = True
            # port=0 让系统自动分配可用端口
            self._server = socketserver.TCPServer(("", 0), Handler)
            self._port = self._server.server_address[1]

            self._thread = threading.Thread(
                target=self._server.serve_forever,
                daemon=True,
                name="live2d-static-server"
            )
            self._thread.start()

            _logger.info(f"静态文件服务器已启动: http://localhost:{self._port}")
        except Exception as e:
            _logger.info(f"启动静态文件服务器失败: {e}")
            self._port = None

    @property
    def port(self):
        return self._port

    @property
    def base_url(self):
        if self._port:
            return f"http://localhost:{self._port}"
        return None

    def model_path_to_url(self, model_path: str) -> str:
        """将本地模型路径转换为 loadOml2d 可用的路径

        loadOml2d 的 path 参数需要相对于当前页面（baseUrl）的路径，
        与 WebUI 中 './assets/model/hiyori/Hiyori.model3.json' 格式一致。

        Args:
            model_path: 本地绝对路径，如 C:\\...\\app\\web\\static\\assets\\model\\hiyori\\Hiyori.model3.json

        Returns:
            相对路径，如 ./assets/model/hiyori/Hiyori.model3.json
        """
        # 尝试将模型路径转为相对于 static 目录的路径
        model_path = model_path.replace("\\", "/")
        static_dir = _STATIC_DIR.replace("\\", "/")

        if model_path.startswith(static_dir):
            relative = model_path[len(static_dir):].lstrip("/")
            return "./" + relative

        # 模型不在 static 目录下 → 尝试在 static 目录中查找同名文件
        model_name = os.path.basename(model_path)
        model_dir = os.path.basename(os.path.dirname(model_path))

        # 在 assets/model/ 下搜索
        assets_model_dir = os.path.join(_STATIC_DIR, "assets", "model")
        if os.path.isdir(assets_model_dir):
            for sub_dir in os.listdir(assets_model_dir):
                candidate = os.path.join(assets_model_dir, sub_dir, model_name)
                if os.path.exists(candidate):
                    return f"./assets/model/{sub_dir}/{model_name}"

        # 最后尝试直接使用文件名
        return f"./assets/model/{model_dir}/{model_name}"

    def shutdown(self):
        """关闭服务器"""
        if self._server:
            try:
                self._server.shutdown()
            except Exception:
                pass
            self._server = None
            self._port = None


# ============ JS Bridge（QWebChannel 通信） ============

if WEBENGINE_AVAILABLE:
    class _JSBridge(QObject):
        """Python ↔ JavaScript 通信桥"""

        # JS → Python 信号
        model_loaded_signal = Signal(str)      # 模型名称
        expressions_signal = Signal(str)       # 表情列表 (JSON)
        motions_signal = Signal(str)           # 动作列表 (JSON)
        model_error_signal = Signal(str)       # 加载错误

        @Slot(str)
        def onModelLoaded(self, model_name: str):
            """JS 通知：模型加载完成"""
            self.model_loaded_signal.emit(model_name)

        @Slot(str)
        def onExpressionsReady(self, expressions_json: str):
            """JS 通知：表情列表就绪"""
            self.expressions_signal.emit(expressions_json)

        @Slot(str)
        def onMotionsReady(self, motions_json: str):
            """JS 通知：动作列表就绪"""
            self.motions_signal.emit(motions_json)

        @Slot(str)
        def onModelLoadError(self, error_msg: str):
            """JS 通知：模型加载失败"""
            self.model_error_signal.emit(error_msg)


# ============ Live2D HTML 模板 ============

def _generate_live2d_html() -> str:
    """v22: 从模板文件读取 HTML（与 WebUI 完全相同逻辑）。

    模板路径: app/web/static/_live2d_template.html
    读取失败时返回 error 页面（含 console.error 便于诊断）。
    """
    import os
    template = os.path.join(PROJECT_DIR, 'app', 'web', 'static', '_live2d_template.html')
    if os.path.exists(template):
        with open(template, 'r', encoding='utf-8') as f:
            html = f.read()
        _logger.info(f"Live2D 模板已加载: {template} ({len(html)} bytes)")
        return html
    _logger.info(f"Live2D 模板不存在: {template}")
    return '<html><body><script>console.error("Live2D template missing: _live2d_template.html")</script></body></html>'

class _Live2DWebPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, source):
        level_names = {0: "INFO", 1: "WARN", 2: "ERROR"}
        level_name = level_names.get(level, "LOG")
        # v17: 记录 [Live2D] 相关消息、所有 ERROR/WARN、以及 oh-my-live2d 相关消息
        if ("[Live2D]" in message or level_name in ("ERROR", "WARN") or
            "oml2d" in message.lower() or "cubism" in message.lower() or
            "live2d" in message.lower() or "pixi" in message.lower()):
            _logger.info(f"[JS {level_name}] L{lineNumber}: {message}")


# ============ 主组件 ============

# ★ QWebEngine 全局配置函数
# 必须在 QApplication 创建之后调用，否则会触发
# "QCoreApplication::arguments: Please instantiate the QApplication object first" 错误，
# 因为 QWebEngineProfile.defaultProfile() 会初始化 Chromium 的 base::CommandLine。
_webengine_configured = False

def _configure_webengine():
    """配置 QWebEngine 全局设置（启用 GPU 加速和 WebGL）。
    必须在 QApplication 实例创建后调用，否则 Chromium 初始化会失败。"""
    global _webengine_configured
    if _webengine_configured:
        return
    from PySide6.QtWebEngineCore import QWebEngineProfile

    # ★ 设置 Chromium 命令行参数（如果还没设置的话）
    # 确保 GPU 加速和 WebGL 可用
    import os
    existing_flags = os.environ.get('QTWEBENGINE_CHROMIUM_FLAGS', '')
    required_flags = [
        '--enable-gpu-rasterization',
        '--ignore-gpu-blocklist',
        '--disable-software-rasterizer',
    ]
    for flag in required_flags:
        if flag not in existing_flags:
            existing_flags += ' ' + flag
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = existing_flags.strip()

    profile = QWebEngineProfile.defaultProfile()
    # 允许 WebGL
    profile.settings().setAttribute(
        QWebEngineSettings.WebAttribute.WebGLEnabled, True)
    # 允许加速的 2D canvas
    profile.settings().setAttribute(
        QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
    # 允许本地内容访问远程 URL（模型文件加载需要）
    profile.settings().setAttribute(
        QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
    # 允许本地内容访问文件 URL
    profile.settings().setAttribute(
        QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
    _webengine_configured = True

class Live2DWidget(QWidget):
    """Live2D Web 渲染组件

    基于 QWebEngineView + pixi.js + pixi-live2d，与 WebUI/桌面宠物相同的技术栈。
    完全替代 live2d-py + QOpenGLWidget 方案，彻底解决白色背景和眼神跟踪问题。

    API 与原 Live2DWidget 完全兼容，chat_page.py / desktop_pet.py 无需修改。
    """

    # 信号：模型加载完成
    model_loaded = Signal(str)  # 模型名称
    # 信号：表情列表更新
    expressions_updated = Signal(list)  # 表情ID列表
    # 信号：动作分组更新
    motions_updated = Signal(list)  # 动作分组列表

    def __init__(self, parent=None):
        super().__init__(parent)

        # ★ 配置 QWebEngine 全局设置（必须在 QApplication 创建后调用）
        _configure_webengine()

        self.model = None  # 兼容属性（非 None 表示模型已加载）
        self.model_path = None
        self._model_name = ""
        self._js_ready = False
        self._pending_model_url = None  # JS 未就绪时暂存模型 URL
        self._waiting_for_resize = False  # v15: widget 尺寸未就绪时延迟加载

        # 布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ★ 使用自定义 QWebEnginePage（转发 JS 控制台消息）
        self._web_page = _Live2DWebPage(self)
        self._web_view = QWebEngineView(self)
        self._web_view.setPage(self._web_page)

        # ★ 启用 WebGL（Live2D 需要 WebGL 渲染）
        settings = self._web_page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)

        # 透明背景
        self._web_page.setBackgroundColor(QColor(0, 0, 0, 0))

        # QWebChannel 通信
        self._channel = QWebChannel()
        self._bridge = _JSBridge()
        self._channel.registerObject("pybridge", self._bridge)
        self._web_page.setWebChannel(self._channel)

        # 连接桥信号
        self._bridge.model_loaded_signal.connect(self._on_model_loaded_js)
        self._bridge.expressions_signal.connect(self._on_expressions_js)
        self._bridge.motions_signal.connect(self._on_motions_js)
        self._bridge.model_error_signal.connect(self._on_model_error_js)

        layout.addWidget(self._web_view)

        # 获取静态文件服务器
        self._server = _StaticFileServer.get()

        # 加载页面
        self._load_page()

        self.setMinimumSize(380, 480)
        self.setMouseTracking(True)

    def _load_page(self):
        """加载 Live2D 渲染页面

        关键：必须使用 setUrl() 而不是 setHtml() 加载页面。
        QWebEngineView 的 setHtml() 对 oh-my-live2d 的 Cubism WASM 初始化
        存在兼容性问题（CubismFramework.startUp()/initialize() 不会触发），
        而 setUrl() 正常工作。因此将 HTML 写入静态文件目录，
        通过本地 HTTP 服务器用 setUrl() 加载。

        v12: 缓存 HTML 文件，避免每次创建 Live2DWidget 时重复写入
        """
        base_url = self._server.base_url
        if not base_url:
            self._show_placeholder("静态文件服务器未启动")
            return

        # v11: 只在文件不存在或版本变更时才写入 HTML
        html_path = os.path.join(_STATIC_DIR, "live2d_widget.html")
        html = _generate_live2d_html()

        # 检查是否需要重新写入（文件不存在或内容变化）
        _need_write = True
        if os.path.exists(html_path):
            try:
                with open(html_path, "r", encoding="utf-8") as f:
                    existing = f.read()
                if existing == html:
                    _need_write = False
            except OSError:
                pass

        if _need_write:
            try:
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html)
            except OSError as e:
                _logger.info(f"写入 HTML 文件失败: {e}")
                return

        # v18: 添加时间戳参数避免 QWebEngineView 缓存旧版本 HTML
        import time as _time
        url = QUrl(f"{base_url}/live2d_widget.html?_t={int(_time.time())}")
        self._web_view.setUrl(url)

        # 监听页面加载完成
        self._web_view.loadFinished.connect(self._on_page_loaded)

    def _on_page_loaded(self, ok: bool):
        """页面加载完成回调

        v18 FIX: 修复 _on_page_loaded 与 resizeEvent 之间的竞态条件。
        当 load_model() 时 widget 尺寸过小（< 50x50），会设置 _waiting_for_resize=True。
        若 resizeEvent 先于 _on_page_loaded 触发（此时 _js_ready=False 被跳过），
        而 _on_page_loaded 又因为 _waiting_for_resize=True 跳过加载，
        将导致模型永远不会开始加载，Live2D 永久卡在"正在加载..."状态。

        修复：在 _on_page_loaded 中，若 _waiting_for_resize=True 且 widget 尺寸已就绪，
        立即加载模型。
        """
        if ok:
            _logger.info(f"页面加载完成, widget size={self.width()}x{self.height()}")
            self._js_ready = True
            # 如果有待加载的模型
            if self._pending_model_url:
                if getattr(self, '_waiting_for_resize', False):
                    # v18: resizeEvent 可能先触发但 _js_ready=False 被跳过，
                    # 现在页面加载完成，检查 widget 尺寸是否已就绪
                    if self.width() >= 50 and self.height() >= 50:
                        self._waiting_for_resize = False
                        url = self._pending_model_url
                        self._pending_model_url = None
                        _logger.info(f"页面加载完成且尺寸就绪，加载暂存模型: {url}")
                        self._load_model_js(url)
                    else:
                        _logger.info(f"页面加载完成但尺寸仍过小({self.width()}x{self.height()})，等待 resize")
                else:
                    url = self._pending_model_url
                    self._pending_model_url = None
                    _logger.info(f"加载暂存模型: {url}")
                    self._load_model_js(url)
        else:
            print("[Live2DWeb] 页面加载失败，1 秒后重试")
            # 重试
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1000, self._load_page)

    def _load_model_js(self, model_url: str):
        """通过 JS 加载模型"""
        js_code = f"if(window.loadModelFromUrl)window.loadModelFromUrl('{model_url}')"
        self._web_page.runJavaScript(js_code)

    def _show_placeholder(self, message: str):
        """显示占位提示"""
        layout = self.layout()
        placeholder = QLabel(f"Live2D\n\n{message}")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 14px;
                background: transparent;
            }
        """)
        layout.addWidget(placeholder)

    def load_model(self, model_path: str):
        """加载 Live2D 模型

        Args:
            model_path: .model3.json 文件的绝对路径

        Returns:
            bool: True 表示加载请求已发送
        """
        if not os.path.exists(model_path):
            _logger.info(f"模型文件不存在: {model_path}")
            return False

        self.model_path = model_path

        # 将本地路径转换为相对路径（和 WebUI 一致：./assets/model/...）
        model_url = self._server.model_path_to_url(model_path)
        if not model_url:
            _logger.info(f"无法生成模型路径: {model_path}")
            return False

        _logger.info(f"加载模型: path={model_path}")
        _logger.info(f"模型URL: {model_url}")
        _logger.info(f"服务器: {self._server.base_url}, JS就绪: {self._js_ready}, widget={self.width()}x{self.height()}")

        # v15 FIX: 如果 widget 尺寸太小，延迟加载模型
        # QWebEngineView 在首次显示时可能尚未获得正确尺寸，
        # 导致 CSS height:100vh 解析为 0，canvas 为 0x0
        if self.width() < 50 or self.height() < 50:
            _logger.info(f"Widget 尺寸过小 ({self.width()}x{self.height()})，延迟加载模型")
            if not self._pending_model_url:
                self._pending_model_url = model_url
                # 安装 resizeEvent 延迟加载
                self._waiting_for_resize = True
            return True

        if self._js_ready:
            self._load_model_js(model_url)
        else:
            # JS 未就绪，暂存 URL
            self._pending_model_url = model_url
            _logger.info(f"JS 未就绪，暂存模型 URL")

        return True

    def resizeEvent(self, event):
        """v15 FIX: 监听尺寸变化，在 widget 获得正确尺寸后加载暂存的模型"""
        super().resizeEvent(event)
        if getattr(self, '_waiting_for_resize', False) and self._pending_model_url:
            if self.width() >= 50 and self.height() >= 50:
                self._waiting_for_resize = False
                url = self._pending_model_url
                _logger.info(f"Widget 尺寸就绪 ({self.width()}x{self.height()})，加载暂存模型")
                if self._js_ready:
                    self._pending_model_url = None
                    self._load_model_js(url)

    # ========== JS → Python 回调 ==========

    def _on_model_loaded_js(self, model_name: str):
        """JS 通知模型加载完成"""
        self.model = True  # 非 None 表示已加载
        self._model_name = model_name
        self.model_loaded.emit(model_name)
        _logger.info(f"模型加载成功: {model_name}")

    def _on_expressions_js(self, expressions_json: str):
        """JS 通知表情列表就绪"""
        try:
            expressions = json.loads(expressions_json)
        except (json.JSONDecodeError, TypeError):
            expressions = []
        self.expressions_updated.emit(expressions)

    def _on_motions_js(self, motions_json: str):
        """JS 通知动作列表就绪"""
        try:
            motions = json.loads(motions_json)
        except (json.JSONDecodeError, TypeError):
            motions = []
        self.motions_updated.emit(motions)

    def _on_model_error_js(self, error_msg: str):
        """JS 通知模型加载失败"""
        _logger.info(f"模型加载失败: {error_msg}")
        self.model = None

    # ========== 表情/动作控制 ==========

    def set_expression(self, name: str):
        """设置表情"""
        self._web_page.runJavaScript(
            f"if(window.setExpression)window.setExpression({json.dumps(name)})"
        )

    def start_motion(self, group: str, index: int = 0, priority=None):
        """播放指定动作"""
        self._web_page.runJavaScript(
            f"if(window.startMotion)window.startMotion({json.dumps(group)},{index})"
        )

    def start_random_motion(self, group: str = "TapBody", priority=None):
        """随机播放动作"""
        self._web_page.runJavaScript(
            f"if(window.startRandomMotion)window.startRandomMotion({json.dumps(group)})"
        )

    # ========== 口型同步 ==========

    def set_mouth_open(self, value: float):
        """设置口型开合度（TTS 口型同步）

        Args:
            value: 0.0~1.0
        """
        clamped = max(0.0, min(1.0, value))
        self._web_page.runJavaScript(
            f"if(window.setMouthOpen)window.setMouthOpen({clamped:.2f})"
        )

    # ========== 空闲动作 ==========

    def start_idle(self):
        """启动空闲动作"""
        self.start_random_motion("Idle")

    # ========== 自适应帧率（兼容接口，Web 自动管理帧率） ==========

    def set_fps(self, fps: int):
        """设置渲染帧率（Web 模式下自动管理，此方法为兼容接口）"""
        pass

