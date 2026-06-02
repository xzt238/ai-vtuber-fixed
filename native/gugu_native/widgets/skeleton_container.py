"""骨架屏占位容器

页面懒加载时显示的占位 UI，避免空白闪烁。
"""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from qfluentwidgets import IndeterminateProgressRing


class SkeletonContainer(QFrame):
    """骨架屏容器：显示加载动画和提示文字"""

    def __init__(self, title_text: str = "正在加载...", parent=None):
        super().__init__(parent)
        self._setup_ui(title_text)

    def _setup_ui(self, title_text: str):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._spinner = IndeterminateProgressRing(self)
        self._spinner.setFixedSize(48, 48)
        layout.addWidget(self._spinner, 0, Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel(title_text, self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label, 0, Qt.AlignmentFlag.AlignCenter)

        self.setVisible(False)

    def show_skeleton(self):
        self.setVisible(True)
        self._spinner.start()

    def hide_skeleton(self):
        self._spinner.stop()
        self.setVisible(False)
