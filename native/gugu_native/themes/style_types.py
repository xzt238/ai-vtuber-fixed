"""
咕咕嘎嘎 AI-VTuber — 主题风格类型系统 v5

多维度主题数据模型：
- BorderRadiusStyle: 圆角风格（rounded/soft/sharp/mixed）
- SpacingStyle: 间距密度（compact/comfortable/spacious）
- ShadowStyle: 阴影风格（flat/material/neumorphic/glow）
- TypographyStyle: 字体风格（msyh/inter/jetbrains）
- ControlStyle: 控件样式（solid/outline/ghost）
- AppTheme: 统一主题数据类

作者: 咕咕嘎嘎
日期: 2026-05-28
"""

from dataclasses import dataclass, field
from typing import Optional


# ============================================================
# 圆角风格
# ============================================================

@dataclass
class BorderRadiusStyle:
    """圆角风格配置

    四种预设:
    - rounded: 圆润风格（14-18px），适合休闲/可爱风格
    - soft:    柔和风格（8-12px），适合通用场景
    - sharp:   锐利风格（2-4px），适合专业/极客风格
    - mixed:   混合风格（卡片圆滑+控件锐利），对比鲜明
    """
    preset: str = "soft"
    card: int = 12
    widget: int = 8
    button: int = 8
    input: int = 8
    menu: int = 10
    bubble_ai: int = 12
    bubble_user: int = 12

    @classmethod
    def from_preset(cls, preset: str, base_mode: str = "dark") -> "BorderRadiusStyle":
        """从预设名称创建圆角风格实例"""
        if preset == "auto":
            preset = "soft"
        styles = {
            "rounded": cls(preset="rounded", card=16, widget=12, button=14,
                           input=12, menu=14, bubble_ai=18, bubble_user=18),
            "soft":    cls(preset="soft",    card=10, widget=8,  button=8,
                           input=8,  menu=10, bubble_ai=12, bubble_user=12),
            "sharp":   cls(preset="sharp",   card=4,  widget=3,  button=3,
                           input=3,  menu=4,  bubble_ai=4,  bubble_user=4),
            "mixed":   cls(preset="mixed",   card=14, widget=4,  button=4,
                           input=4,  menu=14, bubble_ai=14, bubble_user=14),
        }
        return styles.get(preset, styles["soft"])


# ============================================================
# 间距密度
# ============================================================

@dataclass
class SpacingStyle:
    """间距密度配置

    三种预设:
    - compact:      紧凑模式（信息密度高，适合小屏幕）
    - comfortable:  舒适模式（默认，平衡美观和信息量）
    - spacious:     宽敞模式（留白多，适合大屏幕/休闲浏览）
    """
    preset: str = "comfortable"
    global_padding: int = 10
    card_padding: int = 14
    item_spacing: int = 8
    section_gap: int = 14

    @classmethod
    def from_preset(cls, preset: str, base_mode: str = "dark") -> "SpacingStyle":
        """从预设名称创建间距风格实例"""
        if preset == "auto":
            preset = "comfortable"
        styles = {
            "compact":     cls(preset="compact",     global_padding=6,
                               card_padding=8,  item_spacing=4,  section_gap=8),
            "comfortable": cls(preset="comfortable", global_padding=10,
                               card_padding=14, item_spacing=8,  section_gap=14),
            "spacious":    cls(preset="spacious",    global_padding=16,
                               card_padding=20, item_spacing=12, section_gap=22),
        }
        return styles.get(preset, styles["comfortable"])


# ============================================================
# 阴影风格
# ============================================================

