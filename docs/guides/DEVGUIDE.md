# 🛠️ 咕咕嘎嘎 AI-VTuber 开发者指南

> **版本**: v1.0 | **适用项目版本**: v1.9.90+ | **日期**: 2026-05-07

---

## 目录

1. [项目概览](#1-项目概览)
2. [技术栈与依赖](#2-技术栈与依赖)
3. [项目结构](#3-项目结构)
4. [三种启动模式](#4-三种启动模式)
5. [核心架构](#5-核心架构)
6. [模块详解](#6-模块详解)
7. [开发环境搭建](#7-开发环境搭建)
8. [代码规范与约定](#8-代码规范与约定)
9. [调试指南](#9-调试指南)
10. [常见开发任务](#10-常见开发任务)
11. [版本管理与发布流程](#11-版本管理与发布流程)
12. [已知问题与改进方向](#12-已知问题与改进方向)
13. [给 AI 助手的修改指南](#13-给-ai-助手的修改指南)

---

## 1. 项目概览

**咕咕嘎嘎 (GuguGaga)** 是一个功能丰富的 AI 虚拟形象系统，当前版本 v1.9.90。

核心能力：
- **实时语音对话** — ASR 语音识别 → LLM 推理 → TTS 语音合成
- **文字聊天** — 多 LLM 后端支持（10 个 Provider）
- **Function Calling** — 统一工具调用执行器（fc_executor），OpenAI/MiniMax 已激活
- **7 个伴侣工具** — GetTime、GetWeather、SetReminder、RememberThing、ChangeExpression、SearchWeb、PlayMusic
- **TTS 文本增强** — text_enhancer 自动处理 ChatTTS 标记、中文特性和情感扩散
- **ChatTTS / CosyVoice** — 新增 TTS 引擎，扩展语音合成选项
- **声音克隆训练** — 内置 GPT-SoVITS v3 训练面板
- **Live2D 虚拟形象** — 浏览器 WebGL / 原生 OpenGL 渲染
- **四层记忆系统** — 工作记忆 + 情景记忆 + 语义记忆 + 事实记忆
- **视觉理解** — OCR + 图片理解 + 屏幕感知
- **三种运行模式** — 浏览器 WebUI / 桌面 pywebview / 原生 PySide6
- **版本号集中管理** — version.py 单一来源，所有代码统一导入
- **共享配置单源模式** — shared_config.py 集中管理 Provider 配置、语音列表、表情关键词、互斥名

**项目基本信息**：

| 项目 | 值 |
|------|-----|
| 语言 | Python 3.11 |
| 许可证 | GPL-3.0 |
| 操作系统 | Windows 10/11 |
| 仓库 | `https://github.com/xzt238/ai-vtuber-fixed` |
| 本地路径 | `C:\Users\x\Desktop\ai-vtuber-fixed` |

---

## 2. 技术栈与依赖

### 核心技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| **运行时** | Python 3.11 (嵌入式发行版) | 项目自带 python/ 目录，无需用户安装 |
| **后端框架** | aiohttp | HTTP + WebSocket 异步服务 |
| **Web 前端** | 单文件 HTML/CSS/JS (11,374 行) | 内联式，无构建工具 |
| **Web 前端库** | pixi.js, oh-my-live2d, Silero VAD (WASM), ONNX Runtime | Live2D + 语音活动检测 |
| **桌面模式** | pywebview (WebView2) + pystray | 原生窗口壳 + 系统托盘 |
| **原生桌面** | PySide6 6.x + PySide6-Fluent-Widgets | Qt6 + Windows 11 Fluent Design |
| **Live2D 原生** | live2d-py 0.6.x | QOpenGLWidget + OpenGL 渲染 |
| **ASR** | FunASR (Paraformer) / faster-whisper (CTranslate2) | 语音识别 |
| **TTS** | GPT-SoVITS v3 (本地 GPU) / Edge TTS (在线备用) / ChatTTS / CosyVoice | 语音合成 |
| **LLM** | MiniMax / OpenAI / Anthropic + 7 个 OpenAI 兼容 Provider | 大语言模型 |
| **视觉** | MiniMax VL API / MiniCPM-V2 / RapidOCR | 图片理解 + OCR |
| **记忆** | sentence-transformers (BAAI/bge-base-zh-v1.5) | 向量嵌入 |
| **ML** | PyTorch 2.6.0+cu124, transformers, peft, accelerate | 机器学习框架 |
| **打包** | PyInstaller | 单 EXE 启动器 |
| **安装器** | NSIS / Inno Setup | 安装向导 |

### 关键 Python 包

**核心依赖** (`app/requirements.txt`)：
- pyyaml, requests, edge-tts, websocket-server, websockets
- numpy, pillow, soundfile, jieba, pypinyin, cn2an, opencc
- aiohttp, pyaudio, sounddevice

**ML 依赖**：
- torch, torchaudio, transformers (<4.45), peft, accelerate
- pytorch-lightning, bitsandbytes, rotary-embedding-torch
- faster-whisper, funasr, rapidocr-onnxruntime

**原生桌面依赖** (`native/`)：
- PySide6, PySide6-Fluent-Widgets
- live2d-py
- pynput (全局快捷键)

**声音训练依赖** (`GPT-SoVITS/`)：
- librosa, scipy, gradio

---

## 3. 项目结构

```
ai-vtuber-fixed/
│
├── app/                          # 核心应用后端
│   ├── main.py                   # 主入口：AIVTuber + Config + ToolExecutor
│   ├── version.py                # 版本号单一来源（VERSION）
│   ├── shared_config.py          # 共享配置：Provider配置、语音列表、表情关键词、互斥名
│   ├── config.yaml               # 统一配置文件（245行）
│   ├── requirements.txt          # Python 依赖清单
│   ├── requirements-build.txt    # 打包专用依赖
│   │
│   ├── asr/__init__.py           # ASR 语音识别（FunASR / FasterWhisper / OpenAI Whisper）
│   ├── tts/__init__.py           # TTS 语音合成（GPT-SoVITS / Edge TTS / ChatTTS / CosyVoice + 工厂降级）
│   ├── tts/gptsovits.py          # GPT-SoVITS TTS 引擎
│   ├── tts/chattts.py            # ChatTTS 引擎
│   ├── tts/cosyvoice.py          # CosyVoice 引擎
│   ├── tts/text_enhancer.py      # TTS 文本增强系统（ChatTTS 标记、中文特性、情感扩散）
│   ├── llm/__init__.py           # LLM 大语言模型（MiniMax / OpenAI / Anthropic + Function Calling）
│   ├── llm/prompts.py            # 系统提示词 & 人格设定
│   ├── memory/__init__.py        # v3.0 四层记忆系统
│   ├── vision/__init__.py        # 视觉理解（RapidOCR / MiniMax VL / MiniCPM）
│   ├── live2d/__init__.py        # Live2D 虚拟形象管理 + AnimationController
│   ├── voice/__init__.py         # 语音输入（本地 + Web）
│   ├── trainer/__init__.py       # 训练管理器接口
│   ├── trainer/manager.py        # GPT-SoVITS 训练编排
│   ├── tools/__init__.py         # 16 内置工具（9 代码工具 + 7 陪伴工具）
│   ├── tools/fc_executor.py      # Function Calling 执行器（统一工具调用循环）
│   ├── tools/companion.py        # 7 个伴侣工具（GetTime/GetWeather/SetReminder/RememberThing/ChangeExpression/SearchWeb/PlayMusic）
│   ├── ocr/__init__.py           # OCR 模块
│   ├── web/__init__.py           # HTTP + WebSocket 服务
│   ├── web/static/index.html     # 单文件前端（11,374 行！）
│   ├── web/static/assets/model/  # Live2D 模型（shizuku, hiyori）
│   ├── web/static/libs/          # 前端 JS 库
│   ├── mcp/__init__.py           # MCP (Model Context Protocol) 工具桥接
│   ├── desktop_pet/__init__.py   # 桌面宠物模式
│   ├── proactive.py              # AI 主动发言管理器
│   ├── tts_cache.py              # TTS 音频缓存管理器
│   ├── utils.py                  # 工具函数
│   ├── logger_new.py             # 日志模块
│   └── cache/                    # 运行时缓存
│       ├── llm_preferences.json  # LLM 配置持久化（自动生成）
│       ├── api_keys.json         # API 密钥（隐私，.gitignore 排除）
│       └── layout.json           # WebUI 布局缓存
│
├── native/                       # 原生桌面应用（PySide6/Qt6）★ 重点关注
│   ├── main.py                   # 原生桌面入口（~600行）
│   ├── build.bat                 # PyInstaller 构建脚本
│   ├── gugu_setup.iss            # Inno Setup 安装器脚本
│   │
│   └── gugu_native/              # 原生应用包（避免与 app/ 冲突）
│       ├── pages/                # UI 页面
│       │   ├── chat_page.py      # 对话页（含 Live2D）— 1739 行
│       │   ├── train_page.py     # 音色训练页 — 1040 行
│       │   ├── memory_page.py    # 记忆管理页 — 816 行
│       │   ├── settings_page.py  # 设置页（10个LLM Provider）— 1097 行
│       │   └── model_download_page.py  # 模型下载页 — 544 行
│       │
│       ├── widgets/              # 可复用组件
│       │   ├── live2d_widget.py  # Live2D OpenGL 渲染（259行）
│       │   ├── voice_manager.py  # 实时语音管理器（387行）
│       │   ├── tray_manager.py   # 系统托盘（163行）
│       │   ├── hotkey_manager.py # 全局快捷键（169行）
│       │   ├── desktop_pet.py    # 桌面宠物窗口（195行）
│       │   ├── autostart_manager.py  # 开机自启（111行）
│       │   ├── update_manager.py # 自动更新（213行）
│       │   ├── perf_manager.py   # 性能管理器（236行）
│       │   ├── dual_mode_compat.py  # 双模式兼容（159行）
│       │   ├── audio_visualizer.py  # 音频频谱可视化（331行）
│       │   ├── markdown_renderer.py  # Markdown 渲染组件
│       │   ├── chat_web_display.py   # 聊天 Web 展示组件
│       │   ├── multi_line_input.py   # 多行输入组件
│       │   ├── session_manager.py    # 会话管理组件
│       │   └── message_search.py     # 消息搜索组件
│       │
│       ├── theme.py              # 统一主题管理（574行）
│       └── resources/            # 图标、启动画面等资源
│
├── launcher/                     # 桌面启动器（pywebview）
│   ├── launcher.py               # 启动器主代码（~1034行）
│   ├── splash.html               # 启动画面
│   ├── launcher.spec             # PyInstaller 打包配置
│   └── dist/GuguGaga.exe        # 打包后的启动器
│
├── GPT-SoVITS/                   # GPT-SoVITS 声音克隆引擎
│   ├── GPT_SoVITS/               # 核心代码 + 预训练模型
│   ├── api.py                    # TTS API 接口
│   └── webui.py                  # 训练 WebUI
│
├── scripts/                      # 启动和安装脚本
│   ├── setup.bat                 # ★ 一键全安装（新用户首选）
│   ├── setup.py                  # 安装脚本（Python，779行）
│   ├── go.bat                    # 浏览器模式启动
│   ├── desktop.bat               # 桌面模式启动（pywebview）
│   ├── start.bat                 # 原生桌面启动（PySide6）
│   ├── install_deps.bat          # 依赖安装器
│   ├── download_models.bat       # 模型下载器
│   └── installer.nsi             # NSIS 安装器脚本
│
├── docs/                         # 文档
│   ├── README.md                 # 文档索引
│   ├── BUILD.md                  # 构建/打包指南
│   ├── VERSION.md                # 版本历史
│   ├── CHANGE_IMPACT_MAP.md      # 变更影响地图
│   ├── MODIFICATION_GUIDE.md     # 修改指南
│   ├── KNOWN_ISSUES.md           # 已知问题完整列表
│   ├── guides/                   # 指南文档
│   │   └── DEVGUIDE.md           # ★ 本文档 — 开发者指南
│   ├── NATIVE_DESKTOP.md         # ★ 原生桌面架构文档
│   ├── archive/                  # 归档文档
│   │   ├── feasibility_native_desktop.md    # 原生桌面可行性报告
│   │   └── feasibility_tool_system_upgrade.md  # 工具系统升级可行性报告
│   └── ...                       # 其他文档
│
├── assets/                       # 静态资源
│   ├── gugugaga_logo.png         # Logo（256x256）
│   └── gugugaga_logo.ico         # 多尺寸图标
│
├── python/                       # 嵌入式 Python 3.11（~3GB，.gitignore）
├── models/                       # 本地模型文件（.gitignore）
├── memory/                       # 记忆数据（.gitignore）
├── cache/                        # 运行时缓存（.gitignore）
├── logs/                         # 日志文件（.gitignore）
├── .cache/                       # HuggingFace 模型缓存（.gitignore）
│
├── GuguGaga.exe                  # 预构建桌面启动器
├── .env.example                  # 环境变量模板
├── .gitignore                    # Git 忽略规则
├── LICENSE                       # GPL-3.0
├── README.md                     # 项目主文档
└── README_DEV_GUIDE.txt          # 旧版开发者指南（将被本文档替代）
```

### Git 不追踪的文件

以下文件/目录通过脚本下载或运行时生成，不在 Git 仓库中：

| 路径 | 说明 | 大小 |
|------|------|------|
| `python/` | 嵌入式 Python 环境 | ~3GB |
| `GPT-SoVITS/GPT_SoVITS/pretrained_models/` | GPT-SoVITS 预训练底模 | ~2.5GB |
| `models/` | ASR 模型 | ~990MB |
| `.cache/` | HuggingFace 模型缓存 | 不定 |
| `app/cache/api_keys.json` | API 密钥（隐私） | 小 |
| `GPT-SoVITS/GPT_SoVITS/memory/` | 聊天记忆（隐私） | 不定 |

---

## 4. 三种启动模式

### 模式 1：浏览器 / WebUI 模式

**入口脚本**：`scripts/go.bat`

**启动命令**：`python -m app.main`

**架构**：
```
go.bat → app/main.py:main() → AIVTuber.run_web(desktop_mode=False)
    → HTTP Server (:12393) + WebSocket Server (:12394)
    → 后台预加载 LLM/TTS/ASR
    → 用户浏览器访问 http://localhost:12393
```

**特点**：
- 单文件前端 `app/web/static/index.html`（11,374 行）
- 使用浏览器开发者工具调试方便
- 无系统托盘、无启动画面
- 26 个浮动面板，331 个交互控件

### 模式 2：桌面模式（pywebview）

**入口脚本**：`scripts/desktop.bat`

**启动命令**：`python launcher/launcher.py`

**架构**：
```
desktop.bat → launcher/launcher.py
    → BackendManager.start() 启动子进程 (python -m app.main --desktop)
    → pywebview 窗口显示 splash.html 启动画面
    → 健康检查轮询 localhost:12393
    → 后端就绪后切换到 WebUI
    → 系统托盘 (pystray) + 单实例锁 (Windows Mutex)
```

**特点**：
- 原生窗口壳，内容仍是网页
- 有启动画面动画（Logo 旋转 + 进度条）
- 有系统托盘（最小化/退出）
- 单实例互斥锁（命名 Mutex）
- 崩溃循环检测 + DLL 解锁

### 模式 3：原生桌面模式（PySide6）★ 重点关注

**入口脚本**：`scripts/start.bat`

**启动命令**：`python native/main.py`

**架构**：
```
start.bat → native/main.py:main()
    → QApplication → GuguGagaApp(FluentWindow)
    → 延迟 2 秒初始化后端 (from app.main import AIVTuber)
    → 直接 Python 调用后端（无 HTTP/WS 通信层！）
    → 页面：对话 / 音色训练 / 记忆 / 模型下载 / 设置
```

**特点**：
- **真正原生体验**：系统原生窗口、菜单栏、托盘、通知
- **零通信开销**：Python 直接调用 `AIVTuber` 实例，无需 HTTP/WS 序列化
- **Live2D 原生渲染**：`live2d-py` + `QOpenGLWidget` 直接 OpenGL 渲染
- **Windows 11 Fluent Design**：PyQt-Fluent-Widgets 组件库
- **桌面宠物**：无边框透明窗口 + Live2D
- **全局快捷键**：Ctrl+Alt+R/H/P/S
- **开机自启**：Windows 注册表
- **自动更新**：GitHub Releases API

**三种模式对比**：

| 特性 | WebUI | pywebview 桌面 | 原生桌面 |
|------|-------|---------------|---------|
| 原生窗口 | ❌ | ✅ (WebView2壳) | ✅ (Qt6原生) |
| 系统托盘 | ❌ | ✅ | ✅ |
| 启动画面 | ❌ | ✅ | ✅ |
| Live2D 渲染 | WebGL | WebGL | OpenGL |
| 通信方式 | HTTP/WS | HTTP/WS | Python 直调 |
| 桌面宠物 | ❌ | ❌ | ✅ |
| 全局快捷键 | ❌ | ❌ | ✅ |
| 开机自启 | ❌ | ❌ | ✅ |
| 自动更新 | ❌ | ❌ | ✅ |
| 调试便利性 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| 性能 | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |

---

## 5. 核心架构

### 5.1 AIVTuber 主类（懒加载架构）

`app/main.py` 中的 `AIVTuber` 是整个后端的核心门面类，采用**懒加载属性**设计：

```python
class AIVTuber:
    def __init__(self):
        # 只创建轻量对象
        self.config = Config()
        self.tts_cache = TTSCache()
        self.logger = ...
        self.history = []

    @property
    def asr(self):    # 首次访问时才加载 FunASR/FasterWhisper
    @property
    def tts(self):    # 首次访问时才加载 GPT-SoVITS/EdgeTTS/ChatTTS/CosyVoice
    @property
    def llm(self):    # 首次访问时才加载 LLM 引擎
    @property
    def memory(self): # 首次访问时才加载记忆系统
    @property
    def vision(self): # 首次访问时才加载视觉模块
    # ... 更多懒加载属性
```

**关键方法**：

| 方法 | 说明 |
|------|------|
| `process_message(text)` | 文本消息处理：记忆检索 → LLM 推理 → 工具执行 → 记录交互 |
| `process_audio(audio_path)` | 音频处理：ASR → process_message → TTS |
| `speak(text)` | TTS 语音合成（带缓存 + 中断机制） |
| `run_web()` | 启动 Web 服务（HTTP + WS）+ 后台预加载 |
| `run_interactive()` | 交互式命令行模式 |

**消息处理流程**：
```
用户消息 → process_message()
    ├── 记忆检索 (memory.retrieve)
    ├── 提示词注入 (PromptInjector)
    ├── LLM 推理 (llm.chat, 流式)
    ├── 工具调用检测 (_handle_local_tool / ToolExecutor / fc_executor)
    ├── 记忆存储 (memory.store)
    └── 返回结果 {text, action, audio}
```

### 5.2 Config 配置系统

`app/main.py` 中的 `Config` 类：

- 加载 `app/config.yaml`
- 支持 `${VAR}` 环境变量展开
- 合并 `app/cache/api_keys.json`（API 密钥）
- 合并 `app/cache/llm_preferences.json`（LLM 配置持久化）
- 支持点号访问：`config.get("llm.minimax.model")`

**配置优先级**（高 → 低）：
1. `app/cache/llm_preferences.json` — 用户 WebUI/原生界面操作自动保存
2. `app/cache/api_keys.json` — API 密钥
3. `app/config.yaml` — 基础配置
4. 环境变量 `${VAR}` 展开

### 5.3 工厂模式

所有模块统一使用工厂模式，方便扩展新 Provider：

| 工厂 | 文件 | 可选实现 |
|------|------|---------|
| `ASRFactory` | `app/asr/__init__.py` | FunASR, FasterWhisper, OpenAI Whisper |
| `TTSFactory` | `app/tts/__init__.py` | GPT-SoVITS, Edge TTS, ChatTTS, CosyVoice |
| `LLMFactory` | `app/llm/__init__.py` | MiniMax, OpenAI (+ 7个兼容), Anthropic |
| `ToolFactory` | `app/tools/__init__.py` | Read, Write, Edit, Glob, Grep, LS, Bash, Think, Architect |

**添加新 Provider 的步骤**：
1. 创建新的实现类，继承对应基类
2. 在工厂中注册
3. 在 `config.yaml` 中添加配置段
4. 在原生桌面 Settings 页面添加对应 UI

### 5.4 TTS 缓存与中断

`app/tts_cache.py` + `app/tts/__init__.py`：

- **MD5 文本哈希缓存**：相同文本直接返回缓存音频文件
- **全局中断机制**：`_is_playing` 类级变量，新 TTS 请求自动中断当前播放
- **自动降级**：GPT-SoVITS 失败 → Edge TTS 备用
- **限速清理**：避免缓存目录无限增长

### 5.5 WebSocket 协议

`app/web/__init__.py` 定义了完整的 WS 消息协议：

- **入站消息类型**：31 种（text, audio, tool, config, mcp, ...）
- **出站消息类型**：43+ 种（ai_response, audio, tool_call_start/end, ...）
- **实时语音管线**（方案 C）：VAD → ASR → LLM 流式 → 逐句 TTS → 音频推送

### 5.6 version.py 集中管理模式

`app/version.py` 是版本号的**单一来源（Single Source of Truth）**：

```python
# app/version.py
VERSION = "v1.9.90"
```

**原则**：
- 所有代码（Python 后端、原生桌面、启动脚本）通过 `from app.version import VERSION` 获取版本号
- **禁止硬编码版本号**：不在 `main.py`、`native/main.py` 等文件中重复写版本号
- 修改版本号只需改 `app/version.py` 一处

### 5.7 shared_config.py 单源模式

`app/shared_config.py` 集中管理多个跨模块共享的常量和配置：

| 常量 | 说明 |
|------|------|
| `PROVIDER_CONFIG` | LLM Provider 配置映射 |
| `EDGE_VOICES` | Edge TTS 可用语音列表 |
| `EXPRESSION_KEYWORDS` | 表情触发关键词 |
| `EXPRESSION_MAP` | 关键词到表情的映射 |
| `MUTEX` | Windows 命名互斥体名称 |

**原则**：
- 跨模块共享的配置常量集中在此文件
- 避免在多个文件中重复定义相同的常量
- 修改共享配置只需改 `shared_config.py` 一处

### 5.8 JS 同步注意事项

`app/web/static/index.html` 是纯前端文件，**无法直接 import Python 模块**。因此：

- `version.py` 和 `shared_config.py` 中的值需要**手动同步**到 `index.html` 的 JavaScript 中
- 修改版本号或共享配置时，务必检查 `index.html` 中是否有对应的 JS 常量需要同步更新
- 建议在修改后搜索 `index.html` 中的版本号字符串确认一致性

---

## 6. 模块详解

### 6.1 ASR 语音识别 (`app/asr/__init__.py`)

**架构**：抽象基类 + 3 个实现 + 工厂 + 管理器

| 引擎 | 特点 | 依赖 |
|------|------|------|
| FunASRASR | Paraformer 模型，中文效果好 | funasr, modelscope |
| FasterWhisperASR | CTranslate2 加速，多语言 | faster-whisper |
| WhisperASR | OpenAI API，需联网 | openai |

**特性**：
- 模型预热（静音音频触发懒加载）
- 自动降级（主引擎失败切换备用）
- 批量处理支持

### 6.2 TTS 语音合成 (`app/tts/__init__.py` + `app/tts/gptsovits.py`)

| 引擎 | 特点 | 适用 |
|------|------|------|
| GPT-SoVITS | 本地 GPU 推理，声音克隆 | 有 NVIDIA GPU |
| Edge TTS | 在线免费，无需配置 | 无 GPU / 备用 |
| ChatTTS | 本地推理，自然韵律 | 有 GPU，追求自然度 |
| CosyVoice | 本地推理，多风格 | 有 GPU，多语言 |

**特性**：
- 工厂模式 + 自动降级
- 全局中断机制（`_is_playing`）
- MD5 文本哈希缓存
- 限速文件清理
- 指数退避重试

### 6.3 LLM 大语言模型 (`app/llm/__init__.py`)

**架构**：抽象基类 + 3 个引擎类 + 工厂

**10 个 Provider 配置**：

| Provider | 底层引擎 | 特殊处理 |
|----------|---------|---------|
| minimax | MiniMaxLLM | 双格式支持（OpenAI/Anthropic），Function Calling 已激活 |
| anthropic | AnthropicLLM | Claude 原生格式 |
| deepseek | OpenAILLM | OpenAI 兼容 |
| kimi | OpenAILLM | OpenAI 兼容 |
| glm | OpenAILLM | OpenAI 兼容 |
| qwen | OpenAILLM | Qwen3 `<think/>` 标签剥离 |
| doubao | OpenAILLM | OpenAI 兼容 |
| mimo | OpenAILLM | OpenAI 兼容 |
| openai | OpenAILLM | 标准 OpenAI，Function Calling 已激活 |
| ollama | OpenAILLM | 自动检测 + `think:false` 关闭思考模式 |

**关键子系统**：
- `PromptInjector`：模块化提示词注入（优先级排序，Neuro-sama 风格）
- `MemoryRAGInjector`：从记忆系统检索注入
- `RateLimiter`：滑动窗口限速（`threading.Condition`）
- `RetryStrategy`：指数退避 + 抖动
- HTTP 连接池（5/10），LRU 缓存 + TTL，线程安全锁
- 真正的 SSE 流式传输
- **Function Calling**：OpenAI 和 MiniMax 引擎已支持原生 Function Calling，由 fc_executor 统一执行

### 6.4 记忆系统 (`app/memory/__init__.py`)

**v3.0 四层架构**：

| 层级 | 名称 | 说明 | 存储方式 |
|------|------|------|---------|
| L1 | 工作记忆 | 当前对话上下文 | 内存，滑动窗口（上限 20 条） |
| L2 | 情景记忆 | 摘要压缩事件 | 内存，超阈值触发压缩（5 条一批） |
| L3 | 语义记忆 | 向量检索 + 时间衰减 + 遗忘机制 | 向量数据库 |
| L4 | 事实记忆 | 用户偏好、关键事实 | 结构化存储 |

**检索权重**（可配置）：
- 向量相似度 70% — 语义相关
- 关键词匹配 20% — 精确命中
- 时间衰减 10% — 近期优先

### 6.5 视觉理解 (`app/vision/__init__.py`)

| Provider | 功能 | 特点 |
|----------|------|------|
| RapidOCR | 文字识别 | 本地，无需 API |
| MiniMax VL | 图片理解 | API，需密钥 |
| MiniCPM | 图片理解 | 本地模型 |

### 6.6 工具系统 (`app/tools/__init__.py`)

9 个内置工具：

| 工具 | 说明 | 只读 |
|------|------|------|
| Read | 读取文件 | ✅ |
| Write | 写入文件 | ❌ |
| Edit | 编辑文件 | ❌ |
| Glob | 按文件名搜索 | ✅ |
| Grep | 按内容搜索 | ✅ |
| LS | 列出目录 | ✅ |
| Bash | 执行命令 | ❌ |
| Think | 深度思考 | ✅ |
| Architect | 架构分析 | ✅ |

**安全机制**：`shell=False` + `shlex.split`，路径遍历防护，只读标记

### 6.7 MCP 工具桥接 (`app/mcp/__init__.py`)

- Model Context Protocol（Anthropic 标准）via stdio 传输
- 管理 MCP 服务器子进程连接
- "MCP:" 前缀路由，与 ToolFactory 共存

### 6.8 Web 服务 (`app/web/__init__.py`)

- **HTTP 服务**：静态文件、音频服务、文件上传
- **WebSocket 服务**：31 种入站消息，43+ 种出站消息
- **实时语音管线**：VAD → ASR → LLM → TTS → 音频推送

### 6.9 Function Calling 执行器 (`app/tools/fc_executor.py`)

统一工具调用执行循环，支持 LLM 的原生 Function Calling（FC）能力。

**核心功能**：
- **统一执行循环**：接收 LLM 返回的 tool_calls，逐个执行对应工具，将结果返回 LLM
- **流式/非流式模式**：支持流式 LLM 响应中的工具调用检测和非流式批量执行
- **多轮工具调用**：支持 LLM 在一次对话中连续调用多个工具
- **错误处理**：工具执行失败时返回错误信息给 LLM，不中断对话

**执行流程**：
```
LLM 响应包含 tool_calls → fc_executor
    ├── 解析 tool_calls 列表
    ├── 逐个执行对应工具（内置工具 + 伴侣工具 + MCP 工具）
    ├── 收集工具执行结果
    └── 将结果返回 LLM 继续推理
```

**当前状态**：OpenAI 和 MiniMax Provider 已激活 Function Calling，其他 Provider 使用 Prompt 模式降级。

### 6.10 伴侣工具 (`app/tools/companion.py`)

7 个面向用户的伴侣工具，增强 AI 的实用能力：

| 工具 | 说明 | 类型 |
|------|------|------|
| GetTimeTool | 获取当前时间 | 信息查询 |
| GetWeatherTool | 查询天气信息 | 信息查询 |
| SetReminderTool | 设置提醒 | 任务管理 |
| RememberThingTool | 记住用户提到的信息 | 记忆增强 |
| ChangeExpressionTool | 切换 Live2D 表情 | 形象控制 |
| SearchWebTool | 搜索网页信息 | 信息检索 |
| PlayMusicTool | 播放音乐 | 娱乐 |

**特点**：
- 通过 Function Calling 或 Prompt 模式被 LLM 自动调用
- 每个工具都有 JSON Schema 定义，供 FC 引擎使用
- 工具结果格式化为自然语言返回给 LLM

### 6.11 TTS 文本增强 (`app/tts/text_enhancer.py`)

在文本送入 TTS 引擎前进行预处理，提升语音合成质量。

**核心功能**：
- **ChatTTS 标记**：自动添加 `[laugh]`、`[uv_break]` 等 ChatTTS 专用标记
- **自动检测**：根据 TTS 引擎类型自动选择增强策略
- **中文特性处理**：数字转汉字、标点规范化、语气词处理
- **情感扩散**：根据文本内容推断情感，调整 TTS 参数（语速、音调等）

**使用方式**：
```python
from app.tts.text_enhancer import TextEnhancer

enhancer = TextEnhancer(engine_type="chattts")
enhanced_text = enhancer.enhance("今天天气真好啊，哈哈")
# 输出可能包含: "今天天气真好啊，[laugh]"
```

### 6.12 ChatTTS / CosyVoice TTS 引擎

**ChatTTS** (`app/tts/chattts.py`)：
- 本地 GPU 推理，追求自然韵律和表现力
- 支持情感标记和韵律控制
- 适合对话场景，语音自然度高

**CosyVoice** (`app/tts/cosyvoice.py`)：
- 本地 GPU 推理，支持多语言和多风格
- 支持零样本声音克隆
- 适合多语言场景和风格化语音

两个引擎均通过 TTSFactory 注册，支持自动降级到 Edge TTS。

---

## 7. 开发环境搭建

### 7.1 前置条件

- **操作系统**：Windows 10/11
- **Python**：3.11（必须，嵌入式 Python 或系统安装均可）
- **Git**：用于版本管理
- **NVIDIA GPU**（可选）：CUDA 加速，GPT-SoVITS 训练必需
- **Node.js**（可选）：MCP 服务器需要 npx

### 7.2 搭建步骤

```bash
# 1. 克隆代码
git clone https://github.com/xzt238/ai-vtuber-fixed.git
cd ai-vtuber-fixed

# 2. 一键安装（推荐新用户）
scripts\setup.bat
# 自动完成：嵌入式Python + 依赖 + PyTorch CUDA + 模型下载

# 3. 或者手动安装
# 3a. 安装核心依赖
pip install -r app/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3b. 安装 PyTorch CUDA
pip install torch torchaudio --index-url https://mirrors.aliyun.com/pytorch-wheels/cu124

# 3c. 安装原生桌面依赖（开发原生模式）
pip install PySide6 PySide6-Fluent-Widgets live2d-py pynput -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3d. 下载模型
scripts\download_models.bat
```

### 7.3 环境变量

项目使用以下环境变量（可通过 `.env` 文件或启动脚本设置）：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `HF_HOME` | HuggingFace 缓存目录 | `{项目根}/.cache/huggingface` |
| `HF_ENDPOINT` | HuggingFace 镜像 | `https://hf-mirror.com` |
| `PYTHONIOENCODING` | Python 编码 | `utf-8` |

### 7.4 IDE 配置

推荐使用 VS Code + Python 扩展：

```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/python/python.exe",
    "python.envFile": "${workspaceFolder}/.env",
    "files.encoding": "utf-8",
    "search.exclude": {
        "python/": true,
        ".cache/": true,
        "models/": true,
        "GPT-SoVITS/": true
    }
}
```

---

## 8. 代码规范与约定

### 8.1 目录约定

| 约定 | 说明 |
|------|------|
| `app/cache/` | 统一缓存目录（llm_preferences.json, api_keys.json, layout.json） |
| `app/web/cache/` | Web 相关缓存（**不要和 app/cache/ 混淆**） |
| `.cache/` | HuggingFace 模型缓存 |
| `models/` | 本地模型文件 |
| `memory/` | 运行时记忆数据 |
| `gugu_native/` | 原生桌面应用包名（避免与 `app/` 冲突） |

### 8.2 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 类名 | PascalCase | `AIVTuber`, `ChatPage`, `Live2DWidget` |
| 函数/方法 | snake_case | `process_message`, `on_backend_ready` |
| 私有方法 | 前缀 `_` | `_handle_local_tool`, `_prewarm_tts` |
| 信号 | snake_case + 过去分词/描述 | `backend_ready`, `speech_recognized` |
| 配置键 | snake_case | `llm.provider`, `tts.fallback_engines` |
| 文件名 | snake_case | `chat_page.py`, `voice_manager.py` |

### 8.3 懒加载约定

AIVTuber 的所有重型模块都通过 `@property` 懒加载：

```python
@property
def llm(self):
    if self._llm is None:
        self._llm = LLMFactory.create(self.config)
    return self._llm
```

**原则**：`__init__` 只创建轻量对象，重型导入和初始化延迟到首次访问。

### 8.4 错误处理约定

- 后端模块初始化失败：记录日志，返回 None 或空对象
- API 调用失败：指数退避重试 + 降级
- 工具执行失败：返回错误信息，不抛异常
- 原生桌面 UI 错误：InfoBar 提示用户，不弹窗阻断

### 8.5 日志约定

```python
import logging
logger = logging.getLogger('ModuleName')

logger.info("正常操作信息")
logger.warning("非致命问题，可继续运行")
logger.error("严重错误，功能受影响")
```

日志文件位置：
- 后端：项目根目录下（由 `app/logger_new.py` 管理）
- 原生桌面：`native/gugu_native.log`

### 8.6 版本号约定

格式：`v主版本.次版本.修订号`（如 v1.9.90）

| 变更类型 | 递增规则 | 示例 |
|---------|---------|------|
| 重大架构重构 / API 不兼容 | 主版本 | v1.x → v2.0 |
| 新功能 / 模块优化 / 新增模块 | 次版本 | v1.9 → v1.10 |
| Bug 修复 / 小改动 / 文档更新 | 修订号 | v1.9.90 → v1.9.91 |

更新类型标记：✨ 新增 / 🔧 修复 / 🐛 优化 / 🔐 安全 / 📝 文档 / 🔄 重构 / ⚡ 性能

---

## 9. 调试指南

### 9.1 WebUI 模式调试

最方便的调试模式，可使用浏览器开发者工具：

```bash
# 启动
scripts\go.bat

# 浏览器打开
http://localhost:12393

# F12 打开开发者工具
# - Console: 查看 WebSocket 消息
# - Network: 查看 HTTP 请求
# - Elements: 检查 DOM 和 CSS
```

### 9.2 原生桌面模式调试

```bash
# 启动（命令行输出日志）
scripts\start.bat

# 日志文件
type native\gugu_native.log

# 查看后端日志
type logs\*.log
```

### 9.3 后端独立调试

```bash
# 交互式命令行模式
python -m app.main --interactive

# 测试 LLM 连接
python -m app.main --test-llm

# 测试 TTS
python -m app.main --test-tts
```

### 9.4 常见调试场景

**LLM 连不上**：
1. 检查 `app/cache/api_keys.json` 是否有对应 Provider 的密钥
2. 检查 `app/cache/llm_preferences.json` 中的 base_url 是否正确
3. 检查网络连通性（Ollama 需要本地服务运行）

**TTS 无声音**：
1. 检查 GPT-SoVITS 底模是否下载完整（`GPT-SoVITS/GPT_SoVITS/pretrained_models/`）
2. 检查 CUDA 是否可用（`python -c "import torch; print(torch.cuda.is_available())"`）
3. Edge TTS 备用引擎是否正常（需联网）

**Live2D 不显示（原生模式）**：
1. 检查 `live2d-py` 是否安装：`python -c "import live2d"`
2. 检查 OpenGL 是否可用：`python -c "from PySide6.QtOpenGLWidgets import QOpenGLWidget"`
3. 如果都不行，会降级为占位图

**原生桌面闪退**：
1. 查看 `native/gugu_native.log` 错误信息
2. 确保 Python 3.11（其他版本可能 PySide6 不兼容）
3. 确保依赖安装完整：`pip install PySide6 PySide6-Fluent-Widgets`

---

## 10. 常见开发任务

### 10.1 添加新的 LLM Provider

1. 在 `app/llm/__init__.py` 中添加新的 Provider 配置段：

```python
# 在 LLMFactory._create_engine 中添加
if provider == "new_provider":
    return OpenAILLM(config, ...)  # 或新建引擎类
```

2. 在 `app/config.yaml` 的 `llm` 段添加配置：

```yaml
llm:
  new_provider:
    api_key: ""
    base_url: "https://api.newprovider.com/v1"
    model: "model-name"
```

3. 在原生桌面 `native/gugu_native/pages/settings_page.py` 中添加 UI：

```python
# 在 _create_llm_config_card 中添加新 Provider 的表单
```

4. 在 `app/shared_config.py` 的 `PROVIDER_CONFIG` 中添加配置映射

5. 更新 `docs/VERSION.md`

### 10.2 修改 WebUI 界面

- 文件：`app/web/static/index.html`（单文件，11,374 行）
- 修改后重启服务即生效，无需构建
- 注意：此文件仅影响 WebUI 模式和 pywebview 桌面模式
- **JS 同步**：修改 `version.py` 或 `shared_config.py` 后，需手动同步到 index.html 中的 JS 常量

### 10.3 修改原生桌面界面

- 文件在 `native/gugu_native/pages/` 和 `native/gugu_native/widgets/` 下
- 修改后重启应用即生效
- 主题/颜色修改集中在 `native/gugu_native/theme.py`
- 新增页面需在 `native/main.py` 的 `_create_pages()` 中注册

### 10.4 修改启动画面

**pywebview 启动画面**：修改 `launcher/splash.html`
- 使用 `desktop.bat` 启动立即生效
- 使用 `GuguGaga.exe` 启动需重新打包

**原生桌面启动画面**：修改 `native/gugu_native/resources/splash.png`
- 需替换图片文件

### 10.5 添加新的原生桌面页面

1. 在 `native/gugu_native/pages/` 下创建新页面文件：

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import FluentIcon

class NewPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("newPage")
        # 构建UI...

    def on_backend_ready(self):
        """后端初始化完成回调"""
        pass
```

2. 在 `native/main.py` 中注册：

```python
from gugu_native.pages.new_page import NewPage

# 在 _create_pages 中
self.new_page = NewPage(self)
self.addSubInterface(self.new_page, FluentIcon.NEW, "新页面")
```

3. 在 `native/gugu_native/theme.py` 中添加页面样式（如需）

### 10.6 重新打包桌面启动器

⚠️ **必须使用 Python 3.11 打包！**

```bash
cd C:\Users\x\Desktop\ai-vtuber-fixed\launcher
py -3.11 -m PyInstaller launcher.spec --clean --noconfirm

# 打包完成后
copy dist\GuguGaga.exe ..\GuguGaga.exe
```

### 10.7 构建原生桌面安装包

```bash
cd C:\Users\x\Desktop\ai-vtuber-fixed\native
build.bat    # PyInstaller 构建

# 使用 Inno Setup 生成安装器
# 打开 gugu_setup.iss 并编译
```

---

## 11. 版本管理与发布流程

### 11.1 版本号集中管理

版本号现已集中在 `app/version.py`，所有代码通过 `from app.version import VERSION` 获取版本号。

**修改版本号只需改一处**：`app/version.py`

```python
# app/version.py
VERSION = "v1.9.90"
```

### 11.2 代码修改后必做清单

| 步骤 | 文件 | 说明 |
|------|------|------|
| 1 | `app/version.py` | 更新版本号（单一来源） |
| 2 | `docs/VERSION.md` | 在顶部添加新版本记录 |
| 3 | `README.md` | 更新版本号 badge |
| 4 | `app/web/static/index.html` | 手动同步版本号到 JS 常量 |
| 5 | (可选) PyInstaller 重新打包 | 仅修改了 `launcher/` 下文件时需要 |

**参考文档**：修改前请查阅 `docs/CHANGE_IMPACT_MAP.md` 了解变更影响范围，参考 `docs/MODIFICATION_GUIDE.md` 获取详细修改指引。

### 11.3 VERSION.md 格式

```markdown
## 🟢 v1.9.91 (2026-05-08) ✅ STABLE

**简要描述本次更新**

### ✨ 新增
- 具体新增内容

### 🔧 修复
- 具体修复内容

### 🐛 优化
- 具体优化内容
```

### 11.4 Git 提交流程

```bash
cd C:\Users\x\Desktop\ai-vtuber-fixed

# 1. 检查状态
git status

# 2. 添加所有修改
git add .

# 3. 提交
git commit -m "v1.9.91: 更新描述"

# 4. 推送
git push

# 5. (可选) 打标签
git tag v1.9.91
git push origin main --tags
```

**注意**：`GuguGaga.exe` 可能因文件过大导致推送失败，可使用 Git LFS 或在 `.gitignore` 中排除。

---

## 12. 已知问题与改进方向

详见 `../KNOWN_ISSUES.md` 获取完整已知问题列表。

### 12.1 原生桌面模式待改进项

| 优先级 | 问题 | 说明 |
|--------|------|------|
| P0 | 实时语音体验待优化 | VAD 断句精度、录音降噪、多人说话识别 |
| P1 | 记忆页面功能不完整 | 搜索/编辑/删除 UI 存在但后端 API 不完整 |
| P1 | 训练页面缺少进度反馈 | GPT-SoVITS 训练进度显示不精确 |
| P2 | 缺少音频可视化 | audio_visualizer.py 已写好但未集成到主界面 |
| P2 | 缺少通知系统 | 系统通知（Toast）未实现 |
| P2 | 缺少多语言支持 | 目前仅中文 |
| P3 | 缺少插件系统 | 无动态加载扩展的机制 |

### 12.2 WebUI 模式待改进项

| 优先级 | 问题 | 说明 |
|--------|------|------|
| P0 | 前端单文件过大 | index.html 11,374 行，维护困难 |
| P1 | MCP 服务器配置为空 | 默认无 MCP 服务器，用户需手动配置 |

### 12.3 架构改进方向

详见 `../archive/feasibility_native_desktop.md` 和 `../archive/feasibility_tool_system_upgrade.md`。

---

## 13. 给 AI 助手的修改指南

### 关键记忆点

1. **项目有两种 Python 包**：`app/`（后端）和 `gugu_native/`（原生桌面前端），包名不同，不要混淆
2. **后端 CWD**：原生桌面模式下，后端的 CWD 必须在项目根目录（`os.chdir(PROJECT_DIR)`），否则相对路径（`./memory`等）会出错
3. **live2d.init()** 必须在 `QApplication` 创建之前调用
4. **配置持久化**：用户通过 UI 修改的配置保存在 `app/cache/llm_preferences.json`，优先级高于 `config.yaml`
5. **PyInstaller 打包**：必须使用 Python 3.11，其他版本会缺少 pywebview 等模块
6. **版本号集中管理**：所有版本号从 `app/version.py` 导入（`from app.version import VERSION`），不要在其他文件硬编码版本号
7. **共享配置单源**：跨模块常量集中在 `app/shared_config.py`（PROVIDER_CONFIG、EDGE_VOICES、EXPRESSION_KEYWORDS、EXPRESSION_MAP、MUTEX）
8. **前端规模**：WebUI 前端是 11,374 行的单文件 HTML，原生桌面是 ~6000 行的分散 Python 文件
9. **主题系统**：原生桌面的所有颜色常量集中在 `native/gugu_native/theme.py`，不要在页面中硬编码颜色
10. **JS 同步**：`index.html` 无法 import Python，修改 `version.py` 或 `shared_config.py` 后必须手动同步到 JS

### 修改后必须检查

- [ ] `app/version.py` 版本号是否更新
- [ ] `docs/VERSION.md` 是否更新
- [ ] `README.md` 版本号是否更新
- [ ] `app/web/static/index.html` 中的 JS 版本号常量是否同步
- [ ] 是否影响三种启动模式的兼容性
- [ ] 是否影响 WebUI 和原生桌面共享的后端逻辑
- [ ] `app/cache/` 下的 JSON 文件格式是否需要迁移
- [ ] 参考 `docs/CHANGE_IMPACT_MAP.md` 确认变更影响范围
- [ ] 参考 `docs/MODIFICATION_GUIDE.md` 获取详细修改指引

### 不要做的事

- ❌ 不要删除 `app/cache/` 下的任何文件
- ❌ 不要修改 `app/cache/llm_preferences.json` 的格式而不做向后兼容
- ❌ 不要在原生桌面页面中硬编码颜色值（使用 `theme.py` 的 `get_colors()`）
- ❌ 不要在 AIVTuber 的 `__init__` 中做重型导入
- ❌ 不要用 Python 3.14+ 打包 PyInstaller（必须 3.11）
- ❌ 不要在代码中硬编码版本号（使用 `from app.version import VERSION`）
- ❌ 不要在多个文件中重复定义共享常量（使用 `app/shared_config.py`）

---

*本文档最后更新: 2026-05-07 | 适用版本: v1.9.90+*
