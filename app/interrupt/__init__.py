"""
语音打断处理器
实现用户打断AI说话的功能，支持asyncio.Task取消链
"""

import asyncio
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class InterruptReason(Enum):
    """打断原因"""
    USER_SPEECH = "user_speech"      # 用户说话
    MANUAL = "manual"                # 手动打断
    TIMEOUT = "timeout"              # 超时
    ERROR = "error"                  # 错误

@dataclass
class InterruptEvent:
    """打断事件"""
    timestamp: datetime = field(default_factory=datetime.now)
    heard_response: str = ""         # 已听到的回复
    reason: InterruptReason = InterruptReason.USER_SPEECH
    duration_ms: float = 0           # 打断延迟(毫秒)

class TaskRegistry:
    """任务注册表 - 管理可取消的异步任务"""
    
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.task_info: Dict[str, Dict[str, Any]] = {}
    
    def register(self, key: str, task: asyncio.Task, info: Dict[str, Any] = None):
        """注册任务"""
        self.tasks[key] = task
        self.task_info[key] = info or {}
        print(f"[TaskRegistry] 注册任务: {key}")
    
    def unregister(self, key: str):
        """注销任务"""
        if key in self.tasks:
            del self.tasks[key]
            if key in self.task_info:
                del self.task_info[key]
            print(f"[TaskRegistry] 注销任务: {key}")
    
    async def cancel(self, key: str) -> bool:
        """取消指定任务"""
        task = self.tasks.get(key)
        if task and not task.done():
            print(f"[TaskRegistry] 取消任务: {key}")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            self.unregister(key)
            return True
        return False
    
    async def cancel_all(self) -> int:
        """取消所有任务"""
        cancelled = 0
        for key in list(self.tasks.keys()):
            if await self.cancel(key):
                cancelled += 1
        print(f"[TaskRegistry] 取消了 {cancelled} 个任务")
        return cancelled
    
    def get_active_tasks(self) -> List[str]:
        """获取活跃任务列表"""
        return [key for key, task in self.tasks.items() if not task.done()]
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "total_tasks": len(self.tasks),
            "active_tasks": self.get_active_tasks(),
            "task_info": self.task_info
        }

class InterruptionHandler:
    """打断处理器 - 处理用户打断AI说话的逻辑"""
    
    def __init__(self):
        self.task_registry = TaskRegistry()
        self.is_interrupted = False
        self.current_response = ""
        self.interrupt_count = 0
        
        # 打断配置
        self.config = {
            "enabled": True,
            "auto_interrupt": True,           # 自动打断（检测到用户说话时）
            "save_heard_response": True,      # 保存已听到的回复
            "max_interrupt_history": 100,     # 最大打断历史记录数
            "interrupt_cooldown_ms": 500,     # 打断冷却时间(毫秒)
        }
        
        # 打断历史
        self.interrupt_history: List[InterruptEvent] = []
        
        # 最后一次打断时间
        self.last_interrupt_time: Optional[datetime] = None
        
        # 回调函数
        self.on_interrupt_start: Optional[Callable] = None
        self.on_interrupt_complete: Optional[Callable] = None
        self.on_heard_response_saved: Optional[Callable] = None
        
        print("[Interrupt] 打断处理器初始化完成")
    
    async def handle_interrupt(self, heard_response: str = "", 
                              reason: InterruptReason = InterruptReason.USER_SPEECH) -> bool:
        """处理打断"""
        if not self.config["enabled"]:
            return False
        
        # 检查冷却时间
        if self.last_interrupt_time:
            elapsed = (datetime.now() - self.last_interrupt_time).total_seconds() * 1000
            if elapsed < self.config["interrupt_cooldown_ms"]:
                print(f"[Interrupt] 打断冷却中，剩余 {self.config['interrupt_cooldown_ms'] - elapsed:.0f}ms")
                return False
        
        if self.is_interrupted:
            print("[Interrupt] 已经在处理打断中")
            return False
        
        self.is_interrupted = True
        start_time = datetime.now()
        
        print(f"[Interrupt] 检测到打断，原因: {reason.value}")
        if heard_response:
            print(f"[Interrupt] 已听到的回复: {heard_response[:100]}...")
        
        # 触发开始回调
        if self.on_interrupt_start:
            await self.on_interrupt_start()
        
        # 保存已听到的回复
        if self.config["save_heard_response"] and heard_response:
            self.current_response = heard_response
            if self.on_heard_response_saved:
                await self.on_heard_response_saved(heard_response)
        
        # 取消所有正在运行的任务
        cancelled_count = await self.task_registry.cancel_all()
        
        # 计算打断延迟
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        # 记录打断事件
        event = InterruptEvent(
            heard_response=heard_response,
            reason=reason,
            duration_ms=duration_ms
        )
        self.interrupt_history.append(event)
        self.interrupt_count += 1
        
        # 保持历史记录在限制内
        if len(self.interrupt_history) > self.config["max_interrupt_history"]:
            self.interrupt_history = self.interrupt_history[-self.config["max_interrupt_history"]:]
        
        # 更新最后打断时间
        self.last_interrupt_time = end_time
        
        # 重置状态
        self.is_interrupted = False
        
        # 触发完成回调
        if self.on_interrupt_complete:
            await self.on_interrupt_complete(event)
        
        print(f"[Interrupt] 打断处理完成，耗时 {duration_ms:.1f}ms，取消了 {cancelled_count} 个任务")
        return True
    
    def get_heard_response(self) -> str:
        """获取已听到的回复"""
        return self.current_response
    
    def clear_heard_response(self):
        """清除已听到的回复"""
        self.current_response = ""
    
    def get_interrupt_count(self) -> int:
        """获取打断次数"""
        return self.interrupt_count
    
    def get_recent_interrupts(self, count: int = 10) -> List[InterruptEvent]:
        """获取最近的打断事件"""
        return self.interrupt_history[-count:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        avg_duration = 0
        if self.interrupt_history:
            avg_duration = sum(e.duration_ms for e in self.interrupt_history) / len(self.interrupt_history)
        
        return {
            "enabled": self.config["enabled"],
            "is_interrupted": self.is_interrupted,
            "interrupt_count": self.interrupt_count,
            "avg_duration_ms": avg_duration,
            "current_response_length": len(self.current_response),
            "active_tasks": len(self.task_registry.get_active_tasks()),
            "history_size": len(self.interrupt_history)
        }
    
    def get_status(self) -> Dict[str, Any]:
        """获取完整状态"""
        return {
            "interrupt_handler": self.get_stats(),
            "task_registry": self.task_registry.get_status(),
            "config": self.config
        }
    
    def update_config(self, config: Dict[str, Any]):
        """更新配置"""
        self.config.update(config)
        print(f"[Interrupt] 配置已更新: {config}")

# 全局打断处理器实例
_interrupt_handler: Optional[InterruptionHandler] = None

def get_interrupt_handler() -> InterruptionHandler:
    """获取打断处理器实例"""
    global _interrupt_handler
    if _interrupt_handler is None:
        _interrupt_handler = InterruptionHandler()
    return _interrupt_handler
