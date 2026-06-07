import logging
"""
用户交互优化模块
提供防抖、节流、操作队列、反馈优化等功能
"""

logger = logging.getLogger(__name__)

import asyncio
import time
from typing import Optional, Dict, Any, List, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from enum import Enum

class FeedbackType(Enum):
    """反馈类型"""
    VISUAL = "visual"      # 视觉反馈
    AUDIO = "audio"        # 音频反馈
    HAPTIC = "haptic"      # 触觉反馈
    TOAST = "toast"        # 提示消息

@dataclass
class UserAction:
    """用户操作"""
    action_id: str
    action_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    params: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0

@dataclass
class ActionFeedback:
    """操作反馈"""
    action_id: str
    feedback_type: FeedbackType
    message: str
    success: bool
    duration_ms: float = 0
    timestamp: datetime = field(default_factory=datetime.now)

class Debouncer:
    """防抖器"""
    
    def __init__(self, delay_ms: int = 300):
        self.delay_ms = delay_ms
        self.timers: Dict[str, asyncio.Task] = {}
    
    async def debounce(self, key: str, func: Callable[..., Awaitable], *args, **kwargs):
        """防抖执行"""
        # 取消之前的定时器
        if key in self.timers and not self.timers[key].done():
            self.timers[key].cancel()
            try:
                await self.timers[key]
            except asyncio.CancelledError:
                pass
        
        # 创建新的定时器
        async def delayed_execution():
            await asyncio.sleep(self.delay_ms / 1000)
            return await func(*args, **kwargs)
        
        self.timers[key] = asyncio.create_task(delayed_execution())
        return await self.timers[key]
    
    def cancel(self, key: str):
        """取消防抖"""
        if key in self.timers and not self.timers[key].done():
            self.timers[key].cancel()

class Throttler:
    """节流器"""
    
    def __init__(self, interval_ms: int = 100):
        self.interval_ms = interval_ms
        self.last_execution: Dict[str, float] = {}
    
    def should_execute(self, key: str) -> bool:
        """检查是否应该执行"""
        current_time = time.time() * 1000
        
        if key not in self.last_execution:
            self.last_execution[key] = current_time
            return True
        
        elapsed = current_time - self.last_execution[key]
        
        if elapsed >= self.interval_ms:
            self.last_execution[key] = current_time
            return True
        
        return False
    
    async def throttle(self, key: str, func: Callable[..., Awaitable], *args, **kwargs):
        """节流执行"""
        if self.should_execute(key):
            return await func(*args, **kwargs)
        return None

class ActionQueue:
    """操作队列"""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self.is_processing = False
        self.process_task: Optional[asyncio.Task] = None
        
        # 统计
        self.stats = {
            "total_enqueued": 0,
            "total_processed": 0,
            "total_dropped": 0
        }
    
    async def enqueue(self, action: UserAction) -> bool:
        """入队操作"""
        try:
            self.queue.put_nowait(action)
            self.stats["total_enqueued"] += 1
            return True
        except asyncio.QueueFull:
            self.stats["total_dropped"] += 1
            return False
    
    async def start_processing(self, handler: Callable[[UserAction], Awaitable]):
        """开始处理队列"""
        if self.is_processing:
            return
        
        self.is_processing = True
        
        async def process_loop():
            while self.is_processing:
                try:
                    action = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                    await handler(action)
                    self.stats["total_processed"] += 1
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.info(f"[ActionQueue] 处理失败: {e}")
        
        self.process_task = asyncio.create_task(process_loop())
    
    async def stop_processing(self):
        """停止处理队列"""
        self.is_processing = False
        
        if self.process_task:
            self.process_task.cancel()
            try:
                await self.process_task
            except asyncio.CancelledError:
                pass
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "queue_size": self.queue.qsize(),
            "is_processing": self.is_processing,
            "total_enqueued": self.stats["total_enqueued"],
            "total_processed": self.stats["total_processed"],
            "total_dropped": self.stats["total_dropped"]
        }

