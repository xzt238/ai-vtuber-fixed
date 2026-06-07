"""
RAG知识库模块
支持文档导入、智能分块、向量存储、检索增强生成
"""

import os
import json
import asyncio
import hashlib
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime

class DocumentType(Enum):
    """文档类型"""
    TEXT = "text"
    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"

class ChunkStrategy(Enum):
    """分块策略"""
    FIXED_SIZE = "fixed_size"  # 固定大小
    SENTENCE = "sentence"  # 按句子
    PARAGRAPH = "paragraph"  # 按段落
    SEMANTIC = "semantic"  # 语义分块

@dataclass
class Document:
    """文档"""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    doc_type: DocumentType = DocumentType.TEXT
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class Chunk:
    """文档块"""
    id: str
    document_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    start_pos: int = 0
    end_pos: int = 0

@dataclass
class SearchResult:
    """搜索结果"""
    chunk: Chunk
    score: float
    highlights: List[str] = field(default_factory=list)

@dataclass
class RAGConfig:
    """RAG配置"""
    storage_dir: str = "./memory/knowledge_base"
    chunk_size: int = 500
    chunk_overlap: int = 50
    chunk_strategy: ChunkStrategy = ChunkStrategy.FIXED_SIZE
    top_k: int = 5
    similarity_threshold: float = 0.7
    retrieval_weights: Dict[str, float] = field(
        default_factory=lambda: {"vector": 0.7, "keyword": 0.3}
    )

class DocumentProcessor:
    """文档处理器"""
    
    def __init__(self, config: RAGConfig):
        self.config = config
    
    def process_document(self, content: str, doc_type: DocumentType, 
                        metadata: Dict[str, Any] = None) -> Document:
        """处理文档"""
        doc_id = hashlib.md5(content.encode()).hexdigest()
        
        # 清洗内容
        cleaned_content = self._clean_content(content)
        
        return Document(
            id=doc_id,
            content=cleaned_content,
            metadata=metadata or {},
            doc_type=doc_type
        )
    
    def _clean_content(self, content: str) -> str:
        """清洗内容"""
        # 移除多余空白
        content = content.strip()
        # 规范化换行符
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        # 移除多余空行
        lines = content.split("\n")
        cleaned_lines = []
        prev_empty = False
        for line in lines:
            if line.strip():
                cleaned_lines.append(line)
                prev_empty = False
            elif not prev_empty:
                cleaned_lines.append("")
                prev_empty = True
        return "\n".join(cleaned_lines)

