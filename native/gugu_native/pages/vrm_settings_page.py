"""
VRM 模型设置页

左侧实时预览 VRM 模型，右侧滑块调节显示参数。
参数保存到 config.yaml + app/cache/vrm_display.json。

v1.11.24 优化:
- 继承 LazyPageMixin，首次可见时才创建完整 UI，缩短冷启动时间
"""

import os
import json

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QScrollArea, QDoubleSpinBox
)
from PySide6.QtCore import Qt

from qfluentwidgets import (
    Slider, PushButton, CaptionLabel, InfoBar, InfoBarPosition,
    TitleLabel, SubtitleLabel, CardWidget, FluentIcon
)

from app.shared_config import PROJECT_DIR
from gugu_native.widgets.vrm_widget import VRMWidget
from gugu_native.widgets.lazy_page_mixin import LazyPageMixin
from gugu_native.widgets.skeleton_container import SkeletonContainer


_DEFAULTS = {
    # 姿态
    "arm_angle": 1.0,       "head_tilt": 0.0,       "model_rotation": 0.0,
    # 位置/缩放
    "model_scale": 1.0,     "model_x": 0.0,         "model_y": 0.0,
    "camera_distance": 3.0, "target_height": 1.0,   "fov": 30.0,
    # 光照
    "light_intensity": 2.5, "ambient_light": 0.8,   "fill_light": 1.0,
    # 背景
    "bg_opacity": 0.0,
    # 动画
    "anim_speed": 1.0,      "anim_amplitude": 1.0,  "breath_amp": 0.015,
}

_PARAMS = [
    # ---- 姿态 ----
    ("arm_angle",       "🎯 手臂角度",        0.0,  2.0,   1.0,  0.05),
    ("head_tilt",       "🗿 头部倾斜",        0.0,  0.5,   0.0,  0.02),
    ("model_rotation",  "🔄 模型旋转(°)",     -180, 180,  0.0,  5.0),
    # ---- 位置/缩放 ----
    ("model_scale",     "📏 模型缩放",        0.5,  3.0,   1.0,  0.05),
    ("model_x",         "↔️ 模型横移",        -1.0, 1.0,   0.0,  0.05),
    ("model_y",         "⬆️ 模型纵移",        -1.0, 1.0,   0.0,  0.05),
    ("camera_distance", "📷 相机距离",        0.5,  10.0,  3.0,  0.1),
    ("target_height",   "👁️ 视角高度",        0.0,  2.5,   1.0,  0.05),
    ("fov",             "🔍 视场角度",        15.0, 60.0,  30.0, 1.0),
    # ---- 光照 ----
    ("light_intensity", "💡 主光强度",        0.5,  5.0,   2.5,  0.1),
    ("ambient_light",   "🌐 环境光",          0.0,  3.0,   0.8,  0.1),
    ("fill_light",      "🔦 补光强度",        0.0,  3.0,   1.0,  0.1),
    # ---- 背景 ----
    ("bg_opacity",      "🖤 背景不透明",      0.0,  1.0,   0.0,  0.05),
    # ---- 动画 ----
    ("anim_speed",      "⏩ 动画速度",        0.0,  3.0,   1.0,  0.1),
    ("anim_amplitude",  "📳 动画幅度",        0.0,  2.0,   1.0,  0.05),
    ("breath_amp",      "🫁 呼吸幅度",        0.0,  0.1,   0.015,0.005),
]


