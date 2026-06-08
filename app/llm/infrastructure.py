"""
LLM 基础设施模块

包含 RateLimiter（速率限制）、RetryStrategy（重试策略）和 StreamAccumulator（流式累积器）。
"""

import json
import time
import logging
import threading
import random
from typing import Optional, Dict, Any, List, Callable
from collections import deque

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    速率限制器 - 滑动窗口算法

    【设计意图】
    使用滑动时间窗口（而非固定窗口）控制 API 请求频率，避免在窗口边界处
    集中爆发大量请求（固定窗口算法的缺陷）。

    【v1.8 修复】
    原版使用 Lock + sleep 实现等待，但 sleep 期间持有锁会阻塞其他线程的
    acquire() 调用，造成死锁风险。v1.8 改用 threading.Condition.wait() 实现
    等待，wait() 会临时释放底层锁，允许其他线程进入临界区。

    【算法说明】
    维护一个 deque，存储最近 window_seconds 秒内所有请求的时间戳。
    acquire() 时：
    1. 清理超出时间窗口的旧时间戳
    2. 如果当前窗口内请求数 < max_requests，记录时间戳并返回 True
    3. 否则用 Condition.wait() 等待最旧的请求"过期"后重试
    """
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        """
        【功能说明】初始化速率限制器

        【参数说明】
            max_requests (int): 时间窗口内允许的最大请求数，默认 60
            window_seconds (int): 时间窗口大小（秒），默认 60
                                  即"每分钟最多 max_requests 次请求"
        """
        self.max_requests = max_requests        # 窗口内最大请求数
        self.window_seconds = window_seconds    # 滑动时间窗口大小（秒）
        self.requests = deque()                 # 请求时间戳队列（双端，支持 O(1) 左端删除）
        # Condition 包含 Lock，同时提供 wait()/notify_all() 通知机制
        self._condition = threading.Condition(threading.Lock())
    
    def acquire(self, timeout: int = 30) -> bool:
        """
        【功能说明】申请一个请求配额（阻塞等待直到配额可用或超时）

        【参数说明】
            timeout (int): 最长等待时间（秒），默认 30

        【返回值】
            bool: 成功获取配额返回 True；超时返回 False

        【v1.8 核心修复说明】
        旧版实现：
            with lock:
                while not enough_quota:
                    sleep(wait_time)   # 持锁 sleep！其他线程无法进入
        
        新版实现：
            with condition:
                while not enough_quota:
                    condition.wait(timeout=wait_time)  # 释放锁等待，其他线程可进入
        """
        # 计算超时绝对时间（用绝对时间比用相对时间更安全，避免多次 wait 累积误差）
        deadline = time.time() + timeout
        
        with self._condition:
            while True:
                now = time.time()
                # 计算时间窗口的起始时间点（now - window_seconds）
                cutoff = now - self.window_seconds
                
                # 清理超出时间窗口的旧请求记录（deque 左端为最旧）
                while self.requests and self.requests[0] < cutoff:
                    self.requests.popleft()
                
                # 当前窗口内请求数未超限，分配配额并记录时间戳
                if len(self.requests) < self.max_requests:
                    self.requests.append(now)
                    return True
                
                # 计算需要等待多久才能有新配额（最旧请求过期的时间）
                wait_time = self.requests[0] - cutoff
                # 计算距离超时还剩多少时间
                remaining = deadline - now
                
                # 超时或等待时间超过剩余时间，放弃等待
                if remaining <= 0 or wait_time > remaining:
                    return False  # 超时，拒绝请求
                
                # 【关键：释放锁并等待】
                # Condition.wait() 会临时释放底层锁，让其他线程能进入临界区
                # 等待时间结束后（或被 notify() 唤醒）重新获取锁，继续循环
                self._condition.wait(timeout=min(wait_time, remaining))
    
    def reset(self) -> None:
        """
        【功能说明】重置速率限制器（清空所有请求记录并唤醒等待中的线程）

        【返回值】
            无

        【使用场景】
        系统重启、配置更改、或手动解除限速时调用。
        notify_all() 确保所有因 acquire() 阻塞的线程都被唤醒，
        重新参与竞争（v1.8 新增）
        """
        with self._condition:
            self.requests.clear()
            # 唤醒所有在 wait() 中等待的线程，让它们重新检查配额
            self._condition.notify_all()


class RetryStrategy:
    """
    重试策略 - 指数退避 + 随机抖动

    【设计意图】
    网络请求失败时，不立即重试（可能会加剧服务器压力），而是按指数增长的
    间隔等待后重试。加入随机抖动（jitter）防止多个客户端同时重试（雷群效应）。

    【指数退避公式】
    delay = base_delay × 2^attempt + random(0, 0.5)
    第1次重试：~1s，第2次：~2s，第3次：~4s（上限 max_delay）
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0) -> None:
        """
        【功能说明】初始化重试策略

        【参数说明】
            max_retries (int): 最大重试次数（不含首次请求），默认 3
            base_delay (float): 基础延迟时间（秒），默认 1.0
            max_delay (float): 单次等待的最大延迟（秒），默认 10.0
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def should_retry(self, attempt: int, error: Exception) -> bool:
        """
        【功能说明】判断当前错误是否应该重试

        【参数说明】
            attempt (int): 当前尝试次数（从 0 开始，0=首次请求）
            error (Exception): 发生的异常

        【返回值】
            bool: True=应该重试，False=放弃

        【可重试错误类型】
        - 网络超时/连接错误：transient 网络问题，重试可能成功
        - 429 Too Many Requests：速率限制，等待后重试
        - 502/503 Bad Gateway/Service Unavailable：服务暂时不可用

        【不可重试错误】
        - 401/403 认证授权错误（重试无意义）
        - 400 参数错误（重试无意义）
        - 超出最大重试次数
        """
        # 已达最大重试次数，停止重试
        if attempt >= self.max_retries:
            return False
        # 将错误信息转小写，便于关键词匹配
        error_msg = str(error).lower()
        # 可重试的错误关键词列表
        retryable = [
            "timeout",          # 超时
            "connection",       # 连接错误
            "reset",            # 连接重置
            "refused",          # 连接拒绝
            "429", " 429",      # Too Many Requests（速率限制）
            "too many requests",
            "rate limit",       # 速率限制提示
            "503", "502",       # 服务不可用 / 网关错误
        ]
        # 只要错误信息包含任意一个关键词，就认为可以重试
        return any(r in error_msg for r in retryable)
    
    def get_delay(self, attempt: int) -> float:
        """
        【功能说明】计算当前重试的等待时间（指数退避 + 随机抖动）

        【参数说明】
            attempt (int): 当前尝试次数（从 0 开始）

        【返回值】
            float: 等待时间（秒），不超过 max_delay

        【计算公式】
        delay = min(base_delay × 2^attempt + random(0, 0.5), max_delay)
        - attempt=0: ~1.0-1.5s
        - attempt=1: ~2.0-2.5s  
        - attempt=2: ~4.0-4.5s
        """
        # 指数增长的基础延迟
        delay = self.base_delay * (2 ** attempt)
        # 加入随机抖动（0~0.5秒），防止多客户端雷群效应
        jitter = random.uniform(0, 0.5)
        # 限制最大等待时间
        return min(delay + jitter, self.max_delay)


# ==================== 流式处理公共逻辑 =====================

class StreamAccumulator:
    """
    SSE 流式处理辅助类 — thinking 过滤 + buffer 管理 + tool_calls 累积

    【设计意图】
    将 MiniMax/OpenAI/Anthropic 三种引擎的 stream_chat 中重复的公共逻辑
    提取到此类，消除 6 处以上重复代码：
    1. Qwen3 thinking 标签过滤（<think>...</think>）
    2. buffer 管理 + callback 触发（chunk_size 阈值）
    3. tool_calls delta 累积（FC Function Calling）
    4. 流结束处理：_clean_response + 空回复兜底 + buffer flush + action 解析
    5. FC 执行 + 结果合并

    【使用方式】
    acc = StreamAccumulator(chunk_size=10, callback=callback)
    for chunk in stream:
        content = extract_content(chunk)
        if content:
            acc.process_content(content)
        # FC 累积
        for tc_delta in delta_tool_calls:
            acc.accumulate_tool_call(tc_delta)
    # 流结束
    return acc.finish(response)
    # 或含 FC:
    return acc.finish_with_fc(messages, session, base_url, model, api_key, max_tokens)
    """

    def __init__(self, chunk_size: int = 10, callback=None, on_tool_call=None, filter_thinking: bool = True) -> None:
        """
        【功能说明】初始化流式累积器

        【参数说明】
            chunk_size (int): 触发回调的字符数阈值，默认 10
            callback: 流式回调函数，每积累 chunk_size 个字符时调用一次
            on_tool_call: FC 工具调用状态回调，signature: fn(tool_name, display_text, args)
            filter_thinking (bool): 是否过滤 thinking 标签，默认 True
                                    Anthropic 引擎不输出 thinking 标签，可设为 False
        """
        self.full_text: str = ""            # 完整回复文本（累积）
        self.buffer: str = ""               # 待触发回调的缓冲区
        self.in_thinking: bool = False      # Qwen3 thinking 标签跟踪
        self.tool_calls_accum: dict = {}    # FC 累积 tool_calls（按 index 分组）
        self.chunk_size: int = chunk_size
        self.callback = callback
        self.on_tool_call = on_tool_call
        self.filter_thinking: bool = filter_thinking
        self.finish_reason: str = ""        # 外部设置：SSE 流的 finish_reason

    def process_content(self, content: str) -> None:
        """
        【功能说明】处理一个 content 片段：thinking 过滤 + 累积 + 触发回调

        【参数说明】
            content (str): 增量文本内容

        【执行流程】
        1. 如果启用 thinking 过滤，检测 <think> 标签并跳过 thinking 内容
        2. 累积到 full_text 和 buffer
        3. buffer 达到 chunk_size 时触发 callback
        """
        # thinking 过滤（仅当 filter_thinking=True 时生效）
        if self.filter_thinking:
            if "<think" in content and ">" in content:
                self.in_thinking = True
            if self.in_thinking and "</think" in content and ">" in content:
                self.in_thinking = False
                content = re.sub(r"</think\s*>", "", content)
                if not content.strip():
                    return
            if self.in_thinking:
                return

        # 累积到完整文本 + 缓冲区
        self.full_text += content
        self.buffer += content
        # 缓冲区达到阈值时触发回调（通知 TTS 开始合成）
        if len(self.buffer) >= self.chunk_size and self.callback:
            self.callback(self.buffer)
            self.buffer = ""

    def accumulate_tool_call(self, tc_delta: dict) -> None:
        """
        【功能说明】累积一个 tool_call delta（FC Function Calling）

        【参数说明】
            tc_delta (dict): OpenAI SSE 格式的 tool_call 增量
                - index: tool_calls 数组索引
                - id: 工具调用 ID（可选，首次出现时设置）
                - function.name: 函数名称增量
                - function.arguments: 函数参数增量

        【设计意图】
        OpenAI 的 tool_calls 在 SSE 中分多个 chunk 传输，需要按 index 累积
        才能得到完整的工具调用信息。
        """
        idx = tc_delta.get("index", 0)
        if idx not in self.tool_calls_accum:
            self.tool_calls_accum[idx] = {
                "id": "",
                "type": "function",
                "function": {"name": "", "arguments": ""}
            }
        if tc_delta.get("id"):
            self.tool_calls_accum[idx]["id"] = tc_delta["id"]
        func_delta = tc_delta.get("function", {})
        if func_delta.get("name"):
            self.tool_calls_accum[idx]["function"]["name"] += func_delta["name"]
        if func_delta.get("arguments"):
            self.tool_calls_accum[idx]["function"]["arguments"] += func_delta["arguments"]

    def flush(self) -> None:
        """【功能说明】发送缓冲区中剩余的文本片段"""
        if self.buffer and self.callback:
            self.callback(self.buffer)
            self.buffer = ""

    def finish(self, response=None, use_clean_response: bool = True) -> dict:
        """
        【功能说明】流结束处理：buffer flush + 回复清理 + 空回复兜底 + action 解析

        【参数说明】
            response: HTTP 响应对象（用于 thinking 空回复检测，可选）
            use_clean_response (bool): 是否使用 _clean_response（含 thinking 清理），
                                       默认 True。Anthropic 引擎使用 False（调用 _parse_action）

        【返回值】
            dict: {"text": 完整回复文本, "action": 动作指令或 None}
        """
        self.flush()

        if use_clean_response:
            full_text, action_str = _clean_response(self.full_text)
        else:
            full_text = self.full_text
            action_str = _parse_action(full_text)

        # 空回复检查
        if not full_text:
            if self.in_thinking or _THINK_RE.search(response.text if hasattr(response, 'text') else ""):
                full_text = "（LLM 只输出了思考内容，未生成回复，请重试）"
            else:
                full_text = "（LLM 未返回有效回复，请重试）"

        action = json.loads(action_str) if action_str else None
        return {"text": full_text, "action": action}

    def finish_with_fc(self, messages, session, base_url, model, api_key, max_tokens,
                       on_chunk=None, response=None) -> dict:
        """
        【功能说明】流结束 + FC 处理：检查 tool_calls → 执行 → 合并结果

        【参数说明】
            messages: 完整消息列表（FC 重新请求时使用）
            session: requests.Session（FC HTTP 请求用）
            base_url: API 基础 URL
            model: 模型名称
            api_key: API Key
            max_tokens: 最大 token 数
            on_chunk: FC 回调（默认使用 self.callback）
            response: HTTP 响应对象（传递给 finish，可选）

        【返回值】
            dict: {"text": 回复文本, "action": 动作或 None, "_ui_actions": UI 动作列表（可选）}

        【执行流程】
        1. 检查 finish_reason == "tool_calls" 且有累积的 tool_calls
        2. 调用 fc_executor 执行工具
        3. 合并工具结果到回复
        4. 无 tool_calls 时走普通 finish
        """
        # 检查是否有 tool_calls 需要执行
        if self.tool_calls_accum and self.finish_reason == "tool_calls":
            tool_calls_list = [self.tool_calls_accum[i] for i in sorted(self.tool_calls_accum.keys())]
            logger.info(f"[LLM] FC 检测到 {len(tool_calls_list)} 个工具调用")
            try:
                from app.tools.fc_executor import handle_tool_calls_stream
                fc_result = handle_tool_calls_stream(
                    tool_calls=tool_calls_list,
                    messages=messages,
                    session=session,
                    base_url=base_url,
                    model=model,
                    api_key=api_key,
                    max_tokens=max_tokens,
                    on_chunk=on_chunk or self.callback,
                    chunk_size=self.chunk_size,
                    on_tool_call=self.on_tool_call,
                )
                fc_text = fc_result.get("text", "")
                _ui_actions = fc_result.get("_ui_actions", [])
                if fc_text:
                    return {"text": fc_text, "action": None, "_ui_actions": _ui_actions}
                tool_summary_parts = []
                for tr in fc_result.get("tool_results", []):
                    tool_summary_parts.append(tr.get("result", {}).get("content", ""))
                return {"text": "\n".join(tool_summary_parts) or "工具已执行", "action": None, "_ui_actions": _ui_actions}
            except Exception as e:
                logger.info(f"[LLM] FC 执行失败: {e}")
                if self.full_text:
                    return {"text": self.full_text, "action": None}
                # v1.9.99: FC 失败且无文本时，返回错误信息而非空字符串
                return {"text": "工具执行出错", "action": None}

        # 无 tool_calls，走普通 finish
        return self.finish(response)


# ==================== LLM 引擎基类 =====================

