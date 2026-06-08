"""
咕咕嘎嘎 AI-VTuber — 主题色卡组件

ThemeCardWidget 显示单个主题的预览色卡:
- 上方: 2-3 个圆形色块展示 preview_colors
- 下方: 主题名称
- 选中态: accent 色边框 + 轻微阴影
- 悬停态: 边框变浅
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, Signal, QRectF, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QFont

from gugu_native.theme import get_colors


class ThemeCardWidget(QWidget):
    """单个主题色卡，显示主题名 + 预览色块

    Signals:
        clicked(str): 点击时发出，携带 theme_id
    """

    clicked = Signal(str)

    def __init__(self, theme_id: str, name: str, preview_colors: list[str],
                 base_mode: str, style_tags: str = "", parent=None) -> None:
        """初始化主题色卡

        Args:
            theme_id: 主题唯一标识
            name: 主题显示名
            preview_colors: 色卡预览用 2-3 个代表色
            base_mode: "dark" 或 "light"
            style_tags: 风格标签字符串（如 "圆润 · 舒适 · 霓虹"）
            parent: 父组件
        """
        super().__init__(parent)
        self._theme_id = theme_id
        self._name = name
        self._preview_colors = preview_colors
        self._base_mode = base_mode
        self._style_tags = style_tags
        self._selected = False
        self._hovered = False

        self.setFixedSize(100, 108) if style_tags else self.setFixedSize(100, 90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{name}\n{style_tags}" if style_tags else name)

    def set_selected(self, selected: bool) -> None:
        """设置选中状态

        Args:
            selected: 是否选中
        """
        self._selected = selected
        self.update()

    def refresh_theme(self) -> None:
        """主题切换时刷新自身样式（选中边框颜色跟随当前主题 accent）"""
        self.update()

    def mousePressEvent(self, event) -> None:
        """鼠标点击事件 — 发出 clicked 信号"""
        self.clicked.emit(self._theme_id)
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:
        """鼠标进入 — 悬停态"""
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """鼠标离开 — 取消悬停态"""
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        """绘制色卡 — 圆角卡片 + 颜色圆形 + 主题名 + 选中/悬停边框"""
        c = get_colors()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 卡片尺寸
        card_rect = QRectF(0.5, 0.5, 99, 89)
        radius = 12.0

        # --- 绘制圆角卡片背景 ---
        card_path = QPainterPath()
        card_path.addRoundedRect(card_rect, radius, radius)

        # 背景色 — 暗色主题用 card_bg，亮色主题用白色
        if self._base_mode == "dark":
            bg_color = QColor(c.card_bg)
        else:
            bg_color = QColor("#ffffff")

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawPath(card_path)

        # --- 绘制预览色块（圆形，直径 24px）---
        color_count = min(len(self._preview_colors), 3)
        circle_diameter = 24
        circle_spacing = 8
        total_width = color_count * circle_diameter + (color_count - 1) * circle_spacing
        start_x = (100 - total_width) / 2
        circle_y = 18  # 色块中心 Y 坐标

        for i in range(color_count):
            cx = start_x + i * (circle_diameter + circle_spacing) + circle_diameter / 2
            cy = circle_y + circle_diameter / 2

            # 绘制圆形色块
            color_hex = self._preview_colors[i]
            circle_color = QColor(color_hex)
            circle_path = QPainterPath()
            circle_path.addEllipse(QRectF(cx - circle_diameter / 2, cy - circle_diameter / 2,
                                          circle_diameter, circle_diameter))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(circle_color))
            painter.drawPath(circle_path)

        # --- 绘制主题名 ---
        text_color = QColor(c.text_primary)
        font = QFont("Microsoft YaHei UI", 11)
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QPen(text_color))
        text_rect = QRectF(0, 52, 100, 30)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self._name)

        # --- 绘制风格标签（v5.0） ---
        if self._style_tags:
            tag_color = QColor(c.text_muted)
            tag_font = QFont("Microsoft YaHei UI", 8)
            painter.setFont(tag_font)
            painter.setPen(QPen(tag_color))
            tag_rect = QRectF(2, 74, 96, 16)
            painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, self._style_tags)

        # --- 绘制边框 ---
        if self._selected:
            # 选中态: 3px accent 边框 + 内发光 + 文字变色
            border_color = QColor(c.accent)
            pen = QPen(border_color, 3.0)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            selected_rect = QRectF(1.5, 1.5, 97, 87)
            selected_path = QPainterPath()
            selected_path.addRoundedRect(selected_rect, radius - 1, radius - 1)
            painter.drawPath(selected_path)

            # 选中标记：右上角小勾
            check_color = QColor(c.accent)
            painter.setBrush(QBrush(check_color))
            painter.setPen(Qt.PenStyle.NoPen)
            check_rect = QRectF(80, 2, 18, 18)
            check_path = QPainterPath()
            check_path.addEllipse(check_rect)
            painter.drawPath(check_path)
            # 勾号
            painter.setPen(QPen(QColor("#ffffff"), 2.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(84, 12, 88, 16)
            painter.drawLine(88, 16, 94, 8)
        elif self._hovered:
            # 悬停态: 2px 浅色边框
            border_color = QColor(c.card_border_hover)
            pen = QPen(border_color, 2.0)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            hover_rect = QRectF(1.0, 1.0, 98, 88)
            hover_path = QPainterPath()
            hover_path.addRoundedRect(hover_rect, radius, radius)
            painter.drawPath(hover_path)
        else:
            # 未选中态: 1px 浅色边框
            border_color = QColor(c.card_border)
            pen = QPen(border_color, 1.0)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            normal_path = QPainterPath()
            normal_path.addRoundedRect(card_rect, radius, radius)
            painter.drawPath(normal_path)

        painter.end()

    def sizeHint(self) -> QSize:
        """推荐尺寸"""
        return QSize(100, 90)
