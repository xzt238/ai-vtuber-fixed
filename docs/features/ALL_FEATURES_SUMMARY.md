# 🐧 咕咕嘎嘎 AI VTuber - 完整功能清单

> **版本**: v1.15.6  
> **更新日期**: 2026-06-03  
> **整理人**: 齐活林（Qi）· 交付总监

---

## 📋 功能总览

| 类别 | 功能数量 | 状态 |
|------|----------|------|
| 🎤 语音识别 (ASR) | 3种引擎 | ✅ 已实现 |
| 🔊 语音合成 (TTS) | 6种引擎 | ✅ 已实现 |
| 🧠 大语言模型 (LLM) | 12个供应商 | ✅ 已实现 |
| 👁️ 视觉理解 | 4种模式 | ✅ 已实现 |
| 🎭 虚拟形象 | 2种模型 | ✅ 已实现 |
| 🧠 记忆系统 | 4层架构 | ✅ 已实现 |
| 📺 直播功能 | 1个平台 | ✅ 已实现 |
| 🎮 游戏集成 | 1个游戏 | ✅ 已实现 |
| 🤖 社交Bot | 2个平台 | ✅ 已实现 |
| 🎨 AI绘画 | 1种引擎 | ✅ 已实现 |
| 🎵 声音处理 | 2种功能 | ✅ 已实现 |
| 📚 知识库 | RAG系统 | ✅ 已实现 |
| 🎭 角色扮演 | 完整系统 | ✅ 已实现 |
| 💝 情感系统 | 完整系统 | ✅ 已实现 |
| 🔌 插件系统 | 完整框架 | ✅ 已实现 |

---

## 🎤 语音识别 (ASR)

### 支持的引擎

| 引擎 | 类型 | 特点 | 配置项 |
|------|------|------|--------|
| **FunASR** | 本地 | 中文优化，高精度 | `asr.provider: funasr` |
| **Faster Whisper** | 本地 | 多语言支持 | `asr.provider: faster_whisper` |
| **MiMo ASR** | API | 云端识别 | `asr.provider: mimo` |

### 配置示例
```yaml
asr:
  provider: funasr
  funasr:
    model: paraformer-zh
    device: cuda
  faster_whisper:
    model_size: small
    device: auto
  mimo:
    api_key: ''
    base_url: https://api.xiaomimimo.com/v1
    model: mimo-v2.5
```

---

## 🔊 语音合成 (TTS)

### 支持的引擎

| 引擎 | 类型 | 特点 | 配置项 |
|------|------|------|--------|
| **GPT-SoVITS** | 本地 | 声音克隆，高质量 | `tts.provider: gptsovits` |
| **Edge TTS** | 免费 | 微软语音，稳定 | `tts.provider: edge` |
| **MiMo TTS** | API | 云端合成 | `tts.provider: mimo` |
| **ElevenLabs** | API | 高质量英文 | `tts.provider: elevenlabs` |
| **Fish-Speech** | 本地 | 开源方案 | `tts.provider: fish_speech` |

### 配置示例
```yaml
tts:
  provider: gptsovits
  gptsovits:
    root_dir: ./GPT-SoVITS
    device: cuda
    is_half: true
    version: v3
  edge:
    voice: zh-CN-XiaoxiaoNeural
    rate: +0%
    pitch: +0Hz
    volume: +0%
  mimo:
    api_key: ''
    base_url: https://api.xiaomimimo.com/v1
    model: mimo-v2.5-tts
    voice: mimo_default
  elevenlabs:
    api_key: ''
    voice_id: 21m00Tcm4TlvDq8ikWAM
    model_id: eleven_monolingual_v1
  fish_speech:
    api_key: ''
    model_id: fish-speech-1.5
    voice_id: default
```

---

## 🧠 大语言模型 (LLM)

### 支持的供应商

