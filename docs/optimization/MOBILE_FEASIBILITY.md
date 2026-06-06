# GuguGaga AI VTuber — iOS/Android 适配可行性分析

> 2026-05-25 | v1.0

## 总体结论

| 平台 | 可行性 | 推荐方案 | 工作量 |
|------|--------|----------|--------|
| **iOS** | ✅ 可行 | SwiftUI + WKWebView + 云端 API | 5-7月 |
| **Android** | ✅ 可行 | Kotlin Compose + WebView + 云端 API | 5-7月 |

**核心策略：薄原生壳 + WebView 渲染 + 云端 AI。不移植 Python 后端。**

---

## 1. 为什么不能用 Python 方案？

| 方案 | iOS | Android | 问题 |
|------|-----|---------|------|
| PySide6/Qt6 | ❌ | ❌ | 无移动端支持 |
| Kivy | ✅ | ✅ | UI 丑陋、Live2D/VRM WebView 集成复杂 |
| BeeWare | ⚠️ | ✅ | 性能差、生态小、调试困难 |
| Chaquopy | — | ⚠️ | 仅 Android、PyTorch 不支持 |

**结论：Python 移动端路线不可行，必须用原生方案。**

---

## 2. 架构方案：「薄壳模式」

```
┌─────────────────────────────────────────────┐
│  原生 Shell (SwiftUI / Jetpack Compose)     │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  WebView Container                    │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │ HTML5 + pixi.js + pixi-live2d   │  │  │
│  │  │         (Live2D 渲染)           │  │  │
│  │  │  or                             │  │  │
│  │  │ HTML5 + three.js + three-vrm   │  │  │
│  │  │         (VRM 3D 渲染)          │  │  │
│  │  └─────────────────────────────────┘  │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  原生层负责：                                │
│  - WKWebView/WebView 容器                   │
│  - 系统 ASR/STT (iOS Speech / Google)       │
│  - 音频播放                                  │
│  - 设置/Tab 导航                            │
│  - 通知 / 后台模式                          │
│                                             │
│  云端负责：                                  │
│  - LLM 对话 (OpenAI/MiniMax API)            │
│  - TTS 语音合成 (API 或自建服务)             │
│  - 记忆系统 (自建后端)                       │
└─────────────────────────────────────────────┘
```

---

## 3. 逐模块适配分析

### 3.1 Live2D 渲染 ✅ 完全可行

| 组件 | 桌面端 | 移动端 |
|------|--------|--------|
| 技术 | QWebEngineView + pixi.js | WKWebView(iOS) / WebView(Android) + pixi.js |
| WebGL | ✅ 三平台原生支持 | ✅ iOS WKWebView / Android WebView 均支持 |
| 性能 | 60fps | 30-60fps（移动端 GPU 略弱但够用） |

**复用**：`app/web/static/` 下的所有 HTML/JS 可直接复用，pixi-live2d CDN 加载。

**参考**：VTube Studio (iOS/Android) 已成功使用此方案。

### 3.2 VRM 3D 渲染 ✅ 完全可行

| 组件 | 桌面端 | 移动端 |
|------|--------|--------|
| 技术 | QWebEngineView + three.js | WKWebView/WebView + three.js |
| WebGL | ✅ | ✅ three.js r136+ 兼容 iOS Safari/Android Chrome |
| 模型 | 47MB .vrm | 需压缩或按需下载 |

**复用**：`native/gugu_native/widgets/vrm_widget.py` 中的 HTML 模板完全可移。

### 3.3 LLM 对话 ✅ 完全可行

| 方案 | 说明 |
|------|------|
| **云端 API（推荐）** | 直接用 OpenAI/MiniMax/DeepSeek API，桌面端已有 10+ Provider 切换逻辑 |
| **本地推理** | 不需要，移动端跑 LLM 不现实（内存/算力不足） |

### 3.4 语音识别 (ASR) ✅ 可行

| 方案 | iOS | Android |
|------|-----|---------|
| **系统原生（推荐）** | `SFSpeechRecognizer` | `SpeechRecognizer` |
| 云端 API | Whisper API | Whisper API |

系统原生方案零成本、低延迟、离线可用。

### 3.5 语音合成 (TTS) ⚠️ 需改方案

| 方案 | 可行性 |
|------|--------|
| **GPT-SoVITS 本地推理** | ❌ 需要 PyTorch + GPU，移动端完全不可行 |
| **GPT-SoVITS 部署为云服务** | ✅ 自建 GPU 服务器，移动端调 API |
| **系统原生 TTS** | ✅ iOS AVSpeechSynthesizer / Android TTS |
| **第三方 API** | ✅ ElevenLabs / MiniMax TTS API |

