"""
咕咕嘎嘎 AI-VTuber — Discord 预设主题

参考 Discord 桌面应用暗色主题风格:
- 柔和圆角 + 舒适间距 + Material 阴影
- Inter 字体 + Solid 实心按钮
"""

from ..definitions import ThemeDefinition

from gugu_native.themes.style_types import (
    BorderRadiusStyle, SpacingStyle, ShadowStyle, TypographyStyle, ControlStyle
)

DISCORD_THEME = ThemeDefinition(
    id="discord",
    name="Discord",
    description="参考 Discord 桌面应用风格，舒适的社区交流感",
    base_mode="dark",
    preview_colors=["#313338", "#5865f2", "#57f287"],
    colors={
        # === 窗口 ===
        "window_bg": "#313338",
        "sidebar_bg": "#2b2d31",
        "card_bg": "#383a40",
        "card_bg_hover": "#404249",
        "card_border": "#404249",
        "card_border_hover": "#4e5058",

        # === 对话区 ===
        "chat_bg": "#313338",
        "ai_bubble_bg": "#383a40",
        "ai_bubble_border": "#404249",
        "ai_bubble_accent": "#5865f2",
        "user_bubble_bg": "#5865f2",
        "user_bubble_border": "#6d75f5",
        "user_bubble_accent": "#6d75f5",
        "user_text_color": "#ffffff",
        "system_msg_color": "#949ba4",
        "skeleton_color": "#383a40",
        "skeleton_shimmer": "#404249",
        "chat_timestamp_bg": "#2b2d31",
        "chat_timestamp_border": "#404249",
        "chat_group_gap": "12px",
        "chat_same_gap": "4px",
        "chat_bubble_max_width": "80%",
        "chat_avatar_size": "34",
        "chat_bubble_padding": "10px 16px",
        "chat_bubble_radius_ai": "12px",
        "chat_bubble_radius_user": "12px",
        "chat_typing_cursor_color": "#5865f2",

        # === 文字 ===
        "text_primary": "#dbdee1",
        "text_secondary": "#949ba4",
        "text_muted": "#6d6f78",
        "text_on_accent": "#ffffff",

        # === 强调色 ===
        "accent": "#5865f2",
        "accent_hover": "#4752c4",
        "accent_pressed": "#3c45a5",
        "accent_gradient_start": "#6d75f5",
        "accent_gradient_end": "#5865f2",

        # === 语义色 ===
        "success": "#57f287",
        "success_bg": "#1a3a28",
        "warning": "#fee75c",
        "warning_bg": "#3a361a",
        "error": "#ed4245",
        "error_bg": "#3a1a1a",
        "info": "#5865f2",
        "info_bg": "#1a1e3a",

        # === 统计卡片 ===
        "stat_working": "#5865f2",
        "stat_episodic": "#57f287",
        "stat_semantic": "#eb459e",
        "stat_facts": "#fee75c",
        "stat_forgotten": "#6d6f78",

        # === 输入控件 ===
        "input_bg": "#383a40",
        "input_border": "#404249",
        "input_focus_border": "#5865f2",
        "input_focus_shadow": "rgba(88,101,242,0.25)",

        # === 训练日志 ===
        "log_bg": "#2b2d31",
        "log_text": "#dbdee1",
        "log_timestamp": "#6d6f78",
        "log_success": "#57f287",
        "log_error": "#ed4245",
        "log_info": "#5865f2",

        # === 进度条 ===
        "progress_start": "#5865f2",
        "progress_end": "#eb459e",

        # === 阴影 ===
        "shadow_sm": "rgba(0,0,0,0.2)",
        "shadow_md": "rgba(0,0,0,0.3)",
        "shadow_lg": "rgba(0,0,0,0.4)",
        "shadow_xl": "rgba(0,0,0,0.5)",

        # === 时间戳 ===
        "timestamp_color": "#6d6f78",

        # === 分割线 ===
        "divider": "#404249",
    },

    border_radius=BorderRadiusStyle.from_preset("soft"),
    spacing=SpacingStyle.from_preset("comfortable"),
    shadow=ShadowStyle.from_preset("material"),
    typography=TypographyStyle.from_preset("inter"),
    controls=ControlStyle.from_preset("solid"),
)
