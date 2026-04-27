#!/usr/bin/env python3
"""
=====================================
RAG 记忆系统模块 - 优化版 v2.0
=====================================

优化点 (v2.1):
- 文件系统持久化 (参考 Claude Code)
- 四层记忆架构 (工作/情景/语义/程序)
- 遗忘机制: 保留分数 = 重要性 × 时效衰减 × 访问频率 × 关联度
- 滑动窗口: 超过阈值自动摘要压缩早期对话
- 混合检索: 向量相似度 + BM25关键词 + 时间权重重排序
- 重要性评分增强 (关键词扩展)

作者: 咕咕嘎嘎
日期: 2026-04-18
"""

import os
import json
import time
import math
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import OrderedDict
from dataclasses import dataclass, asdict


# ==================== 数据结构 ====================

@dataclass
class MemoryItem:
    """记忆条目(增强版:支持遗忘机制)"""
    role: str  # user/assistant
    content: str
    timestamp: float
    importance: int = 0  # 0-5, 5最重要
    tags: List[str] = None
    
    # 遗忘机制字段
    access_count: int = 1      # 被检索命中的次数
    connectivity: int = 0      # 与其他记忆的共现次数(关联度)
    is_forgotten: bool = False  # 软删除标记
    is_summary: bool = False    # 是否为摘要压缩后的记忆
    
    def __post_init__(self):
        """
        [功能说明]数据类初始化后处理(确保 tags 字段不为 None)

        [返回值]
            无
        """
        if self.tags is None:
            self.tags = []
    
    def get_retention_score(self) -> float:
        """计算当前保留分数"""
        hours_old = (time.time() - self.timestamp) / 3600
        return RetentionScorer.compute_retention_score(
            importance=self.importance,
            hours_old=hours_old,
            access_count=self.access_count,
            connectivity=self.connectivity
        )
    
    def should_forget(self) -> bool:
        """判断是否应该遗忘"""
        if self.is_forgotten:
            return True
        return RetentionScorer.should_forget(self.get_retention_score())
    
    def touch(self):
        """
        [功能说明]记忆被访问时调用,增加访问计数

        [返回值]
            无
        """
        self.access_count += 1
    
    def link(self, other_mem_id: str):
        """
        [功能说明]与其他记忆建立关联,增加关联计数

        [参数说明]
            other_mem_id (str): 关联的记忆 ID(当前版本未使用,保留接口)

        [返回值]
            无
        """
        self.connectivity += 1


# ==================== 遗忘机制 ====================

class RetentionScorer:
    """
    智能遗忘机制
    保留分数 = 重要性 × 时效衰减 × 访问频率 × 关联度
    
    低于阈值的记忆会被软删除(标记为过期),不再被检索到.
    """
    
    # 时效衰减系数(lambda),数值越大衰减越快
    DECAY_LAMBDA = 0.01  # 每天衰减约1%
    
    # 软删除阈值
    RETENTION_THRESHOLD = 0.3
    
    # 关联度计算用的共现窗口
    COOCCUR_WINDOW = 5
    
    @classmethod
    def compute_recency_decay(cls, hours_old: float) -> float:
        """
        [功能说明]计算时效衰减系数 e^(-lambda * hours)

        [参数说明]
            hours_old (float): 记忆存在的小时数

        [返回值]
            float: 衰减系数,24h前约0.79,7天前约0.17,30天前接近0
        """
        return math.exp(-cls.DECAY_LAMBDA * hours_old)
    
    @classmethod
    def compute_retention_score(
        cls,
        importance: float,      # 0-5 原始重要性评分
        hours_old: float,       # 距现在的小时数
        access_count: int = 1,  # 访问次数(被检索命中的次数)
        connectivity: int = 0  # 关联度(与多少条记忆共现过)
    ) -> float:
        """
        计算保留分数 0.0 ~ 1.0
        
        公式:importance_norm × recency_decay × access_boost × connectivity_boost
        """
        # 归一化重要性到 0-1
        importance_norm = importance / 5.0
        
        # 时效衰减
        recency = cls.compute_recency_decay(hours_old)
        
        # 访问频率加成(对数曲线,避免过度刷访问量)
        access_boost = 1.0 + 0.2 * math.log1p(access_count)
        
        # 关联度加成(越多人引用越不容易被遗忘)
        connectivity_boost = 1.0 + 0.1 * connectivity
        
        score = importance_norm * recency * access_boost * connectivity_boost
        return min(score, 1.0)
    
    @classmethod
    def should_forget(cls, retention_score: float) -> bool:
        """判断是否应该遗忘"""
        return retention_score < cls.RETENTION_THRESHOLD
    
    @classmethod
    def get_decay_stats(cls, hours_old: float) -> Dict[str, float]:
        """获取衰减统计(用于调试)"""
        return {
            "hours_old": hours_old,
            "recency_decay": cls.compute_recency_decay(hours_old),
            "score_at_importance_5": cls.compute_retention_score(5, hours_old),
            "score_at_importance_3": cls.compute_retention_score(3, hours_old),
            "score_at_importance_1": cls.compute_retention_score(1, hours_old),
        }


# ==================== 重要性评分 ====================

