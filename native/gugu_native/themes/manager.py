"""
咕咕嘎嘎 AI-VTuber — 主题管理器单例

ThemeManager 负责主题切换、颜色构建、回调通知和偏好持久化。
使用 initialize() 初始化后通过 instance() 全局访问。
"""

import json
import os
from typing import Callable

from qfluentwidgets import setTheme, Theme, setThemeColor
from PySide6.QtGui import QColor

from .registry import ThemeRegistry
from .definitions import ThemeDefinition


class ThemeManager:
    """主题管理器 — 单例模式，负责主题切换与通知"""

    _instance: 'ThemeManager | None' = None

    def __init__(self, registry: ThemeRegistry, prefs_path: str = "") -> None:
        """内部方法"""
        self._registry = registry
        self._current_id = "dark"
        self._colors = None  # AppColors 实例
        self._theme = None   # v5.0 AppTheme 实例
        self._callbacks: list[Callable] = []
        self._prefs_path = prefs_path

    @classmethod
    def instance(cls) -> 'ThemeManager':
        """获取 ThemeManager 单例实例

        Returns:
            ThemeManager 实例

        Raises:
            RuntimeError: 未调用 initialize() 初始化
        """
        if cls._instance is None:
            raise RuntimeError("ThemeManager not initialized")
        return cls._instance

    @classmethod
    def initialize(cls, registry: ThemeRegistry, prefs_path: str = "") -> 'ThemeManager':
        """初始化 ThemeManager 单例

        Args:
            registry: ThemeRegistry 实例
            prefs_path: 偏好持久化文件路径

        Returns:
            初始化后的 ThemeManager 实例
        """
        cls._instance = cls(registry, prefs_path)
        return cls._instance

    def apply(self, theme_id: str) -> None:
        """应用指定主题

        流程:
        1. 从注册中心获取 ThemeDefinition
        2. 设置 qfluentwidgets 主题和主题色
        3. 构建 AppColors 实例
        4. 通知所有回调

        Args:
            theme_id: 主题唯一标识
        """
        definition = self._registry.get(theme_id)
        if not definition:
            return

        self._current_id = theme_id

        # 1. qfluentwidgets 主题映射
        base = Theme.DARK if definition.base_mode == "dark" else Theme.LIGHT
        setTheme(base)
        setThemeColor(QColor(definition.colors.get("accent", "#4263eb")))

        # 2. 构建 AppColors + AppTheme（v5.0 多维度）
        from gugu_native.theme import AppColors
        self._colors = AppColors.from_definition(definition)
        
        # v5.0: 构建完整 AppTheme（含圆角/间距/阴影/字体/控件样式）
        self._theme = definition.to_app_theme()
        self._theme.colors = self._colors

        # 3. 通知回调
        for callback in self._callbacks:
            try:
                callback()
            except Exception as e:
                pass

    def get_colors(self):
        """获取当前颜色方案（AppColors 实例） — 兼容旧 API

        Returns:
            AppColors 实例
        """
        if self._colors is None:
            from gugu_native.theme import AppColors
            self._colors = AppColors()  # 默认暗色
        return self._colors

    def get_theme(self) -> None:
        """v5.0: 获取当前 AppTheme（含颜色+圆角+间距+阴影+字体+控件）

        Returns:
            AppTheme 实例，None 表示未初始化
        """
        if self._theme is None:
            # 回退：从 _colors 构建最小 AppTheme
            from gugu_native.themes.style_types import AppTheme
            self._theme = AppTheme(
                theme_id=self._current_id,
                display_name=self._current_id,
                base_mode="dark",
                colors=self.get_colors(),
            )
        return self._theme

    @classmethod
    def get_instance(cls) -> None:
        """获取 ThemeManager 单例（None-safe 版本）

        Returns:
            ThemeManager 实例或 None
        """
        return cls._instance

    def get_current_id(self) -> str:
        """获取当前主题 ID"""
        return self._current_id

    def is_dark(self) -> bool:
        """当前是否为暗色主题

        Returns:
            True 表示暗色主题
        """
        definition = self._registry.get(self._current_id)
        return definition.base_mode == "dark" if definition else True

    def register_callback(self, callback: Callable) -> None:
        """注册主题变更回调

        Args:
            callback: 回调函数（无参数）
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable) -> None:
        """反注册主题变更回调

        Args:
            callback: 之前注册的回调函数
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def get_registry(self) -> ThemeRegistry:
        """获取主题注册中心"""
        return self._registry

    def save_preferences(self) -> None:
        """保存当前主题偏好到文件"""
        data = {
            "theme_id": self._current_id,
            "custom_accent": None,
            "version": 1
        }
        try:
            prefs_dir = os.path.dirname(self._prefs_path)
            if prefs_dir:
                os.makedirs(prefs_dir, exist_ok=True)
            with open(self._prefs_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass

    def load_preferences(self) -> str:
        """从文件加载主题偏好

        Returns:
            偏好的主题 ID，加载失败时返回 "dark"
        """
        try:
            with open(self._prefs_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                theme_id = data.get("theme_id", "dark")
                if self._registry.get(theme_id):
                    return theme_id
        except Exception as e:
            pass
        return "dark"
