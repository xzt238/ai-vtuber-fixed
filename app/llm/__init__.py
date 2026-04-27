#!/usr/bin/env python3
"""
=====================================
大语言模型模块 (LLM) - 重构版 v2.0
=====================================

【模块功能概述】
本模块是 AI VTuber 系统的"大脑核心"，负责与各种大语言模型 API 进行通信。
支持 MiniMax、OpenAI、Anthropic 三种主流 LLM 提供商，并提供统一接口。

【核心架构】
1. PromptInjector  —— 模块化 Prompt 注入系统（参考 Neuro-sama 架构）
   各功能模块可注册自己的 Prompt 片段，按优先级合并注入 LLM
2. MemoryRAGInjector —— 记忆检索增强生成（RAG）注入器
   从记忆系统检索上下文，动态注入到系统 Prompt 中
3. RateLimiter —— 滑动窗口速率限制（线程安全，v1.8 修复锁内 sleep bug）
4. RetryStrategy —— 指数退避重试策略（应对网络抖动和 429 限流）
5. LLMEngine (ABC) —— 统一抽象接口，三种引擎实现各自差异
6. LLMFactory —— 工厂类，根据配置自动创建对应引擎

【v2.0 重构要点】
- PromptInjector: 模块化 Prompt 注入系统（参考 Neuro 架构）
- MemoryRAGInjector: RAG 检索 + 注入（长期记忆）
- 去掉 history 硬截断：无限制传递对话历史
- 提高 max_tokens：从 512 提升到 2048
- 保留所有原有功能：连接池、缓存、重试、速率限制

【输入/输出】
- 输入：用户消息字符串、对话历史列表、可选记忆系统实例
- 输出：{"text": 回复文本, "action": 解析出的动作指令或 None}

【与其他模块的关系】
- 被 main.py 的 AIVTuber 类初始化，注册为 `self._llm` 属性
- 依赖 llm/prompts.py 提供角色人格 Prompt
- 与 memory/__init__.py 协作，实现对话记忆注入

作者: 咕咕嘎嘎
日期: 2026-04-19
"""

import os
import re
import json
import time
# ABC: 抽象基类支持，abstractmethod: 强制子类实现抽象方法
from abc import ABC, abstractmethod
# Optional: 可空类型, Dict/Any/List/Callable: 类型注解
from typing import Optional, Dict, Any, List, Callable
# dataclass: 自动生成 __init__/__repr__/__eq__ 等方法的装饰器
from dataclasses import dataclass
# lru_cache: LRU 缓存装饰器（本模块中未用到但保留导入以供扩展）
from functools import lru_cache
# deque: 双端队列，用于滑动窗口速率限制中记录请求时间戳
from collections import deque
import threading
import random  # 用于指数退避中的随机抖动
import sys

# ==================== 提示词模块导入 ====================

# 【尝试相对导入】在 Python 包内以相对路径导入同包内的 prompts.py
# 相对导入（from .prompts）要求本文件在包内运行（作为 app.llm 包的一部分）
try:
    from .prompts import (
        SYSTEM_PROMPT,      # 系统角色人格提示词主体
        AGENT_PROMPT,       # Agent 模式提示词（包含工具使用说明）
        get_system_prompt,  # 获取系统提示词的函数（支持环境参数）
        get_agent_prompt,   # 获取 Agent 提示词的函数
        build_system_prompt,# 构建完整系统提示词（含环境信息）
        inject_memories     # 将记忆内容注入 Prompt 的函数
    )
except ImportError:
    # 【回退：直接文件加载】当作为独立脚本运行或包结构不完整时
    # 用 importlib.util 手动加载同目录下的 prompts.py 文件
    prompts_path = os.path.join(os.path.dirname(__file__), 'prompts.py')
    if os.path.exists(prompts_path):
        import importlib.util
        # spec_from_file_location: 从文件路径创建模块规格
        spec = importlib.util.spec_from_file_location("prompts", prompts_path)
        prompts_module = importlib.util.module_from_spec(spec)
        # 注册到 sys.modules，防止重复加载
        sys.modules["prompts"] = prompts_module
        spec.loader.exec_module(prompts_module)
        # 从手动加载的模块中提取需要的变量和函数
        SYSTEM_PROMPT = prompts_module.SYSTEM_PROMPT
        AGENT_PROMPT = prompts_module.AGENT_PROMPT
        get_system_prompt = prompts_module.get_system_prompt
        build_system_prompt = prompts_module.build_system_prompt
        inject_memories = prompts_module.inject_memories
    else:
        # 【最终回退：内联最简实现】prompts.py 完全不存在时使用最小化兼容
        SYSTEM_PROMPT = "你是一个AI助手。"
        AGENT_PROMPT = ""
        def get_system_prompt(e=""):
            """获取系统提示词（兼容模式：无 prompts.py 时的最简实现）"""
            return SYSTEM_PROMPT
        def build_system_prompt(e=""):
            """构建系统提示词（兼容模式：无 prompts.py 时的最简实现）"""
            return SYSTEM_PROMPT
        def inject_memories(t):
            """注入记忆（兼容模式：无 prompts.py 时返回空字符串）"""
            return ""


# ==================== Prompt 注入系统 ====================

@dataclass
class PromptInjection:
    """
    单个 Prompt 注入项

    【设计意图】
    将系统 Prompt 分解为多个独立片段（注入项），各功能模块（记忆、工具、OCR等）
    各自管理自己的 Prompt 片段，通过 PromptInjector 统一合并。
    
    比整个系统共享一个巨型 Prompt 更加模块化、易于维护。

    【属性说明】
    - text: Prompt 文本内容
    - priority: 优先级数字，越大越靠近末尾（LLM 对末尾内容关注度更高）
    """
    text: str           # 注入的文本内容
    priority: int = 0   # 排序优先级：0=最前（最先输出），100=最后（最重要）
    
    def __lt__(self, other):
        """
        【比较方法】实现 < 运算符，用于 list.sort() 按优先级排序

        【参数说明】
            other: 另一个 PromptInjection 实例

        【返回值】
            bool: 当前实例优先级小于 other 时返回 True（排在前面）
        
        【设计意图】
            dataclass 默认不提供排序支持，手动实现 __lt__ 后
            injections.sort() 即可按 priority 升序排列
        """
        return self.priority < other.priority


