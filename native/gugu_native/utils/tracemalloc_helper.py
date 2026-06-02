"""tracemalloc 辅助工具 — 内存快照/对比/报告

仅作为开发调试工具，不自动集成到主流程。
使用方式：
    from gugu_native.utils.tracemalloc_helper import MemorySnapshot

    MemorySnapshot.start()
    snap1 = MemorySnapshot.take_snapshot()
    # ... 执行待分析的代码 ...
    snap2 = MemorySnapshot.take_snapshot()
    diffs = MemorySnapshot.compare(snap1, snap2)
    report = MemorySnapshot.print_report(snap2)
    print(report)
    MemorySnapshot.stop()
"""

import tracemalloc
import linecache
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class MemorySnapshot:
    """封装 tracemalloc 的启动/停止/快照/对比/报告

    所有方法均为静态方法，无需实例化即可使用。
    """

    @staticmethod
    def start(nframe: int = 25) -> None:
        """启动 tracemalloc 内存追踪

        Args:
            nframe: 每个内存块追踪的栈帧数量，默认 25。
                    增大可获取更详细的调用栈，但会增加内存开销。
        """
        if not tracemalloc.is_tracing():
            tracemalloc.start(nframe)
            logger.info("tracemalloc started (nframe=%d)", nframe)
        else:
            logger.warning("tracemalloc is already running")

    @staticmethod
    def stop() -> None:
        """停止 tracemalloc 内存追踪"""
        if tracemalloc.is_tracing():
            tracemalloc.stop()
            logger.info("tracemalloc stopped")
        else:
            logger.warning("tracemalloc is not running")

    @staticmethod
    def take_snapshot() -> tracemalloc.Snapshot:
        """拍摄当前内存快照

        Returns:
            tracemalloc.Snapshot: 当前内存分配快照

        Raises:
            RuntimeError: tracemalloc 未启动时调用
        """
        if not tracemalloc.is_tracing():
            raise RuntimeError(
                "tracemalloc is not running. Call MemorySnapshot.start() first."
            )
        snapshot = tracemalloc.take_snapshot()
        logger.info("Memory snapshot taken: %d allocations", len(snapshot.statistics("lineno")))
        return snapshot

    @staticmethod
    def compare(
        snapshot1: tracemalloc.Snapshot,
        snapshot2: tracemalloc.Snapshot,
        limit: int = 10,
    ) -> List:
        """对比两个快照，返回内存增长最多的位置

        Args:
            snapshot1: 基准快照（较早的）
            snapshot2: 对比快照（较晚的）
            limit: 返回的最大条目数，默认 10

        Returns:
            list[tracemalloc.StatisticDiff]: 内存差异统计列表，
            按增量大小降序排列
        """
        stats = snapshot2.compare_to(snapshot1, "lineno")
        result = stats[:limit]
        logger.info("Memory diff: %d entries (showing top %d)", len(stats), limit)
        return result

    @staticmethod
    def print_report(
        snapshot: tracemalloc.Snapshot,
        limit: int = 10,
    ) -> str:
        """生成可读的内存分配报告

        Args:
            snapshot: 内存快照
            limit: 返回的最大条目数，默认 10

        Returns:
            str: 格式化的报告文本
        """
        stats = snapshot.statistics("lineno")
        lines = []
        lines.append(f"=== Memory Snapshot Report (top {limit}) ===")
        lines.append(f"Total allocations: {len(stats)}")
        lines.append("")

        for idx, stat in enumerate(stats[:limit], 1):
            lines.append(f"[{idx}] {stat}")
            # 输出该分配点的栈帧
            frame = stat.traceback[0] if stat.traceback else None
            if frame:
                line_text = linecache.getline(frame.filename, frame.lineno).strip()
                lines.append(f"    {frame.filename}:{frame.lineno}: {line_text}")
            lines.append("")

        return "\n".join(lines)
