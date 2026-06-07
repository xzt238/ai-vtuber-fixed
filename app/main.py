#!/usr/bin/env python3
"""
=====================================
咕咕嘎嘎 AI虚拟形象 - 主程序（重构版）
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

重构说明:
    - 将懒加载属性提取到 LazyModuleManager
    - 将历史记录管理提取到 HistoryManager
    - 将交互模式管理提取到 InteractionManager
    - 保持原有功能不变，提高代码可维护性

作者: 咕咕嘎嘎
日期: 2026-03-27
"""

import os
import sys
import subprocess as _subprocess
import threading
import logging

logger = logging.getLogger(__name__)

# Windows GBK 编码安全网：强制 stdout/stderr 使用 UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        pass

import json
import tempfile
import argparse
import atexit
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from functools import cached_property

# 将当前 app/ 目录插入 Python 模块搜索路径的最前面
sys.path.insert(0, str(Path(__file__).parent))


# ============ Windows subprocess 安全辅助函数 ============
def _win_subprocess_args():
    """返回 Windows 桌面模式下 subprocess 隐藏 CMD 窗口所需的额外参数。"""
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
from app.shared_config import PROJECT_DIR as _PROJECT_DIR_STR
PROJECT_ROOT = Path(_PROJECT_DIR_STR)
MODELS_CACHE = PROJECT_ROOT / "models"
MODELS_CACHE.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("MODELSCOPE_CACHE", str(MODELS_CACHE / "modelscope"))
os.environ.setdefault("HF_HOME", str(MODELS_CACHE / "hf"))
os.environ.setdefault("TORCH_HOME", str(MODELS_CACHE / "torch"))
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(MODELS_CACHE / "hf"))

# ============ 游戏风格日志系统 ============
from log_style import (
    LogStyle, game_header, game_box, game_loading,
    game_ok, game_skip, game_fail, game_info, game_warn,
    game_debug, game_progress, game_section, game_separator,
)

import warnings
warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")
warnings.filterwarnings("ignore", message=".*ffmpeg is not installed.*")
warnings.filterwarnings("ignore", message=".*Couldn.t find ffmpeg.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*ffmpeg.*")

# ============ 核心工具模块 ============
from logger_new import get_logger, security_logger
from utils import validate_path, temp_file, friendly_error
from tts_cache import TTSCache

# ============ 导入重构后的模块 ============
from lazy_module_manager import LazyModuleManager
from history_manager import HistoryManager
from interaction_manager import InteractionManager


