"""
咕咕嘎嘎 AI-VTuber — 主题定义数据类

ThemeDefinition 封装一个完整主题的所有元数据与配置:
- id: 唯一标识（如 "ocean"）
- name: 显示名（如 "海洋蓝"）
- description: 主题描述
- base_mode: 基底模式（"dark" 或 "light"）
- preview_colors: 色卡预览用 2-3 个代表色
- colors: {field_name: hex_color}，键名与 AppColors 字段一一对应
- border_radius / spacing / shadow / typography / controls: v5.0 多维度风格字段
"""

from dataclasses import dataclass, asdict
from typing import Optional

from .style_types import (
    BorderRadiusStyle, SpacingStyle, ShadowStyle,
    TypographyStyle, ControlStyle, AppTheme,
)


@dataclass
class ThemeDefinition:
    """主题定义数据类 — 描述一个完整主题的元数据与配置"""

    id: str                    # 唯一标识，如 "ocean"
    name: str                  # 显示名，如 "海洋蓝"
    description: str           # 主题描述
    base_mode: str             # "dark" 或 "light"
    preview_colors: list       # 色卡预览用 2-3 个代表色  (field type = list[str])
    colors: dict               # {field_name: hex_color}，键名与 AppColors 字段一一对应  (field type = dict[str, str])

    # v5.0: 多维度风格字段（None 时自动使用默认值）
    border_radius: Optional[BorderRadiusStyle] = None
    spacing: Optional[SpacingStyle] = None
    shadow: Optional[ShadowStyle] = None
    typography: Optional[TypographyStyle] = None
    controls: Optional[ControlStyle] = None

    def __post_init__(self) -> None:
        """初始化后校验：确保 base_mode 是有效值"""
        if self.base_mode not in ("dark", "light"):
            self.base_mode = "dark"

    def get_color(self, field: str, default: str = "") -> str:
        """获取指定颜色字段的值，不存在时返回 default"""
        return self.colors.get(field, default)

    def to_app_theme(self) -> AppTheme:
        """将 ThemeDefinition 转换为 AppTheme 实例

        对 None 维度自动使用 from_preset("auto") 填充默认值，
        确保所有主题都有完整的风格配置。
        """
        # 获取 accent 色用于 glow 阴影
        accent = self.colors.get("accent", "#4263eb")
        bm = self.base_mode

        return AppTheme(
            theme_id=self.id,
            display_name=self.name,
            base_mode=bm,
            colors=None,  # 延迟绑定，由 ThemeManager 填充 AppColors 实例
            border_radius=self.border_radius or BorderRadiusStyle.from_preset("auto", bm),
            spacing=self.spacing or SpacingStyle.from_preset("auto", bm),
            shadow=self.shadow or ShadowStyle.from_preset("auto", accent, bm),
            typography=self.typography or TypographyStyle.from_preset("auto", bm),
            controls=self.controls or ControlStyle.from_preset("auto", bm),
        )

    def to_dict(self) -> dict:
        """将主题定义序列化为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ThemeDefinition':
        """从字典反序列化创建 ThemeDefinition 实例"""
        return cls(**data)
