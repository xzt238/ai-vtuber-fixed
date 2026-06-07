"""
检索器

提供向量检索和关键词检索功能。
"""

import re
from typing import List, Dict, Any
from collections import Counter

from . import TextChunk, RetrievalResult
import logging

logger = logging.getLogger(__name__)


class Retriever:
    """检索器"""
    
    def __init__(self, config: Dict[str, Any] = None) -> None:
        """内部方法"""
        self.config = config or {}
        self.top_k = self.config.get("top_k", 5)
        self.similarity_threshold = self.config.get("similarity_threshold", 0.7)
        
        # 检索权重
        weights = self.config.get("retrieval_weights", {})
        self.vector_weight = weights.get("vector", 0.7)
        self.keyword_weight = weights.get("keyword", 0.3)
        
        # 向量存储引用（延迟初始化）
        self._vector_store = None
    
    @property
    def vector_store(self) -> None:
        """延迟加载向量存储"""
        if self._vector_store is None:
            from app.memory import VectorStore
            self._vector_store = VectorStore(self.config)
        return self._vector_store
    
    def retrieve(self, query: str, chunks: List[TextChunk] = None, top_k: int = None) -> List[RetrievalResult]:
        """检索相关块"""
        if top_k is None:
            top_k = self.top_k
        
        if chunks is None:
            # 从向量存储中检索
            return self._retrieve_from_vector_store(query, top_k)
        else:
            # 从提供的块中检索
            return self._retrieve_from_chunks(query, chunks, top_k)
    
    def _retrieve_from_vector_store(self, query: str, top_k: int) -> List[RetrievalResult]:
        """从向量存储中检索"""
        try:
            # 使用向量存储的搜索功能
            results = self.vector_store.search(query, top_k=top_k)
            
            # 转换为RetrievalResult
            retrieval_results = []
            for doc_id, score, text in results:
                # 创建TextChunk对象
                chunk = TextChunk(
                    id=doc_id,
                    document_id="",  # 需要从元数据中获取
                    content=text,
                    index=0,
                    start_char=0,
                    end_char=len(text),
                    metadata={"doc_id": doc_id}
                )
                
                result = RetrievalResult(
                    chunk=chunk,
                    score=score,
                    source="vector"
                )
                retrieval_results.append(result)
            
            return retrieval_results
            
        except Exception as e:
            logger.info(f" 向量检索失败: {e}")
            return []
    
    def _retrieve_from_chunks(self, query: str, chunks: List[TextChunk], top_k: int) -> List[RetrievalResult]:
        """从提供的块中检索"""
        results = []
        
        for chunk in chunks:
            # 计算相似度分数
            vector_score = self._calculate_vector_similarity(query, chunk.content)
            keyword_score = self._calculate_keyword_similarity(query, chunk.content)
            
            # 混合分数
            hybrid_score = (
                self.vector_weight * vector_score +
                self.keyword_weight * keyword_score
            )
            
            if hybrid_score >= self.similarity_threshold:
                result = RetrievalResult(
                    chunk=chunk,
                    score=hybrid_score,
                    source="hybrid"
                )
                results.append(result)
        
        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results[:top_k]
    
    def _calculate_vector_similarity(self, query: str, text: str) -> float:
        """计算向量相似度"""
        try:
            # 简单的余弦相似度计算（实际应用中应使用embedding模型）
            # 这里使用字符级别的相似度作为示例
            
            # 转换为字符集合
            query_chars = set(query)
            text_chars = set(text)
            
            # 计算Jaccard相似度
            intersection = len(query_chars.intersection(text_chars))
            union = len(query_chars.union(text_chars))
            
            if union == 0:
                return 0.0
            
            return intersection / union
            
        except Exception as e:
            logger.info(f" 向量相似度计算失败: {e}")
            return 0.0
    
    def _calculate_keyword_similarity(self, query: str, text: str) -> float:
        """计算关键词相似度"""
        try:
            # 提取关键词
            query_keywords = self._extract_keywords(query)
            text_keywords = self._extract_keywords(text)
            
            if not query_keywords or not text_keywords:
                return 0.0
            
            # 计算关键词匹配度
            query_counter = Counter(query_keywords)
            text_counter = Counter(text_keywords)
            
            # 计算交集
            intersection = sum((query_counter & text_counter).values())
            
            # 计算相似度
            total = sum(query_counter.values()) + sum(text_counter.values())
            
            if total == 0:
                return 0.0
            
            return (2.0 * intersection) / total
            
        except Exception as e:
            logger.info(f" 关键词相似度计算失败: {e}")
            return 0.0
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取（实际应用中应使用NLP库）
        # 移除标点符号
        text = re.sub(r'[^\w\s]', '', text)
        
        # 分词（简单按空格分割）
        words = text.split()
        
        # 过滤停用词
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        
        keywords = [word for word in words if word not in stop_words and len(word) > 1]
        
        return keywords
    
    def hybrid_search(self, query: str, chunks: List[TextChunk] = None, top_k: int = None) -> List[RetrievalResult]:
        """混合搜索"""
        if top_k is None:
            top_k = self.top_k
        
        # 向量搜索
        vector_results = self._retrieve_from_vector_store(query, top_k * 2)
        
        # 关键词搜索
        keyword_results = self._keyword_search(query, chunks, top_k * 2)
        
        # 合并结果
        merged_results = self._merge_results(vector_results, keyword_results)
        
        # 按分数排序
        merged_results.sort(key=lambda x: x.score, reverse=True)
        
        return merged_results[:top_k]
    
    def _keyword_search(self, query: str, chunks: List[TextChunk] = None, top_k: int = None) -> List[RetrievalResult]:
        """关键词搜索"""
        if chunks is None:
            return []
        
        if top_k is None:
            top_k = self.top_k
        
        results = []
        
        for chunk in chunks:
            score = self._calculate_keyword_similarity(query, chunk.content)
            
            if score > 0:
                result = RetrievalResult(
                    chunk=chunk,
                    score=score,
                    source="keyword"
                )
                results.append(result)
        
        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results[:top_k]
    
    def _merge_results(self, vector_results: List[RetrievalResult], keyword_results: List[RetrievalResult]) -> List[RetrievalResult]:
        """合并搜索结果"""
        # 使用字典去重
        merged = {}
        
        for result in vector_results:
            chunk_id = result.chunk.id
            if chunk_id not in merged:
                merged[chunk_id] = result
            else:
                # 保留分数更高的结果
                if result.score > merged[chunk_id].score:
                    merged[chunk_id] = result
        
        for result in keyword_results:
            chunk_id = result.chunk.id
            if chunk_id not in merged:
                merged[chunk_id] = result
            else:
                # 如果已经存在，增加分数
                existing = merged[chunk_id]
                if existing.source == "vector" and result.source == "keyword":
                    # 混合分数
                    new_score = (
                        self.vector_weight * existing.score +
                        self.keyword_weight * result.score
                    )
                    merged[chunk_id] = RetrievalResult(
                        chunk=existing.chunk,
                        score=new_score,
                        source="hybrid"
                    )
        
        return list(merged.values())