| 供应商 | 模型 | 特点 | 配置项 |
|--------|------|------|--------|
| **OpenAI** | gpt-4o-mini | 国际领先 | `llm.provider: openai` |
| **DeepSeek** | deepseek-chat | 中文优化 | `llm.provider: deepseek` |
| **通义千问** | qwen3.6-plus | 阿里云 | `llm.provider: qwen` |
| **智谱GLM** | GLM-4.7-FlashX | 国产领先 | `llm.provider: glm` |
| **Kimi** | kimi-k2.6 | 长上下文 | `llm.provider: kimi` |
| **MiniMax** | MiniMax-M2.7 | 多模态 | `llm.provider: minimax` |
| **MiMo** | mimo-v2.5 | 小米 | `llm.provider: mimo` |
| **豆包** | doubao-1.5-pro-32k | 字节跳动 | `llm.provider: doubao` |
| **Anthropic** | claude-sonnet-4-5 | 安全 | `llm.provider: anthropic` |
| **Ollama** | qwen3:8b | 本地部署 | `llm.provider: ollama` |

### 配置示例
```yaml
llm:
  provider: ollama
  ollama:
    base_url: http://localhost:11434/v1
    model: qwen3:8b
    api_key: ollama
  openai:
    api_key: ''
    base_url: https://api.openai.com/v1
    model: gpt-4o-mini
  deepseek:
    api_key: ''
    base_url: https://api.deepseek.com
    model: deepseek-chat
  qwen:
    api_key: ''
    base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
    model: qwen3.6-plus
```

---

## 👁️ 视觉理解

### 支持的模式

| 模式 | 功能 | 特点 | 配置项 |
|------|------|------|--------|
| **MiMo Vision** | 图像识别 | 小米视觉 | `vision.default_provider: mimo_vision` |
| **MiniMax VL** | 图像识别 | 多模态 | `vision.default_provider: minimax_vl` |
| **MiniCPM** | 本地视觉 | 本地部署 | `vision.default_provider: minicpm` |
| **RapidOCR** | 文字识别 | OCR功能 | `vision.rapidocr.enabled: true` |

### 配置示例
```yaml
vision:
  default_provider: minimax_vl
  minimax_vl:
    api_host: https://api.minimaxi.com
    api_key: ''
    model: MiniMax-VL-01
  mimo_vision:
    api_key: ''
    base_url: https://api.xiaomimimo.com/v1
    model: mimo-v2.5
  minicpm:
    model_id: OpenBMB/MiniCPM-V-2
    model_path: ''
  rapidocr:
    enabled: true
```

---

## 🎭 虚拟形象

### 支持的模型

| 模型 | 类型 | 特点 | 配置项 |
|------|------|------|--------|
| **Live2D** | 2D动画 | 轻量，流畅 | `live2d.enabled: true` |
| **VRM** | 3D模型 | 立体，真实 | 通过VRM设置页面配置 |

### Live2D配置
```yaml
live2d:
  enabled: true
  model_path: ./app/web/assets/model/shizuku
  idle_motion: Idle
```

### VRM配置
```yaml
vrm_display:
  model_scale: 1.0
  model_x: 0.0
  model_y: 0.0
  camera_distance: 3.0
  light_intensity: 2.5
  ambient_light: 0.8
  fill_light: 0.4
  anim_speed: 1.0
  anim_amplitude: 1.0
  breath_amp: 0.01
```

---

## 🧠 记忆系统

### 四层架构

| 层级 | 名称 | 功能 | 容量 |
|------|------|------|------|
| **第1层** | 工作记忆 | 当前对话上下文 | 30条 |
| **第2层** | 情景记忆 | 对话摘要 | 动态 |
| **第3层** | 语义记忆 | 向量检索 | 动态 |
| **第4层** | 事实库 | 持久知识 | 动态 |