class ChunkingEngine:
    """分块引擎"""
    
    def __init__(self, config: RAGConfig):
        self.config = config
    
    def chunk_document(self, document: Document) -> List[Chunk]:
        """分块文档"""
        strategy = self.config.chunk_strategy
        
        if strategy == ChunkStrategy.FIXED_SIZE:
            return self._chunk_fixed_size(document)
        elif strategy == ChunkStrategy.SENTENCE:
            return self._chunk_by_sentence(document)
        elif strategy == ChunkStrategy.PARAGRAPH:
            return self._chunk_by_paragraph(document)
        elif strategy == ChunkStrategy.SEMANTIC:
            return self._chunk_semantic(document)
        else:
            return self._chunk_fixed_size(document)
    
    def _chunk_fixed_size(self, document: Document) -> List[Chunk]:
        """固定大小分块"""
        chunks = []
        content = document.content
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        
        start = 0
        chunk_index = 0
        
        while start < len(content):
            end = min(start + chunk_size, len(content))
            
            # 尝试在句子边界分割
            if end < len(content):
                # 查找最近的句子结束符
                for sep in ["。", "！", "？", ".", "!", "?", "\n"]:
                    last_sep = content.rfind(sep, start, end)
                    if last_sep > start:
                        end = last_sep + 1
                        break
            
            chunk_content = content[start:end].strip()
            if chunk_content:
                chunk_id = f"{document.id}_chunk_{chunk_index}"
                chunks.append(Chunk(
                    id=chunk_id,
                    document_id=document.id,
                    content=chunk_content,
                    metadata={
                        **document.metadata,
                        "chunk_index": chunk_index,
                        "start_pos": start,
                        "end_pos": end
                    },
                    start_pos=start,
                    end_pos=end
                ))
                chunk_index += 1
            
            # 移动到下一个位置（考虑重叠）
            start = end - overlap if overlap > 0 else end
        
        return chunks
    
    def _chunk_by_sentence(self, document: Document) -> List[Chunk]:
        """按句子分块"""
        chunks = []
        content = document.content
        
        # 分割句子
        sentences = []
        current = ""
        for char in content:
            current += char
            if char in "。！？.!?\n":
                if current.strip():
                    sentences.append(current.strip())
                current = ""
        if current.strip():
            sentences.append(current.strip())
        
        # 组合句子到块
        current_chunk = ""
        chunk_index = 0
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.config.chunk_size:
                if current_chunk:
                    chunk_id = f"{document.id}_chunk_{chunk_index}"
                    chunks.append(Chunk(
                        id=chunk_id,
                        document_id=document.id,
                        content=current_chunk,
                        metadata={**document.metadata, "chunk_index": chunk_index},
                    ))
                    chunk_index += 1
                current_chunk = sentence
            else:
                current_chunk += sentence
        
        if current_chunk:
            chunk_id = f"{document.id}_chunk_{chunk_index}"
            chunks.append(Chunk(
                id=chunk_id,
                document_id=document.id,
                content=current_chunk,
                metadata={**document.metadata, "chunk_index": chunk_index},
            ))
        
        return chunks
    
    def _chunk_by_paragraph(self, document: Document) -> List[Chunk]:
        """按段落分块"""
        chunks = []
        content = document.content
        
        # 分割段落
        paragraphs = content.split("\n\n")
        
        chunk_index = 0
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current_chunk) + len(para) > self.config.chunk_size:
                if current_chunk:
                    chunk_id = f"{document.id}_chunk_{chunk_index}"
                    chunks.append(Chunk(
                        id=chunk_id,
                        document_id=document.id,
                        content=current_chunk,
                        metadata={**document.metadata, "chunk_index": chunk_index},
                    ))
                    chunk_index += 1
                current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
        
        if current_chunk:
            chunk_id = f"{document.id}_chunk_{chunk_index}"
            chunks.append(Chunk(
                id=chunk_id,
                document_id=document.id,
                content=current_chunk,
                metadata={**document.metadata, "chunk_index": chunk_index},
            ))
        
        return chunks
    
    def _chunk_semantic(self, document: Document) -> List[Chunk]:
        """语义分块（简化版本，实际应该使用NLP模型）"""
        # 这里使用简单的语义分块策略
        # 实际实现应该使用句子嵌入模型进行语义相似度计算
        return self._chunk_by_sentence(document)

