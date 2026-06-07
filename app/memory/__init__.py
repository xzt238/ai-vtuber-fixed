"""
=====================================
RAG 记忆系统模块 - v3.0 全面重构
=====================================

v3.0 改进点 (对标 Mem0/Letta/Zep):
- 重要性评分: 多维梯度评分(长度/问题/个人信息/情感/知识深度), 不再只有0/4/5
- 摘要压缩: LLM 语义摘要替代硬截断, 降级到规则摘要
- 事实提取: 规则+LLM 双模式, 独立保存用户偏好/事实
- 向量库: 降低入库阈值(>=3), 添加去重, 确保数据落盘
- 遗忘衰减: 降低衰减速度, 新记忆保护期, 重要性时间衰减保护
- 记忆去重: 向量相似度去重
- 自动标签: 基于关键词的领域分类
- 记忆重整: 跨层整合优化

子模块:
- memory.models: MemoryItem, FactItem 数据类
- memory.scoring: RetentionScorer, ImportanceScorer 评分器
- memory.extraction: FactExtractor, AutoTagger 提取器
- memory.storage: LRUCache, VectorStore, FileStorage 存储层
- memory.summary: SummaryGenerator 摘要生成器

作者: 咕咕嘎嘎
日期: 2026-04-28
"""

import os
import json
import time
import threading
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import asdict

logger = logging.getLogger("memory")

# 从子模块导入所有公开类（保持向后兼容）
from memory.models import MemoryItem, FactItem
from memory.scoring import RetentionScorer, ImportanceScorer
from memory.extraction import FactExtractor, AutoTagger
from memory.storage import LRUCache, VectorStore, FileStorage
from memory.summary import SummaryGenerator


