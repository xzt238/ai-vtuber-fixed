# 🏗️ 咕咕嘎嘎 AI-VTuber 原生桌面应用可行性报告

> ⚠️ **归档说明**：所有 5 个阶段均已执行完毕，PySide6 原生桌面应用已上线运行。本文档已移入归档，仅作决策历史参考。当前架构文档请参见 `guides/NATIVE_DESKTOP.md`。

> **版本**: v1.0 | **日期**: 2026-05-01 | **决策**: WebUI → 原生桌面应用

---

## 一、现状分析

### 1.1 当前架构

```
┌─────────────────────────────────────────────────┐
│  用户入口                                        │
│  ┌──────────────┐    ┌──────────────────────┐   │
│  │ WebUI 模式   │    │ 桌面模式 (pywebview) │   │
│  │ 浏览器访问    │    │ WebView2 壳          │   │
│  │ :12393       │    │ 本质还是网页          │   │
│  └──────┬───────┘    └──────────┬───────────┘   │
│         │                       │                │
│         └─────── HTTP/WS ───────┘                │
│                    │                             │
│         ┌──────────▼──────────┐                  │
│         │   Python 后端        │                  │
│         │   app/main.py       │                  │
│         │   app/web/__init__.py│                  │
│         │   HTTP:12393+WS:12394│                  │
│         └──────────────────────┘                  │
└─────────────────────────────────────────────────┘
```

### 1.2 当前前端规模

| 指标 | 数量 |
|------|------|
| index.html 总行数 | **11,362 行** |
| CSS（内联） | ~1,800 行 |
| JavaScript（内联） | ~7,800 行 |
| HTML 结构 | ~1,700 行 |
| UI 面板数 | **26 个** |
| 交互控件 | 331 个（按钮246 + 下拉22 + 输入60 + 文本域3） |
| WS 入站消息类型 | 31 种 |
| WS 出站消息类型 | 43+ 种 |
| HTTP 端点 | 12 个 |
| 外部 JS 库 | pixi.js + oh-my-live2d + Silero VAD + ONNX Runtime |

### 1.3 核心难点

| 组件 | 当前实现 | 原生化难度 |
|------|----------|------------|
| **Live2D 虚拟形象** | WebGL (pixi.js + oh-my-live2d) | ⭐⭐⭐⭐⭐ 最高 |
| **实时语音** | Web Audio API + Silero VAD (ONNX/WASM) | ⭐⭐⭐⭐ |
| **音频可视化** | Canvas + AnalyserNode | ⭐⭐ |
| **26个浮动面板** | DOM + CSS fixed/absolute | ⭐⭐⭐ |
| **流式对话** | WebSocket + DOM操作 | ⭐⭐ |
| **配置面板** | HTML表单 | ⭐ |
| **系统监控** | WS + 进度条/图表 | ⭐⭐ |

---

## 二、技术方案对比

### 2.1 方案总览

| 方案 | 技术 | 原生感 | 开发效率 | Live2D支持 | 跨平台 | 体积 |
|------|------|--------|----------|------------|--------|------|
| **A: PySide6 + live2d-py** | Python/Qt/OpenGL | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ live2d-py | Win/Mac/Linux | ~80MB |
| **B: Tauri 2.0 + 前端** | Rust+WebView+Vue | ⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ 复用现有 | Win/Mac/Linux | ~8MB |
| **C: Electron + 前端** | Node+Chromium | ⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ 复用现有 | Win/Mac/Linux | ~150MB |
| **D: Flutter Desktop** | Dart+Skia | ⭐⭐⭐⭐⭐ | ⭐⭐ | ❌ 需自研 | Win/Mac/Linux | ~40MB |

### 2.2 方案 A：PySide6 + live2d-py（推荐 ✅）

**架构**：
```
┌──────────────────────────────────────────────┐
│  PySide6 原生窗口                              │
│  ┌────────────────────────────────────────┐  │
│  │  主窗口 (QMainWindow)                   │  │
│  │  ┌──────────┐  ┌──────────────────┐   │  │
│  │  │ Live2D   │  │  右侧面板区       │   │  │
│  │  │ Widget   │  │  ┌────────────┐  │   │  │
│  │  │ (QOpenGL │  │  │ Chat Panel │  │   │  │
│  │  │ Widget)  │  │  │ Memory     │  │   │  │
│  │  │          │  │  │ Training   │  │   │  │
│  │  │          │  │  │ Settings   │  │   │  │
│  │  └──────────┘  │  └────────────┘  │   │  │
│  └────────────────────────────────────────┘  │
│                                               │
│  ┌──────┐  直接 Python 调用（不需要 HTTP/WS）  │
│  │ 后端  │◀── app.main.AIVTuber 实例直接引用   │
│  └──────┘                                     │
└──────────────────────────────────────────────┘
```