@dataclass
class ShadowStyle:
    """阴影风格配置

    四种预设:
    - flat:       扁平风格（无阴影，极简）
    - material:   Material Design 层级阴影（默认）
    - neumorphic: 新拟物风格（凸起/凹陷效果）
    - glow:       霓虹发光风格（accent 色发光边框）
    """
    preset: str = "material"
    elevation_1: str = ""
    elevation_2: str = ""
    elevation_3: str = ""
    glow_color: str = ""

    @classmethod
    def from_preset(cls, preset: str, accent_color: str = "#4263eb",
                    base_mode: str = "dark") -> "ShadowStyle":
        """从预设名称创建阴影风格实例"""
        if preset == "auto":
            preset = "material" if base_mode == "dark" else "flat"
        styles = {
            "flat": cls(
                preset="flat",
                elevation_1="none", elevation_2="none", elevation_3="none",
            ),
            "material": cls(
                preset="material",
                elevation_1="0 1px 3px rgba(0,0,0,0.3)",
                elevation_2="0 3px 8px rgba(0,0,0,0.4)",
                elevation_3="0 6px 16px rgba(0,0,0,0.5)",
            ),
            "neumorphic": cls(
                preset="neumorphic",
                elevation_1="3px 3px 6px rgba(0,0,0,0.4), -2px -2px 5px rgba(255,255,255,0.05)",
                elevation_2="5px 5px 10px rgba(0,0,0,0.5), -3px -3px 8px rgba(255,255,255,0.03)",
                elevation_3="8px 8px 16px rgba(0,0,0,0.6), -4px -4px 12px rgba(255,255,255,0.02)",
            ),
            "glow": cls(
                preset="glow",
                elevation_1=f"0 0 8px {accent_color}44",
                elevation_2=f"0 0 16px {accent_color}66",
                elevation_3=f"0 0 24px {accent_color}88",
                glow_color=accent_color,
            ),
        }
        return styles.get(preset, styles["material"])


# ============================================================
# 字体风格
# ============================================================

@dataclass
class TypographyStyle:
    """字体风格配置

    三种预设:
    - msyh:      微软雅黑（系统默认，中英文均衡）
    - inter:     Inter 字体（现代 UI 字体，英文优先）
    - jetbrains: JetBrains Mono（等宽字体，极客风格）
    """
    preset: str = "msyh"
    font_family: str = "Microsoft YaHei UI"
    font_scale: float = 1.0
    heading_weight: int = 600
    mono_font_family: str = "Consolas"

    @classmethod
    def from_preset(cls, preset: str, base_mode: str = "dark") -> "TypographyStyle":
        """从预设名称创建字体风格实例"""
        if preset == "auto":
            preset = "msyh"
        styles = {
            "msyh": cls(
                preset="msyh", font_family="Microsoft YaHei UI",
                font_scale=1.0, heading_weight=600, mono_font_family="Consolas",
            ),
            "inter": cls(
                preset="inter", font_family="Inter",
                font_scale=1.0, heading_weight=600, mono_font_family="JetBrains Mono",
            ),
            "jetbrains": cls(
                preset="jetbrains", font_family="JetBrains Mono",
                font_scale=0.95, heading_weight=700, mono_font_family="JetBrains Mono",
            ),
        }
        return styles.get(preset, styles["msyh"])


# ============================================================
# 控件样式
# ============================================================

@dataclass
class ControlStyle:
    """控件样式配置

    三种预设:
    - solid:   实心填充（默认，强调操作）
    - outline: 轮廓线框（低调，适合次要操作）
    - ghost:   透明幽灵（极简，适合工具栏）
    """
    preset: str = "solid"
    button_style: str = "solid"
    switch_style: str = "material"
    slider_style: str = "continuous"
    progress_style: str = "gradient"

    @classmethod
    def from_preset(cls, preset: str, base_mode: str = "dark") -> "ControlStyle":
        """从预设名称创建控件样式实例"""
        if preset == "auto":
            preset = "solid" if base_mode == "dark" else "outline"
        styles = {
            "solid": cls(
                preset="solid", button_style="solid",
                switch_style="material", slider_style="continuous",
                progress_style="gradient",
            ),
            "outline": cls(
                preset="outline", button_style="outline",
                switch_style="ios", slider_style="continuous",
                progress_style="solid",
            ),
            "ghost": cls(
                preset="ghost", button_style="ghost",
                switch_style="minimal", slider_style="stepped",
                progress_style="segmented",
            ),
        }
        return styles.get(preset, styles["solid"])


