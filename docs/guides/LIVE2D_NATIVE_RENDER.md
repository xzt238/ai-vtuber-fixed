# Live2D 原生渲染方案 — live2d-py + QOpenGLWidget

> **版本**: v1.10.2 | **文件**: `native/gugu_native/widgets/live2d_widget.py`（423 行） | **最后更新**: 2026-05-22

---

## 概述

Native 桌面模式的 Live2D 渲染使用 **live2d-py**（Cubism SDK v5.1.0 Native 的 Python C 扩展）+ **QOpenGLWidget**，通过原生 OpenGL 直接渲染模型，无需 Web 引擎中间层。

## 为什么不用 QWebEngineView

| | QWebEngineView (v2.0) | live2d-py (v3.0) |
|---|---|---|
| 渲染 | Chromium → WebGL → GPU | OpenGL 直通 GPU |
| 启动 | Chromium 初始化 30~60s | 即时 |
| widget 插入 | **架构级死胡同**：已显示窗口插入后不自动合成 | Qt 原生 widget，布局自动处理 |
| 背景 | CSS/HTML 控制，不可靠 | `clearBuffer(0,0,0,0)` 精确控制 |
| 坐标映射 | PixiJS CSS transform 干扰 | 归一化 [0,1] 直传 |
| 依赖 | HTTP 服务器 + QWebChannel + oh-my-live2d + pixi.js | 仅 live2d-py |

结论：QWebEngineView 在已显示 Qt 窗口中动态插入后，Chromium 不会自动启动渲染管线——这是 Chromium Embedding 的架构级限制，不是 JS/HTML 的 bug。

---

## 架构

```
┌──────────────────────────────────────────────────┐
│  chat_page.py                                    │
│  ┌────────────────────────────────────────────┐  │
│  │  Live2DWidget(QOpenGLWidget)  ← 左侧面板   │  │
│  │  ┌──────────────────────────────────────┐  │  │
│  │  │  live2d-py v3 (C 扩展)              │  │  │
│  │  │  ├─ LAppModel (加载 .model3.json)    │  │  │
│  │  │  ├─ Cubism Core v5.1.0              │  │  │
│  │  │  └─ OpenGL Shader Pipeline           │  │  │
│  │  └──────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────┘  │
│  AnimationController  ──→  signals/methods 同步  │
└──────────────────────────────────────────────────┘
```

---

## 关键文件

| 文件 | 作用 |
|------|------|
| `native/gugu_native/widgets/live2d_widget.py` | Live2DWidget 类，全部渲染逻辑 |
| `native/gugu_native/pages/chat_page.py` | 布局集成，placeholder 替换，API 调用 |
| `app/version.py` | 版本号唯一数据源 `1.10.2` |
| `docs/VERSION.md` | 版本变更记录 |

**不再需要**（v2.0 遗留）：
- `live2d_web_widget.py` — QWebEngineView 实现（保留为回退参考）
- `_live2d_template.html` — oh-my-live2d HTML 模板
- `live2d_widget.html` — 缓存的 HTML 文件

---

## OpenGL 配置（透明背景）

```python
# 模块级全局格式（在 QApplication 创建前执行）
_DEFAULT_SURFACE_FORMAT = QSurfaceFormat()
_DEFAULT_SURFACE_FORMAT.setAlphaBufferSize(8)   # 透明通道
_DEFAULT_SURFACE_FORMAT.setSamples(4)            # MSAA 4x
_DEFAULT_SURFACE_FORMAT.setSwapInterval(1)       # VSync
QSurfaceFormat.setDefaultFormat(_DEFAULT_SURFACE_FORMAT)

# Widget 属性
self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
self.setMouseTracking(True)  # 眼神跟踪需要

# 每帧清屏
def paintGL(self):
    _live2d.clearBuffer(0.0, 0.0, 0.0, 0.0)  # RGBA(0,0,0,0) = 完全透明
```

**为什么用模块级 `setDefaultFormat` 而非 `self.setFormat()`**：
PySide6 的 `self.setFormat()` 在 `super().__init__()` 之前调用会触发 `RuntimeError: '__init__' method of object's base class not called`。使用模块级 `setDefaultFormat` 让所有 QOpenGLWidget 自动继承正确的格式。

---

## 模型加载流程

```
__init__
  └─ 设置属性、定时器、鼠标状态
  └─ 不加载模型（等待 load_model() 或 initializeGL）

load_model(path)
  └─ 保存路径到 self.model_path
  └─ 若 OpenGL 上下文就绪 → _do_load_model()
  └─ 否则等待 initializeGL() 中加载

initializeGL()                          ← Qt 在首次 show() 时自动调用
  └─ live2d.glInit()                    ← SDK OpenGL 初始化
  └─ 若 model_path 已设置 → _do_load_model()

_do_load_model()
  └─ self.makeCurrent()                 ← 绑定 OpenGL 上下文
  └─ LAppModel().LoadModelJson(path)    ← 加载 .model3.json
  └─ SetAutoBlinkEnable(True)           ← 自动眨眼
  └─ SetAutoBreathEnable(True)          ← 自动呼吸
  └─ model.Resize(w, h)                 ← ★ 立即适配 widget 尺寸
  └─ emit model_loaded(name)            ← 通知 animation_controller
  └─ emit expressions_updated(list)     ← 表情列表
  └─ emit motions_updated(list)         ← 动作分组列表
  └─ 启动 _anim_timer                   ← 60FPS 动画循环
  └─ self.doneCurrent()                 ← 释放上下文

paintGL()                               ← 每帧（update() 触发）
  └─ clearBuffer(0,0,0,0)              ← 透明清屏
  └─ model.Update()                     ← 更新模型状态
  └─ model.Draw()                       ← 绘制模型

resizeGL(w, h)                          ← 窗口尺寸变化
  └─ model.Resize(w, h)                 ← 更新视口
```

