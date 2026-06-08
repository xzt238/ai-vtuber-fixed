"""
Live2D 原生渲染组件 — live2d-py + QOpenGLWidget

v3.0: 从零重写，回到 v1.x 的 live2d-py + QOpenGLWidget 方案，
彻底摆脱 QWebEngineView 的 Chromium 渲染问题。

与 v2.0 (Web 渲染) 的问题对比：
  - QWebEngineView 在已显示窗口插入后 Chromium 不会自动合成 → 不可见
  - QWebEngineView 的 stage transform/CSS animation 与 oh-my-live2d 冲突
  - 需要本地 HTTP 服务器 + QWebChannel 通信层，复杂度高

v3.0 优势：
  - 直接 OpenGL 渲染，无 Chromium 依赖
  - 透明背景（clearBuffer + WA_TranslucentBackground + AlphaBufferSize=8）
  - 正确的坐标映射（0~1 归一化 → Drag/SetDragging）
  - 与 AnimationController 完全兼容的 API

API 与 v2.0 完全兼容：
  - 信号: model_loaded, expressions_updated, motions_updated
  - 方法: load_model, set_expression, start_random_motion, start_motion,
          set_mouth_open, start_idle, set_fps
  - 属性: model, model_path
"""

import os
import logging

_logger = logging.getLogger("Live2DNative")

# ============================================================
# live2d-py SDK 初始化（模块级，在 QApplication 创建前执行）
# ============================================================
# 此模块由 chat_page.py 在模块加载时 import，时机早于
# main.py 中 QApplication(sys.argv) 的创建。
# live2d.init() 在 QApplication 之前调用可确保 Cubism SDK
# 框架正确初始化（虽然新版 live2d-py 已放宽此限制，但仍建议提前调用）。

_live2d_available = False
_live2d = None

try:
    import live2d.v3 as _live2d_v3

    _live2d = _live2d_v3
    _live2d_v3.init()
    _live2d_available = True
except ImportError:
    _logger.warning(
        "live2d-py 未安装，Live2DWidget 将不可用。"
        "请安装: pip install live2d-py"
    )
except Exception as e:
    _logger.error(f"live2d-py 初始化失败: {e}")

from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QSurfaceFormat


# ============================================================
# 全局 OpenGL Surface Format（确保透明背景）
# ============================================================
_DEFAULT_SURFACE_FORMAT = QSurfaceFormat()
_DEFAULT_SURFACE_FORMAT.setAlphaBufferSize(8)
_DEFAULT_SURFACE_FORMAT.setSamples(4)  # MSAA 4x 抗锯齿
_DEFAULT_SURFACE_FORMAT.setSwapInterval(1)  # VSync
QSurfaceFormat.setDefaultFormat(_DEFAULT_SURFACE_FORMAT)


