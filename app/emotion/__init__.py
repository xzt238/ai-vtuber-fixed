"""
情感系统模块
支持情感识别、情感表达、情感记忆
"""

import json
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class EmotionType(Enum):
    """情感类型"""
    NEUTRAL = "neutral"  # 中性
    HAPPY = "happy"  # 开心
    SAD = "sad"  # 悲伤
    ANGRY = "angry"  # 生气
    SURPRISED = "surprised"  # 惊讶
    FEARFUL = "fearful"  # 恐惧
    DISGUSTED = "disgusted"  # 厌恶
    CONTEMPTUOUS = "contemptuous"  # 轻蔑
    EXCITED = "excited"  # 兴奋
    CALM = "calm"  # 平静
    ANXIOUS = "anxious"  # 焦虑
    LOVING = "loving"  # 爱意
    GRATEFUL = "grateful"  # 感激
    CURIOUS = "curious"  # 好奇
    CONFUSED = "confused"  # 困惑

@dataclass
class EmotionState:
    """情感状态"""
    primary_emotion: EmotionType = EmotionType.NEUTRAL
    intensity: float = 0.5  # 强度 0-1
    valence: float = 0.0  # 效价 -1 到 1 (负面到正面)
    arousal: float = 0.5  # 唤醒度 0-1 (平静到兴奋)
    secondary_emotions: Dict[EmotionType, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class EmotionAnalysis:
    """情感分析结果"""
    text: str
    emotion_state: EmotionState
    confidence: float = 0.0
    keywords: List[str] = field(default_factory=list)
    source: str = "text"  # text, voice, face

@dataclass
class UserProfile:
    """用户情感档案"""
    user_id: str
    emotion_history: List[EmotionState] = field(default_factory=list)
    dominant_emotions: Dict[EmotionType, float] = field(default_factory=dict)
    interaction_count: int = 0
    last_interaction: Optional[datetime] = None
    preferences: Dict[str, Any] = field(default_factory=dict)

class TextEmotionAnalyzer:
    """文本情感分析器"""
    
    def __init__(self):
        # 情感关键词库
        self.emotion_keywords = {
            EmotionType.HAPPY: ["开心", "快乐", "高兴", "幸福", "愉快", "欢乐", "兴奋", "棒", "好", "喜欢", "爱", "哈哈", "嘻嘻"],
            EmotionType.SAD: ["伤心", "难过", "悲伤", "痛苦", "失望", "沮丧", "哭", "泪", "可怜", "遗憾"],
            EmotionType.ANGRY: ["生气", "愤怒", "恼火", "烦", "讨厌", "恨", "气死", "滚", "闭嘴"],
            EmotionType.SURPRISED: ["惊讶", "震惊", "意外", "没想到", "天啊", "哇", "啊", "什么"],
            EmotionType.FEARFUL: ["害怕", "恐惧", "担心", "焦虑", "紧张", "不安", "怕", "吓"],
            EmotionType.DISGUSTED: ["恶心", "厌恶", "讨厌", "反感", "呕", "吐"],
            EmotionType.EXCITED: ["激动", "兴奋", "期待", "迫不及待", "太棒了", "耶"],
            EmotionType.CALM: ["平静", "冷静", "放松", "安心", "舒适", "宁静"],
            EmotionType.ANXIOUS: ["焦虑", "紧张", "不安", "担心", "忧虑", "压力"],
            EmotionType.LOVING: ["爱", "喜欢", "想念", "思念", "亲爱的", "宝贝", "心"],
            EmotionType.GRATEFUL: ["感谢", "谢谢", "感激", "感恩", "多谢"],
            EmotionType.CURIOUS: ["好奇", "想知道", "有趣", "奇怪", "为什么"],
            EmotionType.CONFUSED: ["困惑", "迷茫", "不懂", "不明白", "搞不懂", "晕"]
        }
    
    async def analyze(self, text: str) -> EmotionAnalysis:
        """分析文本情感"""
        # 统计情感关键词
        emotion_scores = {}
        matched_keywords = []
        
        for emotion, keywords in self.emotion_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1
                    matched_keywords.append(keyword)
            if score > 0:
                emotion_scores[emotion] = score
        
        # 确定主要情感
        if emotion_scores:
            primary_emotion = max(emotion_scores, key=emotion_scores.get)
            max_score = emotion_scores[primary_emotion]
            
            # 计算强度
            intensity = min(max_score / 3.0, 1.0)  # 最多3个关键词达到最大强度
            
            # 计算效价和唤醒度
            valence = self._calculate_valence(primary_emotion)
            arousal = self._calculate_arousal(primary_emotion)
        else:
            primary_emotion = EmotionType.NEUTRAL
            intensity = 0.5
            valence = 0.0
            arousal = 0.5
        
        # 创建情感状态
        emotion_state = EmotionState(
            primary_emotion=primary_emotion,
            intensity=intensity,
            valence=valence,
            arousal=arousal,
            secondary_emotions=emotion_scores
        )
        
        return EmotionAnalysis(
            text=text,
            emotion_state=emotion_state,
            confidence=0.8 if emotion_scores else 0.5,
            keywords=matched_keywords,
            source="text"
        )
    
    def _calculate_valence(self, emotion: EmotionType) -> float:
        """计算效价（正面/负面）"""
        valence_map = {
            EmotionType.NEUTRAL: 0.0,
            EmotionType.HAPPY: 0.8,
            EmotionType.SAD: -0.7,
            EmotionType.ANGRY: -0.6,
            EmotionType.SURPRISED: 0.3,
            EmotionType.FEARFUL: -0.5,
            EmotionType.DISGUSTED: -0.6,
            EmotionType.CONTEMPTUOUS: -0.4,
            EmotionType.EXCITED: 0.7,
            EmotionType.CALM: 0.3,
            EmotionType.ANXIOUS: -0.4,
            EmotionType.LOVING: 0.9,
            EmotionType.GRATEFUL: 0.8,
            EmotionType.CURIOUS: 0.4,
            EmotionType.CONFUSED: -0.2
        }
        return valence_map.get(emotion, 0.0)
    
    def _calculate_arousal(self, emotion: EmotionType) -> float:
        """计算唤醒度（平静/兴奋）"""
        arousal_map = {
            EmotionType.NEUTRAL: 0.5,
            EmotionType.HAPPY: 0.7,
            EmotionType.SAD: 0.3,
            EmotionType.ANGRY: 0.8,
            EmotionType.SURPRISED: 0.9,
            EmotionType.FEARFUL: 0.8,
            EmotionType.DISGUSTED: 0.5,
            EmotionType.CONTEMPTUOUS: 0.4,
            EmotionType.EXCITED: 0.9,
            EmotionType.CALM: 0.2,
            EmotionType.ANXIOUS: 0.7,
            EmotionType.LOVING: 0.6,
            EmotionType.GRATEFUL: 0.5,
            EmotionType.CURIOUS: 0.6,
            EmotionType.CONFUSED: 0.5
        }
        return arousal_map.get(emotion, 0.5)

class EmotionExpression:
    """情感表达器"""
    
    def __init__(self):
        # 情感化回复模板
        self.response_templates = {
            EmotionType.HAPPY: [
                "看到你这么开心，我也很高兴呢！",
                "太棒了！让我们一起庆祝吧！",
                "你的快乐感染到我了！"
            ],
            EmotionType.SAD: [
                "别难过，一切都会好起来的。",
                "我在这里陪着你，想聊聊吗？",
                "抱抱你～不要伤心哦。"
            ],
            EmotionType.ANGRY: [
                "深呼吸，冷静一下。",
                "我理解你的感受，慢慢说。",
                "有什么我可以帮忙的吗？"
            ],
            EmotionType.SURPRISED: [
                "哇！真的吗？",
                "这太令人惊讶了！",
                "没想到会发生这种事！"
            ],
            EmotionType.FEARFUL: [
                "别怕，有我在呢。",
                "深呼吸，你会没事的。",
                "我陪着你，不用害怕。"
            ],
            EmotionType.CALM: [
                "保持平静，这样很好。",
                "你看起来很放松呢。",
                "平静的心态很重要。"
            ],
            EmotionType.ANXIOUS: [
                "别担心，一步一步来。",
                "深呼吸，放松一下。",
                "我理解你的焦虑，慢慢来。"
            ],
            EmotionType.LOVING: [
                "我也很喜欢你呢！",
                "你真是太温暖了！",
                "有你真好！"
            ],
            EmotionType.GRATEFUL: [
                "不客气！我很高兴能帮到你。",
                "这是我应该做的！",
                "你的感谢让我很开心！"
            ],
            EmotionType.CURIOUS: [
                "这个问题很有趣！",
                "让我想想...",
                "我也很好奇呢！"
            ],
            EmotionType.CONFUSED: [
                "别着急，我来帮你理清思路。",
                "这个问题确实有点复杂。",
                "让我换个方式解释一下。"
            ]
        }
    
    def generate_response(self, emotion_state: EmotionState, context: str = "") -> str:
        """生成情感化回复"""
        import random
        
        emotion = emotion_state.primary_emotion
        templates = self.response_templates.get(emotion, [])
        
        if templates:
            return random.choice(templates)
        
        return ""
    
    def get_emotion_emoji(self, emotion: EmotionType) -> str:
        """获取情感对应的emoji"""
        emoji_map = {
            EmotionType.NEUTRAL: "😐",
            EmotionType.HAPPY: "😊",
            EmotionType.SAD: "😢",
            EmotionType.ANGRY: "😠",
            EmotionType.SURPRISED: "😲",
            EmotionType.FEARFUL: "😨",
            EmotionType.DISGUSTED: "🤢",
            EmotionType.CONTEMPTUOUS: "😏",
            EmotionType.EXCITED: "🤩",
            EmotionType.CALM: "😌",
            EmotionType.ANXIOUS: "😰",
            EmotionType.LOVING: "🥰",
            EmotionType.GRATEFUL: "🙏",
            EmotionType.CURIOUS: "🤔",
            EmotionType.CONFUSED: "😵"
        }
        return emoji_map.get(emotion, "😐")
    
    def get_emotion_animation(self, emotion: EmotionType) -> str:
        """获取情感对应的动画"""
        animation_map = {
            EmotionType.NEUTRAL: "idle",
            EmotionType.HAPPY: "happy",
            EmotionType.SAD: "sad",
            EmotionType.ANGRY: "angry",
            EmotionType.SURPRISED: "surprised",
            EmotionType.FEARFUL: "fearful",
            EmotionType.DISGUSTED: "disgusted",
            EmotionType.CONTEMPTUOUS: "contemptuous",
            EmotionType.EXCITED: "excited",
            EmotionType.CALM: "calm",
            EmotionType.ANXIOUS: "anxious",
            EmotionType.LOVING: "loving",
            EmotionType.GRATEFUL: "grateful",
            EmotionType.CURIOUS: "curious",
            EmotionType.CONFUSED: "confused"
        }
        return animation_map.get(emotion, "idle")

class EmotionMemory:
    """情感记忆器"""
    
    def __init__(self, storage_dir: str = "./memory/emotion"):
        self.storage_dir = Path(storage_dir)
        self.profiles_file = self.storage_dir / "user_profiles.json"
        self.profiles: Dict[str, UserProfile] = {}
        
        self._load_profiles()
    
    def _load_profiles(self):
        """加载用户档案"""
        try:
            if self.profiles_file.exists():
                with open(self.profiles_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, profile_dict in data.items():
                        self.profiles[user_id] = UserProfile(**profile_dict)
                logger.info(f"[Emotion] 加载了 {len(self.profiles)} 个用户档案")
        except Exception as e:
            logger.info(f"[Emotion] 加载用户档案失败: {e}")
    
    def _save_profiles(self):
        """保存用户档案"""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            
            data = {}
            for user_id, profile in self.profiles.items():
                data[user_id] = {
                    "user_id": profile.user_id,
                    "interaction_count": profile.interaction_count,
                    "preferences": profile.preferences
                }
            
            with open(self.profiles_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.info(f"[Emotion] 保存用户档案失败: {e}")
    
    def get_or_create_profile(self, user_id: str) -> UserProfile:
        """获取或创建用户档案"""
        if user_id not in self.profiles:
            self.profiles[user_id] = UserProfile(user_id=user_id)
        return self.profiles[user_id]
    
    async def record_emotion(self, user_id: str, emotion_state: EmotionState):
        """记录情感"""
        profile = self.get_or_create_profile(user_id)
        
        # 添加到历史
        profile.emotion_history.append(emotion_state)
        
        # 保持最近100条记录
        if len(profile.emotion_history) > 100:
            profile.emotion_history = profile.emotion_history[-100:]
        
        # 更新主导情感
        self._update_dominant_emotions(profile)
        
        # 更新交互信息
        profile.interaction_count += 1
        profile.last_interaction = datetime.now()
        
        self._save_profiles()
    
    def _update_dominant_emotions(self, profile: UserProfile):
        """更新主导情感"""
        emotion_counts = {}
        for state in profile.emotion_history[-20:]:  # 最近20条
            emotion = state.primary_emotion
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        # 归一化
        total = sum(emotion_counts.values())
        if total > 0:
            profile.dominant_emotions = {
                emotion: count / total 
                for emotion, count in emotion_counts.items()
            }
    
    def get_user_emotion_trend(self, user_id: str) -> Dict[str, Any]:
        """获取用户情感趋势"""
        profile = self.get_or_create_profile(user_id)
        
        if not profile.emotion_history:
            return {"trend": "neutral", "dominant_emotions": {}}
        
        # 计算最近的情感趋势
        recent_states = profile.emotion_history[-10:]
        avg_valence = sum(s.valence for s in recent_states) / len(recent_states)
        avg_arousal = sum(s.arousal for s in recent_states) / len(recent_states)
        
        # 确定趋势
        if avg_valence > 0.3:
            trend = "positive"
        elif avg_valence < -0.3:
            trend = "negative"
        else:
            trend = "neutral"
        
        return {
            "trend": trend,
            "avg_valence": avg_valence,
            "avg_arousal": avg_arousal,
            "dominant_emotions": profile.dominant_emotions,
            "interaction_count": profile.interaction_count
        }

class EmotionManager:
    """情感管理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        storage_dir = self.config.get("storage_dir", "./memory/emotion")
        
        # 初始化组件
        self.text_analyzer = TextEmotionAnalyzer()
        self.expression = EmotionExpression()
        self.memory = EmotionMemory(storage_dir)
        
        # 当前情感状态
        self.current_state = EmotionState()
        
        logger.info(f"[Emotion] 初始化完成")
    
    async def analyze_text(self, text: str, user_id: str = None) -> EmotionAnalysis:
        """分析文本情感"""
        analysis = await self.text_analyzer.analyze(text)
        
        # 记录到记忆
        if user_id:
            await self.memory.record_emotion(user_id, analysis.emotion_state)
        
        # 更新当前状态
        self.current_state = analysis.emotion_state
        
        return analysis
    
    async def analyze_and_respond(self, text: str, user_id: str = None) -> Tuple[EmotionState, str]:
        """分析情感并生成回复"""
        # 分析情感
        analysis = await self.analyze_text(text, user_id)
        
        # 生成情感化回复
        response = self.expression.generate_response(analysis.emotion_state)
        
        return analysis.emotion_state, response
    
    def get_emotion_response(self, emotion_state: EmotionState) -> str:
        """获取情感化回复"""
        return self.expression.generate_response(emotion_state)
    
    def get_emotion_emoji(self, emotion: EmotionType) -> str:
        """获取情感emoji"""
        return self.expression.get_emotion_emoji(emotion)
    
    def get_emotion_animation(self, emotion: EmotionType) -> str:
        """获取情感动画"""
        return self.expression.get_emotion_animation(emotion)
    
    def get_user_emotion_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户情感档案"""
        return self.memory.get_user_emotion_trend(user_id)
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "current_emotion": self.current_state.primary_emotion.value,
            "current_intensity": self.current_state.intensity,
            "current_valence": self.current_state.valence,
            "current_arousal": self.current_state.arousal,
            "users_tracked": len(self.memory.profiles)
        }

# 全局情感管理器实例
_emotion_manager: Optional[EmotionManager] = None

def get_emotion_manager(config: Dict[str, Any] = None) -> EmotionManager:
    """获取情感管理器实例"""
    global _emotion_manager
    if _emotion_manager is None:
        _emotion_manager = EmotionManager(config)
    return _emotion_manager
