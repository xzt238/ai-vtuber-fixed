"""统一异步任务管理器 — 借鉴 Calibre JobManager

职责:
1. 提交 QRunnable 任务到 QThreadPool
2. 追踪活跃任务状态
3. 统一 Signal 通知（job_started / job_finished / job_failed）
4. 支持任务取消（通过 Worker 配合检查标志位）

线程安全规则:
- 所有 Signal 在主线程发射（Qt Signal/Slot 跨线程自动队列连接）
- _active_jobs 字典由主线程独占访问（submit/cancel/shutdown 都在主线程调用）
- Worker 的 _bridge Signal 自动连接到 job_finished/job_failed 槽

版本: v1.11.23
"""

import logging
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool

logger = logging.getLogger(__name__)


class AsyncJobManager(QObject):
    """统一异步任务管理器

    管理通过 QThreadPool 执行的后台任务，提供:
    - 任务提交和引用保持（防止 QRunnable 的 Bridge 被 GC 回收）
    - 统一 Signal 通知（job_started / job_finished / job_failed）
    - 任务取消支持（需 Worker 配合检查标志位）
    - 优雅关闭（等待所有任务完成）

    Signals:
        job_started(str): 任务开始，携带 job_id
        job_finished(str): 任务完成，携带 job_id
        job_failed(str, str): 任务失败，携带 (job_id, error)
    """

    job_started = Signal(str)          # job_id
    job_finished = Signal(str)         # job_id
    job_failed = Signal(str, str)      # job_id, error

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._active_jobs: Dict[str, QRunnable] = {}
        self._thread_pool = QThreadPool.globalInstance()

    def submit(self, job_id: str, worker: QRunnable) -> None:
        """提交异步任务到线程池

        Args:
            job_id: 任务唯一标识符
            worker: QRunnable 实例（StatsResultWorker 等）

        注意:
            - Worker 的 _bridge Signal 会被自动连接到 job_finished / job_failed
            - Worker 引用保存在 _active_jobs 中，防止 Bridge 被 GC 回收
            - Worker 完成后会自动从 _active_jobs 中移除
        """
        if job_id in self._active_jobs:
            logger.warning(f"Job {job_id} already exists, skipping")
            return

        # 保存引用防止 GC 回收 Bridge 对象
        self._active_jobs[job_id] = worker

        # 自动连接 Worker 的 Signal 到管理器
        if hasattr(worker, 'init_done'):
            worker.init_done.connect(lambda name, jid=job_id: self._on_job_finished(jid))
        if hasattr(worker, 'init_failed'):
            worker.init_failed.connect(lambda name, err, jid=job_id: self._on_job_failed(jid, err))
        if hasattr(worker, 'stats_ready'):
            worker.stats_ready.connect(lambda stats, jid=job_id: self._on_job_finished(jid))
        if hasattr(worker, 'error'):
            worker.error.connect(lambda err, jid=job_id: self._on_job_failed(jid, err))

        # 提交到线程池
        self._thread_pool.start(worker)
        self.job_started.emit(job_id)
        logger.debug(f"Job {job_id} submitted")

    def cancel(self, job_id: str) -> bool:
        """取消任务（设置标志位，由 Worker 自行检查退出）

        QThreadPool 不支持强制取消已提交的任务，
        此方法仅标记任务为取消状态。Worker 需要在 run() 中
        定期检查取消标志并主动退出。

        Args:
            job_id: 任务唯一标识符

        Returns:
            True 如果任务存在且已标记取消，False 如果任务不存在
        """
        if job_id in self._active_jobs:
            # KI-XXX: 目前仅从活跃列表移除，Worker 本身不支持中断
            # 未来可扩展 Worker 基类增加 _cancelled 标志位
            del self._active_jobs[job_id]
            logger.info(f"Job {job_id} cancelled (removed from active list)")
            return True
        return False

    @property
    def active_jobs(self) -> List[str]:
        """当前活跃任务 ID 列表"""
        return list(self._active_jobs.keys())

    def shutdown(self, wait_ms: int = 5000) -> None:
        """关闭管理器，等待所有任务完成

        Args:
            wait_ms: 等待超时时间（毫秒），默认 5 秒
        """
        if self._active_jobs:
            logger.info(f"Waiting for {len(self._active_jobs)} active jobs to finish...")
            self._thread_pool.waitForDone(wait_ms)
            remaining = len(self._active_jobs)
            if remaining > 0:
                logger.warning(f"{remaining} jobs did not finish within timeout")
            self._active_jobs.clear()

    # ========== 内部 Slot ==========

    def _on_job_finished(self, job_id: str) -> None:
        """任务完成回调 — 从活跃列表移除"""
        self._active_jobs.pop(job_id, None)
        self.job_finished.emit(job_id)
        logger.debug(f"Job {job_id} finished")

    def _on_job_failed(self, job_id: str, error: str) -> None:
        """任务失败回调 — 从活跃列表移除"""
        self._active_jobs.pop(job_id, None)
        self.job_failed.emit(job_id, error)
        logger.warning(f"Job {job_id} failed: {error}")
