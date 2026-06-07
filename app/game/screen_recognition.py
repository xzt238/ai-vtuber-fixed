"""
通用屏幕识别模块
支持屏幕截图、OCR文字识别、游戏状态推断
"""

import os
import asyncio
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class RecognitionMode(Enum):
    """识别模式"""
    OCR = "ocr"              # 文字识别
    IMAGE = "image"          # 图像识别
    TEMPLATE = "template"    # 模板匹配
    FULL = "full"            # 全部识别

@dataclass
class ScreenRegion:
    """屏幕区域"""
    x: int
    y: int
    width: int
    height: int
    name: str = ""

@dataclass
class OCRResult:
    """OCR识别结果"""
    text: str
    confidence: float
    region: ScreenRegion
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class GameState:
    """游戏状态"""
    game_name: str
    screen_text: str
    detected_elements: List[str]
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

class ScreenRecognition:
    """屏幕识别器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # 配置参数
        self.screenshot_interval = self.config.get("screenshot_interval", 1.0)
        self.ocr_engine = self.config.get("ocr_engine", "rapidocr")
        self.save_screenshots = self.config.get("save_screenshots", False)
        self.screenshot_dir = Path(self.config.get("screenshot_dir", "./cache/screenshots"))
        
        # OCR引擎
        self.ocr_engine_instance = None
        
        # 模板库
        self.templates: Dict[str, np.ndarray] = {}
        
        # 状态
        self.is_running = False
        self.last_screenshot: Optional[np.ndarray] = None
        self.last_ocr_results: List[OCRResult] = []
        
        # 统计
        self.stats = {
            "total_screenshots": 0,
            "total_ocr_calls": 0,
            "average_ocr_time_ms": 0
        }
        
        logger.info("[ScreenRecognition] 初始化完成")
    
    async def initialize(self) -> bool:
        """初始化OCR引擎"""
        try:
            if self.ocr_engine == "rapidocr":
                return await self._init_rapidocr()
            elif self.ocr_engine == "paddleocr":
                return await self._init_paddleocr()
            elif self.ocr_engine == "tesseract":
                return await self._init_tesseract()
            else:
                logger.info(f"[ScreenRecognition] 不支持的OCR引擎: {self.ocr_engine}")
                return False
        except Exception as e:
            logger.info(f"[ScreenRecognition] 初始化失败: {e}")
            return False
    
    async def _init_rapidocr(self) -> bool:
        """初始化RapidOCR"""
        try:
            from rapidocr_onnxruntime import RapidOCR
            self.ocr_engine_instance = RapidOCR()
            logger.info("[ScreenRecognition] RapidOCR初始化成功")
            return True
        except ImportError:
            logger.info("[ScreenRecognition] RapidOCR未安装: pip install rapidocr-onnxruntime")
            return False
    
    async def _init_paddleocr(self) -> bool:
        """初始化PaddleOCR"""
        try:
            from paddleocr import PaddleOCR
            self.ocr_engine_instance = PaddleOCR(use_angle_cls=True, lang="ch")
            logger.info("[ScreenRecognition] PaddleOCR初始化成功")
            return True
        except ImportError:
            logger.info("[ScreenRecognition] PaddleOCR未安装: pip install paddleocr")
            return False
    
    async def _init_tesseract(self) -> bool:
        """初始化Tesseract"""
        try:
            import pytesseract
            self.ocr_engine_instance = pytesseract
            logger.info("[ScreenRecognition] Tesseract初始化成功")
            return True
        except ImportError:
            logger.info("[ScreenRecognition] Tesseract未安装: pip install pytesseract")
            return False
    
    async def capture_screen(self, region: ScreenRegion = None) -> Optional[np.ndarray]:
        """截取屏幕"""
        try:
            import mss
            import mss.tools
            
            with mss.mss() as sct:
                if region:
                    monitor = {
                        "top": region.y,
                        "left": region.x,
                        "width": region.width,
                        "height": region.height
                    }
                else:
                    monitor = sct.monitors[0]  # 整个屏幕
                
                screenshot = sct.grab(monitor)
                
                # 转换为numpy数组
                img = np.array(screenshot)
                
                # 保存截图
                if self.save_screenshots:
                    self.screenshot_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    filepath = self.screenshot_dir / filename
                    # 使用PIL保存
                    from PIL import Image
                    Image.fromarray(img).save(str(filepath))
                
                self.last_screenshot = img
                self.stats["total_screenshots"] += 1
                
                return img
                
        except ImportError:
            logger.info("[ScreenRecognition] mss未安装: pip install mss")
            return None
        except Exception as e:
            logger.info(f"[ScreenRecognition] 截图失败: {e}")
            return None
    
    async def recognize_text(self, image: np.ndarray = None, 
                           region: ScreenRegion = None) -> List[OCRResult]:
        """识别文字"""
        if image is None:
            image = await self.capture_screen(region)
        
        if image is None:
            return []
        
        start_time = datetime.now()
        results = []
        
        try:
            if self.ocr_engine == "rapidocr":
                results = await self._ocr_rapidocr(image)
            elif self.ocr_engine == "paddleocr":
                results = await self._ocr_paddleocr(image)
            elif self.ocr_engine == "tesseract":
                results = await self._ocr_tesseract(image)
            
            # 计算耗时
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.stats["total_ocr_calls"] += 1
            self.stats["average_ocr_time_ms"] = (
                (self.stats["average_ocr_time_ms"] * (self.stats["total_ocr_calls"] - 1) + elapsed_ms)
                / self.stats["total_ocr_calls"]
            )
            
            self.last_ocr_results = results
            return results
            
        except Exception as e:
            logger.info(f"[ScreenRecognition] OCR识别失败: {e}")
            return []
    
    async def _ocr_rapidocr(self, image: np.ndarray) -> List[OCRResult]:
        """RapidOCR识别"""
        if self.ocr_engine_instance is None:
            return []
        
        try:
            result, _ = self.ocr_engine_instance(image)
            
            results = []
            if result:
                for line in result:
                    box, text, confidence = line
                    # 计算区域
                    x_min = min(p[0] for p in box)
                    y_min = min(p[1] for p in box)
                    x_max = max(p[0] for p in box)
                    y_max = max(p[1] for p in box)
                    
                    region = ScreenRegion(
                        x=int(x_min),
                        y=int(y_min),
                        width=int(x_max - x_min),
                        height=int(y_max - y_min)
                    )
                    
                    results.append(OCRResult(
                        text=text,
                        confidence=confidence,
                        region=region
                    ))
            
            return results
            
        except Exception as e:
            logger.info(f"[ScreenRecognition] RapidOCR识别失败: {e}")
            return []
    
    async def _ocr_paddleocr(self, image: np.ndarray) -> List[OCRResult]:
        """PaddleOCR识别"""
        if self.ocr_engine_instance is None:
            return []
        
        try:
            result = self.ocr_engine_instance.ocr(image, cls=True)
            
            results = []
            if result and result[0]:
                for line in result[0]:
                    box, (text, confidence) = line
                    
                    x_min = min(p[0] for p in box)
                    y_min = min(p[1] for p in box)
                    x_max = max(p[0] for p in box)
                    y_max = max(p[1] for p in box)
                    
                    region = ScreenRegion(
                        x=int(x_min),
                        y=int(y_min),
                        width=int(x_max - x_min),
                        height=int(y_max - y_min)
                    )
                    
                    results.append(OCRResult(
                        text=text,
                        confidence=confidence,
                        region=region
                    ))
            
            return results
            
        except Exception as e:
            logger.info(f"[ScreenRecognition] PaddleOCR识别失败: {e}")
            return []
    
    async def _ocr_tesseract(self, image: np.ndarray) -> List[OCRResult]:
        """Tesseract识别"""
        if self.ocr_engine_instance is None:
            return []
        
        try:
            from PIL import Image
            pil_image = Image.fromarray(image)
            
            data = self.ocr_engine_instance.image_to_data(pil_image, output_type=self.ocr_engine_instance.Output.DICT)
            
            results = []
            for i in range(len(data["text"])):
                text = data["text"][i].strip()
                confidence = float(data["conf"][i]) / 100
                
                if text and confidence > 0.5:
                    region = ScreenRegion(
                        x=data["left"][i],
                        y=data["top"][i],
                        width=data["width"][i],
                        height=data["height"][i]
                    )
                    
                    results.append(OCRResult(
                        text=text,
                        confidence=confidence,
                        region=region
                    ))
            
            return results
            
        except Exception as e:
            logger.info(f"[ScreenRecognition] Tesseract识别失败: {e}")
            return []
    
    async def detect_game_state(self, game_name: str, 
                               image: np.ndarray = None) -> Optional[GameState]:
        """检测游戏状态"""
        # 获取OCR结果
        ocr_results = await self.recognize_text(image)
        
        if not ocr_results:
            return None
        
        # 合并所有文字
        all_text = " ".join([r.text for r in ocr_results])
        
        # 检测元素
        detected_elements = []
        for result in ocr_results:
            detected_elements.append(result.text)
        
        # 计算置信度
        avg_confidence = sum(r.confidence for r in ocr_results) / len(ocr_results)
        
        return GameState(
            game_name=game_name,
            screen_text=all_text,
            detected_elements=detected_elements,
            confidence=avg_confidence
        )
    
    def load_template(self, name: str, template_path: str) -> bool:
        """加载模板图像"""
        try:
            from PIL import Image
            template = np.array(Image.open(template_path))
            self.templates[name] = template
            logger.info(f"[ScreenRecognition] 模板已加载: {name}")
            return True
        except Exception as e:
            logger.info(f"[ScreenRecognition] 模板加载失败: {e}")
            return False
    
    async def match_template(self, template_name: str, 
                            image: np.ndarray = None) -> Optional[Tuple[int, int, float]]:
        """模板匹配"""
        if template_name not in self.templates:
            logger.info(f"[ScreenRecognition] 模板不存在: {template_name}")
            return None
        
        if image is None:
            image = await self.capture_screen()
        
        if image is None:
            return None
        
        try:
            import cv2
            
            template = self.templates[template_name]
            
            # 转换为灰度图
            gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            
            # 模板匹配
            result = cv2.matchTemplate(gray_img, gray_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # 返回最佳匹配位置和置信度
            return (max_loc[0], max_loc[1], max_val)
            
        except ImportError:
            logger.info("[ScreenRecognition] OpenCV未安装: pip install opencv-python")
            return None
        except Exception as e:
            logger.info(f"[ScreenRecognition] 模板匹配失败: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_screenshots": self.stats["total_screenshots"],
            "total_ocr_calls": self.stats["total_ocr_calls"],
            "average_ocr_time_ms": self.stats["average_ocr_time_ms"],
            "templates_loaded": len(self.templates),
            "ocr_engine": self.ocr_engine
        }

# 全局实例
_screen_recognition: Optional[ScreenRecognition] = None

def get_screen_recognition(config: Dict[str, Any] = None) -> ScreenRecognition:
    """获取屏幕识别器实例"""
    global _screen_recognition
    if _screen_recognition is None:
        _screen_recognition = ScreenRecognition(config)
    return _screen_recognition
