"""
咕咕嘎嘎 AI-VTuber — 多行输入框组件

功能:
- 多行文本输入（QTextEdit）
- Enter 发送, Shift+Enter 换行
- 自动高度调整（最大 5 行）
- 输入时聚焦发光效果
- 占位文本
- 引用预览栏

替代原有 LineEdit 单行输入框。
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent

from qfluentwidgets import ToolButton, FluentIcon


class MultiLineInput(QWidget):
    """多行输入框组件

    信号:
    - sendRequested(text) — 用户按 Enter 请求发送
    - heightChanged(height) — 输入框高度变化
    """

    sendRequested = Signal(str)
    heightChanged = Signal(int)

    # 最大可见行数
    MAX_VISIBLE_LINES = 5
    # 单行高度（像素，含 padding）
    LINE_HEIGHT = 22
    # 最小高度
    MIN_HEIGHT = 40
    # 最大高度
    MAX_HEIGHT = MIN_HEIGHT + LINE_HEIGHT * (MAX_VISIBLE_LINES - 1)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._quote_text = ""
        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        from gugu_native.theme import get_colors
        c = get_colors()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 引用预览栏（默认隐藏）
        self._quote_bar = QWidget()
        self._quote_bar.setObjectName("quoteBar")
        self._quote_bar.setVisible(False)
        quote_layout = QHBoxLayout(self._quote_bar)
        quote_layout.setContentsMargins(8, 4, 8, 4)
        quote_layout.setSpacing(6)

        quote_label = QLabel("引用:")
        quote_label.setStyleSheet(f"color: {c.text_muted}; font-size: 11px;")
        quote_layout.addWidget(quote_label)

        self._quote_text_label = QLabel()
        self._quote_text_label.setStyleSheet(
            f"color: {c.text_secondary}; font-size: 12px;"
            f"border-left: 2px solid {c.accent}; padding-left: 6px;"
        )
        self._quote_text_label.setWordWrap(True)
        self._quote_text_label.setMaximumHeight(60)
        quote_layout.addWidget(self._quote_text_label, stretch=1)

        self._quote_close_btn = ToolButton(FluentIcon.CLOSE)
        self._quote_close_btn.setFixedSize(20, 20)
        self._quote_close_btn.clicked.connect(self.clear_quote)
        quote_layout.addWidget(self._quote_close_btn)

        self._quote_bar.setStyleSheet(f"""
            QWidget#quoteBar {{
                background-color: {c.chat_timestamp_bg};
                border-bottom: 1px solid {c.card_border};
                border-radius: 8px 8px 0 0;
            }}
        """)

        main_layout.addWidget(self._quote_bar)

        # 多行文本输入框
        self._text_edit = QTextEdit()
        self._text_edit.setObjectName("multiLineInput")
        self._text_edit.setPlaceholderText("输入消息，按 Enter 发送，Shift+Enter 换行...")
        self._text_edit.setFont(QFont("Microsoft YaHei UI", 13))
        self._text_edit.setFrameShape(QTextEdit.Shape.NoFrame)
        self._text_edit.setMaximumHeight(self.MAX_HEIGHT)
        self._text_edit.setMinimumHeight(self.MIN_HEIGHT)
        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._text_edit.textChanged.connect(self._on_text_changed)
        self._text_edit.setStyleSheet(f"""
            QTextEdit#multiLineInput {{
                background-color: {c.input_bg};
                border: 1.5px solid {c.input_border};
                border-radius: 10px;
                padding: 8px 14px;
                color: {c.text_primary};
                font-size: 13px;
            }}
            QTextEdit#multiLineInput:focus {{
                border-color: {c.input_focus_border};
            }}
        """)

        main_layout.addWidget(self._text_edit)

    def keyPressEvent(self, event: QKeyEvent):
        """键盘事件 — Enter 发送, Shift+Enter 换行"""
        # 不拦截，让 QTextEdit 处理
        super().keyPressEvent(event)

    def _on_text_changed(self):
        """文本变化 — 自动调整高度"""
        doc = self._text_edit.document()
        # 计算所需高度
        line_count = doc.lineCount()
        content_height = min(
            self.MIN_HEIGHT + (line_count - 1) * self.LINE_HEIGHT,
            self.MAX_HEIGHT
        )
        self._text_edit.setFixedHeight(int(content_height))
        self.heightChanged.emit(int(content_height))

    # ===== 公共接口 =====

    def text(self) -> str:
        """获取输入文本"""
        return self._text_edit.toPlainText().strip()

    def setText(self, text: str):
        """设置输入文本"""
        self._text_edit.setPlainText(text)
        # 光标移到末尾
        cursor = self._text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self._text_edit.setTextCursor(cursor)

    def clear(self):
        """清空输入"""
        self._text_edit.clear()

    def setPlaceholderText(self, text: str):
        """设置占位文本"""
        self._text_edit.setPlaceholderText(text)

    def setEnabled(self, enabled: bool):
        """设置启用状态"""
        self._text_edit.setEnabled(enabled)

    def setFocus(self):
        """聚焦输入框"""
        self._text_edit.setFocus()

    def hasFocus(self) -> bool:
        """是否聚焦"""
        return self._text_edit.hasFocus()

    def set_quote(self, text: str):
        """设置引用文本"""
        self._quote_text = text
        short = text[:80] + ("..." if len(text) > 80 else "")
        self._quote_text_label.setText(short)
        self._quote_bar.setVisible(True)

    def clear_quote(self):
        """清除引用"""
        self._quote_text = ""
        self._quote_bar.setVisible(False)

    @property
    def quote_text(self) -> str:
        """获取引用文本"""
        return self._quote_text

    def refresh_theme(self):
        """刷新主题"""
        from gugu_native.theme import get_colors
        c = get_colors()

        self._text_edit.setStyleSheet(f"""
            QTextEdit#multiLineInput {{
                background-color: {c.input_bg};
                border: 1.5px solid {c.input_border};
                border-radius: 10px;
                padding: 8px 14px;
                color: {c.text_primary};
                font-size: 13px;
            }}
            QTextEdit#multiLineInput:focus {{
                border-color: {c.input_focus_border};
            }}
        """)

        self._quote_bar.setStyleSheet(f"""
            QWidget#quoteBar {{
                background-color: {c.chat_timestamp_bg};
                border-bottom: 1px solid {c.card_border};
                border-radius: 8px 8px 0 0;
            }}
        """)
        self._quote_text_label.setStyleSheet(
            f"color: {c.text_secondary}; font-size: 12px;"
            f"border-left: 2px solid {c.accent}; padding-left: 6px;"
        )


class _InputTextEdit(QTextEdit):
    """自定义 QTextEdit — 拦截 Enter 键"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._send_on_enter = True

    def keyPressEvent(self, event: QKeyEvent):
        """键盘事件 — Enter 发送, Shift+Enter 换行"""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Shift+Enter: 换行
                self.insertPlainText("\n")
                return
            else:
                # Enter: 发送
                parent = self.parent()
                while parent and not isinstance(parent, MultiLineInput):
                    parent = parent.parent()
                if parent:
                    parent.sendRequested.emit(parent.text())
                return
        super().keyPressEvent(event)


