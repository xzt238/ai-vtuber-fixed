"""
双模式兼容工具

确保 WebUI 模式和原生桌面模式可以共存:
1. 共享配置目录 (app/cache/, memory/)
2. 共享对话历史 (memory/state/chat_history.json)
3. 共享 LLM 偏好 (app/cache/llm_preferences.json)
4. 互斥锁 — 同一时间只运行一种模式
5. 端口检测 — WebUI 运行时通知用户
"""

import os
import sys
import json
import ctypes
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DualModeCompat:
    """双模式兼容管理器"""

    # Mutex 名称（与 WebUI launcher 共享）
    MUTEX_NAME = "Local\\GuguGagaAI-VTuber"

    # 端口配置
    WEBUI_HTTP_PORT = 12393
    WEBUI_WS_PORT = 12394

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
        try:
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            mutex_name = self.MUTEX_NAME + "_Native"

            handle = kernel32.CreateMutexW(None, False, mutex_name)
            last_error = ctypes.get_last_error()

            if last_error == 183:  # ERROR_ALREADY_EXISTS
                logger.warning("Another native instance is already running")
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
        except Exception:
            return False

    def release_mutex(self):
        """释放互斥锁"""
        if self._mutex_handle:
            try:
                kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
                kernel32.CloseHandle(self._mutex_handle)
            except Exception:
                pass
            self._mutex_handle = None

    # ========== 配置迁移 ==========

    def migrate_webui_config(self) -> dict:
        """从 WebUI 配置中提取原生桌面可用的设置

        Returns:
            包含 LLM/TTS/ASR 配置的字典
        """
        config = {}
        config_path = self.project_dir / "app" / "config.yaml"

        if not config_path.exists():
            return config

        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f)

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
            except Exception:
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