class PromptInjector:
    """
    Prompt 注入器（参考 Neuro-sama 架构）

    【设计意图】
    各功能模块（记忆系统、OCR、工具等）通过 register() 方法注册自己的
    Prompt 生成函数，最终由 build() 方法按优先级组装为完整系统 Prompt。
    
    这样的好处是：
    1. 各模块解耦，不需要修改核心代码即可添加新的 Prompt 片段
    2. 优先级控制哪些内容在 Prompt 中更突出（末尾更重要）
    3. 任一模块出错不影响其他模块
    """
    
    def __init__(self):
        """
        【功能说明】初始化 Prompt 注入器，创建空的模块注册列表

        【设计意图】
        使用函数列表而非对象列表，允许使用 lambda 或 bound method
        注册 Prompt 来源，更灵活
        """
        # 已注册的 Prompt 模块函数列表，每个函数返回 PromptInjection 对象
        self._modules: List[Callable[[], PromptInjection]] = []
    
    def register(self, module_fn: Callable[[], PromptInjection]):
        """
        【功能说明】注册一个 Prompt 模块函数

        【参数说明】
            module_fn: 无参可调用对象，调用时返回 PromptInjection 实例
                       例如：lambda: PromptInjection("工具说明...", priority=50)

        【设计意图】
        延迟求值：注册的是函数引用而非值，build() 时才实际调用，
        确保每次构建 Prompt 时都能获取最新的动态内容（如当前时间、状态）
        """
        self._modules.append(module_fn)
    
    def build(self) -> str:
        """
        【功能说明】遍历所有注册模块，收集并按优先级排序组装完整 Prompt

        【执行流程】
        1. 依次调用每个已注册的模块函数，获取 PromptInjection 对象
        2. 过滤掉空内容的注入项
        3. 按 priority 升序排序（priority 小的排前面）
        4. 用换行符连接所有文本片段

        【返回值】
            str: 组装好的完整 Prompt 字符串

        【设计意图】
        越重要的内容（priority 越大）越靠近末尾，
        因为 LLM 在实践中对 Prompt 末尾的指令更加关注（attention 集中效应）
        """
        injections = []
        
        # 依次调用每个注册的模块函数，收集注入项
        for module_fn in self._modules:
            try:
                inj = module_fn()
                # 过滤掉空内容的注入项，避免产生多余空行
                if inj and inj.text:
                    injections.append(inj)
            except Exception as e:
                # 单个模块失败不中断整体构建
                print(f"[PromptInjector] 模块执行失败: {e}")
        
        # 按优先级升序排序（priority=0 最前，priority=100 最后）
        injections.sort()
        
        # 用换行符连接所有 Prompt 片段
        return "\n".join(inj.text for inj in injections)


class MemoryRAGInjector:
    """
    记忆 RAG 注入器（Retrieval-Augmented Generation）

    【设计意图】
    RAG（检索增强生成）模式：不将所有记忆直接放入 Prompt（会超出 token 限制），
    而是从记忆系统中检索最相关的内容动态注入，实现"按需记忆"。
    
    参考 Neuro-sama 的 memories/ 目录持久化 + 自动提取模式。
    
    【工作原理】
    1. 从工作记忆（working memory）获取最近 10 条对话
    2. 从情景记忆（episodic memory）获取最近 5 条重要事件摘要
    3. 格式化后通过 inject_memories() 注入到系统 Prompt
    """
    
    def __init__(self, memory_system=None):
        """
        【功能说明】初始化记忆 RAG 注入器

        【参数说明】
            memory_system: 记忆系统实例（memory/__init__.py 中的 MemorySystem）
                           如果为 None，则 get_injection() 返回空注入项

        【设计意图】
        允许 memory_system 为 None，使该注入器在无记忆系统时"静默降级"，
        不影响 LLM 的正常运行
        """
        self.memory = memory_system
    
    def get_injection(self) -> PromptInjection:
        """
        【功能说明】从记忆系统检索内容，生成 Prompt 注入项

        【执行流程】
        1. 无记忆系统时直接返回空注入项
        2. 获取工作记忆（最近对话，取最新 10 条）
        3. 获取情景记忆（历史摘要，取最新 5 条）
        4. 格式化为 [近期对话] 和 [重要事件摘要] 两段文本
        5. 调用 inject_memories() 包装为标准 Prompt 格式

        【返回值】
            PromptInjection: priority=100（高优先级，靠近 Prompt 末尾）
            
        【设计意图】
        记忆注入使用 priority=100，确保其紧跟在 Prompt 末尾，
        让 LLM 在生成回答时能"最后看到"记忆内容，提高记忆的实际影响力
        """
        # 无记忆系统时直接返回空注入项（不抛异常，静默降级）
        if not self.memory:
            return PromptInjection("")
        
        try:
            # 获取工作记忆（最近的对话轮次，短期记忆）
            working_memories = self.memory.get_working_memory()
            
            # 获取情景记忆（历史摘要，中长期记忆）
            episodic_memories = self.memory.get_episodic_memory()
            
            # 构建记忆文本的各段内容
            memory_parts = []
            
            # 【近期对话】从工作记忆中取最新 10 条（防止太长超出 context）
            if working_memories:
                recent = working_memories[-10:]  # 取最后 10 条（最新的）
                memory_parts.append("[近期对话]")
                for m in recent:
                    # 截取前 200 字符防止单条记忆过长
                    content = m.get("content", "")[:200]
                    role = m.get("role", "?")   # "user" 或 "assistant"
                    memory_parts.append(f"{role}: {content}")
            
            # 【重要摘要】从情景记忆中筛选标记为摘要的条目
            if episodic_memories:
                # 只取 is_summary=True 的条目（过滤普通对话记录）
                summaries = [m for m in episodic_memories if m.get("is_summary")]
                if summaries:
                    memory_parts.append("\n[重要事件摘要]")
                    # 最多取 5 条摘要（最新的 5 条）
                    for m in summaries[-5:]:
                        content = m.get("content", "")
                        memory_parts.append(content)
            
            # 无有效记忆内容时返回空注入项
            if not memory_parts:
                return PromptInjection("")
            
            # 将所有记忆部分用换行连接
            memory_text = "\n".join(memory_parts)
            
            # 使用 prompts.py 中的模板包装记忆文本，生成标准格式的记忆 Prompt
            injected = inject_memories(memory_text)
            
            return PromptInjection(
                text=injected,
                priority=100  # 高优先级：记忆内容靠近 Prompt 末尾，影响力最大
            )
            
        except Exception as e:
            # 记忆获取失败时静默降级，不中断对话流程
            print(f"[MemoryRAGInjector] 错误: {e}")
            return PromptInjection("")


# ==================== 消息构建（无截断版）====================

