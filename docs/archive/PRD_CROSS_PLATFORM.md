# 咕咕嘎嘎 AI VTuber — 跨平台适配 PRD

> 文档版本: v1.0 | 作者: Alice (Product Manager) | 日期: 2025-07-09
> 原始需求: 将当前 Windows-only 的咕咕嘎嘎 AI VTuber 适配到 macOS、Ubuntu/Linux、iOS、Android

---

## 1. 项目信息

| 字段 | 内容 |
|------|------|
| 语言 | 中文 |
| 当前技术栈 | Python 3.11 + PySide6/Qt6 + Live2D Native + GPT-SoVITS + FunASR + LLM + 四层记忆 |
| 当前平台 | Windows 10/11 only |
| 打包方式 | PyInstaller → EXE + 嵌入式 Python |
| 项目路径 | `ai-vtuber-fixed/` |
| 原始需求复述 | 将 Windows-only Python 3.11 + PySide6/Qt6 桌面应用适配到 macOS (Apple Silicon + Intel)、Ubuntu 22.04+、iOS、Android 四个平台 |

---

## 2. 产品目标

1. **核心体验跨平台一致性**：保证 ASR → LLM → TTS → Live2D 渲染的核心管线在四个目标平台上均可完整运行，用户感知的行为一致
2. **平台原生体验**：各平台使用符合该平台惯例的 UI 组件、打包方式、安装流程，而非强行统一
3. **渐进式交付**：先桌面（macOS/Linux）后移动（iOS/Android），降低技术风险和资源投入

---

## 3. 分阶段平台策略

### 阶段一：桌面平台（macOS + Linux）— 预计 3-4 个月

| 平台 | UI 方案 | 打包方案 | GPU | Live2D |
|------|---------|----------|-----|--------|
| **macOS (Apple Silicon)** | PySide6 + QWebEngineView | py2app / PyInstaller .app | MPS (PyTorch) | QWebEngineView + pixi.js + oh-my-live2d |
| **macOS (Intel)** | 同上 | 同上 | CPU / Intel GPU fallback | 同上 |
| **Linux (Ubuntu 22.04+)** | PySide6 + QWebEngineView | AppImage / .deb | CUDA / CPU | QWebEngineView + pixi.js + oh-my-live2d |

**桌面阶段策略**：保留 PySide6 框架，因为 Qt6 跨平台支持良好（macOS/Linux 均可运行），替换成本最低。

### 阶段二：移动平台（iOS + Android）— 预计 5-7 个月

| 平台 | UI 方案 | 打包方案 | GPU | Live2D |
|------|---------|----------|-----|--------|
| **iOS** | SwiftUI + WKWebView 容器 | Xcode .ipa | CoreML / CPU | WKWebView + pixi.js + oh-my-live2d |
| **Android** | Kotlin + Jetpack Compose + WebView 容器 | Gradle .apk/.aab | TFLite / CPU | WebView + pixi.js + oh-my-live2d |

**移动阶段策略**：不能直接用 PySide6。推荐 **混合架构**：原生壳（SwiftUI/Jetpack Compose）内嵌 WebView，Live2D 渲染在 WebView 中运行（pixi.js + oh-my-live2d），核心 AI 推理在设备端通过 ONNX Runtime 或 CoreML/TFLite 执行。

---

## 4. 关键技术挑战与解决方案

### 4.1 平台抽象层（最高优先级）

#### 挑战
项目中有大量 Windows 专有 API 调用：

| 文件 | Windows API | 用途 |
|------|------------|------|
| `launcher/launcher.py` | `ctypes.windll.kernel32.CreateMutexW` | 单实例互斥锁 |
| `launcher/launcher.py` | `ctypes.windll.user32.MessageBoxW` | 系统弹窗 |
| `launcher/launcher.py` | `taskkill /F /PID` | 进程终止 |
| `native/gugu_native/widgets/autostart_manager.py` | `winreg` (HKEY_CURRENT_USER) | 开机自启 |
| `native/gugu_native/widgets/perf_manager.py` | `ctypes.WinDLL('kernel32')` | 性能监控 |
| `native/gugu_native/widgets/dual_mode_compat.py` | `ctypes.WinDLL('kernel32').CreateMutexW` | 双模式互斥 |
| `app/main.py` | `subprocess.CREATE_NO_WINDOW` | 隐藏 CMD 窗口 |
| `app/main.py` | `subprocess.STARTF_USESHOWWINDOW` | 启动信息 |

