"""
LLM 引擎模块

包含 LLMEngine（抽象基类）和三种引擎实现：MiniMaxLLM、OpenAILLM、AnthropicLLM。
"""

import json
import time
import logging
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, List

from llm.infrastructure import RateLimiter, RetryStrategy, StreamAccumulator

logger = logging.getLogger(__name__)

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
                    memory_system = None, chunk_size: int = 10,
                    on_tool_call=None) -> Dict[str, Any]:
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

    def _init_common(self, config: dict, default_rate_limit: int = 60) -> None:
        """
        【功能说明】公共初始化：HTTP 连接池 + 缓存 + 速率限制器

        【参数说明】
            config (dict): 引擎配置字典
            default_rate_limit (int): 默认速率限制（每分钟请求数），子类可覆盖

        【设计意图】
        三个引擎（MiniMax/OpenAI/Anthropic）的 __init__ 中都有相同逻辑：
        创建 requests.Session、配置连接池、初始化缓存和速率限制器。
        提取到基类消除 3 处重复代码。子类调用 _init_common() 后只需设置认证头。
        """
        import requests
        self._session = requests.Session()
        # 连接池优化 — 增加连接池大小，启用 keep-alive
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,    # 并发连接数（线程数）
            pool_maxsize=20,       # 连接池最大连接数
            max_retries=0,         # urllib3 层重试禁用（由 RetryStrategy 控制）
            pool_block=False       # 连接池满时不阻塞（立即报错，由上层重试逻辑处理）
        )
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)
        # 启用 keep-alive — 复用 TCP 连接，减少握手开销
        self._session.headers.update({
            "Connection": "keep-alive",
            "Content-Type": "application/json",
        })

        # 缓存配置（线程安全）
        self._cache = {}
        self._cache_ttl = 300               # 缓存有效期（秒）
        self._cache_lock = threading.Lock() # 缓存操作加锁，防止并发写入丢失

        # 速率限制器（每分钟最多 rate_limit 次请求）
        self._rate_limiter = RateLimiter(max_requests=config.get("rate_limit", default_rate_limit))

    def cleanup(self) -> None:
        """释放 HTTP 连接池资源"""
        if hasattr(self, '_session') and self._session:
            try:
                self._session.close()
            except Exception as e:
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
    
    def __init__(self, config: Dict[str, Any]) -> None:
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
        raw_base_url = config.get("base_url", "https://api.minimaxi.com")
        self.model = config.get("model", "MiniMax-M2.7")
        self.group_id = config.get("group_id", "")

        # 【格式自动判断】base_url 包含 "/anthropic" 时使用 Anthropic 兼容格式
        self._is_anthropic = "/anthropic" in raw_base_url

        # 【base_url 标准化】防止路径重复拼接
        # Anthropic 格式: base_url = https://api.minimaxi.com/anthropic
        # OpenAI 格式:    base_url = https://api.minimaxi.com/v1
        if self._is_anthropic:
            # 确保 base_url 以 /anthropic 结尾（不含多余的 /v1）
            self.base_url = raw_base_url.replace("/v1", "").rstrip("/")
            if not self.base_url.endswith("/anthropic"):
                self.base_url = self.base_url.rstrip("/") + "/anthropic"
        else:
            # OpenAI 格式：确保 base_url 以 /v1 结尾
            self.base_url = raw_base_url.replace("/anthropic", "").rstrip("/")
            if not self.base_url.endswith("/v1"):
                self.base_url = self.base_url.rstrip("/") + "/v1"

        # v2.0: max_tokens 从 512 提升到 2048，支持更长的回复
        self.max_tokens = config.get("max_tokens", 2048)

        # 【公共初始化】HTTP 连接池 + 缓存 + 速率限制器
        self._init_common(config, default_rate_limit=60)
        
        # 根据格式设置认证头
        if self._is_anthropic:
            # Anthropic 格式：使用 x-api-key 头
            self._session.headers["x-api-key"] = self.api_key
            # 指定 Anthropic API 版本（必填）
            self._session.headers["anthropic-version"] = "2023-06-01"
        else:
            # OpenAI 格式：使用 Bearer Token
            self._session.headers["Authorization"] = f"Bearer {self.api_key}"
        
        # 指数退避重试策略
        self._retry = RetryStrategy(
            max_retries=config.get("max_retries", 3),
            base_delay=config.get("retry_delay", 1.0),
        )
        
        logger.info(f"  MiniMax LLM v2.0 初始化: max_tokens={self.max_tokens}")

    def _build_anthropic_messages(self, message: str, history: List[Dict] = None,
                                  memory_system = None) -> None:
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
                logger.info(f" LLM 请求失败，{delay:.1f}s 后重试 ({attempt + 1}/{self._retry.max_retries})...")
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
        POST /chat/completions（base_url 已含 /v1）
        Body: {"model": ..., "messages": [...], "temperature": 0.7, "max_completion_tokens": 2048}
        Response: {"choices": [{"message": {"content": "..."}}]}
        """
        # 构建 OpenAI 格式的消息列表（含 system + history + current）
        messages = build_messages(message, history, None, memory_system)
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,          # 生成多样性（0=确定性，1=最随机）
            "max_completion_tokens": self.max_tokens,  # MiniMax OpenAI 兼容格式使用 max_completion_tokens
        }
        # group_id 是 MiniMax 特有的必填字段（某些账号需要）
        if self.group_id:
            data["group_id"] = self.group_id

        # base_url 已含 /v1，直接拼接 /chat/completions
        url = f"{self.base_url}/chat/completions"
        
        # 发送请求（timeout=60秒，非流式需等待完整生成）
        response = self._session.post(url, json=data, timeout=60)
        response.raise_for_status()  # 4xx/5xx 时抛出 HTTPError
        
        result = response.json()
        # v1.9.99 修复: choices 可能为空列表，保护性处理
        choices = result.get("choices", [])
        if not choices:
            return {"text": "(LLM 返回空回复)", "action": None}
        msg = choices[0].get("message", {})
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
            "max_tokens": self.max_tokens,
            "temperature": 1.0,          # Anthropic 推荐 temperature=1.0（不同于 OpenAI 的 0.7）
        }
        if system_prompt:                 # 仅当 system_prompt 非空时传递，避免 API 拒绝空字符串
            data["system"] = system_prompt

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
                    memory_system = None, chunk_size: int = 10,
                    on_tool_call=None) -> Dict[str, Any]:
        """
        【功能说明】流式对话（SSE 逐 chunk 回调）

        【参数说明】
            message (str): 用户消息
            history (List[Dict]): 对话历史
            callback: 每积累 chunk_size 个字符时触发，signature: callback(chunk: str)
            memory_system: 记忆系统实例
            chunk_size (int): 触发回调的字符数阈值（默认 10）
            on_tool_call: FC 工具调用状态回调，signature: fn(tool_name, display_text, args)

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

        # v1.9.72: 流式请求也增加重试（500 服务端临时故障）
        max_retries = 2
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                # 根据格式分发到对应流式实现
                if self._is_anthropic:
                    return self._stream_anthropic(message, history, callback, memory_system, chunk_size)
                return self._stream_openai(message, history, callback, memory_system, chunk_size, on_tool_call)
            except Exception as e:
                last_error = e
                error_str = str(e)
                # 只有 5xx 服务端错误才重试
                is_server_error = any(code in error_str for code in ["500", "502", "503", "504"])
                if is_server_error and attempt < max_retries:
                    import time
                    wait = 2 ** attempt  # 指数退避: 1s, 2s
                    logger.info(f"[LLM] 流式请求 {attempt+1}/{max_retries+1} 失败({error_str})，{wait}s后重试...")
                    time.sleep(wait)
                    continue
                break

        logger.info(f"[LLM] 流式错误: {last_error}")
        # v1.9.99: 流式错误时返回错误信息而非空字符串，让调用方能感知到失败
        return {"text": f"对话错误: {str(last_error)}", "action": None, "_stream_error": str(last_error)}

    def _stream_openai(self, message: str, history, callback, memory_system, chunk_size, on_tool_call=None) -> Dict[str, Any]:
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
            "max_completion_tokens": self.max_tokens,  # MiniMax OpenAI 兼容格式
            "stream": True,          # 启用流式模式
        }
        if self.group_id:
            data["group_id"] = self.group_id

        # v2.0: Function Calling — 添加工具定义
        try:
            from app.tools.fc_executor import get_tool_schemas
            tool_schemas = get_tool_schemas()
            if tool_schemas:
                data["tools"] = tool_schemas
                data["tool_choice"] = "auto"
        except Exception as e:
            logger.info(f"[LLM] FC 工具 schema 加载失败(不影响对话): {e}")

        # base_url 已含 /v1，直接拼接 /chat/completions
        url = f"{self.base_url}/chat/completions"
        # stream=True: requests 不立即读取响应体，而是保持连接流式读取
        response = self._session.post(url, json=data, timeout=120, stream=True)
        response.raise_for_status()

        acc = StreamAccumulator(chunk_size=chunk_size, callback=callback, on_tool_call=on_tool_call)
        choice = None  # KI-010 FIX: 默认初始化，防止流无有效行时 NameError
        chunk = None

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
                choices = chunk.get("choices", [])
                # v1.9.99 修复: choices 可能为空（流结束信号有时不含 choices）
                if not choices:
                    continue
                choice = choices[0]
                # OpenAI SSE 格式：choices[0].delta.content 包含增量文本
                delta = choice.get("delta", {})
                content = delta.get("content") or ""

                # v2.0: FC — 累积 tool_calls delta
                delta_tool_calls = delta.get("tool_calls")
                if delta_tool_calls:
                    for tc_delta in delta_tool_calls:
                        acc.accumulate_tool_call(tc_delta)

                if content:
                    acc.process_content(content)
            except Exception as e:
                continue  # 单行解析失败不中断流式处理

        # v2.0: FC — 检查 tool_calls + 流结束处理（委托 StreamAccumulator）
        # KI-010 FIX: 使用更安全的 None 检查代替 dir() 检查
        acc.finish_reason = choice.get("finish_reason", "") if choice else ""
        return acc.finish_with_fc(
            messages=messages, session=self._session, base_url=self.base_url,
            model=self.model, api_key=self.api_key, max_tokens=self.max_tokens,
            on_chunk=callback, response=response,
        )

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
            "max_tokens": self.max_tokens,
            "temperature": 1.0,
            "stream": True,
        }
        if system_prompt:                 # 仅当 system_prompt 非空时传递
            data["system"] = system_prompt

        url = f"{self.base_url}/v1/messages"
        response = self._session.post(url, json=data, timeout=120, stream=True)
        response.raise_for_status()
        
        acc = StreamAccumulator(chunk_size=chunk_size, callback=callback)
        
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
                        content = delta.get("text") or ""
                        if content:
                            acc.process_content(content)
                
                # 【Anthropic 特有事件】消息生成完毕
                elif event_type == "message_stop":
                    break
            except Exception as e:
                continue
        
        return acc.finish(response)

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
    
    def __init__(self, config: Dict[str, Any]) -> None:
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
        # v1.9.38: 去掉 base_url 尾部斜杠，避免双斜杠
        self.base_url = self.base_url.rstrip("/")
        self.model = config.get("model", "gpt-3.5-turbo")
        self.max_tokens = config.get("max_tokens", 2048)
        # v1.9.38: 检测是否为 Ollama 端点
        self._is_ollama = "localhost:11434" in self.base_url or "127.0.0.1:11434" in self.base_url
        
        # 【公共初始化】HTTP 连接池 + 缓存 + 速率限制器
        self._init_common(config, default_rate_limit=60)
        # MiMo 使用 api-key 头，其他 OpenAI 兼容提供商使用 Authorization: Bearer
        if "xiaomimimo.com" in self.base_url:
            self._session.headers["api-key"] = self.api_key
        else:
            self._session.headers["Authorization"] = f"Bearer {self.api_key}"
        
        logger.info(f"  OpenAI LLM v2.0 初始化: base_url={self.base_url}, max_tokens={self.max_tokens}, ollama={self._is_ollama}")

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
        # v1.9.38: Ollama 端点走原生 API（支持 think:false 关闭 Qwen3 思考模式）
        if self._is_ollama:
            return self._ollama_chat(message, history, memory_system)

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
            # v1.9.99 修复: choices 可能为空列表，保护性处理
            choices = result.get("choices", [])
            if not choices:
                return {"text": "(LLM 返回空回复)", "action": None}
            msg = choices[0].get("message", {})
            raw_content = msg.get("content") or ""  # Qwen3 thinking 模式下 content 可能为 None
            # v1.9.95 修复：content 可能是 list（多模态/vision 模型）或 dict，需提取文本
            if isinstance(raw_content, list):
                # OpenAI 多模态格式：[{"type": "text", "text": "..."}, ...]
                text = ""
                for item in raw_content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text += item.get("text", "")
                    elif isinstance(item, str):
                        text += item
                if not text:
                    text = str(raw_content)  # 兜底
            elif isinstance(raw_content, dict):
                text = raw_content.get("text", str(raw_content))
            else:
                text = str(raw_content)
            # 兜底清理：<think >...</think > 标签（部分 Qwen3 版本会输出到 content 中）
            text, action = _clean_response(text)
            # 统一返回格式：action 始终为解析后的 dict 或 None（与 MiniMax 等一致）
            if isinstance(action, str):
                try:
                    import json as _json
                    action = _json.loads(action)
                except (ValueError, TypeError):
                    action = None

            ret = {"text": text, "action": action}
            # v1.8: 缓存写入加锁
            with self._cache_lock:
                self._cache[cache_key] = (ret, time.time())
            
            return ret
        except Exception as e:
            logger.info(f"[LLM] 对话异常: {type(e).__name__}: {e}")
            return {"text": "对话出错了，请稍后重试", "action": None}

    def _ollama_chat(self, message: str, history: List[Dict] = None,
                     memory_system = None) -> Dict[str, Any]:
        """v1.9.38: Ollama 原生 API 对话（支持 think:false 关闭思考模式）"""
        if not self._rate_limiter.acquire(timeout=30):
            return {"text": "请求过于频繁，请稍后再试", "action": None}

        cache_key = f"ollama:{message}:{len(history or [])}"
        with self._cache_lock:
            if cache_key in self._cache:
                cached, ts = self._cache[cache_key]
                if time.time() - ts < self._cache_ttl:
                    return cached

        try:
            messages = build_messages(message, history, None, memory_system)
            # Ollama 原生 API 端点: /api/chat
            data = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "think": False,  # 关闭 Qwen3 思考模式
                "options": {
                    "num_predict": self.max_tokens,
                    "temperature": 0.7,
                }
            }
            # Ollama 原生端点是 /api/chat，去掉 base_url 中的 /v1 后缀避免 /v1/api/chat 404
            ollama_base = self.base_url.replace("/v1", "").rstrip("/")
            response = self._session.post(
                f"{ollama_base}/api/chat",
                json=data, timeout=120
            )
            response.raise_for_status()
            result = response.json()
            msg = result.get("message", {})
            raw_content = msg.get("content") or ""
            # v1.9.95 修复：content 可能是 list/dict 而非 string
            if isinstance(raw_content, list):
                text = ""
                for item in raw_content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text += item.get("text", "")
                    elif isinstance(item, str):
                        text += item
                if not text:
                    text = str(raw_content)
            elif isinstance(raw_content, dict):
                text = raw_content.get("text", str(raw_content))
            else:
                text = str(raw_content)
            text, action_str = _clean_response(text)
            # v1.9.95 修复：action 始终返回解析后的 dict 或 None（与其他方法一致）
            action = json.loads(action_str) if action_str else None
            ret = {"text": text, "action": action}
            with self._cache_lock:
                self._cache[cache_key] = (ret, time.time())
            return ret
        except Exception as e:
            logger.info(f"[LLM] 对话异常: {type(e).__name__}: {e}")
            return {"text": "对话出错了，请稍后重试", "action": None}

    def _ollama_stream_chat(self, message: str, history: List[Dict] = None, callback=None,
                            memory_system = None, chunk_size: int = 10) -> Dict[str, Any]:
        """v1.9.38: Ollama 原生 API 流式对话（think:false 关闭思考模式）"""
        if not self._rate_limiter.acquire(timeout=30):
            return {"text": "请求过于频繁，请稍后再试", "action": None}

        try:
            messages = build_messages(message, history, None, memory_system)
            data = {
                "model": self.model,
                "messages": messages,
                "stream": True,
                "think": False,  # 关闭 Qwen3 思考模式
                "options": {
                    "num_predict": self.max_tokens,
                    "temperature": 0.7,
                }
            }
            # Ollama 原生端点是 /api/chat，去掉 base_url 中的 /v1 后缀避免 /v1/api/chat 404
            ollama_base = self.base_url.replace("/v1", "").rstrip("/")
            response = self._session.post(
                f"{ollama_base}/api/chat",
                json=data, timeout=120, stream=True
            )
            response.raise_for_status()

            full_text = ""
            buffer = ""

            for line in response.iter_lines():
                if not line:
                    continue
                line = line.decode('utf-8')
                try:
                    chunk = json.loads(line)
                    # Ollama 原生流式：每行一个完整 JSON 对象
                    msg = chunk.get("message", {})
                    content = msg.get("content", "")
                    if content:
                        full_text += content
                        buffer += content
                        if len(buffer) >= chunk_size and callback:
                            callback(buffer)
                            buffer = ""
                    # 流结束标志
                    if chunk.get("done", False):
                        break
                except Exception as e:
                    continue

            full_text, action_str = _clean_response(full_text)

            # v14 FIX: 检查流式结果是否为空
            if not full_text:
                full_text = "（LLM 未返回有效回复，请重试）"

            if buffer and callback:
                callback(buffer)
            action = json.loads(action_str) if action_str else None
            return {"text": full_text, "action": action}
        except Exception as e:
            logger.info(f"[LLM] Ollama 流式错误: {e}")
            return {"text": "对话出错了，请稍后重试", "action": None}

    def stream_chat(self, message: str, history: List[Dict] = None, callback=None,
                    memory_system = None, chunk_size: int = 10,
                    on_tool_call=None) -> Dict[str, Any]:
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
        # v1.9.38: Ollama 端点走原生 API 流式（支持 think:false）
        if self._is_ollama:
            return self._ollama_stream_chat(message, history, callback, memory_system, chunk_size)

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

            # v2.0: Function Calling — 添加工具定义
            try:
                from app.tools.fc_executor import get_tool_schemas
                tool_schemas = get_tool_schemas()
                if tool_schemas:
                    data["tools"] = tool_schemas
                    data["tool_choice"] = "auto"
            except Exception as e:
                logger.info(f"[LLM] FC 工具 schema 加载失败(不影响对话): {e}")

            response = self._session.post(
                f"{self.base_url}/chat/completions",
                json=data, timeout=120, stream=True
            )
            response.raise_for_status()

            acc = StreamAccumulator(chunk_size=chunk_size, callback=callback, on_tool_call=on_tool_call)

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
                    # v1.9.99 修复: choices 可能为空列表
                    chunk_choices = chunk.get("choices", [])
                    if not chunk_choices:
                        continue
                    choice = chunk_choices[0]
                    delta = choice.get("delta", {})
                    content = delta.get("content") or ""  # content 可能为 None

                    # v2.0: FC — 累积 tool_calls delta
                    delta_tool_calls = delta.get("tool_calls")
                    if delta_tool_calls:
                        for tc_delta in delta_tool_calls:
                            acc.accumulate_tool_call(tc_delta)

                    if content:
                        acc.process_content(content)
                except Exception as e:
                    continue

            # v2.0: FC — 检查 tool_calls + 流结束处理（委托 StreamAccumulator）
            acc.finish_reason = choice.get("finish_reason", "") if chunk.get("choices") else ""
            return acc.finish_with_fc(
                messages=messages, session=self._session, base_url=self.base_url,
                model=self.model, api_key=self.api_key, max_tokens=self.max_tokens,
                on_chunk=callback,
            )
        except Exception as e:
            logger.info(f"[LLM] OpenAI 流式错误: {e}")
            return {"text": "对话出错了，请稍后重试", "action": None}
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
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """
        【功能说明】初始化 Anthropic Claude LLM 引擎

        【参数说明】
            config (Dict[str, Any]): 配置字典，来自 config.yaml 的 llm.anthropic 节
                - api_key (str): Anthropic API Key
                - base_url (str): API 基础 URL，默认官方地址
                - model (str): 模型名称，默认 "claude-3-sonnet-20240229"
                - max_tokens (int): 最大生成 token 数，默认 2048
                - rate_limit (int): 每分钟最大请求数，默认 50（Anthropic 默认限制更严格）
        """
        self.config = config
        self.api_key = config.get("api_key", "")
        # v1.9.44: 支持自定义 base_url（代理/中转）
        self.base_url = config.get("base_url", "https://api.anthropic.com").rstrip("/")
        self.model = config.get("model", "claude-3-sonnet-20240229")
        self.max_tokens = config.get("max_tokens", 2048)
        
        # 【公共初始化】HTTP 连接池 + 缓存 + 速率限制器
        # Anthropic 默认速率限制较低（50 次/分钟）
        self._init_common(config, default_rate_limit=50)
        # Anthropic 官方 API 使用 x-api-key 认证头（与 OpenAI Bearer Token 不同）
        self._session.headers["x-api-key"] = self.api_key
        self._session.headers["anthropic-version"] = "2023-06-01"  # Anthropic API 版本（必填）
        
        logger.info(f"  Anthropic LLM v2.0 初始化: max_tokens={self.max_tokens}")

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
            # v1.9.44: 正确处理 Anthropic 格式 — system 消息通过顶层字段传递
            system_prompt = ""
            claude_messages = []
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                if role == "system":
                    # Anthropic 要求 system 通过顶层 "system" 字段传递
                    system_prompt = content
                else:
                    claude_messages.append({"role": role, "content": content})
            
            data = {
                "model": self.model,
                "messages": claude_messages,
                "temperature": 0.7,
                "max_tokens": self.max_tokens,
            }
            # Anthropic API 要求 system 通过顶层字段传递（非 messages 数组）
            if system_prompt:
                data["system"] = system_prompt
            
            response = self._session.post(
                f"{self.base_url}/v1/messages",
                json=data, timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            # v1.9.99 修复: Anthropic 返回空 content 列表时保护性处理
            content_blocks = result.get("content", [])
            text = ""
            for block in content_blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    text += block.get("text", "")
            # 清理 <think/> 标签（部分 Anthropic 模型会泄漏思维链标签）
            text, action = _clean_response(text)
            
            ret = {"text": text, "action": action}
            # v1.8: 缓存写入加锁
            with self._cache_lock:
                self._cache[cache_key] = (ret, time.time())

            return ret
        except Exception as e:
            logger.info(f"[LLM] 对话异常: {type(e).__name__}: {e}")
            return {"text": "对话出错了，请稍后重试", "action": None}

    def stream_chat(self, message: str, history: List[Dict] = None, callback=None,
                    memory_system = None, chunk_size: int = 10,
                    on_tool_call=None) -> Dict[str, Any]:
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
            # v1.9.44: 正确处理 Anthropic 格式 — system 消息通过顶层字段传递
            system_prompt = ""
            claude_messages = []
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                if role == "system":
                    system_prompt = content
                else:
                    claude_messages.append({"role": role, "content": content})
            
            data = {
                "model": self.model,
                "messages": claude_messages,
                "temperature": 0.7,
                "max_tokens": self.max_tokens,
                "stream": True,
            }
            if system_prompt:
                data["system"] = system_prompt
            
            response = self._session.post(
                f"{self.base_url}/v1/messages",
                json=data, timeout=120, stream=True
            )
            response.raise_for_status()
            
            acc = StreamAccumulator(chunk_size=chunk_size, callback=callback, filter_thinking=False)
            
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
                                acc.process_content(content)
                    
                    # 消息结束标志，退出流式循环
                    elif event_type == "message_stop":
                        break
                except Exception as e:
                    continue
            
            return acc.finish(response, use_clean_response=False)
        except Exception as e:
            logger.info(f"[LLM] Anthropic 流式错误: {e}")
            return {"text": "对话出错了，请稍后重试", "action": None}

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