**优势**：
1. **真正原生体验**：系统原生窗口、菜单栏、托盘、通知、文件对话框
2. **零通信开销**：Python 直接调用后端，不需要 HTTP/WS 序列化/反序列化
3. **Live2D 原生渲染**：`live2d-py` + `QOpenGLWidget` 直接 OpenGL 渲染，比 WebGL 性能更好
4. **同语言生态**：前后端都是 Python，调试方便，类型安全
5. **PyQt-Fluent-Widgets**：Windows 11 Fluent Design 风格，现成美观组件库（16k ⭐）
6. **PyInstaller 打包**：已有经验，改造成本低

**Live2D 集成**：
- `live2d-py` 库支持 PySide6，通过 `QOpenGLWidget` 渲染
- 官方示例：`model.LoadModelJson()` → `QTimer` 驱动 `paintGL()` → `model.Update()/Draw()`
- 支持表情、动作、点击交互、口型同步
- **核心代码量**：Live2D Widget 约 200-300 行

**风险**：
1. **学习曲线**：PySide6 比 HTML/JS 复杂，布局系统需要适应
2. **开发周期**：26个面板需要逐个重建，预计 3-4 周核心开发
3. **live2d-py 成熟度**：社区项目（3.6k ⭐），但核心功能稳定
4. **QOpenGLWidget 限制**：某些显卡驱动可能有问题

### 2.3 方案 B：Tauri 2.0（折中方案）

**架构**：
```
┌──────────────────────────────────────┐
│  Tauri 原生壳 (Rust)                  │
│  ┌────────────────────────────────┐  │
│  │  WebView (系统原生)             │  │
│  │  Vue/React + 现有前端代码       │  │
│  │  Live2D 继续 WebGL             │  │
│  └────────────────────────────────┘  │
│  │ Rust 桥接 → Python 后端进程     │  │
└──────────────────────────────────────┘
```

**优势**：
1. **体积极小**（8MB vs Electron 150MB）
2. **可复用现有前端**：HTML/JS/Live2D 代码几乎不用改
3. **原生菜单栏、托盘、通知**
4. **安全**：Rust 层控制 API 访问

**劣势**：
1. **本质上还是网页**：不满足"实实在在的软件"需求
2. **需要 Rust 工具链**：编译环境配置复杂
3. **Python 桥接**：仍需 HTTP/WS 通信，只是壳变了

### 2.4 方案 C：Electron（不推荐）

- 150MB 体积，内存占用高
- 本质还是网页，不满足需求
- 唯一优势是生态成熟，但 Tauri 完全优于它

### 2.5 方案 D：Flutter Desktop（未来备选）

- 最接近"原生体验"的跨平台框架
- 但 Live2D 没有现成 Flutter 插件，需要自研 OpenGL 渲染
- Dart 语言需要全团队学习
- **不适合近期实施**，可作为 v3.0 考虑

---

## 三、推荐方案：A（PySide6 + live2d-py）分阶段实施

### 3.1 Phase 0：技术验证（3天）

**目标**：验证核心技术可行性

| 任务 | 验证内容 | 预期结果 |
|------|----------|----------|
| 0.1 | PySide6 + PyQt-Fluent-Widgets 安装运行 | Hello World 窗口 |
| 0.2 | live2d-py + QOpenGLWidget 加载 Hiyori 模型 | Live2D 原生渲染 |
| 0.3 | Python 直接调用 AIVTuber 后端 | 无需 HTTP/WS 即可对话 |
| 0.4 | QMediaPlayer / PyAudio 播放 TTS 音频 | 音频输出正常 |
| 0.5 | QSystemTrayIcon 系统托盘 | 托盘图标+右键菜单 |
| 0.6 | PyInstaller 打包 PySide6 应用 | 可生成 EXE |

**关键决策点**：Phase 0 完成后确认 Live2D 渲染效果和性能。如果 live2d-py 有致命问题，退回方案 B（Tauri）。

### 3.2 Phase 1：核心框架（1周）

**目标**：搭建主窗口框架 + Live2D + 对话功能

```
主窗口布局：
┌──────────────────────────────────────────────┐
│ 菜单栏: 文件 | 设置 | 视图 | 帮助             │
├──────────┬───────────────────────────────────┤
│          │  ┌─────────────────────────────┐  │
│ Live2D   │  │  对话面板 (ChatPanel)        │  │
│ 显示区   │  │  - 消息列表 (QListWidget)    │  │
│          │  │  - 流式文本显示              │  │
│ 380x480  │  │  - 输入框 + 发送按钮         │  │
│          │  └─────────────────────────────┘  │
│          │  ┌──────────┬───────────────────┐ │
│ 表情     │  │ TTS控制  │ STT控制           │ │
│ 动作     │  │ 引擎选择 │ 录音按钮          │ │
│ 按钮     │  │ 音色选择 │ 实时模式          │ │
│          │  └──────────┴───────────────────┘ │
├──────────┴───────────────────────────────────┤
│ 状态栏: 连接 | GPU | 版本                      │
└──────────────────────────────────────────────┘
```

