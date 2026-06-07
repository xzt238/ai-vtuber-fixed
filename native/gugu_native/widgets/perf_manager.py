"""
咕咕嘎嘎 AI-VTuber — 性能与资源管理器

职责:
1. 后端延迟初始化（按需加载，避免启动卡顿）
2. 页面资源追踪与清理
3. 增量 GC 分代定时器（替代全量 GC，减少主线程暂停）
4. 大对象生命周期管理

v1.11.22 变更:
- 全量 GC (60s) → 增量 GC (gen0:5s / gen1:30s / gen2:120s)
- 新增 schedule_backend_init_async()：后端异步初始化（QThread + MoveToThread）
- 保留 schedule_backend_init() 标记为 deprecated，向后兼容
- 退出时恢复 gc.enable() + gc.collect(2)

版本: v1.11.23
"""

import os
import sys
import gc
import weakref
import logging
from typing import Optional, Any, Dict

from PySide6.QtCore import QObject, QTimer, Signal, QThread, Slot

logger = logging.getLogger(__name__)


class PerformanceManager(QObject):
    __slots__ = ("_cleanup_targets", "_pending_inits", "_monitor_timer", "_gc_disabled", "_gc_gen0_timer", "_gc_gen1_timer", "_gc_gen2_timer", "_backend_initialized", "_backend_init_started", "_init_worker", "_init_thread", "_callback")
    """性能与资源管理器"""

    # 内存警告信号（MB）
    memory_warning = Signal(float)

    # 窗口拖动/resize 状态广播信号
    window_drag_state_changed = Signal(bool)

    # 内存阈值（MB）
    # 注意: ASR(FunASR/Paraformer) + TTS(GPT-SoVITS双模型) + LLM + 语义向量(bge-base)
    # 自然内存占用 2-3GB（MiMo ASR/TTS 轻量）到 4-5GB（GPT-SoVITS 本地推理）
    # 阈值必须高于此基线才不会误触发清理
    MEMORY_WARNING_THRESHOLD = 3500
    MEMORY_CRITICAL_THRESHOLD = 5500

    # 增量 GC 定时器配置 — 分代回收，每代不同间隔
    # gen0: 年轻对象，频繁回收，耗时 <5ms
    # gen1: 中等年龄对象，中等频率，耗时 <16ms
    # gen2: 老年代对象，低频全量回收，耗时 <50ms
    GC_GEN0_INTERVAL_MS = 5000    # gen0: 每 5s
    GC_GEN1_INTERVAL_MS = 30000   # gen1: 每 30s
    GC_GEN2_INTERVAL_MS = 120000  # gen2: 每 120s

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

        # 增量 GC 定时器（替代原来的全量 GC 60s 定时器）
        self._gc_disabled = False
        self._setup_incremental_gc()

        # 后端初始化标记
        self._backend_initialized = False
        self._backend_init_started = False

        # 异步初始化相关
        self._init_worker = None
        self._init_thread = None
        self._callback = None

    # ========== 增量 GC ==========

    def _setup_incremental_gc(self):
        """初始化增量 GC — 禁用自动 GC，设置分代定时器

        禁用 Python 自动 GC（gc.disable()），改用 3 个 QTimer 分代回收：
        - gen0 每 5s：回收年轻对象，耗时 <5ms
        - gen1 每 30s：回收 gen0+1，耗时 <16ms
        - gen2 每 120s：全量回收 gen0+1+2，耗时 <50ms

        优势：每次 GC 暂停时间大幅缩短，避免 100-500ms 的全量 GC 卡顿。
        退出时必须恢复 gc.enable() + gc.collect(2)（在 cleanup() 中）。
        """
        gc.disable()
        self._gc_disabled = True
        logger.info("Incremental GC enabled: gc.disable(), gen0=5s, gen1=30s, gen2=120s")

        self._gc_gen0_timer = QTimer(self)
        self._gc_gen0_timer.timeout.connect(lambda: self._run_gc_gen(0))
        self._gc_gen0_timer.start(self.GC_GEN0_INTERVAL_MS)

        self._gc_gen1_timer = QTimer(self)
        self._gc_gen1_timer.timeout.connect(lambda: self._run_gc_gen(1))
        self._gc_gen1_timer.start(self.GC_GEN1_INTERVAL_MS)

        self._gc_gen2_timer = QTimer(self)
        self._gc_gen2_timer.timeout.connect(lambda: self._run_gc_gen(2))
        self._gc_gen2_timer.start(self.GC_GEN2_INTERVAL_MS)

    def _run_gc_gen(self, generation: int):
        """分代 GC — 仅回收指定代及更年轻的对象

        Args:
            generation: GC 代数 (0/1/2)
                0: 仅回收最年轻对象
                1: 回收 gen0+1
                2: 全量回收 gen0+1+2
        """
        collected = gc.collect(generation)
        if collected > 0:
            logger.debug(f"GC gen{generation} collected {collected} objects")

    # ========== 后端懒加载（同步，deprecated）==========

    def schedule_backend_init(self, callback=None, delay_ms=2000):
        """延迟初始化后端（同步模式 — deprecated，保留向后兼容）

        .. deprecated::
            请使用 schedule_backend_init_async() 替代。
            此方法在主线程中同步构造 AIVTuber，会阻塞 UI。

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
                    logger.info("Backend initialized successfully (sync, deprecated)")
                    if callback:
                        callback()
            except Exception as e:
                logger.error(f"Backend init failed: {e}")

        QTimer.singleShot(delay_ms, _do_init)

    # ========== 后端异步初始化 ==========

    def schedule_backend_init_async(self, callback=None, delay_ms=2000):
        """异步初始化后端 — 在 QThread 中执行，不阻塞主线程

        使用 MoveToThread 模式在 Worker 线程中构造 AIVTuber 实例，
        构造完成后通过 Signal 传回主线程赋值，GUI 在初始化期间保持可交互。

        Args:
            callback: 初始化完成后的回调函数（在主线程中执行）
            delay_ms: 延迟时间（毫秒），默认 2 秒让 UI 先渲染
        """
        if self._backend_initialized or self._backend_init_started:
            return
        self._backend_init_started = True

        from gugu_native.workers.init_workers import BackendInitWorker

        self._init_worker = BackendInitWorker()
        self._init_thread = QThread()
        self._init_worker.moveToThread(self._init_thread)

        # 连接信号
        self._init_thread.started.connect(self._init_worker.do_work)
        self._init_worker.backend_ready.connect(self._on_backend_init_done)
        self._init_worker.init_failed.connect(self._on_backend_init_failed)
        self._init_worker.init_progress.connect(self._on_backend_init_progress)

        self._callback = callback

        # 延迟启动线程（让 UI 先渲染）
        QTimer.singleShot(delay_ms, self._init_thread.start)
        logger.info(f"Backend async init scheduled (delay={delay_ms}ms)")

    @Slot(object)
    def _on_backend_init_done(self, backend_instance):
        """后端初始化完成 — 在主线程中赋值

        Worker 线程中构造的 AIVTuber 实例通过 Signal 传回主线程，
        在主线程中安全赋值给主窗口的 _backend 属性。

        Args:
            backend_instance: AIVTuber 实例
        """
        main_window = self.parent()
        if main_window:
            main_window._backend = backend_instance  # 直接赋值
            main_window._backend_ready = True
            # 连接语音管理器到后端
            if hasattr(main_window, 'voice_manager') and main_window.voice_manager:
                main_window.voice_manager.backend = backend_instance
            # 通知 splash
            if hasattr(main_window, '_splash') and main_window._splash:
                main_window._splash.mark_backend_ready()
            # 通知 tray
            if hasattr(main_window, 'tray_manager') and main_window.tray_manager:
                main_window.tray_manager.notify_backend_ready()
        self._backend_initialized = True
        logger.info("Backend initialized successfully (async)")
        if self._callback:
            self._callback()
        # 清理线程
        if self._init_thread:
            self._init_thread.quit()
            self._init_thread.wait(3000)

    @Slot(str)
    def _on_backend_init_failed(self, error_msg: str):
        """后端初始化失败回调"""
        logger.error(f"Backend init failed: {error_msg}")
        main_window = self.parent()
        if main_window and hasattr(main_window, 'tray_manager') and main_window.tray_manager:
            main_window.tray_manager.notify_backend_error(error_msg)
        if self._init_thread:
            self._init_thread.quit()
            self._init_thread.wait(3000)

    @Slot(str)
    def _on_backend_init_progress(self, msg: str):
        """后端初始化进度回调"""
        logger.info(f"Backend init progress: {msg}")

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
            except Exception as e:
                return 0.0

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

        # 显式全量 GC（force_cleanup 是紧急清理，需全量回收）
        gc.collect(2)
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
            from app.shared_config import PROJECT_DIR
            cache_dir = os.path.join(PROJECT_DIR, "app", "cache")
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
                    except Exception as e:
                        pass

    # ========== M-001: 模型按需卸载 ==========

    def unload_idle_models(self, idle_threshold_seconds: int = 300):
        """卸载长时间未使用的模型，释放内存

        v1.11.25 新增: 检查后端模块的最后使用时间，
        超过阈值的模块自动卸载（清空 _lazy_modules 中的引用）。

        Args:
            idle_threshold_seconds: 空闲阈值（秒），默认 5 分钟
        """
        import time

        main_window = self.parent()
        if not main_window or not hasattr(main_window, '_lazy_modules'):
            return

        backend = getattr(main_window, 'backend', None)
        if not backend:
            return

        # 可卸载的模块列表（视觉模块通常使用频率低，优先卸载）
        unloadable_modules = ['vision', 'mcp', 'desktop_pet']

        unloaded = []
        for module_name in unloadable_modules:
            module = main_window._lazy_modules.get(module_name)
            if module is None:
                continue

            # 检查模块是否有最后使用时间记录
            last_used = getattr(module, '_last_used_time', None)
            if last_used is None:
                # 没有时间记录，跳过（可能是刚加载的）
                continue

            idle_time = time.time() - last_used
            if idle_time > idle_threshold_seconds:
                # 卸载模块
                try:
                    if hasattr(module, 'cleanup'):
                        module.cleanup()
                    main_window._lazy_modules[module_name] = None
                    unloaded.append(f"{module_name} (idle {idle_time:.0f}s)")
                except Exception as e:
                    logger.warning(f"Failed to unload {module_name}: {e}")

        if unloaded:
            logger.info(f"Unloaded idle models: {', '.join(unloaded)}")
            # 触发 GC 回收卸载的内存
            gc.collect(1)

    # ========== 窗口状态广播 ==========

    def set_window_drag_state(self, dragging: bool):
        """广播窗口拖动/resize 状态给所有订阅组件

        Args:
            dragging: True 表示窗口正处于拖动或 resize 状态；
                      False 表示已恢复静止。
        """
        self.window_drag_state_changed.emit(dragging)

    # ========== GC 调优 ==========

    def tune_gc_thresholds(self):
        """调优 Python GC 阈值，减少启动阶段暂停

        当前增量 GC 配置：gen0:5s / gen1:30s / gen2:120s。
        适当放宽 gen0 阈值，减少小对象频繁回收。
        """
        gc.set_threshold(900, 15, 5)
        logger.info("GC thresholds tuned: (900, 15, 5)")

    # ========== 清理 ==========

    def cleanup(self):
        """全局清理 — 恢复 GC + 停止定时器 + 强制清理资源

        在应用退出时调用，确保:
        1. 停止所有 GC 定时器
        2. 恢复 Python 自动 GC（gc.enable()）
        3. 执行一次全量 GC（gc.collect(2)）
        4. 停止内存监控
        5. 强制清理已注册的资源
        """
        # 停止内存监控
        self._monitor_timer.stop()

        # 停止增量 GC 定时器
        if hasattr(self, '_gc_gen0_timer'):
            self._gc_gen0_timer.stop()
        if hasattr(self, '_gc_gen1_timer'):
            self._gc_gen1_timer.stop()
        if hasattr(self, '_gc_gen2_timer'):
            self._gc_gen2_timer.stop()

        # 恢复 Python 自动 GC
        if self._gc_disabled:
            gc.enable()
            gc.collect(2)  # 退出前全量回收
            logger.info("GC restored: gc.enable() + gc.collect(2)")

        # 强制清理资源
        self.force_cleanup()
