import logging
"""
开机自启管理器 — 跨平台（Windows/macOS/Linux）

logger = logging.getLogger(__name__)

功能:
- 添加/移除开机自启
- 查询当前自启状态
- 线程安全，不阻塞 UI

平台实现:
- Windows: 注册表 HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
- macOS: LaunchAgent plist (~/Library/LaunchAgents/)
- Linux: .desktop autostart (~/.config/autostart/)
"""

import os
import sys
from pathlib import Path
from PySide6.QtCore import QObject, Signal


class AutoStartManager(QObject):
    """跨平台开机自启管理器"""

    state_changed = Signal(bool)
    APP_NAME = "GuguGagaAI"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._app_path = self._get_app_path()

    def _get_app_path(self) -> str:
        """获取应用可执行文件路径"""
        if getattr(sys, 'frozen', False):
            return sys.executable
        else:
            project_dir = Path(__file__).resolve().parents[3]
            main_script = project_dir / "native" / "main.py"
            return f'"{sys.executable}" "{main_script}"'

    def is_enabled(self) -> bool:
        """查询是否已启用开机自启"""
        try:
            if sys.platform == "win32":
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
                    0, winreg.KEY_READ)
                try:
                    value, _ = winreg.QueryValueEx(key, self.APP_NAME)
                    winreg.CloseKey(key)
                    return bool(value)
                except FileNotFoundError:
                    winreg.CloseKey(key)
                    return False
            elif sys.platform == "darwin":
                plist = Path.home() / "Library" / "LaunchAgents" / f"com.gugugaga.{self.APP_NAME}.plist"
                return plist.exists()
            else:  # Linux
                desktop = Path.home() / ".config" / "autostart" / f"{self.APP_NAME}.desktop"
                return desktop.exists()
        except Exception as e:
            return False

    def enable(self) -> bool:
        """启用开机自启"""
        try:
            from app.platform_abstraction import set_autostart
            ok = set_autostart(True, self.APP_NAME, self._app_path)
            if ok:
                self.state_changed.emit(True)
                logger.info(f"[AutoStart] 已启用开机自启 ({sys.platform})")
            return ok
        except Exception as e:
            logger.info(f"[AutoStart] 启用失败: {e}")
            return False

    def disable(self) -> bool:
        """禁用开机自启"""
        try:
            ok = set_autostart(False, self.APP_NAME, self._app_path)
            if ok:
                self.state_changed.emit(False)
                logger.info(f"[AutoStart] 已禁用开机自启 ({sys.platform})")
            return ok
        except Exception as e:
            logger.info(f"[AutoStart] 禁用失败: {e}")
            return False

    def toggle(self) -> bool:
        """切换开机自启状态"""
        if self.is_enabled():
            return self.disable()
        else:
            return self.enable()