class MemorySystem:
    """
    记忆系统 v3.0 — 全面重构
    
    改进点:
    - 多维梯度评分 (不再只有0/4/5)
    - LLM 语义摘要 (替代硬截断)
    - 事实提取 (独立保存用户偏好/信息)
    - 向量库去重 + 降低入库阈值
    - 遗忘衰减调优 (更慢衰减 + 保护期)
    - 自动标签
    - 记忆重整 (跨层整合)
    - 记忆管理 (删除/编辑/标重要)
    """
    
    def __init__(self, config: Dict[str, Any] = None) -> None:
        """初始化记忆系统"""
        self.config = config or {}
        self.storage_dir = self.config.get("storage_dir", "./memory")
        if not os.path.isabs(self.storage_dir):
            from app.shared_config import PROJECT_DIR
            self.storage_dir = Path(PROJECT_DIR) / self.storage_dir
            self.storage_dir = os.path.normpath(self.storage_dir)
        
        self.working_memory_limit = self.config.get("working_memory_limit", 30)
        self.summarize_threshold = self.config.get("summarize_threshold", 20)
        self.summarize_batch = self.config.get("summarize_batch", 5)
        self.episodic_memory_limit = self.config.get("episodic_memory_limit", 200)
        
        self._llm_chat_func = None
        
        RetentionScorer.DECAY_LAMBDA = self.config.get("decay_lambda", 0.005)
        RetentionScorer.RETENTION_THRESHOLD = self.config.get("forgetting_threshold", 0.15)
        RetentionScorer.GRACE_PERIOD_HOURS = self.config.get("grace_period_hours", 12.0)
        
        vs_config = dict(self.config)
        vs_config["storage_dir"] = Path(self.storage_dir) / "vectors"
        vs_config["dedup_threshold"] = self.config.get("dedup_threshold", 0.95)
        self.vector_store = VectorStore(vs_config)
        
        self.file_storage = FileStorage(self.storage_dir)
        
        self.working_memory: List[MemoryItem] = []
        self.episodic_memory: List[MemoryItem] = []
        self._memory_lock = threading.Lock()

        self.facts: List[FactItem] = []
        self.forgotten_count = 0
        self.auto_store = self.config.get("auto_store", True)
        
        self._persist_dir = Path(self.storage_dir) / "state"
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._working_memory_file = self._persist_dir / "working_memory.json"
        self._episodic_memory_file = self._persist_dir / "episodic_memory.json"
        self._forgotten_count_file = self._persist_dir / "forgotten_count.json"
        self._facts_file = self._persist_dir / "facts.json"
        
        self._load_memory_state()
        
        logger.info(f"记忆系统 v3.0 初始化完成")
        logger.info(f"存储目录: {self.storage_dir}")
        logger.info(f" 工作记忆: {len(self.working_memory)}条, 情景记忆: {len(self.episodic_memory)}条, "
              f"语义记忆: {self.vector_store.get_stats()['total_docs']}条, 事实: {len(self.facts)}条")
        logger.info(f" 工作记忆上限: {self.working_memory_limit}, 摘要阈值: {self.summarize_threshold}, "
              f"遗忘阈值: {RetentionScorer.RETENTION_THRESHOLD}")
        
        self._flush_timer = None
        self._start_flush_timer()
        self._embedding_warmed = False
    
    def set_llm_callback(self, chat_func) -> None:
        """设置 LLM 回调函数"""
        self._llm_chat_func = chat_func
        logger.info(f" [记忆系统] LLM 回调已设置")
    
    def _warmup_embedding(self) -> None:
        """后台预热 embedding 模型"""
        if self._embedding_warmed:
            return
        
        def _warmup_worker() -> None:
            """内部方法"""
            try:
                _ = self.vector_store.get_embedding("warmup")
                self._embedding_warmed = True
                logger.info(f" [记忆系统] Embedding 模型预热完成")
            except Exception as e:
                logger.info(f" [记忆系统] Embedding 模型预热失败(不影响使用): {e}")
        
        warmup_thread = threading.Thread(target=_warmup_worker, daemon=True)
        warmup_thread.start()
    
    def _start_flush_timer(self) -> None:
        """内部方法"""
        def _flush_worker() -> None:
            """内部方法"""
            try:
                self._save_memory_state()
            except Exception as e:
                pass
            finally:
                if self._flush_timer is not None:
                    self._flush_timer = threading.Timer(30.0, _flush_worker)
                    self._flush_timer.daemon = True
                    self._flush_timer.start()
        
        self._flush_timer = threading.Timer(30.0, _flush_worker)
        self._flush_timer.daemon = True
        self._flush_timer.start()
    
    def _load_memory_state(self) -> None:
        """从磁盘恢复"""
        if self._working_memory_file.exists():
            try:
                with open(self._working_memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.working_memory = [self._dict_to_memory_item(item) for item in data]
                logger.info(f" [记忆] 恢复工作记忆: {len(self.working_memory)}条")
            except Exception as e:
                logger.info(f" [记忆] 恢复工作记忆失败: {e}")
        
        if self._episodic_memory_file.exists():
            try:
                with open(self._episodic_memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.episodic_memory = [self._dict_to_memory_item(item) for item in data]
                logger.info(f" [记忆] 恢复情景记忆: {len(self.episodic_memory)}条")
            except Exception as e:
                logger.info(f" [记忆] 恢复情景记忆失败: {e}")
        
        if self._forgotten_count_file.exists():
            try:
                with open(self._forgotten_count_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.forgotten_count = data.get("count", 0)
            except Exception as e:
                pass
        
        if self._facts_file.exists():
            try:
                with open(self._facts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.facts = [self._dict_to_fact_item(item) for item in data]
                logger.info(f" [记忆] 恢复事实库: {len(self.facts)}条")
            except Exception as e:
                logger.info(f" [记忆] 恢复事实库失败: {e}")
    
    @staticmethod
    def _dict_to_memory_item(d: Dict[str, Any]) -> MemoryItem:
        """将字典转为 MemoryItem，兼容旧版本缺失字段"""
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
            facts=d.get("facts", []),
            summary_text=d.get("summary_text", ""),
        )
    
    @staticmethod
    def _dict_to_fact_item(d: Dict[str, Any]) -> FactItem:
        """将字典转为 FactItem"""
        return FactItem(
            content=d.get("content", ""),
            source=d.get("source", "key_fact"),
            confidence=d.get("confidence", 0.5),
            timestamp=d.get("timestamp", time.time()),
            access_count=d.get("access_count", 1),
            tags=d.get("tags", []),
        )
    
    def _save_memory_state(self) -> None:
        """保存到磁盘（原子写入）"""
        try:
            with self._memory_lock:
                wm_snapshot = [asdict(item) for item in self.working_memory]
                em_snapshot = [asdict(item) for item in self.episodic_memory]
            self._atomic_write_json(self._working_memory_file, wm_snapshot)
            self._atomic_write_json(self._episodic_memory_file, em_snapshot)
            self._atomic_write_json(self._forgotten_count_file, {"count": self.forgotten_count})
            self._atomic_write_json(self._facts_file, [asdict(item) for item in self.facts])
        except Exception as e:
            logger.info(f" [记忆] 保存状态失败: {e}")
    
    def _atomic_write_json(self, target_path: Path, data: Any) -> None:
        """内部方法"""
        tmp_path = target_path.with_suffix('.tmp')
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, target_path)
    
    def flush(self) -> None:
        """强制将所有未持久化的记忆数据写入磁盘"""
        if self._flush_timer is not None:
            self._flush_timer.cancel()
            self._flush_timer = None
        self._save_memory_state()
        self.vector_store.flush()
        logger.info(f"[Memory] 全部记忆已 flush (工作:{len(self.working_memory)} 情景:{len(self.episodic_memory)} "
              f"语义:{self.vector_store.get_stats()['total_docs']} 事实:{len(self.facts)})")
    
    def add_interaction(self, role: str, content: str, importance: int = None) -> None:
        """添加对话记录"""
        if importance is None:
            importance = ImportanceScorer.score(role, content)
        
        tags = AutoTagger.tag(content)
        
        extracted_facts = []
        if role == "user":
            extracted_facts = FactExtractor.extract_facts(role, content, importance)
            if not extracted_facts and len(content) > 50 and importance >= 2 and self._llm_chat_func:
                extracted_facts = FactExtractor.extract_with_llm(content, self._llm_chat_func)
            
            for fact in extracted_facts:
                self._merge_fact(fact)
        
        item = MemoryItem(
            role=role,
            content=content,
            timestamp=time.time(),
            importance=importance,
            tags=tags,
            facts=[f.content for f in extracted_facts],
        )
        
        with self._memory_lock:
            self.working_memory.append(item)
            if len(self.working_memory) > self.summarize_threshold:
                self._compress_early_memory()
        
        if ImportanceScorer.is_important(importance):
            doc_id = self.vector_store.add(
                f"{role}: {content}",
                {
                    "timestamp": item.timestamp,
                    "importance": importance,
                    "role": role,
                    "is_summary": False,
                    "tags": tags,
                }
            )
            if ImportanceScorer.is_critical(importance):
                self.file_storage.append_long_term(
                    f"[{role}] 重要性:{importance} {tags} - {content}"
                )
        
        self._forgetting_sweep()
        
        if self.auto_store:
            self.file_storage.append_interaction(role, content, importance, tags)
        
        if len(self.working_memory) % 5 == 0:
            self._save_memory_state()
    
    def _compress_early_memory(self) -> None:
        """摘要压缩 v2 — LLM 语义摘要 + 规则降级"""
        if len(self.working_memory) <= self.summarize_threshold:
            return
        
        batch = self.working_memory[:self.summarize_batch]
        self.working_memory = self.working_memory[self.summarize_batch:]
        
        summary_text = SummaryGenerator.generate_summary(batch, self._llm_chat_func)
        
        all_facts = []
        for item in batch:
            all_facts.extend(item.facts)
        
        summary_item = MemoryItem(
            role="system",
            content=summary_text,
            timestamp=batch[-1].timestamp,
            importance=max(item.importance for item in batch),
            is_summary=True,
            summary_text=summary_text,
            facts=list(set(all_facts)),
            tags=AutoTagger.tag(summary_text),
        )

        self.episodic_memory.append(summary_item)

        if len(self.episodic_memory) > self.episodic_memory_limit:
            self.episodic_memory.sort(key=lambda x: x.timestamp)
            excess = len(self.episodic_memory) - self.episodic_memory_limit
            self.episodic_memory = self.episodic_memory[excess:]
            self.forgotten_count += excess
            logger.info(f" 情景记忆裁剪: 淘汰 {excess} 条最旧记忆 (上限: {self.episodic_memory_limit})")

        if summary_item.importance >= 3:
            self.vector_store.add(
                f"[摘要] {summary_text}",
                {
                    "timestamp": summary_item.timestamp,
                    "importance": summary_item.importance,
                    "is_summary": True,
                    "role": "system",
                    "tags": summary_item.tags,
                }
            )
        
        logger.info(f" 记忆压缩: {len(batch)}条 → 1条摘要 (剩余工作记忆: {len(self.working_memory)})")
        self._save_memory_state()
    
    def _forgetting_sweep(self) -> None:
        """遗忘扫描 v2 — 跳过保护期内的新记忆"""
        forgotten = 0
        now = time.time()

        survivors = []
        for item in self.episodic_memory:
            hours_old = (now - item.timestamp) / 3600
            if RetentionScorer.is_in_grace_period(hours_old):
                survivors.append(item)
                continue
            if item.should_forget():
                forgotten += 1
            else:
                survivors.append(item)
        self.episodic_memory = survivors

        if len(self.episodic_memory) > self.episodic_memory_limit:
            excess = len(self.episodic_memory) - self.episodic_memory_limit
            self.episodic_memory.sort(key=lambda x: x.timestamp)
            self.episodic_memory = self.episodic_memory[excess:]
            forgotten += excess

        if forgotten > 0:
            self.forgotten_count += forgotten
            logger.info(f" 遗忘扫描: 清理了 {forgotten} 条过期情景记忆 (累计: {self.forgotten_count})")
        return forgotten
    
    def _merge_fact(self, new_fact: FactItem) -> None:
        """合并事实(去重 + 更新)"""
        for existing in self.facts:
            if self._text_similarity(existing.content, new_fact.content) > 0.7:
                existing.confidence = max(existing.confidence, new_fact.confidence)
                existing.timestamp = new_fact.timestamp
                existing.access_count += 1
                for tag in new_fact.tags:
                    if tag not in existing.tags:
                        existing.tags.append(tag)
                return
        self.facts.append(new_fact)
    
    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        """简单文本相似度(字符级 Jaccard)"""
        if not a or not b:
            return 0.0
        set_a = set(a)
        set_b = set(b)
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """混合检索 v2: 工作记忆 + 情景记忆 + 向量库 + 事实库"""
        results = []
        query_lower = query.lower()
        
        for i, item in enumerate(self.working_memory):
            if query_lower in item.content.lower():
                item.touch()
                results.append({
                    "layer": "working",
                    "index": i,
                    "text": item.content,
                    "role": item.role,
                    "importance": item.importance,
                    "score": 1.0,
                    "is_summary": item.is_summary,
                    "tags": item.tags,
                })
        
        for i, fact in enumerate(self.facts):
            if query_lower in fact.content.lower():
                fact.access_count += 1
                results.append({
                    "layer": "fact",
                    "index": i,
                    "text": fact.content,
                    "role": "fact",
                    "importance": 4,
                    "score": 0.9,
                    "source": fact.source,
                    "tags": fact.tags,
                })
        
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
                    "tags": item.tags,
                })
        
        vector_results = self.vector_store.search(query, top_k)
        for vr in vector_results:
            results.append({
                "layer": "semantic",
                "text": vr["text"],
                "score": vr["score"] * 0.8,
                "vector_score": vr.get("vector_score", 0),
                "keyword_score": vr.get("keyword_score", 0),
                "time_weight": vr.get("time_weight", 0),
                "is_summary": vr["metadata"].get("is_summary", False),
                "tags": vr["metadata"].get("tags", []),
            })
        
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:top_k]
    
    def delete_memory(self, index: int, layer: str = "working") -> bool:
        """删除指定记忆"""
        try:
            if layer == "working" and 0 <= index < len(self.working_memory):
                self.working_memory.pop(index)
                self._save_memory_state()
                return True
            elif layer == "episodic" and 0 <= index < len(self.episodic_memory):
                self.episodic_memory.pop(index)
                self._save_memory_state()
                return True
            elif layer == "fact" and 0 <= index < len(self.facts):
                self.facts.pop(index)
                self._save_memory_state()
                return True
        except Exception as e:
            logger.info(f" [记忆] 删除失败: {e}")
        return False
    
    def edit_memory(self, index: int, content: str, layer: str = "working") -> bool:
        """编辑指定记忆内容"""
        try:
            if layer == "working" and 0 <= index < len(self.working_memory):
                self.working_memory[index].content = content
                self.working_memory[index].tags = AutoTagger.tag(content)
                self._save_memory_state()
                return True
            elif layer == "episodic" and 0 <= index < len(self.episodic_memory):
                self.episodic_memory[index].content = content
                self.episodic_memory[index].tags = AutoTagger.tag(content)
                self._save_memory_state()
                return True
        except Exception as e:
            logger.info(f" [记忆] 编辑失败: {e}")
        return False
    
    def set_importance(self, index: int, importance: int, layer: str = "working") -> bool:
        """手动设置重要性"""
        try:
            if layer == "working" and 0 <= index < len(self.working_memory):
                self.working_memory[index].importance = importance
                if ImportanceScorer.is_important(importance):
                    item = self.working_memory[index]
                    self.vector_store.add(
                        f"{item.role}: {item.content}",
                        {"timestamp": item.timestamp, "importance": importance, "role": item.role}
                    )
                self._save_memory_state()
                return True
            elif layer == "episodic" and 0 <= index < len(self.episodic_memory):
                self.episodic_memory[index].importance = importance
                self._save_memory_state()
                return True
        except Exception as e:
            logger.info(f" [记忆] 设置重要性失败: {e}")
        return False
    
    def delete_fact(self, index: int) -> bool:
        """删除指定事实"""
        if 0 <= index < len(self.facts):
            self.facts.pop(index)
            self._save_memory_state()
            return True
        return False
    
    def consolidate(self) -> Dict[str, Any]:
        """记忆重整 — 跨层整合优化"""
        merged_count = 0
        promoted_count = 0
        
        i = 0
        while i < len(self.episodic_memory) - 1:
            item_a = self.episodic_memory[i]
            j = i + 1
            while j < len(self.episodic_memory):
                item_b = self.episodic_memory[j]
                if (item_a.is_summary and item_b.is_summary and
                    self._text_similarity(item_a.content, item_b.content) > 0.6):
                    if item_a.importance >= item_b.importance:
                        item_a.importance = max(item_a.importance, item_b.importance)
                        item_a.connectivity += item_b.connectivity + 1
                        self.episodic_memory.pop(j)
                        merged_count += 1
                    else:
                        item_b.importance = max(item_a.importance, item_b.importance)
                        item_b.connectivity += item_a.connectivity + 1
                        self.episodic_memory.pop(i)
                        merged_count += 1
                        break
                else:
                    j += 1
            i += 1
        
        for item in self.episodic_memory:
            if item.importance >= 4 and not item.is_forgotten:
                retention = item.get_retention_score()
                if retention > 0.5:
                    self.file_storage.append_long_term(
                        f"[情景提升] {item.content[:200]}"
                    )
                    promoted_count += 1
        
        before = len(self.episodic_memory)
        self.episodic_memory = [m for m in self.episodic_memory if not m.is_forgotten]
        cleaned = before - len(self.episodic_memory)
        
        self._save_memory_state()
        self.vector_store.flush()
        
        result = {
            "merged": merged_count,
            "promoted": promoted_count,
            "cleaned": cleaned,
            "working": len(self.working_memory),
            "episodic": len(self.episodic_memory),
            "semantic": self.vector_store.get_stats()["total_docs"],
            "facts": len(self.facts),
        }
        logger.info(f" [记忆重整] 合并:{merged_count} 提升:{promoted_count} 清理:{cleaned}")
        return result
    
    def prefetch(self, context: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """预加载相关记忆"""
        return self.search(context, top_k)
    
    def get_working_memory(self) -> List[Dict[str, Any]]:
        """Get working memory"""
        return [asdict(item) for item in self.working_memory]
    
    def get_episodic_memory(self) -> List[Dict[str, Any]]:
        """Get episodic memory"""
        return [asdict(item) for item in self.episodic_memory]
    
    def get_facts(self, source: str = None) -> List[Dict[str, Any]]:
        """获取事实列表, 可按来源过滤"""
        if source:
            return [asdict(f) for f in self.facts if f.source == source]
        return [asdict(f) for f in self.facts]
    
    def search_by_time(self, days: int = 7) -> List[Dict[str, Any]]:
        """Search by time"""
        return self.file_storage.search_in_files("", days)
    
    def search_by_role(self, role: str) -> List[Dict[str, Any]]:
        """Search by role"""
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
            tags_str = f" [{','.join(item.tags)}]" if item.tags else ""
            summary += f"- {tag}[{item.role}]{star}{tags_str}: {content}\n"
        
        if self.episodic_memory:
            summary += "\n[情景记忆摘要]\n"
            for item in self.episodic_memory[-5:]:
                if item.is_summary:
                    summary += f"- {item.content[:80]}\n"
        
        if self.facts:
            summary += "\n[已知事实]\n"
            for fact in self.facts[-10:]:
                summary += f"- [{fact.source}] {fact.content}\n"
        
        return summary
    
    def get_stats(self) -> Dict[str, Any]:
        """Get stats"""
        retention_scores = [m.get_retention_score() for m in self.episodic_memory]
        avg_retention = sum(retention_scores) / len(retention_scores) if retention_scores else 0
        
        importance_dist = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for m in self.working_memory:
            if m.importance in importance_dist:
                importance_dist[m.importance] += 1
        
        return {
            "working_memory": len(self.working_memory),
            "episodic_memory": len(self.episodic_memory),
            "semantic_memory": self.vector_store.get_stats()["total_docs"],
            "forgotten_count": self.forgotten_count,
            "avg_retention_score": round(avg_retention, 3),
            "facts_count": len(self.facts),
            "importance_distribution": importance_dist,
            "storage_dir": self.storage_dir,
            "version": "v3.0",
            "persistent": True,
        }
    
    def export(self) -> str:
        """Export"""
        return self.file_storage.export_all()
    
    def import_backup(self, content: str) -> None:
        """Import backup"""
        return self.file_storage.import_backup(content)
    
    def clear_all(self) -> None:
        """Clear all"""
        self.working_memory.clear()
        self.episodic_memory.clear()
        self.facts.clear()
        self.vector_store.flush()
        self.vector_store.clear()
        self.file_storage.clear()
        self.forgotten_count = 0
        for f in [self._working_memory_file, self._episodic_memory_file, 
                  self._forgotten_count_file, self._facts_file]:
            if f.exists():
                f.unlink()
        logger.info(" 所有记忆已清空")
    
    def get_decay_preview(self) -> Dict[str, Any]:
        """Get decay preview"""
        return {
            "now": RetentionScorer.get_decay_stats(0),
            "1day": RetentionScorer.get_decay_stats(24),
            "7days": RetentionScorer.get_decay_stats(24 * 7),
            "30days": RetentionScorer.get_decay_stats(24 * 30),
            "grace_period_hours": RetentionScorer.GRACE_PERIOD_HOURS,
        }