### 配置示例
```yaml
memory:
  working_memory_limit: 30
  summarize_threshold: 20
  summarize_batch: 5
  forgetting_threshold: 0.15
  decay_lambda: 0.005
  grace_period_hours: 12.0
  dedup_threshold: 0.95
  auto_store: true
  embedding_model: BAAI/bge-base-zh-v1.5
  embedding_device: cpu
  retrieval_weights:
    vector: 0.5
    keyword: 0.3
    recency: 0.2
```

---

## 📺 直播功能

### 支持的平台

| 平台 | 功能 | 状态 | 配置项 |
|------|------|------|--------|
| **Bilibili** | 弹幕互动 | ✅ 已实现 | `live.bilibili` |

### 配置示例
```yaml
live:
  enabled: false
  bilibili:
    room_id: ''
    uid: 0
    token: ''
```

---

## 🎮 游戏集成

### 支持的游戏

| 游戏 | 功能 | 状态 | 配置项 |
|------|------|------|--------|
| **Minecraft** | 游戏感知 | ✅ 已实现 | `game.minecraft` |

### 配置示例
```yaml
game:
  enabled: false
  storage_dir: ./cache/game
  minecraft:
    host: localhost
    port: 25565
    username: AI_VTuber
    password: ''
```

---

## 🤖 社交Bot

### 支持的平台

| 平台 | 功能 | 状态 | 配置项 |
|------|------|------|--------|
| **Discord** | 服务器Bot | ✅ 已实现 | `bot.discord` |
| **Telegram** | 聊天Bot | ✅ 已实现 | `bot.telegram` |

### 配置示例
```yaml
bot:
  enabled: false
  storage_dir: ./cache/bot
  discord:
    token: ''
    guild_id: ''
    channel_id: ''
    command_prefix: '!'
  telegram:
    token: ''
    chat_id: ''
    parse_mode: HTML
```

---

## 🎨 AI绘画

### 支持的引擎

| 引擎 | 功能 | 状态 | 配置项 |
|------|------|------|--------|
| **Stable Diffusion** | 文生图 | ✅ 已实现 | `sd` |

### 配置示例
```yaml
sd:
  enabled: false
  api_url: http://127.0.0.1:7860
  model: ''
  sampler: Euler a
  steps: 20
  cfg_scale: 7.0
  width: 512
  height: 512
  seed: -1
```

---

## 🎵 声音处理

### 支持的功能

| 功能 | 说明 | 状态 | 配置项 |
|------|------|------|--------|
| **SVC** | 声音转换 | ✅ 已实现 | `svc` |
| **Singing** | AI唱歌 | ✅ 已实现 | `singing` |

### SVC配置
```yaml
svc:
  enabled: false
  device: cuda
  half: true
  f0_method: crepe
  model_path: ''
  config_path: ''
```

### Singing配置
```yaml
singing:
  enabled: false
  device: cpu
  half: true
  f0_method: crepe
  model_path: ''
```

---

## 📚 知识库 (RAG)

### 功能说明

| 功能 | 说明 | 状态 |
|------|------|------|
| **文档导入** | 支持PDF/TXT/MD/DOCX | ✅ 已实现 |
| **文本分块** | 智能分块 | ✅ 已实现 |
| **向量存储** | 语义索引 | ✅ 已实现 |
| **检索增强** | RAG生成 | ✅ 已实现 |

### 配置示例
```yaml
rag:
  enabled: false
  chunk_size: 500
  chunk_overlap: 50
  top_k: 5
  similarity_threshold: 0.7
  storage_dir: ./memory/knowledge_base
  retrieval_weights:
    vector: 0.7
    keyword: 0.3
```

---

## 🎭 角色扮演

### 功能说明

| 功能 | 说明 | 状态 |
|------|------|------|
| **角色创建** | 自定义角色 | ✅ 已实现 |
| **角色管理** | CRUD操作 | ✅ 已实现 |
| **剧情系统** | 剧情创建 | ✅ 已实现 |
| **会话管理** | 角色扮演会话 | ✅ 已实现 |

