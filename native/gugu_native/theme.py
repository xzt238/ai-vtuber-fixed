"""
咕咕嘎嘎 AI-VTuber — 统一主题管理 v3.0

职责:
1. 集中定义颜色常量（暗色/亮色两套方案）
2. 生成全局 QSS 样式表
3. 一键切换主题并通知所有页面
4. 消除各页面散落的硬编码颜色
5. Material Elevation 阴影系统
6. 按钮渐变/悬停/按下状态
7. 输入框聚焦发光效果
8. 对话气泡 HTML 生成（微信级消息分组+条件头像+条件时间戳）
9. SVG 内联头像（AI 机器人 + 用户轮廓）

参考: 微信 / QQ / Telegram / ChatGPT Desktop / Discord 暗色设计规范
"""

from dataclasses import dataclass, field
from typing import Optional, Callable, List

from qfluentwidgets import setTheme, Theme, isDarkTheme, setThemeColor
from PySide6.QtGui import QColor


# 主题变更回调列表 — 各页面注册后主题切换时自动通知
_theme_change_callbacks: List[Callable] = []


def register_theme_callback(callback: Callable):
    """注册主题变更回调 — 页面在 __init__ 中调用"""
    _theme_change_callbacks.append(callback)


def unregister_theme_callback(callback: Callable):
    """反注册主题变更回调"""
    try:
        _theme_change_callbacks.remove(callback)
    except ValueError:
        pass


@dataclass
class AppColors:
    """应用颜色方案 — 暗色默认"""

    # === 窗口 ===
    window_bg: str = "#1a1b2e"
    sidebar_bg: str = "#151627"
    card_bg: str = "#232438"
    card_bg_hover: str = "#2a2b42"
    card_border: str = "#2e2f48"
    card_border_hover: str = "#3a3b58"

    # === 对话区 — 微信风格左右分列气泡 ===
    chat_bg: str = "#1a1b2e"
    ai_bubble_bg: str = "#2a2d3e"             # AI气泡中性灰底
    ai_bubble_border: str = "#353856"          # AI气泡细边框
    ai_bubble_accent: str = "#7c3aed"          # (保留字段，不再用于竖条)
    user_bubble_bg: str = "#4263eb"            # 用户气泡品牌蓝底(微信绿→品牌蓝)
    user_bubble_border: str = "#5c7cfa"        # 用户气泡(仅图片气泡用)
    user_bubble_accent: str = "#5c7cfa"        # (保留字段，不再用于竖条)
    user_text_color: str = "#ffffff"           # 用户气泡白色文字(蓝底白字)
    system_msg_color: str = "#6c6c8a"
    skeleton_color: str = "#2a2b42"
    skeleton_shimmer: str = "#353655"
    # 对话分组
    chat_timestamp_bg: str = "#1e2030"
    chat_timestamp_border: str = "#2a2b42"
    chat_group_gap: str = "12px"             # 新对话组的上间距
    chat_same_gap: str = "4px"               # 同组连续消息间距
    chat_bubble_max_width: str = "80%"       # 气泡最大宽度
    chat_avatar_size: int = 34               # 头像尺寸(px)
    chat_bubble_padding: str = "10px 16px"
    chat_bubble_radius_ai: str = "12px"
    chat_bubble_radius_user: str = "12px"
    chat_typing_cursor_color: str = "#4263eb"

    # === 文字 ===
    text_primary: str = "#e8e8f0"
    text_secondary: str = "#9a9ab0"
    text_muted: str = "#5c5c72"
    text_on_accent: str = "#ffffff"

    # === 强调色 ===
    accent: str = "#4263eb"
    accent_hover: str = "#3b5bdb"
    accent_pressed: str = "#3549c6"
    accent_gradient_start: str = "#5c7cfa"
    accent_gradient_end: str = "#4263eb"
    success: str = "#37b24d"
    success_bg: str = "#1a3a2a"
    warning: str = "#f59f00"
    warning_bg: str = "#3a331a"
    error: str = "#f03e3e"
    error_bg: str = "#3a1a1a"
    info: str = "#4263eb"
    info_bg: str = "#1a2238"

    # === 统计卡片 ===
    stat_working: str = "#4dabf7"
    stat_episodic: str = "#69db7c"
    stat_semantic: str = "#da77f2"
    stat_facts: str = "#ffd43b"
    stat_forgotten: str = "#868e96"

    # === 输入控件 ===
    input_bg: str = "#1e1f34"
    input_border: str = "#2e2f48"
    input_focus_border: str = "#4263eb"
    input_focus_shadow: str = "rgba(66,99,235,0.25)"

    # === 训练日志 ===
    log_bg: str = "#0d0e1a"
    log_text: str = "#c9d1d9"
    log_timestamp: str = "#5c5c72"
    log_success: str = "#37b24d"
    log_error: str = "#f03e3e"
    log_info: str = "#4dabf7"

    # === 进度条 ===
    progress_start: str = "#4263eb"
    progress_end: str = "#7c3aed"

    # === 阴影 (Material Elevation) ===
    shadow_sm: str = "rgba(0,0,0,0.15)"
    shadow_md: str = "rgba(0,0,0,0.25)"
    shadow_lg: str = "rgba(0,0,0,0.35)"
    shadow_xl: str = "rgba(0,0,0,0.45)"

    # === 时间戳 ===
    timestamp_color: str = "#5c5c72"

    # === 分割线 ===
    divider: str = "#2e2f48"