class ImportanceScorer:
    """重要性评分器"""
    
    # 重要关键词(扩展版)
    IMPORTANT_KEYWORDS = [
        # 明确记忆指令
        "记住", "记住这个", "重要", "不要忘记", "下次",
        "name", "remember", "记住我", "preference", "喜欢", "讨厌",
        # 个人信息
        "电话", "地址", "账号", "密码", "email", "邮箱",
        "生日", "纪念日", "预约", "待办", "todo",
        # 偏好设置
        "不要", "拒绝", "禁止", "偏好", "喜欢用", "习惯了",
        # 项目/任务
        "项目", "任务", "deadline", "截止",
        # 金融相关
        "股票", "基金", "账户", "余额", "密码",
    ]
    
    # 忽略词(无意义闲聊)
    IGNORE_WORDS = ["你好", "hi", "hello", "在吗", "嗯", "哦", "好", "啊", "哈", "呵"]
    
    @classmethod
    def score(cls, role: str, content: str) -> int:
        """
        [功能说明]根据内容和角色自动评分 0-5

        [参数说明]
            role (str): 角色(user/assistant)
            content (str): 对话内容

        [返回值]
            int: 重要性评分 0-5
        """
        content_lower = content.lower()
        
        # 忽略词(极短闲聊)
        if len(content) < 10:
            for word in cls.IGNORE_WORDS:
                if word in content_lower:
                    return 0
        
        # 重要关键词检测
        score = 0
        for keyword in cls.IMPORTANT_KEYWORDS:
            if keyword in content_lower:
                score = max(score, 4)
                break
        
        # 长度加分(长内容更有信息量)
        if len(content) > 100:
            score += 1
        
        # 明确记忆指令最高分
        for kw in ["记住", "不要忘记", "remember", "偏好"]:
            if kw in content_lower:
                score = 5
                break
        
        return min(score, 5)
    
    @classmethod
    def is_important(cls, score: int) -> bool:
        """判断是否重要(>=3分视为重要)"""
        return score >= 3
    
    @classmethod
    def is_critical(cls, score: int) -> bool:
        """判断是否关键记忆(>=4分)"""
        return score >= 4


# ==================== LRU 缓存 ====================

