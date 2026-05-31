"""
咕咕嘎嘎 AI-VTuber — 深色预设主题

与原始 AppColors 默认值完全一致，确保 100% 向后兼容。
"""

from ..definitions import ThemeDefinition
from gugu_native.themes.style_types import (
    BorderRadiusStyle, SpacingStyle, ShadowStyle, TypographyStyle, ControlStyle
)

DARK_THEME = ThemeDefinition(
    id="dark",
    name="深色",
    description="经典深色主题，沉稳护眼",
    base_mode="dark",
    preview_colors=["#1a1b2e", "#4263eb", "#7c3aed"],
    colors={
        "window_bg": "#1a1b2e",
        "sidebar_bg": "#151627",
        "card_bg": "#232438",
        "card_bg_hover": "#2a2b42",
        "card_border": "#2e2f48",
        "card_border_hover": "#3a3b58",

        "chat_bg": "#1a1b2e",
        "ai_bubble_bg": "#2a2d3e",
        "ai_bubble_border": "#353856",
        "ai_bubble_accent": "#7c3aed",
        "user_bubble_bg": "#4263eb",
        "user_bubble_border": "#5c7cfa",
        "user_bubble_accent": "#5c7cfa",
        "user_text_color": "#ffffff",
        "system_msg_color": "#6c6c8a",
        "skeleton_color": "#2a2b42",
        "skeleton_shimmer": "#353655",
        "chat_timestamp_bg": "#1e2030",
        "chat_timestamp_border": "#2a2b42",
        "chat_group_gap": "12px",
        "chat_same_gap": "4px",
        "chat_bubble_max_width": "80%",
        "chat_avatar_size": "34",
        "chat_bubble_padding": "10px 16px",
        "chat_bubble_radius_ai": "12px",
        "chat_bubble_radius_user": "12px",
        "chat_typing_cursor_color": "#4263eb",

        "text_primary": "#e8e8f0",
        "text_secondary": "#9a9ab0",
        "text_muted": "#5c5c72",
        "text_on_accent": "#ffffff",

        "accent": "#4263eb",
        "accent_hover": "#3b5bdb",
        "accent_pressed": "#3549c6",
        "accent_gradient_start": "#5c7cfa",
        "accent_gradient_end": "#4263eb",

        "success": "#37b24d",
        "success_bg": "#1a3a2a",
        "warning": "#f59f00",
        "warning_bg": "#3a331a",
        "error": "#f03e3e",
        "error_bg": "#3a1a1a",
        "info": "#4263eb",
        "info_bg": "#1a2238",

        "stat_working": "#4dabf7",
        "stat_episodic": "#69db7c",
        "stat_semantic": "#da77f2",
        "stat_facts": "#ffd43b",
        "stat_forgotten": "#868e96",

        "input_bg": "#1e1f34",
        "input_border": "#2e2f48",
        "input_focus_border": "#4263eb",
        "input_focus_shadow": "rgba(66,99,235,0.25)",

        "log_bg": "#0d0e1a",
        "log_text": "#c9d1d9",
        "log_timestamp": "#5c5c72",
        "log_success": "#37b24d",
        "log_error": "#f03e3e",
        "log_info": "#4dabf7",

        "progress_start": "#4263eb",
        "progress_end": "#7c3aed",

        "shadow_sm": "rgba(0,0,0,0.15)",
        "shadow_md": "rgba(0,0,0,0.25)",
        "shadow_lg": "rgba(0,0,0,0.35)",
        "shadow_xl": "rgba(0,0,0,0.45)",

        "timestamp_color": "#5c5c72",

        "divider": "#2e2f48",
    },

    border_radius=BorderRadiusStyle.from_preset("soft"),
    spacing=SpacingStyle.from_preset("comfortable"),
    shadow=ShadowStyle.from_preset("material"),
    typography=TypographyStyle.from_preset("msyh"),
    controls=ControlStyle.from_preset("solid"),
)