# ============================================================
# 统一主题数据类
# ============================================================

@dataclass
class AppTheme:
    """统一主题数据类 — 替代纯颜色的 AppColors

    整合颜色、圆角、间距、阴影、字体、控件样式六个维度。
    """
    theme_id: str
    display_name: str
    base_mode: str = "dark"
    colors: Optional[object] = field(default=None, repr=False)
    border_radius: BorderRadiusStyle = field(default_factory=BorderRadiusStyle)
    spacing: SpacingStyle = field(default_factory=SpacingStyle)
    shadow: ShadowStyle = field(default_factory=ShadowStyle)
    typography: TypographyStyle = field(default_factory=TypographyStyle)
    controls: ControlStyle = field(default_factory=ControlStyle)

    def to_qss_vars(self) -> dict:
        """将主题数据转换为 QSS 模板变量字典"""
        c = self.colors
        br = self.border_radius
        sp = self.spacing
        sh = self.shadow
        ty = self.typography

        vars_dict = {}

        # 颜色变量
        if c:
            color_attrs = [
                'accent', 'accent_hover', 'accent_pressed',
                'accent_gradient_start', 'accent_gradient_end',
                'window_bg', 'sidebar_bg',
                'card_bg', 'card_bg_hover', 'card_border', 'card_border_hover',
                'text_primary', 'text_secondary', 'text_muted', 'text_on_accent',
                'success', 'success_hover', 'success_pressed', 'success_bg',
                'warning', 'warning_bg',
                'error', 'error_hover', 'error_pressed', 'error_bg',
                'info', 'info_bg',
                'input_bg', 'input_border', 'input_focus_border', 'input_focus_shadow',
                'log_bg', 'log_text', 'log_timestamp', 'log_success', 'log_error', 'log_info',
                'progress_start', 'progress_end',
                'shadow_sm', 'shadow_md', 'shadow_lg', 'shadow_xl',
                'timestamp_color', 'divider',
                'system_msg_color', 'skeleton_color', 'skeleton_shimmer',
                'stat_working', 'stat_episodic', 'stat_semantic', 'stat_facts', 'stat_forgotten',
            ]
            for attr in color_attrs:
                if hasattr(c, attr):
                    vars_dict[attr] = getattr(c, attr)

            # 对话相关（可选字段）
            chat_attrs = [
                'chat_bg', 'ai_bubble_bg', 'ai_bubble_border', 'ai_bubble_accent',
                'user_bubble_bg', 'user_bubble_border',
                'chat_timestamp_bg', 'chat_timestamp_border',
                'chat_typing_cursor_color',
            ]
            for attr in chat_attrs:
                if hasattr(c, attr):
                    vars_dict[attr] = getattr(c, attr)

        # 圆角变量
        vars_dict.update({
            'br_card': br.card, 'br_widget': br.widget,
            'br_button': br.button, 'br_input': br.input,
            'br_menu': br.menu,
            'br_bubble_ai': br.bubble_ai, 'br_bubble_user': br.bubble_user,
        })

        # 间距变量
        vars_dict.update({
            'sp_global': sp.global_padding, 'sp_card': sp.card_padding,
            'sp_item': sp.item_spacing, 'sp_section': sp.section_gap,
        })

        # 阴影变量
        vars_dict.update({
            'shadow_e1': sh.elevation_1, 'shadow_e2': sh.elevation_2,
            'shadow_e3': sh.elevation_3, 'shadow_glow': sh.glow_color,
            'shadow_preset': sh.preset,
        })

        # 字体变量
        vars_dict.update({
            'font_family': ty.font_family, 'font_scale': ty.font_scale,
            'mono_family': ty.mono_font_family, 'heading_weight': ty.heading_weight,
        })

        # 控件样式变量
        vars_dict.update({
            'btn_style': self.controls.button_style,
            'switch_style': self.controls.switch_style,
            'slider_style': self.controls.slider_style,
            'progress_style': self.controls.progress_style,
        })

        return vars_dict
