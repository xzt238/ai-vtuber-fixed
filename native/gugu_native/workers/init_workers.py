"""GUI 优化专用 Workers — 后端初始化 / 记忆统计读取

Workers 说明:
- BackendInitWorker: 在 QThread 中构造 AIVTuber 实例，避免阻塞主线程
- StatsResultWorker: 在 QThreadPool 中异步读取记忆统计数据

线程安全规则:
- QRunnable 不是 QObject，无法直接定义 Signal
- 使用内部 _SignalBridge(QObject) 持有 Signal，外部通过 bridge 访问
- Bridge 对象必须保持引用（防止 GC 回收），由调用方持有

版本: v1.11.23
"""

from PySide6.QtCore import QObject, Signal, Slot, QRunnable


class BackendInitWorker(QObject):
    """后端异步初始化 Worker — 在 QThread 中构造 AIVTuber 实例

    使用 MoveToThread 模式，支持事件循环（未来可接收命令）。
    AIVTuber 是纯 Python Facade，无 Qt 依赖，可在 QThread 中安全构造。

    Signals:
        backend_ready(object): AIVTuber 实例构造完成
        init_failed(str): 初始化失败，携带错误信息
        init_progress(str): 初始化进度描述（如"正在加载语言模型..."）
    """

    backend_ready = Signal(object)   # AIVTuber 实例
    init_failed = Signal(str)       # 错误信息
    init_progress = Signal(str)     # 进度描述

    def __init__(self):
        super().__init__()
        self._backend_instance = None

    @Slot()
    def do_work(self):
        """在 Worker 线程中执行后端初始化

        构造 AIVTuber 实例（5-15s），通过 Signal 传回主线程赋值。
        """
        try:
            from app.main import AIVTuber
            self.init_progress.emit("正在初始化 AI 引擎...")
            self._backend_instance = AIVTuber()
            self.backend_ready.emit(self._backend_instance)
        except Exception as e:
            self.init_failed.emit(str(e))


class _StatsSignalBridge(QObject):
    """StatsResultWorker 的 Signal 桥接"""
    stats_ready = Signal(dict)
    error = Signal(str)


class StatsResultWorker(QRunnable):
    """记忆统计异步读取 Worker — 在 QThreadPool 中读取记忆数据

    将 MemoryPage 的 _refresh_stats() 从同步阻塞改为异步模式，
    主线程立即返回，统计结果通过 Signal 回传更新 UI。

    注意：
    - Bridge 对象必须被外部持有引用（防止 GC 回收）
    - setAutoDelete(False)：由调用方管理生命周期（_stats_worker 覆盖时旧 worker 自动 GC）

    Args:
        memory_system: MemorySystem 实例（后端的 memory 属性）

    Signals (via _bridge):
        stats_ready(dict): 统计数据字典
        error(str): 读取错误信息
    """

    def __init__(self, memory_system):
        super().__init__()
        self._memory_system = memory_system
        self.setAutoDelete(False)  # 由调用方管理生命周期
        self._bridge = _StatsSignalBridge()
        self.stats_ready = self._bridge.stats_ready
        self.error = self._bridge.error

    def run(self):
        """在线程池线程中异步读取记忆统计数据

        读取操作是纯只读（len / get_stats），与写操作不并发
        （写由用户触发，时序分离），因此并发安全。
        """
        try:
            mem = self._memory_system
            result = {
                "working_count": len(mem.working_memory),
                "episodic_count": len(mem.episodic_memory),
                "semantic_stats": mem.vector_store.get_stats(),
                "facts_count": len(mem.facts),
                "forgotten_count": mem.forgotten_count,
            }
            self.stats_ready.emit(result)
        except Exception as e:
            self.error.emit(str(e))