class Config:
    """
    配置管理器

    设计意图:
        统一管理整个系统的 YAML 配置加载，支持:
        1. 多路径自动探测（打包 exe / 开发模式）
        2. ${VAR} 环境变量自动展开（如 ${MINIMAX_API_KEY}）
        3. 点号分隔的嵌套键访问（如 config.get("llm.minimax.model")）
        4. pyyaml 缺失时的备用硬编码配置
    """

    def __init__(self, config_path: str = None):
        """初始化配置管理器"""
        self.logger = get_logger("config")
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load()

    def _get_default_config_path(self) -> str:
        """自动探测配置文件路径"""
        if getattr(sys, 'frozen', False):
            config_path = Path(sys._MEIPASS) / "app" / "config.yaml"
            if config_path.exists():
                return str(config_path)
            config_path = Path(sys.executable).parent / "config.yaml"
            if config_path.exists():
                return str(config_path)
            config_path = Path(sys.executable).parent / "app" / "config.yaml"
            if config_path.exists():
                return str(config_path)
        else:
            config_path = Path(__file__).parent / "config.yaml"
            if config_path.exists():
                return str(config_path)
        return str(Path(__file__).parent / "config.yaml")

    def _load(self) -> Dict[str, Any]:
        """加载并解析 YAML 配置文件"""
        config_file = Path(self.config_path)
        if not config_file.exists():
            game_warn("配置", f"文件不存在，使用默认配置")
            return self._get_default_config()

        try:
            import yaml
            import re
            with open(config_file, "r", encoding="utf-8") as f:
                raw_config = f.read()

            def _expand_env(match):
                return os.getenv(match.group(1), match.group(0))
            raw_config = re.sub(r'\$\{([^}]+)\}', _expand_env, raw_config)
            config = yaml.safe_load(raw_config)

            # 加载偏好文件（简化版）
            cache_dir = Path(self.config_path).parent / "cache"
            try:
                from concurrent.futures import ThreadPoolExecutor, as_completed

                def _load_json_pref(file_name: str) -> Tuple[str, Optional[dict]]:
                    fpath = cache_dir / file_name
                    if fpath.exists():
                        try:
                            with open(fpath, "r", encoding="utf-8") as pf:
                                return (file_name, json.load(pf))
                        except Exception:
                            pass
                    return (file_name, None)

                pref_files = [
                    "api_keys.json",
                    "llm_preferences.json",
                    "asr_preferences.json",
                    "tts_preferences.json",
                    "vision_preferences.json",
                ]

                prefs_data = {}
                with ThreadPoolExecutor(max_workers=min(5, os.cpu_count() or 4)) as pref_executor:
                    futures = {pref_executor.submit(_load_json_pref, fn): fn for fn in pref_files}
                    for future in as_completed(futures):
                        try:
                            file_name, data = future.result()
                            prefs_data[file_name] = data
                        except Exception:
                            pass
            except Exception:
                prefs_data = {}

            # 恢复 API Keys
            api_keys_data = prefs_data.get("api_keys.json")
            if api_keys_data:
                try:
                    for provider_name, key_value in api_keys_data.items():
                        llm_provider = config.setdefault("llm", {}).setdefault(provider_name, {})
                        if key_value:
                            llm_provider["api_key"] = key_value
                        if provider_name == "minimax":
                            vision_minimax = config.setdefault("vision", {}).setdefault("minimax_vl", {})
                            if key_value:
                                vision_minimax["api_key"] = key_value
                        if provider_name == "mimo" and key_value:
                            asr_mimo = config.setdefault("asr", {}).setdefault("mimo", {})
                            asr_mimo["api_key"] = key_value
                            tts_mimo = config.setdefault("tts", {}).setdefault("mimo", {})
                            tts_mimo["api_key"] = key_value
                            vision_mimo = config.setdefault("vision", {}).setdefault("mimo_vision", {})
                            vision_mimo["api_key"] = key_value
                    self.logger.info(f"从 api_keys.json 加载了 {len(api_keys_data)} 个API Key")
                except Exception as e:
                    self.logger.warning(f"加载 api_keys.json 失败(不影响使用): {e}")

            return config
        except ImportError:
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
        """获取最小化的默认配置"""
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
        """按点号分隔路径获取嵌套配置值"""
        if not hasattr(self, '_flat_config'):
            self._flat_config = self._flatten(self.config)
        value = self._flat_config.get(key, _SENTINEL)
        if value is _SENTINEL:
            return default
        return value if value is not None else default

    @staticmethod
    def _flatten(d: dict, parent_key: str = "", sep: str = ".") -> dict:
        """递归展开嵌套字典为扁平键值对"""
        items = {}
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.update(Config._flatten(v, new_key, sep))
            else:
                items[new_key] = v
        return items


# 用于区分"键不存在"与"值为 None"的哨兵
_SENTINEL = object()


