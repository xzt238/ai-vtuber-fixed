"""
历史记录管理器

负责管理对话历史的加载、保存、压缩等操作。

设计意图:
    - 将 AIVTuber 类中的历史记录管理逻辑提取到独立模块
    - 保持原有功能不变
    - 提高代码可维护性
"""

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class HistoryManager:
    """
    历史记录管理器

    管理对话历史的持久化、加载、压缩等操作。
    """

    def __init__(self, max_history: int = 100, history_file: Optional[Path] = None):
        """
        初始化历史记录管理器

        Args:
            max_history: 最大历史记录条数（每轮 = user + assistant 两条）
            history_file: 历史记录文件路径
        """
        self.max_history = max_history
        self.history: List[Dict] = []
        self._history_lock = threading.Lock()
        self._history_needs_restore = False
        self._save_executor = None

        # 设置历史记录文件路径
        if history_file is None:
            from app.shared_config import PROJECT_DIR as _PD
            self._history_file = Path(_PD) / "memory" / "state" / "chat_history.json"
        else:
            self._history_file = history_file

        # 确保目录存在
        self._history_file.parent.mkdir(parents=True, exist_ok=True)

    def load_history(self, memory=None):
        """
        从磁盘恢复对话历史

        Args:
            memory: 可选的记忆系统实例，用于从工作记忆恢复
        """
        try:
            if self._history_file.exists():
                with open(self._history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    # 仅加载最近的条目到内存
                    self.history = data[-(self.max_history * 2):]
                    logger.info(f"  [历史] 恢复对话历史: {len(self.history)}条 (磁盘共 {len(data)} 条)")
                    return
        except Exception as e:
            logger.info(f"  [历史] 恢复对话历史失败: {e}")

        # 持久化文件不存在或为空，尝试从记忆系统的工作记忆恢复
        try:
            if memory is None:
                # 记忆系统可能还没初始化，延迟恢复
                self._history_needs_restore = True
                self.history = []
                return
            working = getattr(memory, 'working_memory', None)
            if working and len(working) > 0:
                for item in working[-(self.max_history * 2):]:
                    role = getattr(item, 'role', None)
                    content = getattr(item, 'content', None)
                    if role and content:
                        self.history.append({"role": role, "content": content, "time": datetime.now().isoformat()})
                logger.info(f"  [历史] 从工作记忆恢复对话历史: {len(self.history)}条")
                # 首次恢复后保存到磁盘
                self.save_history()
                return
        except Exception as e:
            logger.info(f"  [历史] 从工作记忆恢复失败: {e}")
        self.history = []

    def save_history(self):
        """
        保存对话历史到磁盘

        使用异步写入，不阻塞主线程。
        """
        try:
            data = self.history[-(self.max_history * 2):]
            # 为缺少 time 的旧消息补充时间戳
            for m in data:
                if not m.get('time'):
                    m['time'] = datetime.now().isoformat()

            # 使用单线程池复用，避免频繁创建线程
            if self._save_executor is None:
                from concurrent.futures import ThreadPoolExecutor
                self._save_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="history-save")

            history_file = self._history_file
            def _async_write():
                try:
                    tmp_file = history_file.with_suffix('.tmp')
                    with open(tmp_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    os.replace(tmp_file, history_file)
                except Exception as e:
                    logger.info(f"  [历史] 异步保存对话历史失败: {e}")

            self._save_executor.submit(_async_write)
        except Exception as e:
            logger.info(f"  [历史] 保存对话历史失败: {e}")

    def record_interaction(self, user_text: str, assistant_text: str, memory=None, llm=None):
        """
        统一记录对话交互

        Args:
            user_text: 用户输入文本
            assistant_text: 助手回复文本
            memory: 可选的记忆系统实例
            llm: 可选的 LLM 实例（用于历史压缩）
        """
        if not user_text or not assistant_text:
            return

        # 1. 记忆系统
        if memory is not None:
            try:
                memory.add_interaction("user", user_text)
                memory.add_interaction("assistant", assistant_text)
            except Exception as e:
                logger.debug(f"记忆写入错误（可忽略）: {e}")

        # 2. 历史记录 + 截断 + 持久化
        try:
            with self._history_lock:
                self.history.append({"role": "user", "content": user_text, "time": datetime.now().isoformat()})
                self.history.append({"role": "assistant", "content": assistant_text, "time": datetime.now().isoformat()})

                # 流式历史压缩
                COMPRESS_THRESHOLD = 120  # 触发压缩的条数
                KEEP_RECENT = 40          # 压缩后保留的最近条数（20 轮）
                if len(self.history) > COMPRESS_THRESHOLD:
                    self._compress_history(KEEP_RECENT, llm)

                if len(self.history) > self.max_history * 2:
                    self.history = self.history[-(self.max_history * 2):]
            self.save_history()
        except Exception as e:
            logger.debug(f"历史更新错误（可忽略）: {e}")

    def _compress_history(self, keep_recent: int = 40, llm=None):
        """
        对话历史流式压缩

        将旧对话（keep_recent 之前的）压缩为一条摘要消息，
        减少 LLM token 消耗，同时保留关键上下文。

        Args:
            keep_recent: 保留的最近条数
            llm: 可选的 LLM 实例（用于生成摘要）
        """
        if len(self.history) <= keep_recent:
            return

        old_messages = self.history[:-keep_recent]
        recent_messages = self.history[-keep_recent:]

        # 统计旧对话轮数
        old_turns = len(old_messages) // 2
        if old_turns < 5:
            return  # 太少不值得压缩

        # 尝试 LLM 摘要
        summary_text = None
        if llm is not None:
            try:
                if hasattr(llm, 'chat'):
                    # 构建摘要 prompt
                    old_text = "\n".join([f"[{m.get('role', '?')}]: {m.get('content', '')}" for m in old_messages[-20:]])
                    summary_prompt = (
                        f"请将以下 {old_turns} 轮对话压缩为一段简短摘要（100字以内），"
                        f"保留关键信息（用户偏好、重要决定、未完成事项）：\n\n{old_text}"
                    )
                    result = llm.chat(summary_prompt, [])
                    summary_text = result.get("text", "").strip() if isinstance(result, dict) else str(result).strip()
            except Exception as e:
                logger.debug(f"LLM 摘要失败，降级为规则摘要: {e}")

        # 降级：规则摘要
        if not summary_text:
            # 提取所有用户消息的关键内容
            user_msgs = [m.get('content', '') for m in old_messages if m.get('role') == 'user']
            assistant_msgs = [m.get('content', '') for m in old_messages if m.get('role') == 'assistant']
            # 取首尾各 3 条作为摘要
            preview = user_msgs[:3] + ["..."] + user_msgs[-3:] if len(user_msgs) > 6 else user_msgs
            summary_text = f"[历史摘要: {old_turns}轮对话] " + " | ".join(preview[:6])

        # 构建压缩后的历史
        compressed = {
            "role": "system",
            "content": summary_text,
            "time": datetime.now().isoformat(),
            "is_compressed": True,
            "original_turns": old_turns
        }
        self.history = [compressed] + recent_messages
        logger.info(f"历史压缩: {old_turns}轮 → 1条摘要 + {len(recent_messages)//2}轮最近对话")

    def get_history_snapshot(self) -> List[Dict]:
        """
        获取历史记录的快照（线程安全）

        Returns:
            List[Dict]: 历史记录的副本
        """
        with self._history_lock:
            return list(self.history)

    def clear_history(self):
        """清空历史记录"""
        with self._history_lock:
            self.history.clear()
        self.save_history()
        logger.info("已清空对话历史")

    def flush(self):
        """强制保存历史记录到磁盘"""
        if self.history:
            try:
                self.save_history()
            except Exception:
                pass
