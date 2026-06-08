"""
咕咕嘎嘎 AI-VTuber — 自定义启动画面 + 运行调试窗口

功能:
- 替代 QSplashScreen，显示 Logo + 进度指示
- 内嵌"运行调试窗口"，实时显示 stdout/stderr 输出
- 日志行自动着色（OK=绿色、错误=红色、警告=黄色）
- 启动完成后自动隐藏，可随时从托盘菜单重新打开
- 无边框置顶窗口，半透明暗色背景

StdoutRedirector:
- 重定向 sys.stdout / sys.stderr 到 Qt 信号
- 逐行缓冲，避免单字符碎片

作者: 咕咕嘎嘎
日期: 2026-05-28
"""

import sys
import re
from datetime import datetime

from PySide6.QtCore import Qt, QObject, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QSizePolicy, QGraphicsOpacityEffect
)
from PySide6.QtGui import QFont, QPixmap, QColor, QTextCursor


# ============================================================
# ANSI 颜色码过滤正则（移除 CMD 的 ANSI 转义序列）
# ============================================================
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')


def _strip_ansi(text: str) -> str:
    """移除 ANSI 颜色码，保留纯文本"""
    return _ANSI_RE.sub('', text)


# ============================================================
# 日志行着色规则
# ============================================================

# 从 theme.py 引用颜色常量（延迟导入避免循环依赖）
def _get_log_colors() -> None:
    """获取日志颜色方案（延迟导入避免循环依赖）"""
    try:
        from gugu_native.theme import get_colors
        c = get_colors()
        return {
            'default': c.log_text,
            'timestamp': c.log_timestamp,
            'success': c.log_success,
            'error': c.log_error,
            'info': c.log_info,
            'bg': c.log_bg,
        }
    except Exception as e:
        return {
            'default': '#c9d1d9',
            'timestamp': '#5c5c72',
            'success': '#37b24d',
            'error': '#f03e3e',
            'info': '#4dabf7',
            'bg': '#0d0e1a',
        }


# 日志行关键字匹配 → 颜色
_LOG_PATTERNS = [
    # (正则, 颜色键, 说明)
    (r'\[OK\]|✓|成功|完成|就绪|completed|ready|SUCCESS', 'success'),
    (r'\[ERROR\]|✗|失败|错误|异常|Error|Exception|Traceback|CRITICAL', 'error'),
    (r'\[WARN\]|⚠|警告|WARNING', None),  # None = 使用 default_info 色
    (r'→|正在|加载|初始化|Loading|启动|预热|下载', 'info'),
]


def _classify_log_line(line: str) -> None:
    """根据内容返回日志行的颜色键"""
    for pattern, color_key in _LOG_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return color_key or 'info'
    return 'default'


# ============================================================
# StdoutRedirector — 捕获 Python 输出并转发到 Qt 信号
# ============================================================

class StdoutRedirector(QObject):
    """
    标准输出重定向器 (QObject)

    将 sys.stdout / sys.stderr 的输出拦截并通过 Qt 信号转发，
    支持逐行缓冲以避免单字符碎片。

    用法:
        redirector = StdoutRedirector()
        redirector.text_written.connect(splash.append_log)
        sys.stdout = redirector
        sys.stderr = redirector
    """

    text_written = Signal(str)

    def __init__(self, original_stream=None, parent=None) -> None:
        super().__init__(parent)
        self._original = original_stream or sys.__stdout__
        self._buffer = ""

    def write(self, text) -> None:
        # 同时写入原始流（保留文件日志等）
        try:
            self._original.write(text)
            self._original.flush()
        except Exception as e:
            pass

        # 缓冲并逐行发射信号
        self._buffer += text
        while '\n' in self._buffer:
            line, self._buffer = self._buffer.split('\n', 1)
            line = _strip_ansi(line.strip())
            if line:
                self.text_written.emit(line)

    def flush(self) -> None:
        # 刷新剩余缓冲
        if self._buffer.strip():
            line = _strip_ansi(self._buffer.strip())
            if line:
                self.text_written.emit(line)
            self._buffer = ""
        try:
            self._original.flush()
        except Exception as e:
            pass


# ============================================================
# SplashDebugWindow — 自定义启动画面
# ============================================================

