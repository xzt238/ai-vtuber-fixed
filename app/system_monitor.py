"""
系统监控集成模块
将性能监控、配置热重载和日志分析集成到主程序中
使用独立线程运行 asyncio 事件循环
"""

import asyncio
import threading
import logging
from typing import Optional, Dict, Any, List, Callable

logger = logging.getLogger(__name__)


class SystemMonitor:
    """
    系统监控集成器
    
    在独立线程中运行 asyncio 事件循环，管理：
    - 性能监控 (PerformanceMonitor)
    - 配置热重载 (ConfigHotReload)
    - 日志分析 (LogAnalyzer)
    """
    
    def __init__(self, config_dir: str = ".", enable_performance: bool = True, enable_hot_reload: bool = True, enable_log_analyzer: bool = True, log_analyzer_interval: float = 300.0, llm_config: Dict[str, Any] = None) -> None:
        """初始化系统监控"""
        self.config_dir = config_dir
        self.enable_performance = enable_performance
        self.enable_hot_reload = enable_hot_reload
        self.enable_log_analyzer = enable_log_analyzer
        self.log_analyzer_interval = log_analyzer_interval
        self._llm_config = llm_config

        # asyncio 事件循环（在独立线程中运行）
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

        # 模块实例
        self._performance_monitor = None
        self._config_hot_reload = None
        self._log_analyzer = None

        # 状态
        self.is_running = False

        # 配置文件列表
        self._config_files: List[str] = []

        logger.info(f"[SystemMonitor] 初始化完成 (日志分析间隔: {log_analyzer_interval}秒)")
    
    def _run_event_loop(self) -> None:
        """在独立线程中运行 asyncio 事件循环"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_forever()
        except Exception as e:
            logger.error(f"[SystemMonitor] 事件循环异常: {e}")
        finally:
            self._loop.close()
    
    async def _start_modules(self) -> None:
        """启动所有监控模块"""
        try:
            # 启动性能监控
            if self.enable_performance:
                from performance_monitor import get_performance_monitor
                self._performance_monitor = get_performance_monitor()
                await self._performance_monitor.start_monitoring(interval=2.0)
                logger.info("[SystemMonitor] 性能监控已启动")
            
            # 启动配置热重载
            if self.enable_hot_reload:
                from config_hot_reload import get_config_hot_reload
                self._config_hot_reload = get_config_hot_reload(self.config_dir)
                
                # 添加配置文件监听
                for config_file in self._config_files:
                    self._config_hot_reload.add_watch(config_file)
                
                await self._config_hot_reload.start_watching()
                logger.info("[SystemMonitor] 配置热重载已启动")
            
            # 启动日志分析器
            if self.enable_log_analyzer:
                from log_analyzer import init_log_analyzer
                self._log_analyzer = init_log_analyzer(
                    analysis_interval=self.log_analyzer_interval,
                    auto_start=True,
                    llm_config=self._llm_config
                )
                logger.info(f"[SystemMonitor] 日志分析器已启动 (间隔: {self.log_analyzer_interval}秒)")
                
        except Exception as e:
            logger.error(f"[SystemMonitor] 启动模块失败: {e}")
    
    async def _stop_modules(self) -> None:
        """停止所有监控模块"""
        try:
            if self._performance_monitor:
                await self._performance_monitor.stop_monitoring()
                logger.info("[SystemMonitor] 性能监控已停止")
            
            if self._config_hot_reload:
                await self._config_hot_reload.stop_watching()
                logger.info("[SystemMonitor] 配置热重载已停止")
            
            if self._log_analyzer:
                self._log_analyzer.stop()
                logger.info("[SystemMonitor] 日志分析器已停止")
                
        except Exception as e:
            logger.error(f"[SystemMonitor] 停止模块失败: {e}")
    
    def add_config_file(self, file_path: str) -> None:
        """添加配置文件到监听列表"""
        if file_path not in self._config_files:
            self._config_files.append(file_path)
            
            # 如果热重载已运行，立即添加监听
            if self._config_hot_reload and self.is_running:
                future = asyncio.run_coroutine_threadsafe(
                    self._async_add_watch(file_path),
                    self._loop
                )
                try:
                    future.result(timeout=5)
                except Exception as e:
                    logger.error(f"[SystemMonitor] 添加监听失败: {e}")
    
    async def _async_add_watch(self, file_path: str) -> None:
        """异步添加文件监听"""
        if self._config_hot_reload:
            self._config_hot_reload.add_watch(file_path)
    
    def start(self) -> None:
        """启动系统监控"""
        if self.is_running:
            logger.warning("[SystemMonitor] 已在运行中")
            return
        
        # 启动事件循环线程
        self._thread = threading.Thread(
            target=self._run_event_loop,
            daemon=True,
            name="SystemMonitor-EventLoop"
        )
        self._thread.start()
        
        # 等待事件循环就绪
        import time
        time.sleep(0.1)
        
        # 在事件循环中启动模块
        if self._loop:
            future = asyncio.run_coroutine_threadsafe(
                self._start_modules(),
                self._loop
            )
            try:
                future.result(timeout=10)
                self.is_running = True
                logger.info("[SystemMonitor] 系统监控已启动")
            except Exception as e:
                logger.error(f"[SystemMonitor] 启动失败: {e}")
    
    def stop(self) -> None:
        """停止系统监控"""
        if not self.is_running:
            return
        
        # 停止模块
        if self._loop:
            future = asyncio.run_coroutine_threadsafe(
                self._stop_modules(),
                self._loop
            )
            try:
                future.result(timeout=10)
            except Exception as e:
                logger.error(f"[SystemMonitor] 停止失败: {e}")
            
            # 停止事件循环
            self._loop.call_soon_threadsafe(self._loop.stop)
        
        # 等待线程结束
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        self.is_running = False
        logger.info("[SystemMonitor] 系统监控已停止")
    
    def get_performance_metrics(self) -> Optional[Dict[str, Any]]:
        """获取当前性能指标"""
        if not self._performance_monitor:
            return None
        
        metrics = self._performance_monitor.get_current_metrics()
        if metrics:
            return {
                "cpu_percent": metrics.cpu_percent,
                "memory_percent": metrics.memory_percent,
                "memory_used_mb": metrics.memory_used_mb,
                "memory_total_mb": metrics.memory_total_mb,
                "gpu_percent": metrics.gpu_percent,
                "gpu_memory_used_mb": metrics.gpu_memory_used_mb,
                "gpu_memory_total_mb": metrics.gpu_memory_total_mb,
            }
        return None
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能监控统计"""
        if not self._performance_monitor:
            return {"enabled": False}
        
        stats = self._performance_monitor.get_stats()
        stats["enabled"] = True
        return stats
    
    def get_hot_reload_stats(self) -> Dict[str, Any]:
        """获取配置热重载统计"""
        if not self._config_hot_reload:
            return {"enabled": False}
        
        stats = self._config_hot_reload.get_stats()
        stats["enabled"] = True
        stats["watched_files"] = self._config_hot_reload.get_watched_files()
        return stats
    
    def record_latency(self, operation: str, latency_ms: float) -> None:
        """记录操作延迟（供外部调用）"""
        if self._performance_monitor:
            self._performance_monitor.record_latency(operation, latency_ms)
    
    def on_config_change(self, callback: Callable) -> None:
        """注册配置变更回调"""
        if self._config_hot_reload:
            self._config_hot_reload.on_reload(callback)
    
    def generate_performance_report(self) -> str:
        """生成性能报告"""
        if not self._performance_monitor:
            return "性能监控未启用"
        return self._performance_monitor.generate_report()
    
    def get_log_analyzer_stats(self) -> Dict[str, Any]:
        """获取日志分析器统计"""
        if not self._log_analyzer:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "is_running": self._log_analyzer._is_running,
            "total_logs": len(self._log_analyzer._log_buffer),
            "total_errors": len(self._log_analyzer._error_logs),
            "total_warnings": len(self._log_analyzer._warning_logs)
        }
    
    def get_log_analysis_result(self) -> Optional[Dict[str, Any]]:
        """获取最新的日志分析结果"""
        if not self._log_analyzer:
            return None
        
        result = self._log_analyzer.get_latest_analysis()
        if result:
            return {
                "timestamp": result.timestamp.isoformat(),
                "summary": result.summary,
                "issues": result.issues,
                "suggestions": result.suggestions,
                "severity": result.severity,
                "recent_errors": result.raw_logs[:3]
            }
        return None
    
    def get_log_error_summary(self) -> Dict[str, Any]:
        """获取日志错误摘要"""
        if not self._log_analyzer:
            return {"enabled": False}
        
        return self._log_analyzer.get_error_summary()
    
    def analyze_logs_with_llm(self) -> Optional[str]:
        """使用LLM分析日志"""
        if not self._log_analyzer:
            return "日志分析器未启用"
        
        return self._log_analyzer.analyze_with_llm()


