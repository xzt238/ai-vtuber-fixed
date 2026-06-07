"""
记忆提取模块

包含 FactExtractor（事实提取）和 AutoTagger（自动标签）。
"""

import time
import re
import logging
from typing import List

from memory.models import FactItem

logger = logging.getLogger(__name__)


class FactExtractor:
    """
    事实提取器 v1 — 规则优先 + LLM 降级
    
    从对话中提取独立事实:
    - 用户偏好: "我喜欢...", "我讨厌..."
    - 用户信息: "我叫...", "我在..."
    - 关键事实: 被标记为重要的知识
    """
    
    PREFERENCE_PATTERNS = [
        (r'我(喜欢|爱|偏好|最爱|更倾向)(.+?)(?:[，。！？,.]|$)', 'user_preference'),
        (r'我(讨厌|不喜欢|反感|最讨厌|受不了)(.+?)(?:[，。！？,.]|$)', 'user_preference'),
        (r'我(不要|不想|拒绝|别用)(.+?)(?:[，。！？,.]|$)', 'user_preference'),
        (r'我习惯(.+?)(?:[，。！？,.]|$)', 'user_preference'),
    ]
    
    INFO_PATTERNS = [
        (r'我(?:叫|名字是?)(.{1,10}?)(?:[，。！？,.]|$)', 'user_info'),
        (r'我(?:是|在)(.{1,20}?)(?:工作|上学|住|来自)', 'user_info'),
        (r'我(?:的?)(?:电话|邮箱|地址|微信|QQ)(?:是|:|：)?(.{1,30}?)(?:[，。！？,.]|$)', 'user_info'),
        (r'我(?:的)?生日(?:是|在)?(.{1,15}?)(?:[，。！？,.]|$)', 'user_info'),
    ]
    
    @classmethod
    def extract_facts(cls, role: str, content: str, importance: int) -> List[FactItem]:
        """从对话中提取事实(纯规则,快速)"""
        if role != "user":
            return []
        
        facts = []
        now = time.time()
        
        for pattern, source in cls.PREFERENCE_PATTERNS:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    fact_text = f"用户{match[0]}{match[1]}"
                else:
                    fact_text = f"用户{match}"
                if len(fact_text) > 4:
                    facts.append(FactItem(
                        content=fact_text,
                        source=source,
                        confidence=0.8,
                        timestamp=now,
                        tags=["偏好"],
                    ))
        
        for pattern, source in cls.INFO_PATTERNS:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    fact_text = match[0] if match[0] else str(match)
                else:
                    fact_text = match
                if len(fact_text) > 1:
                    facts.append(FactItem(
                        content=fact_text,
                        source=source,
                        confidence=0.9,
                        timestamp=now,
                        tags=["个人信息"],
                    ))
        
        if importance >= 4 and len(content) > 20:
            fact_text = content[:100]
            facts.append(FactItem(
                content=fact_text,
                source="key_fact",
                confidence=0.7,
                timestamp=now,
                tags=["重要事实"],
            ))
        
        return facts
    
    @classmethod
    def extract_with_llm(cls, content: str, llm_chat_func) -> List[FactItem]:
        """LLM 事实提取(降级方案)"""
        if not llm_chat_func:
            return []
        
        try:
            prompt = f"""从以下对话中提取独立事实。只返回事实列表,每行一条,格式: 事实内容

要求:
1. 只提取客观事实和用户偏好,不要提取对话本身
2. 每条事实独立完整,不依赖上下文
3. 如果没有可提取的事实,返回空

对话内容:
{content}

事实列表:"""
            
            result = llm_chat_func(message=prompt)
            if not result or not isinstance(result, dict):
                return []
            text = result.get("text", "").strip()
            
            if not text:
                return []
            
            facts = []
            now = time.time()
            for line in text.split("\n"):
                line = line.strip().lstrip("-•*0-9. ")
                if len(line) > 5:
                    source = "user_preference" if any(w in line for w in ["喜欢", "讨厌", "偏好", "习惯"]) else "key_fact"
                    facts.append(FactItem(
                        content=line,
                        source=source,
                        confidence=0.7,
                        timestamp=now,
                    ))
            return facts
        except Exception as e:
            logger.error(f"LLM事实提取失败: {e}")
            return []


class AutoTagger:
    """自动标签系统 — 基于关键词的领域分类"""
    
    TAG_KEYWORDS = {
        "编程": ["代码", "python", "javascript", "函数", "API", "bug", "调试", "编程", "开发", "部署", "git", "编译"],
        "AI/ML": ["模型", "训练", "推理", "神经网络", "深度学习", "机器学习", "AI", "LLM", "GPT", "embedding", "向量"],
        "声音/TTS": ["声音", "语音", "TTS", "音色", "克隆", "GPT-SoVITS", "推理", "参考音频", "训练模型"],
        "记忆系统": ["记忆", "遗忘", "摘要", "向量", "检索", "工作记忆", "情景记忆"],
        "情感": ["开心", "难过", "生气", "焦虑", "喜欢", "讨厌", "感动", "失望", "担心"],
        "日常": ["天气", "吃饭", "睡觉", "运动", "旅行", "电影", "音乐", "游戏"],
        "工作": ["项目", "任务", "会议", "deadline", "截止", "进度", "需求", "上线"],
        "学习": ["学习", "考试", "课程", "论文", "研究", "知识", "理解", "概念"],
        "个人": ["名字", "年龄", "生日", "电话", "地址", "家乡", "职业", "爱好"],
    }
    
    @classmethod
    def tag(cls, content: str) -> List[str]:
        """为内容自动打标签"""
        tags = []
        content_lower = content.lower()
        for tag, keywords in cls.TAG_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in content_lower:
                    tags.append(tag)
                    break
        return tags
