"""
全局快捷键管理器 — pynput 实现

功能:
- 全局快捷键注册/注销
- 预定义快捷键: 录音/停止/显示窗口/桌面宠物
- 支持组合键 (Ctrl+Alt+X)
- 快捷键配置持久化到 app/cache/hotkeys.json

预定义快捷键:
- Ctrl+Alt+R: 切换录音
- Ctrl+Alt+H: 显示/隐藏主窗口
- Ctrl+Alt+P: 切换桌面宠物
- Ctrl+Alt+S: 停止当前操作

使用方式:
    manager = HotkeyManager(main_window)
    manager.hotkey_triggered.connect(handler)
    manager.start()   # 开始监听
    manager.stop()    # 停止监听
"""

import os
import json
import threading
from PySide6.QtCore import QObject, Signal


# 默认快捷键配置
DEFAULT_HOTKEYS = {
    "toggle_record": "ctrl+alt+r",
    "show_window": "ctrl+alt+h",
    "toggle_pet": "ctrl+alt+p",
    "stop_action": "ctrl+alt+s",
}

HOTKEY_LABELS = {
    "toggle_record": "切换录音",
    "show_window": "显示/隐藏窗口",
    "toggle_pet": "切换桌面宠物",
    "stop_action": "停止当前操作",
}


class HotkeyManager(QObject):
    """
    全局快捷键管理器

    信号:
        hotkey_triggered(action): 快捷键触发，action 为配置名称
        error_occurred(error_msg): 错误
    """

    hotkey_triggered = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self._main_window = main_window
        self._listener = None
        self._is_running = False
        self._hotkeys = dict(DEFAULT_HOTKEYS)

        # 缓存路径（4层 dirname: widgets → gugu_native → native → project_root）
        project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self._config_path = os.path.join(project_dir, "app", "cache", "hotkeys.json")

        # 加载保存的配置
        self._load_config()

    def _load_config(self):
        """加载快捷键配置"""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                self._hotkeys.update(saved)
            except Exception:
                pass

    def _save_config(self):
        """保存快捷键配置"""
        try:
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._hotkeys, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[HotkeyManager] 保存配置失败: {e}")

    def start(self):
        """开始监听全局快捷键"""
        if self._is_running:
            return

        try:
            from pynput import keyboard
        except ImportError:
            self.error_occurred.emit("需要 pynput: pip install pynput")
            return

        try:
            # 构建 pynput 的热键映射
            hotkey_map = {}
            for action, key_combo in self._hotkeys.items():
                normalized = self._normalize_key(key_combo)
                hotkey_map[normalized] = lambda a=action: self.hotkey_triggered.emit(a)

            self._listener = keyboard.GlobalHotKeys(hotkey_map)
            self._listener.start()
            self._is_running = True
            print(f"[HotkeyManager] 全局快捷键已启动: {self._hotkeys}")
        except Exception as e:
            self.error_occurred.emit(f"快捷键启动失败: {e}")

    def stop(self):
        """停止监听"""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        self._is_running = False

    def cleanup(self):
        """清理资源 — 供 PerformanceManager 调用"""
        self.stop()
        self._main_window = None
        print("[HotkeyManager] cleanup completed")

    def update_hotkey(self, action: str, key_combo: str):
        """更新快捷键配置"""
        if action in self._hotkeys:
            self._hotkeys[action] = key_combo
            self._save_config()

            # 如果正在运行，需要重启监听
            if self._is_running:
                self.stop()
                self.start()

    def get_hotkeys(self) -> dict:
        """获取当前快捷键配置"""
        return dict(self._hotkeys)

    def _normalize_key(self, key_combo: str) -> str:
        """
        将快捷键字符串规范化为 pynput 格式

        "ctrl+alt+r" -> "<ctrl>+<alt>+r"
        """
        parts = key_combo.lower().split("+")
        normalized = []
        for part in parts:
            part = part.strip()
            if part in ("ctrl", "alt", "shift", "cmd", "win"):
                normalized.append(f"<{part}>")
            elif part == "space":
                normalized.append("<space>")
            elif len(part) == 1:
                normalized.append(part)
            else:
                normalized.append(part)
        return "+".join(normalized)

    @property
    def is_running(self):
        return self._is_running
