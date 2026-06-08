"""
咕咕嘎嘎 AI-VTuber — 主题注册中心 + 颜色衍生算法

ColorDeriver: 基于 accent 色自动衍生 hover/pressed/gradient/base 等颜色变体
ThemeRegistry: 主题注册中心，管理所有已注册的主题定义
"""

import colorsys
from .definitions import ThemeDefinition


class ColorDeriver:
    """颜色衍生工具 — 基于 accent 色自动计算相关颜色变体"""

    @staticmethod
    def derive_accent_variants(accent_hex: str) -> dict[str, str]:
        """从强调色自动衍生 hover/pressed/gradient 变体

        Args:
            accent_hex: 强调色 hex 值，如 "#4263eb"

        Returns:
            包含 accent/accent_hover/accent_pressed/accent_gradient_start/accent_gradient_end 的字典
        """
        r, g, b = int(accent_hex[1:3], 16) / 255, int(accent_hex[3:5], 16) / 255, int(accent_hex[5:7], 16) / 255
        h, l, s = colorsys.rgb_to_hls(r, g, b)

        return {
            "accent":              accent_hex,
            "accent_hover":        ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, min(l + 0.08, 1.0), s)),
            "accent_pressed":      ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, max(l - 0.10, 0.0), min(s + 0.05, 1.0))),
            "accent_gradient_start": ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, min(l + 0.06, 1.0), s)),
            "accent_gradient_end":   accent_hex,
        }

    @staticmethod
    def derive_base_colors(accent_hex: str, base_mode: str) -> dict[str, str]:
        """基于 accent + base_mode 自动衍生所有颜色

        返回一个 dict，键名与 AppColors 字段对应。
        对于 dark 基底，背景偏深色；对于 light 基底，背景偏浅色。

        Args:
            accent_hex: 强调色 hex 值
            base_mode: "dark" 或 "light"

        Returns:
            完整颜色字典（与 AppColors 字段对应）
        """
        r, g, b = int(accent_hex[1:3], 16) / 255, int(accent_hex[3:5], 16) / 255, int(accent_hex[5:7], 16) / 255
        h, l, s = colorsys.rgb_to_hls(r, g, b)

        # 衍生 accent 变体
        accent_variants = ColorDeriver.derive_accent_variants(accent_hex)

        if base_mode == "dark":
            # === 暗色基底 ===
            # 窗口/侧栏/卡片背景 — 从 accent 色相衍生，极低饱和度、极低亮度
            window_bg = ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, 0.11, 0.15))
            sidebar_bg = ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, 0.09, 0.15))
            card_bg = ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, 0.14, 0.15))
            card_bg_hover = ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, 0.16, 0.18))
            card_border = ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, 0.18, 0.15))
            card_border_hover = ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, 0.22, 0.18))

            # 对话区
            chat_bg = window_bg
            ai_bubble_bg = ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, 0.16, 0.12))
            ai_bubble_border = ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, 0.21, 0.15))
            ai_bubble_accent = ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, l * 0.6, max(s - 0.15, 0.3)))
            user_bubble_bg = accent_hex
            user_bubble_border = accent_variants["accent_hover"]
            user_bubble_accent = accent_variants["accent_hover"]
            user_text_color = "#ffffff"
            system_msg_color = "#6c6c8a"
            skeleton_color = card_bg_hover
            skeleton_shimmer = ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, 0.20, 0.15))
            chat_timestamp_bg = ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, 0.12, 0.12))
            chat_timestamp_border = card_bg_hover
            chat_typing_cursor_color = accent_hex

            # 文字 — 暗色基底用浅色文字
            text_primary = "#e8e8f0"
            text_secondary = "#9a9ab0"
            text_muted = "#5c5c72"
            text_on_accent = "#ffffff"

            # 语义色背景
            success_bg = "#1a3a2a"
            warning_bg = "#3a331a"
            error_bg = "#3a1a1a"
            info_bg = ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, 0.12, 0.25))

            # 输入控件
            input_bg = ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, 0.12, 0.12))
            input_border = card_border
            input_focus_border = accent_hex
            input_focus_shadow = f"rgba({int(r*255)},{int(g*255)},{int(b*255)},0.25)"

            # 训练日志
            log_bg = ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, 0.06, 0.10))
            log_text = "#c9d1d9"
            log_timestamp = "#5c5c72"

            # 进度条 — accent 到互补色渐变
            complement_h = (h + 0.5) % 1.0
            progress_end = ColorDeriver.to_hex(*colorsys.hls_to_rgb(complement_h, l * 0.6, s))

            # 阴影 — 暗色基底用更深的阴影
            shadow_sm = "rgba(0,0,0,0.15)"
            shadow_md = "rgba(0,0,0,0.25)"
            shadow_lg = "rgba(0,0,0,0.35)"
            shadow_xl = "rgba(0,0,0,0.45)"

            # 时间戳 + 分割线
            timestamp_color = "#5c5c72"
            divider = card_border

            # AI 头像背景 — accent 色相偏移
            ai_avatar_bg = ColorDeriver.to_hex(*colorsys.hls_to_rgb((h + 0.75) % 1.0, 0.45, 0.70))

        else:
            # === 亮色基底 ===
            window_bg = "#f0f2f5"
            sidebar_bg = "#e8eaed"
            card_bg = "#ffffff"
            card_bg_hover = "#f8f9fa"
            card_border = "#e0e2e8"
            card_border_hover = "#c8cad2"

            chat_bg = window_bg
            ai_bubble_bg = "#ffffff"
            ai_bubble_border = "#dee2e6"
            ai_bubble_accent = ColorDeriver.to_hex(*colorsys.hls_to_rgb((h + 0.75) % 1.0, 0.45, 0.70))
            user_bubble_bg = accent_hex
            user_bubble_border = accent_variants["accent_hover"]
            user_bubble_accent = accent_variants["accent_hover"]
            user_text_color = "#ffffff"
            system_msg_color = "#868e96"
            skeleton_color = "#e9ecef"
            skeleton_shimmer = "#f1f3f5"
            chat_timestamp_bg = "#e9ecef"
            chat_timestamp_border = "#dee2e6"
            chat_typing_cursor_color = accent_hex

            text_primary = "#1a1a2e"
            text_secondary = "#555566"
            text_muted = "#9a9aaa"
            text_on_accent = "#ffffff"

            success_bg = "#d3f9d8"
            warning_bg = "#fff3bf"
            error_bg = "#ffe0e0"
            info_bg = ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, 0.92, 0.25))

            input_bg = "#ffffff"
            input_border = "#d0d2d8"
            input_focus_border = accent_hex
            input_focus_shadow = f"rgba({int(r*255)},{int(g*255)},{int(b*255)},0.15)"

            log_bg = "#f8f9fa"
            log_text = "#212529"
            log_timestamp = "#868e96"

            complement_h = (h + 0.5) % 1.0
            progress_end = ColorDeriver.to_hex(*colorsys.hls_to_rgb(complement_h, l * 0.5, s))

            shadow_sm = "rgba(0,0,0,0.06)"
            shadow_md = "rgba(0,0,0,0.10)"
            shadow_lg = "rgba(0,0,0,0.15)"
            shadow_xl = "rgba(0,0,0,0.20)"

            timestamp_color = "#868e96"
            divider = "#e0e2e8"

            ai_avatar_bg = ColorDeriver.to_hex(*colorsys.hls_to_rgb((h + 0.75) % 1.0, 0.45, 0.70))

        # 合并所有颜色
        colors = {
            # 窗口
            "window_bg": window_bg,
            "sidebar_bg": sidebar_bg,
            "card_bg": card_bg,
            "card_bg_hover": card_bg_hover,
            "card_border": card_border,
            "card_border_hover": card_border_hover,
            # 对话区
            "chat_bg": chat_bg,
            "ai_bubble_bg": ai_bubble_bg,
            "ai_bubble_border": ai_bubble_border,
            "ai_bubble_accent": ai_bubble_accent,
            "user_bubble_bg": user_bubble_bg,
            "user_bubble_border": user_bubble_border,
            "user_bubble_accent": user_bubble_accent,
            "user_text_color": user_text_color,
            "system_msg_color": system_msg_color,
            "skeleton_color": skeleton_color,
            "skeleton_shimmer": skeleton_shimmer,
            "chat_timestamp_bg": chat_timestamp_bg,
            "chat_timestamp_border": chat_timestamp_border,
            "chat_group_gap": "12px",
            "chat_same_gap": "4px",
            "chat_bubble_max_width": "80%",
            "chat_avatar_size": "34",
            "chat_bubble_padding": "10px 16px",
            "chat_bubble_radius_ai": "12px",
            "chat_bubble_radius_user": "12px",
            "chat_typing_cursor_color": chat_typing_cursor_color,
            # 文字
            "text_primary": text_primary,
            "text_secondary": text_secondary,
            "text_muted": text_muted,
            "text_on_accent": text_on_accent,
            # 强调色变体
            **accent_variants,
            # 语义色
            "success": "#37b24d",
            "success_bg": success_bg,
            "warning": "#f59f00",
            "warning_bg": warning_bg,
            "error": "#f03e3e",
            "error_bg": error_bg,
            "info": accent_hex,
            "info_bg": info_bg,
            # 统计卡片 — 保持通用性
            "stat_working": "#4dabf7",
            "stat_episodic": "#69db7c",
            "stat_semantic": "#da77f2",
            "stat_facts": "#ffd43b",
            "stat_forgotten": "#868e96",
            # 输入控件
            "input_bg": input_bg,
            "input_border": input_border,
            "input_focus_border": input_focus_border,
            "input_focus_shadow": input_focus_shadow,
            # 训练日志
            "log_bg": log_bg,
            "log_text": log_text,
            "log_timestamp": log_timestamp,
            "log_success": "#37b24d",
            "log_error": "#f03e3e",
            "log_info": "#4dabf7",
            # 进度条
            "progress_start": accent_hex,
            "progress_end": progress_end,
            # 阴影
            "shadow_sm": shadow_sm,
            "shadow_md": shadow_md,
            "shadow_lg": shadow_lg,
            "shadow_xl": shadow_xl,
            # 时间戳 + 分割线
            "timestamp_color": timestamp_color,
            "divider": divider,
        }

        return colors

    @staticmethod
    def lighten(hex_color: str, amount: float) -> str:
        """将颜色变亮指定量

        Args:
            hex_color: hex 颜色值
            amount: 变亮量 (0.0-1.0)

        Returns:
            变亮后的 hex 颜色值
        """
        r, g, b = int(hex_color[1:3], 16) / 255, int(hex_color[3:5], 16) / 255, int(hex_color[5:7], 16) / 255
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        return ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, min(l + amount, 1.0), s))

    @staticmethod
    def darken(hex_color: str, amount: float) -> str:
        """将颜色变暗指定量

        Args:
            hex_color: hex 颜色值
            amount: 变暗量 (0.0-1.0)

        Returns:
            变暗后的 hex 颜色值
        """
        r, g, b = int(hex_color[1:3], 16) / 255, int(hex_color[3:5], 16) / 255, int(hex_color[5:7], 16) / 255
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        return ColorDeriver.to_hex(*colorsys.hls_to_rgb(h, max(l - amount, 0.0), s))

    @staticmethod
    def blend_colors(color1: str, color2: str, ratio: float) -> str:
        """混合两个颜色

        Args:
            color1: 第一个颜色 hex 值
            color2: 第二个颜色 hex 值
            ratio: 混合比例 (0.0=color1, 1.0=color2)

        Returns:
            混合后的 hex 颜色值
        """
        r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
        r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def to_hex(r: float, g: float, b: float) -> str:
        """将 RGB 浮点值 (0.0-1.0) 转换为 hex 颜色字符串

        Args:
            r: 红色分量 (0.0-1.0)
            g: 绿色分量 (0.0-1.0)
            b: 蓝色分量 (0.0-1.0)

        Returns:
            hex 颜色字符串，如 "#4263eb"
        """
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


class ThemeRegistry:
    """主题注册中心 — 管理所有已注册的主题定义"""

    def __init__(self) -> None:
        self._themes: dict[str, ThemeDefinition] = {}

    def register(self, definition: ThemeDefinition) -> None:
        """注册一个主题定义

        Args:
            definition: ThemeDefinition 实例
        """
        self._themes[definition.id] = definition

    def get(self, theme_id: str) -> ThemeDefinition | None:
        """根据 ID 获取主题定义

        Args:
            theme_id: 主题唯一标识

        Returns:
            ThemeDefinition 实例，不存在时返回 None
        """
        return self._themes.get(theme_id)

    def list_all(self) -> list[ThemeDefinition]:
        """列出所有已注册的主题

        Returns:
            所有 ThemeDefinition 实例列表
        """
        return list(self._themes.values())

    def list_by_base_mode(self, mode: str) -> list[ThemeDefinition]:
        """按基底模式筛选主题

        Args:
            mode: "dark" 或 "light"

        Returns:
            符合条件的 ThemeDefinition 实例列表
        """
        return [t for t in self._themes.values() if t.base_mode == mode]
