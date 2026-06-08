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
from PySide6.QtCore import Qt, Signal, QUrl, QTimer
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
    def get(cls) -> None:
        """获取单例实例（懒启动）"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        """内部方法"""
        self._server = None
        self._thread = None
        self._port = None
        self._start()

    def _start(self) -> None:
        """启动 HTTP 服务器"""
        if not os.path.isdir(_STATIC_DIR):
            _logger.info(f"静态文件目录不存在: {_STATIC_DIR}")
            return

        try:
            root_dir = _STATIC_DIR

            class Handler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs) -> None:
                    """内部方法"""
                    super().__init__(*args, directory=root_dir, **kwargs)

                def log_message(self, format, *args) -> None:
                    """Log message"""
                    pass  # 抑制日志

                def end_headers(self) -> None:
                    """End headers"""
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
        """Port"""
        return self._port

    @property
    def base_url(self) -> str:
        """Base url"""
        if self._port:
            return f"http://localhost:{self._port}"
        return None

    def shutdown(self) -> None:
        """关闭服务器"""
        if self._server:
            try:
                self._server.shutdown()
            except Exception as e:
                pass
            self._server = None
            self._port = None


# ============ JS Bridge（QWebChannel 通信） ============

if WEBENGINE_AVAILABLE:
    class _VRMBridge(QObject):
        """Python ↔ JavaScript 通信桥"""

        model_loaded_signal = Signal(str)      # 模型名称
        page_ready_signal = Signal()           # 页面就绪（init3D 完成）
        model_error_signal = Signal(str)       # 模型加载错误

        @Slot(str)
        def onModelLoaded(self, model_name: str) -> None:
            """JS 通知：模型加载完成"""
            self.model_loaded_signal.emit(model_name)

        @Slot()
        def onPageReady(self) -> None:
            """JS 通知：Three.js 初始化完成"""
            self.page_ready_signal.emit()

        @Slot(str)
        def onModelError(self, msg: str) -> None:
            """JS 通知：模型加载失败"""
            self.model_error_signal.emit(msg)


# ============ VRM HTML 模板 ============

_VRM_TEMPLATE = r'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
*{margin:0;padding:0}html,body{overflow:hidden;background:transparent}
canvas{display:block}
#msg{color:rgba(255,255,255,0.4);font-family:sans-serif;text-align:center;padding-top:40px}
#error{color:rgba(255,100,100,0.8);font-family:monospace;font-size:11px;text-align:center;padding:10px;display:none}
</style>
<script src="./three.min.js"></script>
<script src="./GLTFLoader.js"></script>
<script src="./three-vrm.js"></script>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
</head>
<body>
<div id="msg">Loading VRM...</div>
<div id="error"></div>
<script>
// ---- 全局状态 ----
var pybridge = null;       // QWebChannel bridge
var _pendingUrl = null;    // 待加载的模型 URL
var _initDone = false;     // init3D 是否完成
var _bridgeConnected = false;  // QWebChannel 是否已连接
var renderer, scene, camera, currentVrm, lastTime = Date.now();
var _keyLight, _breathTime = 0;
window._vrmState = {
  spherical: null,
  orbitTarget: new THREE.Vector3(0, 1, 0)
};
// 动画可调参数（全局配置，setAnimXxx 修改）
window._vrmAnimConfig = {
  speed: 1.0,       // 速度倍率
  amplitude: 1.0,   // 幅度倍率
  headTilt: 0.0,    // 头部倾斜偏移
  breathAmp: 0.015  // 呼吸幅度
};

// ---- 工具函数 ----

function showError(msg) {
  var el = document.getElementById('error');
  el.textContent = msg;
  el.style.display = 'block';
  console.error('[VRM]', msg);
  if (pybridge && pybridge.onModelError) pybridge.onModelError(msg);
}

function trySignalReady() {
  // 两边都就绪后通知 Python
  if (_initDone && _bridgeConnected && pybridge && pybridge.onPageReady) {
    pybridge.onPageReady();
  }
}

function tryLoadPending() {
  // 两边都就绪 + 有待加载模型时触发
  if (_initDone && _pendingUrl && THREE && THREE.GLTFLoader) {
    _doLoadVRM(_pendingUrl);
  }
}

// ---- 依赖检查 ----

(function() {
  if (typeof THREE === 'undefined') { showError('THREE: not loaded'); }
  else if (typeof THREE.GLTFLoader === 'undefined') { showError('GLTFLoader: not loaded'); }
  else if (typeof THREE.VRM === 'undefined') { showError('THREE.VRM: not loaded'); }
})();

// ---- QWebChannel ----

try {
  new QWebChannel(qt.webChannelTransport, function(c) {
    pybridge = c.objects.pybridge;
    _bridgeConnected = true;
    console.log('[VRM] QWebChannel connected');
    trySignalReady();
    tryLoadPending();
  });
} catch(e) {
  console.error('[VRM] QWebChannel failed:', e);
  // 即使没有 bridge，也标记为已连接（降级模式，无回调）
  _bridgeConnected = true;
}

// ---- Three.js 初始化 ----

function init3D() {
  try {
    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    renderer.setClearColor(0x000000, 0);
    document.body.appendChild(renderer.domElement);

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(30, 1, 0.05, 50);
    camera.position.set(0, 1.3, 3);

    // 多光源：半球光（天空+地面）+ 正面主光 + 背面补光
    scene.add(new THREE.HemisphereLight(0xffeedd, 0x443322, 1.2));
    _keyLight = new THREE.DirectionalLight(0xffffff, 2.5);
    _keyLight.position.set(0, 1.8, 3);
    scene.add(_keyLight);
    var _fillLight = new THREE.DirectionalLight(0x6666aa, 1.0);
    _fillLight.position.set(-1, 0.8, -2);
    scene.add(_fillLight);
    scene.add(new THREE.AmbientLight(0x444444, 0.8));

    _breathTime = 0;

    forceResize();
    window.addEventListener('resize', forceResize);

    // 鼠标拖拽旋转（绕模型中心 Y 轴 + X 轴）
    var _dragging = false, _lastX = 0, _lastY = 0;
    var _orbitTarget = window._vrmState.orbitTarget;
    var _spherical = new THREE.Spherical().setFromVector3(
      camera.position.clone().sub(_orbitTarget)
    );
    window._vrmState.spherical = _spherical;
    renderer.domElement.addEventListener('pointerdown', function(e) {
      _dragging = true; _lastX = e.clientX; _lastY = e.clientY;
    });
    window.addEventListener('pointermove', function(e) {
      if (!_dragging) return;
      var dx = e.clientX - _lastX, dy = e.clientY - _lastY;
      _lastX = e.clientX; _lastY = e.clientY;
      _spherical.theta -= dx * 0.005;
      _spherical.phi   -= dy * 0.005;
      _spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, _spherical.phi));
      camera.position.copy(_orbitTarget).add(
        new THREE.Vector3().setFromSpherical(_spherical)
      );
      camera.lookAt(_orbitTarget);
    });
    window.addEventListener('pointerup', function() { _dragging = false; });

    // 滚轮缩放
    renderer.domElement.addEventListener('wheel', function(e) {
      e.preventDefault();
      _spherical.radius *= 1 + e.deltaY * 0.001;
      _spherical.radius = Math.max(0.5, Math.min(10, _spherical.radius));
      camera.position.copy(_orbitTarget).add(
        new THREE.Vector3().setFromSpherical(_spherical)
      );
      camera.lookAt(_orbitTarget);
    }, { passive: false });

    animate();

    _initDone = true;
    document.getElementById('msg').style.display = 'none';
    document.getElementById('error').style.display = 'none';
    console.log('[VRM] init3D complete, canvas=', renderer.domElement.width, 'x', renderer.domElement.height);

    trySignalReady();
    tryLoadPending();
  } catch(e) {
    showError('init3D error: ' + e.message);
  }
}

function forceResize() {
  var w = window.innerWidth;
  var h = window.innerHeight;
  if (!w || !h || w < 10 || h < 10) {
    w = renderer && renderer.domElement.parentElement ? renderer.domElement.parentElement.offsetWidth : 380;
    h = renderer && renderer.domElement.parentElement ? renderer.domElement.parentElement.offsetHeight : 480;
  }
  if (w < 10 || h < 10) return;
  if (renderer) { renderer.setSize(w, h); }
  if (camera) { camera.aspect = w / h; camera.updateProjectionMatrix(); }
  console.log('[VRM] resize:', w, 'x', h);
}

// ---- VRM 加载 ----

function _unloadVRM() {
  // 从场景移除旧模型及其所有子对象
  if (currentVrm && currentVrm.scene) {
    scene.remove(currentVrm.scene);
  }
  currentVrm = null;
}

function _doLoadVRM(url) {
  _unloadVRM();  // 先卸载旧模型
  // URL 和 loading 状态...
  _pendingUrl = null;
  document.getElementById('error').style.display = 'none';
  document.getElementById('msg').textContent = 'Loading model...';
  document.getElementById('msg').style.display = 'block';

  var loader = new THREE.GLTFLoader();
  loader.crossOrigin = 'anonymous';

  loader.load(url,
    function(gltf) {
      // ★ 抢救原始 glTF 材质贴图（three-vrm 的 VRM_USE_GLTFSHADER 会丢失贴图）
      var texMap = {};  // mesh_name → {map, emissiveMap, ...}
      gltf.scene.traverse(function(node) {
        if (node.isMesh && node.material) {
          var mat = Array.isArray(node.material) ? node.material[0] : node.material;
          var tex = {};
          if (mat.map) tex.map = mat.map;
          if (mat.emissiveMap) tex.emissive = mat.emissiveMap;
          if (mat.normalMap) tex.normal = mat.normalMap;
          if (Object.keys(tex).length > 0) texMap[node.name] = tex;
        }
      });
      console.log('[VRM] Original glTF textured meshes:', Object.keys(texMap).length, Object.keys(texMap).slice(0,5));

      THREE.VRM.from(gltf).then(function(vrm) {
        currentVrm = vrm;
        scene.add(vrm.scene);

        // 把抢救的贴图装回 VRM 材质
        var fixedTex = 0, fixedColor = 0;
        vrm.scene.traverse(function(node) {
          if (node.isMesh) {
            node.frustumCulled = false;
            if (node.material) {
              var mats = Array.isArray(node.material) ? node.material : [node.material];
              mats.forEach(function(m) {
                // 1) 尝试从 texMap 恢复贴图
                var saved = texMap[node.name];
                if (saved && saved.map) {
                  m.map = saved.map;
                  if (m.uniforms && m.uniforms._MainTex) m.uniforms._MainTex.value = saved.map;
                  fixedTex++;
                }
                // 2) 检查是否仍无贴图 → 给肉色
                var hasTex = !!(m.map) || !!(m.uniforms && m.uniforms._MainTex && m.uniforms._MainTex.value);
                if (!hasTex) {
                  if (m.uniforms && m.uniforms._Color) {
                    m.uniforms._Color.value.set(0.95, 0.8, 0.7);
                  } else if (m.color) {
                    m.color.set(0xf5ccbb);
                  }
                  fixedColor++;
                }
                m.needsUpdate = true;
              });
            }
          }
        });
        console.log('[VRM] Fixed textures:', fixedTex, '| Fixed colors:', fixedColor);

        // 放大模型使其可见（如果太小）
        var box = new THREE.Box3().setFromObject(vrm.scene);
        var size = box.getSize(new THREE.Vector3());
        console.log('[VRM] Bounding box size:', size.x.toFixed(2), size.y.toFixed(2), size.z.toFixed(2));
        if (size.y < 0.5) {
          var s = 2.0;
          vrm.scene.scale.set(s, s, s);
          console.log('[VRM] Scaled up by', s);
        }

        // 修复 T-pose：上臂 Z 轴旋转使手臂自然下垂（不用 X 轴，避免内翻）
        if (currentVrm.humanoid && currentVrm.humanoid.getBoneNode) {
          var lArm = currentVrm.humanoid.getBoneNode('leftUpperArm');
          if (lArm) lArm.rotation.z = 1.0;
          var rArm = currentVrm.humanoid.getBoneNode('rightUpperArm');
          if (rArm) rArm.rotation.z = -1.0;
        }

        // 修复材质：透明/眼部渲染问题
        vrm.scene.traverse(function(node) {
          if (node.isMesh && node.material) {
            var mats = Array.isArray(node.material) ? node.material : [node.material];
            mats.forEach(function(m) {
              if (m.alphaTest === 0 || m.transparent) m.alphaTest = 0.1;
              if (m.depthWrite === false) m.depthWrite = true;
              m.needsUpdate = true;
            });
          }
        });

        document.getElementById('msg').style.display = 'none';
        document.getElementById('error').style.display = 'none';
        if (pybridge && pybridge.onModelLoaded) pybridge.onModelLoaded('vrm_model');
      }).catch(function(err) {
        showError('VRM parse: ' + (err.message || err));
      });
    },
    function(progress) {
      if (progress.total > 0) {
        document.getElementById('msg').textContent = 'Loading... ' + Math.round(progress.loaded/progress.total*100) + '%';
      }
    },
    function(err) {
      showError('GLTF load: ' + (err ? (err.message || err) : 'unknown'));
    }
  );
}

// ---- 动画循环 ----

function animate() {
  requestAnimationFrame(animate);
  var now = Date.now();
  var delta = now - lastTime;
  lastTime = now;

  // VRM 更新（spring bones + blend shapes）
  if (currentVrm && currentVrm.update) currentVrm.update(delta);

  // 程序化待机动画：正弦驱动骨骼旋转（参数可调）
  if (currentVrm && currentVrm.humanoid && currentVrm.humanoid.getBoneNode) {
    var ac = window._vrmAnimConfig || {};
    var s = ac.speed || 1.0;
    var a = ac.amplitude || 1.0;
    var t = now * 0.001 * s;
    try {
      var spine = currentVrm.humanoid.getBoneNode('spine');
      if (spine) spine.rotation.z = Math.sin(t * 0.6) * 0.03 * a;
      var head = currentVrm.humanoid.getBoneNode('head');
      if (head) { head.rotation.z = (ac.headTilt || 0) + Math.sin(t * 0.7 + 0.5) * 0.04 * a; head.rotation.x = Math.sin(t * 0.5) * 0.02 * a; }
      var lArm = currentVrm.humanoid.getBoneNode('leftUpperArm');
      if (lArm) lArm.rotation.x = Math.sin(t * 0.4 + 2) * 0.05 * a;
      var rArm = currentVrm.humanoid.getBoneNode('rightUpperArm');
      if (rArm) rArm.rotation.x = Math.sin(t * 0.4 + 0.5) * 0.05 * a;
      var chest = currentVrm.humanoid.getBoneNode('chest');
      if (chest) chest.rotation.x = Math.sin(t * 0.8) * (ac.breathAmp || 0.015) * a;
    } catch(e) {}
  }

  // 主光跟踪相机 + 距离补偿亮度
  if (_keyLight && camera) {
    var dist = camera.position.distanceTo(window._vrmState.orbitTarget);
    _keyLight.position.copy(camera.position);
    _keyLight.intensity = 2.5 * Math.max(0.5, dist / 3);  // 距离越远光越强
  }

  if (renderer && scene && camera) renderer.render(scene, camera);
}

// ---- Display Settings API ----

window.setArmAngle = function(v) {
  var angle = Number(v);
  if (isNaN(angle)) return;
  if (currentVrm && currentVrm.humanoid && currentVrm.humanoid.getBoneNode) {
    var lArm = currentVrm.humanoid.getBoneNode('leftUpperArm');
    if (lArm) lArm.rotation.z = angle;
    var rArm = currentVrm.humanoid.getBoneNode('rightUpperArm');
    if (rArm) rArm.rotation.z = -angle;
  }
};
window.setModelScale = function(v) {
  var s = Number(v);
  if (isNaN(s) || s <= 0) return;
  if (currentVrm && currentVrm.scene) currentVrm.scene.scale.set(s, s, s);
};
window.setCameraDistance = function(v) {
  var dist = Number(v);
  if (isNaN(dist) || dist <= 0) return;
  if (window._vrmState.spherical && camera) {
    window._vrmState.spherical.radius = dist;
    camera.position.copy(window._vrmState.orbitTarget).add(
      new THREE.Vector3().setFromSpherical(window._vrmState.spherical)
    );
    camera.lookAt(window._vrmState.orbitTarget);
  }
};
window.setLightIntensity = function(v) {
  var intensity = Number(v);
  if (isNaN(intensity) || intensity < 0) return;
  if (_keyLight) _keyLight.intensity = intensity;
};

// 5. 视角高度（调整注视点 Y 坐标）
window.setTargetHeight = function(v) {
  var y = Number(v);
  if (isNaN(y)) return;
  window._vrmState.orbitTarget.y = y;
  if (camera) camera.lookAt(window._vrmState.orbitTarget);
};

// 6. 模型垂直偏移
window.setModelY = function(v) {
  var y = Number(v);
  if (isNaN(y)) return;
  if (currentVrm && currentVrm.scene) currentVrm.scene.position.y = y;
};

// 7. 视场角 FOV
window.setFOV = function(v) {
  var fov = Number(v);
  if (isNaN(fov) || fov <= 0) return;
  if (camera) { camera.fov = fov; camera.updateProjectionMatrix(); }
};

// 8. 模型水平偏移
window.setModelX = function(v) {
  var x = Number(v);
  if (isNaN(x)) return;
  if (currentVrm && currentVrm.scene) currentVrm.scene.position.x = x;
};

// 9. 模型 Y 轴旋转
window.setModelRotation = function(v) {
  var deg = Number(v);
  if (isNaN(deg)) return;
  if (currentVrm && currentVrm.scene) currentVrm.scene.rotation.y = deg * Math.PI / 180;
};

// 10. 背景透明度
window.setBgOpacity = function(v) {
  var a = Number(v);
  if (isNaN(a)) return;
  if (renderer) renderer.setClearColor(0x000000, a);
  // 同时控制 body 背景
  document.body.style.background = a < 0.01 ? 'transparent' : 'rgba(0,0,0,' + a + ')';
};

// 11. 环境光强度
window.setAmbientLight = function(v) {
  var intensity = Number(v);
  if (isNaN(intensity) || intensity < 0) return;
  // 找到第一个 AmbientLight 并修改
  scene.traverse(function(o) { if (o.isAmbientLight) o.intensity = intensity; });
};

// 12. 补光强度（找到第一个非 keyLight 的 DirectionalLight）
window.setFillLight = function(v) {
  var intensity = Number(v);
  if (isNaN(intensity) || intensity < 0) return;
  var found = false;
  scene.traverse(function(o) {
    if (o.isDirectionalLight && o !== _keyLight && !found) {
      o.intensity = intensity; found = true;
    }
  });
};

// 13. 动画速度
window.setAnimSpeed = function(v) {
  var s = Number(v);
  if (isNaN(s) || s < 0) return;
  window._vrmAnimConfig.speed = s;
};

// 14. 动画幅度
window.setAnimAmplitude = function(v) {
  var a = Number(v);
  if (isNaN(a) || a < 0) return;
  window._vrmAnimConfig.amplitude = a;
};

// 15. 头部倾斜
window.setHeadTilt = function(v) {
  var tilt = Number(v);
  if (isNaN(tilt)) return;
  window._vrmAnimConfig.headTilt = tilt;
};

// 16. 呼吸幅度
window.setBreathAmp = function(v) {
  var amp = Number(v);
  if (isNaN(amp) || amp < 0) return;
  window._vrmAnimConfig.breathAmp = amp;
};

// ---- Public API (Python runJavaScript 调用) ----

window.loadVRM = function(url) {
  // 总是先存到 _pendingUrl，无论当前状态
  _pendingUrl = url;
  tryLoadPending();
};

window.unloadVRM = _unloadVRM;

window.setMouthOpen = function(v) {
  if (currentVrm && currentVrm.blendShapeProxy)
    currentVrm.blendShapeProxy.setValue('A', Number(v) || 0);
};

window.setExpression = function(name, v) {
  if (currentVrm && currentVrm.blendShapeProxy)
    currentVrm.blendShapeProxy.setValue(name, Number(v) || 1);
};

window.forceResize = forceResize;

// ---- 启动 ----
// 延迟一帧确保 DOM 尺寸已确定
setTimeout(init3D, 10);
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

    def __init__(self, parent=None) -> None:
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
        self._page_ready = False # 页面是否就绪
        self._pending_model_path = None  # 页面就绪前暂存的模型路径

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
        self._bridge.page_ready_signal.connect(self._on_page_ready)
        self._bridge.model_error_signal.connect(self._on_model_error)

        layout.addWidget(self._web_view)

        # 获取静态文件服务器
        self._server = _VRMStaticServer.get()

        # 加载页面
        self._load_page()

        self.setMinimumSize(380, 480)

    # ========== Qt 事件 ==========

    def showEvent(self, event) -> None:
        """widget 变为可见时触发 — 强制 canvas resize（修复隐藏时初始化为 0x0）"""
        super().showEvent(event)
        if self._web_view and self._page_ready:
            # 延迟 100ms 确保 Qt 布局已完成
            QTimer.singleShot(100, self._force_canvas_resize)

    def resizeEvent(self, event) -> None:
        """widget 尺寸变化时触发 — 同步 canvas 尺寸"""
        super().resizeEvent(event)
        if self._web_view and self._page_ready:
            QTimer.singleShot(50, self._force_canvas_resize)

    def _force_canvas_resize(self) -> None:
        """调用 JS forceResize() 同步 canvas 尺寸"""
        try:
            self._web_page.runJavaScript("if(window.forceResize)window.forceResize()")
        except Exception as e:
            pass

    def _load_page(self) -> None:
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

    def _show_placeholder(self, message: str) -> None:
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

    def _on_page_ready(self) -> None:
        """JS 通知页面就绪"""
        self._page_ready = True
        _logger.info("VRM 页面就绪（init3D 完成）")
        # 如果有待加载的模型，现在加载
        if self._pending_model_path:
            pending = self._pending_model_path
            self._pending_model_path = None
            self.load_model(pending)

    def _on_model_loaded(self, model_name: str) -> None:
        """JS 通知模型加载完成"""
        self.model = True
        self._model_name = model_name
        self.model_loaded.emit(model_name)
        _logger.info(f"VRM 模型加载成功: {model_name}")

    def _on_model_error(self, msg: str) -> None:
        """JS 通知模型加载失败"""
        _logger.error(f"VRM 模型加载失败: {msg}")

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

        # 页面还未就绪，暂存路径，等 onPageReady 回调后自动加载
        if not self._page_ready:
            self._pending_model_path = path
            _logger.info(f"VRM 页面未就绪，暂存模型路径: {path}")
            return True

        # 将绝对路径转换为相对 URL
        path_norm = path.replace("\\", "/")
        static_norm = _STATIC_DIR.replace("\\", "/")

        if path_norm.startswith(static_norm):
            rel = path_norm[len(static_norm):].lstrip("/")
            model_url = "./" + rel
        else:
            model_url = path

        _logger.info(f"VRM 加载模型: path={path}, url={model_url}")

        # 设置 _pendingUrl 然后调用 loadVRM — 确保异步时序正确
        js_code = (
            f"window._pendingUrl='{model_url}';"
            f"if(window.loadVRM)window.loadVRM(window._pendingUrl)"
        )
        self._web_page.runJavaScript(js_code)
        return True

    # ========== Public API — 显示设置 ==========

    def set_arm_angle(self, value: float) -> None:
        """Set arm angle"""
        self._web_page.runJavaScript(f"if(window.setArmAngle)window.setArmAngle({value})")

    def set_model_scale(self, value: float) -> None:
        """Set model scale"""
        self._web_page.runJavaScript(f"if(window.setModelScale)window.setModelScale({value})")

    def set_camera_distance(self, value: float) -> None:
        """Set camera distance"""
        self._web_page.runJavaScript(f"if(window.setCameraDistance)window.setCameraDistance({value})")

    def set_light_intensity(self, value: float) -> None:
        """Set light intensity"""
        self._web_page.runJavaScript(f"if(window.setLightIntensity)window.setLightIntensity({value})")

    def set_target_height(self, value: float) -> None:
        """Set target height"""
        self._web_page.runJavaScript(f"if(window.setTargetHeight)window.setTargetHeight({value})")

    def set_model_y(self, value: float) -> None:
        """Set model y"""
        self._web_page.runJavaScript(f"if(window.setModelY)window.setModelY({value})")

    def set_fov(self, value: float) -> None:
        """Set fov"""
        self._web_page.runJavaScript(f"if(window.setFOV)window.setFOV({value})")

    def set_model_x(self, value: float) -> None:
        """Set model x"""
        self._web_page.runJavaScript(f"if(window.setModelX)window.setModelX({value})")

    def set_model_rotation(self, value: float) -> None:
        """Set model rotation"""
        self._web_page.runJavaScript(f"if(window.setModelRotation)window.setModelRotation({value})")

    def set_bg_opacity(self, value: float) -> None:
        """Set bg opacity"""
        self._web_page.runJavaScript(f"if(window.setBgOpacity)window.setBgOpacity({value})")

    def set_ambient_light(self, value: float) -> None:
        """Set ambient light"""
        self._web_page.runJavaScript(f"if(window.setAmbientLight)window.setAmbientLight({value})")

    def set_fill_light(self, value: float) -> None:
        """Set fill light"""
        self._web_page.runJavaScript(f"if(window.setFillLight)window.setFillLight({value})")

    def set_anim_speed(self, value: float) -> None:
        """Set anim speed"""
        self._web_page.runJavaScript(f"if(window.setAnimSpeed)window.setAnimSpeed({value})")

    def set_anim_amplitude(self, value: float) -> None:
        """Set anim amplitude"""
        self._web_page.runJavaScript(f"if(window.setAnimAmplitude)window.setAnimAmplitude({value})")

    def set_head_tilt(self, value: float) -> None:
        """Set head tilt"""
        self._web_page.runJavaScript(f"if(window.setHeadTilt)window.setHeadTilt({value})")

    def set_breath_amp(self, value: float) -> None:
        """Set breath amp"""
        self._web_page.runJavaScript(f"if(window.setBreathAmp)window.setBreathAmp({value})")

    def apply_display_config(self, config: dict) -> None:
        """Apply display config"""
        for key, method in [
            ("arm_angle", self.set_arm_angle),
            ("model_scale", self.set_model_scale),
            ("camera_distance", self.set_camera_distance),
            ("light_intensity", self.set_light_intensity),
            ("target_height", self.set_target_height),
            ("model_y", self.set_model_y),
            ("fov", self.set_fov),
            ("model_x", self.set_model_x),
            ("model_rotation", self.set_model_rotation),
            ("bg_opacity", self.set_bg_opacity),
            ("ambient_light", self.set_ambient_light),
            ("fill_light", self.set_fill_light),
            ("anim_speed", self.set_anim_speed),
            ("anim_amplitude", self.set_anim_amplitude),
            ("head_tilt", self.set_head_tilt),
            ("breath_amp", self.set_breath_amp),
        ]:
            if key in config:
                method(config[key])

    # ========== Public API — 口型同步 ==========

    def set_mouth_open(self, value: float) -> None:
        """设置口型开合度（TTS 口型同步）

        Args:
            value: 0.0（闭合）~ 1.0（完全张开）
        """
        clamped = max(0.0, min(1.0, float(value)))
        js_code = f"if(window.setMouthOpen)window.setMouthOpen({clamped:.2f})"
        self._web_page.runJavaScript(js_code)

    # ========== Public API — 表情控制 ==========

    def set_expression(self, name: str, value: float = 1.0) -> None:
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
