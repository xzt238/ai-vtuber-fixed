"""
咕咕嘎嘎 AI 主动说话模块 (Proactive Speech Manager)

v1.9.51: 新增功能
当用户长时间不说话时，AI 会根据记忆和上下文主动开口说话。

设计思路:
    1. 空闲检测: 追踪 last_user_activity_time，超时后触发
    2. 上下文感知: 利用记忆系统检索最近话题、用户偏好等
    3. 自然语气: 专用 prompt 引导 AI 用闲聊口吻主动说话
    4. 频率控制: 最小间隔 + 每日上限 + 说话中不打断
    5. 随机延迟: 避免机械式固定时间触发

触发条件（全部满足才触发）:
    - 距上次用户消息超过 idle_timeout 秒
    - AI 当前未在说话（realtime pipeline 不活跃）
    - 距上次主动说话超过 min_interval 秒
    - 今日主动说话次数未达上限
    - WebSocket 客户端已连接

线程安全:
    所有状态修改都在 _check_and_trigger 中进行，
    由定时器线程调用，无需额外加锁（Python GIL 足够）。
"""

import time
import threading
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from main import AIVTuber


# 主动说话专用 prompt（不暴露给用户）
PROACTIVE_PROMPT_TEMPLATE = """你已经有一段时间没有和用户交流了。根据你们的记忆和最近的对话，主动说点什么吧。

要求：
- 像朋友闲聊一样自然，不要说"我主动来找你聊天"这种话
- 可以延续之前的话题、分享一个想法、或者简单地打个招呼
- 保持你活泼可爱的性格
- 话语简短自然，1-2句话就好，不要长篇大论
- 如果最近有有趣的话题，可以顺着聊下去
"""

# 时间感知 prompt 补充
TIME_CONTEXT_TEMPLATE = {
    "morning": "现在是早上，可以用朝气蓬勃的语气。",
    "afternoon": "现在是下午，可以用轻松的语气。",
    "evening": "现在是傍晚，可以用温馨的语气。",
    "night": "现在是晚上，可以用安静的语气，关心用户是否该休息了。",
    "late_night": "已经很晚了，可以关心用户怎么还没睡。",
}