@dataclass
class LightColors(AppColors):
    """亮色方案"""
    window_bg: str = "#f0f2f5"
    sidebar_bg: str = "#e8eaed"
    card_bg: str = "#ffffff"
    card_bg_hover: str = "#f8f9fa"
    card_border: str = "#e0e2e8"
    card_border_hover: str = "#c8cad2"

    chat_bg: str = "#f0f2f5"
    ai_bubble_bg: str = "#ffffff"
    ai_bubble_border: str = "#dee2e6"
    ai_bubble_accent: str = "#7c3aed"
    user_bubble_bg: str = "#4263eb"
    user_bubble_border: str = "#5c7cfa"
    user_bubble_accent: str = "#5c7cfa"
    user_text_color: str = "#ffffff"
    system_msg_color: str = "#868e96"
    skeleton_color: str = "#e9ecef"
    skeleton_shimmer: str = "#f1f3f5"
    # 对话分组（亮色）
    chat_timestamp_bg: str = "#e9ecef"
    chat_timestamp_border: str = "#dee2e6"
    chat_typing_cursor_color: str = "#4263eb"

    text_primary: str = "#1a1a2e"
    text_secondary: str = "#555566"
    text_muted: str = "#9a9aaa"
    text_on_accent: str = "#ffffff"

    input_bg: str = "#ffffff"
    input_border: str = "#d0d2d8"
    input_focus_border: str = "#4263eb"
    input_focus_shadow: str = "rgba(66,99,235,0.15)"

    log_bg: str = "#f8f9fa"
    log_text: str = "#212529"
    log_timestamp: str = "#868e96"

    timestamp_color: str = "#868e96"
    divider: str = "#e0e2e8"

    shadow_sm: str = "rgba(0,0,0,0.06)"
    shadow_md: str = "rgba(0,0,0,0.10)"
    shadow_lg: str = "rgba(0,0,0,0.15)"
    shadow_xl: str = "rgba(0,0,0,0.20)"


# === 全局单例 ===
_colors: AppColors = AppColors()
_current_theme: Theme = Theme.DARK


def get_colors() -> AppColors:
    """获取当前颜色方案"""
    return _colors


def is_dark() -> bool:
    """当前是否为暗色主题"""
    return _current_theme == Theme.DARK


