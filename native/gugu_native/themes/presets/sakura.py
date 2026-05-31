"""咕咕嘎嘎 AI-VTuber — 樱花预设主题

粉色调亮色主题，灵感来自樱花。
"""

from ..definitions import ThemeDefinition
from gugu_native.themes.style_types import (
    BorderRadiusStyle, SpacingStyle, ShadowStyle, TypographyStyle, ControlStyle
)

SAKURA_THEME = ThemeDefinition(
    id="sakura",
    name="樱花",
    description="柔美的樱花粉色调，温暖可爱",
    base_mode="light",
    preview_colors=["#fdf2f5", "#e64980", "#f06595"],
    colors={
        "window_bg": "#fdf2f5",
        "sidebar_bg": "#fae8ee",
        "card_bg": "#ffffff",
        "card_bg_hover": "#fef5f7",
        "card_border": "#f0d8e0",
        "card_border_hover": "#e4b8c8",
        "text_primary": "#2e1a22",
        "text_secondary": "#665566",
        "text_muted": "#aa99aa",
        "text_on_accent": "#ffffff",
        "accent": "#e64980",
        "accent_hover": "#d43870",
        "accent_pressed": "#c02860",
        "accent_gradient_start": "#f06595",
        "accent_gradient_end": "#e64980",
        "success": "#37b24d",
        "success_bg": "#d3f9d8",
        "warning": "#f59f00",
        "warning_bg": "#fff3bf",
        "error": "#e03131",
        "error_bg": "#ffe0e0",
        "info": "#e64980",
        "info_bg": "#fce0e8",
        "input_bg": "#ffffff",
        "input_border": "#f0d8e0",
        "input_focus_border": "#e64980",
        "input_focus_shadow": "rgba(230,73,128,0.15)",
        "log_bg": "#fef8fa",
        "log_text": "#212529",
        "log_timestamp": "#aa99aa",
        "log_success": "#37b24d",
        "log_error": "#e03131",
        "log_info": "#e64980",
        "progress_start": "#e64980",
        "progress_end": "#f06595",
        "shadow_sm": "rgba(0,0,0,0.05)",
        "shadow_md": "rgba(0,0,0,0.08)",
        "shadow_lg": "rgba(0,0,0,0.12)",
        "shadow_xl": "rgba(0,0,0,0.16)",
        "timestamp_color": "#aa99aa",
        "divider": "#f0d8e0",
    },
    border_radius=BorderRadiusStyle.from_preset("rounded"),
    spacing=SpacingStyle.from_preset("spacious"),
    shadow=ShadowStyle.from_preset("material"),
    typography=TypographyStyle.from_preset("msyh"),
    controls=ControlStyle.from_preset("solid"),
)
