"""
AI 每日日记/反思系统

每天固定时间自动回顾当天对话，生成反思日记。
支持定期总结和自我提升建议提取。

调度模式: threading.Timer 递归（与 proactive / memory flush 一致）
存储格式: diary/YYYY-MM-DD.md
"""

import os
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, List

_logger = logging.getLogger('Diary')


class DiaryManager:
    """日记管理器 —— 定时自动写日记 + 周度总结"""

    def __init__(self, app):
        """初始化日记管理器

        Args:
            app: AIVTuber 实例，提供 config / memory / llm 访问
        """
        self.app = app
        self._timer: Optional[threading.Timer] = None
        self._running = False
        self._last_diary_date: Optional[str] = None

        # 从配置读取
        config = app.config.config.get("diary", {})
        self.enabled = config.get("enabled", True)
        self.diary_time = config.get("time", "23:00")
        self.max_context = config.get("max_context_items", 30)

        # 日记存储目录 — 项目根目录下 diary/
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.storage_dir = os.path.join(project_dir, "diary")
        os.makedirs(self.storage_dir, exist_ok=True)

    # ========== 调度控制 ==========

    def start(self):
        """启动定时器"""
        if not self.enabled:
            _logger.info("日记系统未启用")
            return
        self._running = True
        _logger.info(f"日记系统已启动，每天 {self.diary_time} 自动写日记")
        self._schedule_next()

    def stop(self):
        """停止定时器"""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        _logger.info("日记系统已停止")

    def _schedule_next(self):
        """计算距离下一次触发时间的秒数，启动 Timer"""
        if not self._running:
            return

        now = datetime.now()
        try:
            parts = self.diary_time.split(":")
            hour, minute = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            hour, minute = 23, 0

        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)

        delay = (target - now).total_seconds()
        self._timer = threading.Timer(delay, self._check_and_write)
        self._timer.daemon = True
        self._timer.start()
        _logger.debug(f"下一次日记触发: {target.strftime('%Y-%m-%d %H:%M')} "
                      f"(约 {delay/3600:.1f} 小时后)")

    def _check_and_write(self):
        """Timer 回调 — 检查是否需要写日记，写完后重新调度"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            if self._last_diary_date != today:
                self._write_diary()
                self._last_diary_date = today
        except Exception as e:
            _logger.error(f"写日记失败: {e}", exc_info=True)
        finally:
            self._schedule_next()

    # ========== 日记编写 ==========

    def _write_diary(self):
        """收集上下文 → 调 LLM → 保存"""
        context = self._collect_today_context()
        if not context or len(context.strip()) < 20:
            _logger.info("今日无足够上下文，跳过日记")
            return

        prompt = self._build_diary_prompt(context)

        try:
            llm_config = self.app.config.config.get("llm", {})
            from llm import LLMFactory
            engine = LLMFactory.create(llm_config)
            result = engine.chat(prompt)
            diary_text = result.get("text", "").strip()
        except Exception as e:
            diary_text = (
                f"# {datetime.now().strftime('%Y-%m-%d')} 日记\n\n"
                f"> ⚠️ LLM 调用失败，无法生成日记。\n\n"
                f"> 错误: {e}\n"
            )
            _logger.error(f"LLM 日记生成失败: {e}")

        if diary_text:
            self._save_diary(diary_text)
            _logger.info(f"日记已保存 ({len(diary_text)} 字)")

    def _collect_today_context(self) -> str:
        """收集今日上下文数据用于 LLM"""
        lines = []
        today = datetime.now().strftime("%Y-%m-%d")
        lines.append(f"# 今日摘要 — {today}\n")

        try:
            mem = self.app.memory
            if mem is None:
                lines.append("(记忆系统未初始化)\n")
                return "".join(lines)

            # 工作记忆（最近对话）
            wm = mem.get_working_memory()
            if wm:
                lines.append("## 今日对话记录\n")
                recent = wm[-self.max_context:] if len(wm) > self.max_context else wm
                for item in recent:
                    role = item.get("role", "unknown")
                    content = item.get("content", "")
                    if content and len(str(content).strip()) > 0:
                        lines.append(f"**{role}**: {content}\n")
            else:
                lines.append("(暂无对话记录)\n")

            # 关键事实
            facts = mem.get_facts()
            if facts:
                recent_facts = facts[-20:]
                lines.append("\n## 已了解的信息\n")
                for f in recent_facts:
                    content = f.get("content", "")
                    if content:
                        lines.append(f"- {content}\n")
        except Exception as e:
            lines.append(f"\n(记忆系统访问异常: {e})\n")

        return "".join(lines)

    def _build_diary_prompt(self, context: str) -> str:
        """构建日记 prompt"""
        return f"""你是一个有自我反思能力的 AI 助手。请基于今天的对话记录，写一篇日记。