class VRMSettingsPage(QWidget, LazyPageMixin):
    """VRM 模型设置页面 — 支持懒加载，首次可见时才创建 VRMWidget"""

    def __init__(self, parent=None) -> None:
        QWidget.__init__(self, parent)
        LazyPageMixin.__init__(self)
        self.setObjectName("vrmSettingsPage")
        self._vrm_widget: VRMWidget | None = None
        self._vrm_loaded = False
        self._sliders = {}  # param_name → (slider, spinbox)
        # 骨架屏占位 — 作为独立浮动 widget，不设置 self 的 layout
        # （lazy_init() 中会创建 layout，避免重复设置）
        self._skeleton = SkeletonContainer("正在加载 VRM 设置...", self)
        self._skeleton.hide_skeleton()

    def show_skeleton(self) -> None:
        self._skeleton.show_skeleton()

    def hide_skeleton(self) -> None:
        self._skeleton.hide_skeleton()

    def lazy_init(self) -> None:
        """首次切换到该页时调用 — 构建完整 UI"""
        if self._is_initialized:
            return
        self._skeleton.hide_skeleton()
        # 骨架屏不再需要，从 parent 分离并释放
        self._skeleton.setParent(None)
        self._skeleton.deleteLater()
        self._init_ui()

    # ========== UI 构建 ==========

    def _init_ui(self) -> None:
        # 清除 __init__ 中创建的占位 layout，避免重复设置
        old_layout = self.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)
            old_layout.deleteLater()

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)  # 紧凑边距

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # ---- 左侧：VRM 预览（无标题，铺满） ----
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self._init_preview(left_layout)
        splitter.addWidget(left)

        # ---- 右侧：控制面板 ----
        right = QScrollArea()
        right.setWidgetResizable(True)
        right.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        right_panel = QWidget()
        right_panel.setObjectName("vrmSettingsPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)

        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("VRM 模型设置"))

        # 按分组显示参数
        groups = {
            "🎭 姿态": ["arm_angle", "head_tilt", "model_rotation"],
            "📐 位置 & 缩放": ["model_scale", "model_x", "model_y", "camera_distance", "target_height", "fov"],
            "💡 光照": ["light_intensity", "ambient_light", "fill_light"],
            "🖤 背景": ["bg_opacity"],
            "🎬 动画": ["anim_speed", "anim_amplitude", "breath_amp"],
        }
        param_lookup = {p[0]: p for p in _PARAMS}
        for group_name, keys in groups.items():
            card_layout.addWidget(CaptionLabel(group_name))
            for key in keys:
                spec = param_lookup.get(key)
                if spec:
                    group = self._create_slider_group(spec[1], spec[0], spec[2], spec[3], spec[4], spec[5])
                    card_layout.addWidget(group)

        # 按钮行
        btn_layout = QHBoxLayout()
        btn_save = PushButton("💾 保存配置")
        btn_save.clicked.connect(self._save_config)
        btn_layout.addWidget(btn_save)

        btn_reset = PushButton("🔄 重置默认")
        btn_reset.clicked.connect(self._reset_defaults)
        btn_layout.addWidget(btn_reset)

        btn_layout.addStretch()
        card_layout.addLayout(btn_layout)

        # 说明
        hint = CaptionLabel(
            "· 手臂角度：上臂 Z 轴旋转，1.0 为自然下垂\n"
            "· 模型缩放：0.5x ~ 3.0x 等比缩放\n"
            "· 相机距离：摄像头距模型中心的距离\n"
            "· 光照强度：主方向光基础强度，缩放时自动补偿"
        )
        hint.setWordWrap(True)
        card_layout.addWidget(hint)

        right_layout.addWidget(card)
        right_layout.addStretch()
        right.setWidget(right_panel)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter)

        # 加载配置
        cfg = self._load_config()
        self._apply_config_to_ui(cfg)

    def _create_slider_group(self, label_text, param_name, vmin, vmax, default, step) -> None:
        """创建横向滑块组：标签 + Slider + SpinBox"""
        group = QWidget()
        layout = QHBoxLayout(group)
        layout.setContentsMargins(0, 2, 0, 2)

        lbl = CaptionLabel(label_text)
        lbl.setFixedWidth(110)
        layout.addWidget(lbl)

        # int slider 映射到 float
        steps = int((vmax - vmin) / step)
        slider = Slider(Qt.Orientation.Horizontal)
        slider.setRange(0, steps)
        slider.setSingleStep(1)

        spinbox = QDoubleSpinBox()
        spinbox.setRange(vmin, vmax)
        spinbox.setSingleStep(step)
        spinbox.setDecimals(2)
        spinbox.setFixedWidth(80)

        # 初始值
        init_int = int((default - vmin) / step)
        slider.setValue(init_int)
        spinbox.setValue(default)

        # 信号连接 — 防止循环
        def _from_slider(val) -> None:
            fval = vmin + val * step
            spinbox.blockSignals(True)
            spinbox.setValue(fval)
            spinbox.blockSignals(False)
            self._on_param_changed(param_name, fval)

        def _from_spinbox(val) -> None:
            ival = int((val - vmin) / step)
            slider.blockSignals(True)
            slider.setValue(ival)
            slider.blockSignals(False)
            self._on_param_changed(param_name, val)

        slider.valueChanged.connect(_from_slider)
        spinbox.valueChanged.connect(_from_spinbox)

        layout.addWidget(slider)
        layout.addWidget(spinbox)

        self._sliders[param_name] = (slider, spinbox)
        return group

    # ========== 预览初始化 ==========

    def _init_preview(self, layout) -> None:
        """创建 VRMWidget 预览"""
        self._vrm_widget = VRMWidget()
        self._vrm_widget.model_loaded.connect(self._on_preview_loaded)
        layout.addWidget(self._vrm_widget)

        default_path = os.path.join(
            PROJECT_DIR, "app", "web", "static", "assets", "model", "default.vrm"
        )
        if os.path.exists(default_path):
            self._vrm_widget.load_model(default_path)

    def _on_preview_loaded(self, _model_name: str) -> None:
        self._vrm_loaded = True
        self._apply_current_to_preview()

    # ========== 参数控制 ==========

    def _on_param_changed(self, param_name: str, value: float) -> None:
        """滑块值变化 → 实时应用到预览"""
        if not self._vrm_widget or not self._vrm_loaded:
            return
        method_map = {
            "arm_angle":       self._vrm_widget.set_arm_angle,
            "head_tilt":       self._vrm_widget.set_head_tilt,
            "model_rotation":  self._vrm_widget.set_model_rotation,
            "model_scale":     self._vrm_widget.set_model_scale,
            "model_x":         self._vrm_widget.set_model_x,
            "model_y":         self._vrm_widget.set_model_y,
            "camera_distance": self._vrm_widget.set_camera_distance,
            "target_height":   self._vrm_widget.set_target_height,
            "fov":             self._vrm_widget.set_fov,
            "light_intensity": self._vrm_widget.set_light_intensity,
            "ambient_light":   self._vrm_widget.set_ambient_light,
            "fill_light":      self._vrm_widget.set_fill_light,
            "bg_opacity":      self._vrm_widget.set_bg_opacity,
            "anim_speed":      self._vrm_widget.set_anim_speed,
            "anim_amplitude":  self._vrm_widget.set_anim_amplitude,
            "breath_amp":      self._vrm_widget.set_breath_amp,
        }
        fn = method_map.get(param_name)
        if fn:
            fn(value)

    def _apply_current_to_preview(self) -> None:
        """将当前所有滑块值一次性应用到预览"""
        if not self._vrm_loaded:
            return
        for name in _DEFAULTS:
            slider, _spinbox = self._sliders.get(name, (None, None))
            if slider is None:
                continue
            vmin, vmax, default, step = next(
                (p[2], p[3], p[4], p[5]) for p in _PARAMS if p[0] == name
            )
            fval = vmin + slider.value() * step
            self._on_param_changed(name, fval)

    def _apply_config_to_ui(self, config: dict) -> None:
        """将配置 dict 应用到 UI（滑块 + SpinBox）"""
        for name, (slider, spinbox) in self._sliders.items():
            val = config.get(name, _DEFAULTS.get(name, 0))
            vmin, vmax, default, step = next(
                (p[2], p[3], p[4], p[5]) for p in _PARAMS if p[0] == name
            )
            val = max(vmin, min(vmax, val))
            slider.blockSignals(True)
            spinbox.blockSignals(True)
            slider.setValue(int((val - vmin) / step))
            spinbox.setValue(val)
            slider.blockSignals(False)
            spinbox.blockSignals(False)

    # ========== 配置读写 ==========

    def _load_config(self) -> dict:
        """加载 VRM 显示配置（优先级：cache → config.yaml → 默认）"""
        cfg = dict(_DEFAULTS)

        # 1. 尝试读 cache JSON
        cache_path = os.path.join(PROJECT_DIR, "app", "cache", "vrm_display.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                cfg.update(saved)
            except Exception as e:
                pass

        # 2. fallback 读 config.yaml
        if cfg == _DEFAULTS:
            try:
                import yaml
                config_path = os.path.join(PROJECT_DIR, "app", "config.yaml")
                with open(config_path, "r", encoding="utf-8") as f:
                    yml = yaml.safe_load(f)
                if yml and "vrm_display" in yml:
                    cfg.update(yml["vrm_display"])
            except Exception as e:
                pass

        return cfg

    def _save_config(self) -> None:
        """保存当前参数到 cache + config.yaml"""
        current = {}
        for name, (slider, _spinbox) in self._sliders.items():
            vmin, vmax, default, step = next(
                (p[2], p[3], p[4], p[5]) for p in _PARAMS if p[0] == name
            )
            current[name] = round(vmin + slider.value() * step, 2)

        # 写 JSON cache
        cache_dir = os.path.join(PROJECT_DIR, "app", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, "vrm_display.json")
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2, ensure_ascii=False)
        except Exception as e:
            InfoBar.error("保存失败", str(e), parent=self)
            return

        # 写 config.yaml
        try:
            config_path = os.path.join(PROJECT_DIR, "app", "config.yaml")
            with open(config_path, "r", encoding="utf-8") as f:
                yml = yaml.safe_load(f) or {}
            yml["vrm_display"] = current
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(yml, f, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            InfoBar.warning("JSON 已保存", f"config.yaml 更新失败: {e}", parent=self)
            return

        InfoBar.success("保存成功", "VRM 显示配置已保存到 config.yaml 和缓存", parent=self)

    def _reset_defaults(self) -> None:
        """重置所有参数为默认值"""
        self._apply_config_to_ui(_DEFAULTS)
        self._apply_current_to_preview()
        InfoBar.info("已重置", "所有参数已恢复默认值", duration=2000, parent=self)