def apply_theme(theme: Theme):
    """应用主题"""
    global _colors, _current_theme

    _current_theme = theme
    setTheme(theme)

    if theme == Theme.DARK:
        _colors = AppColors()
    else:
        _colors = LightColors()

    # 设置 qfluentwidgets 主题色
    setThemeColor(QColor(_colors.accent))

    # 通知所有注册的页面刷新主题
    for callback in _theme_change_callbacks:
        try:
            callback()
        except Exception:
            pass


def get_global_qss() -> str:
    """生成全局 QSS 样式表（基于当前颜色方案）— v2.0 增强版"""
    c = _colors
    return f"""
        /* === 全局字体与基础 === */
        QWidget {{
            font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
        }}

        /* === 对话区 — 更大圆角 + 无边框（内联样式优先，此处为兜底） === */
        QTextEdit[objectName="chatDisplay"] {{
            background-color: {c.chat_bg};
            color: {c.text_primary};
            border: none;
            border-radius: 13px;
            padding: 14px 16px;
            selection-background-color: {c.accent};
            selection-color: white;
        }}

        /* === 卡片容器 — 避免全局 QWidget 样式污染 === */
        QFrame[objectName="chatCard"],
        QFrame[objectName="inputCard"],
        QFrame[objectName="ttsCard"] {{
            border: none;
        }}

        /* === 输入框 — 聚焦发光（排除对话区） === */
        QLineEdit, QTextEdit:not([objectName="chatDisplay"]) {{
            background-color: {c.input_bg};
            color: {c.text_primary};
            border: 1.5px solid {c.input_border};
            border-radius: 8px;
            padding: 6px 12px;
        }}
        QLineEdit:focus, QTextEdit:not([objectName="chatDisplay"]):focus {{
            border-color: {c.input_focus_border};
        }}
        QLineEdit[echoMode="2"] {{
            letter-spacing: 3px;
        }}

        /* === 分组框 — 柔和阴影 === */
        QGroupBox {{
            background-color: {c.card_bg};
            color: {c.text_primary};
            border: 1px solid {c.card_border};
            border-radius: 10px;
            margin-top: 14px;
            padding-top: 18px;
        }}
        QGroupBox::title {{
            color: {c.text_primary};
            subcontrol-origin: margin;
            left: 14px;
            padding: 0 8px;
            font-weight: 500;
        }}

        /* === 标签页 — 圆润设计 === */
        QTabWidget::pane {{
            background-color: {c.card_bg};
            border: 1px solid {c.card_border};
            border-radius: 8px;
            top: -1px;
        }}
        QTabBar::tab {{
            background-color: transparent;
            color: {c.text_muted};
            border: none;
            border-bottom: 2px solid transparent;
            padding: 8px 20px;
            margin-right: 4px;
            font-weight: 500;
        }}
        QTabBar::tab:hover {{
            color: {c.text_secondary};
            border-bottom-color: {c.card_border};
        }}
        QTabBar::tab:selected {{
            color: {c.accent};
            border-bottom-color: {c.accent};
        }}

        /* === 列表 — 更柔和的交互 === */
        QListWidget, QTreeWidget {{
            background-color: {c.input_bg};
            color: {c.text_primary};
            border: 1px solid {c.card_border};
            border-radius: 8px;
            outline: none;
            padding: 2px;
        }}
        QListWidget::item, QTreeWidget::item {{
            border-radius: 6px;
            padding: 4px 8px;
            margin: 1px 2px;
        }}
        QListWidget::item:selected, QTreeWidget::item:selected {{
            background-color: {c.accent};
            color: white;
        }}
        QListWidget::item:hover:!selected, QTreeWidget::item:hover:!selected {{
            background-color: {c.card_bg_hover};
        }}

        /* === 进度条 — 圆润渐变 === */
        QProgressBar {{
            background-color: {c.input_bg};
            border: none;
            border-radius: 6px;
            text-align: center;
            color: {c.text_primary};
            height: 8px;
            font-size: 0px;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {c.progress_start}, stop:1 {c.progress_end});
            border-radius: 6px;
        }}

        /* === 右键菜单 — 圆润 + 阴影感 === */
        QMenu {{
            background-color: {c.card_bg};
            color: {c.text_primary};
            border: 1px solid {c.card_border};
            border-radius: 10px;
            padding: 6px;
        }}
        QMenu::item {{
            border-radius: 6px;
            padding: 6px 24px;
            margin: 1px 4px;
        }}
        QMenu::item:selected {{
            background-color: {c.accent};
            color: white;
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {c.divider};
            margin: 4px 12px;
        }}

        /* === 滚动条 — 极简 === */
        QScrollBar:vertical {{
            background-color: transparent;
            width: 6px;
            margin: 4px 2px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {c.text_muted};
            border-radius: 3px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {c.text_secondary};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        QScrollBar:horizontal {{
            background-color: transparent;
            height: 6px;
            margin: 2px 4px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {c.text_muted};
            border-radius: 3px;
            min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {c.text_secondary};
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}

        /* === 工具提示 === */
        QToolTip {{
            background-color: {c.card_bg};
            color: {c.text_primary};
            border: 1px solid {c.card_border};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 12px;
        }}

        /* === Splitter === */
        QSplitter::handle {{
            background-color: {c.divider};
        }}
        QSplitter::handle:horizontal {{
            width: 1px;
            margin: 8px 4px;
        }}
        QSplitter::handle:vertical {{
            height: 1px;
            margin: 4px 8px;
        }}
    """