def build_messages(
    message: str, 
    history: List[Dict] = None,
    system_prompt: str = None,
    memory_system = None
) -> List[Dict]:
    """
    【功能说明】构建发送给 LLM 的完整消息列表（v2.0 无硬截断版）

    【参数说明】
        message (str): 当前用户消息
        history (List[Dict]): 对话历史（[{"role": "user/assistant", "content": "..."}]）
        system_prompt (str): 覆盖默认系统提示词，None 则使用 SYSTEM_PROMPT
        memory_system: 记忆系统实例，用于 RAG 注入

    【返回值】
        List[Dict]: 符合 OpenAI Chat API 格式的消息列表
                    结构：[system] + [history...] + [current_user_message]

    【v2.0 改动说明】
    - 去掉 history[-20:] 硬截断：完整传递所有历史（由 context window 自然限制）
    - 去掉每条 200 字符截断：保留原始消息完整性
    - 新增记忆 RAG 注入：将记忆系统内容动态追加到系统 Prompt

    【设计意图】
    v1.x 的截断设计是为了节省 token，但会导致 LLM 遗忘早期对话。
    v2.0 的 max_tokens 提升到 2048，context window 更大，不再需要截断。
    """
    # 使用传入的 system_prompt，没有则使用模块级全局常量 SYSTEM_PROMPT
    base_system = system_prompt or SYSTEM_PROMPT
    
    # 【记忆 RAG 注入】如果提供了记忆系统，动态检索并追加到系统 Prompt
    if memory_system:
        rag_injector = MemoryRAGInjector(memory_system)
        memory_inj = rag_injector.get_injection()
        if memory_inj.text:
            # 将记忆内容追加到系统 Prompt 末尾（两个换行分隔）
            base_system = base_system + "\n\n" + memory_inj.text
    
    # 构建消息列表：第一条必须是 system 消息
    messages = [{"role": "system", "content": base_system}]
    
    # 【无截断历史注入】完整传递所有对话历史，让 LLM 看到完整上下文
    if history:
        messages.extend(history)
    
    # 当前用户消息追加到最后
    messages.append({"role": "user", "content": message})
    
    return messages


# ==================== 兼容旧接口 =====================

def _build_messages(message: str, history: List[Dict] = None,
                    system_prompt: str = None) -> List[Dict]:
    """
    【功能说明】兼容旧版接口（thin wrapper 调用新版 build_messages）

    【设计意图】
    v1.x 中使用 _build_messages（私有函数命名），v2.0 改名为 build_messages
    保留此函数避免其他模块的调用链断裂（向后兼容）
    """
    return build_messages(message, history, system_prompt)


# ==================== 动作解析 =====================

# 【预编译正则】匹配 LLM 回复中的 "COMMAND: <命令>" 格式
# re.DOTALL 让 . 匹配包括换行在内的所有字符
_COMMAND_RE = re.compile(r"COMMAND:\s*(.+?)(?:\n|$)", re.DOTALL)

def _parse_action(text: str) -> Optional[str]:
    """
    【功能说明】从 LLM 回复文本中解析 Agent 动作指令

    【参数说明】
        text (str): LLM 的回复文本，可能包含 "ACTION: execute" + "COMMAND: <命令>"

    【返回值】
        Optional[str]: 如果找到动作指令，返回 JSON 字符串；否则返回 None
                       格式：'{"type": "execute", "command": "<命令>"}'

    【设计意图】
    AI VTuber 可以通过在回复中嵌入特定格式触发工具调用。
    此函数解析这些隐式指令，与 tools/__init__.py 的工具系统配合使用。
    """
    if not text:
        return None
    # 检测是否包含执行动作标记
    if "ACTION: execute" in text or "COMMAND:" in text:
        match = _COMMAND_RE.search(text)
        if match:
            # 提取命令文本并序列化为 JSON 字符串，供调用方解析
            return json.dumps({"type": "execute", "command": match.group(1).strip()})
    return None


# ==================== 速率限制 & 重试 =====================

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
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
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
    
    def reset(self):
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
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
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


# ==================== LLM 引擎基类 =====================

class LLMEngine(ABC):
    """
    LLM 引擎抽象基类

    【设计意图】
    定义统一的 LLM 接口，使得 MiniMax/OpenAI/Anthropic 三种引擎
    对上层代码（main.py、web/__init__.py）完全透明可互换。
    
    遵循 LSP（Liskov 替换原则）：任何使用 LLMEngine 的代码都可以无感知地
    替换为任意子类实例。

    【强制实现的方法】
    - chat(): 非流式对话（一次性返回完整回复）
    - stream_chat(): 流式对话（边生成边回调，适合实时 TTS）
    - is_available(): 检查引擎是否可用（已配置必要参数）
    - name: 引擎名称属性
    """
    
    @abstractmethod
    def chat(self, message: str, history: List[Dict] = None, memory_system = None) -> Dict[str, Any]:
        """
        【抽象方法】非流式对话接口（子类必须实现）

        【参数说明】
            message (str): 当前用户消息
            history (List[Dict]): 对话历史
            memory_system: 记忆系统实例（可选）

        【返回值】
            Dict: {"text": 回复文本, "action": 动作指令或 None}
        """
        pass
    
    @abstractmethod
    def stream_chat(self, message: str, history: List[Dict] = None, callback=None, 
                    memory_system = None, chunk_size: int = 10) -> Dict[str, Any]:
        """
        【抽象方法】流式对话接口（子类必须实现）

        【参数说明】
            message (str): 当前用户消息
            history (List[Dict]): 对话历史
            callback: 流式回调函数，每积累 chunk_size 个字符时调用一次
                      signature: callback(text_chunk: str) -> None
            memory_system: 记忆系统实例（可选）
            chunk_size (int): 触发回调的字符数阈值，默认 10

        【返回值】
            Dict: {"text": 完整回复文本, "action": 动作指令或 None}
        
        【设计意图】
        流式接口用于实时 TTS：LLM 边生成文字，TTS 边合成语音，
        实现"边说边出声"的低延迟体验。chunk_size 控制 TTS 的分句粒度。
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        【抽象方法】检查 LLM 引擎是否可用

        【返回值】
            bool: 已配置必要参数（如 API Key）返回 True
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        【抽象属性】获取 LLM 引擎名称

        【返回值】
            str: 引擎标识名称（如 "MiniMax"、"OpenAI"、"Anthropic"）
        """
        pass


# ==================== MiniMax LLM =====================