class SplashDebugWindow(QWidget):
    """自定义启动画面 + 内嵌运行调试窗口"""

    def __init__(self, logo_path=None, parent=None) -> None:
        super().__init__(parent)

        # 窗口属性
        self.setWindowTitle("咕咕嘎嘎 - 启动中...")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(620, 520)

        # 颜色
        self._colors = _get_log_colors()

        # 日志行缓存（保留全部历史）
        self._log_lines = []

        # 窗口拖动
        self._drag_pos = None

        self._setup_ui(logo_path)

    # ========== UI 构建 ==========

    def _setup_ui(self, logo_path) -> None:
        """构建界面布局"""
        # 整体暗色背景
        self.setStyleSheet(f"""
            SplashDebugWindow {{
                background-color: #12131f;
                border: 1px solid #2a2b42;
                border-radius: 12px;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 16)
        main_layout.setSpacing(12)

        # --- Logo 区域 ---
        logo_container = QWidget()
        logo_container.setFixedHeight(160)
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.setSpacing(8)

        self._logo_label = QLabel()
        self._logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if logo_path:
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(140, 140, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
                self._logo_label.setPixmap(pixmap)
        main_layout.addWidget(logo_container)

        # --- 进度文字 ---
        self._progress_label = QLabel("正在启动...")
        self._progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress_label.setStyleSheet("""
            QLabel {
                color: #9a9ab0;
                font-size: 14px;
                font-family: "Microsoft YaHei UI";
                padding: 4px 0;
            }
        """)
        main_layout.addWidget(self._progress_label)

        # --- 跳过按钮（隐藏状态，后端初始化完成后或出错时可用） ---
        self._skip_btn = QPushButton("跳过等待 →")
        self._skip_btn.setVisible(False)
        self._skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._skip_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.08);
                color: #9a9ab0;
                border: 1px solid #2e2f48;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 12px;
                font-family: "Microsoft YaHei UI";
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.15);
                color: #e0e0f0;
            }
        """)
        self._skip_btn.clicked.connect(self._dismiss)
        main_layout.addWidget(self._skip_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- 调试窗口标题栏 ---
        debug_header = QWidget()
        debug_header_layout = QHBoxLayout(debug_header)
        debug_header_layout.setContentsMargins(0, 0, 0, 0)

        self._debug_title = QLabel("运行调试窗口")
        self._debug_title.setStyleSheet("""
            QLabel {
                color: #6c6c8a;
                font-size: 12px;
                font-family: "Microsoft YaHei UI";
            }
        """)
        debug_header_layout.addWidget(self._debug_title)
        debug_header_layout.addStretch()

        self._toggle_btn = QPushButton("收起 ▲")
        self._toggle_btn.setFixedSize(80, 24)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #5c5c72;
                border: 1px solid #2e2f48;
                border-radius: 4px;
                font-size: 11px;
                font-family: "Microsoft YaHei UI";
            }
            QPushButton:hover {
                color: #9a9ab0;
                border-color: #3a3b58;
            }
        """)
        self._toggle_btn.clicked.connect(self._toggle_debug)
        debug_header_layout.addWidget(self._toggle_btn)

        main_layout.addWidget(debug_header)

        # --- 日志输出区域 ---
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setFont(QFont("Cascadia Code", 9))
        self._log_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._log_view.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self._colors['bg']};
                color: {self._colors['default']};
                border: 1px solid #2a2b42;
                border-radius: 6px;
                padding: 8px;
                font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
                font-size: 9pt;
                line-height: 1.4;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: #3a3b58;
                border-radius: 3px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        self._log_view.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        main_layout.addWidget(self._log_view, stretch=1)

        # 初始添加一条欢迎日志
        self.append_log("咕咕嘎嘎 AI-VTuber 启动中...")

    def set_progress(self, text: str, percent: int = -1) -> None:
        """更新启动进度文字 — 供 main.py 各阶段调用

        合并了进度刷新、窗口居中和跳过按钮计时器三项功能。

        Args:
            text: 进度文字
            percent: 进度百分比 (0-100)，-1 表示不显示百分比
        """
        # v1.11.25 S-004: 进度细化 — 显示百分比
        if percent >= 0:
            display_text = f"{text} ({percent}%)"
        else:
            display_text = text

        self._progress_label.setText(display_text)
        QApplication.processEvents()       # 立即刷新 UI
        self._center_on_screen()           # 窗口居中

        # 首次调用 set_progress 后启动 10 秒倒计时显示跳过按钮
        if not hasattr(self, '_skip_timer_started'):
            self._skip_timer_started = True
            QTimer.singleShot(10000, self._show_skip_button)

    def _center_on_screen(self) -> None:
        """将窗口居中到屏幕"""
        screen = self.screen()
        if screen:
            screen_geo = screen.availableGeometry()
            x = (screen_geo.width() - self.width()) // 2 + screen_geo.x()
            y = (screen_geo.height() - self.height()) // 2 + screen_geo.y()
            self.move(x, y)

    # ========== 日志追加 ==========

    def append_log(self, text: str) -> None:
        """
        追加一行日志到调试窗口

        自动添加时间戳前缀，根据内容着色。
        支持换行符分隔的多行文本。
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = self._colors

        # 处理可能的多行文本
        lines = text.split('\n') if '\n' in text else [text]

        for line in lines:
            line = line.strip()
            if not line:
                continue

            self._log_lines.append(line)
            color_key = _classify_log_line(line)

            # 构建带颜色的 HTML 行
            if color_key == 'success':
                line_color = colors['success']
            elif color_key == 'error':
                line_color = colors['error']
            elif color_key == 'info':
                line_color = colors['info']
            else:
                line_color = colors['default']

            # HTML 转义
            safe_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            safe_line = safe_line.replace('"', '&quot;')

            html_line = (
                f'<span style="color:{colors["timestamp"]}">[{timestamp}]</span> '
                f'<span style="color:{line_color}">{safe_line}</span><br>'
            )

            # 追加到 QTextEdit
            cursor = self._log_view.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertHtml(html_line)

            # 自动滚到底部
            scrollbar = self._log_view.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _show_skip_button(self) -> None:
        """显示跳过按钮"""
        self._skip_btn.setVisible(True)
        self.append_log("💡 启动时间较长？按 Esc 或点击「跳过等待」关闭启动画面")

    # ========== 调试窗口折叠 ==========

    def _toggle_debug(self) -> None:
        """折叠/展开调试窗口"""
        if self._log_view.isVisible():
            self._log_view.setVisible(False)
            self._debug_title.setText("运行调试窗口 (已隐藏)")
            self._toggle_btn.setText("展开 ▼")
        else:
            self._log_view.setVisible(True)
            self._debug_title.setText("运行调试窗口")
            self._toggle_btn.setText("收起 ▲")

    # ========== 窗口拖动 ==========

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        """按 Escape 键关闭启动画面"""
        if event.key() == Qt.Key.Key_Escape:
            self._dismiss()
        super().keyPressEvent(event)

    def _dismiss(self) -> None:
        """跳过等待——后端就绪则激活主窗口，否则硬退出"""
        self.append_log("⚠ 用户手动跳过等待")
        if getattr(self, '_backend_ready', False):
            self.append_log("✓ 后端已就绪，显示主窗口")
            self.hide()
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for w in app.topLevelWindows():
                    if w is not self and w.isVisible():
                        w.raise_()
                        w.activateWindow()
                        break
        else:
            self.append_log("✗ 后端未就绪，强制退出（不留僵尸进程）")
            import os
            os._exit(0)  # 硬退出，不依赖 Qt 事件循环

    def mark_backend_ready(self) -> None:
        """标记后端已就绪——由 main.py 调用"""
        self._backend_ready = True

    # ========== 生命周期 ==========

    def fade_out_and_close(self) -> None:
        """
        淡出动画后关闭窗口

        启动完成后调用，给用户一个平滑过渡的视觉体验。
        """
        self.set_progress("启动完成!")
        self.append_log("✓ 全部就绪，即将进入主界面...")

        # 短暂延迟让用户看到最后一条日志
        QTimer.singleShot(800, self._start_fade)

    def _start_fade(self) -> None:
        """开始淡出动画"""
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(400)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.finished.connect(self.hide)
        self._fade_anim.start()

    def get_log_text(self) -> str:
        """获取完整的日志文本（纯文本）"""
        return '\n'.join(self._log_lines)