class VectorStore:
    """向量存储"""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.storage_dir = Path(config.storage_dir)
        self.vectors_file = self.storage_dir / "vectors.json"
        self.chunks_file = self.storage_dir / "chunks.json"
        
        # 内存中的向量和块
        self.vectors: Dict[str, List[float]] = {}
        self.chunks: Dict[str, Chunk] = {}
        
        # 加载已有的向量和块
        self._load_from_disk()
    
    def _load_from_disk(self):
        """从磁盘加载"""
        try:
            if self.vectors_file.exists():
                with open(self.vectors_file, "r", encoding="utf-8") as f:
                    self.vectors = json.load(f)
            
            if self.chunks_file.exists():
                with open(self.chunks_file, "r", encoding="utf-8") as f:
                    chunks_data = json.load(f)
                    for chunk_id, chunk_dict in chunks_data.items():
                        self.chunks[chunk_id] = Chunk(**chunk_dict)
            
            print(f"[RAG] 加载了 {len(self.chunks)} 个文档块")
        except Exception as e:
            print(f"[RAG] 加载失败: {e}")
    
    def _save_to_disk(self):
        """保存到磁盘"""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self.vectors_file, "w", encoding="utf-8") as f:
                json.dump(self.vectors, f)
            
            chunks_data = {}
            for chunk_id, chunk in self.chunks.items():
                chunks_data[chunk_id] = {
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "start_pos": chunk.start_pos,
                    "end_pos": chunk.end_pos
                }
            
            with open(self.chunks_file, "w", encoding="utf-8") as f:
                json.dump(chunks_data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            print(f"[RAG] 保存失败: {e}")
    
    async def add_chunk(self, chunk: Chunk, embedding: List[float] = None):
        """添加块"""
        self.chunks[chunk.id] = chunk
        if embedding:
            self.vectors[chunk.id] = embedding
            chunk.embedding = embedding
        self._save_to_disk()
    
    async def search(self, query_embedding: List[float], top_k: int = None) -> List[SearchResult]:
        """搜索相似块"""
        top_k = top_k or self.config.top_k
        
        if not query_embedding or not self.vectors:
            return []
        
        # 计算相似度
        similarities = []
        for chunk_id, vector in self.vectors.items():
            similarity = self._cosine_similarity(query_embedding, vector)
            if similarity >= self.config.similarity_threshold:
                similarities.append((chunk_id, similarity))
        
        # 排序并返回top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for chunk_id, score in similarities[:top_k]:
            if chunk_id in self.chunks:
                results.append(SearchResult(
                    chunk=self.chunks[chunk_id],
                    score=score
                ))
        
        return results
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    async def delete_document(self, document_id: str):
        """删除文档的所有块"""
        chunk_ids_to_delete = [
            chunk_id for chunk_id, chunk in self.chunks.items()
            if chunk.document_id == document_id
        ]
        
        for chunk_id in chunk_ids_to_delete:
            del self.chunks[chunk_id]
            if chunk_id in self.vectors:
                del self.vectors[chunk_id]
        
        self._save_to_disk()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_chunks": len(self.chunks),
            "total_vectors": len(self.vectors),
            "documents": len(set(c.document_id for c in self.chunks.values()))
        }

