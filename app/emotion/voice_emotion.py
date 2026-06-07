"""
情感语音控制模块
将情感信息转化为语音参数，实现情感化语音合成
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class VoiceEmotion(Enum):
    """语音情感类型"""
    NEUTRAL = "neutral"     # 中性
    HAPPY = "happy"         # 开心
    SAD = "sad"             # 悲伤
    ANGRY = "angry"         # 生气
    FEARFUL = "fearful"     # 恐惧
    SURPRISED = "surprised" # 惊讶
    CALM = "calm"           # 平静
    EXCITED = "excited"     # 兴奋
    TENDER = "tender"       # 温柔
    CONFIDENT = "confident" # 自信

@dataclass
class VoiceEmotionParams:
    """语音情感参数"""
    # 基础参数
    pitch_shift: float = 0.0      # 音高偏移 (-12 到 +12 半音)
    speed_factor: float = 1.0     # 语速因子 (0.5 到 2.0)
    volume_factor: float = 1.0    # 音量因子 (0.5 到 2.0)
    
    # 高级参数
    vibrato_rate: float = 0.0     # 颤音频率 (0-10 Hz)
    vibrato_depth: float = 0.0    # 颤音深度 (0-1)
    breathiness: float = 0.0      # 气息感 (0-1)
    brightness: float = 0.5       # 明亮度 (0-1)
    warmth: float = 0.5           # 温暖度 (0-1)
    
    # 韵律参数
    stress_pattern: str = ""      # 重音模式
    intonation: str = "natural"   # 语调 (natural, rising, falling)

class EmotionVoiceMapper:
    """情感到语音参数的映射器"""
    
    def __init__(self) -> None:
        # 情感参数映射表
        self.emotion_params: Dict[VoiceEmotion, VoiceEmotionParams] = {
            VoiceEmotion.NEUTRAL: VoiceEmotionParams(
                pitch_shift=0.0,
                speed_factor=1.0,
                volume_factor=1.0,
                vibrato_rate=0.0,
                vibrato_depth=0.0,
                breathiness=0.1,
                brightness=0.5,
                warmth=0.5,
                intonation="natural"
            ),
            VoiceEmotion.HAPPY: VoiceEmotionParams(
                pitch_shift=2.0,
                speed_factor=1.1,
                volume_factor=1.1,
                vibrato_rate=2.0,
                vibrato_depth=0.1,
                breathiness=0.2,
                brightness=0.7,
                warmth=0.6,
                intonation="rising"
            ),
            VoiceEmotion.SAD: VoiceEmotionParams(
                pitch_shift=-2.0,
                speed_factor=0.8,
                volume_factor=0.8,
                vibrato_rate=1.0,
                vibrato_depth=0.2,
                breathiness=0.3,
                brightness=0.3,
                warmth=0.4,
                intonation="falling"
            ),
            VoiceEmotion.ANGRY: VoiceEmotionParams(
                pitch_shift=3.0,
                speed_factor=1.2,
                volume_factor=1.3,
                vibrato_rate=5.0,
                vibrato_depth=0.3,
                breathiness=0.1,
                brightness=0.8,
                warmth=0.3,
                intonation="rising"
            ),
            VoiceEmotion.FEARFUL: VoiceEmotionParams(
                pitch_shift=4.0,
                speed_factor=1.3,
                volume_factor=0.9,
                vibrato_rate=8.0,
                vibrato_depth=0.4,
                breathiness=0.4,
                brightness=0.6,
                warmth=0.3,
                intonation="rising"
            ),
            VoiceEmotion.SURPRISED: VoiceEmotionParams(
                pitch_shift=5.0,
                speed_factor=1.2,
                volume_factor=1.2,
                vibrato_rate=3.0,
                vibrato_depth=0.2,
                breathiness=0.2,
                brightness=0.8,
                warmth=0.5,
                intonation="rising"
            ),
            VoiceEmotion.CALM: VoiceEmotionParams(
                pitch_shift=-1.0,
                speed_factor=0.9,
                volume_factor=0.9,
                vibrato_rate=0.5,
                vibrato_depth=0.05,
                breathiness=0.15,
                brightness=0.4,
                warmth=0.6,
                intonation="natural"
            ),
            VoiceEmotion.EXCITED: VoiceEmotionParams(
                pitch_shift=4.0,
                speed_factor=1.3,
                volume_factor=1.2,
                vibrato_rate=4.0,
                vibrato_depth=0.2,
                breathiness=0.2,
                brightness=0.9,
                warmth=0.7,
                intonation="rising"
            ),
            VoiceEmotion.TENDER: VoiceEmotionParams(
                pitch_shift=1.0,
                speed_factor=0.85,
                volume_factor=0.85,
                vibrato_rate=1.0,
                vibrato_depth=0.1,
                breathiness=0.3,
                brightness=0.4,
                warmth=0.8,
                intonation="natural"
            ),
            VoiceEmotion.CONFIDENT: VoiceEmotionParams(
                pitch_shift=0.0,
                speed_factor=1.0,
                volume_factor=1.1,
                vibrato_rate=0.0,
                vibrato_depth=0.0,
                breathiness=0.05,
                brightness=0.6,
                warmth=0.5,
                intonation="falling"
            )
        }
        
        # 情感关键词映射
        self.emotion_keywords: Dict[str, VoiceEmotion] = {
            "开心": VoiceEmotion.HAPPY,
            "快乐": VoiceEmotion.HAPPY,
            "高兴": VoiceEmotion.HAPPY,
            "悲伤": VoiceEmotion.SAD,
            "难过": VoiceEmotion.SAD,
            "伤心": VoiceEmotion.SAD,
            "生气": VoiceEmotion.ANGRY,
            "愤怒": VoiceEmotion.ANGRY,
            "害怕": VoiceEmotion.FEARFUL,
            "恐惧": VoiceEmotion.FEARFUL,
            "惊讶": VoiceEmotion.SURPRISED,
            "平静": VoiceEmotion.CALM,
            "冷静": VoiceEmotion.CALM,
            "兴奋": VoiceEmotion.EXCITED,
            "激动": VoiceEmotion.EXCITED,
            "温柔": VoiceEmotion.TENDER,
            "自信": VoiceEmotion.CONFIDENT
        }
        
        logger.info("[EmotionVoiceMapper] 初始化完成")
    
    def get_params(self, emotion: VoiceEmotion) -> VoiceEmotionParams:
        """获取情感对应的语音参数"""
        return self.emotion_params.get(emotion, self.emotion_params[VoiceEmotion.NEUTRAL])
    
    def get_params_by_name(self, emotion_name: str) -> VoiceEmotionParams:
        """根据情感名称获取语音参数"""
        try:
            emotion = VoiceEmotion(emotion_name)
            return self.get_params(emotion)
        except ValueError:
            # 尝试从关键词映射
            emotion = self.emotion_keywords.get(emotion_name, VoiceEmotion.NEUTRAL)
            return self.get_params(emotion)
    
    def detect_emotion_from_text(self, text: str) -> VoiceEmotion:
        """从文本检测情感"""
        text_lower = text.lower()
        
        # 检查关键词
        for keyword, emotion in self.emotion_keywords.items():
            if keyword in text_lower:
                return emotion
        
        # 检查标点符号
        if "！" in text or "!" in text:
            return VoiceEmotion.EXCITED
        if "？" in text or "?" in text:
            return VoiceEmotion.SURPRISED
        
        return VoiceEmotion.NEUTRAL
    
    def blend_params(self, params1: VoiceEmotionParams, params2: VoiceEmotionParams, 
                    ratio: float = 0.5) -> VoiceEmotionParams:
        """混合两个情感参数"""
        return VoiceEmotionParams(
            pitch_shift=params1.pitch_shift * (1 - ratio) + params2.pitch_shift * ratio,
            speed_factor=params1.speed_factor * (1 - ratio) + params2.speed_factor * ratio,
            volume_factor=params1.volume_factor * (1 - ratio) + params2.volume_factor * ratio,
            vibrato_rate=params1.vibrato_rate * (1 - ratio) + params2.vibrato_rate * ratio,
            vibrato_depth=params1.vibrato_depth * (1 - ratio) + params2.vibrato_depth * ratio,
            breathiness=params1.breathiness * (1 - ratio) + params2.breathiness * ratio,
            brightness=params1.brightness * (1 - ratio) + params2.brightness * ratio,
            warmth=params1.warmth * (1 - ratio) + params2.warmth * ratio,
            intonation=params1.intonation if ratio < 0.5 else params2.intonation
        )

class EmotionVoiceController:
    """情感语音控制器"""
    
    def __init__(self) -> None:
        self.mapper = EmotionVoiceMapper()
        self.current_emotion: VoiceEmotion = VoiceEmotion.NEUTRAL
        self.emotion_history: list = []
        
        logger.info("[EmotionVoiceController] 初始化完成")
    
    def set_emotion(self, emotion: VoiceEmotion) -> None:
        """设置当前情感"""
        self.current_emotion = emotion
        self.emotion_history.append(emotion)
        
        # 保持最近10条记录
        if len(self.emotion_history) > 10:
            self.emotion_history = self.emotion_history[-10:]
    
    def get_current_params(self) -> VoiceEmotionParams:
        """获取当前情感的语音参数"""
        return self.mapper.get_params(self.current_emotion)
    
    def get_params_for_text(self, text: str) -> VoiceEmotionParams:
        """根据文本内容获取语音参数"""
        # 检测文本情感
        detected_emotion = self.mapper.detect_emotion_from_text(text)
        
        # 如果检测到情感，使用检测到的；否则使用当前情感
        if detected_emotion != VoiceEmotion.NEUTRAL:
            return self.mapper.get_params(detected_emotion)
        
        return self.get_current_params()
    
    def get_tts_params(self, text: str) -> Dict[str, Any]:
        """获取TTS参数（用于传递给TTS引擎）"""
        params = self.get_params_for_text(text)
        
        return {
            "pitch_shift": params.pitch_shift,
            "speed_factor": params.speed_factor,
            "volume_factor": params.volume_factor,
            "vibrato_rate": params.vibrato_rate,
            "vibrato_depth": params.vibrato_depth,
            "breathiness": params.breathiness,
            "brightness": params.brightness,
            "warmth": params.warmth,
            "intonation": params.intonation
        }
    
    def get_emotion_dominant(self) -> VoiceEmotion:
        """获取主导情感（基于历史）"""
        if not self.emotion_history:
            return VoiceEmotion.NEUTRAL
        
        # 统计情感频率
        emotion_counts = {}
        for emotion in self.emotion_history:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        # 返回最频繁的情感
        return max(emotion_counts, key=emotion_counts.get)

# 全局实例
_emotion_voice_controller: Optional[EmotionVoiceController] = None

def get_emotion_voice_controller() -> EmotionVoiceController:
    """获取情感语音控制器实例"""
    global _emotion_voice_controller
    if _emotion_voice_controller is None:
        _emotion_voice_controller = EmotionVoiceController()
    return _emotion_voice_controller
