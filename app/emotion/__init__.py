"""
=====================================
情绪表达系统
=====================================

实现 AI 情绪识别 → Live2D 动作/表情映射。

架构：
- EmotionClassifier — 从 LLM 回复中提取情绪标签
- EmotionMapper — 情绪标签 → Live2D 动作/表情映射
- EmotionManager — 管理情绪状态和动画触发

支持的情绪：
- 开心 (happy) → 笑脸表情 + 摇摆动作
- 悲伤 (sad) → 悲伤表情 + 低头动作
- 惊讶 (surprise) → 惊讶表情 + 后仰动作
- 愤怒 (angry) → 愤怒表情 + 摇头动作
- 害羞 (shy) → 害羞表情 + 捂脸动作
- 思考 (thinking) → 思考表情 + 歪头动作
- 平静 (neutral) → 默认表情 + 待机动作

作者: 咕咕嘎嘎
日期: 2026-06-02
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# ==================== 情绪枚举 ====================

class Emotion(Enum):
    """情绪类型"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    SURPRISE = "surprise"
    ANGRY = "angry"
    SHY = "shy"
    THINKING = "thinking"
    EXCITED = "excited"
    CONFUSED = "confused"
    LOVE = "love"


@dataclass
class EmotionState:
    """情绪状态"""
    emotion: Emotion
    intensity: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    source: str  # 来源: "text" | "explicit" | "context"


# ==================== 情绪分类器 ====================

class EmotionClassifier:
    """从文本中提取情绪标签

    使用关键词匹配 + 规则引擎，无需额外模型。
    可选：使用 LLM 进行更精确的情绪分析。
    """

    # 情绪关键词映射
    EMOTION_KEYWORDS = {
        Emotion.HAPPY: [
            "开心", "高兴", "快乐", "哈哈", "嘻嘻", "太好了", "棒", "赞",
            "happy", "glad", "great", "awesome", "wonderful", "yay",
            "😊", "😄", "😁", "🎉", "❤️", "💕", "✨"
        ],
        Emotion.SAD: [
            "难过", "伤心", "悲伤", "哭", "呜呜", "可惜", "遗憾",
            "sad", "sorry", "unfortunately", "regret",
            "😢", "😭", "💔", "😞"
        ],
        Emotion.SURPRISE: [
            "惊讶", "天哪", "哇", "居然", "没想到", "意外",
            "wow", "omg", "really", "amazing", "surprising",
            "😮", "😲", "🤯", "😱"
        ],
        Emotion.ANGRY: [
            "生气", "愤怒", "讨厌", "烦", "气死", "可恶",
            "angry", "hate", "annoying", "terrible",
            "😠", "😡", "🤬"
        ],
        Emotion.SHY: [
            "害羞", "不好意思", "羞", "脸红", "尴尬",
            "shy", "embarrassed", "blush",
            "😳", "☺️", "🙈"
        ],
        Emotion.THINKING: [
            "想想", "思考", "嗯...", "让我想想", "这个问题",
            "think", "hmm", "let me consider",
            "🤔", "💭"
        ],
        Emotion.EXCITED: [
            "兴奋", "激动", "太棒了", "期待", "迫不及待",
            "excited", "thrilled", "can't wait",
            "🤩", "😆", "🔥"
        ],
        Emotion.LOVE: [
            "喜欢", "爱", "可爱", "心动", "甜蜜",
            "love", "cute", "adorable", "sweet",
            "❤️", "💕", "🥰", "😍"
        ],
        Emotion.CONFUSED: [
            "困惑", "不懂", "什么意思", "啥", "为什么",
            "confused", "what", "why", "don't understand",
            "😕", "❓", "🤔"
        ]
    }

    def __init__(self, llm_callback=None):
        """
        Args:
            llm_callback: 可选的 LLM 回调函数，用于更精确的情绪分析
        """
        self._llm_callback = llm_callback
        self._context_emotion = Emotion.NEUTRAL  # 上下文情绪

    def classify(self, text: str, use_llm: bool = False) -> EmotionState:
        """从文本中提取情绪

        Args:
            text: 输入文本
            use_llm: 是否使用 LLM 进行更精确的分析

        Returns:
            EmotionState 情绪状态
        """
        if not text:
            return EmotionState(Emotion.NEUTRAL, 0.0, 1.0, "empty")

        # 1. 关键词匹配
        emotion, score = self._keyword_match(text)

        # 2. 如果置信度低，尝试 LLM 分析
        if score < 0.3 and use_llm and self._llm_callback:
            emotion, score = self._llm_classify(text)

        # 3. 更新上下文情绪
        if score > 0.5:
            self._context_emotion = emotion

        return EmotionState(
            emotion=emotion,
            intensity=min(1.0, score * 1.5),
            confidence=score,
            source="text" if score > 0.3 else "context"
        )

    def _keyword_match(self, text: str) -> Tuple[Emotion, float]:
        """关键词匹配"""
        text_lower = text.lower()
        scores = {}

        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            count = 0
            for keyword in keywords:
                if keyword in text_lower:
                    count += 1
            if count > 0:
                scores[emotion] = count / len(keywords)

        if not scores:
            return self._context_emotion, 0.1

        # 返回得分最高的情绪
        best_emotion = max(scores, key=scores.get)
        return best_emotion, min(1.0, scores[best_emotion] * 5)

    def _llm_classify(self, text: str) -> Tuple[Emotion, float]:
        """使用 LLM 进行情绪分类"""
        try:
            prompt = (
                f"分析以下文本的情绪，只返回情绪标签（happy/sad/surprise/angry/shy/thinking/"
                f"excited/love/confused/neutral）和置信度（0-1），格式: emotion,confidence\n\n"
                f"文本: {text}"
            )
            result = self._llm_callback(prompt)
            if result:
                parts = result.strip().split(",")
                if len(parts) == 2:
                    emotion_str = parts[0].strip().lower()
                    confidence = float(parts[1].strip())
                    try:
                        emotion = Emotion(emotion_str)
                        return emotion, confidence
                    except ValueError:
                        pass
        except Exception as e:
            logger.debug(f"LLM 情绪分析失败: {e}")

        return Emotion.NEUTRAL, 0.1


