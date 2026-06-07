"""
增强版屏幕识别模块
支持多游戏识别、实时状态推断、智能决策
"""

import asyncio
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class RecognitionMode(Enum):
    """识别模式"""
    FAST = "fast"          # 快速模式
    ACCURATE = "accurate"  # 精确模式
    BALANCED = "balanced"  # 平衡模式

class GameState(Enum):
    """游戏状态"""
    MENU = "menu"              # 菜单
    PLAYING = "playing"        # 游戏中
    PAUSED = "paused"          # 暂停
    INVENTORY = "inventory"    # 物品栏
    DIALOG = "dialog"          # 对话
    COMBAT = "combat"          # 战斗
    EXPLORING = "exploring"    # 探索
    CRAFTING = "crafting"      # 制作
    SHOPPING = "shopping"      # 购物
    LOADING = "loading"        # 加载中
    UNKNOWN = "unknown"        # 未知

@dataclass
class UIElement:
    """UI元素"""
    name: str
    position: Tuple[int, int]
    size: Tuple[int, int]
    text: str = ""
    confidence: float = 0.0
    element_type: str = "unknown"

@dataclass
class ScreenState:
    """屏幕状态"""
    game_name: str
    game_state: GameState
    ui_elements: List[UIElement]
    screen_text: str
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