def get_skeleton_css() -> str:
    """骨架屏动画 CSS（用于 QTextEdit HTML 内嵌）"""
    c = _colors
    return f"""
        @keyframes skeletonShimmer {{
            0% {{ background-position: -200px 0; }}
            100% {{ background-position: 200px 0; }}
        }}
        .skeleton {{
            background: linear-gradient(90deg,
                {c.skeleton_color} 25%,
                {c.skeleton_shimmer} 50%,
                {c.skeleton_color} 75%
            );
            background-size: 400px 100%;
            animation: skeletonShimmer 1.5s ease-in-out infinite;
            border-radius: 6px;
        }}
    """


def get_chat_bubble_css() -> str:
    """对话气泡 CSS（用于 QTextEdit HTML 内嵌）— v4.1 微信风格

    QTextEdit HTML 引擎限制:
    - 不支持 float/display/clear/max-width:calc/不对称border-radius
    - 仅支持: background-color, color, margin, padding, border, border-radius(单值),
      font-*, text-align, vertical-align, width/height
    - 气泡定位用 <div align="left/right"> + margin 控制
    """
    c = _colors
    return f"""
        .ai-bubble {{
            background-color: {c.ai_bubble_bg};
            border: 1px solid {c.ai_bubble_border};
            color: {c.text_primary};
            border-radius: 12px;
            padding: {c.chat_bubble_padding};
            margin: 4px 25% 4px 0;
        }}
        .user-bubble {{
            background-color: {c.user_bubble_bg};
            color: {c.user_text_color};
            border-radius: 12px;
            padding: {c.chat_bubble_padding};
            margin: 4px 0 4px 25%;
        }}
        .system-msg {{
            text-align: center;
            color: {c.system_msg_color};
            font-size: 12px;
            padding: 2px 0;
        }}
        .timestamp {{
            font-size: 11px;
            color: {c.timestamp_color};
            margin-top: 2px;
        }}
    """


# ============ 对话气泡 HTML 生成函数 v3.0 ============
# 参考微信/QQ/Telegram 的消息分组、条件头像、条件时间戳设计


def get_ai_avatar_svg(size: int = 36) -> str:
    """生成 AI 头像 — 实心紫色圆 + 白色文字 'AI'（QTextEdit兼容，不用qlineargradient）"""
    c = _colors
    font_size = max(int(size * 0.38), 10)
    return (
        f'<div style="width:{size}px;height:{size}px;border-radius:50%;'
        f'background-color:{c.ai_bubble_accent};'
        f'color:white;text-align:center;'
        f'font-size:{font_size}px;font-weight:bold;line-height:{size}px;">AI</div>'
    )