### 配置示例
```yaml
roleplay:
  enabled: true
  storage_dir: ./memory/roleplay
  characters:
    storage_dir: ./memory/characters
    max_characters: 50
  stories:
    storage_dir: ./memory/stories
    max_stories: 100
  sessions:
    max_sessions: 10
    timeout: 3600
```

---

## 💝 情感系统

### 功能说明

| 功能 | 说明 | 状态 |
|------|------|------|
| **情感识别** | 文本/语音/面部 | ✅ 已实现 |
| **情感表达** | 回复生成 | ✅ 已实现 |
| **情感记忆** | 历史记录 | ✅ 已实现 |
| **情感趋势** | 趋势分析 | ✅ 已实现 |

### 配置示例
```yaml
emotion:
  enabled: true
  storage_dir: ./memory/emotion
  analysis:
    text_enabled: true
    voice_enabled: true
    face_enabled: false
  expression:
    response_templates: true
    emoji_enabled: true
  memory:
    max_history: 100
    trend_window: 10
```

---

## 🔌 插件系统

### 功能说明

| 功能 | 说明 | 状态 |
|------|------|------|
| **插件发现** | 自动扫描 | ✅ 已实现 |
| **插件加载** | 动态加载 | ✅ 已实现 |
| **插件管理** | 启用/禁用 | ✅ 已实现 |
| **插件执行** | 运行插件 | ✅ 已实现 |

### 配置示例
```yaml
plugin:
  enabled: true
  plugins_dir: ./plugins
  auto_load: true
  max_plugins: 50
```

---

## 🎯 其他功能

### 主动说话
```yaml
proactive_speech:
  enabled: true
  idle_timeout: 120
  min_interval: 300
  max_daily_count: 15
  check_interval: 30
  randomize_range: 30
  max_concurrent: 3
```

### 每日日记
```yaml
diary:
  enabled: true
  time: '23:00'
  max_context_items: 30
```

### 桌面宠物
```yaml
desktop_pet:
  enabled: false
  width: 400
  height: 500
  transparent: true
  always_on_top: true
  draggable: true
  click_action: greet
```

### MCP工具桥接
```yaml
mcp:
  enabled: true
  servers: {}
```

### 多AI群聊
```yaml
multi_agent:
  enabled: false
  max_agents: 10
  conversation_timeout: 3600
```

### 摄像头视觉输入
```yaml
vision_input:
  enabled: false
  storage_dir: ./cache/vision
  camera:
    device_id: 0
    width: 640
    height: 480
    fps: 30
```

---

## 📊 功能统计

### 核心功能
- **语音识别**: 3种引擎
- **语音合成**: 6种引擎
- **大语言模型**: 12个供应商
- **视觉理解**: 4种模式
- **虚拟形象**: 2种模型

### 扩展功能
- **记忆系统**: 4层架构
- **直播功能**: 1个平台
- **游戏集成**: 1个游戏
- **社交Bot**: 2个平台
- **AI绘画**: 1种引擎
- **声音处理**: 2种功能
- **知识库**: RAG系统
- **角色扮演**: 完整系统
- **情感系统**: 完整系统
- **插件系统**: 完整框架

### 总计
- **核心功能模块**: 15个
- **扩展功能模块**: 10个
- **配置参数**: 200+个
- **支持平台**: 20+个

---

## 🏆 总结

咕咕嘎嘎 AI VTuber 是一个功能极其丰富的 AI 虚拟形象系统，具备：

1. **完整的语音交互能力** - 支持多种ASR和TTS引擎
2. **强大的LLM支持** - 支持12个LLM供应商
3. **先进的视觉理解** - 支持多种视觉模型
4. **灵活的虚拟形象** - 支持Live2D和VRM
5. **智能记忆系统** - 四层记忆架构
6. **丰富的扩展功能** - 直播、游戏、社交Bot等
7. **完善的插件系统** - 支持第三方扩展

---

**文档版本**: v1.15.6  
**更新日期**: 2026-06-03  
**整理人**: 齐活林（Qi）· 交付总监