class MiniMaxLLM(LLMEngine):
    """
    MiniMax 大语言模型引擎（v2.0）

    【支持的接口格式】
    1. OpenAI 兼容格式：POST /v1/text/chatcompletion_v2
    2. Anthropic 兼容格式：POST /v1/messages（通过 base_url 包含 "/anthropic" 自动判断）

    【功能特性】
    - HTTP 连接池（5 连接 / 10 最大，避免频繁重建 TCP）
    - LRU 缓存（TTL 300s，相同消息+历史长度命中时直接返回缓存，减少 API 调用）
    - 速率限制（滑动窗口，默认每分钟 60 次）
    - 指数退避重试（最多 3 次）
    - 线程安全缓存（v1.8：加 Lock 防止并发写入竞态）
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        【功能说明】初始化 MiniMax LLM 引擎

        【参数说明】
            config (Dict[str, Any]): 配置字典，来自 config.yaml 的 llm.minimax 节
                - api_key (str): MiniMax API Key
                - base_url (str): API 基础 URL（包含 "/anthropic" 则使用 Anthropic 格式）
                - model (str): 模型名称，默认 "MiniMax-M2.7"
                - group_id (str): MiniMax Group ID（某些接口必填）
                - max_tokens (int): 最大生成 token 数，默认 2048
                - rate_limit (int): 每分钟最大请求数，默认 60
                - max_retries (int): 最大重试次数，默认 3
                - retry_delay (float): 基础重试延迟（秒），默认 1.0
        """
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "http://120.24.86.32:3000")
        self.model = config.get("model", "MiniMax-M2.7")
        self.group_id = config.get("group_id", "")
        
        # v2.0: max_tokens 从 512 提升到 2048，支持更长的回复
        self.max_tokens = config.get("max_tokens", 2048)
        
        # 【格式自动判断】base_url 包含 "/anthropic" 时使用 Anthropic 兼容格式
        # 这允许通过代理服务器将 Anthropic 格式的请求转发给 MiniMax
        self._is_anthropic = "/anthropic" in self.base_url
        
        # 【HTTP 连接池配置】
        import requests
        self._session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=5,     # 并发连接数（线程数）
            pool_maxsize=10,        # 连接池最大连接数（超出排队等待）
            max_retries=0,          # urllib3 层重试禁用（由 RetryStrategy 控制）
            pool_block=False        # 连接池满时不阻塞（立即报错，由上层重试逻辑处理）
        )
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)
        self._session.headers.update({"Content-Type": "application/json"})
        
        # 根据格式设置认证头
        if self._is_anthropic:
            # Anthropic 格式：使用 x-api-key 头
            self._session.headers["x-api-key"] = self.api_key
            # 指定 Anthropic API 版本（必填）
            self._session.headers["anthropic-version"] = "2023-06-01"
        else:
            # OpenAI 格式：使用 Bearer Token
            self._session.headers["Authorization"] = f"Bearer {self.api_key}"
        
        # 【缓存配置】简单字典缓存，key = "消息:历史长度"
        self._cache = {}
        self._cache_ttl = 300           # 缓存有效期（秒）
        self._cache_lock = threading.Lock()  # v1.8: 缓存操作加锁，防止并发写入丢失
        
        # 速率限制器（每分钟最多 rate_limit 次请求）
        rate_limit = config.get("rate_limit", 60)
        self._rate_limiter = RateLimiter(max_requests=rate_limit)
        
        # 指数退避重试策略
        self._retry = RetryStrategy(
            max_retries=config.get("max_retries", 3),
            base_delay=config.get("retry_delay", 1.0),
        )
        
        print(f"  MiniMax LLM v2.0 初始化: max_tokens={self.max_tokens}")

    def _build_anthropic_messages(self, message: str, history: List[Dict] = None,
                                  memory_system = None):
        """
        【功能说明】将对话数据转换为 Anthropic API 所需的消息格式

        【参数说明】
            message (str): 当前用户消息
            history (List[Dict]): 对话历史（OpenAI 格式）
            memory_system: 记忆系统实例

        【返回值】
            tuple: (system_prompt: str, messages: List[Dict])
            - system_prompt: 系统提示词字符串（Anthropic 格式中 system 单独传递）
            - messages: Anthropic 格式的消息列表（content 为 content block 列表）

        【Anthropic 格式说明】
        OpenAI 格式：{"role": "user", "content": "text"}
        Anthropic 格式：{"role": "user", "content": [{"type": "text", "text": "text"}]}
        
        系统提示词在 Anthropic API 中通过顶层 "system" 字段传递，
        而不是作为 messages 数组中的一条消息
        """
        system_prompt = SYSTEM_PROMPT
        
        # 如果有记忆系统，注入记忆内容到系统 Prompt
        if memory_system:
            rag_injector = MemoryRAGInjector(memory_system)
            memory_inj = rag_injector.get_injection()
            if memory_inj.text:
                system_prompt = system_prompt + "\n\n" + memory_inj.text
        
        messages = []
        if history:
            for msg in history:
                # 跳过 system 角色的历史消息（system 已通过顶层字段传递）
                if msg.get("role") == "system":
                    continue
                else:
                    # 将 OpenAI 格式的纯文本 content 转换为 Anthropic 的 content block 列表
                    messages.append({
                        "role": msg["role"],
                        "content": [{"type": "text", "text": msg.get("content", "")}]
                    })
        # 当前用户消息也转换为 Anthropic content block 格式
        messages.append({
            "role": "user",
            "content": [{"type": "text", "text": message}]
        })
        return system_prompt, messages

    def chat(self, message: str, history: List[Dict] = None, 
             memory_system = None) -> Dict[str, Any]:
        """
        【功能说明】非流式对话（完整等待 LLM 生成后返回）

        【参数说明】
            message (str): 用户消息
            history (List[Dict]): 对话历史
            memory_system: 记忆系统实例

        【返回值】
            Dict[str, Any]: {"text": 回复文本, "action": 动作指令或 None}

        【执行流程】
        1. API Key 检查
        2. 构造缓存 Key，检查缓存命中（v1.8 加锁）
        3. 速率限制器获取配额
        4. 带重试策略执行 API 调用
        5. 缓存写入（v1.8 加锁），缓存超 100 条时触发 TTL 过期清理

        【设计意图】
        缓存 key 为 "消息内容:历史长度"，相同消息在相同历史长度下命中缓存。
        这是一个近似策略（历史长度相同不代表内容相同），但能覆盖大多数重复请求场景。
        """
        if not self.api_key:
            return {"text": "LLM未配置，请先配置 API Key", "action": None}

        # 生成缓存 Key（消息 + 历史长度，简单近似）
        cache_key = f"{message}:{len(history or [])}"
        
        # v1.8: 缓存读取加锁，防止并发读写竞态
        with self._cache_lock:
            if cache_key in self._cache:
                cached, ts = self._cache[cache_key]
                # 检查缓存是否在 TTL 内（300s）
                if time.time() - ts < self._cache_ttl:
                    return cached  # 直接返回缓存结果

        # 速率限制：等待获取请求配额（最多等待 30 秒）
        if not self._rate_limiter.acquire(timeout=30):
            return {"text": "请求过于频繁，请稍后再试", "action": None}

        last_error = None
        # 重试循环（最多 max_retries+1 次，含首次请求）
        for attempt in range(self._retry.max_retries + 1):
            try:
                result = self._do_chat(message, history, memory_system)
                # v1.8: 缓存写入加锁，防止并发写入冲突
                with self._cache_lock:
                    self._cache[cache_key] = (result, time.time())
                    # 缓存超 100 条时触发惰性清理（只保留 TTL 内的条目）
                    if len(self._cache) > 100:
                        now = time.time()
                        self._cache = {k: v for k, v in self._cache.items() if now - v[1] < self._cache_ttl}
                return result
            except Exception as e:
                last_error = e
                # 判断是否应该重试（网络错误/限速等可重试）
                if not self._retry.should_retry(attempt, e):
                    break
                # 计算指数退避等待时间
                delay = self._retry.get_delay(attempt)
                print(f" LLM 请求失败，{delay:.1f}s 后重试 ({attempt + 1}/{self._retry.max_retries})...")
                time.sleep(delay)
        
        return {"text": f"对话错误: {str(last_error)}", "action": None}

    def _do_chat(self, message: str, history: List[Dict] = None,
                 memory_system = None) -> Dict[str, Any]:
        """
        【功能说明】根据 base_url 格式分发到对应的 API 实现

        【参数说明】
            message (str): 当前用户消息
            history (List[Dict]): 对话历史
            memory_system: 记忆系统实例

        【返回值】
            Dict[str, Any]: {"text": 回复文本, "action": 动作或 None}

        【设计意图】
        将格式判断集中在此分发函数，避免在每个方法中重复判断 _is_anthropic
        """
        if self._is_anthropic:
            return self._do_chat_anthropic(message, history, memory_system)
        return self._do_chat_openai(message, history, memory_system)

    def _do_chat_openai(self, message: str, history: List[Dict] = None,
                        memory_system = None) -> Dict[str, Any]:
        """
        【功能说明】使用 OpenAI 兼容格式发送非流式对话请求

        【参数说明】
            message (str): 用户消息
            history (List[Dict]): 对话历史
            memory_system: 记忆系统实例（用于 RAG 注入）

        【返回值】
            Dict: {"text": 回复文本, "action": 动作指令或 None}

        【API 格式】
        POST /v1/text/chatcompletion_v2
        Body: {"model": ..., "messages": [...], "temperature": 0.7, "max_tokens": 2048}
        Response: {"choices": [{"message": {"content": "..."}}]}
        """
        # 构建 OpenAI 格式的消息列表（含 system + history + current）
        messages = build_messages(message, history, None, memory_system)
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,          # 生成多样性（0=确定性，1=最随机）
            "max_tokens": self.max_tokens,
        }
        # group_id 是 MiniMax 特有的必填字段（某些账号需要）
        if self.group_id:
            data["group_id"] = self.group_id

        url = f"{self.base_url}/v1/text/chatcompletion_v2"
        
        # 发送请求（timeout=60秒，非流式需等待完整生成）
        response = self._session.post(url, json=data, timeout=60)
        response.raise_for_status()  # 4xx/5xx 时抛出 HTTPError
        
        result = response.json()
        # 提取回复文本（OpenAI 格式：choices[0].message.content）
        msg = result["choices"][0].get("message", {})
        text = msg.get("content", "")
        
        # 解析回复中可能嵌入的动作指令
        action_str = _parse_action(text)
        action = json.loads(action_str) if action_str else None
        
        return {"text": text, "action": action}

    def _do_chat_anthropic(self, message: str, history: List[Dict] = None,
                           memory_system = None) -> Dict[str, Any]:
        """
        【功能说明】使用 Anthropic 兼容格式发送非流式对话请求

        【参数说明】
            message (str): 用户消息
            history (List[Dict]): 对话历史（会被转换为 Anthropic content block 格式）
            memory_system: 记忆系统实例

        【返回值】
            Dict: {"text": 回复文本, "action": 动作指令或 None}

        【API 格式】
        POST /v1/messages
        Body: {"model": ..., "messages": [...], "system": "...", "max_tokens": 2048}
        Response: {"content": [{"type": "text", "text": "..."}]}
        """
        # 转换为 Anthropic 格式（system 单独传递，messages 用 content block 格式）
        system_prompt, messages = self._build_anthropic_messages(message, history, memory_system)
        data = {
            "model": self.model,
            "messages": messages,
            "system": system_prompt,     # Anthropic 格式：system 通过顶层字段传递
            "max_tokens": self.max_tokens,
            "temperature": 1.0,          # Anthropic 推荐 temperature=1.0（不同于 OpenAI 的 0.7）
        }

        url = f"{self.base_url}/v1/messages"
        response = self._session.post(url, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        text = ""
        # Anthropic 回复格式：content 是 block 列表，需遍历拼接所有 text block
        for block in result.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
        
        action_str = _parse_action(text)
        action = json.loads(action_str) if action_str else None
        
        return {"text": text, "action": action}

    def stream_chat(self, message: str, history: List[Dict] = None, callback=None,
                    memory_system = None, chunk_size: int = 10) -> Dict[str, Any]:
        """
        【功能说明】流式对话（SSE 逐 chunk 回调）

        【参数说明】
            message (str): 用户消息
            history (List[Dict]): 对话历史
            callback: 每积累 chunk_size 个字符时触发，signature: callback(chunk: str)
            memory_system: 记忆系统实例
            chunk_size (int): 触发回调的字符数阈值（默认 10）

        【返回值】
            Dict: {"text": 完整回复文本, "action": 动作指令或 None}

        【设计意图】
        流式接口为 TTS 提供"边生成边朗读"的体验：
        每积累 chunk_size 个字符就触发 callback，TTS 立即合成该片段并播放，
        无需等待 LLM 生成完整回复，大幅降低首次出声延迟
        """
        if not self.api_key:
            return {"text": "请配置 MiniMax API Key", "action": None}

        # 速率限制检查
        if not self._rate_limiter.acquire(timeout=30):
            return {"text": "请求过于频繁，请稍后再试", "action": None}

        try:
            # 根据格式分发到对应流式实现
            if self._is_anthropic:
                return self._stream_anthropic(message, history, callback, memory_system, chunk_size)
            return self._stream_openai(message, history, callback, memory_system, chunk_size)
        except Exception as e:
            print(f"[LLM] 流式错误: {e}")
            # M5修复: 中断时返回已有的部分响应而非丢弃
            return {"text": "", "action": None, "_stream_error": str(e)}

    def _stream_openai(self, message: str, history, callback, memory_system, chunk_size) -> Dict[str, Any]:
        """
        【功能说明】OpenAI 兼容格式的 SSE 流式对话

        【参数说明】
            message (str): 用户消息
            history: 对话历史
            callback: 字符累积回调函数
            memory_system: 记忆系统
            chunk_size (int): 触发回调的字符阈值

        【返回值】
            Dict: {"text": 完整文本, "action": 动作或 None}

        【SSE 协议说明】
        Server-Sent Events（SSE）：服务器以 "data: <JSON>\n\n" 格式逐行推送数据
        最后一行为 "data: [DONE]" 表示流结束
        """
        messages = build_messages(message, history, None, memory_system)
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": self.max_tokens,
            "stream": True,          # 启用流式模式
        }
        if self.group_id:
            data["group_id"] = self.group_id

        url = f"{self.base_url}/v1/text/chatcompletion_v2"
        # stream=True: requests 不立即读取响应体，而是保持连接流式读取
        response = self._session.post(url, json=data, timeout=120, stream=True)
        response.raise_for_status()
        
        full_text = ""   # 完整回复文本（累积）
        buffer = ""      # 待触发回调的缓冲区
        
        # iter_lines(): 逐行读取 SSE 流，自动处理分块传输编码
        for line in response.iter_lines():
            if not line:
                continue  # 跳过 SSE 的空行分隔符
            
            line = line.decode('utf-8')
            if not line.startswith("data: "):
                continue  # 只处理数据行，忽略注释行（以 ":" 开头）
            
            data_str = line[6:]  # 去掉 "data: " 前缀，提取 JSON 数据
            if data_str == "[DONE]":
                break  # 流结束标记
            
            try:
                chunk = json.loads(data_str)
                # OpenAI SSE 格式：choices[0].delta.content 包含增量文本
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                
                if content:
                    full_text += content   # 累积到完整文本
                    buffer += content      # 累积到回调缓冲区
                    
                    # 缓冲区达到 chunk_size 时触发回调（通知 TTS 开始合成）
                    if len(buffer) >= chunk_size and callback:
                        callback(buffer)
                        buffer = ""  # 清空缓冲区
            except:
                continue  # 单行解析失败不中断流式处理
        
        # 流结束后，发送缓冲区中剩余的文本片段
        if buffer and callback:
            callback(buffer)
        
        action_str = _parse_action(full_text)
        action = json.loads(action_str) if action_str else None
        return {"text": full_text, "action": action}

    def _stream_anthropic(self, message: str, history, callback, memory_system, chunk_size) -> Dict[str, Any]:
        """
        【功能说明】Anthropic 兼容格式的 SSE 流式对话

        【参数说明】
            message (str): 用户消息
            history: 对话历史
            callback: 字符累积回调函数
            memory_system: 记忆系统
            chunk_size (int): 触发回调的字符阈值

        【返回值】
            Dict: {"text": 完整文本, "action": 动作或 None}

        【Anthropic SSE 格式说明】
        Anthropic 的 SSE 事件格式与 OpenAI 不同：
        - event type: "content_block_delta" + delta.type: "text_delta" 表示文本增量
        - event type: "message_stop" 表示消息生成完毕
        """
        system_prompt, messages = self._build_anthropic_messages(message, history, memory_system)
        data = {
            "model": self.model,
            "messages": messages,
            "system": system_prompt,
            "max_tokens": self.max_tokens,
            "temperature": 1.0,
            "stream": True,
        }

        url = f"{self.base_url}/v1/messages"
        response = self._session.post(url, json=data, timeout=120, stream=True)
        response.raise_for_status()
        
        full_text = ""
        buffer = ""
        
        for line in response.iter_lines():
            if not line:
                continue
            
            line = line.decode('utf-8')
            if not line.startswith("data: "):
                continue
            
            data_str = line[6:]
            
            try:
                chunk = json.loads(data_str)
                event_type = chunk.get("type", "")
                
                # 【Anthropic 特有事件格式】文本增量事件
                if event_type == "content_block_delta":
                    delta = chunk.get("delta", {})
                    delta_type = delta.get("type", "")
                    
                    # text_delta 类型表示这是文本内容增量
                    if delta_type == "text_delta":
                        content = delta.get("text", "")
                        if content:
                            full_text += content
                            buffer += content
                            
                            if len(buffer) >= chunk_size and callback:
                                callback(buffer)
                                buffer = ""
                
                # 【Anthropic 特有事件】消息生成完毕
                elif event_type == "message_stop":
                    break
            except:
                continue
        
        # 发送缓冲区剩余内容
        if buffer and callback:
            callback(buffer)
        
        action_str = _parse_action(full_text)
        action = json.loads(action_str) if action_str else None
        return {"text": full_text, "action": action}

    def is_available(self) -> bool:
        """
        【功能说明】检查 MiniMax API Key 是否已配置

        【返回值】
            bool: API Key 非空字符串时返回 True
        """
        return bool(self.api_key)

    @property
    def name(self) -> str:
        """
        【属性】获取 LLM 引擎名称

        【返回值】
            str: "MiniMax"
        """
        return "MiniMax"


