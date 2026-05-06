#!/usr/bin/env python3
"""
=====================================
咕咕嘎嘎 AI虚拟形象 - 主程序
=====================================

功能概述:
    本文件是 AI VTuber 系统的入口点和核心协调器，负责:
    1. 配置管理 (Config): 加载 YAML 配置文件，支持环境变量展开 ${VAR}
    2. 工具执行器 (ToolExecutor): 安全执行系统命令，带白名单/黑名单校验
    3. AI VTuber 主类 (AIVTuber): 懒加载所有子模块，协调 ASR→LLM→TTS 管线
    4. CLI 入口 (main): 解析命令行参数，选择运行模式（Web/交互/测试）

架构设计:
    采用「懒加载」策略: 所有重模块（ASR/TTS/LLM/Vision/Memory 等）通过 @property
    在首次访问时才初始化，大幅缩短启动时间。AIVTuber 类作为统一的门面(Facade)，
    对外提供 process_message()（文字对话）和 process_audio()（语音对话）两个主入口。

与其他模块的关系:
    - Config → 读取 app/config.yaml，所有子模块共享同一配置
    - AIVTuber → 组合调用 asr/tts/llm/memory/vision/tools/web
    - ToolExecutor → 独立的命令执行沙箱，被 AIVTuber.process_message() 调用

输入:
    - config.yaml: YAML 格式配置文件（ASR/TTS/LLM/Voice/Web/Memory 等）
    - 命令行参数: --config, --web, --live2d, --interactive, --test-llm, --test-tts
    - 用户输入: 文字消息 或 音频数据(Base64)

输出:
    - LLM 回复文字
    - TTS 生成的音频文件路径
    - HTTP/WebSocket 服务（Web 模式下）

作者: 咕咕嘎嘎
日期: 2026-03-27
"""

import os
import sys
import subprocess as _subprocess

# Windows GBK 编码安全网：强制 stdout/stderr 使用 UTF-8
# 避免 print() 含 emoji/特殊字符时 UnicodeEncodeError 崩溃
# 必须在所有其他 import 之前执行，因为其他模块的顶层 print 可能触发此问题
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        # Python < 3.7 或 stdout 已关闭时忽略
        pass
import json
import tempfile
import argparse
import atexit
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List
from functools import cached_property

# 将当前 app/ 目录插入 Python 模块搜索路径的最前面
# 这样 import asr / import tts 等能正确解析到 app/ 下的子模块
sys.path.insert(0, str(Path(__file__).parent))


# ============ Windows subprocess 安全辅助函数 ============
# 桌面模式下所有 subprocess 调用必须隐藏 CMD 窗口，否则会闪现控制台
def _win_subprocess_args():
    """返回 Windows 桌面模式下 subprocess 隐藏 CMD 窗口所需的额外参数。
    返回 dict，可直接 **解包到 subprocess.run() 或 subprocess.Popen()。
    在非 Windows 或非桌面模式下返回空 dict。"""
    if sys.platform != "win32" or os.getenv("GUGUGAGA_DESKTOP") != "1":
        return {}
    si = _subprocess.STARTUPINFO()
    si.dwFlags |= _subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = _subprocess.SW_HIDE
    return {
        "startupinfo": si,
        "creationflags": _subprocess.CREATE_NO_WINDOW,
    }

# ============ 模型缓存目录配置 ============
# 所有模型下载缓存统一放在项目根目录下的 models/ 中，避免散落在各处
PROJECT_ROOT = Path(__file__).parent.parent
MODELS_CACHE = PROJECT_ROOT / "models"
# 确保 models/ 及其父目录存在，parents=True 允许递归创建
MODELS_CACHE.mkdir(parents=True, exist_ok=True)

# 设置各种深度学习框架的缓存路径环境变量
# HuggingFace/Transformers/ModelScope/Torch 都会读取这些变量来定位缓存目录
# 注意：使用 os.environ.setdefault() 而非直接赋值，避免覆盖 go.bat 已设置的路径
# go.bat 设置: HF_HOME=%~dp0.cache\huggingface, 项目实际模型在 .cache/ 下
# 只有在 go.bat 没设置时才 fallback 到 models/ 目录
os.environ.setdefault("MODELSCOPE_CACHE", str(MODELS_CACHE / "modelscope"))
os.environ.setdefault("HF_HOME", str(MODELS_CACHE / "hf"))
os.environ.setdefault("TORCH_HOME", str(MODELS_CACHE / "torch"))
# TRANSFORMERS_CACHE 已废弃（transformers v5 将移除），不再设置
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(MODELS_CACHE / "hf"))

# ============ 游戏风格日志系统 ============
import time
import datetime
import warnings

# 抑制常见警告（让 CMD 输出更干净）
warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")
warnings.filterwarnings("ignore", message=".*ffmpeg is not installed.*")

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
    def is_supported():
        return sys.platform != "win32" or os.getenv("TERM") or True

def _color(text, color):
    """给文本添加颜色"""
    return f"{color}{text}{LogStyle.RESET}"

def _timestamp():
    """获取时间戳"""
    return datetime.datetime.now().strftime("%H:%M:%S")

def game_header(title=""):
    """游戏风格标题"""
    print()
    print(_color("╔" + "═" * 58 + "╗", LogStyle.CYAN))
    if title:
        print(_color(f"║  {title.center(54)}  ║", LogStyle.CYAN))
    print(_color("╚" + "═" * 58 + "╝", LogStyle.CYAN))

def game_box(lines):
    """游戏风格信息框"""
    print(_color("┌" + "─" * 58 + "┐", LogStyle.BLUE))
    for line in lines:
        print(_color(f"│  {line:<54}  │", LogStyle.BLUE))
    print(_color("└" + "─" * 58 + "┘", LogStyle.BLUE))

def game_loading(module, status="Loading", color=LogStyle.YELLOW):
    """游戏风格加载提示"""
    dots = "." * ((int(time.time() * 2) % 3) + 1)
    print(f"\r  [{_color('LOAD', LogStyle.DIM)}] {_color(f'{module} {status}{dots}', color)}", end="", flush=True)

def game_ok(module, msg=""):
    """游戏风格成功"""
    msg_part = f" {_color(msg, LogStyle.DIM)}" if msg else ""
    print(f"\r  [{_color('  OK  ', LogStyle.GREEN)}] {_color(module, LogStyle.WHITE)}{msg_part}")

def game_skip(module, msg=""):
    """游戏风格跳过"""
    msg_part = f" {_color(msg, LogStyle.DIM)}" if msg else ""
    print(f"\r  [{_color(' SKIP ', LogStyle.YELLOW)}] {_color(module, LogStyle.DIM)}{msg_part}")

def game_fail(module, msg=""):
    """游戏风格失败"""
    msg_part = f" {_color(msg, LogStyle.RED)}" if msg else ""
    print(f"\r  [{_color(' FAIL ', LogStyle.RED)}] {_color(module, LogStyle.WHITE)}{msg_part}")

def game_info(module, msg=""):
    """游戏风格信息"""
    msg_part = f" {_color(msg, LogStyle.CYAN)}" if msg else ""
    print(f"  [{_color('INFO', LogStyle.CYAN)}] {_color(module, LogStyle.WHITE)}{msg_part}")

def game_warn(module, msg=""):
    """游戏风格警告"""
    msg_part = f" {_color(msg, LogStyle.YELLOW)}" if msg else ""
    print(f"  [{_color('WARN', LogStyle.YELLOW)}] {_color(module, LogStyle.WHITE)}{msg_part}")

def game_debug(module, msg=""):
    """游戏风格调试"""
    msg_part = f" {_color(msg, LogStyle.DIM)}" if msg else ""
    print(f"  [{_color('DEBUG', LogStyle.DIM)}] {_color(module, LogStyle.DIM)}{msg_part}")

def game_progress(current, total, module=""):
    """游戏风格进度条"""
    bar_len = 30
    filled = int(bar_len * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_len - filled)
    percent = int(100 * current / total) if total > 0 else 0
    module_part = f" {_color(module, LogStyle.CYAN)}" if module else ""
    print(f"\r  [{bar}] {percent:3d}%{module_part}", end="", flush=True)
    if current >= total:
        print()

def game_section(title):
    """游戏风格分节标题"""
    print()
    print(_color(f"  ▸ {title}", LogStyle.MAGENTA))

def game_separator():
    """游戏风格分隔线"""
    print(_color("  " + "─" * 56, LogStyle.DIM))

# 模型目录（静默设置，不打印）
# MODELS_CACHE: {MODELS_CACHE}

# ============ 懒加载模块 ============
# 仅导入启动必需的核心模块，重量级模块（torch、transformers 等）
# 在各子模块内部按需延迟导入，以加速冷启动速度

# 核心工具模块（立即加载 —— 这些是轻量级模块，不会拖慢启动）
from logger_new import get_logger, security_logger  # 日志系统: 提供统一日志记录和安全审计
from utils import validate_path, temp_file, friendly_error  # 工具函数: 路径校验、临时文件、错误格式化
from tts_cache import TTSCache  # TTS 缓存: 避免重复合成相同文本的音频


