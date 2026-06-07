"""
生成器

提供检索增强生成功能。
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class Generator:
    """生成器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.llm_callback = None
        
        # 提示词模板
        self.prompt_template = self.config.get("prompt_template", 
            "基于以下上下文信息，回答用户的问题。\n\n"
            "上下文信息：\n{context}\n\n"
            "用户问题：{query}\n\n"
            "请提供准确、详细的回答："
        )
    
    def set_llm_callback(self, callback):
        """设置LLM回调函数"""
        self.llm_callback = callback
    
    def generate(self, query: str, context: List[str] = None) -> str:
        """生成回答"""
        try:
            if self.llm_callback is None:
                return self._generate_without_llm(query, context)
            
            # 准备上下文
            context_text = self._prepare_context(context)
            
            # 构建提示词
            prompt = self._build_prompt(query, context_text)
            
            # 调用LLM
            response = self.llm_callback(prompt)
            
            # 提取回答
            if isinstance(response, dict):
                return response.get("text", response.get("content", ""))
            elif isinstance(response, str):
                return response
            else:
                return str(response)
                
        except Exception as e:
            logger.info(f" 生成失败: {e}")
            return f"生成回答时出错: {e}"
    
    def _prepare_context(self, context: List[str] = None) -> str:
        """准备上下文"""
        if not context:
            return "无相关上下文信息。"
        
        # 合并上下文
        context_parts = []
        for i, ctx in enumerate(context, 1):
            context_parts.append(f"[{i}] {ctx}")
        
        return "\n\n".join(context_parts)
    
    def _build_prompt(self, query: str, context: str) -> str:
        """构建提示词"""
        return self.prompt_template.format(
            context=context,
            query=query
        )
    
    def _generate_without_llm(self, query: str, context: List[str] = None) -> str:
        """不使用LLM的简单生成"""
        if not context:
            return "抱歉，我没有找到相关信息来回答您的问题。"
        
        # 简单的回答生成
        answer_parts = ["基于找到的信息，我了解到："]
        
        for i, ctx in enumerate(context[:3], 1):  # 只使用前3个上下文
            answer_parts.append(f"{i}. {ctx}")
        
        answer_parts.append(f"\n关于您的问题「{query}」，以上是相关的信息。")
        
        return "\n".join(answer_parts)
    
    def generate_with_template(self, query: str, context: List[str], template: str) -> str:
        """使用自定义模板生成"""
        try:
            context_text = self._prepare_context(context)
            prompt = template.format(context=context_text, query=query)
            
            if self.llm_callback:
                response = self.llm_callback(prompt)
                if isinstance(response, dict):
                    return response.get("text", response.get("content", ""))
                return str(response)
            else:
                return self._generate_without_llm(query, context)
                
        except Exception as e:
            logger.info(f" 模板生成失败: {e}")
            return f"生成回答时出错: {e}"
    
    def summarize(self, text: str, max_length: int = 200) -> str:
        """文本摘要"""
        try:
            if self.llm_callback:
                prompt = f"请将以下文本总结为不超过{max_length}字的摘要：\n\n{text}"
                response = self.llm_callback(prompt)
                
                if isinstance(response, dict):
                    summary = response.get("text", response.get("content", ""))
                else:
                    summary = str(response)
                
                # 确保不超过最大长度
                if len(summary) > max_length:
                    summary = summary[:max_length] + "..."
                
                return summary
            else:
                # 简单的摘要生成
                sentences = text.split('。')
                if len(sentences) <= 3:
                    return text
                
                # 取前3句话作为摘要
                summary = '。'.join(sentences[:3]) + '。'
                if len(summary) > max_length:
                    summary = summary[:max_length] + "..."
                
                return summary
                
        except Exception as e:
            logger.info(f" 摘要生成失败: {e}")
            return text[:max_length] + "..." if len(text) > max_length else text
    
    def extract_keywords(self, text: str, top_k: int = 5) -> List[str]:
        """提取关键词"""
        try:
            if self.llm_callback:
                prompt = f"请从以下文本中提取{top_k}个关键词，用逗号分隔：\n\n{text}"
                response = self.llm_callback(prompt)
                
                if isinstance(response, dict):
                    keywords_text = response.get("text", response.get("content", ""))
                else:
                    keywords_text = str(response)
                
                # 解析关键词
                keywords = [kw.strip() for kw in keywords_text.split(',')]
                return keywords[:top_k]
            else:
                # 简单的关键词提取
                import re
                words = re.findall(r'[\w\u4e00-\u9fff]+', text)
                
                # 统计词频
                from collections import Counter
                word_counts = Counter(words)
                
                # 过滤停用词
                stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
                
                keywords = [word for word, count in word_counts.most_common(top_k * 2) 
                           if word not in stop_words and len(word) > 1]
                
                return keywords[:top_k]
                
        except Exception as e:
            logger.info(f" 关键词提取失败: {e}")
            return []