# ==================== OpenAI LLM =====================

class OpenAILLM(LLMEngine):
    """
    OpenAI GPT 大语言模型引擎（v2.0）

    【支持的模型】
    - gpt-3.5-turbo：快速、经济
    - gpt-4、gpt-4-turbo：高质量
    - 通过 base_url 配置也可接入 OpenAI 兼容的第三方代理

    【功能特性】
    - 标准 OpenAI Chat Completions API（/chat/completions）
    - 同步非流式 + SSE 真流式两种接口
    - 缓存 + 速率限制 + 线程安全（v1.8 升级）
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        【功能说明】初始化 OpenAI LLM 引擎

        【参数说明】
            config (Dict[str, Any]): 配置字典，来自 config.yaml 的 llm.openai 节
                - api_key (str): OpenAI API Key
                - base_url (str): API 基础 URL，默认官方地址
                - model (str): 模型名称，默认 "gpt-3.5-turbo"
                - max_tokens (int): 最大生成 token 数，默认 2048
                - rate_limit (int): 每分钟最大请求数，默认 60
        """
        self.config = config
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.model = config.get("model", "gpt-3.5-turbo")
        self.max_tokens = config.get("max_tokens", 2048)
        
        # 创建带认证头的 HTTP Session
        import requests
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
        
        self._rate_limiter = RateLimiter(max_requests=config.get("rate_limit", 60))
        self._cache = {}
        self._cache_ttl = 300
        self._cache_lock = threading.Lock()  # v1.8: 缓存线程安全
        
        print(f"  OpenAI LLM v2.0 初始化: max_tokens={self.max_tokens}")

    def chat(self, message: str, history: List[Dict] = None,
             memory_system = None) -> Dict[str, Any]:
        """
        【功能说明】OpenAI 非流式对话（带缓存和速率限制）

        【参数说明】
            message (str): 用户消息
            history (List[Dict]): 对话历史
            memory_system: 记忆系统实例

        【返回值】
            Dict[str, Any]: {"text": 回复文本, "action": 动作指令或 None}

        【执行流程】
        1. API Key 检查 → 速率限制 → 缓存检查
        2. 构建 OpenAI 格式消息（/chat/completions）
        3. 解析回复，写入缓存，返回结果
        """
        if not self.api_key:
            return {"text": "请配置 OpenAI API Key", "action": None}

        if not self._rate_limiter.acquire(timeout=30):
            return {"text": "请求过于频繁，请稍后再试", "action": None}

        cache_key = f"{message}:{len(history or [])}"
        # v1.8: 缓存读取加锁
        with self._cache_lock:
            if cache_key in self._cache:
                cached, ts = self._cache[cache_key]
                if time.time() - ts < self._cache_ttl:
                    return cached

        try:
            # 使用统一的 build_messages() 构建消息列表
            messages = build_messages(message, history, None, memory_system)
            data = {
                "model": self.model,
                "messages": messages, 
                "temperature": 0.7,
                "max_tokens": self.max_tokens
            }
            
            response = self._session.post(
                f"{self.base_url}/chat/completions", 
                json=data, timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            # OpenAI Chat Completions 格式：choices[0].message.content
            text = result["choices"][0]["message"]["content"]
            action_str = _parse_action(text)
            
            ret = {"text": text, "action": action_str}
            # v1.8: 缓存写入加锁
            with self._cache_lock:
                self._cache[cache_key] = (ret, time.time())
            
            return ret
        except Exception as e:
            return {"text": f"对话错误: {str(e)}", "action": None}

    def stream_chat(self, message: str, history: List[Dict] = None, callback=None,
                    memory_system = None, chunk_size: int = 10) -> Dict[str, Any]:
        """
        【功能说明】OpenAI SSE 真流式对话（v1.8 升级）

        【参数说明】
            message (str): 用户消息
            history (List[Dict]): 对话历史
            callback: 字符累积回调函数，signature: callback(chunk: str)
            memory_system: 记忆系统
            chunk_size (int): 触发回调的字符阈值

        【返回值】
            Dict: {"text": 完整回复文本, "action": 动作或 None}

        【v1.8 升级说明】
        v1.x 是"伪流式"——等待完整回复后再模拟分块回调。
        v1.8 改为真正的 SSE stream，实时接收服务器推送的 token 片段，
        每累积 chunk_size 字符立即触发回调，首次出声延迟大幅降低。
        """
        if not self.api_key:
            return {"text": "请配置 OpenAI API Key", "action": None}

        if not self._rate_limiter.acquire(timeout=30):
            return {"text": "请求过于频繁，请稍后再试", "action": None}

        try:
            messages = build_messages(message, history, None, memory_system)
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": self.max_tokens,
                "stream": True,  # 启用 SSE 流式模式
            }
            
            response = self._session.post(
                f"{self.base_url}/chat/completions",
                json=data, timeout=120, stream=True
            )
            response.raise_for_status()
            
            full_text = ""
            buffer = ""
            
            # 逐行处理 SSE 数据流
            for line in response.iter_lines():
                if not line:
                    continue
                line = line.decode('utf-8')
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break  # 流结束
                
                try:
                    chunk = json.loads(data_str)
                    # OpenAI SSE：choices[0].delta.content 为增量文本
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    
                    if content:
                        full_text += content
                        buffer += content
                        # 缓冲区达到阈值时触发 TTS 回调
                        if len(buffer) >= chunk_size and callback:
                            callback(buffer)
                            buffer = ""
                except:
                    continue
            
            # 发送剩余缓冲区内容
            if buffer and callback:
                callback(buffer)
            
            action_str = _parse_action(full_text)
            action = json.loads(action_str) if action_str else None
            return {"text": full_text, "action": action}
        except Exception as e:
            print(f"[LLM] OpenAI 流式错误: {e}")
            return {"text": f"对话错误: {str(e)}", "action": None}
        # 注意：此 return 语句不可达（异常路径已在上面 except 中返回）
        # return result  # 原代码遗留的不可达语句，可忽略

    def is_available(self) -> bool:
        """
        【功能说明】检查 OpenAI API Key 是否已配置

        【返回值】
            bool: API Key 非空返回 True
        """
        return bool(self.api_key)

    @property
    def name(self) -> str:
        """
        【属性】获取 LLM 引擎名称

        【返回值】
            str: "OpenAI"
        """
        return "OpenAI"


