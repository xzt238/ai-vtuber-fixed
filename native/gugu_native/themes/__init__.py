"""
咕咕嘎嘎 AI-VTuber — 主题管理包

提供主题注册、切换、颜色衍生等核心能力:
- ThemeDefinition: 主题定义数据类
- ThemeRegistry: 主题注册中心
- ThemeManager: 主题管理器单例（切换/回调/持久化）
- ColorDeriver: 基于 accent 的颜色自动衍生
- AppTheme / BorderRadiusStyle / SpacingStyle / ShadowStyle / TypographyStyle / ControlStyle: v5.0 多维度风格类型
"""

from .definitions import ThemeDefinition
from .registry import ThemeRegistry, ColorDeriver
from .manager import ThemeManager
from .style_types import (
    BorderRadiusStyle, SpacingStyle, ShadowStyle,
    TypographyStyle, ControlStyle, AppTheme,
)

__all__ = [
    "ThemeDefinition",
    "ThemeRegistry",
    "ColorDeriver",
    "ThemeManager",
    "AppTheme",
    "BorderRadiusStyle",
    "SpacingStyle",
    "ShadowStyle",
    "TypographyStyle",
    "ControlStyle",
]