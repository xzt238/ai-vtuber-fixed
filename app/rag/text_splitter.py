"""
文本分块器

提供智能文本分块功能，保持语义完整性。
"""

import re
import hashlib
from typing import List, Dict, Any

from . import TextChunk


class TextSplitter:
    """文本分块器"""
    
    def __init__(self, config: Dict[str, Any] = None) -> None:
        self.config = config or {}
        self.chunk_size = self.config.get("chunk_size", 500)
        self.chunk_overlap = self.config.get("chunk_overlap", 50)
        
        # 句子分隔符
        self.sentence_delimiters = [
            '。', '！', '？', '；',  # 中文标点
            '.', '!', '?', ';',      # 英文标点
            '\n\n',                   # 段落分隔
        ]
    
    def split(self, text: str, document_id: str = None) -> List[TextChunk]:
        """分块文本"""
        if not text:
            return []
        
        # 清理文本
        text = self._clean_text(text)
        
        # 按句子分块
        sentences = self._split_into_sentences(text)
        
        # 合并句子成块
        chunks = self._merge_sentences_into_chunks(sentences, document_id)
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        # 移除特殊字符
        text = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:，。！？；：]', '', text)
        return text.strip()
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """将文本分割成句子"""
        # 使用正则表达式分割句子
        pattern = r'([。！？；.!?\n])'
        parts = re.split(pattern, text)
        
        sentences = []
        current_sentence = ""
        
        for i, part in enumerate(parts):
            if re.match(pattern, part):
                # 这是分隔符，添加到当前句子
                current_sentence += part
                if current_sentence.strip():
                    sentences.append(current_sentence.strip())
                current_sentence = ""
            else:
                # 这是句子内容
                current_sentence += part
        
        # 处理最后一个句子
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        return sentences
    
    def _merge_sentences_into_chunks(self, sentences: List[str], document_id: str = None) -> List[TextChunk]:
        """将句子合并成块"""
        chunks = []
        current_chunk = ""
        current_start = 0
        chunk_index = 0
        
        for sentence in sentences:
            # 如果当前块加上新句子超过块大小，且当前块不为空
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                # 创建块
                chunk = self._create_chunk(
                    current_chunk,
                    document_id,
                    chunk_index,
                    current_start,
                    current_start + len(current_chunk)
                )
                chunks.append(chunk)
                
                # 计算重叠
                overlap_text = self._get_overlap_text(current_chunk)
                current_start += len(current_chunk) - len(overlap_text)
                current_chunk = overlap_text + sentence
                chunk_index += 1
            else:
                current_chunk += sentence
        
        # 处理最后一个块
        if current_chunk.strip():
            chunk = self._create_chunk(
                current_chunk,
                document_id,
                chunk_index,
                current_start,
                current_start + len(current_chunk)
            )
            chunks.append(chunk)
        
        return chunks
    
    def _get_overlap_text(self, text: str) -> str:
        """获取重叠文本"""
        if self.chunk_overlap <= 0:
            return ""
        
        # 从文本末尾获取重叠部分
        if len(text) <= self.chunk_overlap:
            return text
        
        # 尝试在句子边界处截断
        overlap_text = text[-self.chunk_size:]
        
        # 找到最近的句子边界
        for delimiter in self.sentence_delimiters:
            idx = overlap_text.find(delimiter)
            if idx != -1:
                return overlap_text[idx + len(delimiter):]
        
        return overlap_text
    
    def _create_chunk(self, content: str, document_id: str, index: int, start: int, end: int) -> TextChunk:
        """创建文本块"""
        # 生成块ID
        chunk_id = hashlib.md5(f"{document_id}:{index}:{start}".encode()).hexdigest()
        
        return TextChunk(
            id=chunk_id,
            document_id=document_id or "",
            content=content,
            index=index,
            start_char=start,
            end_char=end,
            metadata={
                "length": len(content),
                "index": index,
            }
        )
    
    def split_by_paragraph(self, text: str, document_id: str = None) -> List[TextChunk]:
        """按段落分块"""
        paragraphs = text.split('\n\n')
        chunks = []
        
        for i, paragraph in enumerate(paragraphs):
            if paragraph.strip():
                chunk = self._create_chunk(
                    paragraph.strip(),
                    document_id,
                    i,
                    0,
                    len(paragraph)
                )
                chunks.append(chunk)
        
        return chunks
    
    def split_by_fixed_size(self, text: str, document_id: str = None) -> List[TextChunk]:
        """按固定大小分块"""
        chunks = []
        start = 0
        index = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            
            # 尝试在句子边界处截断
            if end < len(text):
                # 找到最近的句子边界
                for delimiter in self.sentence_delimiters:
                    idx = text.rfind(delimiter, start, end)
                    if idx != -1:
                        end = idx + len(delimiter)
                        break
            
            chunk_text = text[start:end]
            if chunk_text.strip():
                chunk = self._create_chunk(
                    chunk_text,
                    document_id,
                    index,
                    start,
                    end
                )
                chunks.append(chunk)
            
            start = end - self.chunk_overlap
            index += 1
        
        return chunks