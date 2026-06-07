"""
视觉理解 Worker 线程 — OCRWorker + VisionWorker
"""

from PySide6.QtCore import QThread, Signal


class OCRWorker(QThread):
    """OCR 识别线程 — 截图后调用 backend.vision 识别文字"""
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, backend, image_path):
        super().__init__()
        self.backend = backend
        self.image_path = image_path

    def run(self):
        try:
            backend = self.backend
            if backend is None:
                self.error.emit("后端未初始化，请先在设置页面配置 API Key")
                return
            try:
                vision = backend.vision
            except Exception as e:
                self.error.emit(f"视觉模块加载失败: {e}")
                return
            if vision is None or not vision.has_provider:
                self.error.emit("视觉 Provider 未配置，请检查设置 > 视觉/OCR")
                return

            text = vision.recognize_text(self.image_path)
            if not text:
                try:
                    from app.vision import VisionProviderType
                    rapidocr = vision.get_provider(VisionProviderType.RAPIDOCR)
                    if rapidocr:
                        text = rapidocr.recognize_text(self.image_path)
                except Exception as e:
                    pass
            self.finished.emit(text or "")
        except Exception as e:
            self.error.emit(str(e))


class VisionWorker(QThread):
    """异步视觉理解工作线程，避免阻塞主线程"""
    result_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, backend, image_path, user_text):
        super().__init__()
        self.backend = backend
        self.image_path = image_path
        self.user_text = user_text

    def run(self):
        try:
            backend = self.backend
            if backend is None:
                self.error_occurred.emit("后端未初始化")
                return

            vision = None
            try:
                vision = backend.vision
            except Exception as e:
                self.error_occurred.emit(f"视觉模块加载失败: {e}")
                self.result_ready.emit(f"[用户上传了一张图片（视觉模块不可用）]\n{self.user_text}")
                return

            if vision is None or not vision.has_provider:
                self.error_occurred.emit("视觉 Provider 未配置")
                self.result_ready.emit(f"[用户上传了一张图片（视觉未配置）]\n{self.user_text}")
                return

            if not self.user_text.strip():
                ocr_result = vision.recognize_text(self.image_path)
                if not ocr_result:
                    try:
                        from app.vision import VisionProviderType
                        rapidocr = vision.get_provider(VisionProviderType.RAPIDOCR)
                        if rapidocr:
                            ocr_result = rapidocr.recognize_text(self.image_path)
                    except Exception as e:
                        pass
                if ocr_result:
                    self.result_ready.emit(f"请根据以下OCR识别结果回答：\n{ocr_result}")
                else:
                    self.result_ready.emit(f"[用户上传了一张图片（OCR未识别到文字）]\n{self.user_text}")
            else:
                description = vision.understand(self.image_path, self.user_text)
                if description:
                    self.result_ready.emit(
                        f"[用户上传了一张图片，AI描述: {description}]\n用户问题: {self.user_text}"
                    )
                else:
                    self.result_ready.emit(f"[用户上传了一张图片（视觉理解失败）]\n{self.user_text}")
        except Exception as e:
            self.error_occurred.emit(str(e))
