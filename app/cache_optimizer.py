"""
缓存优化模块
提供内存缓存、磁盘缓存、LRU策略、缓存预热等功能
"""

import asyncio
import hashlib
import json
import pickle
import time
from typing import Optional, Dict, Any, List, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from collections import OrderedDict
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class CacheEntry(Generic[T]):
    """缓存条目"""
    key: str
    value: T
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl_seconds is None:
            return False
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds

class LRUCache:
    """LRU缓存"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # 统计
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_sets": 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key not in self.cache:
            self.stats["misses"] += 1
            return None
        
        entry = self.cache[key]
        
        # 检查是否过期
        if entry.is_expired:
            del self.cache[key]
            self.stats["misses"] += 1
            return None
        
        # 更新访问信息
        entry.accessed_at = datetime.now()
        entry.access_count += 1
        
        # 移动到末尾（最近使用）
        self.cache.move_to_end(key)
        
        self.stats["hits"] += 1
        return entry.value
    
    def set(self, key: str, value: Any, ttl: int = None):
        """设置缓存"""
        # 如果已存在，更新
        if key in self.cache:
            del self.cache[key]
        
        # 检查容量
        while len(self.cache) >= self.max_size:
            # 淘汰最久未使用的
            evicted_key, _ = self.cache.popitem(last=False)
            self.stats["evictions"] += 1
        
        # 创建新条目
        entry = CacheEntry(
            key=key,
            value=value,
            ttl_seconds=ttl or self.default_ttl
        )
        
        self.cache[key] = entry
        self.stats["total_sets"] += 1
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
    
    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": hit_rate,
            "evictions": self.stats["evictions"],
            "total_sets": self.stats["total_sets"]
        }

class DiskCache:
    """磁盘缓存"""
    
    def __init__(self, cache_dir: str = "./cache", max_size_mb: int = 100):
        self.cache_dir = Path(cache_dir)
        self.max_size_mb = max_size_mb
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 索引文件
        self.index_file = self.cache_dir / "index.json"
        self.index: Dict[str, Dict[str, Any]] = {}
        
        # 加载索引
        self._load_index()
        
        # 统计
        self.stats = {
            "hits": 0,
            "misses": 0,
            "writes": 0
        }
    
    def _load_index(self):
        """加载索引"""
        try:
            if self.index_file.exists():
                with open(self.index_file, "r", encoding="utf-8") as f:
                    self.index = json.load(f)
        except Exception:
            self.index = {}
    
    def _save_index(self):
        """保存索引"""
        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(self.index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.info(f"[DiskCache] 保存索引失败: {e}")
    
    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用MD5作为文件名
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key not in self.index:
            self.stats["misses"] += 1
            return None
        
        entry_info = self.index[key]
        cache_path = self._get_cache_path(key)
        
        # 检查文件是否存在
        if not cache_path.exists():
            del self.index[key]
            self._save_index()
            self.stats["misses"] += 1
            return None
        
        # 检查是否过期
        if "ttl_seconds" in entry_info and entry_info["ttl_seconds"]:
            created_at = datetime.fromisoformat(entry_info["created_at"])
            elapsed = (datetime.now() - created_at).total_seconds()
            if elapsed > entry_info["ttl_seconds"]:
                self.delete(key)
                self.stats["misses"] += 1
                return None
        
        try:
            with open(cache_path, "rb") as f:
                value = pickle.load(f)
            
            # 更新访问信息
            entry_info["accessed_at"] = datetime.now().isoformat()
            entry_info["access_count"] = entry_info.get("access_count", 0) + 1
            self._save_index()
            
            self.stats["hits"] += 1
            return value
            
        except Exception as e:
            logger.info(f"[DiskCache] 读取缓存失败: {e}")
            self.stats["misses"] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        """设置缓存"""
        cache_path = self._get_cache_path(key)
        
        try:
            # 保存值
            with open(cache_path, "wb") as f:
                pickle.dump(value, f)
            
            # 更新索引
            self.index[key] = {
                "created_at": datetime.now().isoformat(),
                "accessed_at": datetime.now().isoformat(),
                "access_count": 0,
                "ttl_seconds": ttl,
                "file_size": cache_path.stat().st_size
            }
            
            self._save_index()
            self.stats["writes"] += 1
            
            # 检查容量
            self._check_capacity()
            
        except Exception as e:
            logger.info(f"[DiskCache] 写入缓存失败: {e}")
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if key not in self.index:
            return False
        
        cache_path = self._get_cache_path(key)
        
        try:
            if cache_path.exists():
                cache_path.unlink()
            
            del self.index[key]
            self._save_index()
            return True
            
        except Exception:
            return False
    
    def clear(self):
        """清空缓存"""
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
        
        self.index.clear()
        self._save_index()
    
    def _check_capacity(self):
        """检查容量"""
        total_size = sum(
            entry.get("file_size", 0)
            for entry in self.index.values()
        )
        
        max_size_bytes = self.max_size_mb * 1024 * 1024
        
        if total_size > max_size_bytes:
            # 按访问时间排序，删除最久未访问的
            sorted_entries = sorted(
                self.index.items(),
                key=lambda x: x[1].get("accessed_at", "")
            )
            
            while total_size > max_size_bytes * 0.8 and sorted_entries:
                key, entry = sorted_entries.pop(0)
                total_size -= entry.get("file_size", 0)
                self.delete(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_size = sum(
            entry.get("file_size", 0)
            for entry in self.index.values()
        )
        
        return {
            "entries": len(self.index),
            "total_size_mb": total_size / (1024 * 1024),
            "max_size_mb": self.max_size_mb,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "writes": self.stats["writes"]
        }

class CacheOptimizer:
    """缓存优化器"""
    
    def __init__(self, memory_cache_size: int = 1000, 
                 disk_cache_dir: str = "./cache",
                 disk_cache_size_mb: int = 100):
        # 内存缓存
        self.memory_cache = LRUCache(max_size=memory_cache_size)
        
        # 磁盘缓存
        self.disk_cache = DiskCache(
            cache_dir=disk_cache_dir,
            max_size_mb=disk_cache_size_mb
        )
        
        # 缓存预热函数
        self.warmup_functions: List[Callable] = []
        
        logger.info("[CacheOptimizer] 初始化完成")
    
    async def get(self, key: str, loader: Callable = None) -> Optional[Any]:
        """获取缓存（多级）"""
        # 先查内存缓存
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        
        # 再查磁盘缓存
        value = self.disk_cache.get(key)
        if value is not None:
            # 提升到内存缓存
            self.memory_cache.set(key, value)
            return value
        
        # 如果有加载器，加载并缓存
        if loader:
            if asyncio.iscoroutinefunction(loader):
                value = await loader()
            else:
                value = loader()
            
            if value is not None:
                self.set(key, value)
            
            return value
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = None, 
            memory_only: bool = False):
        """设置缓存"""
        # 写入内存缓存
        self.memory_cache.set(key, value, ttl)
        
        # 写入磁盘缓存
        if not memory_only:
            self.disk_cache.set(key, value, ttl)
    
    def delete(self, key: str):
        """删除缓存"""
        self.memory_cache.delete(key)
        self.disk_cache.delete(key)
    
    def clear(self):
        """清空缓存"""
        self.memory_cache.clear()
        self.disk_cache.clear()
    
    async def warmup(self):
        """缓存预热"""
        logger.info("[CacheOptimizer] 开始缓存预热...")
        
        for func in self.warmup_functions:
            try:
                if asyncio.iscoroutinefunction(func):
                    await func()
                else:
                    func()
            except Exception as e:
                logger.info(f"[CacheOptimizer] 预热失败: {e}")
        
        logger.info("[CacheOptimizer] 缓存预热完成")
    
    def register_warmup(self, func: Callable):
        """注册预热函数"""
        self.warmup_functions.append(func)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "memory_cache": self.memory_cache.get_stats(),
            "disk_cache": self.disk_cache.get_stats()
        }
    
    def generate_report(self) -> str:
        """生成缓存报告"""
        stats = self.get_stats()
        
        report = []
        report.append("# 缓存优化报告")
        report.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 内存缓存
        report.append("\n## 内存缓存\n")
        mc = stats["memory_cache"]
        report.append(f"- 大小: {mc['size']}/{mc['max_size']}")
        report.append(f"- 命中率: {mc['hit_rate']:.1%}")
        report.append(f"- 命中: {mc['hits']}")
        report.append(f"- 未命中: {mc['misses']}")
        report.append(f"- 淘汰: {mc['evictions']}")
        
        # 磁盘缓存
        report.append("\n## 磁盘缓存\n")
        dc = stats["disk_cache"]
        report.append(f"- 条目数: {dc['entries']}")
        report.append(f"- 大小: {dc['total_size_mb']:.1f}MB / {dc['max_size_mb']}MB")
        report.append(f"- 命中: {dc['hits']}")
        report.append(f"- 未命中: {dc['misses']}")
        report.append(f"- 写入: {dc['writes']}")
        
        return "\n".join(report)

# 全局实例
_cache_optimizer: Optional[CacheOptimizer] = None

def get_cache_optimizer() -> CacheOptimizer:
    """获取缓存优化器实例"""
    global _cache_optimizer
    if _cache_optimizer is None:
        _cache_optimizer = CacheOptimizer()
    return _cache_optimizer

# 缓存装饰器
def cached(key_func: Callable = None, ttl: int = None, memory_only: bool = False):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            optimizer = get_cache_optimizer()
            
            # 尝试从缓存获取
            result = await optimizer.get(cache_key)
            if result is not None:
                return result
            
            # 执行函数
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # 缓存结果
            if result is not None:
                optimizer.set(cache_key, result, ttl, memory_only)
            
            return result
        
        return wrapper
    return decorator
