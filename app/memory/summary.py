"""
记忆摘要模块

包含 SummaryGenerator（摘要生成器）。
"""

import logging
from typing import Optional, List

from memory.models import MemoryItem

logger = logging.getLogger(__name__)


class SummaryGenerator:
    """
    摘要生成器 v2 — LLM 语义摘要 + 规则降级
    
    v3.0: 不再硬截断前80字, 而是真正理解对话内容生成摘要
    """
    
    @classmethod
    def generate_summary(cls, batch: List[MemoryItem], llm_chat_func=None) -> str:
        """
        为一批记忆生成摘要
        
        优先使用 LLM 生成语义摘要, 降级到规则摘要
        """
        if not batch:
            return ""
        
        conversation = "\n".join([
            f"[{item.role}](imp={item.importance}): {item.content}"
            for item in batch
        ])
        
        if llm_chat_func:
            try:
                summary = cls._llm_summarize(conversation, llm_chat_func)
                if summary:
                    return summary
            except Exception as e:
                logger.warning(f"LLM摘要失败,降级到规则摘要: {e}")
        
        return cls._rule_summarize(batch)
    
    @classmethod
    def _llm_summarize(cls, conversation: str, llm_chat_func) -> Optional[str]:
        """LLM 语义摘要"""
        prompt = f"""请将以下对话压缩为一段简洁的摘要。要求:
1. 保留所有重要信息(用户偏好、个人信息、关键决策)
2. 丢弃闲聊和问候
3. 用第三人称客观描述
4. 100字以内

对话内容:
{conversation[:2000]}

摘要:"""
        
        result = llm_chat_func(message=prompt)
        if not result or not isinstance(result, dict):
            return None
        text = result.get("text", "").strip()
        if text and len(text) > 5:
            return text
        return None
    
    @classmethod
    def _rule_summarize(cls, batch: List[MemoryItem]) -> str:
        """规则摘要(降级方案) — v3.0改进: 按重要性分层处理"""
        important_parts = []
        normal_parts = []
        
        for item in batch:
            if item.importance >= 3:
                important_parts.append(f"[{item.role}]: {item.content[:150]}")
            elif item.importance >= 1:
                normal_parts.append(f"[{item.role}]: {item.content[:80]}")
        
        if important_parts:
            return "[重要对话] " + " | ".join(important_parts)
        elif normal_parts:
            return "[对话摘要] " + " | ".join(normal_parts[:5])
        else:
            return "[闲聊记录] (已压缩)"