**关键点**：`LoadModelJson` 后必须立即调用 `model.Resize(w, h)` 适配当前 widget 尺寸，否则首次加载比例异常。

---

## 眼神跟踪

```python
# 鼠标移动：归一化到 [0,1]
def mouseMoveEvent(self, event):
    x = event.position().x() / self.width()
    y = event.position().y() / self.height()
    self._mouse_x = max(0.0, min(1.0, x))
    self._mouse_y = max(0.0, min(1.0, y))

# 每帧应用：驱动眼球跟随 + 头部微转
def _on_tick(self):
    if self.model:
        if hasattr(self.model, "SetDragging"):
            self.model.SetDragging(self._mouse_x, self._mouse_y)
        self.model.Drag(self._mouse_x, self._mouse_y)
    self.update()  # 触发 paintGL()
```

v2.0 (QWebEngineView) 的眼神跟踪被 oh-my-live2d 的 CSS `transform` 干扰，v3.0 直接操作 live2d-py 的 `Drag/SetDragging` API，坐标精确。

---

## API 参考

### 信号

| 信号 | 类型 | 触发时机 |
|------|------|----------|
| `model_loaded` | `Signal(str)` | 模型加载完成，参数为模型名称 |
| `expressions_updated` | `Signal(list)` | 表情 ID 列表就绪 |
| `motions_updated` | `Signal(list)` | 动作分组列表就绪 |

### 方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `load_model` | `(path: str) -> bool` | 加载 .model3.json 模型 |
| `set_expression` | `(name: str)` | 设置表情 |
| `start_motion` | `(group: str, index: int = 0, priority=None)` | 播放指定动作 |
| `start_random_motion` | `(group: str = "TapBody", priority=None)` | 随机动作 |
| `set_mouth_open` | `(value: float)` | 口型 0.0~1.0（写 `ParamMouthOpenY`） |
| `start_idle` | `()` | 启动空闲动画（`start_random_motion("Idle")`） |
| `set_fps` | `(fps: int)` | 帧率 1~120 |

### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `model` | `LAppModel \| None` | live2d-py 模型实例（truthy = 已加载） |
| `model_path` | `str \| None` | 当前模型路径 |

---

## live2d-py API 速查

| 操作 | API |
|------|-----|
| SDK 初始化 | `live2d.v3.init()` |
| OpenGL 初始化 | `live2d.v3.glInit()` |
| OpenGL 释放 | `live2d.v3.glRelease()` |
| 清屏 | `live2d.v3.clearBuffer(r, g, b, a)` |
| 创建模型 | `model = live2d.v3.LAppModel()` |
| 加载模型 | `model.LoadModelJson(path)` |
| 每帧更新 | `model.Update()` |
| 每帧绘制 | `model.Draw()` |
| 视口适配 | `model.Resize(w, h)` |
| 设置参数 | `model.SetParameterValue(name, value)` |
| 设置表情 | `model.SetExpression(id)` |
| 播放动作 | `model.StartMotion(group, index, priority)` |
| 随机动作 | `model.StartRandomMotion(group, priority)` |
| 眼球跟踪 | `model.Drag(x, y)` + `model.SetDragging(x, y)` |
| 自动眨眼 | `model.SetAutoBlinkEnable(True)` |
| 自动呼吸 | `model.SetAutoBreathEnable(True)` |
| 查询表情 | `model.GetExpressionIds()` |
| 查询动作 | `model.GetMotionGroups()` |

---

## 注意事项

1. **`live2d.v3.init()` 在模块级调用**：在 `import live2d_widget` 时执行，早于 `QApplication()` 创建。Cubism SDK 需要此时初始化。

2. **`Resize` 必须在 `LoadModelJson` 后立即调用**：否则首次渲染比例异常（需点击才恢复正常）。

3. **"can't start motion" 警告无害**：出现在 animation_controller 比模型信号更早触发时，不影响功能。

4. **不要用 `self.setFormat()`**：用模块级 `QSurfaceFormat.setDefaultFormat()` 代替。

---

## 迁移历史

| 版本 | 方案 | 状态 |
|------|------|------|
| v1.x | live2d-py + QOpenGLWidget | 可用但白色背景+眼神跟踪偏移 |
| v2.0 | QWebEngineView + oh-my-live2d | **废弃** — 架构级死胡同 |
| v1.10.2 | live2d-py + QOpenGLWidget（重写） | **当前** — 修复全部 v1.x 问题 |
