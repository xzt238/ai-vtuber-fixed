import logging
"""
性能监控模块
提供CPU、内存、GPU、响应时间等性能指标监控
"""

logger = logging.getLogger(__name__)

import asyncio
import time
import psutil
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque

@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: datetime = field(default_factory=datetime.now)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0
    gpu_percent: float = 0.0
    gpu_memory_used_mb: float = 0.0
    gpu_memory_total_mb: float = 0.0
    disk_io_read_mb: float = 0.0
    disk_io_write_mb: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0

@dataclass
class LatencyMetric:
    """延迟指标"""
    operation: str
    latency_ms: float
    timestamp: datetime = field(default_factory=datetime.now)

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, history_size: int = 1000):
        self.history_size = history_size
        
        # 指标历史
        self.metrics_history: deque = deque(maxlen=history_size)
        self.latency_history: deque = deque(maxlen=history_size)
        
        # 警报阈值
        self.alert_thresholds = {
            "cpu_percent": 90.0,
            "memory_percent": 85.0,
            "gpu_percent": 95.0,
            "latency_ms": 1000.0
        }
        
        # 警报回调
        self.alert_callbacks: List[Callable] = []
        
        # 监控状态
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.monitor_interval = 1.0  # 秒
        
        # 统计
        self.stats = {
            "total_samples": 0,
            "total_alerts": 0,
            "start_time": None
        }
        
        logger.info("[PerformanceMonitor] 初始化完成")
    
    async def start_monitoring(self, interval: float = 1.0):
        """开始监控"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_interval = interval
        self.stats["start_time"] = datetime.now()
        
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"[PerformanceMonitor] 开始监控 (间隔: {interval}秒)")
    
    async def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("[PerformanceMonitor] 停止监控")
    
    async def _monitor_loop(self):
        """监控循环"""
        try:
            while self.is_monitoring:
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)
                self.stats["total_samples"] += 1
                
                # 检查警报
                await self._check_alerts(metrics)
                
                await asyncio.sleep(self.monitor_interval)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.info(f"[PerformanceMonitor] 监控循环错误: {e}")
    
    async def _collect_metrics(self) -> PerformanceMetrics:
        """收集性能指标"""
        metrics = PerformanceMetrics()
        
        try:
            # CPU使用率
            metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # 内存使用
            memory = psutil.virtual_memory()
            metrics.memory_percent = memory.percent
            metrics.memory_used_mb = memory.used / (1024 * 1024)
            metrics.memory_total_mb = memory.total / (1024 * 1024)
            
            # GPU信息（如果可用）
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    metrics.gpu_percent = gpu.load * 100
                    metrics.gpu_memory_used_mb = gpu.memoryUsed
                    metrics.gpu_memory_total_mb = gpu.memoryTotal
            except ImportError:
                pass
            
            # 磁盘IO
            disk_io = psutil.disk_io_counters()
            if disk_io:
                metrics.disk_io_read_mb = disk_io.read_bytes / (1024 * 1024)
                metrics.disk_io_write_mb = disk_io.write_bytes / (1024 * 1024)
            
            # 网络IO
            net_io = psutil.net_io_counters()
            if net_io:
                metrics.network_sent_mb = net_io.bytes_sent / (1024 * 1024)
                metrics.network_recv_mb = net_io.bytes_recv / (1024 * 1024)
            
        except Exception as e:
            logger.info(f"[PerformanceMonitor] 收集指标失败: {e}")
        
        return metrics
    
    async def _check_alerts(self, metrics: PerformanceMetrics):
        """检查警报"""
        alerts = []
        
        if metrics.cpu_percent > self.alert_thresholds["cpu_percent"]:
            alerts.append(f"CPU使用率过高: {metrics.cpu_percent:.1f}%")
        
        if metrics.memory_percent > self.alert_thresholds["memory_percent"]:
            alerts.append(f"内存使用率过高: {metrics.memory_percent:.1f}%")
        
        if metrics.gpu_percent > self.alert_thresholds["gpu_percent"]:
            alerts.append(f"GPU使用率过高: {metrics.gpu_percent:.1f}%")
        
        for alert in alerts:
            self.stats["total_alerts"] += 1
            logger.info(f"[PerformanceMonitor] 警报: {alert}")
            
            for callback in self.alert_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(alert, metrics)
                    else:
                        callback(alert, metrics)
                except Exception as e:
                    logger.info(f"[PerformanceMonitor] 警报回调失败: {e}")
    
    def record_latency(self, operation: str, latency_ms: float):
        """记录延迟"""
        metric = LatencyMetric(
            operation=operation,
            latency_ms=latency_ms
        )
        self.latency_history.append(metric)
        
        # 检查延迟警报
        if latency_ms > self.alert_thresholds["latency_ms"]:
            alert = f"{operation} 延迟过高: {latency_ms:.1f}ms"
            logger.info(f"[PerformanceMonitor] 警报: {alert}")
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """获取当前指标"""
        if self.metrics_history:
            return self.metrics_history[-1]
        return None
    
    def get_average_metrics(self, duration_seconds: int = 60) -> Dict[str, float]:
        """获取平均指标"""
        if not self.metrics_history:
            return {}
        
        cutoff_time = datetime.now() - timedelta(seconds=duration_seconds)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {}
        
        return {
            "cpu_percent": sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics),
            "memory_percent": sum(m.memory_percent for m in recent_metrics) / len(recent_metrics),
            "gpu_percent": sum(m.gpu_percent for m in recent_metrics) / len(recent_metrics)
        }
    
    def get_latency_stats(self, operation: str = None) -> Dict[str, float]:
        """获取延迟统计"""
        if operation:
            latencies = [m.latency_ms for m in self.latency_history if m.operation == operation]
        else:
            latencies = [m.latency_ms for m in self.latency_history]
        
        if not latencies:
            return {}
        
        return {
            "count": len(latencies),
            "avg_ms": sum(latencies) / len(latencies),
            "min_ms": min(latencies),
            "max_ms": max(latencies),
            "p50_ms": sorted(latencies)[len(latencies) // 2],
            "p95_ms": sorted(latencies)[int(len(latencies) * 0.95)],
            "p99_ms": sorted(latencies)[int(len(latencies) * 0.99)]
        }
    
    def on_alert(self, callback: Callable):
        """注册警报回调"""
        self.alert_callbacks.append(callback)
    
    def set_threshold(self, metric: str, value: float):
        """设置警报阈值"""
        if metric in self.alert_thresholds:
            self.alert_thresholds[metric] = value
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        uptime = None
        if self.stats["start_time"]:
            uptime = (datetime.now() - self.stats["start_time"]).total_seconds()
        
        return {
            "is_monitoring": self.is_monitoring,
            "total_samples": self.stats["total_samples"],
            "total_alerts": self.stats["total_alerts"],
            "uptime_seconds": uptime,
            "history_size": len(self.metrics_history),
            "latency_count": len(self.latency_history)
        }
    
    def generate_report(self) -> str:
        """生成性能报告"""
        report = []
        report.append("# 性能监控报告")
        report.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 当前指标
        current = self.get_current_metrics()
        if current:
            report.append("\n## 当前指标\n")
            report.append(f"- CPU使用率: {current.cpu_percent:.1f}%")
            report.append(f"- 内存使用率: {current.memory_percent:.1f}%")
            report.append(f"- 内存使用: {current.memory_used_mb:.0f}MB / {current.memory_total_mb:.0f}MB")
            if current.gpu_percent > 0:
                report.append(f"- GPU使用率: {current.gpu_percent:.1f}%")
                report.append(f"- GPU显存: {current.gpu_memory_used_mb:.0f}MB / {current.gpu_memory_total_mb:.0f}MB")
        
        # 平均指标
        avg_metrics = self.get_average_metrics(60)
        if avg_metrics:
            report.append("\n## 最近60秒平均指标\n")
            for key, value in avg_metrics.items():
                report.append(f"- {key}: {value:.1f}%")
        
        # 延迟统计
        latency_stats = self.get_latency_stats()
        if latency_stats:
            report.append("\n## 延迟统计\n")
            for key, value in latency_stats.items():
                report.append(f"- {key}: {value:.1f}ms")
        
        # 统计信息
        stats = self.get_stats()
        report.append("\n## 监控统计\n")
        report.append(f"- 总采样数: {stats['total_samples']}")
        report.append(f"- 总警报数: {stats['total_alerts']}")
        if stats['uptime_seconds']:
            report.append(f"- 运行时间: {stats['uptime_seconds']:.0f}秒")
        
        return "\n".join(report)

# 全局实例
_performance_monitor: Optional[PerformanceMonitor] = None

def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器实例"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor

# 性能计时装饰器
def measure_latency(operation: str):
    """测量延迟装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                latency_ms = (time.time() - start_time) * 1000
                monitor = get_performance_monitor()
                monitor.record_latency(operation, latency_ms)
        return wrapper
    return decorator
