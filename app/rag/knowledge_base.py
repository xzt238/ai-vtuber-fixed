"""
知识库管理

提供文档管理、搜索、统计等功能。
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# 日志模块
logger = logging.getLogger("rag.knowledge_base")

from . import Document, RetrievalResult, SearchResult


class KnowledgeBase:
    """知识库管理"""
    
    def __init__(self, config: Dict[str, Any] = None) -> None:
        self.config = config or {}
        self.storage_dir = self.config.get("storage_dir", "./memory/knowledge_base")
        
        # 确保存储目录存在
        if not os.path.isabs(self.storage_dir):
            from app.shared_config import PROJECT_DIR
            self.storage_dir = Path(PROJECT_DIR) / self.storage_dir
            self.storage_dir = os.path.normpath(self.storage_dir)
        
        Path(self.storage_dir).mkdir(parents=True, exist_ok=True)
        
        # 文档索引文件
        self.index_file = Path(self.storage_dir) / "index.json"
        
        # 文档存储
        self.documents: Dict[str, Document] = {}
        
        # 向量存储引用（延迟初始化）
        self._vector_store = None
        
        # 检索器引用（延迟初始化）
        self._retriever = None
        
        # 加载索引
        self._load_index()
        
        logger.info(f"知识库初始化完成")
        logger.info(f"存储目录: {self.storage_dir}")
        logger.info(f"文档数量: {len(self.documents)}")
    
    @property
    def vector_store(self) -> None:
        """延迟加载向量存储"""
        if self._vector_store is None:
            from app.memory import VectorStore
            self._vector_store = VectorStore(self.config)
        return self._vector_store
    
    @property
    def retriever(self) -> None:
        """延迟加载检索器"""
        if self._retriever is None:
            from .retriever import Retriever
            self._retriever = Retriever(self.config)
        return self._retriever
    
    def add_document(self, document: Document) -> bool:
        """添加文档"""
        try:
            # 检查文档是否已存在
            if document.id in self.documents:
                logger.warning(f"文档已存在: {document.file_name}")
                return False
            
            # 添加到内存
            self.documents[document.id] = document
            
            # 将文档块添加到向量存储
            if document.chunks:
                for chunk in document.chunks:
                    # 使用VectorStore的add方法，它会自动生成doc_id
                    generated_id = self.vector_store.add(
                        text=chunk.content,
                        metadata={
                            "document_id": document.id,
                            "file_name": document.file_name,
                            "chunk_index": chunk.index,
                            "chunk_id": chunk.id,
                        }
                    )
                    # 保存生成的ID映射
                    if generated_id:
                        chunk.metadata = chunk.metadata or {}
                        chunk.metadata["vector_store_id"] = generated_id
            
            # 保存索引
            self._save_index()
            
            # 保存文档内容
            self._save_document(document)
            
            logger.info(f"文档添加成功: {document.file_name}")
            logger.info(f"文档ID: {document.id}")
            logger.info(f"分块数量: {len(document.chunks)}")
            
            return True
            
        except Exception as e:
            logger.error(f"文档添加失败: {e}")
            return False
    
    def remove_document(self, doc_id: str) -> bool:
        """删除文档"""
        try:
            if doc_id not in self.documents:
                logger.warning(f"文档不存在: {doc_id}")
                return False
            
            document = self.documents[doc_id]
            
            # 从向量存储中删除文档块
            # 注意：VectorStore没有直接的remove方法，我们需要清理相关数据
            if document.chunks:
                for chunk in document.chunks:
                    # 尝试从向量存储中删除（如果存在）
                    vector_store_id = chunk.metadata.get("vector_store_id")
                    if vector_store_id and hasattr(self.vector_store, 'vectors'):
                        # 直接操作向量存储的内部数据结构
                        if vector_store_id in self.vector_store.vectors:
                            del self.vector_store.vectors[vector_store_id]
                        if vector_store_id in self.vector_store.texts:
                            del self.vector_store.texts[vector_store_id]
                        if vector_store_id in self.vector_store.metadatas:
                            del self.vector_store.metadatas[vector_store_id]
                        if vector_store_id in self.vector_store._norms:
                            del self.vector_store._norms[vector_store_id]
            
            # 从内存中删除
            del self.documents[doc_id]
            
            # 保存索引
            self._save_index()
            
            # 删除文档文件
            self._delete_document_file(doc_id)
            
            # 标记向量矩阵为脏
            if hasattr(self.vector_store, '_matrix_dirty'):
                self.vector_store._matrix_dirty = True
            
            logger.info(f"文档删除成功: {document.file_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"文档删除失败: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """搜索知识库"""
        try:
            # 从向量存储中检索
            retrieval_results = self.retriever.retrieve(query, top_k=top_k)
            
            # 按文档分组
            doc_results: Dict[str, List[RetrievalResult]] = {}
            for result in retrieval_results:
                doc_id = result.chunk.metadata.get("document_id")
                if doc_id:
                    if doc_id not in doc_results:
                        doc_results[doc_id] = []
                    doc_results[doc_id].append(result)
            
            # 构建搜索结果
            search_results = []
            for doc_id, chunks in doc_results.items():
                if doc_id in self.documents:
                    document = self.documents[doc_id]
                    total_score = sum(chunk.score for chunk in chunks) / len(chunks)
                    
                    result = SearchResult(
                        document=document,
                        chunks=chunks,
                        total_score=total_score
                    )
                    search_results.append(result)
            
            # 按总分排序
            search_results.sort(key=lambda x: x.total_score, reverse=True)
            
            return search_results[:top_k]
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """获取文档"""
        return self.documents.get(doc_id)
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """列出所有文档"""
        docs = []
        for doc_id, document in self.documents.items():
            docs.append({
                "id": doc_id,
                "file_name": document.file_name,
                "file_type": document.file_type,
                "file_size": len(document.content),
                "chunks_count": len(document.chunks),
                "added_time": document.metadata.get("added_time"),
            })
        return docs
    
    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        total_chunks = sum(len(doc.chunks) for doc in self.documents.values())
        total_size = sum(len(doc.content) for doc in self.documents.values())
        
        return {
            "total_documents": len(self.documents),
            "total_chunks": total_chunks,
            "total_size": total_size,
            "storage_dir": self.storage_dir,
        }
    
    def update_document(self, doc_id: str, new_content: str) -> bool:
        """更新文档内容"""
        try:
            if doc_id not in self.documents:
                logger.warning(f"文档不存在: {doc_id}")
                return False
            
            document = self.documents[doc_id]
            
            # 删除旧的向量
            if document.chunks:
                for chunk in document.chunks:
                    self.vector_store.remove(chunk.id)
            
            # 更新内容
            document.content = new_content
            
            # 重新分块
            from .text_splitter import TextSplitter
            splitter = TextSplitter(self.config)
            document.chunks = splitter.split(new_content, doc_id)
            
            # 添加新的向量
            if document.chunks:
                for chunk in document.chunks:
                    self.vector_store.add(
                        doc_id=chunk.id,
                        text=chunk.content,
                        metadata={
                            "document_id": document.id,
                            "file_name": document.file_name,
                            "chunk_index": chunk.index,
                        }
                    )
            
            # 保存更新
            self._save_document(document)
            
            logger.info(f"文档更新成功: {document.file_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"文档更新失败: {e}")
            return False
    
    def _load_index(self) -> None:
        """加载索引"""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                
                # 加载文档元数据
                for doc_id, doc_meta in index_data.get("documents", {}).items():
                    # 创建文档对象（不包含内容）
                    document = Document(
                        id=doc_id,
                        file_path=doc_meta.get("file_path", ""),
                        file_name=doc_meta.get("file_name", ""),
                        file_type=doc_meta.get("file_type", ""),
                        content="",  # 内容从文件加载
                        metadata=doc_meta.get("metadata", {}),
                        chunks=[]
                    )
                    self.documents[doc_id] = document
                
                logger.info(f"索引加载成功: {len(self.documents)} 个文档")
                
        except Exception as e:
            logger.error(f"索引加载失败: {e}")
    
    def _save_index(self) -> None:
        """保存索引"""
        try:
            index_data = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "documents": {}
            }
            
            for doc_id, document in self.documents.items():
                index_data["documents"][doc_id] = {
                    "file_path": document.file_path,
                    "file_name": document.file_name,
                    "file_type": document.file_type,
                    "metadata": document.metadata,
                }
            
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"索引保存成功")
            
        except Exception as e:
            logger.error(f"索引保存失败: {e}")
    
    def _save_document(self, document: Document) -> None:
        """保存文档内容"""
        try:
            doc_dir = Path(self.storage_dir) / "documents"
            doc_dir.mkdir(parents=True, exist_ok=True)
            
            doc_file = doc_dir / f"{document.id}.json"
            
            doc_data = {
                "id": document.id,
                "file_path": document.file_path,
                "file_name": document.file_name,
                "file_type": document.file_type,
                "content": document.content,
                "metadata": document.metadata,
                "chunks": [
                    {
                        "id": chunk.id,
                        "content": chunk.content,
                        "index": chunk.index,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                    }
                    for chunk in document.chunks
                ]
            }
            
            with open(doc_file, 'w', encoding='utf-8') as f:
                json.dump(doc_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"文档保存成功: {document.file_name}")
            
        except Exception as e:
            logger.error(f"文档保存失败: {e}")
    
    def _delete_document_file(self, doc_id: str) -> None:
        """删除文档文件"""
        try:
            doc_file = Path(self.storage_dir) / "documents" / f"{doc_id}.json"
            if doc_file.exists():
                doc_file.unlink()
                logger.info(f"文档文件删除成功: {doc_id}")
        except Exception as e:
            logger.error(f"文档文件删除失败: {e}")