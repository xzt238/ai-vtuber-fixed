# 咕咕嘎嘎 AI-VTuber 架构分析报告

> 版本: v1.6.0  
> 更新日期: 2026-04-19  
> 总代码行数: 65,224 行（app/ 核心模块 ~12,000 行）

---

## 目录

1. [项目概述](#1-项目概述)
2. [模块架构总览](#2-模块架构总览)
3. [核心模块详解](#3-核心模块详解)
4. [模块依赖关系](#4-模块依赖关系)
5. [数据流向](#5-数据流向)
6. [接口定义](#6-接口定义)
7. [配置文件说明](#7-配置文件说明)

---

## 1. 项目概述

### 1.1 项目目标
构建一个具有本地推理能力的AI虚拟形象系统，支持实时语音对话、音色克隆、记忆系统和Live2D虚拟形象。

### 1.2 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| ASR | FunASR + Faster-Whisper | 本地语音识别 |
| LLM | MiniMax-M2.5 / OpenAI / Anthropic | 大语言模型 |
| TTS | GPT-SoVITS / EdgeTTS | 语音合成（支持音色克隆） |
| 记忆 | RAG + 四层架构 | 长期记忆系统 |
| 前端 | Web + WebSocket | 实时交互界面 |

### 1.3 代码统计

| 模块 | 文件数 | 代码行数 | 占比 |
|------|--------|----------|------|
| **app/ (核心)** | 15 | ~12,000 | 18% |
| **GPT-SoVITS/** | 100+ | ~53,000 | 82% |
| **总计** | **150+** | **65,224** | 100% |

---

## 2. 模块架构总览

```
ai-vtuber-fixed/
├── app/                           # 核心应用 (~12,000行)
│   ├── main.py                    # 入口程序，懒加载协调器
│   ├── config.yaml                # 配置文件
│   │
│   ├── web/                       # Web服务层
│   │   └── __init__.py           # HTTP + WebSocket 服务器
│   │
│   ├── llm/                       # 大语言模型层
│   │   ├── __init__.py            # LLM引擎 + PromptInjector + MemoryRAGInjector
│   │   └── prompts.py             # Prompt模板
│   │
│   ├── tts/                       # 语音合成层
│   │   ├── __init__.py            # TTS工厂 + EdgeTTS
│   │   └── gptsovits.py           # GPT-SoVITS 引擎（音色克隆）
│   │
│   ├── asr/                       # 语音识别层
│   │   └── __init__.py            # ASR工厂 + FunASR + Faster-Whisper
│   │
│   ├── memory/                    # 记忆系统
│   │   └── __init__.py            # 四层记忆架构 + RAG检索
│   │
│   ├── vision/                    # 视觉处理
│   │   └── __init__.py            # 截图 + OCR + 视觉理解
│   │
│   ├── subagent.py                # 子Agent（参考Claude Code）
│   │
│   ├── vtubestudio/               # Live2D集成
│   │   └── __init__.py            # VTube Studio HTTP API
│   │
│   └── trainer/                  # LoRA训练管理
│       └── manager.py              # Web端训练系统
│
├── GPT-SoVITS/                    # 训练推理框架 (~53,000行)
│   ├── GPT_SoVITS/                # 核心模型代码
│   ├── tools/                    # 工具（UVR5人声分离等）
│   └── api*.py                    # API服务
│
└── docs/
    └── VERSION.md                 # 版本历史
```

---

## 3. 核心模块详解

---

### 3.1 main.py - 主程序入口

**文件**: `app/main.py` (902行)

**功能**:
- 配置加载（YAML + 环境变量展开）
- 模块懒加载协调器
- 统一入口点

**关键类**:

#### Config 类
```python
class Config:
    def _load(self) -> Dict[str, Any]
    def get(self, key: str, default: Any = None) -> Any
```

#### AIVTuber 类（懒加载）
```python
class AIVTuber:
    # 懒加载属性
    @property
    def asr(self)      # 语音识别
    @property
    def tts(self)      # 语音合成
    @property
    def llm(self)      # 大语言模型
    @property
    def memory(self)    # 记忆系统
    @property
    def web_server(self)   # HTTP服务器
    @property
    def ws_server(self)    # WebSocket服务器
    @property
    def subagent(self)  # 子Agent

    # 核心方法
    def process_message(text: str) -> Dict[str, Any]   # 处理文字消息
    def process_audio(audio_path: str) -> Dict[str, Any]  # 处理音频
    def speak(text: str) -> str   # 语音合成
    def run_web()                  # 启动Web模式
    def run_interactive()          # 交互模式
```

**懒加载机制**:
- 首次访问属性时才加载对应模块
- 避免启动时加载所有模型，提升响应速度
- 配置: `app/config.yaml`

---

### 3.2 web/__init__.py - Web服务层

**文件**: `app/web/__init__.py` (3,292行)

**功能**:
- HTTP服务器（静态文件、音频服务）
- WebSocket实时通信
- 实时语音对话Pipeline
- 训练API

**关键类**:

#### WebServer
```python
class WebServer:
    def start(self)           # 启动HTTP服务器
    def _prewarm_tts(self)    # TTS引擎预热（消除冷启动）
```

#### WebSocketServer
```python
class WebSocketServer:
    # 实时语音Pipeline
    def _realtime_stream_pipeline(...)   # 完整Pipeline
    def _handle_realtime_audio(...)      # 处理实时音频

    # 文本对话
    def _text_worker(...)                # 后台处理文本消息

    # 音频处理
    def _handle_audio_upload(...)        # 处理音频上传
    def _handle_stt(...)                 # ASR识别
```

**API端点**:

| 端点 | 方法 | 功能 |
|------|------|------|
| `/audio/*` | GET | 音频文件服务 |
| `/train/upload` | POST | 训练音频上传 |
| `/api/sandbox/status` | GET | 沙盒状态 |
| `/api/sandbox/*` | POST | 沙盒路径管理 |

**WebSocket消息格式**:

```json
// 客户端 → 服务端
{"type": "text", "text": "你好"}
{"type": "audio", "data": "base64..."}
{"type": "realtime_audio", "data": "base64..."}

// 服务端 → 客户端
{"type": "llm_response", "text": "...", "audio": "/audio/xxx.wav"}
{"type": "tts_done", "audio": "/audio/xxx.wav"}
{"type": "stt_result", "text": "..."}
{"type": "status", "status": "🎤 聆听中..."}
```

---

### 3.3 llm/__init__.py - LLM调用模块

**文件**: `app/llm/__init__.py` (802行)

**功能**:
- 多LLM提供商支持（MiniMax/OpenAI/Anthropic）
- Prompt模块化注入（参考Neuro架构）
- 记忆RAG注入
- 速率限制和重试

**关键类**:

```python
# Prompt注入系统
@dataclass
class PromptInjection:
    content: str
    category: str  # system/personality/memory/context

class PromptInjector:
    def add(self, injection: PromptInjection)
    def build_system_prompt() -> str
    def inject_memories(memory_text: str)

# RAG记忆注入
class MemoryRAGInjector:
    def inject(self, query: str, memory_system) -> str

# LLM引擎基类
class LLMEngine(ABC):
    @abstractmethod
    def chat(self, message: str, history: List, memory_system=None) -> Dict
    @abstractmethod
    def stream_chat(self, message: str, callback, memory_system=None)
    @abstractmethod
    def is_available(self) -> bool

# 具体实现
class MiniMaxLLM(LLMEngine)
class OpenAILLM(LLMEngine)
class AnthropicLLM(LLMEngine)

# 工厂
class LLMFactory:
    @staticmethod
    def create(config: dict) -> LLMEngine
```

**对话流程**:
1. `build_messages()` 构建消息列表
2. `PromptInjector.inject_memories()` 注入记忆
3. 调用具体LLM引擎
4. 返回响应

---

### 3.4 tts/ - 语音合成层

#### 3.4.1 tts/__init__.py - TTS工厂

**文件**: `app/tts/__init__.py` (623行)

```python
# TTS引擎基类
class TTSEngine(ABC):
    @abstractmethod
    def speak(self, text: str, output_path: str = None) -> Optional[str]
    @abstractmethod
    def is_available(self) -> bool
    def stop(self)
    def get_voices(self) -> list

# Edge TTS（保底引擎）
class EdgeTTS(TTSEngine):
    VOICES = {
        "zh-CN": {"XiaoxiaoNeural", "XiaoyiNeural", ...},
        "zh-HK": {"HiuGaaiNeural", ...}
    }

# 工厂
class TTSFactory:
    @staticmethod
    def create(config: dict) -> TTSEngine
```

#### 3.4.2 tts/gptsovits.py - GPT-SoVITS引擎

**文件**: `app/tts/gptsovits.py` (840行)

```python
class GPTSoVITSEngine:
    """GPT-SoVITS 轻量化推理引擎（单例）"""

    # 项目管理
    def set_project(project_name: str)      # 切换音色项目
    def get_available_projects() -> List    # 获取所有项目
    def save_trained_models(...)            # 保存训练模型

    # 语音合成
    def speak(text, ref_audio_path, ref_text, ...) -> str
    def speak_streaming(text, ..., on_chunk=None) -> str
    def speak_zero_shot(text) -> str

    # 状态
    def is_available() -> bool
    def get_voices() -> list
```

**项目配置结构** (`config.json`):
```json
{
    "ref_audio": "path/to/ref.wav",
    "ref_text": "参考音频文本",
    "trained_gpt": "path/to/gpt.ckpt",
    "trained_sovits": "path/to/sovits.pth"
}
```

**分句策略** (v1.6优化):
- MAX_CHARS: 40 → 80
- 优先在标点处断开
- 次优先在连接词处断开
- 最后才硬切

---

### 3.5 asr/__init__.py - 语音识别

**文件**: `app/asr/__init__.py`

```python
class ASREngine(ABC):
    @abstractmethod
    def recognize(self, audio_path: str) -> Optional[str]
    @abstractmethod
    def is_available(self) -> bool

# FunASR（主用）
class FunASRASR(ASREngine)
    # paraformer-zh 模型

# Faster-Whisper（备用）
class FasterWhisperASR(ASREngine)
    # small/base 模型

class ASRFactory:
    @staticmethod
    def create(config: dict) -> ASREngine
```

---

### 3.6 memory/__init__.py - 记忆系统

**文件**: `app/memory/__init__.py` (953行)

**功能**:
- 四层记忆架构
- 遗忘机制
- 滑动窗口摘要压缩
- 混合检索（向量 + 关键词 + 时间权重）

**四层架构**:

```
┌─────────────────────────────────────────┐
│  工作记忆 (Working Memory)               │
│  - 当前对话上下文                        │
│  - Sliding Window (20条)                │
│  - 超过阈值触发摘要压缩                   │
└─────────────────────────────────────────┘
            ↓ 摘要压缩
┌─────────────────────────────────────────┐
│  情景记忆 (Episodic Memory)             │
│  - 已完成对话的摘要                       │
│  - 遗忘机制（保留分数 < 0.3 软删除）      │
└─────────────────────────────────────────┘
            ↓ 重要记忆
┌─────────────────────────────────────────┐
│  语义记忆 (Semantic Memory)              │
│  - 向量存储                             │
│  - 混合检索（0.7×向量 + 0.2×关键词 + 0.1×时间）│
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│  程序记忆 (Procedural Memory)            │
│  - Agent行为模式                        │
│  - 工具使用习惯                         │
│  - 在prompts.py中管理                   │
└─────────────────────────────────────────┘
```

**关键类**:

```python
@dataclass
class MemoryItem:
    role: str
    content: str
    timestamp: float
    importance: int  # 0-5
    access_count: int
    connectivity: int
    is_forgotten: bool
    is_summary: bool

class MemorySystem:
    # 添加记忆
    def add_interaction(role, content, importance=None)

    # 检索
    def search(query, top_k=3) -> List[Dict]

    # 摘要
    def summarize() -> str
    def _compress_early_memory()  # 滑动窗口压缩

    # 遗忘
    def _forgetting_sweep()      # 遗忘扫描

    # 统计
    def get_stats() -> Dict

    # 持久化
    def export() -> str
    def clear_all()
```

**遗忘机制**:

保留分数 = 重要性 × 时效衰减 × 访问频率 × 关联度

```
保留分数 = (importance/5.0) × e^(-0.01×hours) × (1+0.2×log(1+access)) × (1+0.1×connectivity)
```

低于 0.3 分的记忆会被软删除。

---

### 3.7 subagent.py - 子Agent

**文件**: `app/subagent.py` (990行)

**功能**:
- 工具选择与执行
- 沙盒模式（路径限制）
- 参考Claude Code AgentTool架构

**工具列表**:

| 工具 | 功能 | 沙盒限制 |
|------|------|----------|
| `bash` | 执行Shell命令 | 是 |
| `read` | 读取文件 | 是 |
| `write` | 写入文件 | 是 |
| `edit` | 精确替换 | 是 |
| `glob` | 文件搜索 | 否 |
| `grep` | 文本搜索 | 否 |
| `mkdir` | 创建目录 | 是 |
| `ls` | 列出目录 | 是 |
| `tree` | 树形结构 | 是 |
| `remove` | 删除文件 | 是 |

**沙盒管理**:

```python
class SandboxManager:
    def add_path(path: str) -> bool      # 添加允许路径
    def remove_path(path: str) -> bool    # 移除路径
    def is_path_allowed(path: str) -> bool  # 检查权限
    def enable()/disable()                # 启用/禁用
```

**命令权限**:

- 白名单命令: `ls`, `pwd`, `date`, `git status`, `git diff`
- 黑名单命令: `rm`, `dd`, `curl`, `wget`, `python`, `sudo`, ...

---

### 3.8 vtubestudio/__init__.py - VTube Studio集成

**文件**: `app/vtubestudio/__init__.py` (481行)

```python
class VtubeStudioAPI:
    """HTTP API控制"""
    def connect()/disconnect()
    def get_current_model()
    def load_model(model_id/name)
    def set_expression(name, intensity)
    def trigger_motion(name)
    def press_hotkey(hotkey_id)
    def get_tracking_status()

class VirtualAudioCable:
    """虚拟音频线管理"""
    def is_available() -> bool
    def list_devices() -> list

class LipSyncController:
    """口型同步控制器"""
    def start()/stop()
    def sync_with_audio(volume)
```

---

### 3.9 trainer/manager.py - LoRA训练管理

**文件**: `app/trainer/manager.py` (2,554行)

**训练Pipeline**:

```
1. 创建项目
   └── create_project(name)
       └── 创建目录结构

2. 上传音频
   └── save_audio(name, filename, data)
       └── 保存到 raw/

3. 预处理音频
   └── preprocess_audio(name)
       └── 转换为32kHz单声道
       └── 保存到 32k/

4. ASR识别
   └── recognize_audio_text(name, filename)
       └── 生成 texts.json

5. 特征提取
   └── extract_features(name)
       └── BERT特征 → 3-bert/
       └── HuBERT特征 → 4-cnhubert/
       └── 归一化音频 → 5-wav32k/

6. S1训练（GPT）
   └── start_training(name, s1_config)
       └── 生成 .ckpt
       └── 保存到 ckpt/

7. S2训练（SoVITS）
   └── start_training(name, s2_config)
       └── 生成 .pth
       └── 保存到 s2_ckpt/
```

**关键方法**:

```python
class TrainingManager:
    def create_project(name) -> dict
    def save_audio(name, filename, data) -> dict
    def save_text(name, audio_filename, text) -> dict
    def recognize_audio_text(name, filename) -> dict
    def preprocess_audio(name) -> dict
    def extract_features(name) -> dict
    def start_training(name, s1_config, s2_config)
    def switch_checkpoint(name, checkpoint_name) -> dict
    def reset_project(name, delete_all=False) -> dict
    def delete_audio(name, filename) -> dict
```

---

## 4. 模块依赖关系

```
main.py (AIVTuber)
│
├── llm/__init__.py (LLMFactory)
│   └── prompts.py
│   └── memory/__init__.py (MemoryRAGInjector)
│
├── tts/__init__.py (TTSFactory)
│   ├── tts/gptsovits.py (GPTSoVITSEngine)
│   │   └── asr/__init__.py (ASR - 参考音频识别)
│   ├── EdgeTTS
│
├── asr/__init__.py (ASRFactory)
│   ├── FunASRASR
│   └── FasterWhisperASR
│
├── memory/__init__.py (MemorySystem)
│   └── VectorStore (sentence_transformers)
│   └── FileStorage
│
├── web/__init__.py (WebServer + WebSocketServer)
│   ├── trainer/manager.py (TrainingManager)
│   └── subagent.py (SubAgent)
│
├── subagent.py (SubAgent)
│   └── SandboxManager
│
├── vision/__init__.py (VisionSystem)
│   ├── ScreenCapture (mss)
│   ├── OCREngine (rapidocr)
│   └── VisionModel (MiniMax/OpenAI)
│
└── vtubestudio/__init__.py (VtubeStudioController)
    └── VtubeStudioAPI
    └── LipSyncController
```

---

## 5. 数据流向

### 5.1 实时语音对话流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        实时语音对话 Pipeline                       │
└─────────────────────────────────────────────────────────────────┘

1. 前端录音
   └─ Web Audio API → MediaRecorder → base64音频数据

2. WebSocket发送
   └─ {"type": "realtime_audio", "data": "base64..."}

3. WebSocketServer接收
   └─ _handle_realtime_audio()

4. ASR识别
   └─ ASRFactory.create() → recognize(audio_path)
   └─ FunASR / Faster-Whisper → 文本

5. LLM对话
   └─ LLMFactory.create() → chat(message, history)
   └─ MiniMax-M2.5 → 流式响应

6. TTS合成（实时）
   └─ on_chunk回调 → 分句 → speak_streaming()
   └─ GPT-SoVITS → 流式WAV chunks

7. WebSocket发送音频
   └─ {"type": "audio_chunk", "audio": "base64..."}

8. 前端播放
   └─ Web Audio API → decodeAudioData → AudioBuffer → 播放

9. 记忆更新
   └─ memory.add_interaction("user", text)
   └─ memory.add_interaction("assistant", reply)
```

### 5.2 文本对话流程

```
用户输入 → WebSocket → text_worker
    ↓
LLM.chat() + MemoryRAGInjector.inject()
    ↓
记忆检索 → memory.search(query)
    ↓
LLM响应 → TTS合成 → speak()
    ↓
音频URL → WebSocket → {"type": "tts_done", "audio": "/audio/xxx.wav"}
```

---

## 6. 接口定义

### 6.1 LLM接口

```python
class LLMEngine(ABC):
    @property
    def name(self) -> str

    @abstractmethod
    def chat(self, message: str, history: List[Dict], memory_system=None) -> Dict:
        """
        返回: {"text": str, "action": dict, ...}
        """
        pass

    @abstractmethod
    def stream_chat(self, message: str, callback, history: List[Dict], memory_system=None):
        """
        流式对话，callback(chunk_text)
        """
        pass

    @abstractmethod
    def is_available(self) -> bool
```

### 6.2 TTS接口

```python
class TTSEngine(ABC):
    @abstractmethod
    def speak(self, text: str, output_path: str = None) -> Optional[str]:
        """
        语音合成，返回音频文件路径
        """
        pass

    @abstractmethod
    def is_available(self) -> bool

    def stop(self):
        """停止当前播放"""

    def get_voices(self) -> list:
        """获取可用音色列表"""
```

### 6.3 ASR接口

```python
class ASREngine(ABC):
    @abstractmethod
    def recognize(self, audio_path: str) -> Optional[str]:
        """语音识别，返回文本"""
        pass

    @abstractmethod
    def is_available(self) -> bool
```

### 6.4 记忆系统接口

```python
class MemorySystem:
    def add_interaction(self, role: str, content: str, importance: int = None)

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        返回: [{"layer": str, "text": str, "score": float, ...}]
        """

    def get_working_memory(self) -> List[Dict]

    def summarize(self) -> str

    def get_stats(self) -> Dict

    def export(self) -> str

    def clear_all(self)
```

---

## 7. 配置文件说明

**文件**: `app/config.yaml`

```yaml
# 语音识别
asr:
  provider: "funasr"           # faster_whisper / funasr / whisper
  faster_whisper:
    model_size: "small"
    device: "auto"
  funasr:
    model: "paraformer-zh"
    device: "cuda"

# 语音合成
tts:
  provider: "gptsovits"        # gptsovits / edge
  gptsovits:
    device: "cuda"
    is_half: true
    version: "v3"
    lang_code: "zh"
  fallback_engines: ["edge"]

# 大语言模型
llm:
  provider: "minimax"
  max_tokens: 2048
  enable_rag_injection: true
  minimax:
    api_key: "${MINIMAX_API_KEY}"
    base_url: "https://api.minimaxi.com/anthropic"
    model: "MiniMax-M2.7"

# VAD配置
vad:
  thinking_pause_ms: 600      # 思考停顿容忍
  stop_threshold_ms: 1800    # 说完判定时间
  thinking_threshold_factor: 0.8
  thinking_extend_ms: 2000

# 记忆系统
memory:
  provider: "simple"
  working_memory_limit: 20
  summarize_threshold: 15
  summarize_batch: 5
  forgetting_threshold: 0.3
  decay_lambda: 0.01

# 子Agent
subagent:
  enabled: true
  sandbox_paths: []

# Web服务
web:
  port: 12393
  ws_port: 12394
```

---

## 附录

### A. 版本历史

| 版本 | 日期 | 主要更新 |
|------|------|----------|
| v1.6.0 | 2026-04-19 | TTS分句优化 + Bug修复 |
| v1.5.0 | 2026-04-19 | LLM模块重构 |
| v1.4.76 | 2026-04-18 | 实时语音优化 |
| v1.4.70 | 2026-04-18 | TTS流式分句 |
| v1.4.64 | 2026-04-17 | 实时语音四大Bug修复 |

### B. 已知限制

1. **GPT-SoVITS v3/v4 LoRA版本检测**：ZIP文件格式导致版本误判
2. **FunASR CNHuBERT维度不匹配**：Fallback到Faster-Whisper
3. **记忆系统sentence-transformers**：需要网络下载模型

### C. 优化建议

1. **TTS预热**：已在WebServer启动时执行
2. **懒加载**：各模块首次访问时才加载
3. **流式输出**：LLM和TTS都支持流式
4. **并发控制**：请求队列 + cancel机制
