"""
记忆存储模块

包含 LRUCache、VectorStore 和 FileStorage。
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import OrderedDict

from memory.scoring import RetentionScorer

logger = logging.getLogger(__name__)

# NumPy 可选导入
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


class LRUCache:
    """LRU 缓存"""
    
    def __init__(self, capacity: int = 100) -> None:
        self.cache = OrderedDict()
        self.capacity = capacity
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def put(self, key: str, value: Any) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)


class VectorStore:
    """
    向量存储 v2 — 增加去重
    
    v3.0 改进:
    - 降低入库阈值 (不再只存 importance>=4, 所有记忆都入库)
    - 添加向量去重 (cosine > 0.95 视为重复)
    - 确保 flush 逻辑完善
    """
    
    def __init__(self, config: Dict[str, Any] = None) -> None:
        self.config = config or {}
        self.storage_dir = self.config.get("storage_dir", "./memory/vectors")
        if not os.path.isabs(self.storage_dir):
            from app.shared_config import PROJECT_DIR
            self.storage_dir = Path(PROJECT_DIR) / self.storage_dir
            self.storage_dir = os.path.normpath(self.storage_dir)
        self.embedding_dim = self.config.get("embedding_dim", 768)
        
        self.vectors = {}
        self.texts = {}
        self.metadatas = {}
        self._norms = {}
        
        self._vectors_matrix = None
        self._norms_array = None
        self._matrix_dirty = True
        
        self._embedding_cache = LRUCache(1000)
        self._search_cache = LRUCache(200)
        self.embedding_model = None
        self._model_loaded = False
        self._pending_save = False
        
        self._dedup_threshold = self.config.get("dedup_threshold", 0.95)
        
        self._persist_file = Path(self.storage_dir) / "vector_store.json"
        self._vectors_npy_file = Path(self.storage_dir) / "vectors.npy"
        self._vectors_meta_file = Path(self.storage_dir) / "vectors_meta.json"
        Path(self.storage_dir).mkdir(parents=True, exist_ok=True)
        self._retrieval_weights = (config or {}).get("retrieval_weights", {"vector": 0.5, "keyword": 0.3, "recency": 0.2})
        self._embed_device = (config or {}).get("embedding_device", "cpu")
        self._embed_model_name = (config or {}).get("embedding_model", "paraphrase-multilingual-MiniLM-L12-v2")
        self._load_from_disk()
    
    def _get_norm(self, doc_id: str) -> float:
        if doc_id not in self._norms:
            emb = self.vectors[doc_id]
            self._norms[doc_id] = sum(x * x for x in emb) ** 0.5
        return self._norms[doc_id]
    
    def _ensure_matrix(self) -> None:
        if not _HAS_NUMPY:
            return
        if not self._matrix_dirty and self._vectors_matrix is not None:
            return
        if not self.vectors:
            self._vectors_matrix = None
            self._norms_array = None
            self._doc_ids = []
            self._matrix_dirty = False
            return
        self._doc_ids = list(self.vectors.keys())
        vec_list = [self.vectors[doc_id] for doc_id in self._doc_ids]
        self._vectors_matrix = np.array(vec_list, dtype=np.float32)
        self._norms_array = np.linalg.norm(self._vectors_matrix, axis=1)
        self._matrix_dirty = False
    
    def _load_from_disk(self) -> None:
        npy_loaded = False
        if _HAS_NUMPY and self._vectors_npy_file.exists() and self._vectors_meta_file.exists():
            try:
                logger.info("加载持久化记忆（NumPy 二进制格式）...")
                matrix = np.load(str(self._vectors_npy_file))
                with open(self._vectors_meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                doc_ids = meta.get("doc_ids", [])
                self.texts = meta.get("texts", {})
                self.metadatas = meta.get("metadatas", {})
                self.vectors = {}
                for i, doc_id in enumerate(doc_ids):
                    if i < len(matrix):
                        self.vectors[doc_id] = matrix[i].tolist()
                self._norms.clear()
                logger.info(f"已加载 {len(self.texts)} 条语义记忆（npy格式）")
                npy_loaded = True
            except Exception as e:
                logger.warning(f"加载 npy 格式失败，回退到 JSON: {e}")
        
        if not npy_loaded and self._persist_file.exists():
            try:
                logger.info("加载持久化记忆（JSON 格式）...")
                with open(self._persist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.vectors = data.get("vectors", {})
                self.texts = data.get("texts", {})
                self.metadatas = data.get("metadatas", {})
                self._norms.clear()
                logger.info(f"已加载 {len(self.texts)} 条语义记忆")
                if _HAS_NUMPY and self.vectors:
                    try:
                        self._save_to_disk()
                        logger.info(f"已自动迁移记忆数据为 npy 格式")
                    except Exception as e:
                        logger.warning(f"自动迁移 npy 格式失败（不影响使用）: {e}")
            except Exception as e:
                logger.error(f"加载记忆失败: {e}")
        
        self._matrix_dirty = True
    
    def _save_to_disk(self) -> None:
        try:
            if _HAS_NUMPY and self.vectors:
                self._ensure_matrix()
                if self._vectors_matrix is not None:
                    np.save(str(self._vectors_npy_file), self._vectors_matrix)
                    meta = {
                        "doc_ids": self._doc_ids if hasattr(self, '_doc_ids') else list(self.vectors.keys()),
                        "texts": self.texts,
                        "metadatas": self.metadatas,
                        "updated_at": datetime.now().isoformat(),
                    }
                    tmp_meta = self._vectors_meta_file.with_suffix('.tmp')
                    with open(tmp_meta, 'w', encoding='utf-8') as f:
                        json.dump(meta, f, ensure_ascii=False, indent=2)
                    os.replace(tmp_meta, self._vectors_meta_file)
                    return
            
            data = {
                "vectors": self.vectors,
                "texts": self.texts,
                "metadatas": self.metadatas,
                "updated_at": datetime.now().isoformat(),
            }
            tmp_file = self._persist_file.with_suffix('.tmp')
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_file, self._persist_file)
        except Exception as e:
            logger.error(f"保存记忆失败: {e}")
    
    def _get_local_model_path(self) -> str:
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_name = self._embed_model_name
        hf_style = model_name.replace("/", "--")
        model_basename = model_name.split("/")[-1]
        ms_escaped = model_basename.replace(".", "___")
        ms_org = model_name.split("/")[0] if "/" in model_name else ""
        
        search_paths = [
            Path(project_root) / '.cache', 'modelscope', ms_org, ms_escaped if ms_org else "",
            Path(project_root) / '.cache', 'modelscope', 'hub', 'hub', 'sentence-transformers', model_basename,
            Path(project_root) / '.cache', 'huggingface', 'hub', f"models--{hf_style}",
            Path(project_root) / 'models', 'modelscope', 'hub', 'hub', 'sentence-transformers', model_basename,
        ]
        
        for path in search_paths:
            if not path:
                continue
            if os.path.isfile(Path(path) / 'model.safetensors') or \
               os.path.isfile(Path(path) / 'pytorch_model.bin'):
                return path
            if os.path.isdir(Path(path) / 'snapshots'):
                snapshots_dir = Path(path) / 'snapshots'
                snapshots = os.listdir(snapshots_dir) if os.path.isdir(snapshots_dir) else []
                if snapshots:
                    snap_path = Path(snapshots_dir) / snapshots[0]
                    if os.path.isfile(Path(snap_path) / 'model.safetensors') or \
                       os.path.isfile(Path(snap_path) / 'pytorch_model.bin'):
                        return snap_path
        
        ms_cache = Path(project_root) / '.cache', 'modelscope'
        if os.path.isdir(ms_cache):
            for org_dir in os.listdir(ms_cache):
                org_path = Path(ms_cache) / org_dir
                if not os.path.isdir(org_path):
                    continue
                for model_dir in os.listdir(org_path):
                    clean_dir = model_dir.replace("___", ".").replace("--", "/")
                    if model_basename in clean_dir or clean_dir.endswith(model_basename):
                        full_path = Path(org_path) / model_dir
                        if os.path.isfile(Path(full_path) / 'model.safetensors') or \
                           os.path.isfile(Path(full_path) / 'pytorch_model.bin'):
                            return full_path
        return ""
    
    def _load_embedding_model(self) -> None:
        if self._model_loaded:
            return
        self._model_loaded = True
        try:
            from sentence_transformers import SentenceTransformer
            device = self._embed_device
            model_name = self._embed_model_name
            local_path = self._get_local_model_path()
            if local_path:
                logger.info(f"加载本地嵌入模型: {local_path} | device={device}")
                os.environ['TRANSFORMERS_OFFLINE'] = '1'
                self.embedding_model = SentenceTransformer(local_path, device=device)
            else:
                logger.warning(f"未找到本地缓存,尝试在线加载: {model_name} | device={device}")
                self.embedding_model = SentenceTransformer(model_name, device=device)
            actual_dim = self.embedding_model.get_sentence_embedding_dimension()
            if actual_dim != self.embedding_dim:
                logger.info(f"维度自动修正: {self.embedding_dim} -> {actual_dim}")
                self.embedding_dim = actual_dim
            logger.info("嵌入模型加载成功!")
        except ImportError:
            logger.warning("sentence-transformers 未安装,使用简单嵌入")
            self.embedding_model = "simple"
        except Exception as e:
            logger.error(f"嵌入模型加载失败({type(e).__name__}): {e},使用简单嵌入")
            self.embedding_model = "simple"
    
    def get_embedding(self, text: str) -> List[float]:
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
        words = text.lower().split()
        vector = [0.0] * self.embedding_dim
        for i, word in enumerate(words[:self.embedding_dim]):
            vector[i % self.embedding_dim] += hash(word) % 1000 / 1000.0
        total = sum(vector) or 1
        return [v / total for v in vector]
    
    def _is_duplicate(self, text: str, embedding: List[float]) -> bool:
        if not self.vectors:
            return False
        
        if _HAS_NUMPY:
            try:
                self._ensure_matrix()
                if self._vectors_matrix is not None and len(self._vectors_matrix) > 0:
                    query_vec = np.array(embedding, dtype=np.float32)
                    query_norm = np.linalg.norm(query_vec)
                    if query_norm == 0:
                        return False
                    similarities = np.dot(self._vectors_matrix, query_vec) / (self._norms_array * query_norm + 1e-8)
                    max_sim = float(np.max(similarities))
                    if max_sim > self._dedup_threshold:
                        return True
                    return False
            except Exception as e:
                pass
        
        norm_a = sum(x * x for x in embedding) ** 0.5
        if norm_a == 0:
            return False
        for doc_id, existing_emb in self.vectors.items():
            sim = self._cosine_similarity(embedding, norm_a, existing_emb)
            if sim > self._dedup_threshold:
                return True
        return False
    
    def add(self, text: str, metadata: Dict[str, Any] = None) -> Optional[str]:
        import uuid
        
        embedding = self.get_embedding(text)
        
        if self._is_duplicate(text, embedding):
            return None
        
        doc_id = str(uuid.uuid4())
        self.vectors[doc_id] = embedding
        self.texts[doc_id] = text
        self.metadatas[doc_id] = metadata or {}
        self._norms[doc_id] = sum(x * x for x in embedding) ** 0.5
        
        self._matrix_dirty = True
        self._search_cache = LRUCache(50)
        
        if len(self.texts) % 5 == 0:
            self._save_to_disk()
            self._pending_save = False
        else:
            self._pending_save = True
        return doc_id
    
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        cache_key = f"{query}:{top_k}"
        cached = self._search_cache.get(cache_key)
        if cached is not None:
            return cached
        if not self.texts:
            return []
        query_embedding = self.get_embedding(query)
        
        if _HAS_NUMPY:
            try:
                results = self._search_numpy(query_embedding, query, top_k)
                if results is not None:
                    self._search_cache.put(cache_key, results)
                    return results
            except Exception as e:
                pass
        
        norm_a = sum(x * x for x in query_embedding) ** 0.5
        
        results = []
        for doc_id, embedding in self.vectors.items():
            vector_score = self._cosine_similarity(query_embedding, norm_a, embedding)
            keyword_score = self._bm25_keyword_score(query, self.texts[doc_id])
            metadata = self.metadatas.get(doc_id, {})
            timestamp = metadata.get("timestamp", time.time())
            hours_old = (time.time() - timestamp) / 3600
            time_weight = RetentionScorer.compute_recency_decay(hours_old)
            
            weights = getattr(self, '_retrieval_weights', None) or {"vector": 0.5, "keyword": 0.3, "recency": 0.2}
            final_score = (weights.get("vector", 0.5) * vector_score +
                           weights.get("keyword", 0.3) * keyword_score +
                           weights.get("recency", 0.2) * time_weight)
            
            results.append({
                "id": doc_id,
                "vector_score": vector_score,
                "keyword_score": keyword_score,
                "time_weight": time_weight,
                "score": final_score,
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        
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
    
    def _search_numpy(self, query_embedding: List[float], query: str, top_k: int) -> Optional[List[Dict[str, Any]]]:
        self._ensure_matrix()
        if self._vectors_matrix is None or len(self._vectors_matrix) == 0:
            return None
        
        query_vec = np.array(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return []
        
        vector_scores = np.dot(self._vectors_matrix, query_vec) / (self._norms_array * query_norm + 1e-8)
        
        doc_ids = self._doc_ids if hasattr(self, '_doc_ids') else list(self.vectors.keys())
        weights = getattr(self, '_retrieval_weights', None) or {"vector": 0.5, "keyword": 0.3, "recency": 0.2}
        
        results = []
        for i, doc_id in enumerate(doc_ids):
            vector_score = float(vector_scores[i])
            keyword_score = self._bm25_keyword_score(query, self.texts[doc_id])
            metadata = self.metadatas.get(doc_id, {})
            timestamp = metadata.get("timestamp", time.time())
            hours_old = (time.time() - timestamp) / 3600
            time_weight = RetentionScorer.compute_recency_decay(hours_old)
            
            final_score = (weights.get("vector", 0.5) * vector_score +
                           weights.get("keyword", 0.3) * keyword_score +
                           weights.get("recency", 0.2) * time_weight)
            
            results.append({
                "id": doc_id,
                "vector_score": vector_score,
                "keyword_score": keyword_score,
                "time_weight": time_weight,
                "score": final_score,
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        
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
        
        return final_results
    
    def delete(self, doc_id: str) -> bool:
        if doc_id not in self.vectors:
            return False
        del self.vectors[doc_id]
        del self.texts[doc_id]
        del self.metadatas[doc_id]
        self._norms.pop(doc_id, None)
        self._matrix_dirty = True
        self._search_cache = LRUCache(50)
        self._pending_save = True
        return True
    
    def _bm25_keyword_score(self, query: str, text: str) -> float:
        if not query or not text:
            return 0.0
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        if not query_words:
            return 0.0
        matches = len(query_words & text_words)
        return matches / len(query_words)
    
    def _cosine_similarity(self, a: List[float], norm_a: float, b: List[float], norm_b: float = None) -> float:
        if norm_b is None:
            norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        return dot / (norm_a * norm_b)
    
    def get_stats(self) -> Dict[str, Any]:
        return {"total_docs": len(self.texts), "embedding_dim": self.embedding_dim}
    
    def flush(self) -> None:
        if self._pending_save and self.texts:
            self._save_to_disk()
            self._pending_save = False
            logger.info(f"向量存储已 flush ({len(self.texts)} 条)")
        elif self.texts:
            self._save_to_disk()
    
    def clear(self) -> None:
        self.flush()
        self.vectors.clear()
        self.texts.clear()
        self.metadatas.clear()
        self._norms.clear()
        self._vectors_matrix = None
        self._norms_array = None
        self._matrix_dirty = True
        self._embedding_cache = LRUCache(1000)
        self._search_cache = LRUCache(50)
        if self._persist_file.exists():
            self._persist_file.unlink()
        if hasattr(self, '_vectors_npy_file') and self._vectors_npy_file.exists():
            self._vectors_npy_file.unlink()
        if hasattr(self, '_vectors_meta_file') and self._vectors_meta_file.exists():
            self._vectors_meta_file.unlink()


class FileStorage:
    """文件系统存储"""
    
    def __init__(self, base_dir: str = "./memory") -> None:
        if not os.path.isabs(base_dir):
            base_dir = str(Path(base_dir).resolve())
        self.base_dir = Path(base_dir)
        self.daily_dir = self.base_dir / "daily"
        self.long_term_file = self.base_dir / "long_term.md"
        self.index_file = self.base_dir / "index.md"
        self.config_file = self.base_dir / "config.json"
        
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.index_file.exists():
            self._init_index()
    
    def _init_index(self) -> None:
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
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return self.daily_dir / f"{date}.md"
    
    def append_interaction(self, role: str, content: str, importance: int = 0, tags: List[str] = None) -> None:
        daily_file = self.get_daily_file()
        timestamp = datetime.now().strftime("%H:%M")
        star = "⭐" * importance if importance > 0 else ""
        tag_str = f" [{','.join(tags)}]" if tags else ""
        line = f"- **{timestamp}** [{role}]{star}{tag_str}: {content}\n"
        with open(daily_file, 'a', encoding='utf-8') as f:
            f.write(line)
    
    def read_daily(self, date: str = None) -> str:
        daily_file = self.get_daily_file(date)
        if not daily_file.exists():
            return ""
        return daily_file.read_text(encoding='utf-8')
    
    def list_daily_files(self) -> List[str]:
        if not self.daily_dir.exists():
            return []
        files = sorted(self.daily_dir.glob("*.md"), reverse=True)
        return [f.stem for f in files]
    
    def append_long_term(self, content: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        line = f"\n## {timestamp}\n\n{content}\n"
        with open(self.long_term_file, 'a', encoding='utf-8') as f:
            f.write(line)
    
    def read_long_term(self) -> str:
        if not self.long_term_file.exists():
            return ""
        return self.long_term_file.read_text(encoding='utf-8')
    
    def search_in_files(self, query: str, days: int = 7) -> List[Dict[str, Any]]:
        results = []
        query_lower = query.lower()
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_file = self.daily_dir / f"{date}.md"
            if not daily_file.exists():
                continue
            content = daily_file.read_text(encoding='utf-8')
            if query_lower in content.lower():
                lines = content.split('\n')
                matched = [l for l in lines if query_lower in l.lower()]
                if matched:
                    results.append({"date": date, "matches": matched[:5]})
        return results
    
    def export_all(self) -> str:
        output = f"# 记忆导出 - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        long_term = self.read_long_term()
        if long_term:
            output += "## 长期记忆\n\n" + long_term + "\n\n"
        for date in self.list_daily_files()[:30]:
            content = self.read_daily(date)
            if content:
                output += f"## {date}\n\n" + content + "\n\n"
        return output
    
    def import_backup(self, content: str) -> None:
        self.append_long_term("\n[导入备份]\n" + content)
    
    def clear(self) -> None:
        if self.daily_dir.exists():
            for f in self.daily_dir.glob("*.md"):
                f.unlink()
        if self.long_term_file.exists():
            self.long_term_file.unlink()
