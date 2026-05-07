"""
咕咕嘎嘎 AI-VTuber — 性能与资源管理器

职责:
1. 后端延迟初始化（按需加载，避免启动卡顿）
2. 页面资源追踪与清理
3. 定期内存回收
4. 大对象生命周期管理
"""

import os
import sys
import gc
import weakref
import logging
from typing import Optional, Any, Dict

from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger(__name__)


class PerformanceManager(QObject):
    """性能与资源管理器"""

    # 内存警告信号（MB）
    memory_warning = Signal(float)

    # 内存阈值（MB）
    # 注意: ASR(FunASR/Paraformer) + TTS(GPT-SoVITS双模型) + LLM + 语义向量(bge-base)
    # 自然内存占用 2-3GB，阈值必须高于此基线才不会误触发清理
    MEMORY_WARNING_THRESHOLD = 2500
    MEMORY_CRITICAL_THRESHOLD = 4000

    def __init__(self, parent=None):
        super().__init__(parent)

        # 已注册的可清理对象
        self._cleanup_targets: Dict[str, weakref.ref] = {}

        # 后端延迟初始化队列
        self._pending_inits = []

        # 内存监控定时器
        self._monitor_timer = QTimer(self)
        self._monitor_timer.timeout.connect(self._check_memory)
        self._monitor_timer.start(30000)  # 30秒检查一次

        # GC 定时器
        self._gc_timer = QTimer(self)
        self._gc_timer.timeout.connect(self._run_gc)
        self._gc_timer.start(60000)  # 60秒 GC 一次

        # 后端初始化标记
        self._backend_initialized = False
        self._backend_init_started = False

    # ========== 后端懒加载 ==========

    def schedule_backend_init(self, callback=None, delay_ms=2000):
        """延迟初始化后端

        Args:
            callback: 初始化完成后的回调函数
            delay_ms: 延迟时间（毫秒），默认2秒让UI先渲染
        """
        if self._backend_initialized or self._backend_init_started:
            return

        self._backend_init_started = True

        def _do_init():
            try:
                # 触发后端初始化（通过 property）
                main_window = self.parent()
                if main_window and hasattr(main_window, 'backend'):
                    _ = main_window.backend  # 触发 @property
                    self._backend_initialized = True
                    logger.info("Backend initialized successfully")
                    if callback:
                        callback()
            except Exception as e:
                logger.error(f"Backend init failed: {e}")

        QTimer.singleShot(delay_ms, _do_init)

    # ========== 资源注册 ==========

    def register_cleanup_target(self, name: str, obj: QObject):
        """注册可清理的对象

        当需要释放内存时，会调用对象的 cleanup() 方法
        """
        self._cleanup_targets[name] = weakref.ref(obj, lambda ref: self._cleanup_targets.pop(name, None))

    def unregister_cleanup_target(self, name: str):
        """取消注册"""
        self._cleanup_targets.pop(name, None)

    # ========== 内存管理 ==========

    def _check_memory(self):
        """定期检查内存使用"""
        mem_mb = self._get_process_memory()
        if mem_mb > self.MEMORY_CRITICAL_THRESHOLD:
            logger.warning(f"Critical memory usage: {mem_mb:.0f}MB, forcing cleanup")
            self.force_cleanup()
        elif mem_mb > self.MEMORY_WARNING_THRESHOLD:
            # 只在首次超过警告阈值时记录，避免日志刷屏
            if not getattr(self, '_warning_logged', False):
                logger.info(f"High memory usage: {mem_mb:.0f}MB (normal for ASR+TTS+LLM)")
                self._warning_logged = True
            self.memory_warning.emit(mem_mb)
        else:
            self._warning_logged = False

    def _get_process_memory(self) -> float:
        """获取当前进程内存使用（MB）"""
        try:
            import psutil
            proc = psutil.Process(os.getpid())
            return proc.memory_info().rss / (1024 * 1024)
        except ImportError:
            # psutil 不可用时用 Windows API 回退（仅 Windows 平台）
            if sys.platform != "win32":
                return 0.0
            try:
                import ctypes
                kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
                psapi = ctypes.WinDLL('psapi')
                handle = kernel32.GetCurrentProcess()
                class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                    _fields_ = [
                        ('cb', ctypes.c_ulong),
                        ('PageFaultCount', ctypes.c_ulong),
                        ('PeakWorkingSetSize', ctypes.c_size_t),
                        ('WorkingSetSize', ctypes.c_size_t),
                        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                        ('PagefileUsage', ctypes.c_size_t),
                        ('PeakPagefileUsage', ctypes.c_size_t),
                    ]
                counters = PROCESS_MEMORY_COUNTERS()
                counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
                psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
                return counters.WorkingSetSize / (1024 * 1024)
            except Exception:
                return 0.0

    def _run_gc(self):
        """定期垃圾回收"""
        collected = gc.collect()
        if collected > 0:
            logger.debug(f"GC collected {collected} objects")

    def force_cleanup(self):
        """强制清理所有已注册的资源 + 后端缓存"""
        cleaned = 0
        for name, ref in list(self._cleanup_targets.items()):
            obj = ref()
            if obj and hasattr(obj, 'cleanup') and callable(obj.cleanup):
                try:
                    obj.cleanup()
                    cleaned += 1
                except Exception as e:
                    logger.warning(f"Failed to cleanup {name}: {e}")

        # 清理后端缓存（临时音频文件、过期数据等）
        self._cleanup_backend_caches()

        # 强制 GC
        gc.collect()
        logger.info(f"Force cleanup completed: {cleaned} targets cleaned")

    def _cleanup_backend_caches(self):
        """清理后端模块的临时缓存（不卸载模型）"""
        main_window = self.parent()
        if not main_window or not hasattr(main_window, 'backend'):
            return

        backend = main_window.backend
        if not backend:
            return

        # 清理 TTS 缓存的临时音频文件
        try:
            cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))))), "app", "cache")
            if os.path.isdir(cache_dir):
                import time
                now = time.time()
                cleaned_files = 0
                for fname in os.listdir(cache_dir):
                    if fname.startswith("gptsovits_") and fname.endswith(".wav"):
                        fpath = os.path.join(cache_dir, fname)
                        # 只清理超过5分钟的临时音频
                        if now - os.path.getmtime(fpath) > 300:
                            try:
                                os.unlink(fpath)
                                cleaned_files += 1
                            except OSError:
                                pass
                if cleaned_files > 0:
                    logger.info(f"Cleaned {cleaned_files} stale TTS cache files")
        except Exception as e:
            logger.debug(f"TTS cache cleanup skipped: {e}")

    # ========== 页面资源追踪 ==========

    def track_page_resources(self, page_name: str, resources: list):
        """追踪页面使用的资源（临时文件、大对象等）"""
        for res in resources:
            if hasattr(res, 'cleanup'):
                self.register_cleanup_target(f"{page_name}:{id(res)}", res)

    def release_page_resources(self, page_name: str):
        """释放页面资源"""
        prefix = f"{page_name}:"
        for name in list(self._cleanup_targets.keys()):
            if name.startswith(prefix):
                ref = self._cleanup_targets.pop(name)
                obj = ref() if ref else None
                if obj and hasattr(obj, 'cleanup'):
                    try:
                        obj.cleanup()
                    except Exception:
                        pass

    # ========== 清理 ==========

    def cleanup(self):
        """全局清理"""
        self._monitor_timer.stop()
        self._gc_timer.stop()
        self.force_cleanup()
