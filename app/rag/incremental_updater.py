"""
RAG增量更新模块
支持文档增量更新、版本管理、变更追踪
"""

import hashlib
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ChangeType(Enum):
    """变更类型"""
    ADDED = "added"        # 新增
    MODIFIED = "modified"  # 修改
    DELETED = "deleted"    # 删除
    UNCHANGED = "unchanged"  # 未变更

@dataclass
class DocumentVersion:
    """文档版本"""
    doc_id: str
    content_hash: str
    version: int
    timestamp: datetime
    change_type: ChangeType
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UpdateResult:
    """更新结果"""
    added: int = 0
    modified: int = 0
    deleted: int = 0
    unchanged: int = 0
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0

class IncrementalUpdater:
    """增量更新器"""
    
    def __init__(self, storage_dir: str = "./memory/knowledge_base"):
        self.storage_dir = Path(storage_dir)
        self.versions_file = self.storage_dir / "versions.json"
        self.changelog_file = self.storage_dir / "changelog.json"
        
        # 版本历史
        self.versions: Dict[str, DocumentVersion] = {}
        
        # 变更日志
        self.changelog: List[Dict[str, Any]] = []
        
        # 加载历史
        self._load_versions()
        self._load_changelog()
        
        logger.info("[IncrementalUpdater] 初始化完成")
    
    def _load_versions(self):
        """加载版本历史"""
        try:
            if self.versions_file.exists():
                with open(self.versions_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for doc_id, version_data in data.items():
                        self.versions[doc_id] = DocumentVersion(
                            doc_id=version_data["doc_id"],
                            content_hash=version_data["content_hash"],
                            version=version_data["version"],
                            timestamp=datetime.fromisoformat(version_data["timestamp"]),
                            change_type=ChangeType(version_data["change_type"]),
                            metadata=version_data.get("metadata", {})
                        )
                logger.info(f"[IncrementalUpdater] 加载了 {len(self.versions)} 个文档版本")
        except Exception as e:
            logger.info(f"[IncrementalUpdater] 加载版本失败: {e}")
    
    def _save_versions(self):
        """保存版本历史"""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            
            data = {}
            for doc_id, version in self.versions.items():
                data[doc_id] = {
                    "doc_id": version.doc_id,
                    "content_hash": version.content_hash,
                    "version": version.version,
                    "timestamp": version.timestamp.isoformat(),
                    "change_type": version.change_type.value,
                    "metadata": version.metadata
                }
            
            with open(self.versions_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.info(f"[IncrementalUpdater] 保存版本失败: {e}")
    
    def _load_changelog(self):
        """加载变更日志"""
        try:
            if self.changelog_file.exists():
                with open(self.changelog_file, "r", encoding="utf-8") as f:
                    self.changelog = json.load(f)
                logger.info(f"[IncrementalUpdater] 加载了 {len(self.changelog)} 条变更日志")
        except Exception as e:
            logger.info(f"[IncrementalUpdater] 加载变更日志失败: {e}")
    
    def _save_changelog(self):
        """保存变更日志"""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            
            # 保持最近1000条记录
            if len(self.changelog) > 1000:
                self.changelog = self.changelog[-1000:]
            
            with open(self.changelog_file, "w", encoding="utf-8") as f:
                json.dump(self.changelog, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.info(f"[IncrementalUpdater] 保存变更日志失败: {e}")
    
    def _calculate_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def detect_changes(self, documents: Dict[str, str]) -> Dict[str, ChangeType]:
        """检测文档变更"""
        changes = {}
        
        # 检查新增和修改
        for doc_id, content in documents.items():
            content_hash = self._calculate_hash(content)
            
            if doc_id not in self.versions:
                changes[doc_id] = ChangeType.ADDED
            elif self.versions[doc_id].content_hash != content_hash:
                changes[doc_id] = ChangeType.MODIFIED
            else:
                changes[doc_id] = ChangeType.UNCHANGED
        
        # 检查删除
        for doc_id in self.versions:
            if doc_id not in documents:
                changes[doc_id] = ChangeType.DELETED
        
        return changes
    
    async def update(self, documents: Dict[str, str], 
                    metadata: Dict[str, Dict[str, Any]] = None) -> UpdateResult:
        """执行增量更新"""
        import time
        start_time = time.time()
        
        result = UpdateResult()
        metadata = metadata or {}
        
        # 检测变更
        changes = self.detect_changes(documents)
        
        # 处理变更
        for doc_id, change_type in changes.items():
            try:
                if change_type == ChangeType.ADDED:
                    # 新增文档
                    content = documents[doc_id]
                    content_hash = self._calculate_hash(content)
                    
                    version = DocumentVersion(
                        doc_id=doc_id,
                        content_hash=content_hash,
                        version=1,
                        timestamp=datetime.now(),
                        change_type=ChangeType.ADDED,
                        metadata=metadata.get(doc_id, {})
                    )
                    
                    self.versions[doc_id] = version
                    result.added += 1
                    
                    # 记录变更日志
                    self._log_change(doc_id, ChangeType.ADDED)
                
                elif change_type == ChangeType.MODIFIED:
                    # 修改文档
                    content = documents[doc_id]
                    content_hash = self._calculate_hash(content)
                    
                    old_version = self.versions[doc_id]
                    new_version = DocumentVersion(
                        doc_id=doc_id,
                        content_hash=content_hash,
                        version=old_version.version + 1,
                        timestamp=datetime.now(),
                        change_type=ChangeType.MODIFIED,
                        metadata=metadata.get(doc_id, {})
                    )
                    
                    self.versions[doc_id] = new_version
                    result.modified += 1
                    
                    # 记录变更日志
                    self._log_change(doc_id, ChangeType.MODIFIED)
                
                elif change_type == ChangeType.DELETED:
                    # 删除文档
                    del self.versions[doc_id]
                    result.deleted += 1
                    
                    # 记录变更日志
                    self._log_change(doc_id, ChangeType.DELETED)
                
                else:
                    result.unchanged += 1
                
            except Exception as e:
                result.errors.append(f"{doc_id}: {str(e)}")
        
        # 保存更新
        self._save_versions()
        self._save_changelog()
        
        # 计算耗时
        result.duration_ms = (time.time() - start_time) * 1000
        
        logger.info(f"[IncrementalUpdater] 更新完成: +{result.added} ~{result.modified} -{result.deleted} ={result.unchanged}")
        
        return result
    
    def _log_change(self, doc_id: str, change_type: ChangeType):
        """记录变更日志"""
        self.changelog.append({
            "doc_id": doc_id,
            "change_type": change_type.value,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_version(self, doc_id: str) -> Optional[DocumentVersion]:
        """获取文档版本"""
        return self.versions.get(doc_id)
    
    def get_all_versions(self) -> Dict[str, DocumentVersion]:
        """获取所有版本"""
        return self.versions.copy()
    
    def get_changelog(self, count: int = 100) -> List[Dict[str, Any]]:
        """获取变更日志"""
        return self.changelog[-count:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        change_counts = {}
        for version in self.versions.values():
            change_type = version.change_type.value
            change_counts[change_type] = change_counts.get(change_type, 0) + 1
        
        return {
            "total_documents": len(self.versions),
            "changelog_size": len(self.changelog),
            "change_counts": change_counts
        }
    
    def rollback(self, doc_id: str, target_version: int) -> bool:
        """回滚到指定版本"""
        # 这里需要配合文档存储实现
        # 暂时只更新版本记录
        if doc_id in self.versions:
            self.versions[doc_id].version = target_version
            self._save_versions()
            return True
        return False

# 全局实例
_updater: Optional[IncrementalUpdater] = None

def get_incremental_updater(storage_dir: str = None) -> IncrementalUpdater:
    """获取增量更新器实例"""
    global _updater
    if _updater is None:
        _updater = IncrementalUpdater(storage_dir or "./memory/knowledge_base")
    return _updater
