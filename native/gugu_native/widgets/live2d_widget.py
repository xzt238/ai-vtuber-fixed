"""
Live2D 模型渲染组件

基于 live2d-py + QOpenGLWidget 实现 Live2D Cubism 模型的原生 OpenGL 渲染。

功能:
- 60FPS 动画循环
- 鼠标跟踪（眼球/头部）
- 表情/动作切换
- 自动眨眼/呼吸
- 口型同步 (TTS)
- 模型热切换

关键要点（来自 live2d-py v0.6.x 源码）:
1. live2d.init() 必须在创建 QOpenGLWidget 之前调用（在 main.py 中完成）
2. live2d.glInit() 在 initializeGL() 中调用
3. paintGL() 中必须先 clearBuffer → Update → Draw
4. 模型路径必须是 .model3.json 的绝对路径
"""

import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import QTimer, Qt, Signal

# live2d-py 是可选依赖
try:
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    import live2d.v3 as live2d
    LIVE2D_AVAILABLE = True
except ImportError:
    QOpenGLWidget = None
    live2d = None
    LIVE2D_AVAILABLE = False


if LIVE2D_AVAILABLE:

    class Live2DWidget(QOpenGLWidget):
        """Live2D 模型渲染组件"""

        # 信号：模型加载完成
        model_loaded = Signal(str)  # 模型名称
        # 信号：表情列表更新
        expressions_updated = Signal(list)  # 表情ID列表
        # 信号：动作分组更新
        motions_updated = Signal(list)  # 动作分组列表

        def __init__(self, parent=None):
            super().__init__(parent)
            self.model = None
            self.model_path = None
            self._timer = None
            self._mouse_x = 0.0
            self._mouse_y = 0.0
            self._mouth_value = 0.0
            self.setMinimumSize(380, 480)
            self.setMouseTracking(True)

        def initializeGL(self):
            """OpenGL 初始化"""
            try:
                live2d.glInit()
                print("[Live2DWidget] OpenGL 初始化完成")
            except Exception as e:
                print(f"[Live2DWidget] OpenGL 初始化失败: {e}")

        def paintGL(self):
            """每帧渲染"""
            live2d.clearBuffer(0.08, 0.08, 0.12, 1.0)  # 深色背景
            if self.model:
                self.model.Update()
                self.model.Draw()

        def resizeGL(self, w, h):
            """窗口大小变化"""
            if self.model:
                self.model.Resize(w, h)

        def load_model(self, model_path: str):
            """
            加载 Live2D 模型

            Args:
                model_path: .model3.json 文件的绝对路径
            """
            if not os.path.exists(model_path):
                print(f"[Live2DWidget] 模型文件不存在: {model_path}")
                return False

            try:
                # 如果已有模型，先释放
                if self.model:
                    del self.model
                    self.model = None

                self.model = live2d.LAppModel()
                self.model.LoadModelJson(model_path)
                self.model_path = model_path

                # 启用自动眨眼和呼吸
                if hasattr(self.model, 'SetAutoBlinkEnable'):
                    self.model.SetAutoBlinkEnable(True)
                if hasattr(self.model, 'SetAutoBreathEnable'):
                    self.model.SetAutoBreathEnable(True)

                # 启动空闲动作
                self.model.StartRandomMotion("Idle", live2d.MotionPriority.IDLE)

                # 启动动画定时器
                if self._timer is None:
                    self._timer = QTimer(self)
                    self._timer.timeout.connect(self._tick)
                    self._timer.start(16)  # ~60 FPS

                # 调整大小
                self.model.Resize(self.width(), self.height())

                # 发射信号
                model_name = os.path.basename(os.path.dirname(model_path))
                self.model_loaded.emit(model_name)

                expressions = self.model.GetExpressionIds() if hasattr(self.model, 'GetExpressionIds') else []
                self.expressions_updated.emit(expressions)

                motion_groups = self.model.GetMotionGroups() if hasattr(self.model, 'GetMotionGroups') else []
                self.motions_updated.emit(motion_groups)

                print(f"[Live2DWidget] 模型加载成功: {model_name}")
                print(f"  表情: {expressions}")
                print(f"  动作分组: {motion_groups}")
                return True
            except Exception as e:
                print(f"[Live2DWidget] 模型加载失败: {e}")
                import traceback
                traceback.print_exc()
                return False

        def _tick(self):
            """动画帧更新"""
            if self.model:
                self.model.Drag(self._mouse_x, self._mouse_y)
            self.update()

        # ========== 鼠标交互 ==========

        def mouseMoveEvent(self, event):
            """鼠标移动 → 眼球/头部跟踪"""
            if self.model:
                x = (event.position().x() / self.width()) * 2 - 1
                y = 1 - (event.position().y() / self.height()) * 2
                self._mouse_x = x
                self._mouse_y = y
            super().mouseMoveEvent(event)

        def mousePressEvent(self, event):
            """鼠标点击 → 模型交互"""
            if self.model and event.button() == Qt.MouseButton.LeftButton:
                x = event.position().x()
                y = event.position().y()
                # 尝试触发挥手动作
                try:
                    self.model.StartRandomMotion("TapBody", live2d.MotionPriority.NORMAL)
                except Exception:
                    pass
            super().mousePressEvent(event)

        def leaveEvent(self, event):
            """鼠标离开 → 重置跟踪"""
            self._mouse_x = 0.0
            self._mouse_y = 0.0
            super().leaveEvent(event)

        # ========== 表情/动作控制 ==========

        def set_expression(self, name: str):
            """设置表情"""
            if self.model:
                self.model.SetExpression(name)

        def start_motion(self, group: str, index: int = 0, priority=live2d.MotionPriority.NORMAL):
            """播放指定动作"""
            if self.model:
                self.model.StartMotion(group, index, priority)

        def start_random_motion(self, group: str = "TapBody", priority=live2d.MotionPriority.NORMAL):
            """随机播放动作"""
            if self.model:
                self.model.StartRandomMotion(group, priority)

        # ========== 口型同步 ==========

        def set_mouth_open(self, value: float):
            """
            设置口型开合度（TTS 口型同步）

            Args:
                value: 0.0~1.0
            """
            if self.model:
                try:
                    self.model.SetParameterValueById(
                        live2d.StandardParams.ParamMouthOpenY,
                        max(0.0, min(1.0, value))
                    )
                except Exception:
                    pass

        # ========== 空闲动作 ==========

        def start_idle(self):
            """启动空闲动作"""
            if self.model:
                self.model.StartRandomMotion("Idle", live2d.MotionPriority.IDLE)

else:

    class Live2DWidget(QWidget):
        """Live2D 不可用时的占位组件 — 显示提示信息"""

        model_loaded = Signal(str)
        expressions_updated = Signal(list)
        motions_updated = Signal(list)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.model = None
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)

            placeholder = QLabel("Live2D 未安装\n\npip install live2d-py")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("""
                QLabel {
                    color: #888;
                    font-size: 14px;
                    background: transparent;
                }
            """)
            layout.addWidget(placeholder)
            self.setMinimumSize(380, 480)

        def load_model(self, model_path: str):
            return False

        def set_expression(self, name: str):
            pass

        def start_motion(self, group: str, index: int = 0, priority=None):
            pass

        def start_random_motion(self, group: str = "TapBody", priority=None):
            pass

        def set_mouth_open(self, value: float):
            pass

        def start_idle(self):
            pass