**实现要点**：
- `QMainWindow` + `QDockWidget` 实现可拖拽面板
- Live2D Widget 作为中央组件
- Chat Panel 支持流式文本（QTextBrowser + 定时器追加）
- TTS/STT 控制面板直接调用后端方法

**后端调用方式（核心变革）**：
```python
# 旧方式（WebUI）：需要 HTTP/WS 通信
# ws.send(JSON.stringify({type: 'text', content: msg}))
# → Python HTTP server → 解析JSON → 调用方法 → 序列化结果 → WS返回 → JS更新DOM

# 新方式（原生）：直接 Python 调用
class ChatPanel(QWidget):
    def send_message(self, text):
        result = self.app.process_message(text)  # 直接调用！
        self.display_response(result)             # 直接更新UI！
```

### 3.3 Phase 2：功能面板迁移（2周）

**目标**：逐个迁移 26 个面板到原生组件

| 优先级 | 面板 | 原生组件 | 复杂度 |
|--------|------|----------|--------|
| P0 | 对话面板 | QTextBrowser + QLineEdit | 中 |
| P0 | TTS 控制 | QComboBox + QPushButton | 低 |
| P0 | STT/录音 | QPushButton + QComboBox | 中 |
| P0 | Live2D 控制 | QPushButton + QSlider | 低 |
| P0 | 设置面板 | QTabWidget + QFormLayout | 中 |
| P1 | 历史面板 | QTableWidget | 低 |
| P1 | 记忆面板 | QTreeWidget + QTabWidget | 中 |
| P1 | 训练面板 | QProgressBar + QFormLayout | 高 |
| P1 | 系统监控 | QProgressBar + QTimer | 低 |
| P2 | 文件浏览 | QFileSystemModel + QTreeView | 低 |
| P2 | MCP 面板 | QTableWidget + QPushButton | 中 |
| P2 | 工具可视化 | QGroupBox + QScrollArea | 中 |
| P2 | 音频可视化 | QOpenGLWidget + FFT | 高 |
| P2 | 视觉/OCR | QTabWidget + QLabel | 中 |
| P3 | 配置编辑 | QPlainTextEdit (YAML) | 低 |
| P3 | 宏编辑 | QTableWidget | 低 |
| P3 | 桌面宠物 | 透明无边框窗口 | 高 |

### 3.4 Phase 3：高级功能（1周）

| 功能 | 实现方案 |
|------|----------|
| 实时语音 | PyAudio + Silero VAD (Python版，非WASM) |
| 音频可视化 | QOpenGLWidget + numpy FFT |
| 桌面宠物 | QWidget 无边框透明窗口 + Live2D |
| 系统托盘 | QSystemTrayIcon |
| 全局快捷键 | QHotkey / pynput |
| 开机自启 | QSettings + Windows注册表 |
| 自动更新 | GitHub Releases API + QProgressDialog |
| 多窗口 | QMainWindow + QWidget 独立窗口 |

### 3.5 Phase 4：打磨发布（1周）

- PyInstaller 打包优化
- 安装向导 (NSIS / Inno Setup)
- 图标和品牌资源
- 性能优化和内存管理
- 双模式兼容（WebUI + 原生共存过渡期）

---

## 四、关键技术细节

### 4.1 Live2D 原生渲染

```python
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import QTimer
import live2d.v3 as live2d

class Live2DWidget(QOpenGLWidget):
    def __init__(self, model_path, parent=None):
        super().__init__(parent)
        self.model = None
        self.model_path = model_path
        
    def initializeGL(self):
        live2d.glewInit()
        self.model = live2d.LAppModel()
        self.model.LoadModelJson(self.model_path)
        
        # 动画定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(16)  # ~60 FPS
        
    def paintGL(self):
        live2d.clearBuffer()
        if self.model:
            self.model.Update()
            self.model.Draw()
            
    def resizeGL(self, w, h):
        if self.model:
            self.model.Resize(w, h)
    
    def set_expression(self, name):
        if self.model:
            self.model.SetExpression(name)
    
    def start_motion(self, group, index, priority=3):
        if self.model:
            self.model.StartMotion(group, index, priority)
```

### 4.2 后端直调（无需 HTTP/WS）

