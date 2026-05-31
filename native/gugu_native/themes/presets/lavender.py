"""咕咕嘎嘎 AI-VTuber — 薰衣草预设主题

紫罗兰色调暗色主题，灵感来自薰衣草。
"""

from ..definitions import ThemeDefinition
from gugu_native.themes.style_types import (
    BorderRadiusStyle, SpacingStyle, ShadowStyle, TypographyStyle, ControlStyle
)

LAVENDER_THEME = ThemeDefinition(
    id="lavender",
    name="薰衣草",
    description="优雅的薰衣草紫色调，温柔舒缓",
    base_mode="dark",
    preview_colors=["#1a1528", "#7950f2", "#9775fa"],
    colors={
        "window_bg": "#1a1528",
        "sidebar_bg": "#141022",
        "card_bg": "#221a32",
        "card_bg_hover": "#2a2040",
        "card_border": "#2e2448",
        "card_border_hover": "#3a2e58",
        "text_primary": "#e8e0f0",
        "text_secondary": "#a8a0c0",
        "text_muted": "#6a6080",
        "text_on_accent": "#ffffff",
        "accent": "#7950f2",
        "accent_hover": "#6a40e0",
        "accent_pressed": "#5a30c8",
        "accent_gradient_start": "#9775fa",
        "accent_gradient_end": "#7950f2",
        "success": "#37b24d",
        "success_bg": "#1a3a2a",
        "warning": "#f59f00",
        "warning_bg": "#3a331a",
        "error": "#f03e3e",
        "error_bg": "#3a1a1a",
        "info": "#7950f2",
        "info_bg": "#1a203a",
        "input_bg": "#1c1630",
        "input_border": "#2e2448",
        "input_focus_border": "#7950f2",
        "input_focus_shadow": "rgba(121,80,242,0.25)",
        "log_bg": "#141022",
        "log_text": "#c9c0d9",
        "log_timestamp": "#6a6080",
        "log_success": "#37b24d",
        "log_error": "#f03e3e",
        "log_info": "#7950f2",
        "progress_start": "#7950f2",
        "progress_end": "#9775fa",
        "shadow_sm": "rgba(0,0,0,0.2)",
        "shadow_md": "rgba(0,0,0,0.3)",
        "shadow_lg": "rgba(0,0,0,0.4)",
        "shadow_xl": "rgba(0,0,0,0.5)",
        "timestamp_color": "#6a6080",
        "divider": "#2e2448",
    },
    border_radius=BorderRadiusStyle.from_preset("rounded"),
    spacing=SpacingStyle.from_preset("comfortable"),
    shadow=ShadowStyle.from_preset("glow", accent_color="#7950f2"),
    typography=TypographyStyle.from_preset("msyh"),
    controls=ControlStyle.from_preset("solid"),
)