class ToolExecutor:
    """
    命令执行器 - 安全沙箱

    设计意图:
        为 LLM 提供受限的系统命令执行能力。通过白名单 + 黑名单双重过滤，
        防止 LLM 生成的命令对系统造成破坏。
    """

    _BLOCKLIST = frozenset({"rm", "dd", "mkfs", "shutdown", "reboot", "init",
                            "chmod", "chown", "kill", "pkill", "curl", "wget",
                            "nc", "ncat", "bash", "sh", "python", "python3",
                            "perl", "ruby", "node", "sudo", "su"})

    def __init__(self, config: Dict[str, Any]):
        """初始化命令执行器"""
        self.config = config.get("execution", {})
        self.enabled = self.config.get("enabled", True)
        self.allowed_commands = self.config.get("allowed_commands", [])
        self.timeout = self.config.get("timeout", 30)
        from concurrent.futures import ThreadPoolExecutor
        self._executor = ThreadPoolExecutor(max_workers=3)

    def can_execute(self, command: str) -> bool:
        """检查命令是否允许执行"""
        if not self.enabled:
            return False
        import shlex
        try:
            parts = shlex.split(command) if command.strip() else []
        except ValueError:
            return False
        if not parts:
            return False
        cmd_name = parts[0]
        if self.allowed_commands and cmd_name not in self.allowed_commands:
            return False
        _SHELL_CHARS = {">", "<", "|", "&", ";", "`", "$"}
        if any(c in command for c in _SHELL_CHARS):
            return False
        if cmd_name in self._BLOCKLIST:
            return False
        return True

    def execute(self, command: str) -> Dict[str, Any]:
        """使用线程池异步执行命令"""
        if not self.can_execute(command):
            return {"success": False, "error": f"命令不允许执行: {command}"}
        try:
            import subprocess
            import shlex
            cmd_parts = shlex.split(command) if command else []
            win_args = _win_subprocess_args()
            future = self._executor.submit(
                subprocess.run,
                cmd_parts,
                shell=False,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                **win_args
            )
            result = future.result()
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def shutdown(self):
        """安全关闭线程池"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=True)

    def parse_action(self, text: str) -> Optional[Dict[str, Any]]:
        """从 LLM 回复文本中解析工具调用指令"""
        import re
        if "ACTION: execute" in text or "COMMAND:" in text:
            match = re.search(r"COMMAND:\s*(.+?)(?:\n|$)", text, re.DOTALL)
            if match:
                return {"type": "execute", "command": match.group(1).strip()}
        return None


class AIVTuber:
    """
    AI 虚拟形象主程序 - 全系统协调器（懒加载架构）

    重构说明:
        - 使用 LazyModuleManager 管理懒加载模块
        - 使用 HistoryManager 管理历史记录
        - 使用 InteractionManager 管理交互模式
    """

    def __init__(self, config_path: str = None):
        """初始化咕咕嘎嘎主应用（懒加载模式）"""
        # 加载配置
        try:
            self.config = Config(config_path)
        except FileNotFoundError:
            logger.info("\n" + "="*50)
            logger.info("  错误: 配置文件不存在!")
            logger.info(f"  路径: {config_path or 'app/config.yaml'}")
            logger.info("  请确认配置文件存在，或使用 --config 指定路径")
            logger.info("="*50)
            sys.exit(1)
        except Exception as e:
            logger.info("\n" + "="*50)
            logger.info("  错误: 配置文件加载失败!")
            logger.info(f"  原因: {e}")
            logger.info("  请检查 config.yaml 格式是否正确")
            logger.info("="*50)
            sys.exit(1)

        # 初始化日志
        self.logger = get_logger("main")
        self.logger.info("初始化咕咕嘎嘎 AI虚拟形象（懒加载模式）")

        game_section("核心模块")
        game_ok("配置管理器", f"已加载 {Path(self.config.config_path).name}")

        # 初始化懒加载模块管理器
        self._module_manager = LazyModuleManager(self.config, self.logger)

        # 初始化历史记录管理器
        self._history_manager = HistoryManager(max_history=100)
        self._history_manager.load_history()

        # 初始化交互模式管理器
        self._interaction_manager = InteractionManager(self)

        # TTS 缓存 - 立即初始化（轻量级，仅做文件缓存管理）
        self.tts_cache = TTSCache()
        self.logger.info("TTS 缓存已初始化")
        game_ok("TTS缓存", "音频文件缓存已就绪")

        # 对象池
        self._object_pools = {
            'dict': [],
            'list': [],
        }
        self._pool_max_size = 50

        game_section("系统初始化完成")
        game_ok("懒加载模块管理器", "已就绪")
        game_ok("历史记录管理器", "已就绪")
        game_ok("交互模式管理器", "已就绪")

        # 注册 atexit 回调
        atexit.register(self._atexit_flush)

        # 注册信号处理
        if threading.current_thread() is threading.main_thread():
            import signal
            signal.signal(signal.SIGINT, self._signal_handler)
            try:
                signal.signal(signal.SIGTERM, self._signal_handler)
            except (OSError, ValueError):
                pass

    # ============ 懒加载属性（委托给 LazyModuleManager）============

    @property
    def asr(self):
        """语音识别模块 (ASR) - 懒加载"""
        return self._module_manager.asr

    @property
    def tts(self):
        """语音合成模块 (TTS) - 懒加载"""
        return self._module_manager.tts

    @property
    def llm(self):
        """大语言模型模块 (LLM) - 懒加载"""
        return self._module_manager.llm

    @property
    def memory(self):
        """记忆系统模块 - 懒加载"""
        return self._module_manager.memory

    @property
    def vision(self):
        """视觉理解模块 - 懒加载"""
        return self._module_manager.vision

    @property
    def live2d(self):
        """Live2D 虚拟形象模块 - 懒加载"""
        return self._module_manager.live2d

    @property
    def voice(self):
        """语音输入模块 - 懒加载"""
        return self._module_manager.voice

    @property
    def voice_web(self):
        """Web 语音模块 - 懒加载"""
        return self._module_manager.voice_web

    @property
    def executor(self):
        """命令执行器 - 懒加载"""
        return self._module_manager.executor

    @property
    def tools(self):
        """工具管理器 - 懒加载"""
        return self._module_manager.tools

    @property
    def proactive(self):
        """主动对话模块 - 懒加载"""
        return self._module_manager.proactive

    @property
    def diary(self):
        """日记模块 - 懒加载"""
        return self._module_manager.diary

    @property
    def mcp(self):
        """MCP 模块 - 懒加载"""
        return self._module_manager.mcp

    @property
    def desktop_pet(self):
        """桌面宠物模块 - 懒加载"""
        return self._module_manager.desktop_pet

    @property
    def web_server(self):
        """HTTP 服务器 - 懒加载"""
        return self._module_manager.web_server

    @property
    def ws_server(self):
        """WebSocket 服务器 - 懒加载"""
        return self._module_manager.ws_server

    @property
    def emotion(self):
        """情感分析模块 - 懒加载"""
        return self._module_manager.emotion

    @property
    def roleplay(self):
        """角色扮演模块 - 懒加载"""
        return self._module_manager.roleplay

    @property
    def plugin(self):
        """插件系统 - 懒加载"""
        return self._module_manager.plugin

    @property
    def rag(self):
        """RAG 检索增强生成模块 - 懒加载"""
        return self._module_manager.rag

    @property
    def live(self):
        """直播模块 - 懒加载"""
        return self._module_manager.live

    @property
    def svc(self):
        """SVC 变声模块 - 懒加载"""
        return self._module_manager.svc

    @property
    def singing(self):
        """唱歌模块 - 懒加载"""
        return self._module_manager.singing

    @property
    def sd(self):
        """Stable Diffusion 图像生成模块 - 懒加载"""
        return self._module_manager.sd

    @property
    def game(self):
        """游戏模块 - 懒加载"""
        return self._module_manager.game

    @property
    def multi_agent(self):
        """多智能体模块 - 懒加载"""
        return self._module_manager.multi_agent

    @property
    def bot(self):
        """机器人模块 - 懒加载"""
        return self._module_manager.bot

    @property
    def vision_input(self):
        """视觉输入模块 - 懒加载"""
        return self._module_manager.vision_input

    @property
    def trainer(self):
        """训练管理模块 - 懒加载"""
        return self._module_manager.trainer

    # ============ 历史记录管理（委托给 HistoryManager）============

    @property
    def history(self):
        """获取历史记录"""
        return self._history_manager.history

    @history.setter
    def history(self, value):
        """设置历史记录"""
        self._history_manager.history = value

    def _load_history(self):
        """从磁盘恢复对话历史"""
        self._history_manager.load_history(self._memory)

    def _save_history(self):
        """保存对话历史到磁盘"""
        self._history_manager.save_history()

    def record_interaction(self, user_text: str, assistant_text: str):
        """统一记录对话交互"""
        self._history_manager.record_interaction(
            user_text, assistant_text,
            memory=self._memory,
            llm=self._lazy_modules.get('llm')
        )

    # ============ 交互模式（委托给 InteractionManager）============

    def run_interactive(self):
        """交互模式 - 命令行文字/语音对话"""
        self._interaction_manager.run_interactive()

    def run_web(self, desktop_mode: bool = False):
        """Web 模式 - 启动 HTTP + WebSocket 服务"""
        self._interaction_manager.run_web(desktop_mode)

    # ============ 核心处理方法 ============

    def process_message(self, text: str) -> Dict[str, Any]:
        """
        处理文字消息 - 核心对话流程

        参数说明:
            text: 用户输入的文字消息

        返回值:
            Dict: {"text": str, "action": dict|None}
        """
        try:
            self.logger.info(f"处理消息: {text[:50]}...")

            # 步骤1: 从长期记忆检索与当前输入语义相关的历史记忆
            relevant_memories = self.memory.search(text, top_k=3)
            context = ""
            if relevant_memories:
                context = "\n\n相关记忆:\n" + "\n".join([m.get("content") or m.get("text", "") for m in relevant_memories])

            # 步骤2: 将检索到的记忆上下文拼接到用户问题后面
            full_prompt = text
            if context:
                full_prompt = f"用户问题: {text}{context}"

            # 步骤3: 调用 LLM 进行推理
            history_snapshot = self._history_manager.get_history_snapshot()
            result = self.llm.chat(full_prompt, history_snapshot)
            reply = result.get("text", "")
            action = result.get("action")

            # 步骤4a: 处理执行动作（LLM 返回的 action 指令）
            if action and action.get("type") == "execute":
                cmd = action.get("command", "")
                self.logger.info(f"执行命令: {cmd}")
                exec_result = self.executor.execute(cmd)
                if exec_result["success"]:
                    output = exec_result.get("stdout", "") or exec_result.get("stderr", "")
                    reply = f"命令执行完成！\n{output}"
                else:
                    reply = f"命令执行失败: {exec_result.get('error', '未知错误')}"

            # 步骤4b: 处理本地工具调用
            if "BASH:" in reply or "READ:" in reply or "WRITE:" in reply or "EDIT:" in reply:
                tool_result = self._handle_local_tool(reply)
                if tool_result:
                    reply = f"{reply}\n\n 本地工具结果:\n{tool_result}"

            # 步骤5: 统一记录交互
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
            err_msg = str(e)
            if 'api_key' in err_msg.lower() or 'apikey' in err_msg.lower() or 'unauthorized' in err_msg.lower():
                user_msg = "API Key 无效或已过期，请在设置中重新配置"
            elif 'rate_limit' in err_msg.lower() or 'too many' in err_msg.lower():
                user_msg = "请求太频繁了，请稍等片刻再试"
            elif 'connection' in err_msg.lower() or 'timeout' in err_msg.lower():
                user_msg = "网络连接异常，请检查网络后重试"
            elif 'memory' in err_msg.lower() or 'cuda' in err_msg.lower() or 'out of memory' in err_msg.lower():
                user_msg = "显存不足，请尝试重启或减少其他GPU程序"
            else:
                user_msg = f"处理消息时出错（{type(e).__name__}），请查看日志获取详情"
            return {"text": user_msg, "action": None}

    def process_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        处理音频文件 - 完整的语音对话管线

        参数说明:
            audio_path: 音频文件的本地路径

        返回值:
            Dict: {"text": str, "audio": str}
        """
        text = self.asr.recognize(audio_path)
        if not text:
            return {"text": "抱歉，我没有听清楚"}
        result = self.process_message(text)
        output_audio_path = self.tts.speak(result["text"])
        return {
            "text": result["text"],
            "audio": output_audio_path
        }

    def process_audio_data(self, audio_data: str) -> Optional[Dict[str, Any]]:
        """
        处理 Web 端音频数据 - Base64 解码 + 完整语音管线

        参数说明:
            audio_data: Base64 编码的音频数据

        返回值:
            Dict 或 None
        """
        try:
            if "," in audio_data:
                audio_data = audio_data.split(",")[1]
            audio_bytes = base64.b64decode(audio_data)
            with temp_file(suffix=".webm") as temp_path:
                with open(temp_path, 'wb') as f:
                    f.write(audio_bytes)
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

        参数说明:
            text: 要合成的文本

        返回值:
            str: 音频文件路径，或 None
        """
        try:
            self.tts.stop()
        except Exception as e:
            self.logger.warning(f"停止播放失败: {e}")

        voice = getattr(self.tts, 'voice', 'default')
        provider = type(self.tts).__name__
        cached_audio = self.tts_cache.get(text, voice, provider)
        if cached_audio:
            self.logger.debug(f"使用缓存音频: {text[:30]}...")
            return cached_audio

        audio_path = self.tts.speak(text)
        if audio_path:
            self.tts_cache.set(text, voice, audio_path, provider)
        return audio_path

    def process_message_streaming(self, text: str) -> Dict[str, Any]:
        """
        流式消息处理 — 边生成边 TTS

        参数说明:
            text: 用户输入的文字消息

        返回值:
            Dict[str, Any]: {"text": 完整回复, "audio": 最后一段音频路径}
        """
        import re
        try:
            self.logger.info(f"处理消息(流式): {text[:50]}...")

            # 步骤1: 记忆检索
            relevant_memories = self.memory.search(text, top_k=3)
            context = ""
            if relevant_memories:
                context = "\n\n相关记忆:\n" + "\n".join([m.get("content") or m.get("text", "") for m in relevant_memories])

            full_prompt = text
            if context:
                full_prompt = f"用户问题: {text}{context}"

            # 步骤2: LLM 推理
            history_snapshot = self._history_manager.get_history_snapshot()
            result = self.llm.chat(full_prompt, history_snapshot)
            reply = result.get("text", "")
            action = result.get("action")

            # 处理执行动作
            if action and action.get("type") == "execute":
                cmd = action.get("command", "")
                exec_result = self.executor.execute(cmd)
                if exec_result["success"]:
                    output = exec_result.get("stdout", "") or exec_result.get("stderr", "")
                    reply = f"命令执行完成！\n{output}"
                else:
                    reply = f"命令执行失败: {exec_result.get('error', '未知错误')}"

            # 步骤3: 流式 TTS
            sentences = re.split(r'(?<=[。！？\n])', reply)
            sentences = [s.strip() for s in sentences if s.strip()]

            last_audio = None
            if sentences:
                for sentence in sentences:
                    if len(sentence) < 2:
                        continue
                    try:
                        audio_path = self.tts.speak(sentence)
                        if audio_path:
                            last_audio = audio_path
                    except Exception as e:
                        self.logger.warning(f"流式 TTS 失败: {e}")

            # 步骤4: 记录交互
            self.record_interaction(text, reply)

            # 步骤5: 工具执行后的二次对话
            if action and action.get("type") == "execute":
                tool_result = self.process_message(reply)
                return tool_result

            return {"text": reply, "audio": last_audio}

        except FileNotFoundError as e:
            self.logger.error(f"文件未找到: {e}")
            return {"text": f"抱歉，找不到需要的文件: {e}"}
        except PermissionError as e:
            self.logger.error(f"权限错误: {e}")
            return {"text": f"抱歉，权限不足: {e}"}
        except TimeoutError as e:
            self.logger.error(f"处理超时: {e}")
            return {"text": "抱歉，处理消息超时了，请重试"}
        except Exception as e:
            self.logger.exception(f"处理消息错误: {e}")
            return {"text": "抱歉，处理消息时出错了喵~"}

    # ============ 生命周期管理 ============

    def _atexit_flush(self):
        """atexit 回调：确保异常退出时也能 flush 记忆系统和对话历史"""
        self._history_manager.flush()
        if hasattr(self, '_memory') and self._memory:
            try:
                self._memory.flush()
            except Exception:
                pass

    def _signal_handler(self, signum, frame):
        """SIGTERM/SIGINT 信号处理，确保优雅关停"""
        sig_name = {2: "SIGINT", 15: "SIGTERM"}.get(signum, f"Signal {signum}")
        logger.info(f"\n[Signal] 收到 {sig_name}，正在优雅关停...")
        self.stop()
        sys.exit(0)

    def stop(self):
        """停止所有服务并释放资源"""
        self.logger.info("正在停止所有服务...")
        # 停止各种服务
        for service_name in ['web_server', 'ws_server', 'executor']:
            service = self._module_manager.get_module(service_name)
            if service and hasattr(service, 'stop'):
                try:
                    service.stop()
                except Exception as e:
                    self.logger.warning(f"停止 {service_name} 失败: {e}")
        self.logger.info("所有服务已停止")

    def _play_audio(self, audio_path: str):
        """播放音频文件"""
        try:
            import subprocess
            win_args = _win_subprocess_args()
            if sys.platform == "win32":
                subprocess.Popen(["start", audio_path], shell=True, **win_args)
            elif sys.platform == "darwin":
                subprocess.Popen(["afplay", audio_path])
            else:
                subprocess.Popen(["aplay", audio_path])
        except Exception as e:
            self.logger.warning(f"播放音频失败: {e}")

    def rebuild_llm(self):
        """重建 LLM 模块"""
        self._module_manager.clear_cache()
        self.logger.info("LLM 模块已重建")

    def rebuild_tts(self):
        """重建 TTS 模块"""
        self._module_manager.clear_cache()
        self.logger.info("TTS 模块已重建")

    def _handle_local_tool(self, text: str) -> Optional[str]:
        """处理本地工具调用"""
        # 这里可以添加本地工具处理逻辑
        return None

    # ============ 上下文管理器 ============

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.logger.info("清理资源...")
        self.stop()
        return False


# ============ CLI 入口 ============

def main():
    """CLI 入口点"""
    parser = argparse.ArgumentParser(description="咕咕嘎嘎 AI虚拟形象")
    parser.add_argument("--config", type=str, help="配置文件路径")
    parser.add_argument("--web", action="store_true", help="启动 Web 模式")
    parser.add_argument("--live2d", action="store_true", help="启动 Live2D 模式")
    parser.add_argument("--interactive", action="store_true", help="启动交互模式")
    parser.add_argument("--test-llm", type=str, help="测试 LLM")
    parser.add_argument("--test-tts", type=str, help="测试 TTS")
    args = parser.parse_args()

    with AIVTuber(args.config) as ai:
        if args.web:
            ai.run_web()
        elif args.interactive:
            ai.run_interactive()
        elif args.test_llm:
            result = ai.process_message(args.test_llm)
            print(f"LLM 回复: {result['text']}")
        elif args.test_tts:
            audio_path = ai.speak(args.test_tts)
            print(f"TTS 音频: {audio_path}")
        else:
            ai.run_web()


if __name__ == "__main__":
    main()
