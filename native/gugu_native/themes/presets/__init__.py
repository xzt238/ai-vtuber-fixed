"""
咕咕嘎嘎 AI-VTuber — 预设主题包

提供 10 套内置预设主题:
- dark: 深色（默认暗色，与原 AppColors 完全一致）
- light: 浅色（与原 LightColors 完全一致）
- ocean: 海洋（深蓝暗色）
- lavender: 薰衣草（紫罗兰暗色）
- sakura: 樱花（浅粉亮色）
- forest: 森林（深绿暗色）
- sunset: 落日（暖橙暗色）
- arctic: 极光（冰蓝亮色）
- vscode_dark: VS Code Dark（锐利专业风格）
- discord: Discord（柔和社区风格）
"""

from .dark import DARK_THEME
from .light import LIGHT_THEME
from .ocean import OCEAN_THEME
from .lavender import LAVENDER_THEME
from .sakura import SAKURA_THEME
from .forest import FOREST_THEME
from .sunset import SUNSET_THEME
from .arctic import ARCTIC_THEME
from .vscode_dark import VSCODE_DARK_THEME
from .discord import DISCORD_THEME

from ..registry import ThemeRegistry


def register_all_presets(registry: ThemeRegistry) -> None:
    """将所有预设主题注册到 ThemeRegistry

    Args:
        registry: ThemeRegistry 实例
    """
    for theme in [DARK_THEME, LIGHT_THEME, OCEAN_THEME, LAVENDER_THEME,
                  SAKURA_THEME, FOREST_THEME, SUNSET_THEME, ARCTIC_THEME,
                  VSCODE_DARK_THEME, DISCORD_THEME]:
        registry.register(theme)
