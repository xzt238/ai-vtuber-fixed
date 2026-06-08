"""
咕咕嘎嘎 AI-VTuber — 主题选择器组件 v5

ThemeSelector 以网格色卡布局显示所有可用主题:
- 按暗色/亮色分组显示
- 每组前有小标题标签
- 点击色卡切换主题并即时生效
- v5.0: 色卡底部显示风格标签(圆角/间距/阴影/字体)
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal

from qfluentwidgets import CaptionLabel

from gugu_native.theme import get_all_themes, get_current_theme_id, get_colors
from gugu_native.widgets.theme_card import ThemeCardWidget


# 风格标签映射
_STYLE_LABELS = {
    "rounded": "圆润", "soft": "柔和", "sharp": "锐利", "mixed": "混合",
    "compact": "紧凑", "comfortable": "舒适", "spacious": "宽敞",
    "flat": "扁平", "material": "质感", "neumorphic": "拟物", "glow": "霓虹",
    "msyh": "", "inter": "Inter", "jetbrains": "JetBrains",
    "solid": "", "outline": "轮廓", "ghost": "幽灵",
}


def _build_style_tags(theme_def) -> str:
    """从 ThemeDefinition 生成风格标签字符串"""
    try:
        at = theme_def.to_app_theme()
        parts = []
        parts.append(_STYLE_LABELS.get(at.border_radius.preset, at.border_radius.preset))
        parts.append(_STYLE_LABELS.get(at.spacing.preset, at.spacing.preset))
        sh_label = _STYLE_LABELS.get(at.shadow.preset, at.shadow.preset)
        if sh_label != "质感":
            parts.append(sh_label)
        ty_label = _STYLE_LABELS.get(at.typography.preset, "")
        if ty_label:
            parts.append(ty_label)
        return " · ".join(parts)
    except Exception as e:
        return ""


class ThemeSelector(QWidget):
    """主题选择器 — 网格色卡布局，分组显示暗色/亮色主题"""

    theme_selected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cards: dict[str, object] = {}
        self._current_id = "dark"
        self._dark_label = None
        self._light_label = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """构建 UI — 分组显示暗色/亮色主题色卡"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        themes = get_all_themes()
        dark_themes = [t for t in themes if t.base_mode == "dark"]
        light_themes = [t for t in themes if t.base_mode == "light"]

        c = get_colors()

        # 暗色主题组
        if dark_themes:
            self._dark_label = CaptionLabel("暗色主题")
            self._dark_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 12px; font-weight: 500;")
            main_layout.addWidget(self._dark_label)

            dark_row = QHBoxLayout()
            dark_row.setContentsMargins(0, 0, 0, 0)
            dark_row.setSpacing(8)

            for theme_def in dark_themes:
                from gugu_native.widgets.theme_card import ThemeCardWidget as T
                card = T(theme_id=theme_def.id, name=theme_def.name,
                         preview_colors=theme_def.preview_colors,
                         base_mode=theme_def.base_mode,
                         style_tags=_build_style_tags(theme_def), parent=self)
                card.clicked.connect(self._on_card_clicked)
                self._cards[theme_def.id] = card
                dark_row.addWidget(card)

            dark_row.addStretch(1)
            main_layout.addLayout(dark_row)

        # 亮色主题组
        if light_themes:
            self._light_label = CaptionLabel("亮色主题")
            self._light_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 12px; font-weight: 500;")
            main_layout.addWidget(self._light_label)

            light_row = QHBoxLayout()
            light_row.setContentsMargins(0, 0, 0, 0)
            light_row.setSpacing(8)

            for theme_def in light_themes:
                card = T(theme_id=theme_def.id, name=theme_def.name,
                         preview_colors=theme_def.preview_colors,
                         base_mode=theme_def.base_mode,
                         style_tags=_build_style_tags(theme_def), parent=self)
                card.clicked.connect(self._on_card_clicked)
                self._cards[theme_def.id] = card
                light_row.addWidget(card)

            light_row.addStretch(1)
            main_layout.addLayout(light_row)

        self._current_id = get_current_theme_id()
        self._update_selection()

    def _on_card_clicked(self, theme_id: str) -> None:
        self._current_id = theme_id
        self._update_selection()
        self.theme_selected.emit(theme_id)

    def _update_selection(self) -> None:
        for tid, card in self._cards.items():
            card.set_selected(tid == self._current_id)

    def set_current(self, theme_id: str) -> None:
        self._current_id = theme_id
        self._update_selection()

    def refresh_theme(self) -> None:
        c = get_colors()
        if self._dark_label:
            self._dark_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 12px; font-weight: 500;")
        if self._light_label:
            self._light_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 12px; font-weight: 500;")
        for card in self._cards.values():
            card.refresh_theme()
