"""
双模式兼容工具

确保 WebUI 模式和原生桌面模式可以共存:
1. 共享配置目录 (app/cache/, memory/)
2. 共享对话历史 (memory/state/chat_history.json)
3. 共享 LLM 偏好 (app/cache/llm_preferences.json)
4. 互斥锁 — 同一时间只运行一种模式（统一命名，两种模式可互相检测）
5. 端口检测 — WebUI 运行时通知用户
"""

import os
import sys
import json
import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QThread

logger = logging.getLogger(__name__)

# 互斥体名称统一从 shared_config 引入
try:
    from app.shared_config import MUTEX_NAME_BASE, MUTEX_NAME_NATIVE
    _MUTEX_BASE = MUTEX_NAME_BASE
    _MUTEX_NATIVE = MUTEX_NAME_NATIVE
except ImportError:
    _MUTEX_BASE = "Local\\GuguGagaAI-VTuber"
    _MUTEX_NATIVE = _MUTEX_BASE + "_Native"

# KI-002 FIX: 端口配置从 shared_config 统一读取
try:
    from app.shared_config import HTTP_PORT, WS_PORT
    _WEBUI_HTTP_PORT = HTTP_PORT
    _WEBUI_WS_PORT = WS_PORT
except ImportError:
    _WEBUI_HTTP_PORT = 12393
    _WEBUI_WS_PORT = 12394


class WebUICheckWorker(QObject):
    """优化 #4: 异步 WebUI 检测 — 避免阻塞主线程 1s"""

    result_ready = Signal(bool)

    def __init__(self, http_port: int, parent=None):
        super().__init__(parent)
        self._http_port = http_port

    def check(self):
        """在子线程中检测 WebUI 是否在运行"""
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', self._http_port))
                self.result_ready.emit(result == 0)
        except Exception as e:
            self.result_ready.emit(False)


class DualModeCompat:
    """双模式兼容管理器"""

    # Mutex 名称（与 WebUI launcher 共享，统一命名）
    MUTEX_NAME = _MUTEX_BASE

    # 端口配置（KI-002: 从 shared_config 统一读取）
    WEBUI_HTTP_PORT = _WEBUI_HTTP_PORT
    WEBUI_WS_PORT = _WEBUI_WS_PORT

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.cache_dir = self.project_dir / "app" / "cache"
        self.memory_dir = self.project_dir / "memory"
        self.state_dir = self.memory_dir / "state"
        self._mutex_handle = None

    # ========== 共享路径 ==========

    def get_shared_paths(self) -> dict:
        """获取两种模式共享的路径"""
        return {
            "cache_dir": str(self.cache_dir),
            "llm_preferences": str(self.cache_dir / "llm_preferences.json"),
            "chat_history": str(self.state_dir / "chat_history.json"),
            "hotkey_config": str(self.cache_dir / "hotkeys.json"),
            "skip_update": str(self.cache_dir / "skip_update.json"),
            "config_yaml": str(self.project_dir / "app" / "config.yaml"),
        }

    def ensure_dirs(self):
        """确保共享目录存在"""
        for d in [self.cache_dir, self.memory_dir, self.state_dir]:
            d.mkdir(parents=True, exist_ok=True)

    # ========== 互斥锁 ==========

    def acquire_native_mutex(self) -> bool:
        """尝试获取原生桌面模式的互斥锁

        Returns:
            True = 成功获取（无其他实例运行）
            False = 已有实例在运行
        """
        if sys.platform != "win32":
            return True
        try:
            import ctypes
            import time as _time
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            mutex_name = _MUTEX_NATIVE

            handle = kernel32.CreateMutexW(None, False, mutex_name)
            last_error = ctypes.get_last_error()

            if last_error == 183:  # ERROR_ALREADY_EXISTS
                logger.warning("Another native instance is already running")
                # 等待 3 秒后重试（进程被杀后 Windows 互斥锁可能有延迟清理）
                _time.sleep(3)
                handle = kernel32.CreateMutexW(None, False, mutex_name)
                last_error = ctypes.get_last_error()
                if last_error == 183:
                    return False

            self._mutex_handle = handle
            return True
        except Exception as e:
            logger.error(f"Mutex check failed: {e}")
            return True  # 失败时允许启动

    def check_webui_running(self) -> bool:
        """检查 WebUI 模式是否在运行

        通过检测 HTTP 端口是否被占用来判断
        """
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', self.WEBUI_HTTP_PORT))
                return result == 0  # 端口被占用 = WebUI 在运行
        except Exception as e:
            return False

    def release_mutex(self):
        """释放互斥锁"""
        if self._mutex_handle:
            try:
                import ctypes
                kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
                kernel32.CloseHandle(self._mutex_handle)
            except Exception as e:
                pass
            self._mutex_handle = None

    # ========== 配置迁移 ==========

    def migrate_webui_config(self) -> dict:
        """从 WebUI 配置中提取原生桌面可用的设置

        KI-015 FIX: 展开 ${VAR} 环境变量，与主 Config._load() 行为一致

        Returns:
            包含 LLM/TTS/ASR 配置的字典
        """
        config = {}
        config_path = self.project_dir / "app" / "config.yaml"

        if not config_path.exists():
            return config

        try:
            import yaml
            import re

            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # KI-015 FIX: 展开 ${VAR} 环境变量
            def expand_env_vars(text):
                pattern = re.compile(r'\$\{(\w+)\}')
                def replacer(match):
                    var_name = match.group(1)
                    return os.environ.get(var_name, match.group(0))
                return pattern.sub(replacer, text)

            expanded_content = expand_env_vars(content)
            yaml_config = yaml.safe_load(expanded_content)

            if yaml_config:
                config = {
                    "llm": yaml_config.get("llm", {}),
                    "tts": yaml_config.get("tts", {}),
                    "asr": yaml_config.get("asr", {}),
                    "memory": yaml_config.get("memory", {}),
                    "vision": yaml_config.get("vision", {}),
                }
        except Exception as e:
            logger.warning(f"Failed to migrate WebUI config: {e}")

        return config

    def load_llm_preferences(self) -> dict:
        """加载 LLM 偏好（与 WebUI 共享）"""
        pref_path = self.cache_dir / "llm_preferences.json"
        if pref_path.exists():
            try:
                with open(pref_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                pass
        return {}

    def save_llm_preferences(self, prefs: dict):
        """保存 LLM 偏好（与 WebUI 共享）"""
        self.ensure_dirs()
        pref_path = self.cache_dir / "llm_preferences.json"
        try:
            with open(pref_path, 'w', encoding='utf-8') as f:
                json.dump(prefs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save LLM preferences: {e}")
