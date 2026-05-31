"""咕咕嘎嘎 AI-VTuber — 落日预设主题

暖橙色调暗色主题，灵感来自落日。
"""

from ..definitions import ThemeDefinition
from gugu_native.themes.style_types import (
    BorderRadiusStyle, SpacingStyle, ShadowStyle, TypographyStyle, ControlStyle
)

SUNSET_THEME = ThemeDefinition(
    id="sunset",
    name="落日",
    description="温暖的落日橙色调，充满活力",
    base_mode="dark",
    preview_colors=["#1f1410", "#e8590c", "#f08c00"],
    colors={
        "window_bg": "#1f1410",
        "sidebar_bg": "#180e0a",
        "card_bg": "#281a14",
        "card_bg_hover": "#302018",
        "card_border": "#382820",
        "card_border_hover": "#483028",
        "text_primary": "#f0e8e0",
        "text_secondary": "#b0a090",
        "text_muted": "#706050",
        "text_on_accent": "#ffffff",
        "accent": "#e8590c",
        "accent_hover": "#d9480b",
        "accent_pressed": "#c8380a",
        "accent_gradient_start": "#f08c00",
        "accent_gradient_end": "#e8590c",
        "success": "#37b24d",
        "success_bg": "#1a3a2a",
        "warning": "#f59f00",
        "warning_bg": "#3a301a",
        "error": "#f03e3e",
        "error_bg": "#3a1a1a",
        "info": "#e8590c",
        "info_bg": "#301a10",
        "input_bg": "#221610",
        "input_border": "#382820",
        "input_focus_border": "#e8590c",
        "input_focus_shadow": "rgba(232,89,12,0.25)",
        "log_bg": "#180e0a",
        "log_text": "#d9c9c0",
        "log_timestamp": "#706050",
        "log_success": "#37b24d",
        "log_error": "#f03e3e",
        "log_info": "#e8590c",
        "progress_start": "#e8590c",
        "progress_end": "#f08c00",
        "shadow_sm": "rgba(0,0,0,0.2)",
        "shadow_md": "rgba(0,0,0,0.3)",
        "shadow_lg": "rgba(0,0,0,0.4)",
        "shadow_xl": "rgba(0,0,0,0.5)",
        "timestamp_color": "#706050",
        "divider": "#382820",
    },
    border_radius=BorderRadiusStyle.from_preset("rounded"),
    spacing=SpacingStyle.from_preset("spacious"),
    shadow=ShadowStyle.from_preset("material"),
    typography=TypographyStyle.from_preset("msyh"),
    controls=ControlStyle.from_preset("solid"),
)
