<div align="center">

# 🐔 咕咕嘎嘎 AI-VTuber

**GPT-SoVITS 声音克隆 · Live2D 虚拟形象 · 三层记忆 · 视觉理解**

[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Version](https://img.shields.io/badge/version-v1.9.38-green.svg)](docs/VERSION.md)
[![Python](https://img.shields.io/badge/python-3.11-yellow.svg)](https://www.python.org/downloads/release/python-3119/)

[功能特性](#-功能特性) · [快速开始](#-快速开始) · [配置说明](#-配置说明) · [架构](#-项目架构) · [常见问题](#-常见问题) · [更新日志](#-版本更新日志)

</div>

---

## 🌟 项目简介

咕咕嘎嘎是一个功能丰富的 AI 虚拟形象系统，支持实时语音对话、文字聊天、声音克隆训练和视觉理解。内置 Live2D 虚拟形象，拥有三层记忆系统，能记住你说过的话。

**核心亮点：**
- 🎤 **GPT-SoVITS 声音克隆 + LoRA 训练面板** — 录制音频→一键训练→即用，目前同类项目中唯一内置训练面板
- 🧠 **三层记忆系统** — 工作记忆（对话上下文）+ 情景记忆（摘要压缩）+ 语义记忆（向量检索 + 遗忘机制）
- 👁️ **视觉理解** — 支持 OCR 文字识别、图片理解、屏幕感知
- 🖥️ **双模式运行** — 浏览器模式（WebUI）+ 桌面模式（原生窗口 + 系统托盘）
- 🔌 **嵌入式 Python** — 桌面版包含独立 Python，拷贝即用无需预装

## ✨ 功能特性

| 模块 | 功能 | 说明 |
|------|------|------|
| **ASR 语音识别** | FunASR / faster-whisper | 实时语音输入，VAD 智能断句 |
| **LLM 大语言模型** | MiniMax / OpenAI / Anthropic / Ollama | 多后端支持，RAG 记忆注入，支持本地模型 |
| **TTS 语音合成** | GPT-SoVITS（音色克隆）+ Edge TTS（保底） | 主引擎失败自动切换备用 |
| **声音训练** | GPT-SoVITS v3 + LoRA | WebUI 一键训练，无需命令行 |
| **视觉理解** | MiniMax VL / MiniCPM-V2 / RapidOCR | 图片理解 + 文字识别 + 屏幕感知 |
| **记忆系统** | 工作/情景/语义三层 | 向量检索 + 时间衰减 + 遗忘机制 + 摘要压缩 |
| **Live2D** | oh-my-live2d + pixi.js | 可自定义模型，支持表情切换 |
| **子 Agent** | Claude Code / 自定义 | 复杂任务自动调用子智能体 |
| **工具系统** | 沙箱执行 | 安全的本地命令执行，白名单/黑名单校验 |
| **VAD** | Silero VAD (WASM) | AI 语音活动检测，智能区分停顿和说完 |

## 🚀 快速开始

### 环境要求

| 项目 | 要求 |
|------|------|
| **操作系统** | Windows 10/11 |
| **Python** | 3.11（用于首次安装；安装后可用嵌入式 Python，无需系统 Python） |
| **显卡** | NVIDIA GPU 推荐（CUDA 加速；无 GPU 可用 CPU 模式，但 GPT-SoVITS 训练需 GPU） |
| **内存** | 8GB+（推荐 16GB+） |
| **磁盘** | 首次安装需要约 10GB（模型 + 依赖 + 嵌入式 Python） |

### 从 GitHub 安装（2 步）

#### 第 1 步：下载代码

```bash
git clone https://github.com/xzt238/ai-vtuber-fixed.git
cd ai-vtuber-fixed
```

> 也可以直接在 GitHub 页面点击 **Code → Download ZIP** 下载。

#### 第 2 步：一键安装

双击运行 **`scripts\setup.bat`**，它会自动完成：

| 步骤 | 内容 | 说明 |
|------|------|------|
| 1/7 | 下载嵌入式 Python 3.11 | npmmirror 国内源，~10MB |
| 2/7 | 安装全部 Python 依赖包 | 清华镜像源，~2GB |
| 3/7 | 安装 PyTorch CUDA cu124 | 阿里云镜像，GPU 加速 |
| 4/7 | 下载 GPT-SoVITS v3 底模 | HuggingFace 国内镜像，~2.5GB |
| 5/7 | 下载 G2PW 拼音模型 | ModelScope 国内源，~40MB |
| 6/7 | 首次启动自动下载 | ASR 模型 + Embedding 模型 |
| 7/7 | 输出核对报告 | ✅/❌ 标记所有关键项 |

> 💡 全程使用**国内镜像源**（清华/阿里云/HuggingFace 镜像/ModelScope），无需科学上网。
>
> ⏱️ 首次安装约需 20-40 分钟（取决于网速）。
>
> 📋 安装报告保存在 `scripts\setup_report.txt`。

#### 启动！

```bash
scripts\go.bat          # 浏览器模式（推荐首次使用）
scripts\desktop.bat     # 桌面模式（原生窗口）
```

浏览器访问 `http://localhost:12393` 即可。

#### 首次配置

启动后在 WebUI 中：

1. 打开 **API Key 面板**（左下角齿轮图标）— 输入你的 LLM API Key
2. 选择 **LLM Provider + 模型** — MiniMax / OpenAI / Anthropic / Ollama
3. 选择 **TTS 引擎** — Edge TTS 无需配置即可使用；GPT-SoVITS 需先下载底模
4. 开始聊天 🎉

> **使用 Ollama 本地模型**：先安装 [Ollama](https://ollama.com/) 并拉取模型（`ollama pull qwen3:8b`），然后在 WebUI 设置中选择 Provider 为 **OpenAI/Ollama**，Base URL 填 `http://localhost:11434/v1`，API Key 填 `ollama`。无需联网即可对话！

### 脚本说明

| 脚本 | 用途 | 何时使用 |
|------|------|----------|
| **`scripts\setup.bat`** | **一键全安装**（推荐新用户） | 首次安装 |
| `scripts\go.bat` | 启动浏览器模式 | 每次启动 |
| `scripts\desktop.bat` | 启动桌面模式 | 每次启动 |
| `scripts\install_deps.bat` | 单独重装依赖包 | 更新依赖 |
| `scripts\download_models.bat` | 单独下载模型文件 | 重装模型 |

## ⚙️ 配置说明

主配置文件：`app/config.yaml`

```yaml
# 语音识别
asr:
  provider: "funasr"          # funasr / faster_whisper

# 语音合成
tts:
  provider: "gptsovits"       # gptsovits（音色克隆）/ edge（保底）
  fallback_engines: ["edge"]  # 主引擎失败时自动切换

# 大语言模型
llm:
  provider: "openai"          # minimax / openai / anthropic（Ollama 走 openai）
  max_tokens: 2048
  enable_rag_injection: true  # 注入记忆到上下文
  openai:                     # OpenAI / Ollama 共用此配置段
    api_key: "ollama"         # Ollama 填 "ollama" 即可；OpenAI 填真实 key
    base_url: "http://localhost:11434/v1"  # Ollama 端点；OpenAI 留空用默认
    model: "qwen3:8b"         # Ollama 模型名；OpenAI 用 gpt-4o 等

# 视觉理解
vision:
  default_provider: "minimax_vl"  # minimax_vl / minicpm / rapidocr

# 记忆系统
memory:
  provider: "simple"          # simple / vector（向量检索）
  working_memory_limit: 20    # 工作记忆上限
  forgetting_threshold: 0.3   # 遗忘阈值
  retrieval_weights:
    vector: 0.7               # 向量相似度权重
    keyword: 0.2              # 关键词匹配权重
    recency: 0.1              # 时间衰减权重

# Live2D
live2d:
  enabled: true
  model_path: "./app/web/assets/model/shizuku"

# Web 服务
web:
  port: 12393                 # HTTP 端口
  ws_port: 12394              # WebSocket 端口
```

> 💡 API Key 推荐通过 WebUI 面板输入，不直接写在配置文件中。API Key 保存在本地 `app/cache/api_keys.json`，不会上传到 Git。

## 📁 项目架构

```
ai-vtuber-fixed/
├── app/                        # 核心应用
│   ├── main.py                 # 主入口，AIVTuber 类（懒加载架构）
│   ├── config.yaml             # 统一配置文件
│   ├── asr/                    # 语音识别（FunASR / faster-whisper）
│   ├── tts/                    # 语音合成（GPT-SoVITS / Edge TTS）
│   ├── llm/                    # 大语言模型（MiniMax / OpenAI / Anthropic）
│   ├── vision/                 # 视觉理解（MiniMax VL / MiniCPM-V2 / OCR）
│   ├── memory/                 # 记忆系统（三层：工作/情景/语义）
│   ├── live2d/                 # Live2D 虚拟形象
│   ├── voice/                  # 语音输入
│   ├── trainer/                # GPT-SoVITS 声音训练管理
│   ├── tools/                  # 本地工具系统
│   ├── ocr/                    # OCR 文字识别
│   ├── web/                    # HTTP + WebSocket 服务
│   │   └── static/
│   │       ├── index.html      # 单文件前端（面板系统 + Live2D）
│   │       └── libs/           # 前端库（pixi.js, oh-my-live2d, Silero VAD）
│   ├── tts_cache.py            # TTS 语音缓存
│   ├── utils.py                # 工具函数
│   └── logger_new.py           # 日志模块
├── GPT-SoVITS/                 # GPT-SoVITS 声音克隆引擎
│   ├── GPT_SoVITS/             # 核心代码 + 预训练模型（不包含在 Git 中）
│   ├── GPT_weights_v3/         # GPT 模型权重（运行时生成）
│   ├── SoVITS_weights_v3/      # SoVITS 模型权重（运行时生成）
│   ├── api.py                  # TTS API 接口
│   └── webui.py                # 训练 WebUI
├── launcher/                   # 桌面启动器
│   ├── launcher.py             # pywebview 原生窗口 + 启动画面
│   └── splash.html             # 启动画面（进度条 + 状态）
├── scripts/                    # 启动和安装脚本
│   ├── setup.bat               # ⭐ 一键全安装（新用户首选）
│   ├── go.bat                  # 浏览器模式启动
│   ├── desktop.bat             # 桌面模式启动
│   ├── install_deps.bat        # 依赖安装器（高级用户单独使用）
│   └── download_models.bat     # 模型下载（高级用户单独使用）
├── python/                     # 嵌入式 Python 3.11（不包含在 Git 中，通过脚本下载）
├── docs/                       # 文档
│   └── VERSION.md              # 版本历史
├── .env.example                # 环境变量模板
└── LICENSE                     # GPL-3.0
```

**Git 仓库不包含的文件**（通过脚本下载或运行时生成）：
- `python/` — 嵌入式 Python 环境（~3GB）
- `GPT-SoVITS/GPT_SoVITS/pretrained_models/` — 预训练底模（~2.5GB）
- `models/` — ASR 模型（~990MB）
- `.cache/` — HuggingFace 模型缓存（~6.9GB）
- `app/cache/api_keys.json` — API 密钥（隐私）
- `GPT-SoVITS/GPT_SoVITS/memory/` — 聊天记忆（隐私）

## 🔧 核心管线

### 技术栈

| 层 | 技术 | 说明 |
|------|------|------|
| **后端** | Python 3.11 + aiohttp | 异步 HTTP + WebSocket 服务 |
| **前端** | 原生 HTML/CSS/JS（单文件） | 面板系统 + Live2D + VAD + 实时语音 |
| **通信** | WebSocket（实时） + HTTP（API） | 前后端实时双向通信 |
| **桌面端** | pywebview（WebView2） | 原生窗口 + 系统托盘 |
| **打包** | PyInstaller + NSIS | 单 EXE 启动器 + 安装程序 |



```
用户语音 → [ASR 语音识别] → 文字
                              ↓
                         [LLM 大语言模型] ← [记忆系统（RAG注入）]
                              ↓
                         AI 回复文字
                              ↓
                    [TTS 语音合成] → 语音播放
                         ↑
                   [Live2D 口型同步 + 表情]
```

**语音对话流程：**
1. 浏览器采集音频 → WebSocket 发送到后端
2. VAD 检测语音活动，智能区分停顿和说完
3. ASR 将语音转文字
4. LLM 生成回复（自动注入相关记忆）
5. TTS 将回复合成语音（GPT-SoVITS 优先，失败自动降级到 Edge TTS）
6. 前端播放语音 + Live2D 口型同步

## 🎤 声音克隆训练

咕咕嘎嘎内置了 GPT-SoVITS v3 声音克隆训练面板，可以在 WebUI 中一键训练：

1. **录制音频** — 至少 3 分钟干净的人声
2. **上传音频** — 拖拽到训练面板
3. **一键训练** — 自动切片→标注→训练 LoRA
4. **即训练即用** — 训练完成后直接在 TTS 中使用

> 🎯 这是目前同类 AI VTuber 项目中**唯一内置训练面板**的，其他项目需要手动配置命令行训练。

## 🧠 记忆系统

三层记忆架构，模拟人类记忆过程：

| 层级 | 名称 | 说明 |
|------|------|------|
| L1 | 工作记忆 | 当前对话上下文（滑动窗口，上限 20 条） |
| L2 | 情景记忆 | 对话摘要（超出阈值触发压缩，5 条一批） |
| L3 | 语义记忆 | 长期知识（向量检索 + 时间衰减 + 遗忘机制） |

**检索权重可配置：**
- 向量相似度 70% — 语义相关
- 关键词匹配 20% — 精确命中
- 时间衰减 10% — 近期优先

## ❓ 常见问题

### Q: 启动报错 "Python 3.11 not found"
确保已安装 Python 3.11 并添加到 PATH，或运行 `scripts\download_models.bat` 下载嵌入式 Python。

### Q: CUDA 不可用
检查 NVIDIA 驱动是否最新，运行 `scripts\install_deps.bat` 会自动安装 CUDA 版 PyTorch。

### Q: 模型下载太慢 / 下载失败
所有模型都使用国内镜像源。如果仍然失败：
- 检查网络连接
- 查看下载报告中的手动下载地址
- 使用代理或更换网络环境重试

### Q: install_deps.bat 安装某些包失败
部分可选包（如 pyopenjtalk、jieba_fast）需要 C++ 编译环境，安装失败不影响核心功能。查看核对报告中的 ❌ 标记，如果都是"可选"则可忽略。

### Q: GPT-SoVITS 训练失败
确保有 NVIDIA GPU 和足够显存（推荐 6GB+）。无 GPU 可使用 Edge TTS。

### Q: 桌面模式闪退
运行 `scripts\desktop.bat`，它会自动检查并安装 pywebview，并解除 DLL 安全标记。

### Q: 如何更换 Live2D 模型
将模型文件放到 `app/web/assets/model/` 下，在 `config.yaml` 中修改 `live2d.model_path`。

### Q: 如何使用向量记忆
将 `config.yaml` 中 `memory.provider` 改为 `"vector"`，首次启动会自动下载 embedding 模型。

### Q: 如何使用 Ollama 本地模型（无需 API Key）
1. 安装 [Ollama](https://ollama.com/) 并启动
2. 拉取模型：`ollama pull qwen3:8b`（推荐 8B Q4_K_M，~5GB 内存）
3. 在 WebUI 设置中：Provider 选 **OpenAI/Ollama**，Base URL 填 `http://localhost:11434/v1`，API Key 填 `ollama`
4. 或直接改 `config.yaml`：
```yaml
llm:
  provider: "openai"
  openai:
    api_key: "ollama"
    base_url: "http://localhost:11434/v1"
    model: "qwen3:8b"
```
> 💡 系统会自动检测 Ollama 端点并切换到原生 API（关闭 Qwen3 思考模式），无需额外配置。

### Q: 我的 API Key 会泄露吗？
不会。API Key 保存在本地 `app/cache/api_keys.json`，该文件已被 `.gitignore` 排除，不会上传到 Git。聊天记录同样不会被上传。

## 📜 许可证

本项目基于 [GNU General Public License v3.0](LICENSE) 开源。衍生作品必须同样开源。

GPT-SoVITS 子模块遵循其自身的开源许可证（`GPT-SoVITS/LICENSE`）。

## 📋 版本更新日志

> 完整版本记录详见 [docs/VERSION.md](docs/VERSION.md)

### v1.9.38 (2026-04-29) — 前端 LLM 多 Provider 适配 + Ollama 原生 API

**修复** Ollama 用户被 API Key 检查误拦的问题；**新增** Ollama 原生 API 支持

- 🔧 `checkApiKeyStatus()` / `sendMessage()`: 查询当前活跃 provider，本地模型跳过 API Key 拦截
- ✨ LLM 配置面板：新增 Anthropic 选项 + Base URL + API Key 输入框，Provider 切换联动字段显隐
- ✨ 新手引导：Provider 选择 + Base URL 输入，Ollama 用户可跳过 API Key
- ✨ **Ollama 原生 API**：自动检测 Ollama 端点，走 `/api/chat` 而非 `/v1/chat/completions`，传 `think:false` 关闭 Qwen3 思考模式

### v1.9.37 (2026-04-29) — 本地 LLM 适配

- ✨ Ollama + Qwen3-8B Q4_K_M 零代码改动接入
- ✨ Qwen3 thinking 模式三层防护（system prompt `/no_think` + content None 防护 + `_strip_thinking()` 兜底）

### v1.9.36 (2026-04-29) — 记忆前端功能补全

- ✨ 记忆编辑、重要性精确设置（0-5 下拉）、事实来源过滤、衰减预览可视化
- ✨ 后端新增 `decay_preview` 和 `search_by_time` WS action

### v1.9.35 (2026-04-28) — 记忆系统 v3.0 全面重构

- ✨ 多维梯度评分（6 维度 0-5 连续梯度）、LLM 语义摘要、事实提取系统
- ✨ 向量库去重、记忆去重合并、自动标签系统、记忆重整 `consolidate()`
- ✨ 前端标签页切换（全部/工作/情景/事实）、操作按钮、衰减系数滑块

### v1.9.34 (2026-04-28) — 记忆路径漂移修复

- 🔧 `os.chdir()` 导致 `memory/` 路径漂移，所有存储路径 init 时立即 `resolve()` 为绝对路径

### v1.9.33 (2026-04-28) — 记忆面板全面修复

- 🔧 后端 list/timeline 增强字段、WS sub_type 判别、配置实时应用
- 🔧 前端记忆渲染增强（时间标签、层级标签、摘要徽章、重要性星标）

### v1.9.32 (2026-04-28) — 交互动画全面升级

- 🎨 消息气泡化、入场动画、面板折叠/展开动画、按钮涟漪效果、Header 渐变呼吸

### v1.9.31 (2026-04-28) — 用户体验重大改进 + GitHub 发布准备

- ✨ 新手引导系统、API Key 强制拦截、统一 Toast 通知、思考指示器、错误信息改进
- ✨ 新增 LICENSE (GPL-3.0)、README.md、完善 .gitignore、新增 download_models.bat

### v1.9.29 (2026-04-27) — 嵌入式 Python 可移植性修复

- 🔧 补全 python.exe + DLL、安装 pip、重装 PyTorch CUDA cu124、启动脚本支持嵌入式优先检测

### v1.9.28 (2026-04-27) — TTS 进度反馈 + 启动性能优化

- ✨ TTS 进度消息链（`tts_start`/`tts_progress`/`tts_error`）+ 前端状态指示器
- ⚡ 全链路启动性能优化：模块后台预加载、健康检查加速、Live2D 即时加载

### v1.9.26 (2026-04-27) — 记忆系统初始化修复

- 🔧 `hasattr` 静默吞掉异常导致记忆从未初始化，改用 `getattr` + 错误日志

### v1.9.24 (2026-04-26) — GuguGaga.exe 后端冻死修复

- 🔧 evaluate_js 死锁 → stdout 管道满 → 后端冻死，用 `_splash_done` 标志 + 非阻塞 evaluate_js 修复

### v1.9.23 (2026-04-26) — GuguGaga.exe 前端功能全面失效修复

- 🔧 WS 重连后消息丢失（增强器未重新绑定）、TTS 音色下拉框初始为空

### v1.9.22 (2026-04-25) — 实时语音误打断 + TTS 缓存 + 诊断工具

- 🔧 VAD 误打断：800ms 延迟打断机制；TTS 缓存自动清理（上限 120 文件）；ASR 录音 60s

### v1.9.20–21 (2026-04-25) — TTS 修复

- 🔧 TTS 英文被错误正则删除（`\u1F300` 只解析 4 位）、横杠"先全替换再恢复"策略

### v1.9.18–19 (2026-04-25) — GPT-SoVITS 依赖补全 + API Key 面板

- 🔧 补全 44 个 GPT-SoVITS 依赖；✨ 设置面板内置 API Key 输入

### v1.9.15–17 (2026-04-25) — 生产就绪 + 启动脚本修复

- 🔐 生产就绪审计（GPU 显存释放、子进程管理、原子写入等）
- 🔧 启动脚本 CWD 修复、前端 WS 消息分发补全

### v1.9.16 (2026-04-25) — 生产打包

- 📦 嵌入式 Python 3.11.2 + GuguGaga.exe (PyInstaller) + NSIS 安装器

<details>
<summary>📖 更早版本</summary>

### v1.9.14 (2026-04-25) — TTS 预热优化 + 系统监控自动刷新

### v1.9.13 (2026-04-25) — UI/UX 改进 + 游戏风格控制台

### v1.9.12 (2026-04-25) — 桌面模式布局加载完全重构

### v1.9.7–11 — 布局持久化系列修复

</details>

## 🙏 致谢

- [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) — 声音克隆引擎
- [oh-my-live2d](https://github.com/oh-my-live2d/oh-my-live2d) — Live2D 渲染
- [FunASR](https://github.com/modelscope/FunASR) — 语音识别
- [Silero VAD](https://github.com/snakers4/silero-vad) — 语音活动检测
- [MiniMax](https://www.minimaxi.com/) — LLM & 视觉理解 API

---

<div align="center">

**Made with ❤️ by XZT**

</div>