class RAGSystem:
    """RAG系统"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config_data = config or {}
        
        # 创建配置
        self.config = RAGConfig(
            storage_dir=self.config_data.get("storage_dir", "./memory/knowledge_base"),
            chunk_size=self.config_data.get("chunk_size", 500),
            chunk_overlap=self.config_data.get("chunk_overlap", 50),
            top_k=self.config_data.get("top_k", 5),
            similarity_threshold=self.config_data.get("similarity_threshold", 0.7)
        )
        
        # 初始化组件
        self.document_processor = DocumentProcessor(self.config)
        self.chunking_engine = ChunkingEngine(self.config)
        self.vector_store = VectorStore(self.config)
        
        # 嵌入模型（延迟加载）
        self.embedding_model = None
        
        print(f"[RAG] 初始化完成: storage={self.config.storage_dir}")
    
    async def load_embedding_model(self, model_path: str = None):
        """加载嵌入模型"""
        try:
            # 这里应该加载真实的嵌入模型
            # 例如：sentence-transformers, BGE, etc.
            print(f"[RAG] 加载嵌入模型: {model_path or 'default'}")
            
            # 模拟模型加载
            self.embedding_model = {
                "type": "sentence-transformers",
                "model": model_path or "bge-base-zh-v1.5"
            }
            
            print("[RAG] 嵌入模型加载成功")
            return True
            
        except Exception as e:
            print(f"[RAG] 嵌入模型加载失败: {e}")
            return False
    
    async def add_document(self, content: str, doc_type: DocumentType = DocumentType.TEXT,
                          metadata: Dict[str, Any] = None) -> bool:
        """添加文档"""
        try:
            # 处理文档
            document = self.document_processor.process_document(content, doc_type, metadata)
            
            # 分块
            chunks = self.chunking_engine.chunk_document(document)
            
            # 为每个块生成嵌入
            for chunk in chunks:
                embedding = await self._generate_embedding(chunk.content)
                await self.vector_store.add_chunk(chunk, embedding)
            
            print(f"[RAG] 文档添加成功: {document.id}, {len(chunks)} 个块")
            return True
            
        except Exception as e:
            print(f"[RAG] 文档添加失败: {e}")
            return False
    
    async def add_document_from_file(self, file_path: str, 
                                    doc_type: DocumentType = None) -> bool:
        """从文件添加文档"""
        try:
            # 自动检测文档类型
            if doc_type is None:
                ext = Path(file_path).suffix.lower()
                type_map = {
                    ".txt": DocumentType.TEXT,
                    ".pdf": DocumentType.PDF,
                    ".docx": DocumentType.DOCX,
                    ".md": DocumentType.MARKDOWN,
                    ".html": DocumentType.HTML,
                    ".json": DocumentType.JSON,
                }
                doc_type = type_map.get(ext, DocumentType.TEXT)
            
            # 读取文件内容
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 添加文档
            metadata = {"source": file_path, "filename": Path(file_path).name}
            return await self.add_document(content, doc_type, metadata)
            
        except Exception as e:
            print(f"[RAG] 文件添加失败: {e}")
            return False
    
    async def search(self, query: str, top_k: int = None) -> List[SearchResult]:
        """搜索"""
        try:
            # 生成查询嵌入
            query_embedding = await self._generate_embedding(query)
            
            # 搜索相似块
            results = await self.vector_store.search(query_embedding, top_k)
            
            print(f"[RAG] 搜索完成: query='{query}', results={len(results)}")
            return results
            
        except Exception as e:
            print(f"[RAG] 搜索失败: {e}")
            return []
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """生成嵌入向量"""
        if not self.embedding_model:
            # 如果没有嵌入模型，使用简单的哈希作为占位符
            import hashlib
            hash_obj = hashlib.md5(text.encode())
            # 生成一个简单的向量（实际应该使用模型）
            return [float(b) / 255.0 for b in hash_obj.digest()] * 8  # 128维
        
        # 这里应该调用真实的嵌入模型
        # 示例：return self.embedding_model.encode(text)
        
        # 模拟嵌入生成
        import hashlib
        hash_obj = hashlib.md5(text.encode())
        return [float(b) / 255.0 for b in hash_obj.digest()] * 8
    
    async def generate(self, query: str, context: str = None) -> str:
        """检索增强生成"""
        try:
            # 搜索相关文档
            search_results = await self.search(query)
            
            # 构建上下文
            if not context:
                context_parts = []
                for result in search_results:
                    context_parts.append(result.chunk.content)
                context = "\n\n".join(context_parts)
            
            # 这里应该调用LLM生成回复
            # 示例：return await llm.generate(query, context)
            
            # 模拟生成
            response = f"基于检索到的 {len(search_results)} 个相关文档块，回答：{query}"
            
            return response
            
        except Exception as e:
            print(f"[RAG] 生成失败: {e}")
            return f"生成失败: {e}"
    
    async def delete_document(self, document_id: str):
        """删除文档"""
        await self.vector_store.delete_document(document_id)
        print(f"[RAG] 文档已删除: {document_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.vector_store.get_stats()
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "config": {
                "storage_dir": self.config.storage_dir,
                "chunk_size": self.config.chunk_size,
                "top_k": self.config.top_k,
                "similarity_threshold": self.config.similarity_threshold
            },
            "stats": self.get_stats(),
            "embedding_model_loaded": self.embedding_model is not None
        }

# 全局RAG系统实例
_rag_system: Optional[RAGSystem] = None

def get_rag_system(config: Dict[str, Any] = None) -> RAGSystem:
    """获取RAG系统实例"""
    global _rag_system
    if _rag_system is None:
        _rag_system = RAGSystem(config)
    return _rag_system

async def add_document(content: str, doc_type: DocumentType = DocumentType.TEXT,
                      metadata: Dict[str, Any] = None) -> bool:
    """添加文档（便捷函数）"""
    system = get_rag_system()
    return await system.add_document(content, doc_type, metadata)

async def search(query: str, top_k: int = None) -> List[SearchResult]:
    """搜索（便捷函数）"""
    system = get_rag_system()
    return await system.search(query, top_k)