class Config:
    """
    配置管理器

    设计意图:
        统一管理整个系统的 YAML 配置加载，支持:
        1. 多路径自动探测（打包 exe / 开发模式）
        2. ${VAR} 环境变量自动展开（如 ${MINIMAX_API_KEY}）
        3. 点号分隔的嵌套键访问（如 config.get("llm.minimax.model")）
        4. pyyaml 缺失时的备用硬编码配置

    配置参数:
        config_path: 配置文件路径，默认自动探测

    线程安全:
        本类在初始化后仅做读取，不需要额外同步。如需运行时热更新需加锁。
    """

    def __init__(self, config_path: str = None):
        """
        【功能说明】初始化配置管理器，自动探测并加载配置文件

        【参数说明】
            config_path (str): 可选的自定义配置文件路径，None 则自动探测

        【返回值】
            无
        """
        # 如果调用者没传路径，自动探测默认配置文件位置
        self.config_path = config_path or self._get_default_config_path()
        # 加载并解析 YAML 配置
        self.config = self._load()

    def _get_default_config_path(self) -> str:
        """
        自动探测配置文件路径

        执行流程:
            1. 如果是 PyInstaller 打包后的 exe (sys.frozen=True):
               → 先查 _MEIPASS 临时目录下的 app/config.yaml
               → 再查 exe 同目录的 config.yaml
               → 再查 exe 同目录的 app/config.yaml
            2. 如果是开发模式:
               → 查当前脚本(__file__)同目录的 config.yaml
            3. 都找不到则返回默认路径（同目录 config.yaml，即使不存在）

        返回值:
            str: 配置文件的绝对路径字符串
        """
        # 打包后 exe 所在目录
        if getattr(sys, 'frozen', False):
            # PyInstaller 打包后，_MEIPASS 是解压临时目录
            # _MEIPASS 临时目录下的 app/config.yaml
            config_path = Path(sys._MEIPASS) / "app" / "config.yaml"
            if config_path.exists():
                return str(config_path)

            # exe 同目录
            config_path = Path(sys.executable).parent / "config.yaml"
            if config_path.exists():
                return str(config_path)

            # exe 同目录的 app 子目录
            config_path = Path(sys.executable).parent / "app" / "config.yaml"
            if config_path.exists():
                return str(config_path)
        else:
            # 开发模式: 脚本所在目录
            config_path = Path(__file__).parent / "config.yaml"
            if config_path.exists():
                return str(config_path)

        # 返回默认路径（即使文件不存在，后续 _load() 会处理）
        return str(Path(__file__).parent / "config.yaml")

    def _load(self) -> Dict[str, Any]:
        """
        加载并解析 YAML 配置文件

        执行流程:
            1. 读取文件全部内容为原始字符串
            2. 用正则替换 ${VAR_NAME} → os.environ.get("VAR_NAME")
               （支持在 YAML 值中嵌入环境变量，避免硬编码敏感信息）
            3. 用 yaml.safe_load 解析为 Python 字典
            4. 异常处理: pyyaml 未安装 → 返回备用配置；加载失败 → 返回默认配置

        返回值:
            Dict[str, Any]: 解析后的配置字典
        """
        config_file = Path(self.config_path)

        # 配置文件不存在时使用默认配置
        if not config_file.exists():
            game_warn("配置", f"文件不存在，使用默认配置")
            return self._get_default_config()

        try:
            import yaml
            import re
            # 以 UTF-8 读取原始配置文本
            with open(config_file, "r", encoding="utf-8") as f:
                raw_config = f.read()

            # 展开 ${VAR} 环境变量引用
            # 例如: api_key: ${MINIMAX_API_KEY} → api_key: 实际的 key 值
            # 如果环境变量不存在，保留原始 ${VAR} 字符串不变
            def _expand_env(match):
                """
                【内部函数】展开环境变量占位符 ${VAR}

                【参数说明】
                    match: 正则匹配对象，group(1) 为变量名

                【返回值】
                    str: 环境变量值或原始占位符
                """
                return os.getenv(match.group(1), match.group(0))
            raw_config = re.sub(r'\$\{([^}]+)\}', _expand_env, raw_config)

            # 解析 YAML 为 Python 字典
            config = yaml.safe_load(raw_config)
            
            # API Key管理: 从 app/cache/api_keys.json 加载用户保存的API Key
            # 这些Key由前端API Key面板设置，优先级高于config.yaml中的值
            try:
                cache_dir = Path(self.config_path).parent / "cache"
                keys_file = cache_dir / "api_keys.json"
                if keys_file.exists():
                    with open(keys_file, "r", encoding="utf-8") as kf:
                        saved_keys = json.load(kf)
                    # 将保存的Key覆盖到config中
                    for provider_name, key_value in saved_keys.items():
                        # LLM: llm.{provider}.api_key
                        llm_provider = config.setdefault("llm", {}).setdefault(provider_name, {})
                        if key_value:
                            llm_provider["api_key"] = key_value
                        # Vision: vision.minimax_vl.api_key (仅minimax)
                        if provider_name == "minimax":
                            vision_minimax = config.setdefault("vision", {}).setdefault("minimax_vl", {})
                            if key_value:
                                vision_minimax["api_key"] = key_value
                    print(f"[Config] 从 api_keys.json 加载了 {len(saved_keys)} 个API Key")
            except Exception as e:
                print(f"[Config] 加载 api_keys.json 失败(不影响使用): {e}")

            # LLM 偏好持久化: 从 app/cache/llm_preferences.json 加载用户上次选择的 LLM 配置
            # 优先级: llm_preferences.json > config.yaml
            # 这样用户切换 LLM provider 后，重启应用仍保持上次的配置
            try:
                prefs_file = cache_dir / "llm_preferences.json"
                if prefs_file.exists():
                    with open(prefs_file, "r", encoding="utf-8") as pf:
                        llm_prefs = json.load(pf)
                    llm_cfg = config.setdefault("llm", {})
                    # 恢复 provider
                    if "provider" in llm_prefs:
                        llm_cfg["provider"] = llm_prefs["provider"]
                        print(f"[Config] 恢复 LLM provider: {llm_prefs['provider']}")
                    # 恢复 model（如果有）
                    if "model" in llm_prefs:
                        llm_cfg["model"] = llm_prefs["model"]
                    # 恢复 max_tokens（如果有）
                    if "max_tokens" in llm_prefs:
                        llm_cfg["max_tokens"] = llm_prefs["max_tokens"]
                    # 恢复各 provider 的 base_url（Ollama 等自定义 URL）
                    if "provider_configs" in llm_prefs:
                        for pname, pcfg in llm_prefs["provider_configs"].items():
                            existing_sub = llm_cfg.setdefault(pname, {})
                            if "base_url" in pcfg:
                                existing_sub["base_url"] = pcfg["base_url"]
                            if "model" in pcfg:
                                existing_sub["model"] = pcfg["model"]
                    print(f"[Config] 从 llm_preferences.json 恢复了 LLM 配置")
            except Exception as e:
                print(f"[Config] 加载 llm_preferences.json 失败(不影响使用): {e}")

            return config
        except ImportError:
            # pyyaml 未安装，返回一个包含常用默认值的硬编码备用配置
            game_warn("配置", "pyyaml未安装，使用备用配置")
            return {
                "asr": {"provider": "faster_whisper", "faster_whisper": {"model_size": "base", "device": "cuda"}},
                "tts": {"provider": "edge", "edge": {"voice": "zh-CN-XiaoxiaoNeural"}},
                "llm": {"provider": "minimax", "minimax": {"api_key": os.getenv("MINIMAX_API_KEY", ""), "base_url": os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic"), "model": "MiniMax-M2.5"}},
                "live2d": {"enabled": False},
                "voice": {"enabled": True},
                "dialogue": {"max_history": 10},
                "execution": {"enabled": True, "allowed_commands": ["ls", "pwd", "date", "echo", "whoami"]},
                "web": {"port": 12393, "ws_port": 12394}
            }
        except Exception as e:
            game_fail("配置加载", str(e))
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取最小化的默认配置

        设计意图:
            当配置文件不存在或加载失败时提供一个可运行的兜底配置。
            只包含最基本的开关和默认值，不包含详细的 provider 配置。

        返回值:
            Dict[str, Any]: 默认配置字典
        """
        return {
            "asr": {"provider": "faster_whisper"},
            "tts": {"provider": "edge"},
            "llm": {"provider": "minimax"},
            "live2d": {"enabled": False},
            "voice": {"enabled": True},
            "dialogue": {"max_history": 10},
            "execution": {"enabled": True},
            "web": {"port": 12393, "ws_port": 12394}
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        按点号分隔路径获取嵌套配置值

        参数说明:
            key: 配置键路径，如 "llm.minimax.model" → config["llm"]["minimax"]["model"]
            default: 键不存在时的默认返回值

        返回值:
            Any: 配置值，或 default（键不存在 / 值为 None 时）

        示例:
            config.get("web.port", 12393) → 12393
            config.get("llm.minimax.api_key") → "sk-xxx"
        """
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        # 值为 None 也返回 default（避免 YAML 中的 null 误判为有效值）
        return value if value is not None else default


class ToolExecutor:
    """
    命令执行器 - 安全沙箱

    设计意图:
        为 LLM 提供受限的系统命令执行能力。通过白名单 + 黑名单双重过滤，
        防止 LLM 生成的命令对系统造成破坏。

    配置参数:
        execution.enabled: 是否启用命令执行（默认 True）
        execution.allowed_commands: 白名单命令列表（如 ["ls", "pwd", "date"]）
        execution.timeout: 命令超时时间（秒，默认 30）

    安全机制:
        1. 白名单校验: 如果配置了 allowed_commands，仅允许列表内的命令
        2. 黑名单校验: 精确匹配危险命令名（rm/dd/shutdown 等）
        3. Shell 操作符检测: 拒绝包含 > < | & ; ` $ 的原始命令字符串
        4. shlex.split: 安全解析命令参数，避免 shell=True 的注入风险
        5. ThreadPoolExecutor: 命令在线程池中异步执行，避免阻塞主线程

    线程安全:
        内部使用 ThreadPoolExecutor(max_workers=3)，可安全并发调用 execute()。
    """

    def __init__(self, config: Dict[str, Any]):
        """
        【功能说明】初始化命令执行器

        【参数说明】
            config (Dict[str, Any]): 配置字典，读取 execution 字段

        【返回值】
            无
        """
        # 从配置中读取 execution 段
        self.config = config.get("execution", {})
        self.enabled = self.config.get("enabled", True)
        # 白名单: 只有列表中的命令才允许执行（空列表=不过滤）
        self.allowed_commands = self.config.get("allowed_commands", [])
        self.timeout = self.config.get("timeout", 30)

        # 使用线程池执行命令，避免阻塞主线程（最多 3 个并发命令）
        from concurrent.futures import ThreadPoolExecutor
        self._executor = ThreadPoolExecutor(max_workers=3)

    def can_execute(self, command: str) -> bool:
        """
        【功能说明】检查命令是否允许执行

        【参数说明】
            command (str): 用户/LLM 提交的完整命令字符串

        【返回值】
            bool: True=允许执行, False=拒绝

        【执行流程】
            1. 如果执行器被禁用 → 拒绝
            2. 用 shlex.split 安全解析命令，解析失败 → 拒绝
            3. 空命令 → 拒绝
            4. 白名单校验: 如果配置了白名单，命令名必须在列表中
            5. 黑名单校验: 命令名不能是危险命令
            6. Shell 操作符检测: 原始字符串不能包含管道/重定向等操作符
        """
        if not self.enabled:
            return False

        import shlex
        try:
            # shlex.split: 正确处理引号和转义，避免简单 split 的安全问题
            parts = shlex.split(command) if command.strip() else []
        except ValueError:
            return False  # 解析失败（如不匹配的引号），拒绝执行

        if not parts:
            return False

        # 提取命令名（第一个 token）
        cmd_name = parts[0]

        # 白名单校验（如果配置了允许列表）
        if self.allowed_commands and cmd_name not in self.allowed_commands:
            return False

        # 危险命令黑名单：精确匹配命令名 token
        # 设计说明: 使用 set 精确匹配而非 "rm" in command，
        # 避免 "grep rm ..." 这种合法场景被误杀
        _BLOCKLIST = {"rm", "dd", "mkfs", "shutdown", "reboot", "init",
                      "chmod", "chown", "kill", "pkill", "curl", "wget",
                      "nc", "ncat", "bash", "sh", "python", "python3",
                      "perl", "ruby", "node", "sudo", "su"}
        # 同时拒绝包含 shell 操作符的原始字符串
        # （防止 shlex 解析后丢失语义，如 "ls; rm -rf /" 被拆成 ["ls"] 和 ["rm"]）
        _SHELL_CHARS = {">", "<", "|", "&", ";", "`", "$"}
        if any(c in command for c in _SHELL_CHARS):
            return False
        if cmd_name in _BLOCKLIST:
            return False

        return True

    def execute(self, command: str) -> Dict[str, Any]:
        """
        使用线程池异步执行命令

        参数说明:
            command: 要执行的命令字符串

        返回值:
            Dict: {"success": bool, "stdout": str, "stderr": str} 或 {"success": False, "error": str}

        执行流程:
            1. can_execute() 安全校验 → 不通过则返回错误
            2. shlex.split 安全解析命令
            3. 提交到 ThreadPoolExecutor 执行 subprocess.run(shell=False)
            4. 等待结果并返回 stdout/stderr

        安全说明:
            shell=False + shlex.split: 不经过 shell 解释器，直接 execvp，
            从根本上杜绝 shell 注入攻击。
        """
        if not self.can_execute(command):
            return {"success": False, "error": f"命令不允许执行: {command}"}

        try:
            import subprocess
            import shlex

            # 安全拆分命令为参数列表（不经过 shell 解释）
            cmd_parts = shlex.split(command) if command else []

            # v1.9.60: 桌面模式下隐藏 CMD 窗口
            win_args = _win_subprocess_args()

            # 提交到线程池执行，避免阻塞调用线程
            future = self._executor.submit(
                subprocess.run,
                cmd_parts,            # 参数列表（非字符串）
                shell=False,          # 关键: 不经过 shell，防止注入
                capture_output=True,  # 捕获 stdout 和 stderr
                text=True,            # 以文本模式返回（非 bytes）
                timeout=self.timeout, # 超时秒数
                **win_args            # v1.9.60: 桌面模式隐藏 CMD
            )

            # 阻塞等待线程池中的执行结果
            result = future.result()

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def shutdown(self):
        """
        安全关闭线程池

        设计意图:
            在程序退出时调用，等待所有正在执行的命令完成后关闭线程池。
            wait=True 确保不会丢失正在执行的命令输出。
        """
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=True)

    def parse_action(self, text: str) -> Optional[Dict[str, Any]]:
        """
        从 LLM 回复文本中解析工具调用指令

        设计意图:
            兼容旧版 LLM 通过自然语言嵌入指令的方式（如 "ACTION: execute\nCOMMAND: ls"）。
            新版使用 function calling，但保留此方法以兼容旧 provider。

        参数说明:
            text: LLM 回复的完整文本

        返回值:
            Dict: {"type": "execute", "command": "ls"} 或 None（无匹配时）
        """
        import re
        if "ACTION: execute" in text or "COMMAND:" in text:
            # 用正则匹配 COMMAND: 后面的命令内容（到换行或结尾）
            match = re.search(r"COMMAND:\s*(.+?)(?:\n|$)", text, re.DOTALL)
            if match:
                return {"type": "execute", "command": match.group(1).strip()}
        return None


class AIVTuber:
    """
    AI 虚拟形象主程序 - 全系统协调器（懒加载架构）

    设计意图:
        作为 AI VTuber 系统的统一门面(Facade)，组合管理所有子模块:
        ASR（语音识别）、TTS（语音合成）、LLM（大语言模型）、
        Vision（视觉理解）、Memory（记忆系统）、Live2D（虚拟形象）、
        Voice（语音输入）、Web/WebSocket（网络服务）、
        Tools（本地工具）。
        核心设计: 懒加载(Lazy Loading)
        - __init__ 只初始化轻量级对象（Config、TTSCache、Logger）
        - 所有重量级模块通过 @property 延迟到首次访问时才加载
        - 启动时间从 30+ 秒缩短到 1-2 秒

    配置参数:
        config_path: 可选的自定义配置文件路径

    主要对外接口:
        process_message(text) → 文字对话: 输入文字 → 记忆检索 → LLM 推理 → 工具执行 → 返回回复
        process_audio(audio_path) → 语音对话: 输入音频 → ASR 识别 → process_message → TTS 合成
        process_audio_data(base64_data) → Web 端语音: Base64 解码 → process_audio
        speak(text) → TTS 合成（带缓存和打断）
        run_web() → 启动 HTTP + WebSocket 服务
        run_interactive() → 启动命令行交互模式
        stop() → 停止所有服务并释放资源

    线程安全:
        process_message() 本身非线程安全（self.history 无锁），
        Web 模式下由 web 模块的消息队列保证串行处理。
    """

    def __init__(self, config_path: str = None):
        """
        【功能说明】初始化咕咕嘎嘎主应用（懒加载模式）

        【参数说明】
            config_path (str, optional): 配置文件路径

        【返回值】
            无
        """
        # 加载配置
        # M3修复: 配置加载失败时给用户友好提示而非直接崩溃
        try:
            self.config = Config(config_path)
        except FileNotFoundError:
            print("\n" + "="*50)
            print("  错误: 配置文件不存在!")
            print(f"  路径: {config_path or 'app/config.yaml'}")
            print("  请确认配置文件存在，或使用 --config 指定路径")
            print("="*50)
            sys.exit(1)
        except Exception as e:
            print("\n" + "="*50)
            print("  错误: 配置文件加载失败!")
            print(f"  原因: {e}")
            print("  请检查 config.yaml 格式是否正确")
            print("="*50)
            sys.exit(1)

        # 初始化日志
        self.logger = get_logger("main")
        self.logger.info("初始化咕咕嘎嘎 AI虚拟形象（懒加载模式）")

        game_section("核心模块")
        game_ok("配置管理器", f"已加载 {Path(self.config.config_path).name}")

        # 命令执行器 - 延迟初始化（通过 @property executor）
        self._executor = None
        self._executor_initialized = False

        # 记忆系统 - 延迟初始化（通过 @property memory）
        self._memory = None
        self._memory_initialized = False

        # TTS 缓存 - 立即初始化（轻量级，仅做文件缓存管理）
        self.tts_cache = TTSCache()
        self.logger.info("TTS 缓存已初始化")
        game_ok("TTS缓存", "音频文件缓存已就绪")

        # 历史记录限制: 最多保留 MAX_HISTORY 轮对话（每轮 = user + assistant 两条）
        self.MAX_HISTORY = 100
        self.history: List[Dict] = []
        self._history_needs_restore = False  # v1.9.50: 延迟从记忆系统恢复标记
        # v1.9.50: 对话历史持久化文件路径
        self._history_file = Path("./memory/state/chat_history.json").resolve()
        self._history_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_history()

        # 懒加载模块注册表: 存储已加载的模块实例
        # key = 模块名, value = 模块实例
        self._lazy_modules = {}

        print("\n" + "="*50)
        game_separator()
        game_info("系统初始化完成", "模块将在首次使用时懒加载")
        game_header("就绪")
        print("="*50)
        
        # 注册 atexit 回调：确保异常退出时也能 flush 记忆系统
        atexit.register(self._atexit_flush)
        
        # M1修复: 注册信号处理，确保SIGTERM/SIGINT时优雅关停
        import signal
        signal.signal(signal.SIGINT, self._signal_handler)
        try:
            signal.signal(signal.SIGTERM, self._signal_handler)
        except (OSError, ValueError):
            pass  # Windows 可能不支持 SIGTERM

    # ============ 懒加载属性 ============
    # 每个属性在首次访问时才导入并初始化对应的模块
    # 后续访问直接返回缓存的实例（_lazy_modules dict 查找 O(1)）

    @property
    def asr(self):
        """
        语音识别模块 (ASR) - 懒加载

        延迟导入: from asr import ASRFactory
        配置来源: config["asr"]
        可能的实例: FasterWhisperASR / FunASRASR / WhisperASR

        返回值:
            ASREngine 实例（支持 recognize(audio_path) 方法）
        """
        if 'asr' not in self._lazy_modules:
            game_section("加载语音识别模块")
            game_progress(1, 4, "ASR")
            from asr import ASRFactory
            asr_config = self.config.config.get("asr", {})
            self._lazy_modules['asr'] = ASRFactory.create(asr_config)
            if self._lazy_modules['asr'].is_available():
                game_ok(f"ASR [{type(self._lazy_modules['asr']).__name__}]", "就绪")
            else:
                game_skip(f"ASR [{type(self._lazy_modules['asr']).__name__}]", "需安装依赖")
        return self._lazy_modules['asr']

    @property
    def tts(self):
        """
        语音合成模块 (TTS) - 懒加载

        延迟导入: from tts import TTSFactory
        配置来源: config["tts"]
        可能的实例: EdgeTTS / GPTSoVITSTTS / 其他 TTS 引擎

        返回值:
            TTSEngine 实例（支持 speak(text) 和 stop() 方法）
        """
        if 'tts' not in self._lazy_modules:
            game_section("加载语音合成模块")
            game_progress(2, 4, "TTS")
            from tts import TTSFactory
            tts_config = self.config.config.get("tts", {})
            self._lazy_modules['tts'] = TTSFactory.create(tts_config)
            if self._lazy_modules['tts'].is_available():
                game_ok(f"TTS [{type(self._lazy_modules['tts']).__name__}]", "就绪")
            else:
                game_skip(f"TTS [{type(self._lazy_modules['tts']).__name__}]", "需安装依赖")
        return self._lazy_modules['tts']

    @property
    def trainer(self):
        """
        GPT-SoVITS 声音训练管理器 - 懒加载

        延迟导入: from trainer.manager import TrainingManager
        功能: 列出/管理/启动 GPT-SoVITS 训练项目
        原生桌面模式的训练页依赖此属性

        返回值:
            TrainingManager 实例
        """
        if 'trainer' not in self._lazy_modules:
            from trainer.manager import TrainingManager
            self._lazy_modules['trainer'] = TrainingManager()
        return self._lazy_modules['trainer']

    @property
    def llm(self):
        """
        大语言模型模块 (LLM) - 懒加载

        延迟导入: from llm import LLMFactory
        配置来源: config["llm"]
        可能的实例: MiniMaxLLM / OpenAILLM / AnthropicLLM

        返回值:
            LLM 实例（支持 chat(prompt, history) 方法）
        """
        if 'llm' not in self._lazy_modules:
            game_section("加载大语言模型")
            game_progress(3, 4, "LLM")
            from llm import LLMFactory
            llm_config = self.config.config.get("llm", {})
            self._lazy_modules['llm'] = LLMFactory.create(llm_config)
            if self._lazy_modules['llm'].is_available():
                game_ok(f"LLM [{self._lazy_modules['llm'].name}]", "就绪")
            else:
                game_skip(f"LLM [{self._lazy_modules['llm'].name}]", "需配置API")
        return self._lazy_modules['llm']

    @property
    def live2d(self):
        """
        Live2D 虚拟形象模块 - 懒加载

        延迟导入: from live2d import Live2DModel
        配置来源: config["live2d"]

        返回值:
            Live2DModel 实例（支持 enabled, port, start_server() 属性/方法）
        """
        if 'live2d' not in self._lazy_modules:
            from live2d import Live2DModel
            live2d_config = self.config.config.get("live2d", {})
            self._lazy_modules['live2d'] = Live2DModel(live2d_config)
            if self._lazy_modules['live2d'].enabled:
                if self._lazy_modules['live2d'].is_available():
                    game_ok("Live2D 虚拟形象", "模型已加载")
                else:
                    game_skip("Live2D 虚拟形象", "需放置模型文件")
            else:
                game_skip("Live2D 虚拟形象", "未启用")
        return self._lazy_modules['live2d']

    @property
    def voice(self):
        """
        本地语音输入模块 - 懒加载

        延迟导入: from voice import VoiceInputFactory
        配置来源: config["voice"]
        use_web=False: 使用 sounddevice 本地麦克风录音

        返回值:
            VoiceInput 实例（支持 start()/stop() 录音方法）
        """
        if 'voice' not in self._lazy_modules:
            from voice import VoiceInputFactory
            voice_config = self.config.config.get("voice", {})
            self._lazy_modules['voice'] = VoiceInputFactory.create(voice_config, use_web=False)
            if self._lazy_modules['voice'].is_available():
                game_ok("本地语音输入", "麦克风可用")
            else:
                game_skip("本地语音输入", "需安装sounddevice")
        return self._lazy_modules['voice']

    @property
    def voice_web(self):
        """
        Web 语音输入模块 - 懒加载

        延迟导入: from voice import VoiceInputFactory
        配置来源: config["voice"]
        use_web=True: 使用浏览器 MediaRecorder API 通过 WebSocket 传输音频

        返回值:
            WebVoiceInput 实例（提供 HTML/JS 嵌入代码和 Base64 解码）
        """
        if 'voice_web' not in self._lazy_modules:
            from voice import VoiceInputFactory
            voice_config = self.config.config.get("voice", {})
            self._lazy_modules['voice_web'] = VoiceInputFactory.create(voice_config, use_web=True)
            game_ok("Web语音输入", "浏览器录音就绪")
        return self._lazy_modules['voice_web']

    @property
    def executor(self):
        """
        命令执行器 (ToolExecutor) - 懒加载

        设计说明: 使用独立的 _executor_initialized 标志而非 _lazy_modules，
        因为 ToolExecutor 初始化逻辑与其他模块不同（不是通过 Factory 创建）

        返回值:
            ToolExecutor 实例（支持 can_execute()/execute() 方法）
        """
        if not self._executor_initialized:
            game_section("加载命令执行器")
            self._executor = ToolExecutor(self.config.config)
            self._executor_initialized = True
            if self._executor.enabled:
                game_ok("命令执行器", "工具沙箱已启用")
            else:
                game_skip("命令执行器", "已禁用")
        return self._executor

    @property
    def memory(self):
        """
        记忆系统模块 - 懒加载

        延迟导入: from memory import MemorySystem
        配置来源: config["memory"]

        功能: 短期对话记忆 + 长期向量检索记忆
        - add_interaction(): 添加对话记录
        - search(): 按语义检索相关记忆
        - auto_store: 是否自动存储重要对话到长期记忆

        返回值:
            MemorySystem 实例 或 None（初始化失败时）
        """
        if not self._memory_initialized:
            game_section("加载记忆系统")
            try:
                from memory import MemorySystem
                memory_config = self.config.config.get("memory", {})
                self._memory = MemorySystem(memory_config)
                self._memory_initialized = True
                # v1.9.50: 如果历史还没恢复，尝试从记忆系统恢复
                if getattr(self, '_history_needs_restore', False) and not self.history:
                    self._load_history()
                    self._history_needs_restore = False
                # v3.0: 设置 LLM 回调（延迟绑定，避免循环依赖）
                # 使用 lambda 延迟访问 self.llm，确保 LLM 已初始化
                self._memory.set_llm_callback(lambda message: self.llm.chat(message=message) if getattr(self, '_llm', None) else None)
                game_ok("记忆系统", "v3.0 四层架构已就绪 (工作/情景/语义/事实)")
            except Exception as e:
                # 关键修复：记忆系统初始化失败时记录错误，不阻塞整个应用
                self._memory = None
                self._memory_initialized = True  # 标记为已初始化（避免反复重试导致性能问题）
                game_fail("记忆系统", f"初始化失败: {e}")
                self.logger.error(f"记忆系统初始化失败: {e}", exc_info=True)
                print(f"[CRITICAL] 记忆系统初始化失败: {type(e).__name__}: {e}")
                # 打印完整堆栈帮助调试
                import traceback
                traceback.print_exc()
        return self._memory

    @property
    def tools(self):
        """
        本地工具系统 - 懒加载

        延迟导入: from tools import ToolFactory
        无需额外配置（工具列表硬编码在 ToolFactory 中）

        功能: 类似 Claude Code 的本地工具（读文件、写文件、Bash 命令等）
        支持 9 种工具: Read/Write/Edit/Glob/Grep/LS/Bash/Think/Architect

        返回值:
            ToolFactory 类本身（通过 ToolFactory.execute(name, **kwargs) 调用）
        """
        if 'tools' not in self._lazy_modules:
            from tools import ToolFactory
            self._lazy_modules['tools'] = ToolFactory
            tool_count = len(ToolFactory.list_tools())
            game_ok(f"本地工具系统", f"{tool_count} 种工具就绪")
        return self._lazy_modules['tools']

    @property
    def vision(self):
        """
        视觉理解系统 - 懒加载

        延迟导入: from vision import VisionManager
        配置来源: config["vision"]

        功能: 多 Provider 视觉理解（RapidOCR / MiniMax VL / MiniCPM）
        - recognize_text(): OCR 文字识别
        - understand(): 图像内容理解
        - set_provider(): 动态切换视觉 Provider

        返回值:
            VisionManager 实例
        """
        if 'vision' not in self._lazy_modules:
            from vision import VisionManager
            vision_config = self.config.config.get("vision", {})
            self._lazy_modules['vision'] = VisionManager(vision_config)
            game_ok(f"视觉理解", self._lazy_modules['vision'].current_provider_description)
        return self._lazy_modules['vision']

    @property
    def proactive(self):
        """
        AI 主动说话管理器 - 懒加载

        延迟导入: from proactive import ProactiveSpeechManager
        配置来源: config["proactive_speech"]

        功能: 当用户长时间不说话时，AI 根据记忆和上下文主动开口
        - 空闲检测: 追踪 last_user_activity_time
        - 上下文感知: 利用记忆系统检索话题
        - 频率控制: 最小间隔 + 每日上限

        返回值:
            ProactiveSpeechManager 实例
        """
        if 'proactive' not in self._lazy_modules:
            try:
                from proactive import ProactiveSpeechManager
                self._lazy_modules['proactive'] = ProactiveSpeechManager(self)
                if self._lazy_modules['proactive'].enabled:
                    game_ok("主动说话", f"空闲 {self._lazy_modules['proactive'].idle_timeout}s 后触发")
                else:
                    game_skip("主动说话", "未启用 (config.yaml → proactive_speech.enabled)")
            except Exception as e:
                self._lazy_modules['proactive'] = None
                game_fail("主动说话", f"初始化失败: {e}")
        return self._lazy_modules['proactive']

    @property
    def mcp(self):
        """
        MCP 工具桥接器 - 懒加载

        延迟导入: from mcp import MCPToolBridge
        配置来源: config["mcp"]

        功能: 将 MCP (Model Context Protocol) 工具集成到本地工具系统
        - 管理多个 MCP 服务器连接
        - 工具名路由: "MCP:server:tool" → MCP 通道，其他 → 本地工具
        - 动态添加/移除 MCP 服务器

        返回值:
            MCPToolBridge 实例 或 None（未启用时）
        """
        if 'mcp' not in self._lazy_modules:
            try:
                from mcp import MCPToolBridge
                mcp_config = self.config.config.get("mcp", {})
                if mcp_config.get("enabled", False):
                    self._lazy_modules['mcp'] = MCPToolBridge(self)
                    self._lazy_modules['mcp'].start()
                    server_count = self._lazy_modules['mcp'].server_count
                    connected = self._lazy_modules['mcp'].connected_count
                    game_ok("MCP工具桥接", f"{connected}/{server_count} 个服务器已连接")
                else:
                    self._lazy_modules['mcp'] = None
                    game_skip("MCP工具桥接", "未启用 (config.yaml → mcp.enabled)")
            except Exception as e:
                self._lazy_modules['mcp'] = None
                game_fail("MCP工具桥接", f"初始化失败: {e}")
        return self._lazy_modules['mcp']

    @property
    def desktop_pet(self):
        """
        桌面宠物管理器 - 懒加载

        延迟导入: from desktop_pet import DesktopPetManager
        配置来源: config["desktop_pet"]

        功能: 将 Live2D 角色以桌面宠物的形式悬浮在桌面上
        - 无边框透明窗口，始终置顶
        - 可拖拽移动，点击交互
        - 右键菜单：打开主界面/打招呼/随机动作/退出

        返回值:
            DesktopPetManager 实例 或 None（未启用时）
        """
        if 'desktop_pet' not in self._lazy_modules:
            try:
                from desktop_pet import DesktopPetManager
                pet_config = self.config.config.get("desktop_pet", {})
                if pet_config.get("enabled", False):
                    self._lazy_modules['desktop_pet'] = DesktopPetManager(self)
                    game_ok("桌面宠物", "已就绪")
                else:
                    self._lazy_modules['desktop_pet'] = None
                    game_skip("桌面宠物", "未启用 (config.yaml → desktop_pet.enabled)")
            except Exception as e:
                self._lazy_modules['desktop_pet'] = None
                game_fail("桌面宠物", f"初始化失败: {e}")
        return self._lazy_modules['desktop_pet']

    @property
    def web_server(self):
        """
        Web HTTP 服务器 - 懒加载

        延迟导入: import web as web_module
        依赖: config["web"]

        功能: 提供 HTTP 服务（前端页面 + REST API）

        返回值:
            WebServer 实例（支持 start()/stop() 方法）
        """
        if 'web_server' not in self._lazy_modules:
            game_section("启动 Web 服务")
            game_progress(1, 2, "HTTP Server")
            import web as web_module
            WebServer = getattr(web_module, 'WebServer', None)
            self._lazy_modules['web_server'] = WebServer(self.config.config, app=self)
            game_progress(2, 2, "WebServer")
            game_ok("Web HTTP 服务", f"端口 {self.config.config.get('web.port', 12393)}")
        return self._lazy_modules['web_server']

    @property
    def ws_server(self):
        """
        WebSocket 服务器 - 懒加载

        延迟导入: import web as web_module
        依赖: config["web"]

        功能: 提供 WebSocket 实时通信（音频传输、状态推送等）

        返回值:
            WebSocketServer 实例（支持 start()/stop() 方法）
        """
        if 'ws_server' not in self._lazy_modules:
            game_progress(1, 1, "WebSocket")
            import web as web_module
            WebSocketServer = getattr(web_module, 'WebSocketServer', None)
            self._lazy_modules['ws_server'] = WebSocketServer(self.config.config, self)
            game_ok("WebSocket 服务", "实时通道已建立")
        return self._lazy_modules['ws_server']

    def __enter__(self):
        """上下文管理器入口 - 支持 with 语句自动资源管理"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器退出

        设计意图: 确保 with 块结束时（无论正常还是异常）调用 stop() 清理资源。
        返回 False 表示不吞掉异常。
        """
        self.logger.info("清理资源...")
        self.stop()
        return False

    def process_message(self, text: str) -> Dict[str, Any]:
        """
        处理文字消息 - 核心对话流程

        这是整个系统最核心的方法，串联了:
        记忆检索 → LLM 推理 → 工具执行(命令/本地工具) → 记忆存储

        参数说明:
            text: 用户输入的文字消息

        返回值:
            Dict: {"text": str, "action": dict|None}
            - text: LLM 回复文本（可能包含工具执行结果的拼接）
            - action: 解析出的工具调用指令（如果有）

        执行流程:
            1. 短期记忆: 记录用户消息
            2. 长期记忆: 按语义检索 top-3 相关记忆
            3. 构建 prompt: 用户问题 + 记忆上下文
            4. LLM 推理: 调用 self.llm.chat()（传入 history 副本，防止 LLM 内部修改）
            5. 工具执行链:
               a. execute 命令: 如果 action.type == "execute" → ToolExecutor.execute()
               b. 本地工具: 如果回复包含 "BASH:/READ:/WRITE:/EDIT:" → _handle_local_tool()
            6. 短期记忆: 记录助手回复
            7. 长期记忆: 自动存储重要对话（如果 auto_store 开启）
            8. 历史记录: 追加到 self.history 并限制最大长度

        异常处理:
            FileNotFoundError / PermissionError / TimeoutError → 返回友好错误消息
            其他异常 → 返回 "抱歉，处理消息时出错了喵~"
        """
        try:
            self.logger.info(f"处理消息: {text[:50]}...")

            # 步骤1: 从长期记忆检索与当前输入语义相关的历史记忆
            relevant_memories = self.memory.search(text, top_k=3)
            context = ""
            if relevant_memories:
                # 兼容 content 和 text 两种字段名（不同版本/后端返回的字段可能不同）
                context = "\n\n相关记忆:\n" + "\n".join([m.get("content") or m.get("text", "") for m in relevant_memories])

            # 步骤3: 将检索到的记忆上下文拼接到用户问题后面
            full_prompt = text
            if context:
                full_prompt = f"用户问题: {text}{context}"

            # 步骤4: 调用 LLM 进行推理
            # 传入 history 的列表副本（list(self.history)），确保 LLM 内部不会修改原始历史
            result = self.llm.chat(full_prompt, list(self.history))
            reply = result.get("text", "")
            action = result.get("action")

            # 步骤5a: 处理执行动作（LLM 返回的 action 指令）
            if action and action.get("type") == "execute":
                cmd = action.get("command", "")
                self.logger.info(f"执行命令: {cmd}")
                exec_result = self.executor.execute(cmd)

                if exec_result["success"]:
                    output = exec_result.get("stdout", "") or exec_result.get("stderr", "")
                    reply = f"命令执行完成！\n{output}"
                else:
                    reply = f"命令执行失败: {exec_result.get('error', '未知错误')}"

            # 步骤5b: 处理本地工具调用（参考 Claude Code 的工具调用格式）
            # 支持 BASH/READ/WRITE/EDIT 四种指令
            if "BASH:" in reply or "READ:" in reply or "WRITE:" in reply or "EDIT:" in reply:
                tool_result = self._handle_local_tool(reply)
                if tool_result:
                    reply = f"{reply}\n\n 本地工具结果:\n{tool_result}"

            # 步骤6+7: 统一记录交互（v1.9.55: 替换重复的 mem + history + save 逻辑）
            self.record_interaction(text, reply)

            return {"text": reply, "action": action}

        except FileNotFoundError as e:
            self.logger.error(f"文件不存在: {e}")
            return {"text": friendly_error(e), "action": None}
        except PermissionError as e:
            self.logger.error(f"权限不足: {e}")
            return {"text": friendly_error(e), "action": None}
        except TimeoutError as e:
            self.logger.error(f"操作超时: {e}")
            return {"text": friendly_error(e), "action": None}
        except Exception as e:
            self.logger.exception(f"处理消息错误: {e}")
            # v1.9.31: 更具体的错误消息 + 操作建议
            err_name = type(e).__name__
            err_msg = str(e)
            # 常见错误的针对性提示
            if 'api_key' in err_msg.lower() or 'apikey' in err_msg.lower() or 'unauthorized' in err_msg.lower():
                user_msg = "API Key 无效或已过期，请在设置中重新配置"
            elif 'rate_limit' in err_msg.lower() or 'too many' in err_msg.lower():
                user_msg = "请求太频繁了，请稍等片刻再试"
            elif 'connection' in err_msg.lower() or 'timeout' in err_msg.lower():
                user_msg = "网络连接异常，请检查网络后重试"
            elif 'memory' in err_msg.lower() or 'cuda' in err_msg.lower() or 'out of memory' in err_msg.lower():
                user_msg = "显存不足，请尝试重启或减少其他GPU程序"
            else:
                user_msg = f"处理消息时出错（{err_name}），请查看日志获取详情"
            return {"text": user_msg, "action": None}

    def process_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        处理音频文件 - 完整的语音对话管线

        执行流程: 音频文件 → ASR 语音识别 → process_message 文字处理 → TTS 语音合成

        参数说明:
            audio_path: 音频文件的本地路径（WAV/MP3/WEBM 等格式）

        返回值:
            Dict: {"text": str, "audio": str}
            - text: LLM 回复文字
            - audio: TTS 生成的音频文件路径（可能为 None）
        """
        # ASR: 将音频转为文字
        text = self.asr.recognize(audio_path)
        if not text:
            return {"text": "抱歉，我没有听清楚"}

        # LLM: 文字推理
        result = self.process_message(text)

        # TTS: 将回复文字合成为语音
        output_audio_path = self.tts.speak(result["text"])

        return {
            "text": result["text"],
            "audio": output_audio_path
        }

    def process_audio_data(self, audio_data: str) -> Optional[Dict[str, Any]]:
        """
        处理 Web 端音频数据 - Base64 解码 + 完整语音管线

        设计意图:
            接收前端通过 WebSocket 发来的 Base64 编码音频数据，
            解码后写入临时文件，再走 process_audio() 管线。

        参数说明:
            audio_data: Base64 编码的音频数据
                       可能包含 data URI 前缀（如 "data:audio/webm;base64,..."）

        返回值:
            Dict 或 None: process_audio 的返回值，解码失败时返回 None

        执行流程:
            1. 去除 data URI 前缀（逗号前的部分）
            2. Base64 解码为原始音频字节
            3. 写入临时 .webm 文件（使用 temp_file 上下文管理器自动清理）
            4. 调用 process_audio() 处理

        异常处理:
            Base64 解码失败、文件操作失败等 → 记录日志并返回 None
        """
        try:
            # 去除 data URI 前缀（如 "data:audio/webm;base64,UklGRiQAAABX..."）
            if "," in audio_data:
                audio_data = audio_data.split(",")[1]

            # Base64 解码为原始音频字节
            audio_bytes = base64.b64decode(audio_data)

            # 使用上下文管理器创建临时文件（退出 with 块后自动删除）
            with temp_file(suffix=".webm") as temp_path:
                # 写入临时文件
                with open(temp_path, 'wb') as f:
                    f.write(audio_bytes)

                # 走标准音频处理管线: ASR → LLM → TTS
                result = self.process_audio(temp_path)
                return result

        except base64.binascii.Error as e:
            self.logger.error(f"Base64 解码失败: {e}")
            return None
        except OSError as e:
            self.logger.error(f"文件操作失败: {e}")
            return None
        except Exception as e:
            self.logger.exception(f"处理音频错误: {e}")
            return None

    def speak(self, text: str) -> Optional[str]:
        """
        语音合成 - 带缓存和打断功能

        设计意图:
            对 TTS 合成的封装，增加了两个优化:
            1. 缓存: 相同文本 + 相同音色 → 直接返回缓存的音频文件
            2. 打断: 先调用 tts.stop() 停止当前正在播放的音频

        参数说明:
            text: 要合成的文本

        返回值:
            str: 音频文件路径，或 None（合成失败时）
        """
        try:
            # 先停止当前正在播放的音频（实现"打断"效果）
            self.tts.stop()
        except Exception as e:
            self.logger.warning(f"停止播放失败: {e}")

        # 检查 TTS 缓存: 以 (text, voice, provider) 为 key
        voice = getattr(self.tts, 'voice', 'default')
        provider = type(self.tts).__name__

        cached_audio = self.tts_cache.get(text, voice, provider)
        if cached_audio:
            self.logger.debug(f"使用缓存音频: {text[:30]}...")
            return cached_audio

        # 缓存未命中 → 调用 TTS 引擎生成新音频
        audio_path = self.tts.speak(text)

        # 将新音频保存到缓存，供下次复用
        if audio_path:
            self.tts_cache.set(text, voice, audio_path, provider)

        return audio_path

    def run_interactive(self):
        """
        交互模式 - 命令行文字/语音对话

        设计意图:
            用于开发和调试，支持:
            1. 文字输入: 直接在终端输入文字对话
            2. 语音输入: 输入 "voice" 切换到语音模式（3秒录音 → ASR → 回复 → TTS）
            3. Ctrl+C 退出

        执行流程:
            循环:
            - 语音模式: select 检测 stdin 输入停止 → 录音3秒 → process_audio → 播放
            - 文字模式: input() 读取 → process_message → speak() → 播放
        """
        print("\n 咕咕嘎嘎 - 交互模式")
        print("输入文字对话，按 Ctrl+C 退出")
        print("输入 'voice' 开启语音输入模式\n")

        voice_mode = False
        _voice = None  # 延迟获取 voice 模块（避免启动时就加载 sounddevice）

        try:
            while True:
                if voice_mode:
                    print("\n 语音输入模式已开启，按任意键停止...")
                    import select
                    # 非阻塞检测 stdin 是否有输入（超时 0 秒立即返回）
                    if select.select([sys.stdin], [], [], 0)[0]:
                        input()  # 消耗掉按键输入
                        voice_mode = False
                        print(" 语音输入模式已关闭")
                        continue

                    # 懒加载 voice 模块（仅在首次进入语音模式时加载）
                    if _voice is None:
                        _voice = self.voice

                    # 录音: start() 开始 → 等待3秒 → stop() 结束并返回音频文件路径
                    if _voice.start():
                        import time
                        time.sleep(3)  # 录音3秒
                        audio_file = _voice.stop()

                        if audio_file:
                            print(f" 录音文件: {audio_file}")
                            result = self.process_audio(audio_file)
                            print(f" 咕咕嘎嘎: {result['text']}")

                            # 播放 TTS 生成的回复音频
                            if result.get("audio"):
                                self._play_audio(result["audio"])
                else:
                    # 文字输入模式
                    user_input = input(" 你: ").strip()
                    if not user_input:
                        continue

                    # 特殊命令: 切换到语音模式
                    if user_input == "voice":
                        # 懒加载 voice 模块
                        if _voice is None:
                            _voice = self.voice
                        if _voice.is_available():
                            voice_mode = True
                            print(" 进入语音输入模式...")
                        else:
                            print("️ 语音输入不可用，请安装sounddevice")
                        continue

                    # 普通文字对话
                    print(" 思考中...")
                    result = self.process_message(user_input)
                    print(f" 咕咕嘎嘎: {result['text']}\n")

                    # TTS 合成并播放回复
                    audio_path = self.speak(result["text"])
                    if audio_path:
                        self._play_audio(audio_path)

        except KeyboardInterrupt:
            print("\n 再见喵~")

    def run_web(self, desktop_mode: bool = False):
        """
        Web 模式 - 启动 HTTP + WebSocket 服务

        设计意图:
            生产运行模式。启动后通过浏览器访问交互界面。

        参数说明:
            desktop_mode (bool): 桌面模式标志。
                - False (默认): 浏览器模式，打印"打开浏览器"提示
                - True: 桌面模式，由 launcher.py 管理，不自动打开浏览器

        执行流程:
            1. 如果启用了 Live2D，打印其服务地址
            2. 预热关键模块（LLM/TTS/ASR），通过访问 @property 触发懒加载
               避免第一次用户请求时的延迟
            3. 启动 Web HTTP 服务器
            4. 启动 WebSocket 服务器（实时音频/状态推送）
            5. 打印服务地址信息
            6. 主线程 sleep 等待，直到 Ctrl+C 触发停止
        """
        # v1.9.55: 启动时清理旧 TTS 缓存文件（超过24小时的 .wav）
        try:
            cache_dir = Path('app/cache')
            if cache_dir.is_dir():
                import time as _time
                now = _time.time()
                cleaned = 0
                for f in cache_dir.glob('*.wav'):
                    if f.is_file() and (now - f.stat().st_mtime) > 86400:
                        f.unlink(missing_ok=True)
                        cleaned += 1
                if cleaned:
                    self.logger.info(f"已清理 {cleaned} 个过期 TTS 缓存文件")
        except Exception as e:
            self.logger.debug(f"清理 TTS 缓存时出错（可忽略）: {e}")

        game_section("启动 Web 服务")
        
        # 如果启用了 Live2D，打印其独立 HTTP 服务地址
        if self.live2d.enabled:
            game_info("Live2D", f"http://localhost:{self.live2d.port}")

        # v1.9.27: 先启动 Web/WS 服务器（让健康检查尽快通过），再后台预加载模块
        # 原来 LLM/TTS/ASR 串行预加载要 3-8s（import torch 就要 2-5s），全部阻塞 WebServer 启动
        # 现在改为：WebServer 先启动 → 健康检查通过 → 桌面模式跳转 → 后台继续加载

        # 启动 Web HTTP 服务器（通过属性触发懒加载 + start()）
        self.web_server.start()
        self.logger.info(f"Web HTTP 服务已启动: 端口 {self.config.config.get('web.port', 12393)}")

        # 启动 WebSocket 服务器（实时通信）
        self.ws_server.start()
        self.logger.info(f"WebSocket 服务已启动: 端口 {self.config.config.get('web.ws_port', 12394)}")

        # 后台预加载核心模块（不再阻塞 WebServer 启动）
        def _background_preload():
            game_section("预加载核心模块（后台）")
            try:
                _ = self.llm  # 预热 LLM（纯 API 客户端，很快 <0.5s）
                self.logger.info(f"LLM 预热完成: {type(self._lazy_modules.get('llm')).__name__}")
            except Exception as e:
                game_warn("LLM预热", str(e))
                self.logger.error(f"LLM 预热失败: {e}", exc_info=True)
            try:
                _ = self.tts   # 预热 TTS（import torch ~2-5s，但不阻塞服务了）
                self.logger.info(f"TTS 预热完成: {type(self._lazy_modules.get('tts')).__name__}")
            except Exception as e:
                game_warn("TTS预热", str(e))
                self.logger.error(f"TTS 预热失败: {e}", exc_info=True)
            # ASR 无需预加载：FunASRASR 是懒加载的，首次 recognize() 才加载模型
            # 预加载只是创建配置对象，没有实际模型加载
            try:
                _ = self.asr
                self.logger.info(f"ASR 预热完成: {type(self._lazy_modules.get('asr')).__name__}")
            except Exception as e:
                game_warn("ASR预热", str(e))
                self.logger.error(f"ASR 预热失败: {e}", exc_info=True)
        
        import threading
        threading.Thread(target=_background_preload, daemon=True, name="background-preload").start()

        # v1.9.51: 启动主动说话管理器（如果已启用）
        try:
            proactive = self.proactive
            if proactive and proactive.enabled:
                proactive.start()
        except Exception as e:
            game_warn("主动说话", str(e))

        # v1.9.52: 启动 MCP 工具桥接器（如果已启用）
        try:
            mcp = self.mcp
            # MCP 已在懒加载属性中自动启动
        except Exception as e:
            game_warn("MCP工具桥接", str(e))

        # v1.9.52: 启动桌面宠物模式（如果已启用）
        try:
            pet = self.desktop_pet
            if pet and pet.enabled:
                pet.start()
        except Exception as e:
            game_warn("桌面宠物", str(e))

        port = self.config.config.get('web.port', 12393)
        live2d_port = self.live2d.port if self.live2d.enabled else 'N/A'
        
        if desktop_mode:
            game_header(f"桌面模式 | 端口 {port}")
            game_box([
                f"主界面: http://localhost:{port}",
                f"Live2D: http://localhost:{live2d_port}",
                "",
                "桌面窗口由启动器管理"
            ])
        else:
            game_header(f"Web 服务已就绪 | 端口 {port}")
            game_box([
                f"主界面: http://localhost:{port}",
                f"Live2D: http://localhost:{live2d_port}",
                "",
                "按 Ctrl+C 停止服务"
            ])

        try:
            # 主线程保持运行，通过 sleep 阻塞
            # 实际工作由 web_server 和 ws_server 的后台线程完成
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n 服务已停止")
            self.stop()

    def _load_history(self):
        """v1.9.50: 从磁盘恢复对话历史，若无则从记忆系统恢复"""
        try:
            if self._history_file.exists():
                with open(self._history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    self.history = data[-(self.MAX_HISTORY * 2):]
                    print(f"  [历史] 恢复对话历史: {len(self.history)}条")
                    return
        except Exception as e:
            print(f"  [历史] 恢复对话历史失败: {e}")

        # 持久化文件不存在或为空，尝试从记忆系统的工作记忆恢复
        try:
            memory = getattr(self, '_memory', None)
            if memory is None:
                # 记忆系统可能还没初始化，延迟恢复
                self._history_needs_restore = True
                self.history = []
                return
            working = getattr(memory, 'working_memory', None)
            if working and len(working) > 0:
                for item in working[-(self.MAX_HISTORY * 2):]:
                    role = getattr(item, 'role', None)
                    content = getattr(item, 'content', None)
                    if role and content:
                        self.history.append({"role": role, "content": content})
                print(f"  [历史] 从工作记忆恢复对话历史: {len(self.history)}条")
                # 首次恢复后保存到磁盘
                self._save_history()
                return
        except Exception as e:
            print(f"  [历史] 从工作记忆恢复失败: {e}")
        self.history = []

    def _save_history(self):
        """v1.9.50: 保存对话历史到磁盘"""
        try:
            data = self.history[-(self.MAX_HISTORY * 2):]
            tmp_file = self._history_file.with_suffix('.tmp')
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_file, self._history_file)
        except Exception as e:
            print(f"  [历史] 保存对话历史失败: {e}")

    def record_interaction(self, user_text: str, assistant_text: str):
        """
        v1.9.55: 统一记录对话交互（记忆 + 历史 + 持久化）
        消除 main.py / web/__init__.py 三处重复的 mem.add_interaction + history.append + _save_history 逻辑。
        """
        if not user_text or not assistant_text:
            return
        # 1. 记忆系统
        try:
            mem = getattr(self, '_memory', None)
            if mem is not None:
                mem.add_interaction("user", user_text)
                mem.add_interaction("assistant", assistant_text)
        except Exception as e:
            self.logger.debug(f"记忆写入错误（可忽略）: {e}")
        # 2. 历史记录 + 截断 + 持久化
        try:
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": assistant_text})
            if len(self.history) > self.MAX_HISTORY * 2:
                self.history = self.history[-(self.MAX_HISTORY * 2):]
            self._save_history()
        except Exception as e:
            self.logger.debug(f"历史更新错误（可忽略）: {e}")

    def _atexit_flush(self):
        """atexit 回调：确保异常退出时也能 flush 记忆系统和对话历史"""
        # v1.9.50: 保存对话历史
        if self.history:
            try:
                self._save_history()
            except Exception:
                pass  # atexit 中不能抛异常
        if self._memory_initialized and self._memory:
            try:
                self._memory.flush()
            except Exception:
                pass  # atexit 中不能抛异常

    def _signal_handler(self, signum, frame):
        """M1修复: SIGTERM/SIGINT 信号处理，确保优雅关停"""
        sig_name = {2: "SIGINT", 15: "SIGTERM"}.get(signum, f"Signal {signum}")
        print(f"\n[Signal] 收到 {sig_name}，正在优雅关停...")
        self.stop()
        sys.exit(0)

    def stop(self):
        """
        停止所有服务并释放资源

        设计意图:
            在程序退出时按顺序优雅关闭所有子模块，防止资源泄露。
            关闭顺序: Web → WebSocket → 执行器线程池 → 子Agent → TTS 缓存统计

        执行流程:
            1. 停止 Web HTTP 服务器（如果已加载）
            2. 停止 WebSocket 服务器（如果已加载）
            3. 关闭命令执行器线程池（如果已初始化）
            4. 关闭子 Agent（如果已加载）
            5. 打印 TTS 缓存统计信息
        """
        self.logger.info("正在停止服务...")

        # v1.9.51: 停止主动说话管理器
        if 'proactive' in self._lazy_modules and self._lazy_modules.get('proactive'):
            try:
                self._lazy_modules['proactive'].stop()
                self.logger.info("主动说话管理器已停止")
            except Exception as e:
                self.logger.error(f"主动说话管理器停止失败: {e}")

        # v1.9.52: 停止 MCP 工具桥接器
        if 'mcp' in self._lazy_modules and self._lazy_modules.get('mcp'):
            try:
                self._lazy_modules['mcp'].stop()
                self.logger.info("MCP工具桥接器已停止")
            except Exception as e:
                self.logger.error(f"MCP工具桥接器停止失败: {e}")

        # v1.9.52: 停止桌面宠物
        if 'desktop_pet' in self._lazy_modules and self._lazy_modules.get('desktop_pet'):
            try:
                self._lazy_modules['desktop_pet'].stop()
                self.logger.info("桌面宠物已停止")
            except Exception as e:
                self.logger.error(f"桌面宠物停止失败: {e}")

        # 停止 Web HTTP 服务（检查是否已懒加载）
        web_svr = getattr(self, 'web_server', None) if 'web_server' in self._lazy_modules else None
        if web_svr:
            try:
                web_svr.stop()
                self.logger.info("Web服务已停止")
            except Exception as e:
                self.logger.error(f"Web服务停止失败: {e}")

        # 停止 WebSocket 服务（检查是否已懒加载）
        ws_svr = getattr(self, 'ws_server', None) if 'ws_server' in self._lazy_modules else None
        if ws_svr:
            try:
                ws_svr.stop()
                self.logger.info("WebSocket服务已停止")
            except Exception as e:
                self.logger.error(f"WebSocket服务停止失败: {e}")

        # 关闭命令执行器线程池（等待所有正在执行的命令完成）
        if self._executor_initialized and self._executor:
            try:
                self._executor.shutdown()
                self.logger.info("执行器已关闭")
            except Exception as e:
                self.logger.error(f"执行器关闭失败: {e}")

        # 刷新记忆系统（确保所有未持久化的记忆数据写入磁盘）
        # v2.2: 使用 MemorySystem.flush() 一次性 flush 工作/情景/语义记忆
        # 注意: 访问 _memory 而非 memory property，避免触发懒加载
        if self._memory_initialized and self._memory:
            try:
                self._memory.flush()
                self.logger.info("记忆系统已刷新")
            except Exception as e:
                self.logger.error(f"记忆刷新失败: {e}")

        # v1.9.50: 保存对话历史到磁盘
        if self.history:
            try:
                self._save_history()
                self.logger.info(f"对话历史已保存 ({len(self.history)}条)")
            except Exception as e:
                self.logger.error(f"对话历史保存失败: {e}")

        # C2修复: 清理GPU资源（TTS模型等）
        if 'tts' in self._lazy_modules and self._lazy_modules.get('tts'):
            try:
                tts = self._lazy_modules['tts']
                if hasattr(tts, 'cleanup'):
                    tts.cleanup()
                    self.logger.info("TTS GPU资源已释放")
            except Exception as e:
                self.logger.error(f"TTS GPU清理失败: {e}")

        # 打印 TTS 缓存统计（仅统计信息，不做清理）
        if hasattr(self, 'tts_cache'):
            stats = self.tts_cache.get_stats()
            self.logger.info(f"TTS缓存: {stats['count']} 个文件, {stats['size_mb']:.2f} MB")

        self.logger.info("所有服务已停止")

    def _play_audio(self, audio_path: str):
        """
        播放音频文件 - 跨平台支持

        设计意图:
            在本地交互模式下播放 TTS 生成的音频。
            根据操作系统选择不同的播放方式:
            - Windows: winsound.PlaySound（同步播放，内置库）
            - macOS: afplay 命令（异步播放）
            - Linux: aplay（ALSA）或 play（SoX）命令（异步播放）

        参数说明:
            audio_path: 音频文件的绝对路径

        安全说明:
            使用 subprocess.Popen + 列表参数（非字符串），
            避免 shell 注入风险（虽然 audio_path 理论上应该是安全的路径）。
        """
        try:
            import platform
            import subprocess

            system = platform.system()
            if system == "Windows":
                # Windows 内置音频播放 API（同步，播放完才返回）
                import winsound
                winsound.PlaySound(audio_path, winsound.SND_FILENAME)
            elif system == "Darwin":
                # macOS 系统自带播放器（异步）
                subprocess.Popen(["afplay", audio_path])
            else:
                # Linux: 优先尝试 ALSA 的 aplay，失败则尝试 SoX 的 play
                try:
                    subprocess.Popen(["aplay", audio_path],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except FileNotFoundError:
                    subprocess.Popen(["play", audio_path],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"️ 播放失败: {e}")

    def _handle_local_tool(self, text: str) -> Optional[str]:
        """
        处理本地工具调用（参考 Claude Code 的工具调用格式）

        设计意图:
            解析 LLM 回复中的嵌入式工具指令，支持四种操作:
            - BASH: command → 执行 Bash 命令
            - READ: path → 读取文件内容
            - WRITE: path|content → 写入文件（路径和内容用 | 分隔）
            - EDIT: path（暂未实现）

        参数说明:
            text: LLM 回复的完整文本

        返回值:
            str: 工具执行结果，或 None（无匹配或执行失败时）
        """
        import re

        result = None

        # BASH 命令: 匹配 "BASH: ls -la" 格式
        match = re.search(r"BASH:\s*(.+?)(?:\n|$)", text, re.DOTALL)
        if match:
            cmd = match.group(1).strip()
            # 调用 ToolFactory 的 bash 工具执行
            result = self.tools.execute("bash", command=cmd)

        # READ 文件: 匹配 "READ: /path/to/file" 格式
        if not result:
            match = re.search(r"READ:\s*(.+?)(?:\n|$)", text, re.DOTALL)
            if match:
                path = match.group(1).strip()
                result = self.tools.execute("read", path=path)

        # WRITE 文件: 匹配 "WRITE: path|content" 格式（路径和内容用 | 分隔）
        if not result:
            match = re.search(r"WRITE:\s*(.+?)(?:\n|$)", text, re.DOTALL)
            if match:
                args = match.group(1).strip()
                # 格式: path|content（用第一个 | 分隔路径和内容）
                if "|" in args:
                    path, content = args.split("|", 1)
                    result = self.tools.execute("write", path=path.strip(), content=content)

        # 格式化返回结果
        if result and result.get("success"):
            # 优先返回 stdout，其次 content，最后 message
            return result.get("stdout") or result.get("content") or result.get("message", "完成")
        elif result:
            return f"失败: {result.get('error', '未知错误')}"

        return None


def main():
    """
    CLI 入口函数 - 解析命令行参数并启动对应模式

    支持的命令行参数:
        --config / -c: 自定义配置文件路径
        --web / -w: 启动 Web 服务模式
        --live2d / -l: 仅启动 Live2D 服务
        --interactive / -i: 启动命令行交互模式
        --test-llm: 测试 LLM 连接（发送 "你好" 并打印回复）
        --test-tts TEXT: 测试 TTS（合成指定文本并输出音频文件路径）

    默认行为（无参数）: 启动 Web 模式

    资源管理:
        使用 with AIVTuber(...) 上下文管理器，确保异常时也能正确清理资源。
    """
    try:
        parser = argparse.ArgumentParser(description="咕咕嘎嘎 - AI虚拟形象")
        parser.add_argument("--config", "-c", help="配置文件路径")
        parser.add_argument("--web", "-w", action="store_true", help="启动Web服务")
        parser.add_argument("--desktop", "-d", action="store_true", help="桌面模式（由launcher.py调用，不自动打开浏览器）")
        parser.add_argument("--live2d", "-l", action="store_true", help="启动Live2D服务")
        parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
        parser.add_argument("--test-llm", action="store_true", help="测试LLM")
        parser.add_argument("--test-tts", type=str, help="测试TTS")

        args = parser.parse_args()

        game_header("咕咕嘎嘎 AI-VTuber v1.9.82")
        game_info("系统启动中", f"{_timestamp()} | Python {sys.version_info.major}.{sys.version_info.minor}")

        # 使用上下文管理器创建 AIVTuber 实例（确保退出时清理资源）
        with AIVTuber(args.config) as vtuber:
            game_ok("系统就绪", "所有核心模块已加载")

            # 桌面模式标志（--desktop 参数或环境变量）
            desktop_mode = args.desktop or os.getenv("GUGUGAGA_DESKTOP") == "1"

            # 根据参数选择运行模式
            if len(sys.argv) == 1:
                # 无参数 → 默认启动 Web 模式
                print("\n 启动Web模式...")
                vtuber.run_web(desktop_mode=desktop_mode)

            elif args.live2d:
                # --live2d → 仅启动 Live2D 独立服务
                print("\n 启动Live2D...")
                vtuber.live2d.start_server()

            elif args.web:
                # --web → Web 模式
                vtuber.run_web(desktop_mode=desktop_mode)

            elif args.desktop:
                # --desktop → 桌面模式（由 launcher.py 调用）
                print("\n 启动桌面模式...")
                vtuber.run_web(desktop_mode=True)

            elif args.test_llm:
                # --test-llm → 测试 LLM 连接
                print(" 测试LLM...")
                result = vtuber.llm.chat("你好")
                print(f" 回复: {result.get('text')}")

            elif args.test_tts:
                # --test-tts TEXT → 测试 TTS 合成
                print(f" 测试TTS: {args.test_tts}")
                audio = vtuber.tts.speak(args.test_tts)
                print(f" 文件: {audio}")

            else:
                # --interactive 或其他 → 交互模式
                vtuber.run_interactive()

    except KeyboardInterrupt:
        print("\n[EXIT] User interrupted")
    except Exception as e:
        # 未捕获的全局异常: 打印堆栈并暂停，便于调试
        print(f"\n[FATAL] Error: {e}")
        import traceback
        traceback.print_exc()
        # v1.9.60: 桌面模式下跳过 input()（无控制台，input() 会挂起进程）
        if not os.getenv("GUGUGAGA_DESKTOP"):
            input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
