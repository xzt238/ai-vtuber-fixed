"""
ChatPage 视觉/OCR Mixin

包含图片上传、OCR 识别、视觉理解相关的功能。
"""

import os
import logging
from typing import Optional

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QFileDialog

from gugu_native.workers.vision_workers import OCRWorker, VisionWorker

logger = logging.getLogger('ChatPage.Vision')


class ChatPageVisionMixin:
    """视觉/OCR 处理 Mixin"""

    def _upload_image(self) -> None:
        """上传图片进行视觉理解"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.webp *.gif);;所有文件 (*)"
        )
        if not file_path:
            return
        self._pending_image = file_path
        self.chat_display.append_image(file_path)
        self.input_field.setFocus()
        self.input_field.setPlaceholderText("输入关于图片的问题，或直接按回车进行OCR识别...")

    def _screenshot_ocr(self) -> None:
        """截图OCR — 区域选择截图后识别文字"""
        if not self.backend:
            self.chat_display.append_system_msg("后端未初始化，无法使用OCR")
            return
        try:
            from gugu_native.widgets.screenshot_selector import ScreenshotSelector
            self._screenshot_selector = ScreenshotSelector()
            self._screenshot_selector.region_selected.connect(self._on_screenshot_ready)
            self._screenshot_selector.start()
        except Exception as e:
            self.chat_display.append_system_msg(f"截图OCR失败: {e}")

    def _on_screenshot_ready(self, tmp_path: str) -> None:
        """截图区域保存完成，开始 OCR"""
        self.chat_display.append_system_msg("正在识别屏幕文字...")
        self._ocr_worker = OCRWorker(self.backend, tmp_path)
        self._ocr_worker.finished.connect(self._on_ocr_result)
        self._ocr_worker.error.connect(self._on_ocr_error)
        self._ocr_worker.start()

    @Slot(str)
    def _on_ocr_result(self, text: str) -> None:
        """OCR 识别完成"""
        if text:
            self.chat_display.append_system_msg(f"OCR 识别结果:\n{text}")
            self.input_field.setText(text)
        else:
            self.chat_display.append_system_msg("OCR 未识别到文字")

    @Slot(str)
    def _on_ocr_error(self, error: str) -> None:
        """OCR 识别失败"""
        self.chat_display.append_system_msg(f"OCR 识别失败: {error}")

    def _process_pending_image(self, user_text: str) -> str:
        """处理待发送的图片 — 异步处理，不阻塞主线程"""
        if not self._pending_image:
            return user_text

        image_path = self._pending_image
        self._pending_image = None

        if not self.backend:
            return user_text

        # 使用 QThread 异步处理视觉请求，避免 UI 冻结
        self.input_field.setPlaceholderText("正在分析图片...")
        self.input_field.setEnabled(False)

        self._vision_worker = VisionWorker(self.backend, image_path, user_text)
        self._vision_worker.result_ready.connect(self._on_vision_result)
        self._vision_worker.error_occurred.connect(self._on_vision_error)
        self._vision_worker.finished.connect(lambda: self.input_field.setEnabled(True))
        self._vision_worker.start()
        return None  # 异步返回，结果通过信号传递

    @Slot(str)
    def _on_vision_result(self, enriched_text: str) -> None:
        """视觉理解完成，发送消息"""
        self.input_field.setPlaceholderText("输入消息，Enter 发送 · Ctrl+F 搜索")
        if enriched_text:
            self._send_message(enriched_text)

    @Slot(str)
    def _on_vision_error(self, error_msg: str) -> None:
        """视觉理解失败"""
        self.chat_display.append_system_msg(f"视觉理解失败: {error_msg}")
        self.input_field.setPlaceholderText("输入消息，Enter 发送 · Ctrl+F 搜索")
