"""
咕咕嘎嘎 AI-VTuber — VS Code Dark 预设主题

参考 Visual Studio Code 默认暗色主题风格:
- 锐利直角 + 紧凑间距 + 扁平无阴影
- JetBrains Mono 等宽字体 + Outline 按钮风格
"""

from ..definitions import ThemeDefinition

from gugu_native.themes.style_types import (
    BorderRadiusStyle, SpacingStyle, ShadowStyle, TypographyStyle, ControlStyle
)

VSCODE_DARK_THEME = ThemeDefinition(
    id="vscode_dark",
    name="VS Code Dark",
    description="参考 VS Code 默认暗色主题，锐利专业风格",
    base_mode="dark",
    preview_colors=["#1e1e1e", "#007acc", "#569cd6"],
    colors={
        # === 窗口 ===
        "window_bg": "#1e1e1e",
        "sidebar_bg": "#252526",
        "card_bg": "#2d2d30",
        "card_bg_hover": "#3e3e42",
        "card_border": "#3e3e42",
        "card_border_hover": "#525257",

        # === 对话区 ===
        "chat_bg": "#1e1e1e",
        "ai_bubble_bg": "#2d2d30",
        "ai_bubble_border": "#3e3e42",
        "ai_bubble_accent": "#007acc",
        "user_bubble_bg": "#007acc",
        "user_bubble_border": "#1a8ad4",
        "user_bubble_accent": "#1a8ad4",
        "user_text_color": "#ffffff",
        "system_msg_color": "#858585",
        "skeleton_color": "#2d2d30",
        "skeleton_shimmer": "#3e3e42",
        "chat_timestamp_bg": "#252526",
        "chat_timestamp_border": "#3e3e42",
        "chat_group_gap": "12px",
        "chat_same_gap": "4px",
        "chat_bubble_max_width": "80%",
        "chat_avatar_size": "34",
        "chat_bubble_padding": "10px 16px",
        "chat_bubble_radius_ai": "4px",
        "chat_bubble_radius_user": "4px",
        "chat_typing_cursor_color": "#007acc",

        # === 文字 ===
        "text_primary": "#cccccc",
        "text_secondary": "#858585",
        "text_muted": "#6a6a6a",
        "text_on_accent": "#ffffff",

        # === 强调色 ===
        "accent": "#007acc",
        "accent_hover": "#1a8ad4",
        "accent_pressed": "#005a9e",
        "accent_gradient_start": "#1a8ad4",
        "accent_gradient_end": "#007acc",

        # === 语义色 ===
        "success": "#4ec9b0",
        "success_bg": "#1a2b28",
        "warning": "#cca700",
        "warning_bg": "#2e2a1a",
        "error": "#f14c4c",
        "error_bg": "#2e1a1a",
        "info": "#569cd6",
        "info_bg": "#1a2430",

        # === 统计卡片 ===
        "stat_working": "#569cd6",
        "stat_episodic": "#4ec9b0",
        "stat_semantic": "#c586c0",
        "stat_facts": "#dcdcaa",
        "stat_forgotten": "#6c6c6c",

        # === 输入控件 ===
        "input_bg": "#3c3c3c",
        "input_border": "#3e3e42",
        "input_focus_border": "#007acc",
        "input_focus_shadow": "rgba(0,122,204,0.25)",

        # === 训练日志 ===
        "log_bg": "#1e1e1e",
        "log_text": "#d4d4d4",
        "log_timestamp": "#6a6a6a",
        "log_success": "#4ec9b0",
        "log_error": "#f14c4c",
        "log_info": "#569cd6",

        # === 进度条 ===
        "progress_start": "#007acc",
        "progress_end": "#569cd6",

        # === 阴影 ===
        "shadow_sm": "rgba(0,0,0,0.2)",
        "shadow_md": "rgba(0,0,0,0.3)",
        "shadow_lg": "rgba(0,0,0,0.4)",
        "shadow_xl": "rgba(0,0,0,0.5)",

        # === 时间戳 ===
        "timestamp_color": "#6a6a6a",

        # === 分割线 ===
        "divider": "#3e3e42",
    },

    border_radius=BorderRadiusStyle.from_preset("sharp"),
    spacing=SpacingStyle.from_preset("compact"),
    shadow=ShadowStyle.from_preset("flat"),
    typography=TypographyStyle.from_preset("jetbrains"),
    controls=ControlStyle.from_preset("outline"),
)