# ==================== 情绪映射器 ====================

class EmotionMapper:
    """情绪 → Live2D 动作/表情映射

    将情绪标签映射到具体的 Live2D 动作组和表情 ID。
    """

    # 默认映射表（可配置）
    DEFAULT_MAPPING = {
        Emotion.NEUTRAL: {
            "motion_group": "Idle",
            "expression": None,
            "description": "默认待机"
        },
        Emotion.HAPPY: {
            "motion_group": "TapBody",
            "expression": "happy",
            "description": "开心摇摆"
        },
        Emotion.SAD: {
            "motion_group": "Idle",
            "expression": "sad",
            "description": "悲伤低头"
        },
        Emotion.SURPRISE: {
            "motion_group": "TapBody",
            "expression": "surprise",
            "description": "惊讶后仰"
        },
        Emotion.ANGRY: {
            "motion_group": "TapBody",
            "expression": "angry",
            "description": "愤怒摇头"
        },
        Emotion.SHY: {
            "motion_group": "Idle",
            "expression": "shy",
            "description": "害羞捂脸"
        },
        Emotion.THINKING: {
            "motion_group": "Idle",
            "expression": "thinking",
            "description": "思考歪头"
        },
        Emotion.EXCITED: {
            "motion_group": "TapBody",
            "expression": "happy",
            "description": "兴奋跳动"
        },
        Emotion.LOVE: {
            "motion_group": "TapBody",
            "expression": "happy",
            "description": "心动脸红"
        },
        Emotion.CONFUSED: {
            "motion_group": "Idle",
            "expression": "thinking",
            "description": "困惑歪头"
        }
    }

    def __init__(self, custom_mapping: Dict[str, Dict] = None):
        """
        Args:
            custom_mapping: 自定义映射，覆盖默认映射
        """
        self.mapping = self.DEFAULT_MAPPING.copy()
        if custom_mapping:
            for key, value in custom_mapping.items():
                try:
                    emotion = Emotion(key)
                    self.mapping[emotion] = value
                except ValueError:
                    logger.warning(f"未知情绪类型: {key}")

    def get_animation(self, emotion: Emotion) -> Dict[str, Any]:
        """获取情绪对应的动画配置

        Args:
            emotion: 情绪类型

        Returns:
            动画配置字典
        """
        return self.mapping.get(emotion, self.mapping[Emotion.NEUTRAL])


