"""
截图区域选择器 — 按下左键拖拽选择区域，松开后返回截图

用法:
    from gugu_native.widgets.screenshot_selector import ScreenshotSelector
    selector = ScreenshotSelector()
    selector.region_selected.connect(lambda path: ...)
    selector.start()
"""

import os
import tempfile
import time
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, Signal, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QScreen


class ScreenshotSelector(QWidget):
    """半透明遮罩 + 拖拽选框 — 截图区域选择器"""

    region_selected = Signal(str)  # 截图保存路径

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._start = QPoint()
        self._end = QPoint()
        self._selecting = False
        self._screenshots = {}  # 屏幕快照缓存

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.X11BypassWindowManagerHint  # 覆盖任务栏
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def start(self) -> None:
        """启动截图 — 全屏遮罩"""
        screen = QApplication.primaryScreen()
        if not screen:
            return

        # 截取整个屏幕作为背景
        geometry = screen.geometry()
        self._full_screenshot = screen.grabWindow(0)
        self.setGeometry(geometry)
        self.showFullScreen()

    def paintEvent(self, event) -> None:
        """绘制半透明遮罩 + 选区"""
        painter = QPainter(self)
        # 绘制全屏截图作为背景
        painter.drawPixmap(self.rect(), self._full_screenshot, self._full_screenshot.rect())

        # 半透明黑色遮罩
        mask = QColor(0, 0, 0, 100)
        painter.fillRect(self.rect(), mask)

        # 绘制选区矩形
        if self._selecting:
            rect = self._selection_rect().normalized()
            # 选区区域内恢复原图亮度
            painter.drawPixmap(rect, self._full_screenshot, rect)
            # 选区边框
            painter.setPen(QPen(QColor("#7c3aed"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

            # 选区尺寸提示
            size_text = f"{rect.width()} × {rect.height()}"
            painter.setPen(QColor("white"))
            painter.drawText(
                rect.x() + 4, rect.y() + rect.height() - 6,
                size_text
            )

        painter.end()

    def _selection_rect(self) -> QRect:
        return QRect(self._start, self._end)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self.close()
            return
        self._start = event.pos()
        self._end = event.pos()
        self._selecting = True
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._selecting:
            self._end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._selecting:
            self._selecting = False
            rect = self._selection_rect().normalized()
            self.hide()

            if rect.width() < 10 or rect.height() < 10:
                self.close()
                return

            # 保存选区截图
            screenshot = self._full_screenshot.copy(rect)
            tmp_path = os.path.join(
                tempfile.gettempdir(),
                f"gugu_screenshot_{int(time.time())}.png"
            )
            screenshot.save(tmp_path, "PNG")
            self.region_selected.emit(tmp_path)
            self.close()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)