# 全局实例
_system_monitor: Optional[SystemMonitor] = None


def get_system_monitor() -> SystemMonitor:
    """获取系统监控实例"""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor


def init_system_monitor(
    config_dir: str = ".",
    config_files: List[str] = None,
    enable_performance: bool = True,
    enable_hot_reload: bool = True,
    enable_log_analyzer: bool = True,
    log_analyzer_interval: float = 300.0,
    llm_config: Dict[str, Any] = None
) -> SystemMonitor:
    """
    初始化并启动系统监控

    Args:
        config_dir: 配置文件目录
        config_files: 要监听的配置文件列表
        enable_performance: 是否启用性能监控
        enable_hot_reload: 是否启用配置热重载
        enable_log_analyzer: 是否启用日志分析器
        log_analyzer_interval: 日志分析间隔（秒）
        llm_config: LLM配置（可选）

    Returns:
        SystemMonitor 实例
    """
    global _system_monitor

    # 停止旧实例
    if _system_monitor and _system_monitor.is_running:
        _system_monitor.stop()

    # 创建新实例
    _system_monitor = SystemMonitor(
        config_dir=config_dir,
        enable_performance=enable_performance,
        enable_hot_reload=enable_hot_reload,
        enable_log_analyzer=enable_log_analyzer,
        log_analyzer_interval=log_analyzer_interval,
        llm_config=llm_config
    )
    
    # 添加配置文件
    if config_files:
        for f in config_files:
            _system_monitor.add_config_file(f)
    
    # 启动监控
    _system_monitor.start()
    
    return _system_monitor
