"""
TTS语速控制模块
提供语速调整、停顿控制、情感语速等功能
"""

import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class SpeedMode(Enum):
    """语速模式"""
    SLOW = "slow"           # 慢速 (0.7x)
    NORMAL = "normal"       # 正常 (1.0x)
    FAST = "fast"           # 快速 (1.3x)
    VERY_FAST = "very_fast" # 极快 (1.6x)
    CUSTOM = "custom"       # 自定义

@dataclass
class SpeedConfig:
    """语速配置"""
    mode: SpeedMode = SpeedMode.NORMAL
    speed_factor: float = 1.0  # 语速因子 (0.5-2.0)
    
    # 停顿控制
    pause_after_sentence: float = 0.5  # 句子后停顿(秒)
    pause_after_comma: float = 0.2     # 逗号后停顿(秒)
    pause_after_question: float = 0.8  # 问号后停顿(秒)
    
    # 情感语速
    emotion_speed_map: Dict[str, float] = None
    
    def __post_init__(self) -> None:
        """初始化后处理"""
        if self.emotion_speed_map is None:
            self.emotion_speed_map = {
                "happy": 1.1,      # 开心时稍快
                "sad": 0.8,        # 悲伤时较慢
                "angry": 1.2,      # 生气时较快
                "calm": 0.9,       # 平静时稍慢
                "excited": 1.3,    # 兴奋时快
                "anxious": 1.1,    # 焦虑时稍快
                "neutral": 1.0     # 中性时正常
            }

class SpeedController:
    """语速控制器"""
    
    def __init__(self, config: SpeedConfig = None) -> None:
        self.config = config or SpeedConfig()
        
        # 语速预设
        self.speed_presets = {
            SpeedMode.SLOW: 0.7,
            SpeedMode.NORMAL: 1.0,
            SpeedMode.FAST: 1.3,
            SpeedMode.VERY_FAST: 1.6
        }
        
        logger.info("[SpeedController] 初始化完成")
    
    def get_speed_factor(self, emotion: str = None) -> float:
        """获取语速因子"""
        # 基础语速
        if self.config.mode == SpeedMode.CUSTOM:
            base_speed = self.config.speed_factor
        else:
            base_speed = self.speed_presets.get(self.config.mode, 1.0)
        
        # 根据情感调整
        if emotion and self.config.emotion_speed_map:
            emotion_factor = self.config.emotion_speed_map.get(emotion, 1.0)
            base_speed *= emotion_factor
        
        # 限制范围
        return max(0.5, min(2.0, base_speed))
    
    def adjust_text_for_speed(self, text: str, speed_factor: float = None) -> str:
        """调整文本以适应语速"""
        if speed_factor is None:
            speed_factor = self.get_speed_factor()
        
        # 快速模式：移除多余标点
        if speed_factor > 1.2:
            text = self._simplify_punctuation(text)
        
        # 慢速模式：添加更多停顿
        if speed_factor < 0.8:
            text = self._add_pauses(text)
        
        return text
    
    def _simplify_punctuation(self, text: str) -> str:
        """简化标点（用于快速模式）"""
        # 移除省略号
        text = re.sub(r'…', '。', text)
        text = re.sub(r'\.{3,}', '。', text)
        
        # 合并连续标点
        text = re.sub(r'[，,]{2,}', '，', text)
        text = re.sub(r'[。.]{2,}', '。', text)
        
        return text
    
    def _add_pauses(self, text: str) -> str:
        """添加停顿（用于慢速模式）"""
        # 在句子后添加停顿标记
        text = re.sub(r'([。！？])', r'\1<pause:500>', text)
        
        # 在逗号后添加短停顿
        text = re.sub(r'([，,])', r'\1<pause:200>', text)
        
        return text
    
    def get_pause_duration(self, punctuation: str) -> float:
        """获取标点对应的停顿时长"""
        pause_map = {
            '。': self.config.pause_after_sentence,
            '！': self.config.pause_after_sentence,
            '？': self.config.pause_after_question,
            '，': self.config.pause_after_comma,
            '、': self.config.pause_after_comma,
            '；': self.config.pause_after_sentence,
            '：': self.config.pause_after_comma,
            '...': self.config.pause_after_sentence * 1.5,
            '…': self.config.pause_after_sentence * 1.5
        }
        
        return pause_map.get(punctuation, 0)
    
    def split_by_speed(self, text: str, max_chunk_length: int = 100) -> List[str]:
        """根据语速分割文本"""
        speed_factor = self.get_speed_factor()
        
        # 快速模式：更长的chunks
        if speed_factor > 1.2:
            max_chunk_length = int(max_chunk_length * 1.3)
        
        # 慢速模式：更短的chunks
        if speed_factor < 0.8:
            max_chunk_length = int(max_chunk_length * 0.7)
        
        # 按句子分割
        sentences = re.split(r'([。！？])', text)
        
        chunks = []
        current_chunk = ""
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            punctuation = sentences[i + 1] if i + 1 < len(sentences) else ""
            
            full_sentence = sentence + punctuation
            
            if len(current_chunk) + len(full_sentence) > max_chunk_length:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = full_sentence
            else:
                current_chunk += full_sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return {
            "mode": self.config.mode.value,
            "speed_factor": self.config.speed_factor,
            "pause_after_sentence": self.config.pause_after_sentence,
            "pause_after_comma": self.config.pause_after_comma,
            "pause_after_question": self.config.pause_after_question
        }
    
    def update_config(self, config: Dict[str, Any]) -> None:
        """更新配置"""
        if "mode" in config:
            self.config.mode = SpeedMode(config["mode"])
        if "speed_factor" in config:
            self.config.speed_factor = config["speed_factor"]
        if "pause_after_sentence" in config:
            self.config.pause_after_sentence = config["pause_after_sentence"]
        if "pause_after_comma" in config:
            self.config.pause_after_comma = config["pause_after_comma"]
        if "pause_after_question" in config:
            self.config.pause_after_question = config["pause_after_question"]
        
        logger.info(f"[SpeedController] 配置已更新: {config}")

# 全局实例
_speed_controller: Optional[SpeedController] = None

def get_speed_controller(config: SpeedConfig = None) -> SpeedController:
    """获取语速控制器实例"""
    global _speed_controller
    if _speed_controller is None:
        _speed_controller = SpeedController(config)
    return _speed_controller