#### 解决方案：创建 `app/platform_abstraction.py` 统一平台抽象层

```python
# 平台抽象层示例架构
class PlatformAbstraction:
    @staticmethod
    def create_mutex(name: str) -> Optional[Any]: ...
    @staticmethod
    def release_mutex(handle: Any) -> None: ...
    @staticmethod
    def show_message(title: str, message: str, level: str) -> None: ...
    @staticmethod
    def kill_process(pid: int) -> bool: ...
    @staticmethod    def set_autostart(enabled: bool) -> bool: ...
    @staticmethod
    def get_subprocess_args() -> dict: ...
```

| 平台 | 互斥锁 | 消息弹窗 | 进程终止 | 开机自启 | 子进程参数 |
|------|--------|----------|----------|----------|-----------|
| Windows | kernel32 CreateMutex | user32 MessageBox | taskkill | 注册表 | CREATE_NO_WINDOW |
| macOS | fcntl.lockf / posix_ipc | osascript dialog | kill -9 | LaunchAgent plist | {} |
| Linux | fcntl.lockf / posix_ipc | zenity/notify-send | kill -9 | systemd user / .desktop | {} |
| iOS | N/A (单实例) | UIAlertController | N/A | N/A | N/A |
| Android | N/A (单实例) | Snackbar/Dialog | N/A | N/A | N/A |

### 4.2 GPU 推理适配

#### 挑战
- 当前代码大量硬编码 `device="cuda"` 
- 训练流程强制 CUDA（`torch.cuda.is_available()`）
- 无 MPS (macOS) / Vulkan (Linux) / CoreML (iOS) / TFLite (Android) 支持

#### 影响范围

| 文件 | 问题 |
|------|------|
| `app/asr/__init__.py:788` | `"device": "cuda"` 默认值 |
| `app/main.py:407` | `"device": "cuda"` 硬编码 |
| `app/trainer/manager.py:350/1022-1023/1549/1554` | 训练流程强制 CUDA 检查 |
| `app/trainer/manager.py:1863-1864` | `CUDA_VISIBLE_DEVICES` 环境变量 |
| `GPT-SoVITS/` 子模块 | 大量 CUDA 专用算子 |

#### 解决方案

**推理侧（P0）**：创建 `app/device_manager.py` 统一设备选择：

```python
class DeviceManager:
    @staticmethod
    def get_best_device() -> str:
        if torch.cuda.is_available(): return "cuda"
        if torch.backends.mps.is_available(): return "mps"
        return "cpu"
```

**训练侧（P1）**：GPT-SoVITS 训练暂时仅支持 NVIDIA GPU（桌面端），移动端不提供训练功能，仅使用预训练模型推理。

**移动端推理（P2）**：将 GPT-SoVITS / FunASR 模型导出为 ONNX 格式，通过 ONNX Runtime 在移动端 CPU 上推理。

### 4.3 Live2D 渲染

#### 挑战
- `live2d-py` 是 C 扩展（.pyd），仅 Windows 有预编译版本
- QOpenGLWidget 方案在 macOS/Linux 上有兼容性问题

#### 当前状态
项目最新版本（v2.0+）已将 Live2D 渲染切换到 **QWebEngineView + pixi.js + oh-my-live2d** 方案，`live2d-py` 已降级为可选依赖。

#### 解决方案

| 平台 | Live2D 方案 | 状态 |
|------|------------|------|
| Windows | QWebEngineView + pixi.js (当前) | ✅ 已实现 |
| macOS | QWebEngineView + pixi.js | ✅ Qt6 QWebEngineView 在 macOS 上原生支持 WebGL |
| Linux | QWebEngineView + pixi.js | ✅ Qt6 QWebEngineView 在 Linux 上原生支持 WebGL |
| iOS | WKWebView + pixi.js | ⚠️ 需验证 WKWebView WebGL 性能 |
| Android | WebView + pixi.js | ⚠️ 需验证 Android WebView WebGL 性能 |

