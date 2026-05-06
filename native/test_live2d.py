"""
Phase 0.2 验证: live2d-py + QOpenGLWidget 加载 Hiyori 模型

验证目标:
- live2d-py 在 PySide6 QOpenGLWidget 中渲染 Live2D 模型
- 60FPS 动画循环
- 鼠标跟踪 (Drag)
- 表情/动作切换

关键要点（来自 live2d-py v0.6.x Arkueid 版本源码）:
1. live2d.init() 必须在创建 QApplication 和 QWidget 之前调用
2. live2d.glInit() 在 initializeGL() 中调用（Arkueid 版本用 glInit，非 glewInit）
3. live2d.dispose() 在 app.exec() 之后调用
"""

import sys
import os

# 确保项目路径在 sys.path 中
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import live2d.v3 as live2d

# 关键: live2d.init() 必须在创建 QApplication 和 QWidget 之前调用！
live2d.init()

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PySide6.QtCore import QTimer, Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget


class Live2DWidget(QOpenGLWidget):
    """Live2D 模型渲染组件 — 基于 live2d-py + QOpenGLWidget"""

    def __init__(self, model_path, parent=None):
        super().__init__(parent)
        self.model = None
        self.model_path = model_path
        self._anim_timer = None
        self._mouse_x = 0.0
        self._mouse_y = 0.0
        self.setMinimumSize(380, 480)
        self.setMouseTracking(True)

    def initializeGL(self):
        """OpenGL 初始化 — 加载 Live2D 模型"""
        try:
            # 关键: glInit() 初始化 OpenGL 上下文
            live2d.glInit()

            self.model = live2d.LAppModel()
            self.model.LoadModelJson(self.model_path)

            # 启用自动眨眼和呼吸
            if hasattr(self.model, 'SetAutoBlinkEnable'):
                self.model.SetAutoBlinkEnable(True)
            if hasattr(self.model, 'SetAutoBreathEnable'):
                self.model.SetAutoBreathEnable(True)

            # 启动空闲动作
            self.model.StartRandomMotion("Idle", 3)

            # 60FPS 动画定时器
            self._anim_timer = QTimer(self)
            self._anim_timer.timeout.connect(self._tick)
            self._anim_timer.start(16)  # ~60 FPS

            print(f"[Live2D] 模型加载成功: {self.model_path}")
            print(f"[Live2D] 可用表情: {self.model.GetExpressionIds()}")
            print(f"[Live2D] 动作分组: {self.model.GetMotionGroups()}")
        except Exception as e:
            print(f"[Live2D] 模型加载失败: {e}")
            import traceback
            traceback.print_exc()

    def paintGL(self):
        """每帧渲染"""
        live2d.clearBuffer(0.1, 0.1, 0.15, 1.0)  # 深色背景
        if self.model:
            self.model.Update()
            self.model.Draw()

    def resizeGL(self, w, h):
        """窗口大小变化时调整模型尺寸"""
        if self.model:
            self.model.Resize(w, h)

    def _tick(self):
        """动画帧更新"""
        if self.model:
            # 鼠标跟踪
            self.model.Drag(self._mouse_x, self._mouse_y)
        self.update()  # 触发 paintGL

    def mouseMoveEvent(self, event):
        """鼠标移动 → 模型眼球/头部跟踪"""
        if self.model:
            # 将鼠标坐标归一化到 [-1, 1]
            x = (event.position().x() / self.width()) * 2 - 1
            y = 1 - (event.position().y() / self.height()) * 2
            self._mouse_x = x
            self._mouse_y = y
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        """鼠标点击 → 触发模型交互"""
        if self.model:
            x = event.position().x()
            y = event.position().y()
            # 检测点击区域
            if hasattr(self.model, 'HitTest'):
                hit = self.model.HitTest("Body", x, y)
                if hit:
                    self.model.StartRandomMotion("TapBody", 3)
        super().mousePressEvent(event)

    def set_expression(self, name):
        """设置表情"""
        if self.model:
            self.model.SetExpression(name)

    def start_motion(self, group="TapBody", index=0, priority=3):
        """播放动作"""
        if self.model:
            self.model.StartMotion(group, index, priority)

    def start_random_motion(self, group="TapBody", priority=3):
        """随机播放动作"""
        if self.model:
            self.model.StartRandomMotion(group, priority)


class TestWindow(QMainWindow):
    """测试主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("咕咕嘎嘎 AI-VTuber — Phase 0.2 Live2D 验证")
        self.setMinimumSize(800, 600)

        # 中央布局
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Live2D 组件
        model_path = os.path.join(
            PROJECT_DIR, "app", "web", "static", "assets", "model",
            "hiyori", "Hiyori.model3.json"
        )
        self.live2d_widget = Live2DWidget(model_path)
        layout.addWidget(self.live2d_widget, stretch=1)

        # 控制按钮行
        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        # 表情按钮
        expressions = ["happy", "angry", "sad", "surprised", "neutral"]
        for expr in expressions:
            btn = QPushButton(expr)
            btn.clicked.connect(lambda checked, e=expr: self.live2d_widget.set_expression(e))
            btn_layout.addWidget(btn)

        # 动作按钮
        btn_motion = QPushButton("随机动作")
        btn_motion.clicked.connect(lambda: self.live2d_widget.start_random_motion())
        btn_layout.addWidget(btn_motion)

        # 状态栏
        self.statusBar().showMessage("Live2D 模型加载中...")


def main():
    app = QApplication(sys.argv)

    # 设置高 DPI 缩放
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    window = TestWindow()
    window.show()

    # 延迟更新状态栏（等模型加载完）
    QTimer.singleShot(1000, lambda: window.statusBar().showMessage(
        "Live2D 模型加载成功 — 移动鼠标可跟踪眼球/头部"
    ))

    exit_code = app.exec()

    # 关键: 退出前清理 Live2D 资源
    live2d.dispose()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
