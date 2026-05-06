"""
Phase 0.5 验证: PyInstaller 打包 PySide6 + live2d-py 应用

最小化打包测试，验证:
1. PySide6 能被正确打包
2. live2d-py 的 .pyd/.so 动态库能被收集
3. 打包后 EXE 能运行
"""

import sys
import os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import live2d.v3 as live2d
live2d.init()

from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phase 0.5 — PyInstaller 打包测试")
        self.setMinimumSize(400, 300)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        label = QLabel("✅ PySide6 + live2d-py 打包测试成功！")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 18px; color: #4CAF50;")
        layout.addWidget(label)

        info = QLabel(
            f"Python: {sys.version}\n"
            f"PySide6: {__import__('PySide6').__version__}\n"
            f"Live2D Core: 已加载"
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)


def main():
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    exit_code = app.exec()
    live2d.dispose()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