**结论**：Live2D 渲染是最不需要担心的部分——Web 方案天然跨平台。

### 4.4 路径与文件系统

#### 挑战
- 部分代码使用反斜杠路径
- `.bat` 脚本仅 Windows 可用
- 配置文件路径硬编码

#### 解决方案
- 全量审核并替换为 `pathlib.Path`
- 创建对应 `.sh` 脚本用于 Unix 平台（go.sh、setup.sh、desktop.sh）
- 配置文件和数据目录遵循各平台惯例：

| 平台 | 配置目录 | 数据目录 |
|------|----------|----------|
| Windows | `%APPDATA%/GuguGaga/` | 项目目录下 |
| macOS | `~/Library/Application Support/GuguGaga/` | `~/Library/Application Support/GuguGaga/` |
| Linux | `~/.config/gugugaga/` | `~/.local/share/gugugaga/` |
| iOS | App Sandbox | App Sandbox |
| Android | `context.getFilesDir()` | `context.getFilesDir()` |

### 4.5 桌面端 UI 适配（PySide6 跨平台）

#### 挑战
- `PySide6-Fluent-Widgets` 主要面向 Windows 11 Fluent Design
- 系统托盘行为在 macOS/Linux 上有差异
- 开机自启机制不同

#### 解决方案
- PySide6 本身跨三个桌面平台，主要工作在于：
  - 移除 `qfluentwidgets` 依赖，改用原生 Qt 样式或使用 Material Design 主题
  - 系统托盘：macOS 原生支持、Linux 需 `libappindicator`
  - 全局快捷键：macOS 需辅助功能权限、Linux 需 X11/Wayland 适配

### 4.6 打包与分发

| 平台 | 推荐方案 | 替代方案 |
|------|----------|----------|
| Windows (现有) | PyInstaller → 目录分发 | NSIS 安装包 |
| macOS | **py2app** → .app Bundle | PyInstaller (有 Qt 问题) |
| Linux | **PyInstaller → AppImage** | .deb / Flatpak |
| iOS | Xcode Archive → .ipa | — |
| Android | Gradle → .apk/.aab | — |

**关键**: macOS 代码签名需 Apple Developer Program ($99/年)。iOS 分发必须通过 App Store 或 TestFlight。

### 4.7 嵌入式 Python

#### 挑战
当前 Windows 版通过 `scripts/setup.bat` 下载嵌入式 Python，此方案仅 Windows 有。

#### 解决方案

| 平台 | Python 分发方案 |
|------|----------------|
| macOS | 使用系统 Python 3.11 或 pyenv，或通过 py2app 捆绑 |
| Linux | 使用系统 Python 3.11 或 pyenv |
| iOS | **不使用 Python**，移动端用原生语言重写核心模块 |
| Android | **不使用 Python**，移动端用原生语言重写核心模块 |

---

## 5. 移动端技术栈选型

### 推荐：混合原生架构

