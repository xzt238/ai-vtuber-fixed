"""咕咕嘎嘎 AI-VTuber — 极光预设主题

冰蓝色调亮色主题，灵感来自极光。
"""

from ..definitions import ThemeDefinition
from gugu_native.themes.style_types import (
    BorderRadiusStyle, SpacingStyle, ShadowStyle, TypographyStyle, ControlStyle
)

ARCTIC_THEME = ThemeDefinition(
    id="arctic",
    name="极光",
    description="冰蓝极光色调，清冷通透",
    base_mode="light",
    preview_colors=["#f0f5f7", "#0c8599", "#15aabf"],
    colors={
        "window_bg": "#f0f5f7",
        "sidebar_bg": "#e8f0f2",
        "card_bg": "#ffffff",
        "card_bg_hover": "#f5f9fa",
        "card_border": "#d8e4e8",
        "card_border_hover": "#b8cdd4",
        "text_primary": "#1a2a2e",
        "text_secondary": "#55666a",
        "text_muted": "#99aaae",
        "text_on_accent": "#ffffff",
        "accent": "#0c8599",
        "accent_hover": "#0b7588",
        "accent_pressed": "#0a6577",
        "accent_gradient_start": "#15aabf",
        "accent_gradient_end": "#0c8599",
        "success": "#2f9e44",
        "success_bg": "#d3f9d8",
        "warning": "#f59f00",
        "warning_bg": "#fff3bf",
        "error": "#e03131",
        "error_bg": "#ffe0e0",
        "info": "#0c8599",
        "info_bg": "#e0f4f8",
        "input_bg": "#ffffff",
        "input_border": "#d0d8dc",
        "input_focus_border": "#0c8599",
        "input_focus_shadow": "rgba(12,133,153,0.15)",
        "log_bg": "#f8fafa",
        "log_text": "#212529",
        "log_timestamp": "#99aaae",
        "log_success": "#2f9e44",
        "log_error": "#e03131",
        "log_info": "#0c8599",
        "progress_start": "#0c8599",
        "progress_end": "#15aabf",
        "shadow_sm": "rgba(0,0,0,0.05)",
        "shadow_md": "rgba(0,0,0,0.08)",
        "shadow_lg": "rgba(0,0,0,0.12)",
        "shadow_xl": "rgba(0,0,0,0.16)",
        "timestamp_color": "#99aaae",
        "divider": "#d8e4e8",
    },
    border_radius=BorderRadiusStyle.from_preset("sharp"),
    spacing=SpacingStyle.from_preset("compact"),
    shadow=ShadowStyle.from_preset("neumorphic"),
    typography=TypographyStyle.from_preset("inter"),
    controls=ControlStyle.from_preset("ghost"),
)
