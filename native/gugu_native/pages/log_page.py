"""
日志查看页面

功能：
1. 实时日志流显示
2. 日志级别过滤（DEBUG/INFO/WARNING/ERROR）
3. 日志搜索
4. 日志导出
5. 自动滚动控制
"""

import os
import logging
from datetime import datetime
from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QComboBox, QLineEdit,
    QCheckBox, QGroupBox, QFrame, QSplitter
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QTextCursor, QFont, QColor

from qfluentwidgets import (
    PushButton, ToolButton, FluentIcon, CaptionLabel,
    TogglePushButton, Slider, InfoBar, ComboBox,
    LineEdit, CheckBox, CardWidget
)

from gugu_native.theme import get_colors, register_theme_callback

logger = logging.getLogger('LogPage')


class LogPage(QWidget):
    """日志查看页面"""

    def __init__(self, parent=None) -> None:
        """内部方法"""
        super().__init__(parent)
        self.setObjectName("logPage")
        
        # 日志缓冲区
        self._log_buffer: List[str] = []
        self._max_buffer_size = 10000
        self._auto_scroll = True
        self._current_filter = "ALL"
        self._search_keyword = ""
        
        # 初始化 UI
        self._init_ui()
        
        # 注册主题回调
        register_theme_callback(self._apply_theme)
        
        # 启动日志监听定时器
        self._log_timer = QTimer(self)
        self._log_timer.timeout.connect(self._flush_log_buffer)
        self._log_timer.start(100)  # 每 100ms 刷新一次
        
        logger.info("LogPage initialized")

    def _init_ui(self) -> None:
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 标题栏
        title_layout = QHBoxLayout()
        title_label = QLabel("📋 系统日志")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # 自动滚动开关
        self.auto_scroll_cb = CheckBox("自动滚动")
        self.auto_scroll_cb.setChecked(True)
        self.auto_scroll_cb.toggled.connect(self._toggle_auto_scroll)
        title_layout.addWidget(self.auto_scroll_cb)
        
        # 清空按钮
        clear_btn = PushButton("清空")
        clear_btn.setIcon(FluentIcon.DELETE)
        clear_btn.clicked.connect(self._clear_logs)
        title_layout.addWidget(clear_btn)
        
        # 导出按钮
        export_btn = PushButton("导出")
        export_btn.setIcon(FluentIcon.SAVE)
        export_btn.clicked.connect(self._export_logs)
        title_layout.addWidget(export_btn)
        
        layout.addLayout(title_layout)
        
        # 过滤栏
        filter_layout = QHBoxLayout()
        
        # 日志级别过滤
        filter_label = QLabel("级别过滤:")
        filter_layout.addWidget(filter_label)
        
        self.level_combo = ComboBox()
        self.level_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.setCurrentText("ALL")
        self.level_combo.currentTextChanged.connect(self._filter_changed)
        filter_layout.addWidget(self.level_combo)
        
        filter_layout.addSpacing(20)
        
        # 搜索框
        search_label = QLabel("搜索:")
        filter_layout.addWidget(search_label)
        
        self.search_input = LineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索...")
        self.search_input.textChanged.connect(self._search_changed)
        filter_layout.addWidget(self.search_input)
        
        # 搜索按钮
        search_btn = PushButton("搜索")
        search_btn.setIcon(FluentIcon.SEARCH)
        search_btn.clicked.connect(self._do_search)
        filter_layout.addWidget(search_btn)
        
        layout.addLayout(filter_layout)
        
        # 日志显示区域
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Consolas", 10))
        self.log_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.log_display)
        
        # 状态栏
        status_layout = QHBoxLayout()
        self.status_label = QLabel("就绪")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        self.count_label = QLabel("日志条数: 0")
        status_layout.addWidget(self.count_label)
        layout.addLayout(status_layout)

    def _toggle_auto_scroll(self, checked: bool) -> None:
        """切换自动滚动"""
        self._auto_scroll = checked

    def _filter_changed(self, level: str) -> None:
        """日志级别过滤变更"""
        self._current_filter = level
        self._refresh_display()

    def _search_changed(self, keyword: str) -> None:
        """搜索关键词变更"""
        self._search_keyword = keyword
        if not keyword:
            self._refresh_display()

    def _do_search(self) -> None:
        """执行搜索"""
        self._refresh_display()

    def _clear_logs(self) -> None:
        """清空日志"""
        self._log_buffer.clear()
        self.log_display.clear()
        self.count_label.setText("日志条数: 0")
        logger.info("Logs cleared")

    def _export_logs(self) -> None:
        """导出日志"""
        try:
            from PySide6.QtWidgets import QFileDialog
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出日志", 
                f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "文本文件 (*.txt);;所有文件 (*)"
            )
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_display.toPlainText())
                InfoBar.success("导出成功", f"日志已导出到: {filename}", parent=self)
                logger.info(f"Logs exported to: {filename}")
        except Exception as e:
            InfoBar.error("导出失败", f"错误: {e}", parent=self)
            logger.error(f"Failed to export logs: {e}")

    def _refresh_display(self) -> None:
        """刷新日志显示"""
        self.log_display.clear()
        for log_line in self._log_buffer:
            if self._should_show_log(log_line):
                self._append_log_to_display(log_line)
        
        if self._auto_scroll:
            self._scroll_to_bottom()

    def _should_show_log(self, log_line: str) -> bool:
        """判断是否应该显示该日志"""
        # 级别过滤
        if self._current_filter != "ALL":
            if self._current_filter not in log_line:
                return False
        
        # 关键词搜索
        if self._search_keyword:
            if self._search_keyword.lower() not in log_line.lower():
                return False
        
        return True

    def _append_log_to_display(self, log_line: str) -> None:
        """添加日志到显示区域"""
        # 根据日志级别设置颜色
        if "ERROR" in log_line or "CRITICAL" in log_line:
            color = "#ff6b6b"  # 红色
        elif "WARNING" in log_line:
            color = "#ffd93d"  # 黄色
        elif "DEBUG" in log_line:
            color = "#6bcb77"  # 绿色
        else:
            color = "#d4d4d4"  # 默认灰色
        
        self.log_display.setTextColor(QColor(color))
        self.log_display.append(log_line)

    def _scroll_to_bottom(self) -> None:
        """滚动到底部"""
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_display.setTextCursor(cursor)

    def _flush_log_buffer(self) -> None:
        """刷新日志缓冲区"""
        # 这里可以从日志文件或日志处理器读取新日志
        # 暂时使用定时器模拟
        pass

    def add_log(self, message: str, level: str = "INFO") -> None:
        """添加日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_line = f"[{timestamp}] [{level}] {message}"
        
        self._log_buffer.append(log_line)
        
        # 限制缓冲区大小
        if len(self._log_buffer) > self._max_buffer_size:
            self._log_buffer = self._log_buffer[-self._max_buffer_size:]
        
        # 如果符合过滤条件，添加到显示
        if self._should_show_log(log_line):
            self._append_log_to_display(log_line)
            
            if self._auto_scroll:
                self._scroll_to_bottom()
        
        # 更新计数
        self.count_label.setText(f"日志条数: {len(self._log_buffer)}")

    def _apply_theme(self) -> None:
        """应用主题"""
        colors = get_colors()
        self.log_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {colors.card_bg};
                color: {colors.text_primary};
                border: 1px solid {colors.card_border};
                border-radius: 8px;
                padding: 8px;
            }}
        """)


class LogHandler(logging.Handler):
    """自定义日志处理器，将日志发送到 LogPage"""
    
    def __init__(self, log_page: LogPage) -> None:
        """内部方法"""
        super().__init__()
        self.log_page = log_page
    
    def emit(self, record) -> None:
        """发送日志记录"""
        try:
            msg = self.format(record)
            self.log_page.add_log(msg, record.levelname)
        except Exception:
            self.handleError(record)