```
┌─────────────────────────────────────────┐
│  原生壳 (SwiftUI / Jetpack Compose)      │
│  ┌───────────────────────────────────┐  │
│  │  WebView                          │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │ pixi.js + oh-my-live2d      │  │  │
│  │  │ (Live2D 渲染层)              │  │  │
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  原生 AI 推理层                    │  │
│  │  CoreML (iOS) / TFLite (Android)  │  │
│  │  使用 ONNX 导出的模型              │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  原生 UI (设置/对话列表等)          │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### 为什么不用 React Native / Flutter？

| 方案 | 优势 | 劣势 |
|------|------|------|
| **React Native** | 代码复用高、生态丰富 | WebView 集成复杂、JS Bridge 开销 |
| **Flutter** | 高性能渲染、单代码库 | WebView 插件在 iOS/Android 上行为不一致、Dart 生态有限 |
| **原生 + WebView（推荐）** | 最佳性能、原生平台特性完整 | 需维护两套原生代码 |

**推荐原生 + WebView**：核心原因是 Live2D 渲染需要高性能 WebGL，而 AI 推理需要直接访问平台加速框架（CoreML/TFLite）。原生方案性能最优且可充分利用平台特性。

---

## 6. P0/P1/P2 需求池

### P0 — 必须实现（阻塞发布）

| ID | 需求 | 平台 | 说明 |
|----|------|------|------|
| P0-01 | **平台抽象层** | 全平台 | `app/platform_abstraction.py`，封装所有 Windows API 调用 |
| P0-02 | **路径规范化** | 全平台 | 全量替换为 `pathlib.Path`，移除反斜杠硬编码 |
| P0-03 | **GPU 设备自动检测** | macOS/Linux | MPS / CUDA / CPU 自动选择，移除 `"cuda"` 硬编码 |
| P0-04 | **PySide6 macOS 适配** | macOS | Qt6 QWebEngineView 在 macOS 上的编译和运行 |
| P0-05 | **PySide6 Linux 适配** | Linux | Qt6 QWebEngineView 在 Linux (X11/Wayland) 上的运行 |
| P0-06 | **Unix 启动脚本** | macOS/Linux | go.sh、desktop.sh、setup.sh（替代 .bat） |
| P0-07 | **打包方案验证** | macOS/Linux | py2app (.app) / AppImage 可运行版本 |
| P0-08 | **subprocess 跨平台** | 全平台 | 移除 `CREATE_NO_WINDOW`、`STARTF_USESHOWWINDOW` 等 Windows 标志 |
| P0-09 | **单实例互斥锁跨平台** | macOS/Linux | fcntl / posix_ipc 替代 kernel32 Mutex |

### P1 — 应该实现（影响体验）

| ID | 需求 | 平台 | 说明 |
|----|------|------|------|
| P1-01 | **系统托盘跨平台** | macOS/Linux | macOS 原生托盘、Linux libappindicator |
| P1-02 | **自动更新跨平台** | macOS/Linux | Sparkle (macOS) / AppImageUpdate (Linux) |
| P1-03 | **开机自启跨平台** | macOS/Linux | LaunchAgent / systemd user service |
| P1-04 | **全局快捷键跨平台** | macOS/Linux | macOS 辅助功能权限、Linux X11/Wayland |
| P1-05 | **macOS 代码签名** | macOS | Apple Developer 证书、Notarization |
| P1-06 | **GPT-SoVITS 训练 CPU fallback** | macOS/Linux | 训练支持 CPU 模式（速度慢但可用） |
| P1-07 | **GPU 推理 MPS 适配验证** | macOS | PyTorch MPS 后端在 ASR/TTS/LLM 推理中的验证 |
| P1-08 | **移动端需求调研与原型** | iOS/Android | 验证 WebView + pixi.js + oh-my-live2d 在移动端表现 |

### P2 — 可以后续实现（锦上添花）

| ID | 需求 | 平台 | 说明 |
|----|------|------|------|
| P2-01 | **iOS 原生应用** | iOS | SwiftUI + WKWebView + CoreML 推理 |
| P2-02 | **Android 原生应用** | Android | Jetpack Compose + WebView + TFLite 推理 |
| P2-03 | **模型 ONNX 导出** | 全平台 | GPT-SoVITS / FunASR 模型导出为 ONNX 格式 |
| P2-04 | **移动端离线推理** | iOS/Android | 设备端 ASR/TTS/LLM 推理（小模型） |
| P2-05 | **桌面宠物跨平台** | macOS/Linux | 无边框透明窗口在 macOS/Linux 上的实现 |
| P2-06 | **动态性能调节** | 全平台 | 根据平台能力和电池状态自动调整模型精度 |
| P2-07 | **VRM 3D 模型跨平台支持** | macOS/Linux | VRM 渲染在非 Windows 平台的支持 |

---

## 7. 风险评估

| 风险 | 严重度 | 概率 | 缓解措施 |
|------|--------|------|----------|
| **GPT-SoVITS 训练仅支持 CUDA** | 高 | 确认 | 移动端不提供训练；桌面端 macOS/Linux 仅提供 CPU 训练模式 |
| **live2d-py 无 macOS/Linux 预编译** | 中 | 低 | 项目已切换到 Web 渲染方案，不依赖 live2d-py |
| **PySide6 QWebEngineView macOS 打包体积** | 中 | 高 | py2app 捆绑 Qt6，预计 .app 体积 300-500MB |
| **macOS 签名/公证成本** | 中 | 确认 | $99/年 Apple Developer Program |
| **移动端 AI 推理性能** | 高 | 高 | 第一阶段使用云端 API；第二阶段 ONNX 导出 + 量化 |
| **Wayland 兼容性** | 低 | 中 | Qt6 已支持 Wayland，但有已知问题，保留 X11 fallback |
| **Apple Silicon Rosetta vs Native** | 中 | 低 | PyTorch 已原生支持 MPS，需确保依赖链全链路 ARM64 |
| **iOS App Store 审核** | 中 | 中 | AI 模型合规、隐私说明、沙盒限制 |

---

## 8. 架构演进路线图

```
当前 Windows-only
    │
    ▼ 阶段一（3-4个月）
