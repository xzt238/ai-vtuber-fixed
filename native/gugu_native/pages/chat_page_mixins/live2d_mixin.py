"""
ChatPage Live2D/VRM Mixin

包含 Live2D 和 VRM 模型相关的功能。
"""

import json
import os
import shutil
import logging


from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFileDialog

from qfluentwidgets import InfoBar

from gugu_native.utils.path_utils import (
    get_model_dir, get_live2d_model_path, get_vrm_model_path,
    get_vrm_display_config_path, path_exists
)

logger = logging.getLogger('ChatPage.Live2D')


class ChatPageLive2DMixin:
    """Live2D/VRM 模型管理 Mixin"""

    def _lazy_init_live2d(self) -> None:
        """延迟创建 Live2DWidget — 让窗口先显示再加载 Chromium

        QWebEngineView 的创建需要启动 Chromium 渲染进程，这是整个启动链路中
        最耗时的操作（5-10 秒）。通过延迟创建，窗口可以先显示出来，
        用户看到的是"应用已启动"，而不是"等了 20 秒什么都没出来"。
        """
        if self.live2d_widget is not None:
            return  # 已经创建过了

        # 创建 Live2D 组件
        from gugu_native.widgets.live2d_widget import Live2DWidget
        self.live2d_widget = Live2DWidget()

        # 性能优化：连接窗口拖动状态信号，拖动/resize 时暂停 Live2D 渲染
        main_window = self.window()
        if main_window and hasattr(main_window, 'perf_manager') and main_window.perf_manager:
            main_window.perf_manager.window_drag_state_changed.connect(
                self.live2d_widget.set_window_drag_state
            )

        # 替换占位符
        if self._live2d_placeholder:
            idx = self._live2d_layout.indexOf(self._live2d_placeholder)
            if idx >= 0:
                self._live2d_layout.removeWidget(self._live2d_placeholder)
                self._live2d_placeholder.hide()
                self._live2d_placeholder.deleteLater()
                self._live2d_placeholder = None

                # 在同一位置插入 Live2D widget
                self._live2d_layout.insertWidget(idx, self.live2d_widget, stretch=1)
                self.live2d_widget.show()
                self.live2d_widget.updateGeometry()

                # 强制布局刷新
                self._live2d_layout.invalidate()
                self._live2d_layout.activate()
                self.update()

                # 三段式 repaint：确保 QWebEngineView 合成到屏幕
                QTimer.singleShot(0, self._force_live2d_repaint)
                QTimer.singleShot(500, self._force_live2d_repaint)
                QTimer.singleShot(3000, self._force_live2d_repaint)
                logger.info("Live2D placeholder replaced with widget")
            else:
                # fallback: indexOf 没找到 — 追加到布局末尾
                self._live2d_layout.addWidget(self.live2d_widget, stretch=1)
                self.live2d_widget.show()
                self.live2d_widget.updateGeometry()
                self._live2d_placeholder.hide()
                self._live2d_placeholder.deleteLater()
                self._live2d_placeholder = None

                QTimer.singleShot(0, self._force_live2d_repaint)
                QTimer.singleShot(500, self._force_live2d_repaint)
                QTimer.singleShot(3000, self._force_live2d_repaint)
                logger.info("Live2D placeholder replaced (fallback append)")

        # 创建动画控制器
        from gugu_native.widgets.animation_controller import AnimationController
        self._animation_controller = AnimationController(self.live2d_widget)

        # 加载默认模型
        self._load_default_model()

        # VRM 3D 模型支持 — 延迟创建（与 Live2D 共用布局位置）
        try:
            from gugu_native.widgets.vrm_widget import VRMWidget
            self._vrm_widget = VRMWidget()
            self._vrm_widget.model_loaded.connect(lambda _: self._apply_vrm_display_config())
            self._live2d_layout.addWidget(self._vrm_widget, stretch=1)
            self._vrm_widget.hide()
            self._load_default_vrm_model()
            self._btn_vrm.show()
            logger.info("VRM widget created (hidden)")
        except ImportError:
            self._vrm_widget = None
            logger.info("VRMWidget not available, skipping VRM support")

    def _force_live2d_repaint(self) -> None:
        """微调窗口尺寸强制 QWebEngineView 合成到屏幕"""
        if not self.live2d_widget:
            return
        w = self.window()
        if w:
            g = w.geometry()
            w.resize(g.width() + 1, g.height())
            w.resize(g.width(), g.height())

    def _load_default_model(self) -> None:
        """加载默认 Live2D 模型"""
        if self.live2d_widget is None:
            return

        model_path = get_live2d_model_path("hiyori")
        if path_exists(model_path):
            self.live2d_widget.load_model(model_path)
            if self._animation_controller:
                self._animation_controller.start()
        else:
            if self._chat_display_ready and self.chat_display:
                self.chat_display.append_system_msg(f"默认模型不存在: {model_path}")

    def _load_default_vrm_model(self) -> None:
        """加载默认 VRM 3D 模型"""
        if self._vrm_widget is None:
            return

        vrm_path = get_vrm_model_path("default")
        if path_exists(vrm_path):
            self._vrm_widget.load_model(vrm_path)
            logger.info(f"VRM default model loaded: {vrm_path}")
        else:
            logger.warning(f"VRM default model not found: {vrm_path}")

    def switch_model_type(self, model_type: str) -> None:
        """切换 Live2D / VRM 模型显示"""
        if model_type == self._current_model_type:
            return

        if model_type == "vrm" and self._vrm_widget is None:
            logger.warning("VRM widget not available, cannot switch")
            return

        if model_type == "vrm":
            if self.live2d_widget:
                self.live2d_widget.hide()
            if self._vrm_widget:
                self._vrm_widget.show()
                if self._animation_controller:
                    self._animation_controller._widget = self._vrm_widget
            self._current_model_type = "vrm"
            self._btn_live2d.setChecked(False)
            self._btn_vrm.setChecked(True)
            self._vrm_variant_bar.show()
            logger.info("Switched to VRM model")
        else:
            if self._vrm_widget:
                self._vrm_widget.hide()
            if self.live2d_widget:
                self.live2d_widget.show()
                if self._animation_controller:
                    self._animation_controller._widget = self.live2d_widget
            self._current_model_type = "live2d"
            self._btn_live2d.setChecked(True)
            self._btn_vrm.setChecked(False)
            self._vrm_variant_bar.hide()
            logger.info("Switched to Live2D model")

    def _switch_vrm_variant(self, variant: str) -> None:
        """切换 VRM 变体"""
        if not self._vrm_widget:
            return

        variant_files = {
            "default": "default.vrm",
            "cow": "Asmodeus_cow.vrm",
            "jacket": "Asmodeus_jacket.vrm",
            "swim": "Asmodeus_swim.vrm",
        }
        filename = variant_files.get(variant)
        if not filename:
            return

        model_dir = get_model_dir("vrm")
        vrm_path = os.path.join(model_dir, filename)
        if path_exists(vrm_path):
            self._vrm_widget.load_model(vrm_path)
            for name, btn in self._btn_vrm_variants.items():
                btn.setChecked(name == variant)
            logger.info(f"Switched VRM variant: {variant} → {filename}")

    def _import_vrm_model(self) -> None:
        """导入新的 VRM 模型文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 VRM 模型文件",
            os.path.expanduser("~"), "VRM 模型 (*.vrm)"
        )
        if not path:
            return

        model_name = os.path.splitext(os.path.basename(path))[0]
        model_dir = get_model_dir("vrm")
        dest = os.path.join(model_dir, f"user_{model_name}.vrm")
        shutil.copy2(path, dest)

        if self._vrm_widget and self._current_model_type == "vrm":
            self._vrm_widget.load_model(dest)

        InfoBar.success("导入成功", f"VRM 模型已导入: {model_name}", parent=self)
        logger.info(f"Imported VRM: {path} → {dest}")

    def _import_live2d_model(self) -> None:
        """导入新的 Live2D 模型文件夹"""
        path = QFileDialog.getExistingDirectory(
            self, "选择 Live2D 模型文件夹"
        )
        if not path:
            return

        model_name = os.path.basename(path)
        model_dir = get_model_dir("live2d")
        dest_dir = os.path.join(model_dir, f"l2d_{model_name}")
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)
        shutil.copytree(path, dest_dir)

        for f in os.listdir(dest_dir):
            if f.endswith(".model3.json"):
                model_json = os.path.join(dest_dir, f)
                if self.live2d_widget:
                    self.live2d_widget.load_model(model_json)
                break

        InfoBar.success("导入成功", f"Live2D 模型已导入: {model_name}", parent=self)
        logger.info(f"Imported Live2D: {path} → {dest_dir}")

    def _apply_vrm_display_config(self) -> None:
        """读取保存的 VRM 显示配置并应用到当前模型"""
        if not self._vrm_widget:
            return

        import json
        config_path = get_vrm_display_config_path()
        config = {}
        if path_exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load VRM display config: {e}")

        # 应用配置
        if config:
            self._vrm_widget.apply_display_config(config)
