"""
咕咕嘎嘎 AI-VTuber — 统一主题管理 v4.0

职责:
1. 集中定义颜色常量（AppColors dataclass）
2. 生成全局 QSS 样式表
3. 一键切换主题并通知所有页面
4. 消除各页面散落的硬编码颜色
5. Material Elevation 阴影系统
6. 按钮渐变/悬停/按下状态
7. 输入框聚焦发光效果
8. 对话气泡 HTML 生成（微信级消息分组+条件头像+条件时间戳）
9. SVG 内联头像（AI 机器人 + 用户轮廓）

v4.0 变更:
- 删除 LightColors 子类，主题数据由 ThemeDefinition 管理
- 删除全局 _colors/_current_theme 变量，委托给 ThemeManager
- 新增 apply_theme_by_id() / get_all_themes() / get_current_theme_id() 函数
- AppColors 新增 from_definition() 工厂方法
- get_user_avatar_svg() / get_ai_avatar_svg() 改为动态获取颜色

参考: 微信 / QQ / Telegram / ChatGPT Desktop / Discord 暗色设计规范
"""

import os
from dataclasses import dataclass, fields
from typing import Callable, List

from qfluentwidgets import setTheme, Theme, isDarkTheme, setThemeColor
from PySide6.QtGui import QColor


# 主题管理器（延迟初始化）
_theme_manager: 'ThemeManager | None' = None

# v1.11.25 S-003: QSS 缓存 — 避免每次切换主题时重新生成
_qss_cache: dict = {}
_qss_cache_max_size = 10  # 最多缓存 10 个主题的 QSS


def _ensure_manager() -> None:
    """确保 ThemeManager 已初始化，未初始化时自动创建"""
    global _theme_manager
    if _theme_manager is None:
        from gugu_native.themes import ThemeManager, ThemeRegistry
        from gugu_native.themes.presets import register_all_presets
        registry = ThemeRegistry()
        register_all_presets(registry)
        prefs_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'app', 'cache', 'theme_preferences.json'
        )
        _theme_manager = ThemeManager.initialize(registry, prefs_path)
    return _theme_manager


# 主题变更回调列表 — 各页面注册后主题切换时自动通知
_theme_change_callbacks: List[Callable] = []


def register_theme_callback(callback: Callable) -> None:
    """注册主题变更回调 — 页面在 __init__ 中调用"""
    _theme_change_callbacks.append(callback)
    # 同时注册到 ThemeManager
    manager = _ensure_manager()
    manager.register_callback(callback)


def unregister_theme_callback(callback: Callable) -> None:
    """反注册主题变更回调"""
    try:
        _theme_change_callbacks.remove(callback)
    except ValueError:
        pass
    # 同时从 ThemeManager 反注册
    try:
        manager = _ensure_manager()
        manager.unregister_callback(callback)
    except Exception as e:
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
    success_hover: str = "#2f9e44"
    success_pressed: str = "#2b8a3e"
    success_bg: str = "#1a3a2a"
    warning: str = "#f59f00"
    warning_bg: str = "#3a331a"
    error: str = "#f03e3e"
    error_hover: str = "#e03131"
    error_pressed: str = "#c92a2a"
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

    @classmethod
    def from_definition(cls, definition) -> 'AppColors':
        """从 ThemeDefinition 创建 AppColors 实例

        Args:
            definition: ThemeDefinition 实例

        Returns:
            AppColors 实例，未指定的字段使用默认值
        """
        kwargs = {}
        for f in fields(cls):
            value = definition.colors.get(f.name)
            if value is not None:
                # 处理 int 类型字段（如 chat_avatar_size）
                if f.type == "int" or (hasattr(f, 'type') and 'int' in str(f.type)):
                    try:
                        kwargs[f.name] = int(value)
                    except (ValueError, TypeError):
                        pass
                else:
                    kwargs[f.name] = value
            # 如果 definition 中没有该字段，使用 AppColors 的默认值
        return cls(**kwargs)


