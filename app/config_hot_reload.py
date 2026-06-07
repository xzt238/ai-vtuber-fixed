"""
配置热重载模块
支持配置文件监听、自动重载、变更通知
"""

import os
import asyncio
import hashlib
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ReloadEvent(Enum):
    """重载事件类型"""
    CONFIG_CHANGED = "config_changed"
    RELOAD_SUCCESS = "reload_success"
    RELOAD_FAILED = "reload_failed"
    WATCHER_STARTED = "watcher_started"
    WATCHER_STOPPED = "watcher_stopped"

@dataclass
class ConfigChange:
    """配置变更"""
    file_path: str
    old_hash: str
    new_hash: str
    timestamp: datetime = field(default_factory=datetime.now)

class ConfigHotReload:
    """配置热重载管理器"""
    
    def __init__(self, config_dir: str = ".", watch_interval: float = 1.0):
        self.config_dir = Path(config_dir)
        self.watch_interval = watch_interval
        
        # 监听的文件
        self.watched_files: Dict[str, str] = {}  # 文件路径 -> 内容哈希
        
        # 回调函数
        self.on_change_callbacks: List[Callable] = []
        self.on_reload_callbacks: List[Callable] = []
        self.on_error_callbacks: List[Callable] = []
        
        # 状态
        self.is_watching = False
        self.watch_task: Optional[asyncio.Task] = None
        
        # 变更历史
        self.change_history: List[ConfigChange] = []
        self.max_history = 100
        
        # 统计
        self.stats = {
            "total_watches": 0,
            "total_changes": 0,
            "total_reloads": 0,
            "total_errors": 0
        }
        
        logger.info("[ConfigHotReload] 初始化完成")
    
    def add_watch(self, file_path: str) -> bool:
        """添加监听文件"""
        try:
            path = Path(file_path)
            if not path.exists():
                logger.info(f"[ConfigHotReload] 文件不存在: {file_path}")
                return False
            
            # 计算初始哈希
            content_hash = self._calculate_hash(path)
            self.watched_files[str(path)] = content_hash
            
            logger.info(f"[ConfigHotReload] 添加监听: {file_path}")
            return True
            
        except Exception as e:
            logger.info(f"[ConfigHotReload] 添加监听失败: {e}")
            return False
    
    def remove_watch(self, file_path: str) -> bool:
        """移除监听文件"""
        path = str(Path(file_path))
        if path in self.watched_files:
            del self.watched_files[path]
            logger.info(f"[ConfigHotReload] 移除监听: {file_path}")
            return True
        return False
    
    def _calculate_hash(self, path: Path) -> str:
        """计算文件哈希"""
        try:
            with open(path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    async def start_watching(self):
        """开始监听"""
        if self.is_watching:
            return
        
        self.is_watching = True
        self.watch_task = asyncio.create_task(self._watch_loop())
        
        # 触发回调
        await self._notify_callbacks(ReloadEvent.WATCHER_STARTED, {})
        
        logger.info("[ConfigHotReload] 开始监听配置文件")
    
    async def stop_watching(self):
        """停止监听"""
        self.is_watching = False
        
        if self.watch_task:
            self.watch_task.cancel()
            try:
                await self.watch_task
            except asyncio.CancelledError:
                pass
        
        # 触发回调
        await self._notify_callbacks(ReloadEvent.WATCHER_STOPPED, {})
        
        logger.info("[ConfigHotReload] 停止监听配置文件")
    
    async def _watch_loop(self):
        """监听循环"""
        try:
            while self.is_watching:
                await self._check_changes()
                await asyncio.sleep(self.watch_interval)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.info(f"[ConfigHotReload] 监听循环错误: {e}")
    
    async def _check_changes(self):
        """检查文件变更"""
        self.stats["total_watches"] += 1
        
        for file_path, old_hash in list(self.watched_files.items()):
            try:
                path = Path(file_path)
                if not path.exists():
                    continue
                
                new_hash = self._calculate_hash(path)
                
                if new_hash != old_hash:
                    # 检测到变更
                    change = ConfigChange(
                        file_path=file_path,
                        old_hash=old_hash,
                        new_hash=new_hash
                    )
                    
                    # 记录变更
                    self.change_history.append(change)
                    if len(self.change_history) > self.max_history:
                        self.change_history.pop(0)
                    
                    # 更新哈希
                    self.watched_files[file_path] = new_hash
                    
                    # 更新统计
                    self.stats["total_changes"] += 1
                    
                    # 触发变更回调
                    await self._notify_callbacks(ReloadEvent.CONFIG_CHANGED, {
                        "file_path": file_path,
                        "change": change
                    })
                    
                    # 尝试重载
                    await self._reload_config(file_path)
                    
            except Exception as e:
                logger.info(f"[ConfigHotReload] 检查文件失败 {file_path}: {e}")
    
    async def _reload_config(self, file_path: str):
        """重载配置"""
        try:
            # 触发重载回调
            for callback in self.on_reload_callbacks:
                if asyncio.iscoroutinefunction(callback):
                    await callback(file_path)
                else:
                    callback(file_path)
            
            self.stats["total_reloads"] += 1
            
            # 触发成功回调
            await self._notify_callbacks(ReloadEvent.RELOAD_SUCCESS, {
                "file_path": file_path
            })
            
            logger.info(f"[ConfigHotReload] 配置已重载: {file_path}")
            
        except Exception as e:
            self.stats["total_errors"] += 1
            
            # 触发错误回调
            await self._notify_callbacks(ReloadEvent.RELOAD_FAILED, {
                "file_path": file_path,
                "error": str(e)
            })
            
            logger.info(f"[ConfigHotReload] 重载失败 {file_path}: {e}")
    
    async def _notify_callbacks(self, event: ReloadEvent, data: Dict[str, Any]):
        """通知回调函数"""
        for callback in self.on_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event, data)
                else:
                    callback(event, data)
            except Exception as e:
                logger.info(f"[ConfigHotReload] 回调执行失败: {e}")
    
    def on_change(self, callback: Callable):
        """注册变更回调"""
        self.on_change_callbacks.append(callback)
    
    def on_reload(self, callback: Callable):
        """注册重载回调"""
        self.on_reload_callbacks.append(callback)
    
    def on_error(self, callback: Callable):
        """注册错误回调"""
        self.on_error_callbacks.append(callback)
    
    def get_watched_files(self) -> List[str]:
        """获取监听的文件列表"""
        return list(self.watched_files.keys())
    
    def get_change_history(self, count: int = 50) -> List[ConfigChange]:
        """获取变更历史"""
        return self.change_history[-count:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "is_watching": self.is_watching,
            "watched_files": len(self.watched_files),
            "total_watches": self.stats["total_watches"],
            "total_changes": self.stats["total_changes"],
            "total_reloads": self.stats["total_reloads"],
            "total_errors": self.stats["total_errors"]
        }

# 全局实例
_hot_reload: Optional[ConfigHotReload] = None

def get_config_hot_reload(config_dir: str = None) -> ConfigHotReload:
    """获取配置热重载实例"""
    global _hot_reload
    if _hot_reload is None:
        _hot_reload = ConfigHotReload(config_dir or ".")
    return _hot_reload