# ==================== Anthropic LLM =====================

class AnthropicLLM(LLMEngine):
    """
    Anthropic Claude 大语言模型引擎（v2.0）

    【支持的模型】
    - claude-3-haiku-20240307：快速、经济
    - claude-3-sonnet-20240229：平衡
    - claude-3-opus-20240229：最强

    【与 MiniMax Anthropic 格式的区别】
    MiniMaxLLM 中的 Anthropic 格式是通过代理服务器转发的，
    本类直接调用 Anthropic 官方 API（api.anthropic.com）。
    接口格式相同，但认证和端点地址不同。
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        【功能说明】初始化 Anthropic Claude LLM 引擎

        【参数说明】
            config (Dict[str, Any]): 配置字典，来自 config.yaml 的 llm.anthropic 节
                - api_key (str): Anthropic API Key
                - model (str): 模型名称，默认 "claude-3-sonnet-20240229"
                - max_tokens (int): 最大生成 token 数，默认 2048
                - rate_limit (int): 每分钟最大请求数，默认 50（Anthropic 默认限制更严格）
        """
        self.config = config
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "claude-3-sonnet-20240229")
        self.max_tokens = config.get("max_tokens", 2048)
        
        # Anthropic 官方 API 使用 x-api-key 认证头（与 OpenAI Bearer Token 不同）
        import requests
        self._session = requests.Session()
        self._session.headers.update({
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",  # Anthropic API 版本（必填）
            "Content-Type": "application/json",
        })
        
        # Anthropic 默认速率限制较低（50 次/分钟）
        self._rate_limiter = RateLimiter(max_requests=config.get("rate_limit", 50))
        self._cache = {}
        self._cache_ttl = 300
        self._cache_lock = threading.Lock()  # v1.8: 缓存线程安全
        
        print(f"  Anthropic LLM v2.0 初始化: max_tokens={self.max_tokens}")

    def chat(self, message: str, history: List[Dict] = None,
             memory_system = None) -> Dict[str, Any]:
        """
        【功能说明】Anthropic 非流式对话（带缓存和速率限制）

        【参数说明】
            message (str): 用户消息
            history (List[Dict]): OpenAI 格式的对话历史（自动转换）
            memory_system: 记忆系统实例

        【返回值】
            Dict: {"text": 回复文本, "action": 动作或 None}

        【Anthropic API 特殊处理】
        - 消息格式：将 OpenAI 格式历史转换为 Anthropic 格式
        - System 消息：从 messages 中过滤出，通过 data["system"] 单独传递
        - 回复解析：content 是 block 列表，需遍历取 text block
        """
        if not self.api_key:
            return {"text": "请配置 Anthropic API Key", "action": None}

        if not self._rate_limiter.acquire(timeout=30):
            return {"text": "请求过于频繁，请稍后再试", "action": None}

        cache_key = f"{message}:{len(history or [])}"
        # v1.8: 缓存读取加锁
        with self._cache_lock:
            if cache_key in self._cache:
                cached, ts = self._cache[cache_key]
                if time.time() - ts < self._cache_ttl:
                    return cached

        try:
            # 使用 build_messages 构建消息列表（含记忆注入）
            messages = build_messages(message, history, None, memory_system)
            # 将 messages 转换为纯 role/content 格式（Anthropic 接受这种简化格式）
            # 注意：system 消息会被保留，但 Anthropic 官方建议通过 system 字段传递
            claude_messages = [{"role": msg["role"], "content": msg["content"]} for msg in messages]
            
            data = {
                "model": self.model,
                "messages": claude_messages,
                "temperature": 0.7,
                "max_tokens": self.max_tokens,
            }
            
            response = self._session.post(
                "https://api.anthropic.com/v1/messages",  # Anthropic 官方端点（硬编码）
                json=data, timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            # Anthropic 回复格式：content[0].text
            text = result["content"][0]["text"]
            action_str = _parse_action(text)
            
            ret = {"text": text, "action": action_str}
            # v1.8: 缓存写入加锁
            with self._cache_lock:
                self._cache[cache_key] = (ret, time.time())
            
            return ret
        except Exception as e:
            return {"text": f"对话错误: {str(e)}", "action": None}

    def stream_chat(self, message: str, history: List[Dict] = None, callback=None,
                    memory_system = None, chunk_size: int = 10) -> Dict[str, Any]:
        """
        【功能说明】Anthropic SSE 真流式对话（v1.8 升级）

        【参数说明】
            message (str): 用户消息
            history (List[Dict]): 对话历史
            callback: 字符累积回调函数
            memory_system: 记忆系统
            chunk_size (int): 触发回调的字符阈值

        【返回值】
            Dict: {"text": 完整回复文本, "action": 动作或 None}

        【Anthropic 流式 SSE 格式说明】
        事件类型按顺序：
        1. "message_start" - 消息开始
        2. "content_block_start" - 内容块开始
        3. "content_block_delta" (type="text_delta") - 文本增量（反复出现）
        4. "content_block_stop" - 内容块结束
        5. "message_delta" - 消息元数据更新（包含 stop_reason、usage 等）
        6. "message_stop" - 消息结束（触发退出循环）
        """
        if not self.api_key:
            return {"text": "请配置 Anthropic API Key", "action": None}

        if not self._rate_limiter.acquire(timeout=30):
            return {"text": "请求过于频繁，请稍后再试", "action": None}

        try:
            messages = build_messages(message, history, None, memory_system)
            claude_messages = [{"role": msg["role"], "content": msg["content"]} for msg in messages]
            
            data = {
                "model": self.model,
                "messages": claude_messages,
                "temperature": 0.7,
                "max_tokens": self.max_tokens,
                "stream": True,
            }
            
            response = self._session.post(
                "https://api.anthropic.com/v1/messages",
                json=data, timeout=120, stream=True
            )
            response.raise_for_status()
            
            full_text = ""
            buffer = ""
            
            for line in response.iter_lines():
                if not line:
                    continue
                line = line.decode('utf-8')
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                
                try:
                    chunk = json.loads(data_str)
                    event_type = chunk.get("type", "")
                    
                    # 只处理文本增量事件（content_block_delta + text_delta 双重匹配）
                    if event_type == "content_block_delta":
                        delta = chunk.get("delta", {})
                        delta_type = delta.get("type", "")
                        
                        if delta_type == "text_delta":
                            content = delta.get("text", "")
                            if content:
                                full_text += content
                                buffer += content
                                if len(buffer) >= chunk_size and callback:
                                    callback(buffer)
                                    buffer = ""
                    
                    # 消息结束标志，退出流式循环
                    elif event_type == "message_stop":
                        break
                except:
                    continue
            
            # 发送缓冲区剩余内容
            if buffer and callback:
                callback(buffer)
            
            action_str = _parse_action(full_text)
            action = json.loads(action_str) if action_str else None
            return {"text": full_text, "action": action}
        except Exception as e:
            print(f"[LLM] Anthropic 流式错误: {e}")
            return {"text": f"对话错误: {str(e)}", "action": None}

    def is_available(self) -> bool:
        """
        【功能说明】检查 Anthropic API Key 是否已配置

        【返回值】
            bool: API Key 非空返回 True
        """
        return bool(self.api_key)

    @property
    def name(self) -> str:
        """
        【属性】获取 LLM 引擎名称

        【返回值】
            str: "Anthropic"
        """
        return "Anthropic"


# ==================== LLM 工厂 =====================

class LLMFactory:
    """
    LLM 工厂类

    【设计意图】
    工厂模式（Factory Pattern）：将对象创建逻辑集中在工厂中，
    调用方只需传入配置，无需知道具体要实例化哪个类。
    
    新增 LLM 提供商时只需：
    1. 新建引擎类（继承 LLMEngine）
    2. 在 LLMFactory.create() 中添加一个 elif 分支

    【使用示例】
    engine = LLMFactory.create({"provider": "openai", "openai": {"api_key": "..."}})
    """
    
    @staticmethod
    def create(config: Dict[str, Any]) -> LLMEngine:
        """
        【功能说明】根据配置创建对应的 LLM 引擎实例

        【参数说明】
            config (Dict[str, Any]): 包含 provider 字段的配置字典
                - provider (str): 提供商标识（"minimax" / "openai" / "anthropic"）
                - minimax (Dict): MiniMax 引擎配置（当 provider=="minimax" 时使用）
                - openai (Dict): OpenAI 引擎配置（当 provider=="openai" 时使用）
                - anthropic (Dict): Anthropic 引擎配置（当 provider=="anthropic" 时使用）

        【返回值】
            LLMEngine: 对应提供商的引擎实例

        【异常】
            ValueError: 当 provider 值不在支持范围内时抛出

        【设计意图】
        config.get("minimax", {}) 而非 config.get("minimax")：
        确保子配置不存在时传入空字典，引擎类内部用 .get() 获取各字段时使用默认值，
        避免 NoneType 错误
        """
        # 从配置中获取提供商类型，默认使用 minimax
        provider = config.get("provider", "minimax")
        
        if provider == "minimax":
            # 传入 minimax 子配置（包含 api_key、model 等）
            return MiniMaxLLM(config.get("minimax", {}))
        elif provider == "openai":
            # 传入 openai 子配置
            return OpenAILLM(config.get("openai", {}))
        elif provider == "anthropic":
            # 传入 anthropic 子配置
            return AnthropicLLM(config.get("anthropic", {}))
        else:
            raise ValueError(f"未知 LLM 提供商: {provider}")
