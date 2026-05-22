"""
VRM 3D 模型渲染组件

基于 QWebEngineView + three.js + three-vrm 实现 VRM 3D 模型渲染，
与 Live2DWidget API 兼容，支持在 Live2D/VRM 之间无缝切换。

架构:
  ┌──────────────────────────────────────┐
  │  VRMWidget (QWidget)                 │
  │  ┌────────────────────────────────┐  │
  │  │  QWebEngineView                │  │
  │  │  ┌──────────────────────────┐  │  │
  │  │  │  three.js + three-vrm    │  │  │
  │  │  │  (WebGL 渲染 VRM 3D)     │  │  │
  │  │  └──────────────────────────┘  │  │
  │  └────────────────────────────────┘  │
  │  ↕ QWebChannel (Python ↔ JS 通信)   │
  │  ↕ Local HTTP Server (模型文件服务)  │
  └──────────────────────────────────────┘

与 AnimationController 兼容:
  - model 属性 (True/None = 已加载/未加载)
  - set_mouth_open(value) — 口型同步
  - set_expression(name, value=1.0) — 表情设置
"""

import os
import logging
import threading
import http.server
import socketserver

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QColor

_logger = logging.getLogger('VRM')

# QWebEngineView 是可选依赖
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

from app.shared_config import PROJECT_DIR

# 静态文件根目录（包含 vrm_template.html 和 .vrm 模型文件）
_STATIC_DIR = os.path.join(PROJECT_DIR, "app", "web", "static")


# ============ 本地 HTTP 服务器 ============

class _VRMStaticServer:
    """本地静态文件 HTTP 服务器，为 QWebEngineView 提供 HTML 和 .vrm 文件"""

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

                def end_headers(self):
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Cache-Control", "no-cache")
                    super().end_headers()

            socketserver.TCPServer.allow_reuse_address = True
            self._server = socketserver.TCPServer(("", 0), Handler)
            self._port = self._server.server_address[1]

            self._thread = threading.Thread(
                target=self._server.serve_forever,
                daemon=True,
                name="vrm-static-server"
            )
            self._thread.start()

            _logger.info(f"VRM 静态文件服务器已启动: http://localhost:{self._port}")
        except Exception as e:
            _logger.info(f"启动 VRM 静态文件服务器失败: {e}")
            self._port = None

    @property
    def port(self) -> int:
        return self._port

    @property
    def base_url(self) -> str:
        if self._port:
            return f"http://localhost:{self._port}"
        return None

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
    class _VRMBridge(QObject):
        """Python ↔ JavaScript 通信桥"""

        model_loaded_signal = Signal(str)      # 模型名称

        @Slot(str)
        def onModelLoaded(self, model_name: str):
            """JS 通知：模型加载完成"""
            self.model_loaded_signal.emit(model_name)


# ============ VRM HTML 模板 ============

_VRM_TEMPLATE = r'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
*{margin:0;padding:0}html,body{overflow:hidden;background:transparent}
canvas{display:block}
#msg{color:rgba(255,255,255,0.4);font-family:sans-serif;text-align:center;padding-top:40px}
</style>
<script src="https://cdn.jsdelivr.net/npm/three@0.150.1/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.150.1/examples/js/loaders/GLTFLoader.js"></script>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
</head>
<body>
<div id="msg">Loading VRM...</div>
<script>
// three-vrm CDN (global build — compatible with QWebEngineView)
var _vrmReady = false;
var script = document.createElement('script');
script.src = 'https://cdn.jsdelivr.net/npm/@pixiv/three-vrm@1/lib/three-vrm.min.js';
script.onload = function() { _vrmReady = true; onReady(); };
script.onerror = function() { 
  document.getElementById('msg').textContent = 'VRM SDK load failed';
  // fallback: try v0
  var s2 = document.createElement('script');
  s2.src = 'https://cdn.jsdelivr.net/npm/@pixiv/three-vrm@0.6.10/lib/three-vrm.js';
  s2.onload = function() { _vrmReady = true; onReady(); };
  s2.onerror = function() { document.getElementById('msg').textContent = 'VRM SDK unavailable'; };
  document.head.appendChild(s2);
};
document.head.appendChild(script);

