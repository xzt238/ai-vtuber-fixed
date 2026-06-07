#!/usr/bin/env python3
"""
=====================================
日志系统 - 统一日志管理
=====================================

功能:
- 统一日志配置: 为项目中所有模块提供一致的日志记录接口
- 自动轮转: 单个日志文件达到大小上限后自动创建新文件，保留指定数量的备份
- 分级输出: 文件和控制台使用不同的日志级别阈值（文件更详细，控制台更简洁）
- 安全日志独立: 安全相关事件写入独立文件，便于安全审计

设计意图:
  Python 内置的 logging 模块功能强大但配置繁琐。本模块对其进行封装，
  提供一个 setup_logger() 函数即可完成完整的日志配置（文件+控制台+轮转+彩色）。
  预定义了各模块的 Logger 实例，可以直接 import 使用。

作者: 咕咕嘎嘎
日期: 2026-04-06
"""

import os       # 操作系统接口（本模块中用于文件路径操作）
import logging  # Python 标准日志库，提供 Logger、Handler、Formatter 等核心组件
from pathlib import Path  # 面向对象的路径处理
from logging.handlers import RotatingFileHandler  # 日志文件自动轮转处理器
from typing import Optional  # 类型注解：表示可选值


# ============================================================
# 日志目录配置
# ============================================================
# 所有日志文件统一存放在 logs/ 目录下
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)  # 确保日志目录存在，不存在则自动创建


# ============================================================
# 彩色日志格式化器
# ============================================================

class ColoredFormatter(logging.Formatter):
    """
    彩色日志格式化器（仅用于控制台输出）

    功能: 根据日志级别为日志消息添加 ANSI 颜色代码，在终端中显示不同颜色。
    - DEBUG: 青色（用于开发调试信息）
    - INFO: 绿色（用于正常运行信息）
    - WARNING: 黄色（用于潜在问题警告）
    - ERROR: 红色（用于错误信息）
    - CRITICAL: 紫色（用于严重错误）

    设计决策:
    - 只在控制台输出中使用颜色，文件日志保持纯文本（便于日志分析工具处理）
    - 使用 ANSI 转义码实现颜色，兼容大多数现代终端
    - 继承 logging.Formatter，通过重写 format() 方法注入颜色
    """

    # 日志级别到 ANSI 颜色代码的映射表
    # \033[XXm 是 ANSI 转义序列，XX 是颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色 (Cyan)
        'INFO': '\033[32m',       # 绿色 (Green)
        'WARNING': '\033[33m',    # 黄色 (Yellow)
        'ERROR': '\033[31m',      # 红色 (Red)
        'CRITICAL': '\033[35m',   # 紫色 (Magenta)
    }
    RESET = '\033[0m'  # 重置颜色代码，确保颜色不会"泄漏"到后续输出

    def format(self, record):
        """
        重写格式化方法，为日志级别名称添加颜色

        参数:
            record (logging.LogRecord): 日志记录对象，包含 levelname、message 等属性

        返回:
            str: 格式化后的带颜色日志字符串
        """
        # 根据日志级别获取对应的颜色代码，未匹配则使用重置代码（无颜色）
        log_color = self.COLORS.get(record.levelname, self.RESET)
        # 将颜色代码包裹在日志级别名称前后
        # 例如: "INFO" -> "\033[32mINFO\033[0m"（终端中显示为绿色）
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        # 调用父类的 format 方法完成其余格式化工作
        return super().format(record)


# ============================================================
# 核心函数: 设置日志记录器
# ============================================================

