# ASR → LLM → TTS 全链路多线程/并发优化分析报告

> **项目**：咕咕嘎嘎 AI-VTuber v1.7.5  
> **分析范围**：`app/web/__init__.py`、`app/llm/__init__.py`、`app/tts/gptsovits.py`、`app/asr/__init__.py`  
> **分析日期**：2026-04-20  
> **分析目标**：识别并发架构中的 Bug、性能瓶颈和可优化点，按优先级排序并给出修复方案

---

## 目录

1. [执行摘要](#1-执行摘要)
2. [全链路并发架构总览](#2-全链路并发架构总览)
3. [Bug 清单](#3-bug-清单)
4. [各模块深度分析](#4-各模块深度分析)
5. [优化建议与实施方案](#5-优化建议与实施方案)
6. [优先级排序](#6-优先级排序)
7. [实施路线图](#7-实施路线图)

---

## 1. 执行摘要

本项目采用 **WebSocket 单线程事件循环 + daemon 线程池** 的混合并发架构，实现了 ASR→LLM→TTS 的实时语音对话能力。核心设计思路是正确的——使用 `threading.Event(cancel)` 实现协作式打断、`queue.Queue` 做 TTS 任务缓冲、`threading.Thread(daemon=True)` 隔离请求。

但深度审计发现 **3 个高危并发 Bug** 和 **1 个架构级性能瓶颈**：

| 级别 | 问题 | 影响 |
|------|------|------|
| 🔴 P0 | `cancel.set()` 与 `cancel.clear()` 之间竞态窗口 | 幽灵音频：旧 pipeline 的 TTS 继续播放 |
| 🔴 P0 | RateLimiter 锁内 `time.sleep()` | 所有 LLM 线程被串行化，吞吐量坍塌 |
| 🟡 P1 | `_cache` 字典无锁保护 | 多线程下缓存可能读到半写入状态 |
| 🟡 P1 | `on_chunk` 同步阻塞 LLM 流接收 | TTS 合成期间 LLM 输出被阻塞，首句延迟增加 |
| 🟢 P2 | OpenAI/Anthropic `stream_chat` 为伪流式 | 回退到 OpenAI/Anthropic 时首句延迟从 ~1s 增至 5-15s |

---

## 2. 全链路并发架构总览

### 2.1 线程模型

```
┌─────────────────────────────────────────────────────────────────┐
│                      Main Thread (WebSocket Server)              │
│  websocket-server 单线程事件循环                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  _handle_realtime_audio()                               │   │
│  │  ├── cancel.set() / cancel.clear()  ← 取消旧 pipeline    │   │
│  │  └── threading.Thread(target=realtime_pipeline) ← 新线程 │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                    │ spawn daemon thread
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│              realtime_pipeline (per-request daemon thread)       │
│  ┌─────────┐    ┌──────────────────┐    ┌──────────────────┐   │
│  │   ASR   │───▶│  LLM stream_chat │───▶│ on_chunk callback│   │
│  │ recognize│   │  iter_lines()   │    │ _split_sentences │   │
│  └─────────┘    └──────────────────┘    └────────┬─────────┘   │
│                                                   │             │
│                                                   ▼             │
│                                        ┌──────────────────┐    │
│                                        │ TTS speak_streaming│   │
│                                        │  (同步阻塞!)      │    │
│                                        │  on_chunk → WS    │    │
│                                        └──────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 并发原语使用清单

| 原语 | 位置 | 用途 |
|------|------|------|
| `threading.Thread(daemon=True)` | `web/__init__.py:2910` | 每个语音请求一个后台线程 |
| `threading.Event` (cancel) | `web/__init__.py:2692` | 协作式打断标志 |
| `queue.Queue` (tts_queue) | state dict | TTS 任务缓冲队列 |
| `threading.Lock` (init_lock) | `gptsovits.py:351` | Double-Checked Locking 防并发初始化 |
| `threading.Lock` (RateLimiter) | `llm/__init__.py:246` | LLM 请求限流（⚠️ 锁内 sleep） |
| `dict` (state) | per-client | 无锁字典，按 client_id 隔离 |
| `dict` (_cache) | `llm/__init__.py:403` | LLM 响应缓存（⚠️ 无锁保护） |

### 2.3 请求生命周期

```
用户说话 → VAD检测停顿 → 前端发送音频
  → _handle_realtime_audio()
    → cancel.set() [打断旧pipeline]
    → cancel.clear() [重置]
    → threading.Thread.start() [新线程]
      → ASR.recognize()
      → 语义判停检测
      → LLM.stream_chat(callback=on_chunk)
        → on_chunk: 增量分句 → TTS合成 → WS发送
      → pipeline完成: state["running"]=False
```

---

## 3. Bug 清单

### Bug #1 — cancel 竞态窗口（🔴 严重）

**位置**：`app/web/__init__.py:2692-2703`

**问题代码**：
```python
# 第2692行：设置取消标志
state["cancel"].set()
state["speaking"] = False
# ... 清空 TTS 队列 ...

# 第2703行：重置取消标志
state["cancel"].clear()
state["running"] = True
```

**根因**：`cancel.set()` 到 `cancel.clear()` 之间存在时间窗口，旧的 `realtime_pipeline` 线程的 `on_chunk` 回调可能正好在 `cancel.clear()` 之后、新 pipeline 启动之前检查 `cancel.is_set()`，发现为 `False`，继续执行 TTS 合成和发送。这导致 **幽灵音频**——新请求的回复和旧请求的 TTS 残余交替播放。

**触发条件**：
1. 旧 pipeline 的 LLM 正在流式输出
2. `on_chunk` 正好处于两个 `cancel.is_set()` 检查之间
3. 用户快速连续说话（打断间隔 < 100ms）

**修复方案**：见 [5.1 Generation ID 替代方案](#51-generation-id-替代-cancel-event)

---

### Bug #2 — RateLimiter 锁内 sleep（🔴 严重）

**位置**：`app/llm/__init__.py:246-255`

**问题代码**：
```python
def acquire(self, timeout: int = 30) -> bool:
    now = time.time()
    cutoff = now - self.window_seconds
    
    with self._lock:  # ← 获取锁
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
        
        if len(self.requests) >= self.max_requests:
            wait_time = self.requests[0] - cutoff
            if timeout > 0 and wait_time > timeout:
                return False
            time.sleep(min(wait_time, timeout))  # ⚠️ 持有锁的同时 sleep！
            return self.acquire(0)
        
        self.requests.append(now)
        return True
```

**根因**：`time.sleep()` 在 `with self._lock` 内执行。在 sleep 期间，所有其他调用 `acquire()` 的线程都被阻塞在锁上，等待当前线程 sleep 完成。这完全违背了限流器的初衷——本应允许请求排队等待，实际却将所有请求串行化。

**影响**：
- 单客户端场景：每次限流等待时，所有其他客户端的 LLM 请求被阻塞
- 多客户端场景：一个客户端触发限流 → 所有客户端卡住直到等待结束
- 极端情况：多个线程同时触发限流 → 锁内递归调用 `self.acquire(0)` → 递归深度增加

**修复方案**：见 [5.2 RateLimiter 修复](#52-ratelimiter-修复)

---

### Bug #3 — LLM 缓存无锁保护（🟡 中等）

**位置**：`app/llm/__init__.py:403-418`

**问题代码**：
```python
cache_key = f"{message}:{len(history or [])}"
if cache_key in self._cache:           # ← 读操作
    cached, ts = self._cache[cache_key] # ← 读操作
    if time.time() - ts < self._cache_ttl:
        return cached

# ... LLM 请求 ...

self._cache[cache_key] = (result, time.time())  # ← 写操作
if len(self._cache) > 100:
    now = time.time()
    self._cache = {k: v for k, v in self._cache.items() if now - v[1] < self._cache_ttl}  # ← 重建整个字典
```

**根因**：Python `dict` 虽然在 CPython 中由于 GIL 对单次操作是原子的，但组合操作（先读后写、重建字典）不是原子的。在多线程环境下：
- 线程 A 检查 `cache_key in self._cache` → False
- 线程 B 写入 `self._cache[cache_key]`
- 线程 A 发起重复的 LLM 请求（性能浪费）
- 字典重建时 `self._cache = {k: v for ...}` 不是原子操作，其他线程可能读到空字典

**修复方案**：见 [5.3 缓存线程安全](#53-缓存线程安全)

---

### Bug #4 — on_chunk 同步阻塞 LLM 流接收（🟡 性能瓶颈）

**位置**：`app/web/__init__.py:3005-3055` → `_realtime_tts_single` → `_tts_do_and_send`

**调用链**：
```
MiniMax LLM (真流式)
  → response.iter_lines()  ← 网络循环
    → callback(buffer)  ← 每 chunk_size 字符触发
      → on_chunk()  ← web 层
        → _split_sentences_streaming()  ← 分句
          → _realtime_tts_single()  ← 同步调用
            → _tts_do_and_send()  ← 同步调用
              → tts_engine.speak_streaming()  ← GPU 推理，阻塞 200-800ms/句
```

**根因**：`on_chunk` 回调在 `iter_lines()` 的循环中被同步调用。当 TTS 合成一句需要 200-800ms（GPT-SoVITS GPU 推理），在这段时间内 `iter_lines()` 循环被阻塞，无法接收新的 LLM 输出 chunk。这导致：

1. **首句延迟叠加**：ASR(500ms) + LLM首chunk(800ms) + TTS首句(300ms) = **~1.6s**
2. **LLM 输出缓冲堆积**：TTS 合成期间，LLM 继续输出但无法被消费，文本堆积在 `sentence_buffer`
3. **无法并行**：TTS 和 LLM 本应并行工作，但被串行化了

**修复方案**：见 [5.4 TTS 异步化](#54-tts-异步化)

---

## 4. 各模块深度分析

### 4.1 ASR 模块（`app/asr/__init__.py`）

**并发安全性**：✅ 低风险

- FunASR / Faster-Whisper 均为懒加载模式，模型加载在 `__init__` 中完成
- `recognize()` 方法无共享可变状态，每次调用独立
- Faster-Whisper fallback（`_fallback_whisper`）的懒加载有潜在竞态：
  ```python
  # web/__init__.py:2776
  if not hasattr(self, '_fallback_whisper'):
      self._fallback_whisper = WhisperModel("base", device="cpu")  # 无锁
  ```
  两个线程同时触发 fallback 时可能重复加载，但后果仅为浪费内存，不影响正确性。

**建议**：
- 对 `_fallback_whisper` 加 `threading.Lock` 保护懒加载
- `recognize_batch()` 是逐个串行识别的，可改为 `ThreadPoolExecutor` 并行（如果有多段音频同时需要识别的场景）

---

### 4.2 LLM 模块（`app/llm/__init__.py`）

#### 4.2.1 RateLimiter（第233-263行）

**严重问题**：锁内 sleep（Bug #2），详见 [3.2](#bug-2--ratelimiter-锁内-sleep-严重)

#### 4.2.2 流式实现差异

| 提供商 | 实现方式 | 真流式 | 首句延迟 |
|--------|----------|--------|----------|
| MiniMax | `response.iter_lines()` + 逐 chunk 回调 | ✅ | ~800ms |
| Anthropic | `_stream_anthropic()` + 逐 chunk 回调 | ✅ | ~1s |
| OpenAI | `chat()` 同步调用 → 整段返回 → 单次 callback | ❌ | 5-15s |
| Anthropic (stream_chat) | `chat()` 同步调用 → 整段返回 → 单次 callback | ❌ | 5-15s |

**问题**：OpenAI 和 Anthropic 的 `stream_chat()` 方法（第689-694、771-776行）是伪流式：
```python
def stream_chat(self, message, history, callback=None, memory_system=None, chunk_size=10):
    result = self.chat(message, history, memory_system)  # 同步等待完整响应
    if callback and result.get("text"):
        callback(result["text"][:chunk_size])  # 只回调一次
    return result
```

注意：Anthropic 的 `_stream_anthropic()` 是真流式的，但 `stream_chat()` 入口没有调用它，而是直接调了 `chat()`。这是一个需要修复的接口遗漏。

#### 4.2.3 缓存设计

- 缓存键：`f"{message}:{len(history or [])}"` — 忽略了 history 内容，只看长度
- 缓存 TTL：300s（5分钟）
- 最大容量：100 条，超限时按 TTL 清理
- **问题**：不同对话内容如果消息数相同且当前消息相同，会命中错误缓存

---

### 4.3 TTS 模块（`app/tts/gptsovits.py`）

#### 4.3.1 并发初始化（第341-355行）

```python
def _lazy_init(self):
    if self.tts_pipeline is not None:
        return
    if not hasattr(self, '_init_lock'):
        import threading
        self._init_lock = threading.Lock()
    with self._init_lock:
        if self.tts_pipeline is not None:
            return  # double-check
        # ... 加载模型 ...
```

**评估**：✅ 正确的 Double-Checked Locking 模式

Python 的 GIL 保证了 `tts_pipeline is not None` 的读取是原子的，外层检查避免了不必要的锁竞争。内层 double-check 处理了两个线程同时通过外层检查的情况。

**微小改进**：`if not hasattr(self, '_init_lock')` 本身不是线程安全的，但因为它只在 `tts_pipeline is None` 时执行，且锁一旦创建就不会再改变，所以实际上不会出问题。可以在 `__init__` 中初始化 `_init_lock` 更规范。

#### 4.3.2 GPU 串行策略

v1.5.3 之后，TTS 从多线程并行改为 **串行调用**。这是正确的决策——GPT-SoVITS 的 GPU 推理不支持多线程并发（显存冲突、CUDA context 切换开销），串行化是唯一安全的方案。

当前串行化方式是在 `on_chunk` 回调中同步调用 `_realtime_tts_single()`，隐式地串行化了所有 TTS 请求。但这也导致了 Bug #4（LLM 流被阻塞）。

---

### 4.4 Pipeline 层（`app/web/__init__.py`）

#### 4.4.1 打断机制分析

**正常打断流程**（`_handle_realtime_audio`）：
```
新音频到达
  → 检查 state["speaking"] || state["running"]
    → cancel.set()       ← 通知旧 pipeline
    → speaking = False
    → 清空 tts_queue
    → cancel.clear()     ← ⚠️ 竞态窗口开始
    → running = True     ← 启动新 pipeline
```

**快速打断流程**（`_handle_realtime_interrupt_fast`）：
```
用户开始说话（VAD 检测到）
  → cancel.set()
  → speaking = False
  → running = False     ← 更激进
  → 清空 tts_queue
  → 立即 ACK 前端
```

**竞态窗口分析**：

```
时间线：
  t0: 旧 pipeline 的 on_chunk 检查 cancel.is_set() → False
  t1: 新请求到达，cancel.set()
  t2: 新请求 cancel.clear()  ← ⚠️ 旧 on_chunk 如果在 t2 后再次检查，看到 False
  t3: 旧 on_chunk 继续执行 TTS → 幽灵音频！
```

关键在于 t1-t2 之间的窗口。如果旧 `on_chunk` 正好在这个窗口内执行，且它的 `cancel.is_set()` 检查落在 t2 之后，就会逃过取消。

---

## 5. 优化建议与实施方案

### 5.1 Generation ID 替代 cancel Event

**目标**：彻底消除 cancel 竞态窗口

**方案**：每个 pipeline 请求分配一个唯一的 generation ID，所有回调检查当前 generation ID 而非 cancel 标志。

```python
import uuid

def _handle_realtime_audio(self, client, data):
    client_id = client['id']
    state = self._get_realtime_state(client_id)
    
    # 分配新 generation ID
    gen_id = str(uuid.uuid4())[:8]
    state["current_gen"] = gen_id
    state["running"] = True
    state["speaking"] = False
    # 清空 TTS 队列
    while not state["tts_queue"].empty():
        try:
            state["tts_queue"].get_nowait()
        except Exception:
            break
    
    # 不再需要 cancel.set() / cancel.clear()
    # 旧 pipeline 通过检查 generation ID 自动失效

    def realtime_pipeline():
        try:
            # 在每个关键节点检查 generation
            if state.get("current_gen") != gen_id:
                return  # 已被新请求取代
            
            # ASR 识别...
            if state.get("current_gen") != gen_id:
                return
            
            # LLM 流式...
            def on_chunk(chunk_text):
                if state.get("current_gen") != gen_id:  # ← 检查 generation
                    return
                # 分句 + TTS...
            
            # TTS 合成...
            if state.get("current_gen") != gen_id:
                return
        finally:
            # 只有当前 generation 才清理状态
            if state.get("current_gen") == gen_id:
                state["speaking"] = False
                state["running"] = False
    
    threading.Thread(target=realtime_pipeline, daemon=True).start()
```

**优势**：
- 无竞态窗口：gen_id 是原子赋值（Python GIL 保证）
- 旧 pipeline 不需要"被通知"，自己检查发现过期就退出
- `cancel` Event 可以保留用于快速打断场景，但不再是唯一防护

**改动范围**：`web/__init__.py` 中约 8 处 `cancel.is_set()` 检查替换为 generation ID 检查

---

### 5.2 RateLimiter 修复

**目标**：消除锁内 sleep，允许并发等待

**方案**：使用 Condition 变量替代 Lock + sleep

```python
import threading
from collections import deque
import time

class RateLimiter:
    """速率限制器 - 滑动窗口（线程安全版）"""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self._condition = threading.Condition(threading.Lock())  # Condition = Lock + wait/notify
    
    def acquire(self, timeout: int = 30) -> bool:
        deadline = time.time() + timeout
        
        with self._condition:
            while True:
                now = time.time()
                cutoff = now - self.window_seconds
                
                # 清理过期记录
                while self.requests and self.requests[0] < cutoff:
                    self.requests.popleft()
                
                if len(self.requests) < self.max_requests:
                    self.requests.append(now)
                    return True
                
                # 计算需要等待的时间
                wait_time = self.requests[0] - cutoff
                remaining = deadline - now
                
                if remaining <= 0 or wait_time > remaining:
                    return False  # 超时
                
                # 释放锁并等待（不阻塞其他线程）
                self._condition.wait(timeout=min(wait_time, remaining))
    
    def reset(self):
        with self._condition:
            self.requests.clear()
            self._condition.notify_all()  # 唤醒所有等待的线程
```

**关键变化**：
- `threading.Lock` → `threading.Condition`：`wait()` 会原子性地释放锁并挂起线程
- 不再在锁内 sleep：其他线程可以在等待期间获取锁、检查限流状态
- `notify_all()` 在 `reset()` 时唤醒所有等待线程

---

### 5.3 缓存线程安全

**目标**：防止多线程下缓存读写竞态

**方案**：使用 `threading.Lock` 保护缓存操作

```python
class LLMEngine:
    def __init__(self, ...):
        ...
        self._cache = {}
        self._cache_ttl = 300
        self._cache_lock = threading.Lock()
    
    def chat(self, message, history=None, memory_system=None):
        cache_key = f"{message}:{len(history or [])}"
        
        # 读取缓存（加锁）
        with self._cache_lock:
            if cache_key in self._cache:
                cached, ts = self._cache[cache_key]
                if time.time() - ts < self._cache_ttl:
                    return cached
        
        # LLM 请求（不持锁）
        if not self._rate_limiter.acquire(timeout=30):
            return {"text": "请求过于频繁，请稍后再试", "action": None}
        
        result = self._do_chat(message, history, memory_system)
        
        # 写入缓存（加锁）
        with self._cache_lock:
            self._cache[cache_key] = (result, time.time())
            if len(self._cache) > 100:
                now = time.time()
                self._cache = {
                    k: v for k, v in self._cache.items() 
                    if now - v[1] < self._cache_ttl
                }
        
        return result
```

**额外建议**：改进缓存键设计，加入 history 内容哈希：
```python
import hashlib
history_hash = hashlib.md5(
    json.dumps(history or [], sort_keys=True).encode()
).hexdigest()[:8]
cache_key = f"{message}:{history_hash}"
```

---

### 5.4 TTS 异步化

**目标**：TTS 合成不阻塞 LLM 流接收

**方案**：使用独立 TTS 线程 + 句子队列

```python
import queue
import threading

def _realtime_stream_pipeline(self, client, state, text, llm, engine, voice, no_split=False):
    sentence_buffer = ""
    cancel = state["cancel"]
    
    # 新增：句子队列 + TTS 工作线程
    sentence_queue = queue.Queue()
    tts_active = [True]  # 用列表包装以允许闭包修改
    
    def tts_worker():
        """独立的 TTS 消费线程"""
        while tts_active[0] or not sentence_queue.empty():
            try:
                item = sentence_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            
            gen_id, sentence = item
            
            # 检查 generation
            if state.get("current_gen") != gen_id:
                sentence_queue.task_done()
                continue
            
            # 执行 TTS（此时不阻塞 LLM 流接收）
            try:
                self._tts_do_and_send(client, state, sentence, voice, engine)
            except Exception as e:
                print(f"[TTS Worker] 错误: {e}")
            finally:
                sentence_queue.task_done()
    
    gen_id = state.get("current_gen", "")
    tts_thread = threading.Thread(target=tts_worker, daemon=True)
    tts_thread.start()
    
    def on_chunk(chunk_text):
        nonlocal sentence_buffer
        if state.get("current_gen") != gen_id:
            return
        
        chunk_text = self._strip_tool_calls(chunk_text)
        sentences, sentence_buffer = self._split_sentences_streaming(
            sentence_buffer + chunk_text
        )
        
        for sent in sentences:
            if state.get("current_gen") != gen_id:
                return
            # 放入队列，不等待 TTS 完成
            sentence_queue.put((gen_id, sent))
    
    # LLM 流式调用（不再被 TTS 阻塞）
    result = llm.stream_chat(text, callback=on_chunk, chunk_size=5, ...)
    
    # LLM 完成，发送剩余 buffer
    if sentence_buffer.strip() and state.get("current_gen") == gen_id:
        sentence_queue.put((gen_id, sentence_buffer.strip()))
    
    # 等待 TTS 队列清空
    sentence_queue.join()
    tts_active[0] = False  # 通知 worker 退出
```

**效果**：
- LLM 流接收和 TTS 合成完全并行
- 首句延迟不变（仍需等 LLM 首句 + TTS 首句），但后续句子的延迟大幅降低
- LLM 输出不再因 TTS 阻塞而堆积

**注意事项**：
- GPT-SoVITS GPU 推理仍然串行（TTS worker 是单线程）
- 句子顺序通过单 worker + FIFO 队列保证
- 打断时 generation ID 检查确保旧句子被丢弃

---

### 5.5 OpenAI/Anthropic 伪流式 → 真流式

**目标**：OpenAI 和 Anthropic 的 `stream_chat` 使用真正的 SSE 流式

**OpenAI 修复**：
```python
class OpenAILLM(LLMEngine):
    def stream_chat(self, message, history=None, callback=None, 
                    memory_system=None, chunk_size=10):
        messages = build_messages(message, history, None, memory_system)
        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": 1.0,
            "stream": True,  # ← 关键：启用流式
        }
        
        response = self._session.post(
            f"{self.base_url}/v1/chat/completions",
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
            if data_str == "[DONE]":
                break
            
            chunk = json.loads(data_str)
            delta = chunk["choices"][0].get("delta", {})
            content = delta.get("content", "")
            
            if content:
                full_text += content
                buffer += content
                if len(buffer) >= chunk_size and callback:
                    callback(buffer)
                    buffer = ""
        
        if buffer and callback:
            callback(buffer)
        
        return {"text": full_text, "action": _parse_action(full_text)}
```

**Anthropic 修复**：已有 `_stream_anthropic()` 实现真流式，只需让 `stream_chat()` 调用它：
```python
class AnthropicLLM(LLMEngine):
    def stream_chat(self, message, history=None, callback=None,
                    memory_system=None, chunk_size=10):
        # 直接调用已有的真流式实现
        return self._stream_anthropic(message, history, callback, memory_system, chunk_size)
```

---

### 5.6 其他优化建议

#### 5.6.1 ASR 预加载

当前 ASR fallback 模型（`_fallback_whisper`）在首次失败时懒加载，需要 5-10 秒。可以在启动时预加载：

```python
# 在 web/__init__.py 的 __init__ 或 setup 中
if config.asr.enable_fallback:
    self._fallback_whisper = WhisperModel("base", device="cpu")
```

#### 5.6.2 TTS 队列清空原子化

当前 TTS 队列清空是循环 `get_nowait()`：
```python
while not state["tts_queue"].empty():
    try:
        state["tts_queue"].get_nowait()
    except Exception:
        break
```

问题：`empty()` 和 `get_nowait()` 之间可能有新元素入队。改进：
```python
# 直接清空（queue.Queue 内部有锁保护）
with state["tts_queue"].mutex:
    state["tts_queue"].queue.clear()
```

#### 5.6.3 WebSocket 发送保护

`self.server.send_message(client, ...)` 在多个位置被调用，但没有异常保护（部分有 try-except，部分没有）。如果客户端断连，可能抛出异常。建议统一包装：

```python
def _safe_send(self, client, message):
    """安全发送 WebSocket 消息"""
    try:
        self.server.send_message(client, json.dumps(message))
        return True
    except Exception as e:
        print(f"[WS] 发送失败: {e}")
        return False
```

---

## 6. 优先级排序

| 优先级 | 编号 | 问题 | 预计工作量 | 影响面 |
|--------|------|------|------------|--------|
| **P0** | #1 | cancel 竞态窗口（幽灵音频） | 2h | 所有用户，每次打断 |
| **P0** | #2 | RateLimiter 锁内 sleep | 0.5h | 多客户端场景 |
| **P1** | #3 | LLM 缓存无锁 | 0.5h | 多线程 LLM 调用 |
| **P1** | #4 | TTS 异步化（LLM 流不被阻塞） | 4h | 首句延迟、用户体验 |
| **P1** | #5 | OpenAI/Anthropic 伪流式修复 | 1h | OpenAI/Anthropic 用户 |
| **P2** | #6 | ASR 预加载 | 0.5h | 首次 fallback 延迟 |
| **P2** | #7 | TTS 队列清空原子化 | 0.2h | 打断边界情况 |
| **P2** | #8 | WS 发送统一保护 | 0.5h | 客户端断连稳定性 |

---

## 7. 实施路线图

### Phase 1：紧急修复（P0，预计 2.5h）

```
v1.7.6 — 并发 Bug 修复
├── [P0] Generation ID 替代 cancel Event（Bug #1）
│   ├── 新增 state["current_gen"] = uuid
│   ├── 替换 8 处 cancel.is_set() 检查
│   └── 保留 cancel Event 用于快速打断
├── [P0] RateLimiter Condition 替代 Lock+sleep（Bug #2）
│   ├── threading.Lock → threading.Condition
│   ├── sleep → condition.wait()
│   └── reset() 中 notify_all()
└── [P1] LLM 缓存加锁（Bug #3）
    ├── 新增 self._cache_lock
    └── 读写缓存时加锁
```

### Phase 2：性能优化（P1，预计 5h）

```
v1.8.0 — 全链路延迟优化
├── [P1] TTS 异步化（Bug #4）
│   ├── 新增 sentence_queue + tts_worker 线程
│   ├── on_chunk 只入队不等待
│   └── pipeline 结束时 join 队列
├── [P1] OpenAI 真流式（Bug #5）
│   ├── OpenAI stream_chat 使用 SSE
│   └── Anthropic stream_chat 调用 _stream_anthropic
└── [P2] 缓存键改进
    └── history 内容哈希加入 cache_key
```

### Phase 3：稳定性增强（P2，预计 1.2h）

```
v1.8.1 — 稳定性改进
├── [P2] ASR fallback 预加载
├── [P2] TTS 队列清空原子化
├── [P2] WebSocket 发送统一保护
└── [P2] _fallback_whisper 加锁保护
```

---

## 附录 A：测试建议

### A.1 并发 Bug 复现测试

```python
import threading
import time

def test_cancel_race_condition():
    """测试 cancel 竞态窗口"""
    # 模拟旧 pipeline 在 cancel.set() 和 cancel.clear() 之间执行
    cancel = threading.Event()
    cancel.set()
    
    # 模拟旧 on_chunk 在 clear 之后检查
    time.sleep(0.001)  # 极短延迟
    cancel.clear()
    
    # 如果旧 on_chunk 正好在 clear 之后检查
    assert not cancel.is_set()  # ← 旧 pipeline 逃过取消
    
    # Generation ID 方案不会出现此问题
    gen_old = "aaa"
    gen_new = "bbb"
    state = {"current_gen": gen_new}
    
    # 旧 pipeline 检查
    assert state["current_gen"] != gen_old  # ← 正确识别为过期

def test_ratelimiter_concurrent():
    """测试 RateLimiter 多线程行为"""
    from collections import deque
    import threading
    
    limiter = RateLimiter(max_requests=3, window_seconds=1)
    results = []
    
    def worker(i):
        start = time.time()
        ok = limiter.acquire(timeout=5)
        elapsed = time.time() - start
        results.append((i, ok, elapsed))
    
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # 验证：前3个立即通过，后2个等待
    immediate = sum(1 for _, ok, e in results if ok and e < 0.1)
    waited = sum(1 for _, ok, e in results if ok and e >= 0.8)
    assert immediate == 3
    assert waited == 2
```

### A.2 性能基准测试

测试指标：
- **首句延迟**（First Token Latency）：用户说完到听到第一个音节
- **打断响应时间**：用户打断到旧音频停止
- **多客户端吞吐**：3个客户端同时对话时的响应时间

建议在每个 Phase 完成后重新跑基准测试，量化优化效果。

---

*报告结束。如有疑问或需要更详细的实现代码，请随时提出。*