要求：
1. 使用第一人称「我」来写
2. 总结今天发生的主要对话和事件（3-5 条）
3. 记录自己的感受和想法
4. 思考今天学到了什么，有什么可以改进的
5. 对明天有什么期待或计划
6. 格式用 Markdown，包含标题和小节
7. 字数控制在 200-500 字

{context}

请开始写今天的日记："""

    def _save_diary(self, content: str):
        """保存日记文件"""
        today = datetime.now().strftime("%Y-%m-%d")
        filepath = os.path.join(self.storage_dir, f"{today}.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    # ========== 读取 & 总结 ==========

    def get_diary(self, date_str: str = None) -> Optional[str]:
        """读取指定日期的日记

        Args:
            date_str: 日期字符串 "YYYY-MM-DD"，默认今天

        Returns:
            日记内容，不存在返回 None
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = os.path.join(self.storage_dir, f"{date_str}.md")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def list_diaries(self) -> List[str]:
        """列出所有已有日记的日期"""
        if not os.path.isdir(self.storage_dir):
            return []
        files = [f for f in os.listdir(self.storage_dir) if f.endswith(".md")]
        return sorted([f.replace(".md", "") for f in files])

    def summarize_week(self, days: int = 7) -> str:
        """对最近 N 天的日记做总结

        Args:
            days: 回顾天数，默认 7

        Returns:
            LLM 生成的总结文本
        """
        diaries = self.list_diaries()
        if not diaries:
            return "还没有日记记录。"

        recent = diaries[-days:]
        all_content = []
        for d in recent:
            content = self.get_diary(d)
            if content:
                all_content.append(f"## {d}\n{content}\n")

        if not all_content:
            return "最近没有日记内容。"

        prompt = f"""请基于以下 {len(recent)} 天的 AI 日记，写一份周度总结：

要求：
1. 这一周的主要成长和收获
2. 反复出现的问题或模式
3. 对下周的具体改进建议
4. 格式用 Markdown

{''.join(all_content)}

请给出周度总结："""

        try:
            from llm import LLMFactory
            llm_config = self.app.config.config.get("llm", {})
            engine = LLMFactory.create(llm_config)
            result = engine.chat(prompt)
            return result.get("text", "").strip()
        except Exception as e:
            return f"[总结生成失败: {e}]"

    def write_now(self) -> Optional[str]:
        """手动触发立即写一篇日记（用于测试或即时需求）

        Returns:
            日记内容，失败返回 None
        """
        try:
            context = self._collect_today_context()
            if not context or len(context.strip()) < 20:
                _logger.info("上下文不足，跳过手动写日记")
                return None
            prompt = self._build_diary_prompt(context)
            llm_config = self.app.config.config.get("llm", {})
            from llm import LLMFactory
            engine = LLMFactory.create(llm_config)
            result = engine.chat(prompt)
            diary_text = result.get("text", "").strip()
            if diary_text:
                self._save_diary(diary_text)
            return diary_text
        except Exception as e:
            _logger.error(f"手动写日记失败: {e}")
            return None