class EnhancedScreenRecognition:
    """增强版屏幕识别器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # 识别模式
        self.mode = RecognitionMode(self.config.get("mode", "balanced"))
        
        # OCR引擎
        self.ocr_engine = self.config.get("ocr_engine", "rapidocr")
        self.ocr_instance = None
        
        # 游戏模板
        self.game_templates: Dict[str, Dict[str, Any]] = {}
        
        # 识别历史
        self.recognition_history: List[ScreenState] = []
        self.max_history = 100
        
        # 统计信息
        self.stats = {
            "total_recognitions": 0,
            "successful_recognitions": 0,
            "average_confidence": 0,
            "average_time_ms": 0
        }
        
        logger.info("[EnhancedScreenRecognition] 初始化完成")
    
    async def initialize(self) -> bool:
        """初始化OCR引擎"""
        try:
            if self.ocr_engine == "rapidocr":
                return await self._init_rapidocr()
            elif self.ocr_engine == "paddleocr":
                return await self._init_paddleocr()
            elif self.ocr_engine == "easyocr":
                return await self._init_easyocr()
            else:
                logger.info(f"[EnhancedScreenRecognition] 不支持的OCR引擎: {self.ocr_engine}")
                return False
        except Exception as e:
            logger.info(f"[EnhancedScreenRecognition] 初始化失败: {e}")
            return False
    
    async def _init_rapidocr(self) -> bool:
        """初始化RapidOCR"""
        try:
            from rapidocr_onnxruntime import RapidOCR
            self.ocr_instance = RapidOCR()
            logger.info("[EnhancedScreenRecognition] RapidOCR初始化成功")
            return True
        except ImportError:
            logger.info("[EnhancedScreenRecognition] RapidOCR未安装")
            return False
    
    async def _init_paddleocr(self) -> bool:
        """初始化PaddleOCR"""
        try:
            from paddleocr import PaddleOCR
            self.ocr_instance = PaddleOCR(use_angle_cls=True, lang="ch")
            logger.info("[EnhancedScreenRecognition] PaddleOCR初始化成功")
            return True
        except ImportError:
            logger.info("[EnhancedScreenRecognition] PaddleOCR未安装")
            return False
    
    async def _init_easyocr(self) -> bool:
        """初始化EasyOCR"""
        try:
            import easyocr
            self.ocr_instance = easyocr.Reader(['ch_sim', 'en'])
            logger.info("[EnhancedScreenRecognition] EasyOCR初始化成功")
            return True
        except ImportError:
            logger.info("[EnhancedScreenRecognition] EasyOCR未安装")
            return False
    
    def register_game_template(self, game_name: str, template: Dict[str, Any]):
        """注册游戏模板"""
        self.game_templates[game_name] = template
        logger.info(f"[EnhancedScreenRecognition] 注册游戏模板: {game_name}")
    
    async def recognize(self, screenshot: np.ndarray = None, 
                       game_name: str = None) -> Optional[ScreenState]:
        """识别屏幕"""
        import time
        start_time = time.time()
        
        self.stats["total_recognitions"] += 1
        
        try:
            # 获取截图
            if screenshot is None:
                screenshot = await self._capture_screen()
            
            if screenshot is None:
                return None
            
            # OCR识别
            ocr_results = await self._ocr_recognize(screenshot)
            
            # 提取UI元素
            ui_elements = self._extract_ui_elements(ocr_results)
            
            # 合并文字
            screen_text = " ".join([elem.text for elem in ui_elements if elem.text])
            
            # 推断游戏状态
            game_state = await self._infer_game_state(screen_text, ui_elements, game_name)
            
            # 计算置信度
            confidence = self._calculate_confidence(ocr_results, game_state)
            
            # 创建屏幕状态
            state = ScreenState(
                game_name=game_name or "unknown",
                game_state=game_state,
                ui_elements=ui_elements,
                screen_text=screen_text,
                confidence=confidence,
                metadata={
                    "ocr_engine": self.ocr_engine,
                    "mode": self.mode.value,
                    "ocr_results_count": len(ocr_results)
                }
            )
            
            # 记录历史
            self.recognition_history.append(state)
            if len(self.recognition_history) > self.max_history:
                self.recognition_history.pop(0)
            
            # 更新统计
            elapsed_ms = (time.time() - start_time) * 1000
            self.stats["successful_recognitions"] += 1
            self.stats["average_time_ms"] = (
                (self.stats["average_time_ms"] * (self.stats["successful_recognitions"] - 1) + elapsed_ms)
                / self.stats["successful_recognitions"]
            )
            self.stats["average_confidence"] = (
                (self.stats["average_confidence"] * (self.stats["successful_recognitions"] - 1) + confidence)
                / self.stats["successful_recognitions"]
            )
            
            logger.info(f"[EnhancedScreenRecognition] 识别完成: {game_state.value} ({confidence:.1%})")
            
            return state
            
        except Exception as e:
            logger.info(f"[EnhancedScreenRecognition] 识别失败: {e}")
            return None
    
    async def _capture_screen(self) -> Optional[np.ndarray]:
        """截取屏幕"""
        try:
            import mss
            
            with mss.mss() as sct:
                # 截取主显示器
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                
                # 转换为numpy数组
                img = np.array(screenshot)
                
                return img
                
        except ImportError:
            logger.info("[EnhancedScreenRecognition] mss未安装")
            return None
        except Exception as e:
            logger.info(f"[EnhancedScreenRecognition] 截图失败: {e}")
            return None
    
    async def _ocr_recognize(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """OCR识别"""
        try:
            if self.ocr_engine == "rapidocr":
                return await self._ocr_rapidocr(image)
            elif self.ocr_engine == "paddleocr":
                return await self._ocr_paddleocr(image)
            elif self.ocr_engine == "easyocr":
                return await self._ocr_easyocr(image)
            else:
                return []
        except Exception as e:
            logger.info(f"[EnhancedScreenRecognition] OCR识别失败: {e}")
            return []
    
    async def _ocr_rapidocr(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """RapidOCR识别"""
        if self.ocr_instance is None:
            return []
        
        try:
            result, _ = self.ocr_instance(image)
            
            results = []
            if result:
                for line in result:
                    box, text, confidence = line
                    
                    # 计算位置和大小
                    x_min = min(p[0] for p in box)
                    y_min = min(p[1] for p in box)
                    x_max = max(p[0] for p in box)
                    y_max = max(p[1] for p in box)
                    
                    results.append({
                        "text": text,
                        "confidence": confidence,
                        "position": (int(x_min), int(y_min)),
                        "size": (int(x_max - x_min), int(y_max - y_min)),
                        "box": box
                    })
            
            return results
            
        except Exception as e:
            logger.info(f"[EnhancedScreenRecognition] RapidOCR识别失败: {e}")
            return []
    
    async def _ocr_paddleocr(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """PaddleOCR识别"""
        if self.ocr_instance is None:
            return []
        
        try:
            result = self.ocr_instance.ocr(image, cls=True)
            
            results = []
            if result and result[0]:
                for line in result[0]:
                    box, (text, confidence) = line
                    
                    x_min = min(p[0] for p in box)
                    y_min = min(p[1] for p in box)
                    x_max = max(p[0] for p in box)
                    y_max = max(p[1] for p in box)
                    
                    results.append({
                        "text": text,
                        "confidence": confidence,
                        "position": (int(x_min), int(y_min)),
                        "size": (int(x_max - x_min), int(y_max - y_min)),
                        "box": box
                    })
            
            return results
            
        except Exception as e:
            logger.info(f"[EnhancedScreenRecognition] PaddleOCR识别失败: {e}")
            return []
    
    async def _ocr_easyocr(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """EasyOCR识别"""
        if self.ocr_instance is None:
            return []
        
        try:
            result = self.ocr_instance.readtext(image)
            
            results = []
            for (box, text, confidence) in result:
                x_min = min(p[0] for p in box)
                y_min = min(p[1] for p in box)
                x_max = max(p[0] for p in box)
                y_max = max(p[1] for p in box)
                
                results.append({
                    "text": text,
                    "confidence": confidence,
                    "position": (int(x_min), int(y_min)),
                    "size": (int(x_max - x_min), int(y_max - y_min)),
                    "box": box
                })
            
            return results
            
        except Exception as e:
            logger.info(f"[EnhancedScreenRecognition] EasyOCR识别失败: {e}")
            return []
    
    def _extract_ui_elements(self, ocr_results: List[Dict[str, Any]]) -> List[UIElement]:
        """提取UI元素"""
        elements = []
        
        for result in ocr_results:
            element = UIElement(
                name=result.get("text", ""),
                position=result.get("position", (0, 0)),
                size=result.get("size", (0, 0)),
                text=result.get("text", ""),
                confidence=result.get("confidence", 0.0),
                element_type=self._classify_element(result.get("text", ""))
            )
            elements.append(element)
        
        return elements
    
    def _classify_element(self, text: str) -> str:
        """分类UI元素"""
        text_lower = text.lower()
        
        # 生命值相关
        if any(kw in text_lower for kw in ["hp", "health", "生命", "血量"]):
            return "health"
        
        # 魔法值相关
        if any(kw in text_lower for kw in ["mp", "mana", "魔法", "魔力"]):
            return "mana"
        
        # 物品栏相关
        if any(kw in text_lower for kw in ["inventory", "物品栏", "背包"]):
            return "inventory"
        
        # 菜单相关
        if any(kw in text_lower for kw in ["menu", "菜单", "设置", "options"]):
            return "menu"
        
        # 对话相关
        if any(kw in text_lower for kw in ["dialog", "对话", "talk"]):
            return "dialog"
        
        return "text"
    
    async def _infer_game_state(self, text: str, elements: List[UIElement], 
                               game_name: str = None) -> GameState:
        """推断游戏状态"""
        text_lower = text.lower()
        
        # 检查游戏模板
        if game_name and game_name in self.game_templates:
            template = self.game_templates[game_name]
            return self._match_template(text_lower, elements, template)
        
        # 通用状态推断
        # 菜单状态
        if any(kw in text_lower for kw in ["menu", "菜单", "主菜单", "开始游戏", "设置"]):
            return GameState.MENU
        
        # 物品栏状态
        if any(kw in text_lower for kw in ["inventory", "物品栏", "背包", "箱子"]):
            return GameState.INVENTORY
        
        # 对话状态
        if any(kw in text_lower for kw in ["dialog", "对话", "talk", "说话"]):
            return GameState.DIALOG
        
        # 暂停状态
        if any(kw in text_lower for kw in ["pause", "暂停", "继续"]):
            return GameState.PAUSED
        
        # 加载状态
        if any(kw in text_lower for kw in ["loading", "加载", "请稍候"]):
            return GameState.LOADING
        
        # 默认为游戏中
        return GameState.PLAYING
    
    def _match_template(self, text: str, elements: List[UIElement], 
                       template: Dict[str, Any]) -> GameState:
        """匹配游戏模板"""
        # 获取模板中的状态关键词
        state_keywords = template.get("state_keywords", {})
        
        # 遍历所有状态
        for state_name, keywords in state_keywords.items():
            if any(kw in text for kw in keywords):
                try:
                    return GameState(state_name)
                except ValueError:
                    continue
        
        return GameState.PLAYING
    
    def _calculate_confidence(self, ocr_results: List[Dict[str, Any]], 
                            game_state: GameState) -> float:
        """计算置信度"""
        if not ocr_results:
            return 0.0
        
        # OCR置信度
        ocr_confidence = sum(r.get("confidence", 0) for r in ocr_results) / len(ocr_results)
        
        # 状态推断置信度
        state_confidence = 0.8 if game_state != GameState.UNKNOWN else 0.3
        
        # 综合置信度
        return (ocr_confidence * 0.6 + state_confidence * 0.4)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "ocr_engine": self.ocr_engine,
            "mode": self.mode.value,
            "total_recognitions": self.stats["total_recognitions"],
            "successful_recognitions": self.stats["successful_recognitions"],
            "success_rate": self.stats["successful_recognitions"] / max(1, self.stats["total_recognitions"]),
            "average_confidence": self.stats["average_confidence"],
            "average_time_ms": self.stats["average_time_ms"],
            "registered_games": len(self.game_templates),
            "history_size": len(self.recognition_history)
        }

# 全局实例
_enhanced_recognition: Optional[EnhancedScreenRecognition] = None

def get_enhanced_screen_recognition(config: Dict[str, Any] = None) -> EnhancedScreenRecognition:
    """获取增强版屏幕识别器实例"""
    global _enhanced_recognition
    if _enhanced_recognition is None:
        _enhanced_recognition = EnhancedScreenRecognition(config)
    return _enhanced_recognition
