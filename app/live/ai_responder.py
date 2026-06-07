"""
AI回复生成器

提供基于弹幕内容的AI生成功能。
"""

from typing import Dict, Any, Optional

from . import Danmaku
import logging

logger = logging.getLogger(__name__)


class AIResponder:
    """AI回复生成器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.llm_callback = None
        
        # 回复模板
        self.response_templates = {
            "greeting": [
                "你好{username}！欢迎来到直播间！",
                "嗨{username}！很高兴见到你！",
                "欢迎{username}！",
            ],
            "question": [
                "关于「{content}」，我认为...",
                "这是一个很好的问题！{content}",
                "让我想想{content}...",
            ],
            "general": [
                "谢谢{username}的弹幕！",
                "收到{username}的消息！",
                "{username}说得对！",
            ],
            "farewell": [
                "再见{username}！",
                "拜拜{username}！",
                "下次见{username}！",
            ],
        }
        
        # 关键词匹配规则
        self.keyword_rules = {
            "greeting": ["你好", "嗨", "hi", "hello", "早上好", "下午好", "晚上好"],
            "question": ["？", "?", "什么", "怎么", "为什么", "如何", "请问"],
            "farewell": ["再见", "拜拜", "bye", "goodbye", "下次见"],
        }
    
    def set_llm_callback(self, callback):
        """设置LLM回调函数"""
        self.llm_callback = callback
    
    def generate_response(self, danmaku: Danmaku) -> Optional[str]:
        """生成AI回复"""
        try:
            # 分析弹幕内容
            content = danmaku.content
            username = danmaku.username
            
            # 检查是否需要回复
            if not self._should_respond(content):
                return None
            
            # 确定回复类型
            response_type = self._determine_response_type(content)
            
            # 生成回复
            response = self._generate_response_by_type(response_type, username, content)
            
            return response
            
        except Exception as e:
            logger.info(f" AI回复生成失败: {e}")
            return None
    
    def _should_respond(self, content: str) -> bool:
        """判断是否需要回复"""
        # 过滤太短的内容
        if len(content) < 2:
            return False
        
        # 过滤纯表情
        if all(ord(c) > 127 for c in content):
            return False
        
        # 过滤纯数字
        if content.isdigit():
            return False
        
        return True
    
    def _determine_response_type(self, content: str) -> str:
        """确定回复类型"""
        content_lower = content.lower()
        
        # 检查关键词匹配
        for response_type, keywords in self.keyword_rules.items():
            for keyword in keywords:
                if keyword in content_lower:
                    return response_type
        
        # 默认为一般回复
        return "general"
    
    def _generate_response_by_type(self, response_type: str, username: str, content: str) -> str:
        """根据类型生成回复"""
        try:
            # 获取模板
            templates = self.response_templates.get(response_type, self.response_templates["general"])
            
            # 选择模板（简单轮询）
            import random
            template = random.choice(templates)
            
            # 填充模板
            response = template.format(
                username=username,
                content=content,
            )
            
            return response
            
        except Exception as e:
            logger.info(f" 回复生成失败: {e}")
            return f"谢谢{username}的弹幕！"
    
    def generate_response_with_llm(self, danmaku: Danmaku) -> Optional[str]:
        """使用LLM生成回复"""
        try:
            if self.llm_callback is None:
                return self.generate_response(danmaku)
            
            # 构建提示词
            prompt = self._build_prompt(danmaku)
            
            # 调用LLM
            response = self.llm_callback(prompt)
            
            # 提取回复
            if isinstance(response, dict):
                return response.get("text", response.get("content", ""))
            elif isinstance(response, str):
                return response
            else:
                return str(response)
                
        except Exception as e:
            logger.info(f" LLM回复生成失败: {e}")
            return self.generate_response(danmaku)
    
    def _build_prompt(self, danmaku: Danmaku) -> str:
        """构建提示词"""
        prompt = f"""
你是一个直播间的AI助手。用户{danmaku.username}发送了一条弹幕：

弹幕内容：{danmaku.content}

请生成一个友好、自然的回复。要求：
1. 回复要简洁明了
2. 语气要友好亲切
3. 如果是问题，要给出有帮助的回答
4. 如果是打招呼，要热情回应
5. 避免重复用户的话

请直接给出回复内容：
"""
        return prompt
    
    def analyze_sentiment(self, content: str) -> Dict[str, Any]:
        """分析情感"""
        try:
            # 简单的情感分析
            positive_words = ["好", "棒", "赞", "喜欢", "爱", "开心", "高兴", "谢谢"]
            negative_words = ["差", "烂", "讨厌", "恨", "难过", "生气", "愤怒"]
            
            content_lower = content.lower()
            
            positive_count = sum(1 for word in positive_words if word in content_lower)
            negative_count = sum(1 for word in negative_words if word in content_lower)
            
            if positive_count > negative_count:
                sentiment = "positive"
                score = positive_count / (positive_count + negative_count + 1)
            elif negative_count > positive_count:
                sentiment = "negative"
                score = negative_count / (positive_count + negative_count + 1)
            else:
                sentiment = "neutral"
                score = 0.5
            
            return {
                "sentiment": sentiment,
                "score": score,
                "positive_count": positive_count,
                "negative_count": negative_count,
            }
            
        except Exception as e:
            logger.info(f" 情感分析失败: {e}")
            return {
                "sentiment": "neutral",
                "score": 0.5,
                "positive_count": 0,
                "negative_count": 0,
            }
    
    def extract_keywords(self, content: str) -> list:
        """提取关键词"""
        try:
            import re
            
            # 移除标点符号
            content_clean = re.sub(r'[^\w\s]', '', content)
            
            # 分词
            words = content_clean.split()
            
            # 过滤停用词
            stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
            
            keywords = [word for word in words if word not in stop_words and len(word) > 1]
            
            return keywords
            
        except Exception as e:
            logger.info(f" 关键词提取失败: {e}")
            return []