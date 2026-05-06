# 🖥️ 咕咕嘎嘎 AI-VTuber 原生桌面应用架构文档

> **版本**: v1.0 | **适用项目版本**: v1.9.82+ | **日期**: 2026-05-05

---

## 目录

1. [架构概览](#1-架构概览)
2. [入口与启动流程](#2-入口与启动流程)
3. [主窗口结构](#3-主窗口结构)
4. [页面详解](#4-页面详解)
5. [组件详解](#5-组件详解)
6. [后端交互方式](#6-后端交互方式)
7. [主题系统](#7-主题系统)
8. [构建与打包](#8-构建与打包)
9. [当前状态与待改进项](#9-当前状态与待改进项)
10. [开发指南](#10-开发指南)

---

## 1. 架构概览

### 1.1 与其他模式的关系

```
┌─────────────────────────────────────────────────────────────────┐
│                    咕咕嘎嘎 AI-VTuber 三种模式                    │
├──────────────────┬──────────────────┬───────────────────────────┤
│   WebUI 模式     │  pywebview 桌面  │   原生桌面 (PySide6) ★    │
│   scripts/go.bat │ scripts/desktop  │   scripts/start.bat       │
│                  │     .bat         │                           │
├──────────────────┼──────────────────┼───────────────────────────┤
│   浏览器访问      │  WebView2 壳    │   Qt6 原生窗口            │
│   index.html     │  + index.html   │   PySide6 Widgets         │
│   WebGL Live2D   │  WebGL Live2D   │   OpenGL Live2D           │
│   HTTP/WS 通信   │  HTTP/WS 通信   │   Python 直调 ★           │
│   无托盘/快捷键   │  有托盘/启动画面 │   全功能 ★                │
└──────────────────┴──────────────────┴───────────────────────────┘
                           │
                    ┌──────┴──────┐
                    │  共享后端     │
                    │  app/main.py │
                    │  AIVTuber    │
                    └─────────────┘
```

**原生桌面的核心优势**：
- **零通信开销**：直接 Python 调用 `AIVTuber` 实例，无 HTTP/WS 序列化/反序列化
- **真正原生体验**：系统原生窗口、菜单、托盘、通知、文件对话框
- **Live2D 原生渲染**：live2d-py + QOpenGLWidget，比 WebGL 性能更好
- **独有功能**：桌面宠物、全局快捷键、开机自启、自动更新

### 1.2 技术选型

| 技术 | 版本 | 用途 |
|------|------|------|
| PySide6 | 6.x | Qt6 框架 |
| PySide6-Fluent-Widgets | latest | Windows 11 Fluent Design 组件库 |
| live2d-py | 0.6.x | Live2D Cubism SDK Python 绑定 |
| pynput | latest | 全局键盘监听（快捷键） |
| sounddevice | latest | 音频录制 |
| Silero VAD | latest | 语音活动检测（Python 版，非 WASM） |

### 1.3 包名策略

原生桌面应用使用 `gugu_native` 作为包名，避免与后端 `app/` 包冲突。

```python
# native/main.py 中的 sys.path 设置
NATIVE_DIR = os.path.dirname(os.path.abspath(__file__))     # native/
PROJECT_DIR = os.path.dirname(NATIVE_DIR)                    # 项目根

sys.path.insert(0, NATIVE_DIR)      # 优先加载 gugu_native
sys.path.append(PROJECT_DIR)        # append 而非 insert，避免 app/ 覆盖 gugu_native
```

---

## 2. 入口与启动流程

### 2.1 启动脚本 (`scripts/start.bat`)

```
start.bat 流程:
1. 设置环境变量 (HF_HOME, HF_ENDPOINT, PYTHONIOENCODING)
2. 查找 Python（嵌入式 python/python.exe 优先，回退系统 py -3.11）
3. 检查并安装 PySide6
4. 检查并安装 live2d-py
5. cd native && python main.py
```

### 2.2 主入口 (`native/main.py`)

```
main() 函数流程:
1. QApplication.setHighDpiScaleFactorRoundingPolicy(PassThrough)  ← 高DPI
2. QApplication() 创建
3. 设置全局字体 (Microsoft YaHei UI, 10pt)
4. 设置应用图标 (app.ico)
5. QSplashScreen 显示启动画面 (splash.png)
6. GuguGagaApp(FluentWindow) 创建主窗口
7. window.show()
8. splash.finish(window)  ← 关闭启动画面
9. app.exec() 进入事件循环
10. 退出时 live2d.dispose() 清理
```

### 2.3 主窗口初始化 (`GuguGagaApp.__init__`)

```
__init__() 流程:
1. setWindowTitle / setMinimumSize / resize
2. DualModeCompat — 确保目录、检查互斥锁、检测 WebUI
3. PerformanceManager — 注册清理目标
4. AutoStartManager — 开机自启
5. _create_pages() — 创建 5 个导航页面
6. apply_theme(Theme.DARK) — 暗色主题
7. get_global_qss() — 全局样式表
8. TrayManager — 系统托盘
9. RealtimeVoiceManager — 实时语音
10. HotkeyManager — 全局快捷键
11. UpdateManager — 自动更新
12. 延迟 2 秒初始化后端 (perf_manager.schedule_backend_init)
13. 延迟 10 秒检查更新
```

### 2.4 后端初始化 (`backend` property)

```python
@property
def backend(self):
    if self._backend is None:
        os.chdir(PROJECT_DIR)           # 确保 CWD 在项目根
        from app.main import AIVTuber
        self._backend = AIVTuber()      # 懒加载创建后端
        self.voice_manager.backend = self._backend
        self._backend_ready = True
    return self._backend
```

### 2.5 后端就绪回调 (`_on_backend_ready`)

```
_on_backend_ready() 流程:
1. 通知所有页面 on_backend_ready()
2. 注册主动说话回调 (proactive._native_callback)
3. TTS 预热 (串行加载上次音色)
4. ASR 预加载 (后台线程)
```

---

## 3. 主窗口结构

### 3.1 FluentWindow 布局

```
┌─────────────────────────────────────────────────────┐
│  ┌──────┐  ┌────────────────────────────────────┐  │
│  │ 导航  │  │                                     │  │
│  │ 侧栏  │  │         当前页面内容区               │  │
│  │       │  │                                     │  │
│  │ 对话  │  │  ┌─────────────────────────────┐   │  │
│  │ 训练  │  │  │                             │   │  │
│  │ 记忆  │  │  │    Page Content Area        │   │  │
│  │ 下载  │  │  │                             │   │  │
│  │       │  │  │                             │   │  │
│  │ ────  │  │  │                             │   │  │
│  │ 设置  │  │  └─────────────────────────────┘   │  │
│  └──────┘  └────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 3.2 导航配置

```python
# native/main.py - _create_pages()
self.chat_page = ChatPage(self)
self.addSubInterface(self.chat_page, FluentIcon.CHAT, "对话")

self.train_page = TrainPage(self)
self.addSubInterface(self.train_page, FluentIcon.MICROPHONE, "音色训练")

self.memory_page = MemoryPage(self)
self.addSubInterface(self.memory_page, FluentIcon.BOOK_SHELF, "记忆")

self.model_download_page = ModelDownloadPage(self)
self.addSubInterface(self.model_download_page, FluentIcon.DOWNLOAD, "模型下载")

self.settings_page = SettingsPage(self)
self.addSubInterface(self.settings_page, FluentIcon.SETTING, "设置",
                     position=NavigationItemPosition.BOTTOM)
```

导航栏属性：
- 展开宽度：200px
- 可折叠：是
- 设置在底部

---

## 4. 页面详解

### 4.1 对话页 (`chat_page.py`, 1739 行) ★ 最核心

**布局**：

```
┌───────────────────────────────────────────────┐
│ ┌─────────────┐  ┌────────────────────────┐  │
│ │             │  │  聊天显示区              │  │
│ │   Live2D    │  │  (QTextEdit, HTML气泡)  │  │
│ │   Widget    │  │                         │  │
│ │  (OpenGL)   │  │                         │  │
│ │             │  ├────────────────────────┤  │
│ │  380x480    │  │  输入栏卡片             │  │
│ │             │  │  [📎][────输入框────][➤] │  │
│ │             │  ├────────────────────────┤  │
│ │             │  │  TTS工具栏 (单行)       │  │
│ │             │  │  [TTS引擎][音色][🎤][🔊] │  │
│ └─────────────┘  └────────────────────────┘  │
└───────────────────────────────────────────────┘
```

**核心功能**：

| 功能 | 实现方式 |
|------|---------|
| 对话 | `_send_message()` → `backend.process_message()` → 流式显示 |
| TTS | `_speak_text()` → `backend.speak()` → QMediaPlayer 播放 |
| 录音 | sounddevice 录音 → ASR → 发送消息 |
| 实时语音 | `RealtimeVoiceManager` → VAD + ASR → 自动发送 |
| Live2D | `Live2DWidget` → OpenGL 渲染 + 口型同步 + 表情切换 |
| 桌面宠物 | `_toggle_desktop_pet()` → `DesktopPetWindow` |
| OCR/视觉 | 文件上传 → `backend.vision` → 显示结果 |
| 主动说话 | `proactive._native_callback` → `_on_proactive_speech()` |
| 聊天历史 | `_save_chat_history()` / `_load_chat_history()` → JSON 文件 |

**对话气泡**（微信风格）：
- AI 气泡：左对齐，灰色底 (#2a2d3e)，带 SVG 头像
- 用户气泡：右对齐，蓝色底 (#4263eb)，白字
- 系统消息：居中胶囊标签
- 时间戳：对话间隔 >3 分钟显示
- 打字光标：流式回复时 ▍ 闪烁 (530ms)
- 思考动画：●●● 轮转亮度

**流式回复实现**：
```python
def _send_message(self):
    # 1. 在后台线程调用 LLM
    # 2. 使用 QTimer 轮询获取流式文本
    # 3. 逐字追加到聊天显示区
    # 4. 每句完成时触发 TTS
    # 5. 完成后添加分隔线
```

**Live2D 交互**：
- 鼠标跟踪：`mouseMoveEvent` → `model.SetParameterValue`
- 点击交互：`mousePressEvent` → 随机表情/动作
- 口型同步：TTS 播放时 `start_mouth_sync()` → 定时器驱动
- 表情检测：AI 回复文本含 `（笑）` 等标记 → 自动切换表情

### 4.2 音色训练页 (`train_page.py`, 1040 行)

**布局**：

```
┌───────────────────────────────────────────────┐
│ 项目管理栏                                      │
│ [新建项目▼] [新建] [删除] [刷新]               │
├───────────────────────────────────────────────┤
│ ┌──────────────────┐  ┌──────────────────┐   │
│ │ 音频管理          │  │ 训练配置          │   │
│ │ - 上传音频        │  │ - 参考音频选择    │   │
│ │ - 录制音频        │  │ - 参考文本输入    │   │
│ │ - 音频列表        │  │ - S1 训练参数    │   │
│ │ - 自动切片        │  │ - S2 训练参数    │   │
│ │                  │  │                  │   │
│ └──────────────────┘  │ [开始训练]        │   │
│                       └──────────────────┘   │
├───────────────────────────────────────────────┤
│ 训练日志 (QTextEdit)                           │
│ ═════════════════════════════════════════════  │
│ [14:30:01] Starting S1 training...            │
│ [14:30:15] Epoch 1/10, Loss: 0.45            │
│ ═════════════════════════════════════════════  │
└───────────────────────────────────────────────┘
```

**核心功能**：
- 项目管理（新建/删除/切换）
- 音频上传（拖拽 + 文件对话框）
- 录音功能（sounddevice）
- 自动切片（GPT-SoVITS 的 slicer）
- 参考音频配置（选择/试听）
- S1/S2 训练参数配置
- 训练进度监控（子进程 stdout 解析）
- 项目重置

### 4.3 记忆页 (`memory_page.py`, 816 行)

**布局**：

```
┌───────────────────────────────────────────────┐
│ 统计卡片（4层）                                 │
│ [工作:12] [情景:5] [语义:89] [事实:23]         │
├───────────────────────────────────────────────┤
│ [搜索框_________________________] [🔍]         │
├───────────────────────────────────────────────┤
│ ┌─────┬─────┬─────┬─────┐                    │
│ │工作  │情景  │语义  │事实  │  ← QTabWidget    │
│ ├─────┼─────┼─────┼─────┤                    │
│ │     │     │     │     │                    │
│ │ 记忆 │ 记忆 │ 记忆 │ 记忆 │  ← QTreeWidget  │
│ │ 列表 │ 列表 │ 列表 │ 列表 │                    │
│ │     │     │     │     │                    │
│ └─────┴─────┴─────┴─────┘                    │
├───────────────────────────────────────────────┤
│ [标记重要] [删除] [搜索] [整合] [导出]         │
└───────────────────────────────────────────────┘
```

**四层记忆**：

| 层 | 显示内容 | 操作 |
|----|---------|------|
| L1 工作记忆 | 对话上下文 | 查看、删除 |
| L2 情景记忆 | 摘要事件 | 查看、编辑、删除 |
| L3 语义记忆 | 向量检索条目 | 查看、标记重要、删除 |
| L4 事实记忆 | 用户偏好/关键事实 | 查看、编辑、删除 |

**统计卡片颜色**：
- 工作记忆：`#4dabf7`（蓝色）
- 情景记忆：`#69db7c`（绿色）
- 语义记忆：`#da77f2`（紫色）
- 事实记忆：`#ffd43b`（黄色）

### 4.4 模型下载页 (`model_download_page.py`, 544 行)

**支持的模型**：

| 模型 | 来源 | 大小 | 说明 |
|------|------|------|------|
| FunASR Paraformer | ModelScope | ~990MB | 中文语音识别 |
| Faster-Whisper | HuggingFace | ~1GB | 多语言语音识别 |
| BGE-Base-zh-v1.5 | HuggingFace | ~400MB | 中文文本嵌入 |
| RapidOCR | 本地 | ~50MB | OCR 文字识别 |
| Silero VAD | HuggingFace | ~2MB | 语音活动检测 |

**功能**：
- 检测模型是否已下载（文件存在性检查）
- 显示下载状态（✅ 已下载 / ⬇️ 可下载 / ❌ 下载失败）
- 下载进度显示
- 重试下载

### 4.5 设置页 (`settings_page.py`, 1097 行)

**布局**：

```
┌───────────────────────────────────────────────┐
│ 📋 模型配置                                     │
│ ┌─────────────────────────────────────────┐   │
│ │ LLM Provider: [DeepSeek ▼]             │   │
│ │ API Key:      [________________]        │   │
│ │ Base URL:     [________________]        │   │
│ │ Model:        [________________]        │   │
│ │ Max Tokens:   [2048___]                │   │
│ └─────────────────────────────────────────┘   │
├───────────────────────────────────────────────┤
│ 🎤 语音配置                                     │
│ ┌──────────────────┬──────────────────┐       │
│ │ TTS 引擎         │ ASR 引擎          │       │
│ │ [GPT-SoVITS ▼]  │ [FunASR ▼]       │       │
│ │ 音色: [默认 ▼]   │                   │       │
│ │ 语速: [1.0___]   │                   │       │
│ └──────────────────┴──────────────────┘       │
├───────────────────────────────────────────────┤
│ 👁️ 视觉/OCR 配置                                │
│ Provider: [RapidOCR ▼]                        │
├───────────────────────────────────────────────┤
│ 🎨 外观                                         │
│ 主题: [暗色 ● ○ 亮色]                           │
├───────────────────────────────────────────────┤
│ ⚙️ 系统                                         │
│ 开机自启 [○]  系统托盘 [●]                      │
│ 主动说话 [●]  间隔 [60___]秒                    │
├───────────────────────────────────────────────┤
│ ℹ️ 关于                                         │
│ 咕咕嘎嘎 AI-VTuber v1.9.82                    │
│ GitHub: xzt238/ai-vtuber-fixed               │
└───────────────────────────────────────────────┘
```

**10 个 LLM Provider 配置**：

| Provider | 需要 API Key | 需要 Base URL | 特殊说明 |
|----------|-------------|---------------|---------|
| DeepSeek | ✅ | 默认 | - |
| Kimi | ✅ | 默认 | - |
| GLM | ✅ | 默认 | - |
| Qwen | ✅ | 默认 | 自动剥离 think 标签 |
| MiniMax | ✅ | 默认 | 默认 Provider |
| Doubao | ✅ | 默认 | - |
| MiMo | ✅ | 默认 | - |
| OpenAI | ✅ | 默认 | - |
| Anthropic | ✅ | 默认 | Claude 格式 |
| Ollama | "ollama" | localhost:11434 | 本地模型 |

---

## 5. 组件详解

### 5.1 Live2D Widget (`live2d_widget.py`, 259 行)

**架构**：
```
QOpenGLWidget
    ├── initializeGL() → live2d.glewInit() + LoadModelJson
    ├── paintGL() → model.Update() + model.Draw() (60FPS)
    ├── resizeGL() → model.Resize()
    ├── mouseMoveEvent → model.SetParameterValue (头部跟踪)
    ├── mousePressEvent → 随机表情/动作
    ├── start_mouth_sync() → QTimer 驱动口型
    └── stop_mouth_sync() → 停止口型
```

**降级机制**：如果 `live2d-py` 未安装，显示 QLabel 占位图。

**口型同步**：TTS 播放时，定时器以 ~30ms 间隔读取音频振幅，映射到 `ParamMouthOpenY` 参数。

**模型切换**：`load_model(model_path)` 方法支持运行时切换 Live2D 模型。

### 5.2 实时语音管理器 (`voice_manager.py`, 387 行)

**架构**：
```
RealtimeVoiceManager(QWidget)
    ├── QThread: _RecordingThread
    │   ├── sounddevice 录音 (16kHz, mono, int16)
    │   ├── Silero VAD 语音活动检测
    │   ├── 能量 VAD (备用，Silero 不可用时)
    │   ├── 静音超时断句 (1.5秒)
    │   └── 写 WAV 文件
    │
    ├── QThread: _ASRWorker
    │   ├── 读取 WAV 文件
    │   ├── backend.asr.transcribe()
    │   └── 发射 speech_recognized 信号
    │
    ├── Signals:
    │   ├── speech_recognized(str)  ← ASR 识别完成
    │   ├── vad_state_changed(bool) ← 说话状态
    │   └── error_occurred(str)     ← 错误
    │
    └── 流程: start_listening() → VAD检测 → 静音断句 → ASR → 信号
```

**关键设计**：
- ASR 在独立 QThread 运行，不阻塞录音
- `stop_listening()` 只设标志 + 等待线程退出（≤2s），UI 不冻结
- 启动前检查 `backend` 是否已初始化

### 5.3 系统托盘管理器 (`tray_manager.py`, 163 行)

**功能**：
- 托盘图标（gugugaga_logo.ico）
- 右键菜单：显示窗口 / 开启录音 / 桌面宠物 / 退出
- 双击恢复窗口
- 关闭事件拦截（最小化到托盘 vs 退出）
- 后端初始化进度通知

### 5.4 全局快捷键管理器 (`hotkey_manager.py`, 169 行)

**默认快捷键**：

| 快捷键 | 动作 | 说明 |
|--------|------|------|
| Ctrl+Alt+R | toggle_record | 切换录音 |
| Ctrl+Alt+H | show_window | 显示/隐藏窗口 |
| Ctrl+Alt+P | toggle_pet | 切换桌面宠物 |
| Ctrl+Alt+S | stop_action | 停止当前操作 |

**实现**：pynput 键盘监听，配置持久化到 `app/cache/hotkey_config.json`。

### 5.5 桌面宠物 (`desktop_pet.py`, 195 行)

**特性**：
- 无边框透明窗口（`Qt.FramelessWindowHint` + `Qt.WindowTransparentForInput` 部分透传）
- Live2D 渲染在独立 QOpenGLWidget
- 可拖拽移动
- 右键菜单：返回主窗口 / 切换表情 / 退出宠物模式
- 点击交互：随机表情/动作
- 信号：`switch_to_main` / `pet_closed`

### 5.6 自动更新管理器 (`update_manager.py`, 213 行)

**流程**：
```
check_for_updates()
    → GitHub API: /repos/{owner}/{repo}/releases/latest
    → 版本比较 (semver)
    → 有更新 → emit check_done({has_update: True})
    → 用户确认 → download_release()
    → 保存到本地 → emit download_done(file_path)
```

**支持**：
- 跳过版本（`skip_version`）
- 打开发布页面
- 下载进度

### 5.7 性能管理器 (`perf_manager.py`, 236 行)

**功能**：
- 延迟后端初始化（`schedule_backend_init`）
- 内存监控：2500MB 警告 / 4000MB 严重
- 定期 GC（5 分钟间隔）
- 清理目标注册（`register_cleanup_target`）
- 页面资源追踪

### 5.8 双模式兼容 (`dual_mode_compat.py`, 159 行)

**功能**：
- 确保共享目录存在（`app/cache/`、`memory/`、`logs/`）
- Windows 命名互斥锁（单实例限制）
- WebUI 端口检测（提示共存但共享配置）
- 配置迁移（从 WebUI 模式继承配置）

### 5.9 音频频谱可视化 (`audio_visualizer.py`, 331 行)

**已实现但未集成**（v1.9.77 从对话页移除）。

**特性**：
- 32 频段 FFT 柱状图
- QPainter 绘制
- 渐变颜色 + 峰值指示器
- 主题循环
- 模拟模式（无音频时）

---

## 6. 后端交互方式

### 6.1 Python 直调（核心优势）

原生桌面模式**不启动 HTTP/WS 服务**，直接通过 Python 调用后端：

```python
# 对话页发送消息
result = self.window().backend.process_message(text)

# TTS 合成
audio_path = self.window().backend.speak(text)

# ASR 识别
text = self.window().backend.asr.transcribe(audio_path)

# 记忆操作
memories = self.window().backend.memory.retrieve(query)

# 训练
self.window().backend.trainer.start_training(config)
```

### 6.2 异步处理

由于 AIVTuber 的方法大多是同步阻塞的，原生桌面使用 **QThread + Signal** 机制：

```python
# 在 QThread 中调用后端
class _LLMWorker(QThread):
    response_received = Signal(str)

    def run(self):
        result = self.backend.process_message(self.text)
        self.response_received.emit(result)
```

### 6.3 与 WebUI 模式的兼容

原生桌面和 WebUI 模式共享：
- `app/config.yaml` — 配置文件
- `app/cache/api_keys.json` — API 密钥
- `app/cache/llm_preferences.json` — LLM 配置持久化
- `memory/` — 记忆数据
- `GPT-SoVITS/` — 声音训练数据

`DualModeCompat` 负责确保目录存在和配置迁移。

---

## 7. 主题系统

### 7.1 架构 (`native/gugu_native/theme.py`, 574 行)

```
AppColors (dataclass) — 暗色方案
    └── LightColors (AppColors) — 亮色方案

全局单例:
    _colors: AppColors
    _current_theme: Theme

API:
    get_colors() → AppColors         ← 获取当前颜色
    apply_theme(theme)               ← 切换主题
    get_global_qss() → str           ← 全局样式表
    get_chat_bubble_css() → str      ← 对话气泡 CSS
    register_theme_callback(cb)      ← 注册主题变更回调
```

### 7.2 颜色常量（暗色方案重点）

| 类别 | 常量 | 值 | 说明 |
|------|------|-----|------|
| 窗口 | window_bg | #1a1b2e | 主背景 |
| 卡片 | card_bg | #232438 | 卡片背景 |
| AI 气泡 | ai_bubble_bg | #2a2d3e | AI 消息底色 |
| 用户气泡 | user_bubble_bg | #4263eb | 用户消息品牌蓝 |
| 强调色 | accent | #4263eb | 主强调色 |
| 输入框 | input_bg | #1e1f34 | 输入框背景 |
| 主文字 | text_primary | #e8e8f0 | 主要文字色 |
| 辅助文字 | text_secondary | #9a9ab0 | 辅助文字色 |

### 7.3 主题切换机制

```python
# 在页面 __init__ 中注册回调
register_theme_callback(self._on_theme_changed)

# 回调中刷新样式
def _on_theme_changed(self):
    c = get_colors()
    self.setStyleSheet(f"background-color: {c.card_bg};")
```

### 7.4 对话气泡 HTML 生成

QTextEdit 使用 HTML 渲染对话内容，但 HTML 引擎有限制：
- ❌ 不支持 float / display / clear / max-width:calc / 不对称 border-radius
- ✅ 支持 background-color, color, margin, padding, border, border-radius, font-*, text-align

因此气泡定位使用 `<div align="left/right">` + `margin` 控制。

---

## 8. 构建与打包

### 8.1 PyInstaller 构建 (`native/build.bat`)

```bash
# 前置条件：Python 3.11
cd native
build.bat
```

**build.bat 流程**：
1. 检查 Python 3.11
2. 检查 PySide6 / live2d-py / qfluentwidgets
3. 运行 PyInstaller（从 gugu.spec）
4. 输出到 `dist/` 目录

### 8.2 Inno Setup 安装器 (`native/gugu_setup.iss`)

**特性**：
- LZMA2 压缩
- 中/英双语界面
- 桌面图标
- 开机自启注册表项
- 旧版本检测
- 安装目录：`{pf}\GuguGaga`

---

## 9. 当前状态与待改进项

### 9.1 功能完成度

| 页面/功能 | 完成度 | 说明 |
|-----------|--------|------|
| 对话页 | ⭐⭐⭐⭐ | 核心功能完整，流式回复+TTS+录音+Live2D |
| 训练页 | ⭐⭐⭐ | 基本可用，缺少精确进度反馈 |
| 记忆页 | ⭐⭐⭐ | 展示完整，后端 API 部分缺失 |
| 模型下载页 | ⭐⭐⭐⭐ | 功能完整 |
| 设置页 | ⭐⭐⭐⭐ | 10 个 Provider 配置完整 |
| 系统托盘 | ⭐⭐⭐⭐ | 功能完整 |
| 全局快捷键 | ⭐⭐⭐⭐ | 功能完整 |
| 桌面宠物 | ⭐⭐⭐ | 基本可用，缺少更多交互 |
| 自动更新 | ⭐⭐⭐ | 检测+下载可用，缺少自动安装 |
| 音频可视化 | ⭐⭐ | 已实现但未集成 |

### 9.2 P0 待改进（核心体验）

| # | 问题 | 影响 | 建议方案 |
|---|------|------|---------|
| 1 | 工具系统未激活 | LLM 无法使用 9 个内置工具 | 实施 Function Calling（见可行性报告） |
| 2 | 实时语音体验 | VAD 精度、降噪、断句 | 优化 VAD 参数 + 添加降噪 |
| 3 | 流式回复与 TTS 协调 | 逐句 TTS 有时延迟 | 优化句子分割 + 预加载 |

### 9.3 P1 待改进（功能完善）

| # | 问题 | 影响 | 建议方案 |
|---|------|------|---------|
| 4 | 记忆搜索/编辑不完整 | 用户无法有效管理记忆 | 完善 backend API + UI |
| 5 | 训练进度不精确 | 用户不知道训练到哪一步 | 解析更多训练日志格式 |
| 6 | MCP 工具集成 | 原生模式无 MCP 支持 | 添加 MCP 管理页面 |
| 7 | 对话历史管理 | 无搜索/导出/清除功能 | 添加对话历史管理 |
| 8 | 多窗口模式 | 无分离式窗口 | 支持 QDockWidget 拖出 |

### 9.4 P2 待改进（体验打磨）

| # | 问题 | 影响 | 建议方案 |
|---|------|------|---------|
| 9 | 音频可视化未集成 | 视觉反馈不足 | 作为可选组件集成到对话页 |
| 10 | 通知系统 | 无系统 Toast 通知 | 使用 QSystemTrayIcon.showMessage |
| 11 | 亮色主题不完善 | 亮色部分颜色不对 | 完善 LightColors 方案 |
| 12 | 快捷键自定义 UI | 只能通过代码改 | 添加快捷键设置界面 |
| 13 | 窗口位置记忆 | 每次启动居中 | 保存/恢复窗口位置和大小 |

### 9.5 P3 待改进（锦上添花）

| # | 问题 | 建议 |
|---|------|------|
| 14 | 多语言支持 | i18n 框架 |
| 15 | 插件系统 | 动态加载扩展 |
| 16 | 表情/动作编辑器 | 可视化配置 Live2D 表情映射 |
| 17 | 主题编辑器 | 可视化自定义颜色方案 |
| 18 | 多显示器优化 | 记住窗口所在显示器 |

---

## 10. 开发指南

### 10.1 添加新页面

```python
# 1. 创建 native/gugu_native/pages/new_page.py
from PySide6.QtWidgets import QWidget, QVBoxLayout
from gugu_native.theme import get_colors, register_theme_callback

class NewPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("newPage")
        register_theme_callback(self._on_theme_changed)
        self._setup_ui()

    def _setup_ui(self):
        c = get_colors()
        layout = QVBoxLayout(self)
        # ... 添加控件

    def on_backend_ready(self):
        """后端初始化完成回调 — 在此访问 self.window().backend"""
        pass

    def _on_theme_changed(self):
        """主题变更回调 — 刷新样式"""
        pass

# 2. 在 native/main.py 中注册
from gugu_native.pages.new_page import NewPage

# 在 _create_pages() 中添加
self.new_page = NewPage(self)
self.addSubInterface(self.new_page, FluentIcon.NEW_ICON, "新页面")
```

### 10.2 添加新 Widget 组件

```python
# 在 native/gugu_native/widgets/ 下创建
from PySide6.QtWidgets import QWidget
from gugu_native.theme import get_colors

class MyWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        c = get_colors()
        self.setStyleSheet(f"background-color: {c.card_bg};")
```

### 10.3 修改颜色/主题

**所有颜色定义在 `native/gugu_native/theme.py`**：

1. 修改 `AppColors` 类中的颜色常量（暗色方案）
2. 修改 `LightColors` 类中的颜色常量（亮色方案）
3. 如果需要新的颜色常量，添加到 `AppColors` 中

**不要在页面/组件中硬编码颜色值**，统一使用 `get_colors()` 获取。

### 10.4 访问后端

```python
# 在任何页面/组件中
backend = self.window().backend  # GuguGagaApp 实例

# 后端就绪检查
if hasattr(self.window(), '_backend_ready') and self.window()._backend_ready:
    # 安全使用后端
    pass
```

### 10.5 添加新的全局快捷键

1. 在 `native/gugu_native/widgets/hotkey_manager.py` 中添加新动作
2. 在 `native/main.py` 的 `_on_hotkey_triggered()` 中添加处理
3. 更新默认快捷键配置

### 10.6 调试原生桌面

```bash
# 直接运行，查看控制台输出
cd C:\Users\x\Desktop\ai-vtuber-fixed\native
python main.py

# 查看日志
type gugu_native.log

# Python 调试
python -c "from PySide6.QtWidgets import QApplication; print('PySide6 OK')"
python -c "import live2d; print('live2d OK')"
```

---

*本文档最后更新: 2026-05-05 | 适用版本: v1.9.82+*
