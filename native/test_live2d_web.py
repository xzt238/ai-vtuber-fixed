"""
Phase v2.0 验证: Live2D Web 渲染组件

验证目标:
- QWebEngineView + oh-my-live2d + pixi.js v7 渲染 Live2D 模型
- 透明背景（深色主题下无白色底色）
- 鼠标跟踪由 oh-my-live2d 自动处理
- 表情/动作切换
- 口型同步

测试方法:
  python test_live2d_web.py
"""

import sys
import os

# 确保项目路径在 sys.path 中
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# native 目录
NATIVE_DIR = os.path.dirname(os.path.abspath(__file__))
if NATIVE_DIR not in sys.path:
    sys.path.insert(0, NATIVE_DIR)

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

# OpenGL 上下文共享（QWebEngineView 需要）
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
try:
    from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)
except ImportError:
    pass

from gugu_native.widgets.live2d_web_widget import Live2DWidget


class TestWindow(QMainWindow):
    """测试主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("咕咕嘎嘎 AI-VTuber — Live2D Web 渲染验证")
        self.setMinimumSize(800, 600)

        # 深色背景（验证透明效果）
        self.setStyleSheet("QMainWindow { background-color: #1a1a2e; }")

        # 中央布局
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Live2D Web 组件
        self.live2d_widget = Live2DWidget()
        layout.addWidget(self.live2d_widget, stretch=1)

        # 控制按钮行
        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        # 表情按钮
        expressions = ["happy", "angry", "sad", "surprised", "neutral"]
        for expr in expressions:
            btn = QPushButton(expr)
            btn.setStyleSheet("QPushButton { color: white; background: #333; padding: 8px 16px; border-radius: 4px; }")
            btn.clicked.connect(lambda checked, e=expr: self.live2d_widget.set_expression(e))
            btn_layout.addWidget(btn)

        # 动作按钮
        btn_motion = QPushButton("随机动作")
        btn_motion.setStyleSheet("QPushButton { color: white; background: #333; padding: 8px 16px; border-radius: 4px; }")
        btn_motion.clicked.connect(lambda: self.live2d_widget.start_random_motion())
        btn_layout.addWidget(btn_motion)

        # 口型同步按钮
        btn_mouth = QPushButton("张嘴")
        btn_mouth.setStyleSheet("QPushButton { color: white; background: #333; padding: 8px 16px; border-radius: 4px; }")
        btn_mouth.clicked.connect(lambda: self._test_mouth())
        btn_layout.addWidget(btn_mouth)

        # 状态栏
        self.statusBar().showMessage("Live2D Web 渲染组件加载中...")
        self.statusBar().setStyleSheet("QStatusBar { color: #aaa; background: #1a1a2e; }")

        # 连接信号
        self.live2d_widget.model_loaded.connect(self._on_model_loaded)

        # 延迟加载模型
        QTimer.singleShot(1000, self._load_model)

    def _load_model(self):
        """加载默认 Live2D 模型"""
        model_path = os.path.join(
            PROJECT_DIR, "app", "web", "static", "assets", "model",
            "hiyori", "Hiyori.model3.json"
        )
        if os.path.exists(model_path):
            self.live2d_widget.load_model(model_path)
        else:
            self.statusBar().showMessage(f"模型不存在: {model_path}")

    def _on_model_loaded(self, model_name: str):
        """模型加载完成"""
        self.statusBar().showMessage(f"模型加载成功: {model_name} — 移动鼠标可跟踪眼球")

    def _test_mouth(self):
        """测试口型同步"""
        # 循环张嘴-闭嘴动画
        self._mouth_values = [0.0, 0.5, 1.0, 0.5, 0.0]
        self._mouth_index = 0
        self._mouth_timer = QTimer()
        self._mouth_timer.timeout.connect(self._mouth_tick)
        self._mouth_timer.start(200)

    def _mouth_tick(self):
        """口型动画 tick"""
        if self._mouth_index >= len(self._mouth_values):
            self._mouth_timer.stop()
            return
        self.live2d_widget.set_mouth_open(self._mouth_values[self._mouth_index])
        self._mouth_index += 1


def main():
    app = QApplication(sys.argv)

    window = TestWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
