# RAG知识库架构设计

## 📋 架构概述

### 1.1 目标
- 支持文档导入（PDF、TXT、MD、DOCX等）
- 实现文档分块和向量化
- 实现检索增强生成（RAG）
- 集成到现有的记忆系统中

### 1.2 技术选型
- **文档解析**: PyPDF2, python-docx, markdown
- **文本分块**: 自定义分块器（基于句子/段落）
- **向量化**: sentence-transformers（复用现有embedding模型）
- **向量存储**: 复用现有VectorStore
- **检索**: 向量相似度检索 + 关键词检索

---

## 二、架构设计

### 2.1 模块结构

```
app/rag/
├── __init__.py           # RAG模块入口
├── document_loader.py    # 文档加载器
├── text_splitter.py      # 文本分块器
├── vector_store.py       # 向量存储（复用现有）
├── retriever.py          # 检索器
├── generator.py          # 生成器
└── knowledge_base.py     # 知识库管理
```

### 2.2 数据流

```
文档导入 → 文档解析 → 文本分块 → 向量化 → 存储
                                          ↓
用户查询 → 向量化 → 检索相似块 → 上下文组装 → LLM生成
```

### 2.3 与现有系统集成

```
┌─────────────────────────────────────────────┐
│              记忆系统 v3.0                   │
├─────────────────────────────────────────────┤
│  工作记忆 │ 情景记忆 │ 语义记忆 │ 事实库    │
├─────────────────────────────────────────────┤
│              RAG知识库                       │
├─────────────────────────────────────────────┤
│  文档导入 │ 文本分块 │ 向量存储 │ 检索增强  │
└─────────────────────────────────────────────┘
```

---

## 三、核心组件设计

### 3.1 文档加载器 (DocumentLoader)

**功能**:
- 支持多种文档格式：PDF、TXT、MD、DOCX
- 文档解析和文本提取
- 元数据提取（标题、作者、日期等）

**接口**:
```python
class DocumentLoader:
    def load(self, file_path: str) -> Document
    def load_batch(self, file_paths: List[str]) -> List[Document]
```

### 3.2 文本分块器 (TextSplitter)

**功能**:
- 基于句子/段落的智能分块
- 保持语义完整性
- 支持重叠窗口

**接口**:
```python
class TextSplitter:
    def split(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[TextChunk]
```

### 3.3 检索器 (Retriever)

**功能**:
- 向量相似度检索
- 关键词检索
- 混合检索（向量+关键词）

**接口**:
```python
class Retriever:
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]
```

### 3.4 生成器 (Generator)

**功能**:
- 检索增强生成
- 上下文组装
- LLM调用

**接口**:
```python
class Generator:
    def generate(self, query: str, context: List[str]) -> str
```

### 3.5 知识库管理 (KnowledgeBase)

**功能**:
- 文档管理（导入、删除、更新）
- 知识库统计
- 知识库持久化

**接口**:
```python
class KnowledgeBase:
    def add_document(self, file_path: str) -> bool
    def remove_document(self, doc_id: str) -> bool
    def search(self, query: str, top_k: int = 5) -> List[SearchResult]
    def get_stats(self) -> Dict[str, Any]
```

---

## 四、实现计划

### 4.1 Phase 1: 基础功能（1周）
1. 文档加载器实现
2. 文本分块器实现
3. 向量存储集成
4. 基础检索功能

### 4.2 Phase 2: 高级功能（1周）
1. 混合检索（向量+关键词）
2. 检索增强生成
3. 知识库管理界面
4. 文档更新和删除

### 4.3 Phase 3: 优化和测试（1周）
1. 性能优化
2. 测试用例编写
3. 文档编写
4. 用户界面集成

---

## 五、配置设计

### 5.1 RAG配置

```yaml
rag:
  enabled: true
  chunk_size: 500
  chunk_overlap: 50
  top_k: 5
  similarity_threshold: 0.7
  retrieval_weights:
    vector: 0.7
    keyword: 0.3
  supported_formats:
    - pdf
    - txt
    - md
    - docx
```

### 5.2 存储配置

```yaml
rag:
  storage_dir: ./memory/knowledge_base
  vector_store_dir: ./memory/vectors
  max_documents: 1000
  max_chunks_per_doc: 1000
```

---

## 六、接口设计

### 6.1 API接口

```python
# 文档导入
POST /api/rag/documents
Content-Type: multipart/form-data

# 文档搜索
GET /api/rag/search?q=查询内容&top_k=5

# 文档列表
GET /api/rag/documents

# 文档删除
DELETE /api/rag/documents/{doc_id}

# 知识库统计
GET /api/rag/stats
```

### 6.2 WebSocket接口

```python
# 实时搜索
WS /ws/rag/search
{
  "type": "search",
  "query": "查询内容",
  "top_k": 5
}
```

---

## 七、测试计划

### 7.1 单元测试
- 文档加载器测试
- 文本分块器测试
- 检索器测试
- 生成器测试

### 7.2 集成测试
- 文档导入流程测试
- 检索增强生成测试
- 知识库管理测试

### 7.3 性能测试
- 文档导入性能
- 检索性能
- 生成性能

---

## 八、风险评估

### 8.1 技术风险
- 文档解析兼容性
- 向量检索准确性
- LLM生成质量

### 8.2 性能风险
- 大文档处理性能
- 向量存储内存占用
- 检索响应时间

### 8.3 缓解措施
- 多种文档格式支持
- 分块和索引优化
- 缓存和预计算

---

**设计时间**: 2026-06-03 08:22:00  
**设计人**: 齐活林（Qi）· 交付总监  
**版本**: v1.0