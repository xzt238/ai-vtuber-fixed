"""
记忆评分模块

包含 RetentionScorer（遗忘机制）和 ImportanceScorer（重要性评分）。
"""

import math
import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class RetentionScorer:
    """
    智能遗忘机制 v2
    保留分数 = 重要性 × 时效衰减 × 访问频率 × 关联度
    
    v3.0 改进:
    - 降低衰减速度 (lambda 0.01→0.005, 记忆存续更久)
    - 新记忆保护期 (12小时内不参与遗忘扫描)
    - 重要性时间衰减保护 (importance>=3 的记忆衰减减半)
    """
    
    DECAY_LAMBDA = 0.005
    RETENTION_THRESHOLD = 0.15
    GRACE_PERIOD_HOURS = 12.0
    COOCCUR_WINDOW = 5
    
    @classmethod
    def compute_recency_decay(cls, hours_old: float) -> float:
        """计算时效衰减系数 e^(-lambda * hours)"""
        return math.exp(-cls.DECAY_LAMBDA * hours_old)
    
    @classmethod
    def compute_retention_score(
        cls,
        importance: float,
        hours_old: float,
        access_count: int = 1,
        connectivity: int = 0
    ) -> float:
        """计算保留分数 0.0 ~ 1.0"""
        importance_norm = importance / 5.0
        if importance >= 3:
            recency = math.exp(-cls.DECAY_LAMBDA * 0.5 * hours_old)
        else:
            recency = cls.compute_recency_decay(hours_old)
        access_boost = 1.0 + 0.2 * math.log1p(access_count)
        connectivity_boost = 1.0 + 0.1 * connectivity
        score = importance_norm * recency * access_boost * connectivity_boost
        return min(score, 1.0)
    
    @classmethod
    def should_forget(cls, retention_score: float) -> bool:
        """判断是否应该遗忘"""
        return retention_score < cls.RETENTION_THRESHOLD
    
    @classmethod
    def is_in_grace_period(cls, hours_old: float) -> bool:
        """是否在新记忆保护期内"""
        return hours_old < cls.GRACE_PERIOD_HOURS
    
    @classmethod
    def get_decay_stats(cls, hours_old: float) -> Dict[str, float]:
        """获取衰减统计(用于调试)"""
        return {
            "hours_old": hours_old,
            "recency_decay": cls.compute_recency_decay(hours_old),
            "score_at_importance_5": cls.compute_retention_score(5, hours_old),
            "score_at_importance_3": cls.compute_retention_score(3, hours_old),
            "score_at_importance_1": cls.compute_retention_score(1, hours_old),
            "score_at_importance_0": cls.compute_retention_score(0, hours_old),
        }


class ImportanceScorer:
    """
    重要性评分器 v2 — 多维梯度评分
    
    评分维度:
    1. 内容长度: 短闲聊→0, 中等→1, 长→2
    2. 问题检测: 疑问句+1
    3. 关键词匹配: 根据类别梯度加分
    4. 个人信息: 名字/偏好/身份 → 3-5
    5. 情感强度: 感叹/表情 → +1
    6. 知识深度: 专业术语/概念 → +2
    7. 明确记忆指令: "记住" → 5
    """
    
    INFO_WORDS = [
        "因为", "所以", "原因", "结果", "方法", "方式",
        "认为", "觉得", "想法", "观点", "看法",
        "工作", "学习", "项目", "计划", "目标",
        "问题", "解决", "方案", "建议",
    ]
    
    PREFERENCE_WORDS = [
        "喜欢", "讨厌", "偏好", "习惯", "不想", "不愿意",
        "最爱", "最讨厌", "受不了", "受不了",
        "喜欢用", "习惯了", "更倾向于", "更偏爱",
        "不要", "拒绝", "禁止", "别用", "避免",
    ]
    
    IDENTITY_WORDS = [
        "名字", "叫", "我是", "电话", "地址", "账号",
        "邮箱", "email", "生日", "年龄", "职业",
        "住", "来自", "家乡", "学校", "公司",
    ]
    
    MEMORY_COMMAND_WORDS = [
        "记住", "记住这个", "不要忘记", "下次记住",
        "记住我", "别忘了", "一定要记住", "帮我记",
        "remember", "keep in mind", "don't forget",
    ]
    
    IGNORE_WORDS = [
        "你好", "hi", "hello", "在吗", "嗯", "哦", "好", "啊",
        "哈", "呵", "嗯嗯", "好的", "ok", "OK", "嗯呢",
    ]
    
    EMOTION_MARKERS = ["！", "！","？", "？", "...", "……", "😂", "😭", "🤔", "👍", "❤"]
    
    KNOWLEDGE_PATTERNS = [
        r'(?:矩阵|向量|维度|映射|函数|算法|模型|架构|协议|接口|模块|组件)',
        r'(?:系统|框架|原理|机制|逻辑|策略|优化|参数|配置|部署)',
        r'(?:分析|设计|实现|集成|测试|验证|评估|监控)',
        r'(?:数据|信息|知识|理论|概念|定义|分类|结构)',
    ]
    
    @classmethod
    def score(cls, role: str, content: str) -> int:
        """多维梯度评分 0-5"""
        content_lower = content.lower()
        s = 0
        
        content_len = len(content)
        if content_len < 5:
            for word in cls.IGNORE_WORDS:
                if word in content_lower:
                    return 0
            s = 0
        elif content_len < 20:
            s = 0
        elif content_len < 50:
            s = 1
        elif content_len < 100:
            s = 1
        else:
            s = 2
        
        if '？' in content or '?' in content or content.endswith('吗') or content.endswith('呢'):
            s += 1
        
        for word in cls.INFO_WORDS:
            if word in content_lower:
                s = max(s, 2)
                break
        
        for word in cls.PREFERENCE_WORDS:
            if word in content_lower:
                s = max(s, 3)
                break
        
        for word in cls.IDENTITY_WORDS:
            if word in content_lower:
                s = max(s, 4)
                break
        
        for word in cls.MEMORY_COMMAND_WORDS:
            if word in content_lower:
                s = 5
                break
        
        emotion_count = sum(1 for m in cls.EMOTION_MARKERS if m in content)
        if emotion_count >= 2:
            s += 1
        
        for pattern in cls.KNOWLEDGE_PATTERNS:
            if re.search(pattern, content):
                s += 1
                break
        
        if role == "user" and s >= 2:
            s = min(s + 1, 5)
        
        return min(s, 5)
    
    @classmethod
    def is_important(cls, score: int) -> bool:
        """判断是否重要(>=3分视为重要)"""
        return score >= 3
    
    @classmethod
    def is_critical(cls, score: int) -> bool:
        """判断是否关键记忆(>=4分)"""
        return score >= 4