class Live2DWidget(QOpenGLWidget):
    """Live2D 模型渲染组件 — 基于 live2d-py + QOpenGLWidget

    直接在 OpenGL 上下文中渲染 Cubism 模型，无需 WebView 中间层。
    支持透明背景、鼠标跟踪、表情切换、动作播放、口型同步。

    Signals:
        model_loaded(str): 模型加载完成，参数为模型名称
        expressions_updated(list): 表情 ID 列表就绪
        motions_updated(list): 动作分组列表就绪
    """

    # ========== Signals ==========
    model_loaded = Signal(str)       # 模型名称
    expressions_updated = Signal(list)  # 表情 ID 列表
    motions_updated = Signal(list)      # 动作分组列表

    def __init__(self, parent=None) -> None:
        """初始化 Live2D 渲染组件

        Args:
            parent: 父级 QWidget
        """
        # QSurfaceFormat 已在模块级通过 setDefaultFormat 全局设置
        super().__init__(parent)

        if not _live2d_available:
            _logger.error("live2d-py 不可用，Live2DWidget 无法正常工作")
            self.setMinimumSize(380, 480)
            return

        # ---- 模型状态 ----
        self.model = None       # LAppModel 实例（None = 未加载）
        self.model_path = None  # .model3.json 文件路径
        self._model_name = ""   # 模型名称（用于信号）

        # ---- 动画定时器 ----
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_tick)

        # ---- 鼠标跟踪状态 ----
        self._mouse_x = 0.0
        self._mouse_y = 0.0

        # ---- 渲染参数 ----
        self._target_fps = 60
        self._idle_fps = 15  # v1.11.29 P1-2: 空闲时帧率
        self._last_activity_time = 0  # 最后活动时间（鼠标移动/点击）

        # ---- 窗口拖动状态 ----
        self._is_dragging = False

        # v1.11.25 R-005: OpenGL 渲染优化 — 减少不必要的状态切换
        self._last_gl_state = {}  # 缓存 GL 状态，避免重复设置

        # ---- Widget 配置 ----
        self.setMinimumSize(380, 480)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    # ============================================================
    # OpenGL 生命周期
    # ============================================================

    def initializeGL(self) -> None:
        """OpenGL 上下文初始化 — 由 Qt 在首次 show() 时自动调用"""
        if not _live2d_available:
            return

        try:
            _live2d.glInit()
            _logger.info("OpenGL 上下文初始化完成")

            # 如果 load_model() 在 initializeGL 之前被调用，
            # model_path 已被设置，在此处执行实际加载
            if self.model_path and os.path.exists(self.model_path):
                self._do_load_model()

        except Exception as e:
            _logger.error(f"OpenGL 初始化失败: {e}")

    def paintGL(self) -> None:
        """每帧渲染 — 由 update() 触发"""
        if not _live2d_available:
            return

        # 清屏：RGBA(0,0,0,0) = 完全透明
        _live2d.clearBuffer(0.0, 0.0, 0.0, 0.0)

        if self.model is not None:
            self.model.Update()
            self.model.Draw()

    def resizeGL(self, w: int, h: int) -> None:
        """窗口尺寸变化时调整模型视口

        Args:
            w: 新宽度（像素）
            h: 新高度（像素）
        """
        if self.model is not None:
            self.model.Resize(w, h)

    # ============================================================
    # 动画循环
    # ============================================================

    def _on_tick(self) -> None:
        """动画帧更新 — 定时器回调

        每帧执行：
        1. 更新鼠标拖拽状态（眼球/头部跟踪）
        2. 触发 paintGL 重绘

        窗口拖动/resize 期间跳过重绘，释放主线程保证窗口操作流畅。

        v1.11.29 P1-2: 帧率自适应 — 空闲时自动降帧率
        """
        import time

        # v1.11.29 P1-2: 帧率自适应
        # 检测是否有活动（鼠标移动/点击）
        current_time = time.time()
        idle_time = current_time - self._last_activity_time

        # 空闲超过 3 秒时降帧率，有活动时恢复高帧率
        if idle_time > 3.0:
            target_interval = 1000 // self._idle_fps  # 66ms (15fps)
        else:
            target_interval = 1000 // self._target_fps  # 16ms (60fps)

        # 动态调整定时器间隔
        current_interval = self._anim_timer.interval()
        if abs(current_interval - target_interval) > 5:  # 避免频繁微调
            self._anim_timer.setInterval(target_interval)

        if self.model is not None:
            # 鼠标跟踪：将归一化坐标传给模型
            if hasattr(self.model, "SetDragging"):
                self.model.SetDragging(self._mouse_x, self._mouse_y)
            self.model.Drag(self._mouse_x, self._mouse_y)

        if not self._is_dragging:
            self.update()  # 触发 paintGL()

    # ============================================================
    # 鼠标事件（眼球/头部跟踪 + 点击交互）
    # ============================================================

    def mouseMoveEvent(self, event) -> None:
        """鼠标移动 → 模型眼球/头部跟踪

        将 Qt 像素坐标归一化到 [0, 1] 范围传给 live2d-py。
        live2d-py 内部使用此坐标驱动模型的眼球跟随和头部微转。

        v1.11.29 P1-2: 记录活动时间，用于帧率自适应
        """
        self._last_activity_time = time.time()  # 记录活动时间

        if self.model is not None and self.width() > 0 and self.height() > 0:
            x = event.position().x() / self.width()
            y = event.position().y() / self.height()
            self._mouse_x = max(0.0, min(1.0, x))
            self._mouse_y = max(0.0, min(1.0, y))
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:
        """鼠标点击 → 触发 TapBody 交互动作"""
        if self.model is not None:
            try:
                self.model.StartRandomMotion("TapBody", 3)
            except Exception as e:
                pass
        super().mousePressEvent(event)

    # ============================================================
    # 内部模型加载
    # ============================================================

    def _do_load_model(self) -> None:
        """内部方法：从 self.model_path 加载模型

        在 OpenGL 上下文就绪后调用（initializeGL 或 load_model 中）。
        加载成功后发出 model_loaded / expressions_updated / motions_updated 信号，
        并启动动画定时器。
        """
        if not _live2d_available:
            return

        try:
            self.makeCurrent()

            self.model = _live2d.LAppModel()
            self.model.LoadModelJson(self.model_path)

            # 启用自动眨眼和呼吸
            if hasattr(self.model, "SetAutoBlinkEnable"):
                self.model.SetAutoBlinkEnable(True)
            if hasattr(self.model, "SetAutoBreathEnable"):
                self.model.SetAutoBreathEnable(True)

            # 立即应用当前 widget 尺寸（修复首次加载比例问题）
            w, h = self.width(), self.height()
            if w > 0 and h > 0:
                self.model.Resize(w, h)

            # 提取模型名称（从文件名）
            model_name = os.path.splitext(os.path.basename(self.model_path))[0]
            # 处理 .model3.json 后缀
            if model_name.endswith(".model3"):
                model_name = model_name[:-7]
            self._model_name = model_name

            # 发出模型加载完成信号
            self.model_loaded.emit(model_name)

            # 查询并发出可用表情列表
            try:
                expressions = self.model.GetExpressionIds()
                if expressions:
                    self.expressions_updated.emit(list(expressions))
                    _logger.info(f"可用表情: {expressions}")
            except Exception as e:
                _logger.debug(f"查询表情列表失败: {e}")

            # 查询并发出可用动作分组列表
            try:
                motions = self.model.GetMotionGroups()
                if motions:
                    self.motions_updated.emit(list(motions))
                    _logger.info(f"可用动作分组: {motions}")
            except Exception as e:
                _logger.debug(f"查询动作分组列表失败: {e}")

            # 启动动画定时器
            interval_ms = int(1000 / max(1, self._target_fps))
            self._anim_timer.start(interval_ms)

            _logger.info(
                f"模型加载成功: {model_name} "
                f"({self.width()}x{self.height()}, {self._target_fps}FPS)"
            )

        except Exception as e:
            _logger.error(f"模型加载失败: {e}")
            import traceback
            traceback.print_exc()
            self.model = None

        finally:
            self.doneCurrent()

    # ============================================================
    # Public API — 模型管理
    # ============================================================

    def load_model(self, model_path: str) -> bool:
        """加载 Live2D 模型

        Args:
            model_path: .model3.json 文件的绝对路径

        Returns:
            bool: True 表示加载请求已接受
        """
        if not _live2d_available:
            _logger.error("live2d-py 不可用，无法加载模型")
            return False

        if not os.path.exists(model_path):
            _logger.error(f"模型文件不存在: {model_path}")
            return False

        # 保存路径，重置状态
        self.model_path = model_path
        self._model_name = ""
        self.model = None

        # 如果 OpenGL 上下文已就绪，立即加载
        if self.isValid():
            self._do_load_model()
        # 否则等待 initializeGL() 中加载

        return True

    # ============================================================
    # Public API — 表情控制
    # ============================================================

    def set_expression(self, name: str) -> None:
        """设置表情

        Args:
            name: 表情 ID（如 "happy", "sad", "f01", "F01"）
        """
        if self.model is None:
            return

        try:
            self.model.SetExpression(name)
            _logger.debug(f"表情切换: {name}")
        except Exception as e:
            _logger.error(f"表情设置失败 '{name}': {e}")

    # ============================================================
    # Public API — 动作控制
    # ============================================================

    def start_motion(self, group: str, index: int = 0, priority=None) -> None:
        """播放指定动作

        Args:
            group: 动作分组名（如 "TapBody", "Idle"）
            index: 分组内的动作索引
            priority: 优先级（数值越大越优先，默认 3）
        """
        if self.model is None:
            return

        try:
            prio = priority if priority is not None else 3
            self.model.StartMotion(group, index, prio)
            _logger.debug(f"动作播放: {group}[{index}] priority={prio}")
        except Exception as e:
            _logger.error(f"动作播放失败 '{group}[{index}]': {e}")

    def start_random_motion(self, group: str = "TapBody", priority=None) -> None:
        """随机播放动作组中的一个动作

        Args:
            group: 动作分组名（如 "TapBody", "Idle"）
            priority: 优先级（数值越大越优先，默认 3）
        """
        if self.model is None:
            return

        try:
            prio = priority if priority is not None else 3
            self.model.StartRandomMotion(group, prio)
            _logger.debug(f"随机动作: {group} priority={prio}")
        except Exception as e:
            _logger.error(f"随机动作失败 '{group}': {e}")

    # ============================================================
    # Public API — 口型同步
    # ============================================================

    def set_mouth_open(self, value: float) -> None:
        """设置口型开合度（TTS 口型同步）

        写入 Cubism 标准参数 ParamMouthOpenY。
        大多数 Live2D 模型使用此参数控制嘴巴开合。

        Args:
            value: 0.0（闭合）~ 1.0（完全张开）
        """
        if self.model is None:
            return

        clamped = max(0.0, min(1.0, float(value)))
        try:
            self.model.SetParameterValue("ParamMouthOpenY", clamped)
        except Exception as e:
            # 某些模型可能使用不同的参数名，静默忽略
            pass

    # ============================================================
    # Public API — 空闲动画
    # ============================================================

    def start_idle(self) -> None:
        """启动空闲动画（随机播放 Idle 分组动作）"""
        self.start_random_motion("Idle")

    # ============================================================
    # Public API — 帧率控制
    # ============================================================

    def set_fps(self, fps: int) -> None:
        """设置渲染帧率

        Args:
            fps: 目标帧率（1~120）
        """
        self._target_fps = max(1, min(120, int(fps)))
        if self._anim_timer.isActive():
            interval_ms = int(1000 / self._target_fps)
            self._anim_timer.setInterval(interval_ms)
            _logger.debug(f"FPS 更新: {self._target_fps}")

    def set_window_drag_state(self, dragging: bool) -> None:
        """响应窗口拖动/resize 状态变化，暂停或恢复重绘

        Args:
            dragging: True 时跳过重绘；False 时恢复正常帧率。
        """
        self._is_dragging = dragging
        if dragging:
            _logger.debug("Live2D 渲染暂停（窗口拖动/resize）")
        else:
            _logger.debug("Live2D 渲染恢复")


__all__ = ["Live2DWidget"]