# 替换 _text_edit 为自定义版本
class MultiLineInputV2(MultiLineInput):
    """改进版多行输入框 — 自定义 QTextEdit 处理 Enter 键"""

    def _init_ui(self):
        """初始化 UI — 使用自定义 QTextEdit"""
        from gugu_native.theme import get_colors
        c = get_colors()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 引用预览栏
        self._quote_bar = QWidget()
        self._quote_bar.setObjectName("quoteBar")
        self._quote_bar.setVisible(False)
        quote_layout = QHBoxLayout(self._quote_bar)
        quote_layout.setContentsMargins(8, 4, 8, 4)
        quote_layout.setSpacing(6)

        quote_label = QLabel("引用:")
        quote_label.setStyleSheet(f"color: {c.text_muted}; font-size: 11px;")
        quote_layout.addWidget(quote_label)

        self._quote_text_label = QLabel()
        self._quote_text_label.setStyleSheet(
            f"color: {c.text_secondary}; font-size: 12px;"
            f"border-left: 2px solid {c.accent}; padding-left: 6px;"
        )
        self._quote_text_label.setWordWrap(True)
        self._quote_text_label.setMaximumHeight(60)
        quote_layout.addWidget(self._quote_text_label, stretch=1)

        self._quote_close_btn = ToolButton(FluentIcon.CLOSE)
        self._quote_close_btn.setFixedSize(20, 20)
        self._quote_close_btn.clicked.connect(self.clear_quote)
        quote_layout.addWidget(self._quote_close_btn)

        self._quote_bar.setStyleSheet(f"""
            QWidget#quoteBar {{
                background-color: {c.chat_timestamp_bg};
                border-bottom: 1px solid {c.card_border};
                border-radius: 8px 8px 0 0;
            }}
        """)

        main_layout.addWidget(self._quote_bar)

        # 自定义多行输入框
        self._text_edit = _InputTextEdit()
        self._text_edit.setObjectName("multiLineInput")
        self._text_edit.setPlaceholderText("输入消息，按 Enter 发送，Shift+Enter 换行...")
        self._text_edit.setFont(QFont("Microsoft YaHei UI", 13))
        self._text_edit.setFrameShape(QTextEdit.Shape.NoFrame)
        self._text_edit.setMaximumHeight(self.MAX_HEIGHT)
        self._text_edit.setMinimumHeight(self.MIN_HEIGHT)
        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._text_edit.textChanged.connect(self._on_text_changed)
        self._text_edit.setStyleSheet(f"""
            QTextEdit#multiLineInput {{
                background-color: {c.input_bg};
                border: 1.5px solid {c.input_border};
                border-radius: 10px;
                padding: 8px 14px;
                color: {c.text_primary};
                font-size: 13px;
            }}
            QTextEdit#multiLineInput:focus {{
                border-color: {c.input_focus_border};
            }}
        """)

        main_layout.addWidget(self._text_edit)
