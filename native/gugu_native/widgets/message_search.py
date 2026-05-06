"""
咕咕嘎嘎 AI-VTuber — 消息搜索栏

功能:
- 实时搜索消息内容
- 上/下导航搜索结果
- 搜索计数显示
- ESC 关闭搜索栏

嵌入到聊天页面顶部，默认隐藏。
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal

from qfluentwidgets import LineEdit, ToolButton, FluentIcon


class MessageSearchBar(QWidget):
    """消息搜索栏

    信号:
    - searchRequested(query) — 搜索请求
    - searchNavigate(direction) — 导航搜索结果 (1=下一个, -1=上一个)
    - searchClosed() — 搜索栏关闭
    """

    searchRequested = Signal(str)
    searchNavigate = Signal(int)
    searchClosed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("messageSearchBar")
        self._result_count = 0
        self._current_index = 0
        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        from gugu_native.theme import get_colors
        c = get_colors()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # 搜索图标
        search_icon = ToolButton(FluentIcon.SEARCH)
        search_icon.setFixedSize(24, 24)
        layout.addWidget(search_icon)

        # 搜索输入框
        self._search_input = LineEdit()
        self._search_input.setPlaceholderText("搜索消息...")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.setFixedWidth(200)
        self._search_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._search_input)

        # 上一个
        self._prev_btn = ToolButton(FluentIcon.UP)
        self._prev_btn.setFixedSize(24, 24)
        self._prev_btn.setToolTip("上一个")
        self._prev_btn.clicked.connect(lambda: self.searchNavigate.emit(-1))
        layout.addWidget(self._prev_btn)

        # 下一个
        self._next_btn = ToolButton(FluentIcon.DOWN)
        self._next_btn.setFixedSize(24, 24)
        self._next_btn.setToolTip("下一个")
        self._next_btn.clicked.connect(lambda: self.searchNavigate.emit(1))
        layout.addWidget(self._next_btn)

        # 结果计数
        self._count_label = QLabel("0/0")
        self._count_label.setStyleSheet(f"color: {c.text_muted}; font-size: 12px;")
        layout.addWidget(self._count_label)

        layout.addStretch()

        # 关闭按钮
        close_btn = ToolButton(FluentIcon.CLOSE)
        close_btn.setFixedSize(24, 24)
        close_btn.setToolTip("关闭搜索")
        close_btn.clicked.connect(self._on_close)
        layout.addWidget(close_btn)

        # 整体样式
        self.setStyleSheet(f"""
            QWidget#messageSearchBar {{
                background-color: {c.card_bg};
                border-bottom: 1px solid {c.card_border};
                border-radius: 8px;
            }}
        """)

        # 默认隐藏
        self.setVisible(False)

    def _on_text_changed(self, text: str):
        """搜索文本变化"""
        if text.strip():
            self.searchRequested.emit(text.strip())
        else:
            self._result_count = 0
            self._current_index = 0
            self._update_count_label()

    def _on_close(self):
        """关闭搜索栏"""
        self._search_input.clear()
        self.setVisible(False)
        self.searchClosed.emit()

    def set_result_count(self, count: int, cross_session: int = 0):
        """设置搜索结果数量

        Args:
            count: 当前会话匹配数
            cross_session: 其他会话中的匹配消息数
        """
        self._result_count = count
        self._cross_session_count = cross_session
        self._current_index = min(self._current_index, max(count - 1, 0))
        if count > 0 and self._current_index == 0:
            self._current_index = 1
        self._update_count_label()

    def _update_count_label(self):
        """更新计数标签"""
        if self._result_count == 0 and getattr(self, '_cross_session_count', 0) == 0:
            self._count_label.setText("无结果")
        elif self._result_count == 0 and getattr(self, '_cross_session_count', 0) > 0:
            self._count_label.setText(f"其他会话 {self._cross_session_count} 条")
        else:
            text = f"{self._current_index}/{self._result_count}"
            if getattr(self, '_cross_session_count', 0) > 0:
                text += f" (+{self._cross_session_count})"
            self._count_label.setText(text)

    def keyPressEvent(self, event):
        """键盘事件 — ESC 关闭, Enter 下一个"""
        if event.key() == Qt.Key.Key_Escape:
            self._on_close()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.searchNavigate.emit(1)
        super().keyPressEvent(event)

    def show_search(self):
        """显示搜索栏并聚焦"""
        self.setVisible(True)
        self._search_input.setFocus()

    def refresh_theme(self):
        """刷新主题"""
        from gugu_native.theme import get_colors
        c = get_colors()

        self.setStyleSheet(f"""
            QWidget#messageSearchBar {{
                background-color: {c.card_bg};
                border-bottom: 1px solid {c.card_border};
                border-radius: 8px;
            }}
        """)
        self._count_label.setStyleSheet(f"color: {c.text_muted}; font-size: 12px;")
