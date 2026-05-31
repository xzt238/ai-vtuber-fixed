"""咕咕嘎嘎 AI-VTuber — 森林预设主题

深绿色调暗色主题，灵感来自森林。
"""

from ..definitions import ThemeDefinition
from gugu_native.themes.style_types import (
    BorderRadiusStyle, SpacingStyle, ShadowStyle, TypographyStyle, ControlStyle
)

FOREST_THEME = ThemeDefinition(
    id="forest",
    name="森林",
    description="自然森林绿色调，护眼舒适",
    base_mode="dark",
    preview_colors=["#0f1a12", "#2f9e44", "#40c057"],
    colors={
        "window_bg": "#0f1a12",
        "sidebar_bg": "#0a140d",
        "card_bg": "#152218",
        "card_bg_hover": "#1a2a1e",
        "card_border": "#1e3022",
        "card_border_hover": "#26402a",
        "text_primary": "#e0f0e0",
        "text_secondary": "#8aaa8a",
        "text_muted": "#5a7a5a",
        "text_on_accent": "#ffffff",
        "accent": "#2f9e44",
        "accent_hover": "#2b8c3e",
        "accent_pressed": "#277a38",
        "accent_gradient_start": "#40c057",
        "accent_gradient_end": "#2f9e44",
        "success": "#2f9e44",
        "success_bg": "#1a3020",
        "warning": "#e6a817",
        "warning_bg": "#30281a",
        "error": "#d93030",
        "error_bg": "#301a1a",
        "info": "#2f9e44",
        "info_bg": "#1a241a",
        "input_bg": "#102014",
        "input_border": "#1e3022",
        "input_focus_border": "#2f9e44",
        "input_focus_shadow": "rgba(47,158,68,0.25)",
        "log_bg": "#0a140d",
        "log_text": "#c9d9c9",
        "log_timestamp": "#5a7a5a",
        "log_success": "#2f9e44",
        "log_error": "#d93030",
        "log_info": "#2f9e44",
        "progress_start": "#2f9e44",
        "progress_end": "#40c057",
        "shadow_sm": "rgba(0,0,0,0.2)",
        "shadow_md": "rgba(0,0,0,0.3)",
        "shadow_lg": "rgba(0,0,0,0.4)",
        "shadow_xl": "rgba(0,0,0,0.5)",
        "timestamp_color": "#5a7a5a",
        "divider": "#1e3022",
    },
    border_radius=BorderRadiusStyle.from_preset("sharp"),
    spacing=SpacingStyle.from_preset("compact"),
    shadow=ShadowStyle.from_preset("material"),
    typography=TypographyStyle.from_preset("jetbrains"),
    controls=ControlStyle.from_preset("ghost"),
)