# ==================== 情绪管理器 ====================

class EmotionManager:
    """情绪管理器

    管理情绪状态、触发动画、维护情绪历史。
    """

    def __init__(self, llm_callback=None, animation_callback=None):
        """
        Args:
            llm_callback: LLM 回调函数（用于情绪分析）
            animation_callback: 动画回调函数（用于触发动画）
        """
        self.classifier = EmotionClassifier(llm_callback)
        self.mapper = EmotionMapper()
        self._animation_callback = animation_callback
        self._current_emotion = EmotionState(Emotion.NEUTRAL, 0.0, 1.0, "init")
        self._emotion_history: List[EmotionState] = []
        self._max_history = 50

    @property
    def current_emotion(self) -> EmotionState:
        """当前情绪状态"""
        return self._current_emotion

    def process_text(self, text: str, trigger_animation: bool = True) -> EmotionState:
        """处理文本，提取情绪并触发动画

        Args:
            text: 输入文本
            trigger_animation: 是否触发动画

        Returns:
            情绪状态
        """
        emotion_state = self.classifier.classify(text)

        # 更新当前情绪
        self._current_emotion = emotion_state
        self._emotion_history.append(emotion_state)
        if len(self._emotion_history) > self._max_history:
            self._emotion_history = self._emotion_history[-self._max_history:]

        # 触发动画
        if trigger_animation and emotion_state.confidence > 0.3:
            self._trigger_animation(emotion_state)

        return emotion_state

    def set_emotion(self, emotion: Emotion, intensity: float = 0.8):
        """手动设置情绪

        Args:
            emotion: 情绪类型
            intensity: 情绪强度
        """
        state = EmotionState(emotion, intensity, 1.0, "explicit")
        self._current_emotion = state
        self._trigger_animation(state)

    def _trigger_animation(self, emotion_state: EmotionState):
        """触发动画"""
        if not self._animation_callback:
            return

        animation = self.mapper.get_animation(emotion_state.emotion)
        try:
            self._animation_callback(
                emotion=emotion_state.emotion.value,
                motion_group=animation.get("motion_group"),
                expression=animation.get("expression"),
                intensity=emotion_state.intensity
            )
        except Exception as e:
            logger.error(f"动画触发失败: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """获取情绪统计"""
        if not self._emotion_history:
            return {"total": 0}

        emotion_counts = {}
        for state in self._emotion_history:
            emotion_name = state.emotion.value
            emotion_counts[emotion_name] = emotion_counts.get(emotion_name, 0) + 1

        return {
            "total": len(self._emotion_history),
            "current": self._current_emotion.emotion.value,
            "distribution": emotion_counts
        }


# ==================== 工厂函数 ====================

def create_emotion_manager(
    llm_callback=None,
    animation_callback=None,
    custom_mapping: Dict[str, Dict] = None
) -> EmotionManager:
    """创建情绪管理器

    Args:
        llm_callback: LLM 回调函数
        animation_callback: 动画回调函数
        custom_mapping: 自定义情绪映射

    Returns:
        EmotionManager 实例
    """
    manager = EmotionManager(llm_callback, animation_callback)
    if custom_mapping:
        manager.mapper = EmotionMapper(custom_mapping)
    return manager