**推荐**：自建 GPT-SoVITS 云服务（桌面端已有的模型直接暴露 API），移动端调接口。

### 3.6 记忆系统 ✅ 需改造

| 当前 | 移动端方案 |
|------|-----------|
| Python MemorySystem（72KB） | 不能直接移植 |
| 四层架构（工作/情景/语义/事实） | 改为云端服务：记忆 API + 本地缓存 |

**方案**：
- 所有对话历史通过云端 API 存储
- 语义搜索通过向量数据库（服务端）
- 本地只缓存最近会话

### 3.7 口型同步 ✅ 可行

| 桌面端 | 移动端 |
|--------|--------|
| QTimer 50ms 轮询 + Live2D mouth_open | JS 定时器 + WebView Bridge |

---

## 4. 不可移植的模块

| 模块 | 原因 | 替代方案 |
|------|------|----------|
| GPT-SoVITS 训练 | GPU 训练流程 | 桌面端训练 → 导出模型 → 云服务部署 |
| GPT-SoVITS 推理 | PyTorch 2GB+ | 云端 API 或 ONNX Lite |
| FunASR/Faster-Whisper | PyTorch 依赖 | 系统原生 ASR |
| Vision 视觉理解 | GPU + 大模型 | 不需要（移动端用相机实时画面） |
| Function Calling | Python subprocess | 不需要（移动端沙盒限制） |
| 桌面宠物 | Qt 悬浮窗 | 移动端不需要 |

---

## 5. 可行性评分

| 模块 | 可行性 | 复杂度 | 备注 |
|------|--------|--------|------|
| UI 框架 | ✅ 100% | 🟢 低 | 原生 SwiftUI/Kotlin |
| Live2D 渲染 | ✅ 95% | 🟢 低 | WebView 直接复用 |
| VRM 3D 渲染 | ✅ 95% | 🟢 低 | WebView 直接复用 |
| LLM 对话 | ✅ 100% | 🟢 低 | 云端 API 直接调用 |
| 语音识别 | ✅ 90% | 🟢 低 | 系统原生 API |
| 语音合成 | ✅ 80% | 🟡 中 | 需部署云服务 |
| 记忆系统 | ✅ 80% | 🟡 中 | 需云服务 API |
| 口型同步 | ✅ 90% | 🟢 低 | JS 实现 |
| 面部捕捉 | ✅ 95% | 🟢 低 | ARKit(iOS) / CameraX(Android) |
| 变体切换 | ✅ 90% | 🟢 低 | WebView Bridge |
| 参数调节 | ✅ 90% | 🟡 中 | 原生 Slider → JS Bridge |

**综合可行性：82%**

---

## 6. 移动端功能集（MVP）

### Phase 2a — iOS/Android MVP（预计 3 月）

| 功能 | 优先级 |
|------|--------|
| 原生壳 (SwiftUI/Kotlin) + WebView | P0 |
| Live2D 模型加载 + WebGL 渲染 | P0 |
| 云端 LLM 对话 (复用现有 API 配置) | P0 |
| 系统语音识别 (iOS Speech / Android) | P0 |
| TTS 语音合成 (云端 API) | P0 |
| 口型同步 | P0 |
| ARKit 面部捕捉 (iOS) / CameraX (Android) | P0 |
| 对话历史 | P1 |
| VRM 3D 渲染 | P1 |
| 模型变体切换 | P1 |
| 记忆系统 (云端) | P1 |

### Phase 2b — 进阶（预计 3-4 月）

| 功能 | 优先级 |
|------|--------|
| GPT-SoVITS 云端声音克隆服务 | P2 |
| 设备端小模型推理 (ONNX Lite) | P2 |
| 离线模式（缓存对话 + 简化 TTS） | P2 |
| 照片/视频分享 | P2 |

---

## 7. 成本估算

| 项目 | 预估 |
|------|------|
| iOS 开发（2-3 月全职） | SwiftUI + WebView + ARKit 面捕 |
| Android 开发（2-3 月全职） | Kotlin Compose + WebView + CameraX |
| 云服务部署 | GPT-SoVITS API 服务器 (GPU) $200-500/月 |
| Apple Developer | $99/年 |
| Google Play | $25 一次性 |
| iOS App Store 审核 | 需合规文档（隐私/内容审核） |

---

## 8. 建议

1. **先做 macOS/Linux 桌面端**（Phase 1，当前进行中），验证跨平台抽象层
2. **同步开发云端记忆 + TTS API**（桌面端和移动端共用）
3. **移动端先做 iOS**（ARKit 面捕成熟、设备统一），再做 Android
4. **MVP 聚焦对话交互**（Live2D + LLM + TTS + 面捕），不做 VRM、训练、设置页