class LRUCache:
    """LRU 缓存"""
    
    def __init__(self, capacity: int = 100):
        """初始化 LRU 缓存"""
        self.cache = OrderedDict()
        self.capacity = capacity
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值,如果存在则移动到末尾(LRU)"""
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def put(self, key: str, value: Any):
        """放入缓存,超出容量时淘汰最旧的"""
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)


# ==================== 向量存储 ====================

class VectorStore:
    """向量存储 - 优化版"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化向量存储器"""
        self.config = config or {}
        self.storage_dir = self.config.get("storage_dir", "./memory/vectors")
        self.embedding_dim = self.config.get("embedding_dim", 768)
        
        self.vectors = {}
        self.texts = {}
        self.metadatas = {}
        self._norms = {}  # 缓存向量范数,避免重复计算
        
        self._embedding_cache = LRUCache(200)
        self._search_cache = LRUCache(50)
        self.embedding_model = None
        self._model_loaded = False
        self._pending_save = False  # 批处理标志
        
        self._persist_file = Path(self.storage_dir) / "vector_store.json"
        Path(self.storage_dir).mkdir(parents=True, exist_ok=True)
        # 检索权重配置
        self._retrieval_weights = (config or {}).get("retrieval_weights", {"vector": 0.7, "keyword": 0.2, "recency": 0.1})
        # Embedding 配置
        self._embed_device = (config or {}).get("embedding_device", "cpu")  # cpu / cuda
        self._embed_model_name = (config or {}).get("embedding_model", "paraphrase-multilingual-MiniLM-L12-v2")
        self._load_from_disk()
    
    def _get_norm(self, doc_id: str) -> float:
        """获取向量范数(带缓存)"""
        if doc_id not in self._norms:
            emb = self.vectors[doc_id]
            self._norms[doc_id] = sum(x * x for x in emb) ** 0.5
        return self._norms[doc_id]
    
    def _load_from_disk(self):
        """从磁盘加载持久化的向量数据"""
        if not self._persist_file.exists():
            return
        try:
            print(" 加载持久化记忆...")
            with open(self._persist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.vectors = data.get("vectors", {})
            self.texts = data.get("texts", {})
            self.metadatas = data.get("metadatas", {})
            print(f" 已加载 {len(self.texts)} 条记忆")
        except Exception as e:
            print(f"️ 加载记忆失败: {e}")
    
    def _save_to_disk(self):
        """保存向量数据到磁盘（原子写入）"""
        try:
            data = {
                "vectors": self.vectors,
                "texts": self.texts,
                "metadatas": self.metadatas,
                "updated_at": datetime.now().isoformat(),
            }
            # 原子写入：先写临时文件再rename
            tmp_file = self._persist_file.with_suffix('.tmp')
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_file, self._persist_file)
        except Exception as e:
            print(f"️ 保存记忆失败: {e}")
    
    def _get_local_model_path(self) -> str:
        """
        [功能说明]查找本地已缓存的 embedding 模型路径

        [查找策略]
            根据 self._embed_model_name 在多个可能位置搜索:
            1. .cache/modelscope/ (ModelScope 格式, org/model___variant)
            2. .cache/modelscope/hub/hub/sentence-transformers/ (旧格式)
            3. .cache/huggingface/hub/ (HuggingFace 格式)
            4. models/modelscope/ (旧路径兼容)
        """
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_name = self._embed_model_name
        # 将 / 替换为 -- (HuggingFace 格式)
        hf_style = model_name.replace("/", "--")
        # ModelScope 的转义规则: . -> ___
        # 如 bge-base-zh-v1.5 -> bge-base-zh-v1___5
        model_basename = model_name.split("/")[-1]  # e.g. bge-base-zh-v1.5
        ms_escaped = model_basename.replace(".", "___")  # e.g. bge-base-zh-v1___5
        ms_org = model_name.split("/")[0] if "/" in model_name else ""  # e.g. BAAI

        # 构建候选搜索路径
        search_paths = [
            # 1. ModelScope 新格式 (.cache/modelscope/Org/model___variant)
            os.path.join(project_root, '.cache', 'modelscope', ms_org, ms_escaped) if ms_org else "",
            # 2. ModelScope 旧格式 (.cache/modelscope/hub/hub/sentence-transformers/model_basename)
            os.path.join(project_root, '.cache', 'modelscope', 'hub', 'hub', 'sentence-transformers', model_basename),
            # 3. HuggingFace 格式 (.cache/huggingface/hub/models--Org--model_basename)
            os.path.join(project_root, '.cache', 'huggingface', 'hub', f"models--{hf_style}"),
            # 4. 旧路径兼容 (models/modelscope/hub/hub/sentence-transformers/model_basename)
            os.path.join(project_root, 'models', 'modelscope', 'hub', 'hub', 'sentence-transformers', model_basename),
        ]

        for path in search_paths:
            if not path:
                continue
            # 检查是否有模型文件 (safetensors 或 pytorch_model.bin)
            if os.path.isfile(os.path.join(path, 'model.safetensors')) or \
               os.path.isfile(os.path.join(path, 'pytorch_model.bin')):
                return path
            # HuggingFace 格式需要进入 snapshots 子目录
            if os.path.isdir(os.path.join(path, 'snapshots')):
                snapshots_dir = os.path.join(path, 'snapshots')
                snapshots = os.listdir(snapshots_dir) if os.path.isdir(snapshots_dir) else []
                if snapshots:
                    snap_path = os.path.join(snapshots_dir, snapshots[0])
                    if os.path.isfile(os.path.join(snap_path, 'model.safetensors')) or \
                       os.path.isfile(os.path.join(snap_path, 'pytorch_model.bin')):
                        return snap_path

        # 5. 兜底: 在 .cache/modelscope/ 下模糊搜索包含模型名关键字的目录
        ms_cache = os.path.join(project_root, '.cache', 'modelscope')
        if os.path.isdir(ms_cache):
            for org_dir in os.listdir(ms_cache):
                org_path = os.path.join(ms_cache, org_dir)
                if not os.path.isdir(org_path):
                    continue
                for model_dir in os.listdir(org_path):
                    # 模糊匹配: 目录名包含模型名关键字（去掉特殊字符后比较）
                    clean_dir = model_dir.replace("___", ".").replace("--", "/")
                    if model_basename in clean_dir or clean_dir.endswith(model_basename):
                        full_path = os.path.join(org_path, model_dir)
                        if os.path.isfile(os.path.join(full_path, 'model.safetensors')) or \
                           os.path.isfile(os.path.join(full_path, 'pytorch_model.bin')):
                            return full_path
        return ""

    def _load_embedding_model(self):
        """
        [功能说明]加载 SentenceTransformer 嵌入模型

        [降级策略]
            1. 优先从本地缓存加载 (modelscope / huggingface)
            2. 本地无缓存时尝试在线下载 (支持 HF_ENDPOINT 镜像)
            3. 全部失败回退到 hash-based 简单嵌入
        """
        if self._model_loaded:
            return
        self._model_loaded = True
        try:
            from sentence_transformers import SentenceTransformer
            device = self._embed_device
            model_name = self._embed_model_name
            # 优先本地路径
            local_path = self._get_local_model_path()
            if local_path:
                print(f" [记忆系统] 加载本地嵌入模型: {local_path} | device={device}")
                # 设置离线模式，避免 SentenceTransformer 内部尝试联网检查 modules.json
                os.environ['TRANSFORMERS_OFFLINE'] = '1'
                self.embedding_model = SentenceTransformer(local_path, device=device)
            else:
                print(f" [记忆系统] 未找到本地缓存,尝试在线加载: {model_name} | device={device}")
                self.embedding_model = SentenceTransformer(model_name, device=device)
            # 自动修正 embedding 维度
            actual_dim = self.embedding_model.get_sentence_embedding_dimension()
            if actual_dim != self.embedding_dim:
                print(f" [记忆系统] 维度自动修正: {self.embedding_dim} -> {actual_dim}")
                self.embedding_dim = actual_dim
            print(" [记忆系统] 嵌入模型加载成功!")
        except ImportError:
            print(" [记忆系统] sentence-transformers 未安装,使用简单嵌入")
            self.embedding_model = "simple"
        except Exception as e:
            print(f" [记忆系统] 嵌入模型加载失败({type(e).__name__}): {e},使用简单嵌入")
            self.embedding_model = "simple"
    
    def get_embedding(self, text: str) -> List[float]:
        """获取文本的嵌入向量(带缓存)"""
        cached = self._embedding_cache.get(text)
        if cached is not None:
            return cached
        if not self._model_loaded:
            self._load_embedding_model()
        if self.embedding_model == "simple":
            embedding = self._simple_embedding(text)
        elif self.embedding_model:
            embedding = self.embedding_model.encode(text, convert_to_numpy=True).tolist()
        else:
            import random
            embedding = [random.random() for _ in range(self.embedding_dim)]
        self._embedding_cache.put(text, embedding)
        return embedding
    
    def _simple_embedding(self, text: str) -> List[float]:
        """简单嵌入方法(当 sentence-transformers 不可用时使用)"""
        words = text.lower().split()
        vector = [0.0] * self.embedding_dim
        for i, word in enumerate(words[:self.embedding_dim]):
            vector[i % self.embedding_dim] += hash(word) % 1000 / 1000.0
        total = sum(vector) or 1
        return [v / total for v in vector]
    
    def add(self, text: str, metadata: Dict[str, Any] = None) -> str:
        """添加文本到向量存储"""
        import uuid
        doc_id = str(uuid.uuid4())
        embedding = self.get_embedding(text)
        self.vectors[doc_id] = embedding
        self.texts[doc_id] = text
        self.metadatas[doc_id] = metadata or {}
        # 预缓存向量范数
        self._norms[doc_id] = sum(x * x for x in embedding) ** 0.5
        # 持久化策略:每5条写一次磁盘，重要数据不能等50条才落盘
        # (原来50条批量导致数据几乎永远不会写入磁盘)
        if len(self.texts) % 5 == 0:
            self._save_to_disk()
            self._pending_save = False
        else:
            self._pending_save = True
        return doc_id
    
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """混合检索:向量相似度 + 关键词 + 时间权重"""
        cache_key = f"{query}:{top_k}"
        cached = self._search_cache.get(cache_key)
        if cached is not None:
            return cached
        if not self.texts:
            return []
        query_embedding = self.get_embedding(query)
        # 预计算查询向量范数(复用)
        norm_a = sum(x * x for x in query_embedding) ** 0.5
        
        # ===== 混合检索:向量相似度 + 关键词匹配 + 时间权重 =====
        results = []
        for doc_id, embedding in self.vectors.items():
            # 1. 向量余弦相似度
            vector_score = self._cosine_similarity(query_embedding, norm_a, embedding)
            
            # 2. 关键词 BM25 得分(简化版)
            keyword_score = self._bm25_keyword_score(query, self.texts[doc_id])
            
            # 3. 时间权重(越近的记忆权重越高)
            metadata = self.metadatas.get(doc_id, {})
            timestamp = metadata.get("timestamp", time.time())
            hours_old = (time.time() - timestamp) / 3600
            time_weight = RetentionScorer.compute_recency_decay(hours_old)
            
            # 综合得分 = 可配置权重（默认 0.7 * 向量 + 0.2 * 关键词 + 0.1 * 时间）
            weights = getattr(self, '_retrieval_weights', None) or {"vector": 0.7, "keyword": 0.2, "recency": 0.1}
            final_score = (weights.get("vector", 0.7) * vector_score +
                           weights.get("keyword", 0.2) * keyword_score +
                           weights.get("recency", 0.1) * time_weight)
            
            results.append({
                "id": doc_id,
                "vector_score": vector_score,
                "keyword_score": keyword_score,
                "time_weight": time_weight,
                "score": final_score,
            })
        
        # 按综合得分排序
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # 组装最终结果
        final_results = []
        for item in results[:top_k]:
            doc_id = item["id"]
            final_results.append({
                "id": doc_id,
                "text": self.texts[doc_id],
                "score": item["score"],
                "vector_score": item["vector_score"],
                "keyword_score": item["keyword_score"],
                "time_weight": item["time_weight"],
                "metadata": self.metadatas.get(doc_id, {}),
            })
        
        self._search_cache.put(cache_key, final_results)
        return final_results
    
    def _bm25_keyword_score(self, query: str, text: str) -> float:
        """
        简化 BM25:统计查询词在文本中出现的比例
        返回 0.0 ~ 1.0
        """
        if not query or not text:
            return 0.0
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        if not query_words:
            return 0.0
        matches = len(query_words & text_words)
        return matches / len(query_words)
    
    def _cosine_similarity(self, a: List[float], norm_a: float, b: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        return {"total_docs": len(self.texts), "embedding_dim": self.embedding_dim}
    
    def flush(self):
        """
        [功能说明]将 pending 的向量数据强制写入磁盘

        [使用场景]
            - 程序关闭前调用,确保未满50条批量的数据不丢失
            - clear_all 清空前调用,确保最终状态持久化
        """
        if self._pending_save and self.texts:
            self._save_to_disk()
            self._pending_save = False
            print(f"[Memory] 向量存储已 flush ({len(self.texts)} 条)")
    
    def clear(self):
        """清空所有向量数据"""
        self.flush()  # 关闭前确保 pending 数据写入磁盘
        self.vectors.clear()
        self.texts.clear()
        self.metadatas.clear()
        self._norms.clear()
        self._embedding_cache = LRUCache(200)
        self._search_cache = LRUCache(50)
        if self._persist_file.exists():
            self._persist_file.unlink()


# ==================== 文件存储 ====================

class FileStorage:
    """文件系统存储 (参考 Claude Code)"""
    
    def __init__(self, base_dir: str = "./memory"):
        """初始化文件存储"""
        self.base_dir = Path(base_dir)
        self.daily_dir = self.base_dir / "daily"
        self.long_term_file = self.base_dir / "long_term.md"
        self.index_file = self.base_dir / "index.md"
        self.config_file = self.base_dir / "config.json"
        
        # 创建目录
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化 index.md
        if not self.index_file.exists():
            self._init_index()
    
    def _init_index(self):
        """
        [功能说明]初始化记忆系统入口文件 index.md

        [返回值]
            无
        """
        content = """# 记忆系统入口

## 结构
- `daily/` - 每日对话记录
- `long_term.md` - 长期记忆
- `config.json` - 配置

## 功能
- 自动保存对话
- 重要性评分
- 搜索历史
"""
        self.index_file.write_text(content, encoding='utf-8')
    
    def get_daily_file(self, date: str = None) -> Path:
        """
        [功能说明]获取指定日期的记忆文件路径

        [参数说明]
            date (str): 日期字符串,格式 YYYY-MM-DD,None 表示今天

        [返回值]
            Path: 每日记忆文件路径
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return self.daily_dir / f"{date}.md"
    
    def append_interaction(self, role: str, content: str, importance: int = 0):
        """
        [功能说明]追加对话记录到当日记忆文件

        [参数说明]
            role (str): 角色(user/assistant)
            content (str): 对话内容
            importance (int): 重要性评分(决定星标数量)

        [返回值]
            无
        """
        daily_file = self.get_daily_file()
        timestamp = datetime.now().strftime("%H:%M")
        star = "⭐" * importance if importance > 0 else ""
        line = f"- **{timestamp}** [{role}]{star}: {content}\n"
        
        # 追加写入
        with open(daily_file, 'a', encoding='utf-8') as f:
            f.write(line)
    
    def read_daily(self, date: str = None) -> str:
        """
        [功能说明]读取指定日期的记忆记录

        [参数说明]
            date (str): 日期字符串,None 表示今天

        [返回值]
            str: 记忆内容,文件不存在时返回空字符串
        """
        daily_file = self.get_daily_file(date)
        if not daily_file.exists():
            return ""
        return daily_file.read_text(encoding='utf-8')
    
    def list_daily_files(self) -> List[str]:
        """
        [功能说明]列出所有每日记忆文件

        [返回值]
            List[str]: 日期字符串列表(YYYY-MM-DD 格式,按时间倒序)
        """
        if not self.daily_dir.exists():
            return []
        files = sorted(self.daily_dir.glob("*.md"), reverse=True)
        return [f.stem for f in files]
    
    def append_long_term(self, content: str):
        """
        [功能说明]追加长期记忆内容

        [参数说明]
            content (str): 要追加的记忆内容

        [返回值]
            无
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        line = f"\n## {timestamp}\n\n{content}\n"
        
        with open(self.long_term_file, 'a', encoding='utf-8') as f:
            f.write(line)
    
    def read_long_term(self) -> str:
        """
        [功能说明]读取长期记忆内容

        [返回值]
            str: 长期记忆内容,文件不存在时返回空字符串
        """
        if not self.long_term_file.exists():
            return ""
        return self.long_term_file.read_text(encoding='utf-8')
    
    def search_in_files(self, query: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        [功能说明]在每日记忆文件中搜索关键词

        [参数说明]
            query (str): 搜索关键词
            days (int): 搜索范围(天数),默认7天

        [返回值]
            List[Dict[str, Any]]: 匹配结果列表
        """
        results = []
        query_lower = query.lower()
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_file = self.daily_dir / f"{date}.md"
            if not daily_file.exists():
                continue
            
            content = daily_file.read_text(encoding='utf-8')
            if query_lower in content.lower():
                # 简单高亮
                lines = content.split('\n')
                matched = [l for l in lines if query_lower in l.lower()]
                if matched:
                    results.append({
                        "date": date,
                        "matches": matched[:5],
                    })
        
        return results
    
    def export_all(self) -> str:
        """
        [功能说明]导出所有记忆(长期 + 近期30天)

        [返回值]
            str: 格式化的记忆导出文本
        """
        output = f"# 记忆导出 - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        # 长期记忆
        long_term = self.read_long_term()
        if long_term:
            output += "## 长期记忆\n\n" + long_term + "\n\n"
        
        # 每日记录
        for date in self.list_daily_files()[:30]:  # 最近30天
            content = self.read_daily(date)
            if content:
                output += f"## {date}\n\n" + content + "\n\n"
        
        return output
    
    def import_backup(self, content: str):
        """
        [功能说明]导入记忆备份

        [参数说明]
            content (str): 备份内容

        [返回值]
            无
        """
        # 简单实现:追加到 long_term
        self.append_long_term("\n[导入备份]\n" + content)
    
    def clear(self):
        """
        [功能说明]清空所有记忆文件

        [返回值]
            无
        """
        if self.daily_dir.exists():
            for f in self.daily_dir.glob("*.md"):
                f.unlink()
        if self.long_term_file.exists():
            self.long_term_file.unlink()


# ==================== 主记忆系统 ====================

class MemorySystem:
    """
    记忆系统 v2.1 - 增强版
    
    改进点:
    - 四层记忆架构: 工作记忆 → 情景记忆 → 语义记忆 → 程序记忆
    - 遗忘机制: 保留分数自动淘汰低价值记忆
    - 滑动窗口: 自动摘要压缩超限对话
    - 混合检索: 向量 + 关键词 + 时间权重
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """初始化记忆系统"""
        self.config = config or {}
        self.provider = self.config.get("provider", "simple")
        
        # 存储目录
        self.storage_dir = self.config.get("storage_dir", "./memory")
        
        # 从配置读取参数（不再硬编码）
        self.working_memory_limit = self.config.get("working_memory_limit", 20)
        self.summarize_threshold = self.config.get("summarize_threshold", 15)
        self.summarize_batch = self.config.get("summarize_batch", 5)
        
        # 遗忘机制参数
        RetentionScorer.DECAY_LAMBDA = self.config.get("decay_lambda", 0.01)
        RetentionScorer.RETENTION_THRESHOLD = self.config.get("forgetting_threshold", 0.3)
        
        # 向量存储 (语义记忆 - 长期)
        # 确保 vector_store 使用 storage_dir/vectors/ 子目录，避免与根目录混在一起
        vs_config = dict(self.config)  # 浅拷贝，不污染原 config
        vs_config["storage_dir"] = os.path.join(self.storage_dir, "vectors")
        self.vector_store = VectorStore(vs_config)
        
        # 文件存储 (情景记忆 - 每日日志)
        self.file_storage = FileStorage(self.storage_dir)
        
        # ===== 四层记忆 =====
        # 工作记忆:当前对话窗口内的上下文(sliding window)
        self.working_memory: List[MemoryItem] = []
        
        # 情景记忆:已完成对话的原始记录(会被压缩或遗忘)
        self.episodic_memory: List[MemoryItem] = []
        
        # 语义记忆:通过摘要提炼出的结构化知识(存在向量库)
        # → 由 vector_store 管理
        
        # 程序记忆:Agent 行为模式和工具使用习惯(System Prompt)
        # → 在 prompts.py 中管理
        
        # 过期记忆计数(用于遗忘机制)
        self.forgotten_count = 0
        
        # 自动存储
        self.auto_store = self.config.get("auto_store", True)
        
        # ===== 持久化文件路径 =====
        self._persist_dir = Path(self.storage_dir) / "state"
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._working_memory_file = self._persist_dir / "working_memory.json"
        self._episodic_memory_file = self._persist_dir / "episodic_memory.json"
        self._forgotten_count_file = self._persist_dir / "forgotten_count.json"
        
        # ===== 从磁盘恢复工作/情景记忆 =====
        self._load_memory_state()
        
        print(f" 记忆系统 v2.2 初始化完成")
        print(f" 存储目录: {self.storage_dir}")
        print(f" 工作记忆: {len(self.working_memory)}条, 情景记忆: {len(self.episodic_memory)}条, 语义记忆: {self.vector_store.get_stats()['total_docs']}条")
        print(f" 工作记忆上限: {self.working_memory_limit}, 摘要阈值: {self.summarize_threshold}, 遗忘阈值: {RetentionScorer.RETENTION_THRESHOLD}")
        
        # H5修复: 定时flush，防止不满5条时数据丢失
        # 每30秒自动持久化一次，确保崩溃时最多丢失30秒数据
        self._flush_timer = None
        self._start_flush_timer()
    
    def _start_flush_timer(self):
        """启动定时flush计时器(每30秒一次)"""
        import threading
        def _flush_worker():
            try:
                self._save_memory_state()
            except Exception:
                pass  # 定时flush不能抛异常
            finally:
                # 重新调度
                if self._flush_timer is not None:
                    self._flush_timer = threading.Timer(30.0, _flush_worker)
                    self._flush_timer.daemon = True
                    self._flush_timer.start()
        
        self._flush_timer = threading.Timer(30.0, _flush_worker)
        self._flush_timer.daemon = True
        self._flush_timer.start()
    
    # ==================== 持久化方法 ====================
    
    def _load_memory_state(self):
        """从磁盘恢复工作记忆和情景记忆（重启后不丢失）"""
        # 恢复工作记忆
        if self._working_memory_file.exists():
            try:
                with open(self._working_memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.working_memory = [self._dict_to_memory_item(item) for item in data]
                print(f" [记忆] 恢复工作记忆: {len(self.working_memory)}条")
            except Exception as e:
                print(f" [记忆] 恢复工作记忆失败: {e}")
        
        # 恢复情景记忆
        if self._episodic_memory_file.exists():
            try:
                with open(self._episodic_memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.episodic_memory = [self._dict_to_memory_item(item) for item in data]
                print(f" [记忆] 恢复情景记忆: {len(self.episodic_memory)}条")
            except Exception as e:
                print(f" [记忆] 恢复情景记忆失败: {e}")
        
        # 恢复遗忘计数
        if self._forgotten_count_file.exists():
            try:
                with open(self._forgotten_count_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.forgotten_count = data.get("count", 0)
            except Exception:
                pass
    
    @staticmethod
    def _dict_to_memory_item(d: Dict[str, Any]) -> MemoryItem:
        """将字典转为 MemoryItem，兼容旧版本缺失字段"""
        # 确保 dataclass 所有字段都有默认值，缺失字段用默认值填充
        return MemoryItem(
            role=d.get("role", "unknown"),
            content=d.get("content", ""),
            timestamp=d.get("timestamp", time.time()),
            importance=d.get("importance", 0),
            tags=d.get("tags", []),
            access_count=d.get("access_count", 1),
            connectivity=d.get("connectivity", 0),
            is_forgotten=d.get("is_forgotten", False),
            is_summary=d.get("is_summary", False),
        )
    
    def _save_memory_state(self):
        """将工作记忆和情景记忆保存到磁盘（原子写入：先写临时文件再rename）"""
        try:
            # 保存工作记忆
            self._atomic_write_json(
                self._working_memory_file,
                [asdict(item) for item in self.working_memory]
            )
            
            # 保存情景记忆
            self._atomic_write_json(
                self._episodic_memory_file,
                [asdict(item) for item in self.episodic_memory]
            )
            
            # 保存遗忘计数
            self._atomic_write_json(
                self._forgotten_count_file,
                {"count": self.forgotten_count}
            )
        except Exception as e:
            print(f" [记忆] 保存状态失败: {e}")
    
    def _atomic_write_json(self, target_path: Path, data: Any):
        """原子写入JSON：先写临时文件再rename，防止写到一半断电导致文件损坏"""
        tmp_path = target_path.with_suffix('.tmp')
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # Windows: rename 会覆盖目标文件（Python 3.8+ os.replace）
        os.replace(tmp_path, target_path)
    
    def flush(self):
        """强制将所有未持久化的记忆数据写入磁盘（程序退出前调用）"""
        # 停止定时flush
        if self._flush_timer is not None:
            self._flush_timer.cancel()
            self._flush_timer = None
        self._save_memory_state()
        self.vector_store.flush()
        print(f"[Memory] 全部记忆已 flush (工作:{len(self.working_memory)} 情景:{len(self.episodic_memory)} 语义:{self.vector_store.get_stats()['total_docs']})")
    
    def add_interaction(self, role: str, content: str, importance: int = None):
        """
        [功能说明]添加对话记录(自动评分 + 滑动窗口 + 遗忘机制)

        [参数说明]
            role (str): 角色(user/assistant)
            content (str): 对话内容
            importance (int): 重要性评分,None 表示自动评分

        [返回值]
            无

        [流程]
            1. 自动评分 → 创建 MemoryItem
            2. 加入工作记忆(sliding window)
            3. 超过阈值时触发摘要压缩
            4. 重要记忆存入向量库(语义记忆)
            5. 每次添加顺带执行遗忘扫描
            6. 文件持久化
        
        流程:
        1. 自动评分 → 创建 MemoryItem
        2. 加入工作记忆(sliding window)
        3. 超过阈值时触发摘要压缩(工作记忆 → 情景记忆)
        4. 重要记忆存入向量库(语义记忆)
        5. 每次添加顺带执行遗忘扫描
        6. 文件持久化
        """
        # 自动重要性评分
        if importance is None:
            importance = ImportanceScorer.score(role, content)
        
        # 创建记忆条目
        item = MemoryItem(
            role=role,
            content=content,
            timestamp=time.time(),
            importance=importance,
        )
        
        # ===== 1. 加入工作记忆 =====
        self.working_memory.append(item)
        
        # ===== 2. 滑动窗口 + 摘要压缩 =====
        if len(self.working_memory) > self.summarize_threshold:
            self._compress_early_memory()
        
        # ===== 3. 重要记忆存入向量库 =====
        if ImportanceScorer.is_critical(importance):
            self.vector_store.add(
                f"{role}: {content}",
                {
                    "timestamp": item.timestamp,
                    "importance": importance,
                    "role": role,
                    "is_summary": False,
                }
            )
            # 重要记忆同步写入 long_term.md（人类可读的长期记忆文件）
            self.file_storage.append_long_term(f"[{role}] 重要性:{importance} - {content}")
        
        # ===== 4. 遗忘扫描(每次添加顺带清理一次)=====
        self._forgetting_sweep()
        
        # ===== 5. 文件持久化 =====
        if self.auto_store:
            self.file_storage.append_interaction(role, content, importance)
        
        # ===== 6. 工作记忆/情景记忆状态持久化（每5条保存一次）=====
        if len(self.working_memory) % 5 == 0:
            self._save_memory_state()
    
    def _compress_early_memory(self):
        """
        摘要压缩:将早期对话压缩成摘要存入情景记忆
        释放工作记忆空间,同时保留关键信息
        """
        if len(self.working_memory) <= self.summarize_threshold:
            return
        
        # 取最早的 summarize_batch 条
        batch = self.working_memory[:self.summarize_batch]
        self.working_memory = self.working_memory[self.summarize_batch:]
        
        # 构建摘要文本
        summary_parts = []
        key_info = []
        for item in batch:
            if item.importance >= 3:
                key_info.append(f"[{item.role}]: {item.content[:80]}")
            else:
                summary_parts.append(f"[{item.role}]: {item.content[:40]}")
        
        # 如果有关键记忆,保留完整内容
        if key_info:
            summary = "[重要对话摘要] " + " | ".join(key_info)
        else:
            summary = "[对话摘要] " + " ".join(summary_parts[:3])
        
        # 创建摘要记忆条目
        summary_item = MemoryItem(
            role="system",
            content=summary,
            timestamp=batch[-1].timestamp,  # 用最后一条的时间
            importance=max(item.importance for item in batch),
            is_summary=True,
        )
        
        # 加入情景记忆
        self.episodic_memory.append(summary_item)
        
        # 如果是关键对话,也存入向量库
        if summary_item.importance >= 3:
            self.vector_store.add(
                f"[摘要] {summary}",
                {
                    "timestamp": summary_item.timestamp,
                    "importance": summary_item.importance,
                    "is_summary": True,
                    "role": "system",
                }
            )
        
        print(f" 记忆压缩: {len(batch)}条 → 1条摘要 (剩余工作记忆: {len(self.working_memory)})")
        
        # 压缩后立即持久化状态
        self._save_memory_state()
    
    def _forgetting_sweep(self):
        """
        遗忘扫描:检查所有记忆,淘汰保留分数过低的
        在 vector_store 和 episodic_memory 中执行
        """
        forgotten = 0
        
        # 检查情景记忆
        survivors = []
        for item in self.episodic_memory:
            if item.should_forget():
                forgotten += 1
            else:
                survivors.append(item)
        self.episodic_memory = survivors
        
        # 更新遗忘计数
        if forgotten > 0:
            self.forgotten_count += forgotten
            print(f" 遗忘扫描: 清理了 {forgotten} 条过期情景记忆 (累计: {self.forgotten_count})")
        return forgotten
    
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        混合检索:工作记忆 + 情景记忆 + 向量库
        - 工作记忆:关键词完全匹配,优先返回
        - 情景记忆:保留分数过滤
        - 向量库:混合检索(向量+关键词+时间权重)
        """
        results = []
        query_lower = query.lower()
        
        # ===== 1. 工作记忆搜索(最优先)=====
        for i, item in enumerate(self.working_memory):
            if query_lower in item.content.lower():
                item.touch()  # 增加访问计数
                results.append({
                    "layer": "working",
                    "index": i,
                    "text": item.content,
                    "role": item.role,
                    "importance": item.importance,
                    "score": 1.0,  # 最高优先级
                    "is_summary": item.is_summary,
                })
        
        # ===== 2. 情景记忆搜索 =====
        for i, item in enumerate(self.episodic_memory):
            if item.is_forgotten:
                continue
            if query_lower in item.content.lower():
                item.touch()
                retention = item.get_retention_score()
                results.append({
                    "layer": "episodic",
                    "index": i,
                    "text": item.content,
                    "role": item.role,
                    "importance": item.importance,
                    "retention_score": retention,
                    "score": 0.7 * retention,
                    "is_summary": item.is_summary,
                })
        
        # ===== 3. 向量库混合检索 =====
        vector_results = self.vector_store.search(query, top_k)
        for vr in vector_results:
            results.append({
                "layer": "semantic",
                "text": vr["text"],
                "score": vr["score"],
                "vector_score": vr.get("vector_score", 0),
                "keyword_score": vr.get("keyword_score", 0),
                "time_weight": vr.get("time_weight", 0),
                "is_summary": vr["metadata"].get("is_summary", False),
            })
        
        # 按分数排序,取 top_k
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:top_k]
    
    def set_importance(self, index: int, importance: int, layer: str = "working"):
        """手动设置重要性"""
        if layer == "working" and 0 <= index < len(self.working_memory):
            self.working_memory[index].importance = importance
            if ImportanceScorer.is_critical(importance):
                item = self.working_memory[index]
                self.vector_store.add(
                    f"{item.role}: {item.content}",
                    {"timestamp": item.timestamp, "importance": importance, "role": item.role}
                )
        elif layer == "episodic" and 0 <= index < len(self.episodic_memory):
            self.episodic_memory[index].importance = importance
    
    def get_working_memory(self) -> List[Dict[str, Any]]:
        """获取工作记忆"""
        return [asdict(item) for item in self.working_memory]
    
    def get_episodic_memory(self) -> List[Dict[str, Any]]:
        """获取情景记忆"""
        return [asdict(item) for item in self.episodic_memory]
    
    def search_by_time(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        [功能说明]按时间范围搜索记忆

        [参数说明]
            days (int): 搜索范围(天数)

        [返回值]
            List[Dict[str, Any]]: 匹配的记忆列表
        """
        return self.file_storage.search_in_files("", days)
    
    def search_by_role(self, role: str) -> List[Dict[str, Any]]:
        """
        [功能说明]按角色搜索工作记忆

        [参数说明]
            role (str): 角色名(user/assistant)

        [返回值]
            List[Dict[str, Any]]: 匹配的 MemoryItem 字典列表
        """
        results = []
        for item in self.working_memory:
            if item.role == role:
                results.append(asdict(item))
        return results
    
    def summarize(self) -> str:
        """生成对话摘要"""
        if not self.working_memory:
            return ""
        
        recent = self.working_memory[-10:]
        summary = "[对话摘要]\n"
        for item in recent:
            content = item.content[:60] + "..." if len(item.content) > 60 else item.content
            star = "⭐" * item.importance if item.importance else ""
            tag = "[摘要]" if item.is_summary else ""
            summary += f"- {tag}[{item.role}]{star}: {content}\n"
        
        # 加入情景记忆摘要
        if self.episodic_memory:
            summary += "\n[情景记忆摘要]\n"
            for item in self.episodic_memory[-5:]:
                if item.is_summary:
                    summary += f"- {item.content[:80]}\n"
        
        return summary
    
    def get_stats(self) -> Dict[str, Any]:
        """统计信息"""
        # 计算平均保留分数
        retention_scores = [m.get_retention_score() for m in self.episodic_memory]
        avg_retention = sum(retention_scores) / len(retention_scores) if retention_scores else 0
        
        return {
            "working_memory": len(self.working_memory),
            "episodic_memory": len(self.episodic_memory),
            "semantic_memory": self.vector_store.get_stats()["total_docs"],
            "forgotten_count": self.forgotten_count,
            "avg_retention_score": round(avg_retention, 3),
            "provider": self.provider,
            "storage_dir": self.storage_dir,
            "version": "v2.2",
            "persistent": True,  # 标记工作/情景记忆已持久化
        }
    
    def export(self) -> str:
        """
        [功能说明]导出所有记忆为格式化文本

        [返回值]
            str: 导出的记忆文本
        """
        return self.file_storage.export_all()
    
    def import_backup(self, content: str):
        """导入备份"""
        return self.file_storage.import_backup(content)
    
    def clear_all(self):
        """
        [功能说明]清空所有记忆(工作/情景/语义/文件)

        [返回值]
            无
        """
        self.working_memory.clear()
        self.episodic_memory.clear()
        self.vector_store.flush()  # 先 flush 再 clear
        self.vector_store.clear()
        self.file_storage.clear()
        self.forgotten_count = 0
        # 清理持久化状态文件
        for f in [self._working_memory_file, self._episodic_memory_file, self._forgotten_count_file]:
            if f.exists():
                f.unlink()
        print(" 所有记忆已清空")
    
    def get_decay_preview(self) -> Dict[str, Any]:
        """
        [功能说明]预览不同时间跨度的记忆衰减情况(用于调试遗忘机制)

        [返回值]
            Dict[str, Any]: 包含不同时段的衰减统计
        """
        return {
            "now": RetentionScorer.get_decay_stats(0),
            "1day": RetentionScorer.get_decay_stats(24),
            "7days": RetentionScorer.get_decay_stats(24 * 7),
            "30days": RetentionScorer.get_decay_stats(24 * 30),
        }


# 示例
if __name__ == "__main__":
    config = {"storage_dir": "./memory/test"}
    memory = MemorySystem(config)
    
    print("=== 记忆系统 v2.1 测试 ===\n")
    
    # 测试添加
    memory.add_interaction("user", "你好咕咕嘎嘎")           # 忽略词,重要性=0
    memory.add_interaction("assistant", "你好呀~主人")
    memory.add_interaction("user", "记住我的名字是小明")    # 重要,触发向量存储
    memory.add_interaction("user", "我喜欢简洁的回复")
    memory.add_interaction("assistant", "好的喵~我会注意的")
    
    # 添加多条触发滑动窗口压缩
    for i in range(20):
        memory.add_interaction("user", f"这是第{i}条测试对话内容")
    
    # 统计
    print(f"\n统计: {memory.get_stats()}")
    
    # 遗忘衰减预览
    print(f"\n遗忘衰减预览: {memory.get_decay_preview()}")
    
    # 搜索
    results = memory.search("名字")
    print(f"\n搜索'名字'结果: {results}")
    
    # 工作记忆
    print(f"\n工作记忆 ({len(memory.working_memory)}条):")
    for m in memory.get_working_memory():
        tag = "[摘要]" if m["is_summary"] else ""
        print(f"  {tag}[{m['role']}] 重要性:{m['importance']} - {m['content'][:50]}")
    
    # 摘要
    print(f"\n摘要:\n{memory.summarize()}")