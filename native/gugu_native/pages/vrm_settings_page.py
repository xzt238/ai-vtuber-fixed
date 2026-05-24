"""
VRM 模型设置页

左侧实时预览 VRM 模型，右侧滑块调节显示参数。
参数保存到 config.yaml + app/cache/vrm_display.json。
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


_DEFAULTS = {
    "arm_angle": 1.0,
    "model_scale": 1.0,
    "camera_distance": 3.0,
    "light_intensity": 2.5,
    "target_height": 1.0,
    "model_y": 0.0,
    "fov": 30.0,
}

_PARAMS = [
    ("arm_angle",       "🎯 手臂角度",    0.0, 2.0,  1.0,  0.05),
    ("model_scale",     "📏 模型缩放",    0.5, 3.0,  1.0,  0.05),
    ("camera_distance", "📷 相机距离",    0.5, 10.0, 3.0,  0.1),
    ("light_intensity", "💡 光照强度",    0.5, 5.0,  2.5,  0.1),
    ("target_height",   "👁️ 视角高度",    0.0, 2.5,  1.0,  0.05),
    ("model_y",         "⬆️ 模型纵移",   -1.0, 1.0,  0.0,  0.05),
    ("fov",             "🔍 视场角度",    15.0,60.0, 30.0, 1.0),
]


class VRMSettingsPage(QWidget):
    """VRM 模型设置页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("vrmSettingsPage")
        self._vrm_widget: VRMWidget | None = None
        self._vrm_loaded = False
        self._sliders = {}  # param_name → (slider, spinbox)
        self._init_ui()

    # ========== UI 构建 ==========

    def _init_ui(self):
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

        card_layout.addWidget(SubtitleLabel("VRM 显示设置"))

        # 4 个参数滑块
        for name, label, vmin, vmax, default, step in _PARAMS:
            group = self._create_slider_group(label, name, vmin, vmax, default, step)
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

    def _create_slider_group(self, label_text, param_name, vmin, vmax, default, step):
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
        def _from_slider(val):
            fval = vmin + val * step
            spinbox.blockSignals(True)
            spinbox.setValue(fval)
            spinbox.blockSignals(False)
            self._on_param_changed(param_name, fval)

        def _from_spinbox(val):
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

    def _init_preview(self, layout):
        """创建 VRMWidget 预览"""
        self._vrm_widget = VRMWidget()
        self._vrm_widget.model_loaded.connect(self._on_preview_loaded)
        layout.addWidget(self._vrm_widget)

        default_path = os.path.join(
            PROJECT_DIR, "app", "web", "static", "assets", "model", "default.vrm"
        )
        if os.path.exists(default_path):
            self._vrm_widget.load_model(default_path)

    def _on_preview_loaded(self, _model_name: str):
        self._vrm_loaded = True
        self._apply_current_to_preview()

    # ========== 参数控制 ==========

    def _on_param_changed(self, param_name: str, value: float):
        """滑块值变化 → 实时应用到预览"""
        if not self._vrm_widget or not self._vrm_loaded:
            return
        method_map = {
            "arm_angle":       self._vrm_widget.set_arm_angle,
            "model_scale":     self._vrm_widget.set_model_scale,
            "camera_distance": self._vrm_widget.set_camera_distance,
            "light_intensity": self._vrm_widget.set_light_intensity,
            "target_height":   self._vrm_widget.set_target_height,
            "model_y":         self._vrm_widget.set_model_y,
            "fov":             self._vrm_widget.set_fov,
        }
        fn = method_map.get(param_name)
        if fn:
            fn(value)

    def _apply_current_to_preview(self):
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

    def _apply_config_to_ui(self, config: dict):
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
            except Exception:
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
            except Exception:
                pass

        return cfg

    def _save_config(self):
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
            import yaml
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

    def _reset_defaults(self):
        """重置所有参数为默认值"""
        self._apply_config_to_ui(_DEFAULTS)
        self._apply_current_to_preview()
        InfoBar.info("已重置", "所有参数已恢复默认值", duration=2000, parent=self)
