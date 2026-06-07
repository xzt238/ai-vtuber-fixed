#!/usr/bin/env python3
"""
=====================================
游戏风格日志系统 (Game-Style Log System)
=====================================

从 app/main.py 抽取的装饰性日志输出函数，用于在控制台显示
游戏风格的加载提示、状态标签和进度条。

设计意图:
    这些纯装饰性函数与核心业务逻辑无关，独立成模块后
    main.py 更简洁，也方便其他模块复用统一的日志风格。

作者: 咕咕嘎嘎
日期: 2026-05-26 (从 main.py 抽取)
"""

import sys
import os
import time
import datetime
import logging

logger = logging.getLogger(__name__)


# ANSI 颜色码（Windows 10+ 支持）
class LogStyle:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # 颜色
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    # 背景
    BG_DARK = "\033[40m"
    BG_BLUE = "\033[44m"

    @staticmethod
    def is_supported() -> None:
        return sys.platform != "win32" or os.getenv("TERM") or True


def _color(text, color) -> None:
    """给文本添加颜色"""
    return f"{color}{text}{LogStyle.RESET}"


def _timestamp() -> None:
    """获取时间戳"""
    return datetime.datetime.now().strftime("%H:%M:%S")


def game_header(title="") -> None:
    """游戏风格标题"""
    logger.info()
    logger.info(_color("╔" + "═" * 58 + "╗", LogStyle.CYAN))
    if title:
        logger.info(_color(f"║  {title.center(54)}  ║", LogStyle.CYAN))
    logger.info(_color("╚" + "═" * 58 + "╝", LogStyle.CYAN))


def game_box(lines) -> None:
    """游戏风格信息框"""
    logger.info(_color("┌" + "─" * 58 + "┐", LogStyle.BLUE))
    for line in lines:
        logger.info(_color(f"│  {line:<54}  │", LogStyle.BLUE))
    logger.info(_color("└" + "─" * 58 + "┘", LogStyle.BLUE))


def game_loading(module, status="Loading", color=LogStyle.YELLOW) -> None:
    """游戏风格加载提示"""
    dots = "." * ((int(time.time() * 2) % 3) + 1)
    logger.info(f"\r  [{_color('LOAD', LogStyle.DIM)}] {_color(f'{module} {status}{dots}', color)}", end="", flush=True)


def game_ok(module, msg="") -> None:
    """游戏风格成功"""
    msg_part = f" {_color(msg, LogStyle.DIM)}" if msg else ""
    logger.info(f"\r  [{_color('  OK  ', LogStyle.GREEN)}] {_color(module, LogStyle.WHITE)}{msg_part}")


def game_skip(module, msg="") -> None:
    """游戏风格跳过"""
    msg_part = f" {_color(msg, LogStyle.DIM)}" if msg else ""
    logger.info(f"\r  [{_color(' SKIP ', LogStyle.YELLOW)}] {_color(module, LogStyle.DIM)}{msg_part}")


def game_fail(module, msg="") -> None:
    """游戏风格失败"""
    msg_part = f" {_color(msg, LogStyle.RED)}" if msg else ""
    logger.info(f"\r  [{_color(' FAIL ', LogStyle.RED)}] {_color(module, LogStyle.WHITE)}{msg_part}")


def game_info(module, msg="") -> None:
    """游戏风格信息"""
    msg_part = f" {_color(msg, LogStyle.CYAN)}" if msg else ""
    logger.info(f"  [{_color('INFO', LogStyle.CYAN)}] {_color(module, LogStyle.WHITE)}{msg_part}")


def game_warn(module, msg="") -> None:
    """游戏风格警告"""
    msg_part = f" {_color(msg, LogStyle.YELLOW)}" if msg else ""
    logger.info(f"  [{_color('WARN', LogStyle.YELLOW)}] {_color(module, LogStyle.WHITE)}{msg_part}")


def game_debug(module, msg="") -> None:
    """游戏风格调试"""
    msg_part = f" {_color(msg, LogStyle.DIM)}" if msg else ""
    logger.info(f"  [{_color('DEBUG', LogStyle.DIM)}] {_color(module, LogStyle.DIM)}{msg_part}")


def game_progress(current, total, module="") -> None:
    """游戏风格进度条"""
    bar_len = 30
    filled = int(bar_len * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_len - filled)
    percent = int(100 * current / total) if total > 0 else 0
    module_part = f" {_color(module, LogStyle.CYAN)}" if module else ""
    logger.info(f"\r  [{bar}] {percent:3d}%{module_part}", end="", flush=True)
    if current >= total:
        logger.info()


def game_section(title) -> None:
    """游戏风格分节标题"""
    logger.info("")
    logger.info(_color(f"  ▸ {title}", LogStyle.MAGENTA))


def game_separator() -> None:
    """游戏风格分隔线"""
    logger.info(_color("  " + "─" * 56, LogStyle.DIM))
