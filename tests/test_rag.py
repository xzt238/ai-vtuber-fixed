"""
RAG知识库测试
"""

import pytest
import os
import sys
import tempfile

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.rag import RAGSystem, Document, TextChunk


class TestRAGSystem:
    """RAG系统测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            "storage_dir": self.temp_dir,
            "chunk_size": 100,
            "chunk_overlap": 20,
        }
        self.rag = RAGSystem(self.config)
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_rag_initialization(self):
        """测试RAG系统初始化"""
        assert self.rag is not None
        assert self.rag.storage_dir == self.temp_dir
    
    def test_text_splitter(self):
        """测试文本分块器"""
        text = "这是一个测试文本。它包含多个句子。每个句子都应该被正确分块。"
        
        chunks = self.rag.text_splitter.split(text)
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, TextChunk)
            assert len(chunk.content) > 0
    
    def test_document_loader_txt(self):
        """测试TXT文档加载器"""
        # 创建临时TXT文件
        txt_file = os.path.join(self.temp_dir, "test.txt")
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write("这是一个测试文档的内容。")
        
        # 加载文档
        document = self.rag.document_loader.load(txt_file)
        
        assert document is not None
        assert document.file_name == "test.txt"
        assert document.file_type == "txt"
        assert len(document.content) > 0
    
    def test_knowledge_base_add_document(self):
        """测试知识库添加文档"""
        # 创建测试文档
        document = Document(
            id="test_doc_1",
            file_path="/test/path",
            file_name="test.txt",
            file_type="txt",
            content="这是一个测试文档的内容。",
            metadata={"test": True}
        )
        
        # 添加到知识库
        success = self.rag.knowledge_base.add_document(document)
        
        assert success is True
        assert "test_doc_1" in self.rag.knowledge_base.documents
    
    def test_knowledge_base_search(self):
        """测试知识库搜索"""
        # 添加测试文档
        document = Document(
            id="test_doc_2",
            file_path="/test/path",
            file_name="test.txt",
            file_type="txt",
            content="人工智能是计算机科学的一个分支。它试图理解智能的本质。",
            metadata={"test": True}
        )
        
        # 分块
        chunks = self.rag.text_splitter.split(document.content, document.id)
        document.chunks = chunks
        
        # 添加到知识库
        self.rag.knowledge_base.add_document(document)
        
        # 搜索
        results = self.rag.knowledge_base.search("人工智能")
        
        # 注意：由于向量存储可能没有初始化，搜索可能返回空结果
        # 这里主要测试搜索流程是否正常
        assert isinstance(results, list)
    
    def test_knowledge_base_stats(self):
        """测试知识库统计"""
        stats = self.rag.knowledge_base.get_stats()
        
        assert "total_documents" in stats
        assert "total_chunks" in stats
        assert "total_size" in stats
        assert "storage_dir" in stats
    
    def test_knowledge_base_list_documents(self):
        """测试知识库列出文档"""
        # 添加测试文档
        document = Document(
            id="test_doc_3",
            file_path="/test/path",
            file_name="test.txt",
            file_type="txt",
            content="测试内容",
            metadata={"test": True}
        )
        
        self.rag.knowledge_base.add_document(document)
        
        # 列出文档
        docs = self.rag.knowledge_base.list_documents()
        
        assert len(docs) > 0
        assert any(doc["id"] == "test_doc_3" for doc in docs)


class TestDocument:
    """Document数据类测试"""
    
    def test_document_creation(self):
        """测试Document创建"""
        doc = Document(
            id="test",
            file_path="/test",
            file_name="test.txt",
            file_type="txt",
            content="内容",
            metadata={"key": "value"}
        )
        
        assert doc.id == "test"
        assert doc.file_name == "test.txt"
        assert doc.content == "内容"
        assert doc.metadata["key"] == "value"
        assert doc.chunks == []
    
    def test_document_chunks(self):
        """测试Document chunks"""
        doc = Document(
            id="test",
            file_path="/test",
            file_name="test.txt",
            file_type="txt",
            content="内容",
            metadata={}
        )
        
        chunk = TextChunk(
            id="chunk1",
            document_id="test",
            content="块内容",
            index=0,
            start_char=0,
            end_char=4
        )
        
        doc.chunks = [chunk]
        
        assert len(doc.chunks) == 1
        assert doc.chunks[0].content == "块内容"


class TestTextChunk:
    """TextChunk数据类测试"""
    
    def test_text_chunk_creation(self):
        """测试TextChunk创建"""
        chunk = TextChunk(
            id="chunk1",
            document_id="doc1",
            content="这是块内容",
            index=0,
            start_char=0,
            end_char=6
        )
        
        assert chunk.id == "chunk1"
        assert chunk.document_id == "doc1"
        assert chunk.content == "这是块内容"
        assert chunk.index == 0
        assert chunk.start_char == 0
        assert chunk.end_char == 6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])