// QWebChannel
var pybridge = null;
try {
  new QWebChannel(qt.webChannelTransport, function(c) { pybridge = c.objects.pybridge; });
} catch(e) {}

// Three.js setup (global THREE from CDN)
var renderer, scene, camera, currentVrm, lastTime = Date.now();

function init3D() {
  renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setClearColor(0x000000, 0);
  document.body.appendChild(renderer.domElement);

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(30, 1, 0.1, 20);
  camera.position.set(0, 1.3, 3);

  scene.add(new THREE.DirectionalLight(0xffffff, 2));
  scene.add(new THREE.AmbientLight(0xffffff, 1));

  resize();
  window.addEventListener('resize', resize);
  animate();
}

function resize() {
  var w = window.innerWidth || 640;
  var h = window.innerHeight || 480;
  if (renderer) { renderer.setSize(w, h); }
  if (camera) { camera.aspect = w / Math.max(h, 1); camera.updateProjectionMatrix(); }
}

function onReady() {
  if (!_vrmReady || !window.THREE) return;
  init3D();
  document.getElementById('msg').style.display = 'none';
  // Auto-load if URL set
  if (window._pendingUrl) loadVRM(window._pendingUrl);
}

// Load VRM
function loadVRM(url) {
  if (!_vrmReady || !THREE) { window._pendingUrl = url; return; }
  if (!THREE.VRM || !THREE.VRM.VRMLoaderPlugin) { setTimeout(function(){ loadVRM(url); }, 500); return; }
  
  var loader = new THREE.GLTFLoader();
  loader.crossOrigin = 'anonymous';
  var plugin = new THREE.VRM.VRMLoaderPlugin();
  THREE.GLTFLoader.register(function(parser) { return plugin; });
  
  loader.load(url, function(gltf) {
    currentVrm = gltf.userData.vrm;
    if (currentVrm && currentVrm.scene) {
      scene.add(currentVrm.scene);
      document.getElementById('msg').style.display = 'none';
      if (pybridge) pybridge.onModelLoaded('vrm_model');
    }
  }, undefined, function(err) {
    document.getElementById('msg').textContent = 'VRM load error: ' + (err.message || err);
  });
}

function animate() {
  requestAnimationFrame(animate);
  var now = Date.now();
  var delta = now - lastTime;
  lastTime = now;
  if (currentVrm && currentVrm.update) currentVrm.update(delta);
  if (renderer && scene && camera) renderer.render(scene, camera);
}