# === 公共 API — 委托给 ThemeManager ===

def get_colors() -> AppColors:
    """获取当前颜色方案"""
    manager = _ensure_manager()
    return manager.get_colors()


def is_dark() -> bool:
    """当前是否为暗色主题"""
    manager = _ensure_manager()
    return manager.is_dark()


def apply_theme(theme: Theme) -> None:
    """应用主题（兼容旧接口，内部映射为 theme_id）

    Args:
        theme: qfluentwidgets.Theme 枚举值
    """
    theme_id = "dark" if theme == Theme.DARK else "light"
    apply_theme_by_id(theme_id)


def apply_theme_by_id(theme_id: str) -> None:
    """通过主题 ID 应用主题 + 重新生成 QSS

    Args:
        theme_id: 主题唯一标识，如 "dark", "ocean"
    """
    manager = _ensure_manager()
    manager.apply(theme_id)
    # v1.11.27: 清空 QSS 缓存，确保切换主题后使用新 QSS
    clear_qss_cache()
    # v5.0: 切换主题后重新应用全局 QSS（圆角/间距/阴影/字体会变化）
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app:
        app.setStyleSheet(build_global_qss_v5(manager.get_theme()))


def get_all_themes() -> list:
    """获取所有可用主题列表

    Returns:
        ThemeDefinition 实例列表
    """
    manager = _ensure_manager()
    return manager.get_registry().list_all()


def get_current_theme_id() -> str:
    """获取当前主题 ID

    Returns:
        当前主题唯一标识，如 "dark"
    """
    manager = _ensure_manager()
    return manager.get_current_id()


def get_global_qss() -> str:
    """生成全局 QSS 样式表 — v5 多维度升级版

    基于当前主题的 AppTheme 自动调整颜色、圆角、间距、阴影、字体。
    兼容旧 API：内部调用 build_global_qss_v5()。

    v1.11.25 S-003: 添加 QSS 缓存，避免重复生成
    """
    # 获取当前主题 ID 作为缓存 key
    try:
        from gugu_native.themes.manager import ThemeManager
        manager = ThemeManager.get_instance()
        theme_id = manager.get_theme_id() if manager else "default"
    except Exception as e:
        theme_id = "default"

    # 检查缓存
    if theme_id in _qss_cache:
        return _qss_cache[theme_id]

    # 缓存未命中，生成 QSS
    qss = build_global_qss_v5()

    # 存入缓存（如果缓存已满，清空最旧的）
    if len(_qss_cache) >= _qss_cache_max_size:
        _qss_cache.pop(next(iter(_qss_cache)))
    _qss_cache[theme_id] = qss

    return qss


def clear_qss_cache() -> None:
    """清空 QSS 缓存 — 主题配置变更时调用"""
    _qss_cache.clear()


def build_global_qss_v5(theme=None) -> str:
    """v5 多维度 QSS 生成器
    
    基于 AppTheme.to_qss_vars() 的变量字典，
    使用 Python %(var)s 模板替换生成完整 QSS。
    
    Args:
        theme: AppTheme 实例，None 时使用当前主题
        
    Returns:
        完整的 QSS 样式表字符串
    """
    if theme is None:
        from gugu_native.themes.manager import ThemeManager
        manager = ThemeManager.get_instance()
        if manager:
            theme = manager.get_theme()
    
    if theme is None:
        return get_global_qss.__wrapped__() if hasattr(get_global_qss, '__wrapped__') else ""
    
    v = theme.to_qss_vars()

    # v1.11.27: 补全所有 QSS 模板中使用的变量 fallback，防止 KeyError 导致 QSS 解析失败
    # 颜色
    v.setdefault('accent', '#4263eb')
    v.setdefault('window_bg', '#1a1b2e')
    v.setdefault('card_bg', '#232438')
    v.setdefault('card_bg_hover', '#2a2b42')
    v.setdefault('card_border', '#2e2f48')
    v.setdefault('text_primary', '#e8e8f0')
    v.setdefault('text_secondary', '#9a9ab0')
    v.setdefault('text_muted', '#5c5c72')
    v.setdefault('input_bg', '#1e1f34')
    v.setdefault('input_border', '#2e2f48')
    v.setdefault('input_focus_border', '#4263eb')
    v.setdefault('divider', '#2e2f48')
    v.setdefault('chat_bg', '#1a1b2e')
    v.setdefault('progress_start', '#4263eb')
    v.setdefault('progress_end', '#7c3aed')
    # 圆角
    v.setdefault('br_card', 12)
    v.setdefault('br_widget', 8)
    v.setdefault('br_input', 8)
    v.setdefault('br_menu', 10)
    v.setdefault('br_button', 8)
    # 间距
    v.setdefault('sp_global', 16)
    v.setdefault('sp_card', 14)
    v.setdefault('sp_item', 8)
    v.setdefault('sp_section', 14)
    # 字体
    v.setdefault('font_family', 'Microsoft YaHei UI')

    # 构建完整的 QSS
    return _QSS_BASE_TEMPLATE % v


