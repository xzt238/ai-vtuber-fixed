"""
开机自启管理器 — Windows 注册表方式

功能:
- 添加/移除开机自启（注册表 HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Run）
- 查询当前自启状态
- 线程安全，不阻塞 UI

使用方式:
    manager = AutoStartManager()
    manager.is_enabled()  # 查询状态
    manager.enable()      # 启用
    manager.disable()     # 禁用
"""

import os
import sys
from PySide6.QtCore import QObject, Signal


class AutoStartManager(QObject):
    """
    开机自启管理器

    信号:
        state_changed(enabled): 自启状态变化
    """

    state_changed = Signal(bool)

    # 注册表键路径
    REG_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
    APP_NAME = "GuguGagaAI"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._app_path = self._get_app_path()

    def _get_app_path(self) -> str:
        """获取应用可执行文件路径"""
        if getattr(sys, 'frozen', False):
            # PyInstaller 打包模式
            return sys.executable
        else:
            # 开发模式：返回 python 脚本路径
            project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            main_script = os.path.join(project_dir, "native", "main.py")
            return f'"{sys.executable}" "{main_script}"'

    def is_enabled(self) -> bool:
        """查询是否已启用开机自启"""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REG_KEY, 0, winreg.KEY_READ)
            try:
                value, _ = winreg.QueryValueEx(key, self.APP_NAME)
                winreg.CloseKey(key)
                return bool(value)
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception:
            return False

    def enable(self) -> bool:
        """启用开机自启"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self.REG_KEY, 0,
                winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, self.APP_NAME, 0, winreg.REG_SZ, self._app_path)
            winreg.CloseKey(key)
            self.state_changed.emit(True)
            print(f"[AutoStart] 已启用开机自启: {self._app_path}")
            return True
        except PermissionError:
            print("[AutoStart] 权限不足，无法设置开机自启")
            return False
        except Exception as e:
            print(f"[AutoStart] 启用失败: {e}")
            return False

    def disable(self) -> bool:
        """禁用开机自启"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, self.REG_KEY, 0,
                winreg.KEY_SET_VALUE
            )
            try:
                winreg.DeleteValue(key, self.APP_NAME)
            except FileNotFoundError:
                pass  # 本来就没设置
            winreg.CloseKey(key)
            self.state_changed.emit(False)
            print("[AutoStart] 已禁用开机自启")
            return True
        except Exception as e:
            print(f"[AutoStart] 禁用失败: {e}")
            return False

    def toggle(self) -> bool:
        """切换开机自启状态"""
        if self.is_enabled():
            return self.disable()
        else:
            return self.enable()