class ProactiveSpeechManager:
    """
    AI 主动说话管理器

    配置来源: config.yaml → proactive_speech 节
    默认值: enabled=false, idle_timeout=120, min_interval=300, max_daily_count=15
    """

    def __init__(self, app: "AIVTuber"):
        self.app = app
        self.logger = app.logger

        # 从配置读取参数
        cfg = app.config.config.get("proactive_speech", {})
        self.enabled = cfg.get("enabled", False)
        self.idle_timeout = cfg.get("idle_timeout", 120)       # 空闲多少秒触发
        self.min_interval = cfg.get("min_interval", 300)        # 两次主动说话最小间隔（秒）
        self.max_daily_count = cfg.get("max_daily_count", 15)   # 每日主动说话上限
        self.randomize_range = cfg.get("randomize_range", 30)   # 随机延迟范围（秒）
        self.check_interval = cfg.get("check_interval", 30)     # 检查间隔（秒）

        # 运行状态
        self._last_user_activity = time.time()  # 上次用户活动时间
        self._last_proactive_time = 0.0          # 上次主动说话时间
        self._daily_count = 0                     # 今日主动说话次数
        self._daily_count_date = ""               # 今日日期（用于每日重置）
        self._timer = None                        # 定时器
        self._running = False                     # 是否正在运行
        self._lock = threading.Lock()             # 保护 _running 状态
        self._native_callback = None               # v1.9.80: 原生桌面模式回调函数

        if self.enabled:
            self.logger.info(f"[主动说话] 已启用: idle={self.idle_timeout}s, min_interval={self.min_interval}s, max_daily={self.max_daily_count}")
        else:
            self.logger.info("[主动说话] 未启用 (proactive_speech.enabled=false)")

    def start(self, interval=None):
        """启动主动说话定时器

        Args:
            interval: 可选，覆盖 min_interval（秒）。用于 UI 动态调整间隔。
        """
        if interval is not None:
            self.min_interval = max(10, interval)
            self.logger.info(f"[主动说话] 间隔已更新为 {self.min_interval}s")

        if not self.enabled:
            return
        with self._lock:
            if self._running:
                return
            self._running = True
        self._schedule_next()
        self.logger.info("[主动说话] 定时器已启动")

    def stop(self):
        """停止主动说话定时器"""
        with self._lock:
            self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        self.logger.info("[主动说话] 定时器已停止")

    def notify_user_activity(self):
        """
        通知用户有活动（发消息/说话等）
        更新 last_user_activity_time，防止在用户刚说完就主动开口
        """
        self._last_user_activity = time.time()

    def _schedule_next(self):
        """安排下一次检查"""
        with self._lock:
            if not self._running:
                return
        self._timer = threading.Timer(self.check_interval, self._check_and_trigger)
        self._timer.daemon = True
        self._timer.start()

    def _check_and_trigger(self):
        """定时检查是否应该主动说话

        v1.9.64 修复：移除 try 块内的 _schedule_next() 调用，
        只保留 finally 中的统一调度。之前的写法导致双重调度：
        try 中 return 前调用 _schedule_next() + finally 再调用一次
        → 每次2个Timer → 指数级线程爆炸 → CPU/内存爆满
        """
        try:
            with self._lock:
                if not self._running:
                    return

            now = time.time()

            # 1. 检查空闲时间
            idle_seconds = now - self._last_user_activity
            if idle_seconds < self.idle_timeout:
                return  # 还没到空闲阈值，跳过（由 finally 统一调度）

            # 2. 检查最小间隔
            since_last_proactive = now - self._last_proactive_time
            if since_last_proactive < self.min_interval:
                return

            # 3. 检查每日上限
            self._check_daily_reset(now)
            if self._daily_count >= self.max_daily_count:
                return

            # 4. 检查 AI 是否正在说话
            if self._is_ai_speaking():
                return

            # 5. 检查 WebSocket 客户端是否连接
            if not self._has_connected_client():
                return

            # 所有条件满足，触发主动说话
            self.logger.info(f"[主动说话] 触发! 空闲 {idle_seconds:.0f}s, 今日第 {self._daily_count + 1} 次")
            self._do_proactive_speech()

        except Exception as e:
            self.logger.error(f"[主动说话] 检查异常: {e}")
        finally:
            # 无论是否触发，都安排下一次检查（唯一调度点）
            self._schedule_next()

    def _is_ai_speaking(self) -> bool:
        """检查 AI 是否正在说话"""
        try:
            # 检查 web 模块的 realtime 状态
            ws_server = getattr(self.app, '_lazy_modules', {}).get('ws_server')
            if ws_server:
                # 检查是否有客户端正在 realtime pipeline 中
                realtime_states = getattr(ws_server, '_realtime', {})
                for client_id, state in realtime_states.items():
                    if state.get("speaking") or state.get("running"):
                        return True
                # 检查是否有文本生成线程正在运行
                text_gens = getattr(ws_server, '_text_gen_running', {})
                for client_id, running in text_gens.items():
                    if running:
                        return True
        except Exception:
            pass
        return False

    def _has_connected_client(self) -> bool:
        """检查是否有 WebSocket 客户端连接，或原生桌面模式"""
        try:
            # v1.9.80: 原生桌面模式检测 — 如果设置了 native_callback，说明运行在原生模式
            if self._native_callback:
                return True

            ws_server = getattr(self.app, '_lazy_modules', {}).get('ws_server')
            if ws_server and hasattr(ws_server, 'server'):
                clients = getattr(ws_server.server, 'clients', [])
                return len(clients) > 0
        except Exception:
            pass
        return False

    def _check_daily_reset(self, now: float):
        """检查是否需要重置每日计数"""
        import datetime
        today = datetime.date.fromtimestamp(now).isoformat()
        if today != self._daily_count_date:
            self._daily_count = 0
            self._daily_count_date = today

    def _get_time_context(self) -> str:
        """获取当前时间段的语境描述"""
        import datetime
        hour = datetime.datetime.now().hour
        if 6 <= hour < 12:
            return TIME_CONTEXT_TEMPLATE["morning"]
        elif 12 <= hour < 18:
            return TIME_CONTEXT_TEMPLATE["afternoon"]
        elif 18 <= hour < 22:
            return TIME_CONTEXT_TEMPLATE["evening"]
        elif 22 <= hour < 24:
            return TIME_CONTEXT_TEMPLATE["night"]
        else:
            return TIME_CONTEXT_TEMPLATE["late_night"]

    def _do_proactive_speech(self):
        """执行主动说话"""
        try:
            # 更新状态
            self._last_proactive_time = time.time()
            self._daily_count += 1

            # 构建主动说话的 prompt
            time_context = self._get_time_context()
            proactive_prompt = PROACTIVE_PROMPT_TEMPLATE + "\n" + time_context

            # 从记忆系统获取最近话题（如果有）
            memory_context = self._get_memory_context()
            if memory_context:
                proactive_prompt += f"\n\n最近的记忆参考:\n{memory_context}"

            # 调用 LLM 生成主动说话内容
            # 使用精简的 history（不需要全部历史，最近几轮即可）
            recent_history = list(self.app.history[-6:]) if self.app.history else []
            result = self.app.llm.chat(proactive_prompt, recent_history)
            reply = result.get("text", "").strip()

            if not reply:
                self.logger.info("[主动说话] LLM 返回空内容，跳过")
                return

            # 过滤掉可能的工具调用格式
            import re
            reply = re.sub(r'```[\s\S]*?```', '', reply)
            lines = [l for l in reply.split('\n') if not any(kw in l for kw in ['TOOL:', 'ARG:', 'BASH:', 'READ:', 'WRITE:', 'EDIT:'])]
            reply = '\n'.join(lines).strip()

            if not reply:
                return

            self.logger.info(f"[主动说话] 内容: {reply[:50]}...")

            # v1.9.80: 优先使用原生回调（桌面模式）
            if self._native_callback:
                try:
                    self._native_callback(reply)
                    self.logger.info("[主动说话] 已通过原生回调推送")
                except Exception as cb_err:
                    self.logger.error(f"[主动说话] 原生回调失败: {cb_err}")
            else:
                # 通过 WebSocket 推送给前端（WebUI 模式）
                self._push_to_clients(reply)

            # 写入记忆和历史（统一使用 record_interaction，确保 MAX_HISTORY 截断等逻辑一致）
            try:
                self.app.record_interaction("[主动说话触发]", reply)
            except Exception as e:
                self.logger.warning(f"[主动说话] 记录交互失败: {e}")

            # 触发 TTS
            if self._native_callback:
                # 原生模式：TTS 由回调侧处理（chat_page 的 _on_proactive_speech 会播放）
                pass
            else:
                # WebUI 模式：通过 WebSocket 发送音频 URL
                self._trigger_tts(reply)

        except Exception as e:
            self.logger.error(f"[主动说话] 执行失败: {e}")

    def _get_memory_context(self) -> str:
        """从记忆系统获取上下文，为主动说话提供话题"""
        try:
            mem = getattr(self.app, 'memory', None)
            if mem is None:
                return ""

            # 获取工作记忆中的最近对话
            working = mem.get_working_memory()
            if working:
                # 取最近 5 条作为参考
                recent = working[-5:]
                items = []
                for item in recent:
                    role = item.get("role", "?")
                    content = item.get("content", "")[:80]  # 截断
                    items.append(f"[{role}] {content}")
                return "\n".join(items)

            return ""
        except Exception:
            return ""

    def _push_to_clients(self, text: str):
        """通过 WebSocket 推送消息给所有连接的客户端"""
        try:
            ws_server = getattr(self.app, '_lazy_modules', {}).get('ws_server')
            if not ws_server or not hasattr(ws_server, 'server'):
                return

            import json
            clients = getattr(ws_server.server, 'clients', [])
            for client in clients:
                try:
                    ws_server.server.send_message(client, json.dumps({
                        "type": "text",
                        "text": text,
                        "proactive": True  # 标记为主动说话
                    }))
                except Exception:
                    pass
        except Exception as e:
            self.logger.error(f"[主动说话] 推送失败: {e}")

    def _trigger_tts(self, text: str):
        """触发 TTS 语音合成，发送音频给前端"""
        try:
            ws_server = getattr(self.app, '_lazy_modules', {}).get('ws_server')
            if not ws_server:
                return

            import json, os

            # 获取默认 TTS 引擎
            tts_engine = self.app.tts
            if not tts_engine or not tts_engine.is_available():
                return

            # 合成语音
            audio_path = tts_engine.speak(text)
            if not audio_path or not os.path.exists(audio_path):
                return

            # 发送音频 URL 给前端
            audio_url = "/audio/" + os.path.basename(audio_path)

            clients = getattr(ws_server.server, 'clients', [])
            for client in clients:
                try:
                    ws_server.server.send_message(client, json.dumps({
                        "type": "tts_done",
                        "audio": audio_url,
                        "proactive": True
                    }))
                except Exception:
                    pass

        except Exception as e:
            self.logger.error(f"[主动说话] TTS 触发失败: {e}")
