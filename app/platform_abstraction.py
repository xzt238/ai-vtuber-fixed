"""
平台抽象层 — 封装 Windows/macOS/Linux 差异

提供统一的接口：
- 单实例互斥锁
- 系统消息弹窗
- 进程终止
- 开机自启
- 子进程参数
- 获取程序数据目录
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from typing import Optional, Any

_logger = logging.getLogger("Platform")


# ========== 平台检测 ==========

def is_windows() -> bool:
    return sys.platform == "win32"

def is_macos() -> bool:
    return sys.platform == "darwin"

def is_linux() -> bool:
    return sys.platform.startswith("linux")


# ========== 单实例互斥锁 ==========

if is_windows():
    import ctypes
    _kernel32 = ctypes.windll.kernel32

def create_mutex(name: str) -> Optional[Any]:
    """创建单实例互斥锁

    Returns:
        Windows: mutex handle
        Unix: lock file fd
        失败返回 None
    """
    if is_windows():
        try:
            handle = _kernel32.CreateMutexW(None, False, name)
            if _kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
                return None
            return handle
        except Exception:
            return None
    else:
        # Unix: 使用文件锁
        try:
            import fcntl
            lock_dir = get_app_data_dir() / "locks"
            lock_dir.mkdir(parents=True, exist_ok=True)
            lock_file = lock_dir / f"{name.replace('/', '_')}.lock"
            fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR)
            fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except (ImportError, OSError):
            _logger.warning("Unix 文件锁不可用，跳过单实例检测")
            return True  # 降级：认为锁定成功


def release_mutex(handle: Any) -> None:
    """释放互斥锁"""
    if handle is None or handle is True:
        return
    if is_windows():
        try:
            _kernel32.CloseHandle(handle)
        except Exception:
            pass
    else:
        try:
            os.close(handle)
        except Exception:
            pass


# ========== 系统消息弹窗 ==========

def show_message(title: str, message: str, level: str = "info") -> None:
    """跨平台消息弹窗"""
    if is_windows():
        MB_ICONMAP = {"info": 0x40, "warning": 0x30, "error": 0x10}
        try:
            ctypes.windll.user32.MessageBoxW(0, message, title, MB_ICONMAP.get(level, 0x40))
        except Exception:
            _logger.warning(f"消息弹窗失败: {title}")
    elif is_macos():
        subprocess.run(["osascript", "-e",
            f'display notification "{message}" with title "{title}"'], check=False)
    else:
        # Linux: 尝试 zenity 或 notify-send
        try:
            subprocess.run(["zenity", "--info", "--title", title, "--text", message], check=False)
        except FileNotFoundError:
            try:
                subprocess.run(["notify-send", title, message], check=False)
            except FileNotFoundError:
                _logger.info(f"{title}: {message}")


# ========== 进程终止 ==========

def kill_process(pid: int) -> bool:
    """终止指定 PID 的进程"""
    try:
        if is_windows():
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                         capture_output=True, check=False)
        else:
            os.kill(pid, 9)
        return True
    except Exception as e:
        _logger.error(f"终止进程 {pid} 失败: {e}")
        return False


# ========== 开机自启 ==========

def set_autostart(enabled: bool, app_name: str = "GuguGaga",
                  app_path: str = None, args: str = "") -> bool:
    """设置开机自启

    Args:
        enabled: True=启用, False=禁用
        app_name: 应用名
        app_path: 可执行文件路径（默认当前 Python）
        args: 命令行参数
    """
    if app_path is None:
        app_path = sys.executable

    try:
        if is_windows():
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE)
            if enabled:
                cmd = f'"{app_path}" {args}'.strip()
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            return True

        elif is_macos():
            plist_dir = Path.home() / "Library" / "LaunchAgents"
            plist_dir.mkdir(parents=True, exist_ok=True)
            plist_path = plist_dir / f"com.gugugaga.{app_name}.plist"
            if enabled:
                plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.gugugaga.{app_name}</string>
    <key>ProgramArguments</key>
    <array><string>{app_path}</string>{f'<string>{args}</string>' if args else ''}</array>
    <key>RunAtLoad</key><true/>
</dict>
</plist>"""
                plist_path.write_text(plist)
            else:
                plist_path.unlink(missing_ok=True)
            return True

        else:  # Linux
            autostart_dir = Path.home() / ".config" / "autostart"
            autostart_dir.mkdir(parents=True, exist_ok=True)
            desktop_path = autostart_dir / f"{app_name}.desktop"
            if enabled:
                desktop = f"""[Desktop Entry]
Type=Application
Name={app_name}
Exec={app_path} {args}
X-GNOME-Autostart-enabled=true
"""
                desktop_path.write_text(desktop)
            else:
                desktop_path.unlink(missing_ok=True)
            return True

    except Exception as e:
        _logger.error(f"开机自启设置失败: {e}")
        return False


# ========== 子进程参数 ==========

def get_subprocess_kwargs() -> dict:
    """获取跨平台子进程启动参数

    Windows 需隐藏 CMD 窗口，Unix 无需特殊处理
    """
    if is_windows():
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        return {
            "startupinfo": startupinfo,
            "creationflags": subprocess.CREATE_NO_WINDOW,
        }
    return {}


# ========== 应用数据目录 ==========

def get_app_data_dir() -> Path:
    """获取跨平台应用数据目录"""
    app = "GuguGaga"
    if is_windows():
        base = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(base) / app
    elif is_macos():
        return Path.home() / "Library" / "Application Support" / app
    else:
        return Path(os.environ.get("XDG_DATA_HOME",
                   str(Path.home() / ".local" / "share"))) / app


def get_app_config_dir() -> Path:
    """获取跨平台应用配置目录"""
    app = "gugugaga"
    if is_windows():
        base = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(base) / "GuguGaga"
    elif is_macos():
        return Path.home() / "Library" / "Application Support" / "GuguGaga"
    else:
        return Path(os.environ.get("XDG_CONFIG_HOME",
                   str(Path.home() / ".config"))) / app