def setup_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 默认 10MB
    backup_count: int = 5,
    console_level: str = "WARNING"
) -> logging.Logger:
    """
    创建并配置一个日志记录器

    功能: 为指定模块创建一个完整的日志系统，包含:
    1. 文件 Handler: 将日志写入文件，支持自动轮转
    2. 控制台 Handler: 将日志输出到终端，带彩色格式

    参数说明:
        name (str): Logger 名称，通常使用模块名（如 "main"、"tts"、"llm"）
                    也是日志文件的默认文件名
        level (str): 文件日志的最低级别，默认 "INFO"
                     文件中会记录此级别及以上的所有日志
        log_file (str, optional): 日志文件名。默认为 "{name}.log"
        max_bytes (int): 单个日志文件的最大字节数，超过后自动轮转。默认 10MB
        backup_count (int): 保留的历史日志文件数量。默认 5 个
        console_level (str): 控制台输出的最低级别，默认 "WARNING"
                             控制台只显示此级别及以上的日志，减少终端噪音

    返回值:
        logging.Logger: 配置完成的 Logger 实例，可直接调用 info()/warning()/error() 等方法

    设计决策:
    - 文件日志默认 INFO 级别（记录所有重要信息），控制台默认 WARNING 级别（只显示警告和错误）
    - 防止重复添加 Handler: 如果 Logger 已有 Handler，直接返回（避免模块被多次 import 时重复配置）
    - 使用 RotatingFileHandler 而非 TimedRotatingFileHandler:
      按大小轮转更直观，且避免了零长度文件的问题
    """
    # 获取或创建指定名称的 Logger
    logger = logging.getLogger(name)
    # 设置 Logger 的全局最低级别（Handler 可以设置更高级别来过滤）
    logger.setLevel(getattr(logging, level.upper()))  # 将字符串 "INFO" 转为 logging.INFO 常量

    # 防止重复添加 Handler
    # 场景: 同一个模块被多次 import 时，setup_logger 会被多次调用
    if logger.handlers:
        return logger  # 已配置过，直接返回

    # ===== 配置文件日志 Handler =====
    if log_file is None:
        log_file = f"{name}.log"  # 默认使用 Logger 名称作为文件名

    log_path = LOG_DIR / log_file  # 完整的日志文件路径: logs/{name}.log

    # 创建 RotatingFileHandler: 当日志文件达到 max_bytes 时自动轮转
    # 轮转机制: app.log -> app.log.1 -> app.log.2 -> ... -> app.log.{backup_count}
    # 最旧的文件会被删除，确保磁盘空间不会无限增长
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,        # 单文件最大 10MB
        backupCount=backup_count,  # 保留 5 个备份
        encoding='utf-8'           # UTF-8 编码，支持中文日志
    )
    file_handler.setLevel(getattr(logging, level.upper()))  # 文件日志级别

    # 文件日志格式: 时间 - Logger名称 - 级别 - 消息
    # 示例: 2026-04-06 12:00:00 - main - INFO - 应用启动完成
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'  # 时间格式: 年-月-日 时:分:秒
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)  # 将文件 Handler 添加到 Logger

    # ===== 配置控制台日志 Handler =====
    console_handler = logging.StreamHandler()  # 默认输出到 sys.stderr
    console_handler.setLevel(getattr(logging, console_level.upper()))  # 控制台日志级别

    # 控制台日志格式: 级别 - 消息（更简洁，省略时间和 Logger 名称）
    # 使用 ColoredFormatter 实现彩色输出
    console_formatter = ColoredFormatter(
        '%(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)  # 将控制台 Handler 添加到 Logger

    return logger


# ============================================================
# 安全日志
# ============================================================

def setup_security_logger() -> logging.Logger:
    """
    创建专用的安全日志记录器

    功能: 创建一个独立的安全审计日志 Logger，用于记录安全相关事件
    （如权限检查、未授权访问、命令执行审计等）。

    设计决策:
    - 安全日志使用独立的文件 (security.log)，便于安全审计和合规检查
    - 文件日志级别设为 WARNING（只记录警告及以上），减少日志量
    - 控制台级别设为 ERROR（只在严重安全事件时才在终端显示）

    返回值:
        logging.Logger: 安全日志 Logger 实例
    """
    return setup_logger(
        name="security",        # Logger 名称
        level="WARNING",        # 文件日志级别: 只记录 WARNING 及以上
        log_file="security.log",  # 独立的安全日志文件
        console_level="ERROR"   # 控制台级别: 只显示 ERROR 和 CRITICAL
    )


# ============================================================
# 预定义的模块日志记录器
# ============================================================
# 为项目中每个核心模块创建预配置的 Logger 实例。
# 使用方只需 `from logger_new import main_logger` 即可直接使用。
# 设计意图: 避免在每个模块中重复配置日志，统一管理日志行为。

main_logger = setup_logger("main", level="INFO")      # 主应用日志 (main.py)
tts_logger = setup_logger("tts", level="INFO")        # TTS 语音合成模块日志
asr_logger = setup_logger("asr", level="INFO")        # ASR 语音识别模块日志
llm_logger = setup_logger("llm", level="INFO")        # LLM 大语言模型模块日志
web_logger = setup_logger("web", level="INFO")        # Web 服务器模块日志
memory_logger = setup_logger("memory", level="INFO")  # 记忆系统模块日志
tool_logger = setup_logger("tool", level="INFO")      # 工具调用模块日志
security_logger = setup_security_logger()              # 安全审计日志（独立文件）


# ============================================================
# 便捷函数
# ============================================================

def get_logger(name: str) -> logging.Logger:
    """
    获取或创建指定名称的 Logger

    功能: 如果该名称的 Logger 已经存在（包括预定义的和动态创建的），
    直接返回现有实例；否则创建一个新的。

    参数:
        name (str): Logger 名称

    返回值:
        logging.Logger: Logger 实例

    使用场景: 当模块需要自定义名称的 Logger 时（非预定义的模块名），使用此函数获取。
    """
    # 检查 Logger 是否已存在于 logging 的全局注册表中
    if name in logging.Logger.manager.loggerDict:
        return logging.getLogger(name)

    # 不存在则创建新的
    return setup_logger(name)


# ============================================================
# 模块自测入口
# ============================================================
if __name__ == "__main__":
    print("🧪 测试日志系统...")

    logger = get_logger("test")

    # 测试各级别日志输出
    logger.debug("这是 DEBUG 消息")      # 开发调试信息（默认不会输出到控制台）
    logger.info("这是 INFO 消息")        # 正常运行信息
    logger.warning("这是 WARNING 消息")  # 警告信息
    logger.error("这是 ERROR 消息")      # 错误信息
    logger.critical("这是 CRITICAL 消息")  # 严重错误

    # 测试安全日志
    security_logger.warning("检测到可疑操作")
    security_logger.error("安全事件：未授权访问")

    print(f"✅ 日志文件已保存到: {LOG_DIR}")
