"""
咕咕嘎嘎 原生桌面 — 共享工具函数

提供所有页面通用的 helper，避免重复代码。
"""

import sys
import logging
from typing import Optional
from PySide6.QtCore import QTimer
from qfluentwidgets import InfoBar, InfoBarPosition


logger = logging.getLogger("gugu_native.utils")


def show_info(parent, title: str, content: str, duration: int = 3000) -> None:
    """显示信息栏（InfoBar）— 所有页面的统一通知方式"""
    InfoBar.info(
        title=title,
        content=content,
        parent=parent,
        position=InfoBarPosition.TOP,
        duration=duration,
    )


def show_warning(parent, title: str, content: str, duration: int = 4000) -> None:
    """显示警告栏"""
    InfoBar.warning(
        title=title,
        content=content,
        parent=parent,
        position=InfoBarPosition.TOP,
        duration=duration,
    )


def show_error(parent, title: str, content: str, duration: int = 5000) -> None:
    """显示错误栏"""
    InfoBar.error(
        title=title,
        content=content,
        parent=parent,
        position=InfoBarPosition.TOP,
        duration=duration,
    )


def deferred_call(callback, delay_ms: int = 50) -> None:
    """延迟调用 — 避免在信号处理中阻塞 UI"""
    QTimer.singleShot(delay_ms, callback)


# 自动重试的互斥锁获取（Windows 互斥锁延迟清理）
def acquire_mutex_with_retry(mutex_name: str, max_retries: int = 1, retry_delay: float = 3.0) -> bool:
    """尝试获取 Windows 命名互斥锁，失败后等待重试

    解决进程崩溃/强制终止后互斥锁延迟清理的问题。
    """
    import sys
    import ctypes
    import time as _time

    if sys.platform != "win32":
        return True

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

    for attempt in range(max_retries + 1):
        handle = kernel32.CreateMutexW(None, False, mutex_name)
        last_error = ctypes.get_last_error()

        if last_error != 183:  # ERROR_ALREADY_EXISTS
            return True  # Returns handle, but handle lifetime is managed by caller

        if attempt < max_retries:
            logger.warning(f"Mutex {mutex_name} already exists, retrying in {retry_delay}s...")
            _time.sleep(retry_delay)

    return False
