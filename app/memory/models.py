"""
记忆系统数据结构

包含 MemoryItem 和 FactItem 两个核心数据类。
"""

import time
import logging
from typing import List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MemoryItem:
    """记忆条目(增强版:支持遗忘机制 + 事实提取)"""
    role: str  # user/assistant/system
    content: str
    timestamp: float
    importance: int = 0  # 0-5, 5最重要
    tags: List[str] = field(default_factory=list)
    
    # 遗忘机制字段
    access_count: int = 1      # 被检索命中的次数
    connectivity: int = 0      # 与其他记忆的共现次数(关联度)
    is_forgotten: bool = False  # 软删除标记
    is_summary: bool = False    # 是否为摘要压缩后的记忆
    
    # v3.0 新增字段
    facts: List[str] = field(default_factory=list)  # 从此条提取的事实
    summary_text: str = ""  # LLM 生成的摘要文本
    
    def __post_init__(self) -> None:
        """数据类初始化后处理(确保字段不为 None)"""
        if self.tags is None:
            self.tags = []
        if self.facts is None:
            self.facts = []
    
    def get_retention_score(self) -> float:
        """计算当前保留分数"""
        from memory.scoring import RetentionScorer
        hours_old = (time.time() - self.timestamp) / 3600
        return RetentionScorer.compute_retention_score(
            importance=self.importance,
            hours_old=hours_old,
            access_count=self.access_count,
            connectivity=self.connectivity
        )
    
    def should_forget(self) -> bool:
        """判断是否应该遗忘"""
        from memory.scoring import RetentionScorer
        if self.is_forgotten:
            return True
        return RetentionScorer.should_forget(self.get_retention_score())
    
    def touch(self) -> None:
        """记忆被访问时调用,增加访问计数"""
        self.access_count += 1
    
    def link(self, other_mem_id: str) -> None:
        """与其他记忆建立关联,增加关联计数"""
        self.connectivity += 1


@dataclass
class FactItem:
    """独立事实条目(从对话中提取的用户偏好/个人信息/关键事实)"""
    content: str       # 事实内容
    source: str        # 来源(user_preference / user_info / key_fact)
    confidence: float  # 置信度 0-1
    timestamp: float   # 提取时间
    access_count: int = 1
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        """初始化后处理"""
        if self.tags is None:
            self.tags = []
