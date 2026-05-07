"""
Live2D 主动动画控制器

让 Live2D 角色从"会说话的贴纸"进化为"有灵魂的伙伴"。

功能:
- 基于情绪的主动动画触发（开心→挥手，伤心→低头，等）
- 随机 idle 动画（待机时偶尔歪头、眨眼、换姿势）
- TTS 口型同步（播放音频时驱动嘴巴开合）
- 对话内容 → 情绪 → 动画 的完整映射链
- 主动问候动画（启动时挥手打招呼）

设计理念:
AI 女友的核心体验是"陪伴感"。主动动画 = 生命感 = 陪伴感。
当角色在你说话时点头，在你夸她时害羞低头，在你离开时挥手告别——
这才是"女朋友"而不是"聊天机器人"。

作者: 咕咕嘎嘎
日期: 2026-05-06
"""

import random
import time
from typing import Optional, Dict, List, Tuple
from PySide6.QtCore import QTimer, Qt


class EmotionType:
    """情绪类型枚举"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    SHY = "shy"
    LOVE = "love"
    THINKING = "thinking"
    WAVE = "wave"        # 挥手
    NOD = "nod"          # 点头
    SHAKE = "shake"      # 摇头


# 情绪 → 动作映射表
# 不同模型可能拥有不同的动作组，这里提供多层 fallback
EMOTION_MOTION_MAP: Dict[str, List[Tuple[str, str]]] = {
    # emotion_type: [(motion_group, fallback_group), ...]
    EmotionType.HAPPY: [
        ("TapBody", "Idle"),       # 大多数模型有 TapBody
    ],
    EmotionType.SAD: [
        ("Idle",),                  # 没有专门的伤心动作，用 idle + 表情代替
    ],
    EmotionType.ANGRY: [
        ("TapBody", "Idle"),
    ],
    EmotionType.SURPRISED: [
        ("TapBody", "Idle"),
    ],
    EmotionType.SHY: [
        ("Idle",),
    ],
    EmotionType.LOVE: [
        ("TapBody", "Idle"),
    ],
    EmotionType.THINKING: [
        ("Idle",),
    ],
    EmotionType.WAVE: [
        ("TapBody", "Idle"),
    ],
    EmotionType.NOD: [
        ("Idle",),
    ],
    EmotionType.SHAKE: [
        ("Idle",),
    ],
}

# 情绪 → 表情映射（基于 Live2D 模型常见表情 ID）
EMOTION_EXPRESSION_MAP: Dict[str, List[str]] = {
    EmotionType.HAPPY: ["happy", "smile", "f02", "F02"],
    EmotionType.SAD: ["sad", "f03", "F03"],
    EmotionType.ANGRY: ["angry", "f04", "F04"],
    EmotionType.SURPRISED: ["surprised", "shine", "f04", "F04"],
    EmotionType.SHY: ["shy", "smile", "f03", "F03"],
    EmotionType.LOVE: ["happy", "love", "f02", "F02"],
    EmotionType.THINKING: ["neutral", "f01", "F01"],
    EmotionType.WAVE: ["happy", "smile", "f02", "F02"],
    EmotionType.NOD: ["neutral", "smile", "f01", "F01"],
    EmotionType.SHAKE: ["sad", "f03", "F03"],
}

# 关键词 → 情绪映射（增强版，比原来的更丰富）
EMOTION_KEYWORDS: Dict[str, List[str]] = {
    EmotionType.HAPPY: [
        '开心', '高兴', '快乐', '好开心', '哈哈', '嘻', '棒', '赞',
        '太好了', '太棒了', '好耶', '耶', '嘻嘻', '嘿嘿', '好嗨',
        '爱你', '喜欢', '么么哒', '可爱', '萌', '最棒',
    ],
    EmotionType.SAD: [
        '难过', '伤心', '哭', '悲伤', '遗憾', '可惜', '唉', '郁闷',
        '烦', '无聊', '寂寞', '孤独', '不想', '好累', '辛苦',
    ],
    EmotionType.ANGRY: [
        '生气', '愤怒', '哼', '气死', '可恶', '滚', '烦死了',
        '讨厌', '不想理', '不理你', '坏蛋',
    ],
    EmotionType.SURPRISED: [
        '震惊', '什么', '怎么', '为什么', '啥', '啥情况',
        '哇', '啊', '惊讶', '惊喜', '厉害', '太厉害', '真的吗',
        '真的假的', '天哪', '我的天', '哇塞', '哇哦',
    ],
    EmotionType.SHY: [
        '害羞', '脸红', '不好意思', '羞', '羞涩', '别看', '别说了',
        '讨厌啦', '哼哼',
    ],
    EmotionType.LOVE: [
        '爱你', '喜欢你', '亲爱的', '宝贝', '么么', '亲亲', '抱抱',
        '想你', '想念', '心上人', '最喜欢', '好喜欢',
    ],
    EmotionType.THINKING: [
        '嗯...', '让我想想', '想一下', '思考', '考虑', '怎么说呢',
        '怎么说', '嗯~', '唔',
    ],
}

# idle 动画候选组（按优先级尝试）
IDLE_MOTION_GROUPS = ["Idle", "TapBody"]


class AnimationController:
    """
    Live2D 主动动画控制器

    职责:
    1. 管理随机 idle 动画（待机时偶尔动一动）
    2. 根据情绪触发主动动画（表情 + 动作联动）
    3. 管理口型同步状态
    4. 协调动画优先级（避免 idle 动画打断正在播放的情绪动画）

    用法:
        controller = AnimationController(live2d_widget)
        controller.start()  # 启动 idle 动画循环
        controller.trigger_emotion("happy")  # 触发开心动画
        controller.set_mouth_open(0.8)  # 口型同步
    """

    def __init__(self, live2d_widget):
        """
        初始化动画控制器

        Args:
            live2d_widget: Live2DWidget 实例
        """
        self._widget = live2d_widget
        self._is_active = False
        self._current_emotion = EmotionType.NEUTRAL
        self._emotion_locked_until = 0  # 情绪锁定截止时间（防止 idle 打断情绪动画）
        self._last_idle_time = time.time()
        self._idle_interval_range = (5.0, 15.0)  # idle 动画间隔 5~15 秒
        self._next_idle_time = self._random_idle_interval()
        self._available_motions = []  # 模型支持的动作分组
        self._available_expressions = []  # 模型支持的表情

        # idle 动画定时器
        self._idle_timer = QTimer()
        self._idle_timer.timeout.connect(self._on_idle_tick)

        # 问候动画（启动后延迟 1 秒播放）
        self._greet_timer = QTimer()
        self._greet_timer.setSingleShot(True)
        self._greet_timer.timeout.connect(self._play_greeting)

        # 连接模型加载信号
        if hasattr(live2d_widget, 'motions_updated'):
            live2d_widget.motions_updated.connect(self._on_motions_updated)
        if hasattr(live2d_widget, 'expressions_updated'):
            live2d_widget.expressions_updated.connect(self._on_expressions_updated)

    def start(self):
        """启动动画控制器（idle 动画 + 问候动画）"""
        self._is_active = True
        self._last_idle_time = time.time()
        self._next_idle_time = self._random_idle_interval()
        # 每 2000ms 检查是否该播放 idle 动画（idle 动画 5-15 秒触发，无需 500ms 高频检查）
        self._idle_timer.start(2000)
        # 1 秒后播放问候动画
        self._greet_timer.start(1000)
        print("[AnimationController] 动画控制器已启动")

    def stop(self):
        """停止动画控制器"""
        self._is_active = False
        self._idle_timer.stop()
        self._greet_timer.stop()
        print("[AnimationController] 动画控制器已停止")

    def trigger_emotion(self, emotion: str, lock_duration: float = 3.0):
        """
        触发情绪动画

        Args:
            emotion: 情绪类型（EmotionType 枚举值）
            lock_duration: 情绪锁定时长（秒），期间 idle 动画不会打断
        """
        if not self._is_active:
            return

        self._current_emotion = emotion
        self._emotion_locked_until = time.time() + lock_duration

        # 1. 触发表情
        self._apply_expression(emotion)

        # 2. 触发动作
        self._apply_motion(emotion)

        print(f"[AnimationController] 触发情绪动画: {emotion}")

    def detect_emotion_from_text(self, text: str) -> str:
        """
        从文本中检测情绪

        Args:
            text: LLM 回复文本

        Returns:
            检测到的情绪类型
        """
        if not text:
            return EmotionType.NEUTRAL

        text_lower = text.lower()
        max_score = 0
        detected = EmotionType.NEUTRAL

        for emotion, keywords in EMOTION_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > max_score:
                max_score = score
                detected = emotion

        return detected if max_score >= 1 else EmotionType.NEUTRAL

    def trigger_emotion_from_text(self, text: str, lock_duration: float = 3.0):
        """
        从文本中检测情绪并触发对应动画（便捷方法）

        Args:
            text: LLM 回复文本
            lock_duration: 情绪锁定时长
        """
        emotion = self.detect_emotion_from_text(text)
        if emotion != EmotionType.NEUTRAL:
            self.trigger_emotion(emotion, lock_duration)

    def set_mouth_open(self, value: float):
        """
        设置口型开合度（TTS 口型同步）

        Args:
            value: 0.0~1.0
        """
        if self._widget and hasattr(self._widget, 'set_mouth_open'):
            self._widget.set_mouth_open(max(0.0, min(1.0, value)))

    def reset_emotion(self):
        """重置情绪为中性（恢复 idle 状态）"""
        self._current_emotion = EmotionType.NEUTRAL
        self._apply_expression(EmotionType.NEUTRAL)

    # ========== 内部方法 ==========

    def _on_idle_tick(self):
        """idle 动画定时检查"""
        if not self._is_active:
            return

        now = time.time()

        # 情绪锁定期间不播放 idle 动画
        if now < self._emotion_locked_until:
            return

        # 检查是否到了播放 idle 动画的时间
        if now - self._last_idle_time >= self._next_idle_time:
            self._play_idle_animation()
            self._last_idle_time = now
            self._next_idle_time = self._random_idle_interval()

    def _play_idle_animation(self):
        """播放一个随机 idle 动画"""
        if not self._widget or not hasattr(self._widget, 'model') or not self._widget.model:
            return

        # 选择一个可用的 idle 动作组
        group = self._find_available_motion_group(IDLE_MOTION_GROUPS)
        if group:
            try:
                self._widget.start_random_motion(group, 1)  # 低优先级，不打断正在播放的
            except Exception:
                pass

    def _play_greeting(self):
        """播放启动问候动画"""
        if not self._is_active:
            return

        # 尝试播放挥手动作
        self.trigger_emotion(EmotionType.WAVE, lock_duration=2.0)

    def _apply_expression(self, emotion: str):
        """
        应用情绪对应的表情

        Args:
            emotion: 情绪类型
        """
        if not self._widget or not hasattr(self._widget, 'set_expression'):
            return

        if not self._available_expressions:
            return

        # 查找可用的表情
        candidate_names = EMOTION_EXPRESSION_MAP.get(emotion, [])
        for exp_name in candidate_names:
            if exp_name in self._available_expressions:
                try:
                    self._widget.set_expression(exp_name)
                    return
                except Exception:
                    continue

    def _apply_motion(self, emotion: str):
        """
        应用情绪对应的动作

        Args:
            emotion: 情绪类型
        """
        if not self._widget or not hasattr(self._widget, 'model') or not self._widget.model:
            return

        motion_candidates = EMOTION_MOTION_MAP.get(emotion, [])
        if not motion_candidates:
            return

        group = self._find_available_motion_group(motion_candidates)
        if group:
            try:
                # 情绪动画用 NORMAL 优先级
                self._widget.start_random_motion(group, 3)
            except Exception:
                pass

    def _find_available_motion_group(self, candidates) -> Optional[str]:
        """
        从候选列表中找到模型实际支持的动作组

        Args:
            candidates: 候选动作组列表，如 [("TapBody", "Idle"), ("Idle",)]

        Returns:
            第一个可用的动作组名，或 None
        """
        for item in candidates:
            group = item[0] if isinstance(item, tuple) else item
            if not self._available_motions:
                # 如果不知道模型支持什么，直接尝试
                return group
            if group in self._available_motions:
                return group
        return None

    def _on_motions_updated(self, motion_groups: list):
        """模型动作分组列表更新"""
        self._available_motions = motion_groups
        print(f"[AnimationController] 可用动作分组: {motion_groups}")

    def _on_expressions_updated(self, expressions: list):
        """模型表情列表更新"""
        self._available_expressions = expressions
        print(f"[AnimationController] 可用表情: {expressions}")

    def _random_idle_interval(self) -> float:
        """生成随机 idle 动画间隔"""
        return random.uniform(*self._idle_interval_range)
