"""
系统托盘管理器

功能:
- QSystemTrayIcon + 右键菜单（显示窗口/隐藏/退出）
- 双击托盘图标恢复窗口
- 后端初始化进度通知
- 最小化到托盘行为
"""

import os
import sys
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject, Signal


class TrayManager(QObject):
    """系统托盘管理器"""

    # 信号：用户请求退出
    quit_requested = Signal()
    # 信号：后端初始化进度
    init_progress = Signal(str)  # 进度消息

    def __init__(self, main_window, parent=None) -> None:
        super().__init__(parent)
        self.main_window = main_window
        self._tray = None
        self._menu = None
        self._backend_initialized = False

    def setup(self) -> None:
        """初始化托盘图标和菜单"""
        from app.shared_config import PROJECT_DIR
        _native_dir = os.path.join(PROJECT_DIR, "native")
        icon_candidates = [
            os.path.join(_native_dir, "gugu_native", "resources", "app.ico"),
            os.path.join(_native_dir, "resources", "app.ico"),
            os.path.join(PROJECT_DIR, "assets", "gugugaga_logo.ico"),  # 项目根/assets/
            os.path.join(PROJECT_DIR, "assets", "icon.ico"),   # 项目根/assets/icon.ico (旧名)
        ]
        # PyInstaller 打包后，图标在 _internal/resources/ 或 exe 同级目录
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
            icon_candidates.insert(0, os.path.join(base, "resources", "app.ico"))
            icon_candidates.insert(1, os.path.join(base, "app.ico"))

        icon_path = None
        for p in icon_candidates:
            if os.path.exists(p):
                icon_path = p
                break

        icon = QIcon(icon_path) if icon_path else QIcon()

        self._tray = QSystemTrayIcon(icon, self.main_window)
        self._tray.setToolTip("咕咕嘎嘎 AI-VTuber")

        # 右键菜单
        self._menu = QMenu()

        self._show_action = QAction("显示窗口", self.main_window)
        self._show_action.triggered.connect(self._show_window)
        self._menu.addAction(self._show_action)

        self._hide_action = QAction("隐藏到托盘", self.main_window)
        self._hide_action.triggered.connect(self._hide_window)
        self._menu.addAction(self._hide_action)

        self._menu.addSeparator()

        self._debug_action = QAction("运行日志", self.main_window)
        self._debug_action.triggered.connect(self._show_debug)
        self._menu.addAction(self._debug_action)

        self._menu.addSeparator()

        self._quit_action = QAction("退出", self.main_window)
        self._quit_action.triggered.connect(self._on_quit)
        self._menu.addAction(self._quit_action)

        self._tray.setContextMenu(self._menu)

        # 双击托盘图标恢复窗口
        self._tray.activated.connect(self._on_tray_activated)

        # 消息点击回调
        self._tray.messageClicked.connect(self._show_window)

        self._tray.show()

        # 显示启动通知
        self._tray.showMessage(
            "咕咕嘎嘎 AI-VTuber",
            "应用已启动，正在初始化后端...",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )

    def _on_tray_activated(self, reason) -> None:
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self) -> None:
        """显示并激活主窗口"""
        self.main_window.showNormal()
        self.main_window.activateWindow()
        self.main_window.raise_()

    def _hide_window(self) -> None:
        """隐藏主窗口到托盘"""
        self.main_window.hide()

    def _show_debug(self) -> None:
        """显示运行调试窗口"""
        if hasattr(self.main_window, 'show_debug_window'):
            self.main_window.show_debug_window()

    def _on_quit(self) -> None:
        """用户请求退出"""
        self.quit_requested.emit()

    def notify_backend_ready(self) -> None:
        """通知后端初始化完成"""
        self._backend_initialized = True
        if self._tray:
            self._tray.showMessage(
                "咕咕嘎嘎 AI-VTuber",
                "后端已就绪，可以开始对话！",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )

    def notify_backend_error(self, error_msg: str) -> None:
        """通知后端初始化错误"""
        if self._tray:
            self._tray.showMessage(
                "咕咕嘎嘎 AI-VTuber",
                f"后端初始化失败: {error_msg}",
                QSystemTrayIcon.MessageIcon.Critical,
                5000
            )

    def update_progress(self, message: str) -> None:
        """更新初始化进度"""
        if self._tray:
            self._tray.setToolTip(f"咕咕嘎嘎 AI-VTuber - {message}")

    def handle_close_event(self, event) -> None:
        """
        处理主窗口关闭事件 — 最小化到托盘而非退出

        Returns:
            True: 事件已处理（最小化到托盘）
            False: 事件未处理（应退出）
        """
        # 检查设置页面是否启用了"最小化到托盘"
        settings_page = getattr(self.main_window, 'settings_page', None)
        if settings_page:
            tray_switch = getattr(settings_page, 'tray_switch', None)
            if tray_switch and tray_switch.isChecked():
                self._hide_window()
                event.ignore()
                return True
        return False

    def toggle_record_action(self) -> None:
        """托盘菜单切换录音 — 带 None guard"""
        voice_manager = getattr(self.main_window, 'voice_manager', None)
        if voice_manager is None:
            return
        if voice_manager.is_listening:
            voice_manager.stop_listening()
        else:
            voice_manager.start_listening()

    def cleanup(self) -> None:
        """清理托盘资源"""
        if self._tray:
            self._tray.hide()
            self._tray = None