def get_user_avatar_svg(size: int = 36) -> str:
    """生成用户头像 — 实心蓝色圆 + 白色文字 'Me'（QTextEdit兼容，不用qlineargradient）"""
    font_size = max(int(size * 0.35), 10)
    return (
        f'<div style="width:{size}px;height:{size}px;border-radius:50%;'
        f'background-color:#4263eb;'
        f'color:white;text-align:center;'
        f'font-size:{font_size}px;font-weight:bold;line-height:{size}px;">Me</div>'
    )


def get_avatar_placeholder(size: int = 36) -> str:
    """生成头像占位 — 与头像等宽的透明占位（QTextEdit兼容）"""
    return (
        f'<div style="width:{size}px;height:1px;"></div>'
    )


def get_timestamp_html(ts_text: str) -> str:
    """生成居中胶囊时间标签 HTML（微信风格 — 仅在时间间隔>3分钟时调用）"""
    c = _colors
    return (
        f'<div style="margin:12px 0 8px 0;text-align:center;">'
        f'<span style="font-size:12px;color:{c.timestamp_color};'
        f'background-color:{c.chat_timestamp_bg};'
        f'border:1px solid {c.chat_timestamp_border};'
        f'border-radius:10px;padding:3px 12px;">{ts_text}</span>'
        f'</div>'
    )


def get_system_msg_html(text: str) -> str:
    """生成系统消息 HTML（居中胶囊样式，替代旧版纯文字）"""
    c = _colors
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'<div style="margin:8px 0;text-align:center;">'
        f'<span style="font-size:12px;color:{c.system_msg_color};'
        f'background-color:{c.chat_timestamp_bg};'
        f'border:1px solid {c.chat_timestamp_border};'
        f'border-radius:10px;padding:3px 14px;">{escaped}</span>'
        f'</div>'
    )


def format_timestamp(dt) -> str:
    """将 datetime 格式化为友好的时间标签文字

    规则:
    - 今天: "HH:MM"
    - 昨天: "昨天 HH:MM"
    - 今年: "MM月DD日 HH:MM"
    - 去年及更早: "YYYY年MM月DD日 HH:MM"
    """
    from datetime import datetime, timedelta
    now = datetime.now()
    time_str = dt.strftime("%H:%M")

    if dt.date() == now.date():
        return time_str
    elif dt.date() == (now - timedelta(days=1)).date():
        return f"昨天 {time_str}"
    elif dt.year == now.year:
        return dt.strftime("%m月%d日 ") + time_str
    else:
        return dt.strftime("%Y年%m月%d日 ") + time_str


def get_web_theme_vars() -> dict:
    """获取 Web 端主题变量（用于 QWebEngineView JavaScript setTheme()）

    返回 CSS 变量名到颜色值的映射，与 chat_web_display.html 中的 CSS 变量对应。
    """
    c = _colors
    return {
        "bg": c.chat_bg,
        "text-primary": c.text_primary,
        "text-secondary": c.text_secondary,
        "text-muted": c.text_muted,
        "ai-bubble-bg": c.ai_bubble_bg,
        "ai-bubble-border": c.ai_bubble_border,
        "user-bubble-bg": c.user_bubble_bg,
        "user-text-color": c.user_text_color,
        "system-bg": c.chat_timestamp_bg,
        "system-border": c.chat_timestamp_border,
        "system-color": c.system_msg_color,
        "timestamp-bg": c.chat_timestamp_bg,
        "timestamp-border": c.chat_timestamp_border,
        "timestamp-color": c.timestamp_color,
        "accent": c.accent,
        "typing-cursor": c.chat_typing_cursor_color,
    }