// API
window.loadVRM = loadVRM;
window.setMouthOpen = function(v) {
  if (currentVrm && currentVrm.expressionManager) currentVrm.expressionManager.setValue('aa', v);
};
window.setExpression = function(name, v) {
  if (currentVrm && currentVrm.expressionManager) currentVrm.expressionManager.setValue(name, v||1);
};
</script>
</body>
</html>'''


# ============ 主组件 ============

class VRMWidget(QWidget):
    """VRM 3D 模型渲染组件

    基于 QWebEngineView + three.js + three-vrm，与 Live2DWidget API 兼容。

    Signals:
        model_loaded(str): 模型加载完成，参数为模型名称
    """

    model_loaded = Signal(str)

    def __init__(self, parent=None):
        """初始化 VRM 渲染组件

        Args:
            parent: 父级 QWidget
        """
        super().__init__(parent)

        if not WEBENGINE_AVAILABLE:
            _logger.error("QWebEngine 不可用，VRMWidget 无法正常工作")
            self.setMinimumSize(380, 480)
            return

        # ---- 模型状态 ----
        self.model = None        # True = 已加载，None = 未加载
        self.model_path = None   # .vrm 文件路径
        self._model_name = ""    # 模型名称（用于信号）

        # 布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # QWebEngineView
        self._web_page = QWebEnginePage(self)
        self._web_view = QWebEngineView(self)
        self._web_view.setPage(self._web_page)

        # WebGL 启用
        settings = self._web_page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)

        # 透明背景
        self._web_page.setBackgroundColor(QColor(0, 0, 0, 0))

        # QWebChannel 通信
        self._channel = QWebChannel()
        self._bridge = _VRMBridge()
        self._channel.registerObject("pybridge", self._bridge)
        self._web_page.setWebChannel(self._channel)

        # 连接桥信号
        self._bridge.model_loaded_signal.connect(self._on_model_loaded)

        layout.addWidget(self._web_view)

        # 获取静态文件服务器
        self._server = _VRMStaticServer.get()

        # 加载页面
        self._load_page()

        self.setMinimumSize(380, 480)

    def _load_page(self):
        """加载 VRM 渲染页面"""
        base_url = self._server.base_url
        if not base_url:
            self._show_placeholder("静态文件服务器未启动")
            return

        # 写入 HTML 模板到静态文件目录
        html_path = os.path.join(_STATIC_DIR, "vrm_widget.html")
        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(_VRM_TEMPLATE)
        except OSError as e:
            _logger.info(f"写入 VRM HTML 失败: {e}")
            return

        # 加载页面（带时间戳避免缓存）
        import time as _time
        url = QUrl(f"{base_url}/vrm_widget.html?_t={int(_time.time())}")
        self._web_view.setUrl(url)

    def _show_placeholder(self, message: str):
        """显示占位提示"""
        layout = self.layout()
        if layout:
            placeholder = QLabel(f"VRM\n\n{message}")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("""
                QLabel {
                    color: #888;
                    font-size: 14px;
                    background: transparent;
                }
            """)
            layout.addWidget(placeholder)

    # ========== JS → Python 回调 ==========

    def _on_model_loaded(self, model_name: str):
        """JS 通知模型加载完成"""
        self.model = True
        self._model_name = model_name
        self.model_loaded.emit(model_name)
        _logger.info(f"VRM 模型加载成功: {model_name}")

    # ========== Public API — 模型管理 ==========

    def load_model(self, path: str) -> bool:
        """加载 VRM 模型

        Args:
            path: .vrm 文件的绝对路径

        Returns:
            bool: True 表示加载请求已发送
        """
        if not os.path.exists(path):
            _logger.info(f"VRM 模型文件不存在: {path}")
            return False

        self.model_path = path
        self.model = None  # 重置加载状态

        # 将绝对路径转换为相对 URL
        path_norm = path.replace("\\", "/")
        static_norm = _STATIC_DIR.replace("\\", "/")

        if path_norm.startswith(static_norm):
            rel = path_norm[len(static_norm):].lstrip("/")
            model_url = "./" + rel
        else:
            # 模型不在 static 目录下，尝试直接使用路径
            model_url = path

        _logger.info(f"VRM 加载模型: path={path}, url={model_url}")

        js_code = f"if(window.loadVRM)window.loadVRM('{model_url}')"
        self._web_page.runJavaScript(js_code)
        return True

    # ========== Public API — 口型同步 ==========

    def set_mouth_open(self, value: float):
        """设置口型开合度（TTS 口型同步）

        Args:
            value: 0.0（闭合）~ 1.0（完全张开）
        """
        clamped = max(0.0, min(1.0, float(value)))
        js_code = f"if(window.setMouthOpen)window.setMouthOpen({clamped:.2f})"
        self._web_page.runJavaScript(js_code)

    # ========== Public API — 表情控制 ==========

    def set_expression(self, name: str, value: float = 1.0):
        """设置表情

        VRM 使用 expressionManager.setValue(name, value) 控制表情权重。

        Args:
            name: 表情名称（如 'happy', 'angry', 'sad', 'surprised', 'aa' 等）
            value: 表情权重 0.0~1.0（默认 1.0）
        """
        clamped = max(0.0, min(1.0, float(value)))
        js_code = (
            f"if(window.setExpression)"
            f"window.setExpression('{name}',{clamped:.2f})"
        )
        self._web_page.runJavaScript(js_code)