class FeedbackManager:
    """反馈管理器"""
    
    def __init__(self):
        self.feedback_history: deque = deque(maxlen=100)
        self.feedback_handlers: Dict[FeedbackType, List[Callable]] = {
            feedback_type: [] for feedback_type in FeedbackType
        }
    
    def register_handler(self, feedback_type: FeedbackType, handler: Callable):
        """注册反馈处理器"""
        self.feedback_handlers[feedback_type].append(handler)
    
    async def show_feedback(self, feedback: ActionFeedback):
        """显示反馈"""
        self.feedback_history.append(feedback)
        
        # 调用对应的处理器
        for handler in self.feedback_handlers.get(feedback.feedback_type, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(feedback)
                else:
                    handler(feedback)
            except Exception as e:
                logger.info(f"[FeedbackManager] 反馈处理失败: {e}")
    
    async def show_success(self, action_id: str, message: str):
        """显示成功反馈"""
        feedback = ActionFeedback(
            action_id=action_id,
            feedback_type=FeedbackType.TOAST,
            message=message,
            success=True
        )
        await self.show_feedback(feedback)
    
    async def show_error(self, action_id: str, message: str):
        """显示错误反馈"""
        feedback = ActionFeedback(
            action_id=action_id,
            feedback_type=FeedbackType.TOAST,
            message=message,
            success=False
        )
        await self.show_feedback(feedback)
    
    def get_history(self, count: int = 50) -> List[ActionFeedback]:
        """获取反馈历史"""
        return list(self.feedback_history)[-count:]

class InteractionOptimizer:
    """用户交互优化器"""
    
    def __init__(self):
        # 防抖器
        self.debouncer = Debouncer(delay_ms=300)
        
        # 节流器
        self.throttler = Throttler(interval_ms=100)
        
        # 操作队列
        self.action_queue = ActionQueue(max_size=100)
        
        # 反馈管理器
        self.feedback_manager = FeedbackManager()
        
        # 操作历史
        self.action_history: deque = deque(maxlen=1000)
        
        # 统计
        self.stats = {
            "total_actions": 0,
            "debounced_actions": 0,
            "throttled_actions": 0,
            "queued_actions": 0
        }
        
        logger.info("[InteractionOptimizer] 初始化完成")
    
    async def process_action(self, action: UserAction, 
                           handler: Callable[[UserAction], Awaitable]) -> Any:
        """处理用户操作"""
        self.stats["total_actions"] += 1
        self.action_history.append(action)
        
        # 入队
        if await self.action_queue.enqueue(action):
            self.stats["queued_actions"] += 1
        
        # 执行处理
        start_time = time.time()
        
        try:
            result = await handler(action)
            
            # 计算耗时
            duration_ms = (time.time() - start_time) * 1000
            
            # 显示成功反馈
            await self.feedback_manager.show_success(
                action.action_id,
                f"操作完成 ({duration_ms:.0f}ms)"
            )
            
            return result
            
        except Exception as e:
            # 显示错误反馈
            await self.feedback_manager.show_error(
                action.action_id,
                f"操作失败: {str(e)}"
            )
            raise
    
    async def debounced_action(self, key: str, action: UserAction,
                              handler: Callable[[UserAction], Awaitable]) -> Any:
        """防抖操作"""
        self.stats["debounced_actions"] += 1
        
        async def wrapped_handler():
            return await self.process_action(action, handler)
        
        return await self.debouncer.debounce(key, wrapped_handler)
    
    async def throttled_action(self, key: str, action: UserAction,
                              handler: Callable[[UserAction], Awaitable]) -> Any:
        """节流操作"""
        if not self.throttler.should_execute(key):
            self.stats["throttled_actions"] += 1
            return None
        
        return await self.process_action(action, handler)
    
    async def start_queue_processing(self, handler: Callable[[UserAction], Awaitable]):
        """开始队列处理"""
        await self.action_queue.start_processing(handler)
    
    async def stop_queue_processing(self):
        """停止队列处理"""
        await self.action_queue.stop_processing()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_actions": self.stats["total_actions"],
            "debounced_actions": self.stats["debounced_actions"],
            "throttled_actions": self.stats["throttled_actions"],
            "queued_actions": self.stats["queued_actions"],
            "queue_stats": self.action_queue.get_stats(),
            "action_history_size": len(self.action_history)
        }
    
    def get_recent_actions(self, count: int = 50) -> List[UserAction]:
        """获取最近的操作"""
        return list(self.action_history)[-count:]

# 全局实例
_interaction_optimizer: Optional[InteractionOptimizer] = None

def get_interaction_optimizer() -> InteractionOptimizer:
    """获取用户交互优化器实例"""
    global _interaction_optimizer
    if _interaction_optimizer is None:
        _interaction_optimizer = InteractionOptimizer()
    return _interaction_optimizer

# 便捷装饰器
def debounce(key: str, delay_ms: int = 300):
    """防抖装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            optimizer = get_interaction_optimizer()
            optimizer.debouncer.delay_ms = delay_ms
            return await optimizer.debouncer.debounce(key, func, *args, **kwargs)
        return wrapper
    return decorator

def throttle(key: str, interval_ms: int = 100):
    """节流装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            optimizer = get_interaction_optimizer()
            optimizer.throttler.interval_ms = interval_ms
            return await optimizer.throttler.throttle(key, func, *args, **kwargs)
        return wrapper
    return decorator
