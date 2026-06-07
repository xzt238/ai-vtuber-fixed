"""
启动优化模块
提供懒加载、预加载、启动时间优化等功能
"""

import asyncio
import time
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

class LoadPriority(Enum):
    """加载优先级"""
    CRITICAL = 0    # 关键模块，必须立即加载
    HIGH = 1        # 高优先级，尽快加载
    MEDIUM = 2      # 中优先级，空闲时加载
    LOW = 3         # 低优先级，延迟加载

@dataclass
class ModuleInfo:
    """模块信息"""
    name: str
    loader: Callable
    priority: LoadPriority = LoadPriority.MEDIUM
    dependencies: List[str] = field(default_factory=list)
    loaded: bool = False
    load_time_ms: float = 0
    error: Optional[Exception] = None

class StartupOptimizer:
    """启动优化器"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 模块注册表
        self.modules: Dict[str, ModuleInfo] = {}
        
        # 加载队列
        self.load_queues: Dict[LoadPriority, List[str]] = {
            priority: [] for priority in LoadPriority
        }
        
        # 状态
        self.is_loading = False
        self.start_time: Optional[float] = None
        
        # 统计
        self.stats = {
            "total_modules": 0,
            "loaded_modules": 0,
            "failed_modules": 0,
            "total_load_time_ms": 0
        }
        
        # 回调
        self.on_module_loaded: List[Callable] = []
        self.on_all_loaded: List[Callable] = []
        
        logger.info("[StartupOptimizer] 初始化完成")
    
    def register_module(self, name: str, loader: Callable, 
                       priority: LoadPriority = LoadPriority.MEDIUM,
                       dependencies: List[str] = None):
        """注册模块"""
        module = ModuleInfo(
            name=name,
            loader=loader,
            priority=priority,
            dependencies=dependencies or []
        )
        
        self.modules[name] = module
        self.load_queues[priority].append(name)
        self.stats["total_modules"] += 1
        
        logger.info(f"[StartupOptimizer] 注册模块: {name} (优先级: {priority.name})")
    
    async def load_critical_modules(self) -> List[str]:
        """加载关键模块"""
        loaded = []
        
        for name in self.load_queues[LoadPriority.CRITICAL]:
            if await self._load_module(name):
                loaded.append(name)
        
        return loaded
    
    async def load_high_priority_modules(self) -> List[str]:
        """加载高优先级模块"""
        loaded = []
        
        for name in self.load_queues[LoadPriority.HIGH]:
            if await self._load_module(name):
                loaded.append(name)
        
        return loaded
    
    async def load_all_modules(self):
        """加载所有模块"""
        self.is_loading = True
        self.start_time = time.time()
        
        logger.info("\n" + "="*50)
        logger.info("开始加载模块...")
        logger.info("="*50 + "\n")
        
        # 按优先级顺序加载
        for priority in LoadPriority:
            queue = self.load_queues[priority]
            
            if not queue:
                continue
            
            logger.info(f"\n加载 {priority.name} 优先级模块 ({len(queue)} 个)...")
            
            # 并行加载同优先级的模块
            tasks = [self._load_module(name) for name in queue]
            await asyncio.gather(*tasks)
        
        # 计算总耗时
        total_time = (time.time() - self.start_time) * 1000
        self.stats["total_load_time_ms"] = total_time
        
        self.is_loading = False
        
        # 触发完成回调
        for callback in self.on_all_loaded:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.info(f"[StartupOptimizer] 完成回调失败: {e}")
        
        # 打印统计
        self._print_stats()
    
    async def _load_module(self, name: str) -> bool:
        """加载单个模块"""
        if name not in self.modules:
            logger.info(f"[StartupOptimizer] 模块不存在: {name}")
            return False
        
        module = self.modules[name]
        
        # 检查依赖
        for dep in module.dependencies:
            if dep in self.modules and not self.modules[dep].loaded:
                logger.info(f"[StartupOptimizer] 等待依赖: {dep}")
                await self._load_module(dep)
        
        # 加载模块
        start_time = time.time()
        
        try:
            if asyncio.iscoroutinefunction(module.loader):
                await module.loader()
            else:
                # 在线程池中运行同步加载器
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self.executor, module.loader)
            
            # 计算加载时间
            load_time = (time.time() - start_time) * 1000
            module.load_time_ms = load_time
            module.loaded = True
            
            # 更新统计
            self.stats["loaded_modules"] += 1
            self.stats["total_load_time_ms"] += load_time
            
            logger.info(f"✅ {name} ({load_time:.1f}ms)")
            
            # 触发回调
            for callback in self.on_module_loaded:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(name, module)
                    else:
                        callback(name, module)
                except Exception as e:
                    logger.info(f"[StartupOptimizer] 加载回调失败: {e}")
            
            return True
            
        except Exception as e:
            module.error = e
            self.stats["failed_modules"] += 1
            logger.info(f"❌ {name}: {e}")
            return False
    
    def _print_stats(self):
        """打印统计信息"""
        logger.info("\n" + "="*50)
        logger.info("模块加载完成")
        logger.info("="*50)
        logger.info(f"总模块数: {self.stats['total_modules']}")
        logger.info(f"已加载: {self.stats['loaded_modules']}")
        logger.info(f"失败: {self.stats['failed_modules']}")
        logger.info(f"总耗时: {self.stats['total_load_time_ms']:.1f}ms")
        logger.info("="*50 + "\n")
    
    def get_module(self, name: str) -> Optional[ModuleInfo]:
        """获取模块信息"""
        return self.modules.get(name)
    
    def is_module_loaded(self, name: str) -> bool:
        """检查模块是否已加载"""
        module = self.modules.get(name)
        return module.loaded if module else False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_modules": self.stats["total_modules"],
            "loaded_modules": self.stats["loaded_modules"],
            "failed_modules": self.stats["failed_modules"],
            "total_load_time_ms": self.stats["total_load_time_ms"],
            "is_loading": self.is_loading
        }
    
    def generate_report(self) -> str:
        """生成启动报告"""
        report = []
        report.append("# 启动优化报告")
        report.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 统计信息
        report.append("\n## 统计信息\n")
        report.append(f"- 总模块数: {self.stats['total_modules']}")
        report.append(f"- 已加载: {self.stats['loaded_modules']}")
        report.append(f"- 失败: {self.stats['failed_modules']}")
        report.append(f"- 总耗时: {self.stats['total_load_time_ms']:.1f}ms")
        
        # 模块详情
        report.append("\n## 模块详情\n")
        report.append("| 模块 | 优先级 | 状态 | 耗时 |")
        report.append("|------|--------|------|------|")
        
        for name, module in sorted(self.modules.items(), key=lambda x: x[1].priority.value):
            status = "✅" if module.loaded else "❌"
            report.append(f"| {name} | {module.priority.name} | {status} | {module.load_time_ms:.1f}ms |")
        
        # 失败模块
        failed_modules = [m for m in self.modules.values() if m.error]
        if failed_modules:
            report.append("\n## 失败模块\n")
            for module in failed_modules:
                report.append(f"### {module.name}")
                report.append(f"- 错误: {str(module.error)}")
                report.append("")
        
        return "\n".join(report)

# 全局实例
_startup_optimizer: Optional[StartupOptimizer] = None

def get_startup_optimizer() -> StartupOptimizer:
    """获取启动优化器实例"""
    global _startup_optimizer
    if _startup_optimizer is None:
        _startup_optimizer = StartupOptimizer()
    return _startup_optimizer