```python
class AIVTuberApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # 直接创建后端实例（不需要 web server）
        from app.main import AIVTuber
        self.backend = AIVTuber()
        
    def send_chat(self, text):
        """直接调用后端，无需序列化"""
        result = self.backend.process_message(text)
        # 直接更新 UI
        self.chat_panel.add_message('ai', result['text'])
        # 直接播放 TTS
        if result.get('audio'):
            self.audio_player.play(result['audio'])
```

### 4.3 实时语音（Python 原生）

```python
import pyaudio
import numpy as np

class RealtimeVoiceManager:
    def __init__(self, backend):
        self.backend = backend
        self.audio = pyaudio.PyAudio()
        self.vad = SileroVAD()  # Python 版 Silero VAD
        
    def start_listening(self):
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=512
        )
        while self.listening:
            data = stream.read(512)
            if self.vad.is_speech(data):
                self.backend.handle_realtime_audio(data)
```

### 4.4 PyQt-Fluent-Widgets 示例

```python
from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, 
    MessageBox, setTheme, Theme, 
    CaptionLabel, CardWidget, InfoBar
)

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("咕咕嘎嘎 AI-VTuber")
        self.setMinimumSize(1200, 800)
        
        # 导航侧栏
        self.addSubInterface(self.chat_page, FluentIcon.CHAT, "对话")
        self.addSubInterface(self.train_page, FluentIcon.MICROPHONE, "训练")
        self.addSubInterface(self.memory_page, FluentIcon.BOOK_SHELF, "记忆")
        self.addSubInterface(self.settings_page, FluentIcon.SETTING, "设置")
```

---

## 五、风险评估

### 5.1 高风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| live2d-py 不稳定/不维护 | Live2D 无法原生渲染 | Phase 0 先验证；备选：QWebEngineView 局部嵌入 |
| QOpenGLWidget 显卡兼容性 | 部分用户无法渲染 | 检测 OpenGL 版本，降级到 QWebEngineView |
| 开发周期超预期 | 功能延迟上线 | 分阶段交付，WebUI 并行维护 |

### 5.2 中风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| PySide6 打包体积大 | 分发不便 | UPX 压缩 + 在线安装包 |
| Silero VAD Python 版性能 | 实时语音延迟 | 可用 webrtcvad 替代；Silero 用 ONNX Runtime Python |
| 26 个面板重建工作量大 | 开发时间长 | 优先 P0，P2/P3 面板后期补 |

### 5.3 低风险

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| PyQt-Fluent-Widgets 样式覆盖 | 部分组件风格不统一 | 支持 QSS 自定义 |
| 多显示器 DPI 缩放 | 高 DPI 显示模糊 | Qt6 原生支持高 DPI |

---

## 六、工作量估算

| 阶段 | 时间 | 人力 | 关键产出 |
|------|------|------|----------|
| Phase 0: 技术验证 | 3天 | 1人 | 可运行的 Live2D + 对话 Demo |
| Phase 1: 核心框架 | 1周 | 1人 | 主窗口 + 对话 + TTS/STT |
| Phase 2: 面板迁移 | 2周 | 1-2人 | 全部 26 面板原生化 |
| Phase 3: 高级功能 | 1周 | 1人 | 实时语音 + 桌面宠物 + 可视化 |
| Phase 4: 打磨发布 | 1周 | 1人 | 打包 + 安装器 + 文档 |
| **总计** | **5-6周** | | |

### 与 WebUI 并行过渡

```
时间线：
Week 1-2: Phase 0 + Phase 1 → Demo 可用
Week 3-4: Phase 2 → 逐步替代 WebUI
Week 5:   Phase 3 → 高级功能
Week 6:   Phase 4 → 发布

过渡期策略：
- v2.0 同时保留 WebUI 和原生模式
- 启动时选择模式（或通过启动参数）
- 原生模式不启动 HTTP/WS 服务
```

---

## 七、结论

### ✅ 可行性结论：高度可行

1. **PySide6 + live2d-py** 是最符合需求的方案
2. Python 直接调用后端消除了 HTTP/WS 通信层
3. live2d-py 有完整的 PySide6 集成示例
4. PyQt-Fluent-Widgets 提供了 Windows 11 风格的现成组件
5. 开发周期 5-6 周，可分阶段交付

### ⚠️ 前提条件

1. **Phase 0 必须先通过**：Live2D 渲染是最大技术风险
2. **live2d-py 需要下载 Live2D Cubism SDK Core**：需要从 Live2D 官网手动下载（许可协议限制）
3. **开发过程中 WebUI 保持可用**：双模式并行过渡

### 📋 建议执行顺序

1. **立即**：Phase 0 技术验证（3天）
2. **验证通过后**：启动 Phase 1 核心框架
3. **Phase 1 完成后**：决定是否继续全面迁移
4. **如果 live2d-py 有致命问题**：退回 Tauri 方案（方案 B）