┌─────────────────────────────┐
│  跨平台桌面 (v2.x)           │
│  ✅ macOS (Apple Silicon)   │
│  ✅ macOS (Intel)           │
│  ✅ Ubuntu 22.04+           │
│                             │
│  核心变化:                   │
│  - 平台抽象层                │
│  - MPS/CUDA/CPU 自动选择     │
│  - pathlib 全量替换          │
│  - py2app + AppImage 打包   │
│  - .sh 脚本                 │
└─────────────────────────────┘
    │
    ▼ 阶段二（5-7个月）
┌─────────────────────────────┐
│  移动平台 (v3.x)             │
│  ✅ iOS (SwiftUI + WebView) │
│  ✅ Android (Kotlin + WebView) │
│                             │
│  核心变化:                   │
│  - 原生壳 + WebView 容器     │
│  - 设备端 ONNX 推理          │
│  - CoreML / TFLite 后端     │
│  - 移动端 UX 重设计          │
└─────────────────────────────┘
```

---

## 9. 竞品简析

| 竞品 | 平台 | 优势 | 劣势 | 对咕咕嘎嘎的启示 |
|------|------|------|------|-----------------|
| **VTube Studio** | Win/Mac/iOS/Android | Live2D 渲染成熟、手机面捕 | 无 AI 对话功能 | 移动端可参考其 WebView 架构 |
| **VRoid Mobile** | iOS/Android | 3D 模型跨平台 | 无 Live2D、无 AI 对话 | 移动端 3D 渲染方案参考 |
| **VTuber Maker** | iOS/Android | 手机端全功能 | 无 GPT-SoVITS 级声音克隆 | 移动端功能集参考 |
| **VSeeFace** | Windows only | 3D VRM + 面捕 | 无跨平台 | 功能对标但需跨平台 |
| **PrprLive** | Windows/Mac | Live2D + 面捕 | Mac 版功能受限 | macOS Live2D 方案参考 |

**核心竞争力**: 咕咕嘎嘎的 GPT-SoVITS 声音克隆 + 训练面板 + 多层记忆系统 + Function Calling 在当前竞品中属于独有功能组合，跨平台后将形成显著差异化优势。

---

## 10. Open Questions

1. **macOS 上 PySide6 + QWebEngineView 的实际性能**：需在 M1/M2/M3 上实际测试 WebGL 渲染 Live2D 的帧率和功耗
2. **移动端是否保留 GPT-SoVITS 本地推理**：ONNX 导出的 GPT-SoVITS 模型在移动端 CPU 上的推理延迟是否可接受（目标 < 2s）
3. **Linux 分发的目标格式**：优先 AppImage 还是 Flatpak？需调研目标用户偏好
4. **iOS/Android 是否需要桌面宠物模式**：移动端桌面宠物概念不同（Widget？悬浮窗？）
5. **移动端 LLM 是否完全依赖云端 API**：还是支持 Ollama 等本地 LLM（移动端运行 LLM 目前不现实）