# ============================================================
# v5.0 QSS 基础模板（使用 %(var)s 占位符）
# ============================================================

_QSS_BASE_TEMPLATE = """\
        /* === v5.0 多维度全局 QSS === */
        * {
            font-family: "%(font_family)s", "Microsoft YaHei UI", "Segoe UI", sans-serif;
        }

        /* === 全局容器 — 统一背景色 === */
        QWidget {
            background-color: %(window_bg)s;
            color: %(text_primary)s;
        }
        /* QLabel 默认透明背景，避免被 QWidget 的 background 覆盖后出现黑底 */
        QLabel {
            background-color: transparent;
            color: %(text_primary)s;
        }

        /* === 对话区 === */
        QTextEdit[objectName="chatDisplay"] {
            background-color: %(chat_bg)s;
            color: %(text_primary)s;
            border: none;
            border-radius: %(br_card)dpx;
            padding: %(sp_card)dpx %(sp_global)dpx;
            selection-background-color: %(accent)s;
            selection-color: white;
        }

        /* === 卡片容器 === */
        QFrame[objectName="chatCard"],
        QFrame[objectName="inputCard"],
        QFrame[objectName="ttsCard"] {
            border: none;
        }

        /* === 输入框 === */
        QLineEdit, QTextEdit:not([objectName="chatDisplay"]) {
            background-color: %(input_bg)s;
            color: %(text_primary)s;
            border: 1px solid %(input_border)s;
            border-radius: %(br_input)dpx;
            padding: 6px 12px;
        }
        QLineEdit:focus, QTextEdit:not([objectName="chatDisplay"]):focus {
            border-color: %(input_focus_border)s;
        }
        QLineEdit[echoMode="2"] {
            letter-spacing: 3px;
        }

        /* === 分组框 === */
        QGroupBox {
            background-color: %(card_bg)s;
            color: %(text_primary)s;
            border: 1px solid %(card_border)s;
            border-radius: %(br_card)dpx;
            margin-top: 14px;
            padding-top: 18px;
        }
        QGroupBox::title {
            color: %(text_primary)s;
            subcontrol-origin: margin;
            left: 14px;
            padding: 0 8px;
            font-weight: bold;
        }

        /* === 标签页 === */
        QTabWidget::pane {
            background-color: %(card_bg)s;
            border: 1px solid %(card_border)s;
            border-radius: %(br_widget)dpx;
            top: -1px;
        }
        QTabBar::tab {
            background-color: transparent;
            color: %(text_muted)s;
            border: none;
            border-bottom: 2px solid transparent;
            padding: 8px 20px;
            margin-right: 4px;
            font-weight: bold;
        }
        QTabBar::tab:hover {
            color: %(text_secondary)s;
            border-bottom-color: %(card_border)s;
        }
        QTabBar::tab:selected {
            color: %(accent)s;
            border-bottom-color: %(accent)s;
        }

        /* === 列表 === */
        QListWidget, QTreeWidget {
            background-color: %(input_bg)s;
            color: %(text_primary)s;
            border: 1px solid %(card_border)s;
            border-radius: %(br_widget)dpx;
            padding: 2px;
        }
        QListWidget::item, QTreeWidget::item {
            border-radius: %(br_widget)dpx;
            padding: 4px 8px;
            margin: 1px 2px;
        }
        QListWidget::item:selected, QTreeWidget::item:selected {
            background-color: %(accent)s;
            color: white;
        }
        QListWidget::item:hover:!selected, QTreeWidget::item:hover:!selected {
            background-color: %(card_bg_hover)s;
        }

        /* === 进度条 === */
        QProgressBar {
            background-color: %(input_bg)s;
            border: none;
            border-radius: %(br_widget)dpx;
            text-align: center;
            color: transparent;
            height: 8px;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 %(progress_start)s, stop:1 %(progress_end)s);
            border-radius: %(br_widget)dpx;
        }

        /* === 右键菜单 === */
        QMenu {
            background-color: %(card_bg)s;
            color: %(text_primary)s;
            border: 1px solid %(card_border)s;
            border-radius: %(br_menu)dpx;
            padding: 6px;
        }
        QMenu::item {
            border-radius: %(br_widget)dpx;
            padding: 6px 24px;
            margin: 1px 4px;
        }
        QMenu::item:selected {
            background-color: %(accent)s;
            color: white;
        }
        QMenu::separator {
            height: 1px;
            background-color: %(divider)s;
            margin: 4px 12px;
        }

        /* === 滚动条 === */
        QScrollBar:vertical {
            background-color: transparent;
            width: 6px;
            margin: 4px 2px;
        }
        QScrollBar::handle:vertical {
            background-color: %(text_muted)s;
            border-radius: 3px;
            min-height: 30px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: %(text_secondary)s;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
        QScrollBar:horizontal {
            background-color: transparent;
            height: 6px;
            margin: 2px 4px;
        }
        QScrollBar::handle:horizontal {
            background-color: %(text_muted)s;
            border-radius: 3px;
            min-width: 30px;
        }
        QScrollBar::handle:horizontal:hover {
            background-color: %(text_secondary)s;
        }
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
        }

        /* === 工具提示 === */
        QToolTip {
            background-color: %(card_bg)s;
            color: %(text_primary)s;
            border: 1px solid %(card_border)s;
            border-radius: %(br_widget)dpx;
            padding: 6px 10px;
            font-size: 12px;
        }

        /* === Splitter === */
        QSplitter::handle {
            background-color: %(divider)s;
        }
        QSplitter::handle:horizontal {
            width: 1px;
            margin: 8px 4px;
        }
        QSplitter::handle:vertical {
            height: 1px;
            margin: 4px 8px;
        }
"""


def get_skeleton_css() -> str:
    """骨架屏动画 CSS（用于 QTextEdit HTML 内嵌）"""
    c = get_colors()
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
    c = get_colors()
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
    """生成 AI 头像 — 实心圆 + 白色文字 'AI'（QTextEdit兼容，不用qlineargradient）"""
    c = get_colors()
    font_size = max(int(size * 0.38), 10)
    return (
        f'<div style="width:{size}px;height:{size}px;border-radius:50%;'
        f'background-color:{c.ai_bubble_accent};'
        f'color:white;text-align:center;'
        f'font-size:{font_size}px;font-weight:bold;line-height:{size}px;">AI</div>'
    )


def get_user_avatar_svg(size: int = 36) -> str:
    """生成用户头像 — 实心圆 + 白色文字 'Me'（QTextEdit兼容，动态获取颜色）"""
    c = get_colors()
    font_size = max(int(size * 0.35), 10)
    return (
        f'<div style="width:{size}px;height:{size}px;border-radius:50%;'
        f'background-color:{c.user_bubble_bg};'
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
    c = get_colors()
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
    c = get_colors()
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
    c = get_colors()
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
