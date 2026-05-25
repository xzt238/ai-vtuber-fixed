# 📋 咕咕嘎嘎 AI-VTuber 版本管理

# ============================

## 📌 版本号格式

# version: 主版本.次版本.修订号

# 示例: v1.0.0 → v1.1.0 → v1.1.1

# 

# 主版本(X.0.0): 重大功能新增、架构重构、API不兼容

# 次版本(0.X.0): 功能改进、模块优化、新增模块

# 修订号(0.0.X): Bug修复、小改动、文档更新

## 📌 更新类型标记

|标记|类型|说明|
|-|-|-|
|✨ 新增|new|新功能、 新模块|
|🔧 修复|fix|Bug修复、问题修复|
|🐛 优化|opt|性能优化、代码优化|
|🔐 安全|sec|安全加固|
|📝 文档|doc|文档更新|
|🔄 重构|refactor|重构代码|
|⚡ 性能|perf|性能提升|

## 📌 版本状态

|状态|说明|
|-|-|
|🔴 DEV|开发中|
|🟡 BETA|测试中|
|🟢 STABLE|稳定版|


## 🟢 v1.11.2 (2026-05-25) ✅ STABLE

**修复 Windows 启动脚本编码错误**

### 🔧 修复
- **[scripts] 重写 start.bat / go.bat**：sed 批量替换导致中文注释乱码 + 行尾截断，改纯 ASCII 注释
- **[version] v1.11.2**

## 🟢 v1.11.1 (2026-05-25) ✅ STABLE

**模型导入系统 + AI 伴侣竞品对比**

### 🔧 新增
- **[model] 模型导入系统**：用户可加载任意 VRM/Live2D 模型文件，自动复制到模型目录并立即生效
- **[model] 加载VRM模型按钮**：文件选择器 → 复制 → 注册 → 直接显示
- **[model] 加载Live2D模型按钮**：文件夹选择 → 复制 → 扫码 .model3.json → 加载
- **[vrm] AI 伴侣竞品深度对比**：8 个 AI 伴侣/女友项目对比分析 + 差距评估 + SWOT

### 🔧 修复
- **[version] v1.11.1**

## 🟢 v1.11.0 (2026-05-25) ✅ STABLE

**跨平台适配 Phase 1：macOS/Linux 基础设施**

### 🔧 新增
- **[platform] 新建 `app/device_manager.py`**：GPU 自动检测（CUDA→MPS→CPU），消除全项目 `"cuda"` 硬编码
- **[platform] 新建 `app/platform_abstraction.py`**：封装互斥锁/进程终止/子进程/开机自启/消息弹窗的平台差异
- **[platform] Unix 启动/安装脚本**：`scripts/go.sh` + `scripts/setup.sh`
- **[vrm] VRM 设置页**：16 参数实时调节面板（姿态/位置/光照/背景/动画），分组滑块
- **[vrm] 变体切换**：4 种 VRM 形态按钮（AU/cow/jacket/swim），加载新模型前自动卸载旧模型
- **[docs] 竞品分析报告**：37 功能×9 竞品对比矩阵 + 差距分析 + 优势分析
- **[docs] 移动端可行性分析**：iOS/Android 适配方案（82% 可行）

### 🔧 修复
- **[platform] 修复 `trainer/manager.py`**：硬编码 `C:\Users\x\...` 路径 → `sys.executable`
- **[platform] 修复 `vision/__init__.py`**：4 处 `.cuda()` / `device_map` → `DeviceManager`
- **[platform] 修复 `asr/__init__.py`**：默认 device `"cuda"` → `"auto"` 动态检测
- **[platform] 修复 `autostart_manager.py`**：winreg → platform_abstraction 跨平台
- **[vrm] 修复手臂 T-pose**：加载后自动下垂至自然位置
- **[vrm] 修复材质全白**：从原始 glTF 抢救贴图到 VRM 材质
- **[vrm] 修复缩放变暗**：主光亮度随距离等比补偿
- **[version] v1.11.0**

## 🟢 v1.10.5 (2026-05-24) ✅ STABLE

**AI 日记 + VRM 渲染管线完善**

### 🔧 新增
- **[diary] AI 每日日记系统**：`app/diary.py`，每天 23:00 自动回顾当日对话写反思日记
- **[vrm] VRM 渲染管线全通**：three.js + three-vrm 0.6.10 本地化 + 透明背景
- **[vrm] 鼠标拖拽旋转 + 滚轮缩放**：VRM 模型交互
- **[vrm] 程序化待机动画**：正弦驱动骨骼（脊柱/头/手臂/胸部），速度/幅度/呼吸可调
- **[vrm] 实时参数调节面板**：保存后聊天模式自动加载

### 🔧 修复
- **[vrm] 修复 QWebChannel 时序竞争**：双标志模式保证 bridge 就绪后加载模型
- **[vrm] 修复 canvas 0x0**：init3D 延迟一帧确保 DOM 尺寸确定
- **[version] v1.10.5**

## 🟢 v1.10.4 (2026-05-23) ✅ STABLE

**VRM 3D 修复：GLTFLoader 404 + three-vrm API 适配**

### 🔧 修复
- **[vrm] 修复 GLTFLoader 404**：three.js 0.150.1 已删除 `examples/js/` 目录，降级至 0.136 + 从本地加载静态文件
- **[vrm] 修复 three-vrm API 不兼容**：适配 three-vrm 0.6.10（VRM 0.x），使用 `VRM.from()` + `blendShapeProxy` 替代 1.x 的 `VRMLoaderPlugin`
- **[vrm] 重写 HTML 模板**：加载失败时显示详细错误信息（依赖缺失 / GLTF 加载失败 / VRM 解析失败）
- **[vrm] 重生成 test model**：VRM 0.x 格式（`VRM` 扩展），含 BlendShape 'A'
- **[version] v1.10.4**（9 处同步更新）

## 🟢 v1.10.3 (2026-05-22) ✅ STABLE

**LLM 补齐 + VRM 3D 实验性支持**

### 🔧 新增
- **[llm] 新增 Google Gemini + OpenRouter**（12 个 LLM 供应商）
- **[vrm] VRM 3D 模型实验性支持**：`vrm_widget.py`（420行），QWebEngineView + three.js + three-vrm，与 Live2D 共用左侧面板。支持 .vrm 模型加载、BlendShape 表情、口型同步。
- **[webui] 设置页 + 新手引导新增 Gemini / OpenRouter 选项**
- **[docs] VRM 3D 模型可行性分析**
- **[version] v1.10.3**

## 🟢 v1.10.2 (2026-05-21) ✅ STABLE

**Native 桌面 Live2D — 迁移至 live2d-py + QOpenGLWidget**

### 背景
QWebEngineView + oh-my-live2d 存在架构级缺陷（Chromium 在已显示窗口插入后不自动合成），20+ 轮修复无效。迁移至 v1.x 的 live2d-py + QOpenGLWidget 原生渲染方案。

### 🔧 变更
- **[live2d] 重写 Live2DWidget**：从 QWebEngineView 工厂改为 `QOpenGLWidget` 直接类（423行），live2d-py v3 C 扩展 + OpenGL 原生渲染
- **[live2d] 透明背景**：`clearBuffer(0,0,0,0)` + `WA_TranslucentBackground` + `AlphaBufferSize=8`
- **[live2d] 眼神跟踪**：归一化坐标 [0,1] → `Drag/SetDragging` 每帧
- **[live2d] 首次加载比例修复**：模型加载后立即调用 `Resize(w, h)`，无需点击触发
- **[live2d] API 完全兼容**：3 信号 + 7 方法，chat_page.py 无需修改
- **[version] v1.10.2**：15 处统一版本号

## 🟡 v1.10.1 (2026-05-20) — 已废弃
- **[live2d] 布局正确性**：使用 `self._live2d_layout` 直接操作，`invalidate()` + `activate()` 确保几何传播；fallback 处理 `indexOf` -1。


## 🟡 v1.9.100 (2026-05-18) 🔄 BETA

**原生桌面模式性能优化 + Live2D 居中修复 + 启动速度提升 + 鼠标交互修复**

### ⚡ 性能
- **[startup] Live2D 延迟创建**：QWebEngineView 创建需要启动 Chromium 渲染进程（5-10 秒），是启动链路中最大的瓶颈。v11 将 Live2DWidget 的创建从 ChatPage.__init__ 移至窗口显示后 200ms 执行，窗口先用占位符显示，用户感知的启动时间从 20 秒缩短至 3-5 秒
- **[live2d] HTML 文件缓存**：`live2d_widget.html` 只在内容变化时才重新写入，避免每次创建 Live2DWidget 时的重复文件 I/O
- **[live2d] 模型加载延迟缩短**：从 500ms 缩短至 Live2D 组件创建后立即加载

### 🔧 修复
- **[live2d] v12: 修复 CSS transform 破坏鼠标交互**：v11 使用 CSS `translate(-50%,-50%) scale(fitScale)` 居中 canvas，但 CSS transform 会改变浏览器的鼠标坐标映射，导致 PixiJS EventSystem 接收到的坐标与视觉位置不一致 → 眼球跟踪偏移、点击区域错位。v12 改为专业 VTuber 方案：通过 `live2dApi.pixiApp.app` 访问 PixiJS Application，使用 `model.scale.set(fitScale)` + `model.x/y` 在 PixiJS 坐标系内居中模型，canvas CSS 填满容器无 transform，鼠标坐标 1:1 对应 → 交互正确。若 PixiJS Application 不可访问，自动降级到 v11 CSS transform 方案
- **[live2d] v11: 修复窗口缩放时不居中/变形**：v10 使用 `live2dApi.setStageStyle()/setScale()/setPosition()` API 居中模型，但这些 API 在不同版本的 oh-my-live2d 中行为不一致，导致窗口缩放时模型出现高矮胖瘦异常。v11 改为与 WebUI 完全一致的 CSS transform 方案（已在 v12 中升级为 JS-based 方案）
- **[live2d] 修复 Live2D 加载后守护定时器过度检查**：v10 的守护定时器 5 秒检查一次 slideOut，v12 改为 2 秒检查且同时检测 stage 定位 + 模型缩放/位置状态，首次检查在模型就绪后 300ms

### 🔄 重构
- **[live2d] v12: JS-based 居中方案**：通过 oh-my-live2d 内部的 PixiJS Application 直接操作模型，替代 CSS transform。自动降级机制确保兼容性
- **[live2d] v12: ResizeObserver**：新增 ResizeObserver 监听容器尺寸变化（比 window.resize 更可靠），配合 requestAnimationFrame 节流
- **[live2d] v12: 统一守护检查**：`_guardCheck()` 同时检查 stage 定位异常和模型缩放/位置异常（JS 方案下检查 canvas transform 是否被重置、model.scale 偏差是否 > 20%）


## 🟡 v1.9.99 (2026-05-17) 🔄 BETA

**版本号统一修复 + 未使用 TTS 引擎清理 + 冗余模型清理 + 配置去重 + Bug 修复**

### 🔧 修复
- **[live2d] 修复 Live2D 不跟随窗口缩放**：CSS `#oml2d-canvas { width:100%; height:100% }` 导致 `centerLive2DModel()` 计算 fitScale 始终为 1.0。移除该 CSS 规则，改用 transform 控制缩放。增加模型自然尺寸缓存（`_initModelW`/`_initModelH`），参照 native v8 版实现。增加 window.resize 监听和 ResizeObserver
- **[live2d] 修复 Live2D 不居中/比例异常**：同上，fitScale 计算错误导致模型显示异常
- **[tts] 修复 TTS 流式生成句子顺序错乱**：`playStreamBuffer()` 使用 `source.start(0)` 立即播放所有 chunk，导致同一句子内多个 chunk 重叠播放。改为按 AudioContext 时间线顺序调度（`_sentenceEndTime` 跟踪），确保 chunk 依次播放
- **[realtime] 修复实时沟通功能启动失败**：`startRealtime()` 在 VAD 初始化前设置 `realtime.active=true`，VAD 失败时状态不一致。改为 VAD 成功后才激活；增加麦克风权限预检查，提前报错；增加 WS 未连接提示；失败时恢复按钮状态
- **[llm] 修复 LLM 偶尔返回空值**：(1) Anthropic `result["content"][0]["text"]` 空 content 列表时 IndexError → 改为安全遍历；(2) OpenAI `choices` 空列表 → 保护性处理；(3) MiniMax 流式错误返回空文本 → 改为返回错误信息；(4) FC 执行失败且无文本 → 返回错误信息而非空字符串；(5) 流式 `_stream_error` 标记 → 调用方检查并通知前端
- **[version] 修复 9 处版本号不一致**：app/version.py 已是 v1.9.98，但以下文件仍使用旧版本号：native/build.bat (v1.9.90)、version_info.txt (1.9.90.0)、generate_icons.py (v1.9.90)、native/main.py fallback (1.9.90)、update_manager.py fallback (1.9.90)、scripts/go.bat (1.9.94)、scripts/start.bat (1.9.94)、launcher/splash.html (v1.9.82)、index.html 标题 (v1.9.82)。全部统一为 v1.9.98
- **[tts] 移除未使用的 ChatTTS 引擎**：删除 app/tts/chattts.py，从 TTSFactory 移除 chattts 分支，从原生桌面 chat_page 下拉框和 provider_map 移除 ChatTTS 选项，删除 _populate_chattts_voices_chat() 方法
- **[tts] 移除未使用的 CosyVoice 引擎**：删除 app/tts/cosyvoice.py，从 TTSFactory 移除 cosyvoice 分支，从原生桌面 chat_page 下拉框和 provider_map 移除 CosyVoice 选项，删除 _populate_cosyvoice_voices_chat() 方法
- **[docs] 清理 model_download_page.py 中的 chattts 引用**
- **[config] 修复 index.html _providerConfig 重复覆盖 bug**：L18 加载动态 /api/config.js，L7355 硬编码副本覆盖了动态版本。删除硬编码副本，将 hint/color 字段补入 shared_config.py，实现单一数据源
- **[config] 修复 index.html voiceOptions/expressionKeywords 重复定义**：删除硬编码副本，改由 /api/config.js 动态提供
- **[config] 更新 shared_config.py 注释**：删除"需手动同步"警告，改为"动态加载自动生效"
- **[setup] 清理 setup.py 中 ChatTTS 下载和验证逻辑**：移除 download_chattts_models() 函数、安装检查和模型下载步骤
- **[live2d] 修复 Live2D 比例异常**：`centerLive2DModel()` 未修复 `#oml2d-stage` 定位属性（Native 版已修复但 Web 版遗漏），oh-my-live2d 的 `reloadStyle()` 篡改 stage 样式导致模型移位和比例错误。现参照 Native 版增加 stage 定位修复；增加 canvas 尺寸有效性验证（<10px 不缓存）；增强守护定时器全面检测 stage 定位异常
- **[live2d] 修复 Live2D 不立即显示**：模型加载后 2500ms 硬编码延迟导致用户需等 2.5 秒才看到模型。改为事件驱动：轮询检测 canvas 渲染完成（50ms 间隔）+ 100ms 安全延迟，平均 <500ms 即可显示；3s 超时兜底
- **[perf] 优化 Live2D 启动速度**：①Live2D 库轮询 300ms→50ms（6s→3s 超时）②守护定时器 2s→1s 间隔③点击交互 3s→0.5s 延迟④加载覆盖层与 Live2D 就绪联动
- **[perf] 优化 Native 桌面模式 Live2D 启动**：同步 Web 版优化：库轮询 300ms→50ms、模型就绪检测从 2500ms 硬延迟改为事件驱动、守护定时器 2s→1s
- **[live2d] 修复 Native 模式 Live2D 缩放/比例异常**：CSS `#oml2d-stage { width:100%!important; height:100%!important }` 与 JS `stage.style.width = cw+'px'` 冲突，CSS `!important` 优先级高于 inline style 导致 JS 设置不生效。移除 width/height 的 `!important`，由 JS `centerLive2DModel()` 动态控制；增加 canvas 尺寸有效性验证（<10px 不缓存）；补齐 canvas 样式清理。Web 版 main.css 同步修复
- **[perf] 优化 Native 模式启动速度**：后端初始化延迟 2000ms→500ms；增加启动计时日志帮助诊断
- **[live2d] 修复 Native 模式 Live2D 容器尺寸震荡**：`ResizeObserver` + `window.resize` + 守护定时器三者互相触发形成反馈环，导致容器尺寸在 904×1373 ↔ 398×774 间震荡，模型反复重算居中。修复：①移除 ResizeObserver（与 window.resize 重复且触发反馈环）②增加容器尺寸变化阈值（<10px 不重算，消除微震荡）③防抖从 200ms 增至 300ms ④添加重入守卫防止并发 centerLive2DModel() ⑤守护定时器间隔从 1s 放宽到 3s ⑥降低居中日志噪音
- **[perf] 修复 Native 模式启动计时与加速**：①启动计时从 `__init__` 内移至 `main()` 入口，测量用户感知的真实启动时间（非仅构造函数耗时）②后端初始化延迟 500ms→100ms ③新增 "UI visible" 日志标记界面显示时间

### 🐛 优化
- **[tts] TTS 引擎精简**：从 4 个引擎（Edge/GPT-SoVITS/ChatTTS/CosyVoice）精简为 2 个（Edge/GPT-SoVITS），减少代码维护负担和启动时的冗余检测
- **[models] 删除冗余模型文件，释放 ~1.5GB 空间**：
  - G2PWModel_1.1.zip (562MB) — 下载残留压缩包
  - G2PWModel/g2pW.onnx (606MB) — 与 text/G2PWModel/g2pW.onnx 重复
  - s2D488k.pth / s2G488k.pth / s1bert25hz-*.ckpt (~340MB) — v1 预训练底模（项目使用 v3）
  - MiniCPM-V-2/assets/ (39MB) — 模型卡 GIF/PNG，非推理必需
  - VAD examples/tests (24MB) — Silero VAD 示例和测试文件
  - torch hub .partial (2MB) — 失败的下载残留
- **[models] 更新 GPT-SoVITS config.py 默认预训练路径**：从 v1 更新为 v3，匹配实际使用版本
- **[models] 更新 gptsovits.py 回退逻辑**：v1 底模引用改为 v3，确保加载失败时使用正确的回退模型
- **[models] 更新 tts_infer.yaml v1 默认路径**：指向 v3 模型文件


## 🟢 v1.9.97 (2026-05-17) ✅ STABLE

**Live2D 原生模式定位修复 — 根因：模型钉在左下角而非居中**

### 🔧 修复
- **[live2d] 修复 Live2D 模型在原生桌面模式中显示在左下角的问题**：根因是原生模式的 HTML 缺少 WebUI `main.css` 中的 `#oml2d-stage` CSS 覆盖。oh-my-live2d 默认使用 `position: fixed; bottom: 0; left: 0` 将模型钉在视口左下角（网页挂件行为），而 QWebEngineView 需要改为 `position: absolute; top: 0; left: 0; width: 100%; height: 100%; transform: none` 让模型在容器内居中渲染
- **[live2d] 修复窗口 resize 后 Live2D 模型消失/不居中的问题**：添加 `window.resize` 事件监听和 `ResizeObserver` 双重保障，QWebEngineView 大小变化时自动重新调用 `centerLive2DModel()` 重新计算居中位置
- **[live2d] 增强 `centerLive2DModel()` 函数**：不仅居中 PIXI canvas，还强制修复 `#oml2d-stage` 的定位属性（position/top/left/bottom/width/height/transform/animationName），防止 oh-my-live2d 的 `reloadStyle()` 在内部事件中重设 stage 样式导致模型移位
- **[live2d] 改进守护定时器**：从仅检测 transform 异常升级为全面检测 stage 定位异常（position/bottom/animationName/transform），一旦发现定位被篡改立即强制修复并重新居中

### 🐛 优化
- **[live2d] 添加 `#oml2d-canvas` CSS 覆盖**：`width: 100%; height: 100%` 确保画布跟随容器自适应


## 🟢 v1.9.96 (2026-05-17) ✅ STABLE

**对话显示修复 + Live2D 原生模式根本性修复**

### 🔧 修复
- **[native] 对话显示 [object Promise] 问题**：QWebChannel 的 Slot 方法在 JS 端总是返回 Promise，`renderMarkdownSync(text)` 返回 Promise 而非 HTML 字符串，直接赋值给 innerHTML 显示为 [object Promise]。改用 `.then()` 异步解包 Promise 结果。影响 `updateStreaming()` 和 `finishStreaming()` 两个函数
- **[live2d] QWebEngineView 中 document.currentScript 为 null 的根本修复**：v5 的 HTTP 重定向方案只修复了 WASM 文件路径，但 Emscripten 的 nr（脚本目录）仍为空，可能影响其他内部路径操作。v6 在脚本加载前 monkey-patch `Document.prototype.currentScript`，当真实值为 null 时返回带有正确 `src` 的假元素，从根源上解决 Emscripten 路径解析问题
- **[live2d] 修复 HTTP 服务器重复 Content-Type header**：`end_headers()` 对 .wasm 文件额外添加 `Content-Type: application/wasm`，但 `SimpleHTTPRequestHandler` 已通过 `mimetypes.guess_type()` 设置了相同的 header，导致响应包含两个 Content-Type 头，可能使 `WebAssembly.instantiateStreaming()` 失败。移除冗余 header
- **[live2d] 改进守护定时器**：不仅检测 slideOut（translateX(-100%)），还检测初始隐藏（translateY(130%)），通过解析 CSS matrix 中的平移值判断是否需要强制重置 stage 位置
- **[live2d] 增强诊断信息**：模型就绪检查时输出更详细的状态（models 的 keys、canvas 尺寸、currentScript patch 是否生效等）

## 🟢 v1.9.95 (2026-05-17) ✅ STABLE

**Live2D Web 渲染修复 — QWebEngineView 中模型显示问题彻底解决**

### 🔧 修复
- **[live2d] QWebEngineView 中 Live2D 模型不显示（核心修复）**：根因是 QWebEngineView 对 deferred script 不设置 document.currentScript，导致 oh-my-live2d 内部的 Emscripten 模块无法正确解析 WASM 文件路径（解析为 _em_module.wasm 而非 libs/_em_module.wasm），fetch 404，CubismCore 初始化失败，模型创建静默失败。修复方式：HTTP 服务器将根路径的 _em_module.wasm 请求重定向到 libs/_em_module.wasm
- **[live2d] 移除 Live2DCubismCore.locateFile 预配置**：之前版本在脚本加载前预设 window.Live2DCubismCore = { locateFile: ... }，导致 oh-my-live2d 跳过内置 CubismCore 初始化，模型创建失败。已移除此预设
- **[live2d] 简化模型就绪检测**：使用 setTimeout(2500) 代替轮询 models.model（与 WebUI 的 index.html 一致）
- **[live2d] 简化守护定时器**：与 index.html 一致，2s 间隔只检测 slide-out，移除 forceStagePosition()
- **[live2d] 移除 CSS !important 覆盖**：不覆盖 #oml2d-stage 的任何属性，让 oh-my-live2d 自由运行
- **[llm] 修复 content 类型处理**：OpenAI API content 字段可以是 list/dict 而非 string，添加类型检查（list→提取 text items，dict→提取 text 字段，str→直接使用）
- **[llm] 修复 _ollama_chat action 返回类型**：action 现在返回解析后的 dict（之前返回 JSON 字符串）
- **[llm] 修复 Function Calling 条件逻辑**：(finish_reason == "tool_calls" or tool_calls_accum) 恒为 True，修正为 tool_calls_accum and finish_reason == "tool_calls"

## 🟢 v1.9.90 (2026-05-07) ✅ STABLE

**全面代码审计 — 18 项 Bug 修复 + 版本号/配置集中化**

### ✨ 新增
- **[core] 版本号单一数据源** (`app/version.py`)：新建 `VERSION` 常量，所有代码文件从此处引用，杜绝 6 处硬编码版本号（曾出现 1.9.86/1.9.83/1.9.64 三个不同值）
- **[core] 共享配置集中化** (`app/shared_config.py`)：将 10 个 LLM 提供商配置、8 个 Edge TTS 语音、表情关键词映射、Windows Mutex 名称统一到一处，消除 `settings_page.py` 和 `index.html` 中的重复定义
- **[docs] 变更影响地图** (`docs/CHANGE_IMPACT_MAP.md`)：文档化"改一处需同步 N 处"的依赖关系，含 14 个变更类别和发布检查清单

### 🔧 修复
- **[llm] Function Calling 条件永远为 True**：`tool_calls_accum and (finish_reason == "tool_calls" or tool_calls_accum)` → `tool_calls_accum and finish_reason == "tool_calls"`，原逻辑因短路求值恒为 True，导致 FC 逻辑异常
- **[tts] 类变量被实例变量遮蔽**：`TTSBase._is_playing`/`_current_process`/`_current_audio_file` 是类变量用于跨实例共享播放状态，但 `self._is_playing = True` 创建了实例变量覆盖类变量，导致多实例状态不同步。改用 property 桥接到 `_cls_*` 类变量
- **[live2d] `os.chdir()` 污染进程工作目录**：`app/live2d/__init__.py` 用 `os.chdir(web_dir)` 切换目录启动 HTTP 服务器，影响整个进程的工作目录。改为 `SimpleHTTPRequestHandler(directory=web_dir)` 参数
- **[live2d] HTTP 服务器端口占用**：添加 `allow_reuse_address = True`，避免重启时 `Address already in use` 错误
- **[proactive] 主动说话未走历史截断**：`proactive.py` 直接 `self.app.history.append()` 绕过了 `record_interaction()` 的 MAX_HISTORY 截断逻辑，改为调用 `record_interaction("[主动说话触发]", reply)`
- **[native] 桌面宠物拖拽误触**：`desktop_pet.py` 鼠标释放时无论移动距离都触发点击动作，添加 `_drag_start_pos` 追踪，manhattan distance < 5px 才判定为点击
- **[native] 语音管理器死锁**：`voice_manager.py` 的 `_finalize_speech_segment` 在持有锁时 emit Qt 信号，若信号处理函数尝试获取同一把锁则死锁。改为先释放锁再 emit
- **[native] 播放状态信号泄漏**：`chat_page.py` 每次调用都 `connect` playbackStateChanged 信号但不先 `disconnect`，导致回调重复触发。改为先 disconnect 再 connect
- **[native] 唇形同步计时器泄漏**：`chat_page.py` 的 `_start_lipsync()` 未停止旧计时器就创建新的，导致多个定时器同时运行。添加 cleanup 逻辑
- **[native] 魔法时间戳**：`chat_page.py` 和 `main.py` 中硬编码 `'2026-05-07T19:35:00'` 时间戳，改为 `datetime.now().isoformat()`
- **[native] UpdateManager 版本比较不支持后缀**：`_compare_versions` 无法正确处理 `-hotfix` 等后缀版本号，重写比较逻辑
- **[native] Windows API 在非 Windows 平台崩溃**：`dual_mode_compat.py` 和 `perf_manager.py` 直接调用 `ctypes.windll`，添加 `sys.platform != "win32"` 保护
- **[native] Mutex 名称分散**：3 处各自定义 Mutex 名称字符串，改为从 `shared_config` 导入
- **[web] health 端点版本号硬编码**：`app/web/__init__.py` 健康检查端点中硬编码版本号，改为从 `app.version` 导入
- **[web] Edge TTS 语音列表不同步**：`index.html` 中的语音选项与 Python 端不一致（缺少 2 个语音），同步为 8 个语音
- **[web] 表情关键词重复**：`index.html` 中"哈哈"和"讨厌"重复定义，清理去重

### 🔄 重构
- **[native] settings_page 配置去重**：删除本地 `PROVIDER_CONFIG`/`EDGE_VOICES` 定义，改从 `app.shared_config` 导入
- **[native] update_manager 默认版本号**：硬编码 "1.9.64" 改为从 `app.version` 读取

## 🟢 v1.9.89 (2026-05-07) ✅ STABLE

**TTS 文本增强系统 v2 — 自动检测、中文特征、情绪扩散、统一清理**

### ✨ 新增
- **[tts] 自动检测情感词** (`_auto_detect_markers`)：LLM 未使用 `[laugh]` 标记时，自动从自然语言中检测"哈哈"/"嘻嘻"/"嘿嘿"/"呵呵"并插入 TTS 标记，确保笑声/情感仍被正确处理（受 `max_markers_per_reply` 限制）
- **[tts] 情绪扩散** (`_diffuse_emotion`)：让情感标记影响周围句子的语气——笑声后加～（轻松）、叹气后加……（低落）、惊讶后加！（强调）
- **[tts] 中文语言学增强** (`_enhance_chinese_features`)：句末语气词（嘛/啦/呀/喔/呢）、重复强调（好！→好好！）、口语填充词（我觉得→我觉得嗯，），使用确定性策略避免随机性
- **[tts] 文本增强配置** (`config.yaml text_enhancement`)：新增 `text_enhancement` 配置段，支持 style/auto_detect/chinese_features/emotion_diffusion/max_markers_per_reply 五项配置
- **[tts] Edge TTS 文本增强**：EdgeTTS.speak() 添加 enhance_text() 调用，[laugh] 等标记不再原样传给 Edge TTS

### 🔄 重构
- **[tts] 统一文本清理逻辑**：将 gptsovits.py 中重复的 markdown/emoji/连字符/连续标点清理全部合并到 text_enhancer.py，gptsovits.py 仅保留引擎特定兜底（标点结尾、流式逗号→空格），消除 ~60 行重复代码
- **[llm] TTS_EXPRESSION 提示词重写**：表格化标记说明、明确使用原则（1-3标记/段回复）、正反示例对比，显著提升 LLM 标记使用率

### 🔧 修复（延续自 v1.9.88 hotfix）
- **[proactive] 修复主动说话消息缺少时间戳**：`proactive.py` 的 `history.append` 补上 `"time": datetime.now().isoformat()`
- **[main] 修复工作记忆恢复时 `time` 为空字符串**
- **[native] 修复时间戳显示逻辑**：正确处理三种情况
- **[web] 修复 `_handle_history` 丢弃 `time` 字段**
- **[native] 修复重启后对话历史重复加载**
- **[native] 修复用户消息未记录到历史**
- **[native] 增大历史记录容量**：保存 200 条 / 加载 100 条
- **[main/native] 旧消息时间戳自动补全**

## 🟡 v1.9.88-hotfix (2026-05-07) 🔄 BETA

**消息时间戳持久化修复 — 重启后历史消息时间不再被重置**

### 🔧 修复
- **[proactive] 修复主动说话消息缺少时间戳**：`proactive.py` 的 `history.append` 补上 `"time": datetime.now().isoformat()`
- **[main] 修复工作记忆恢复时 `time` 为空字符串**：`_load_history()` 从工作记忆恢复历史时 `time` 设为 `""`，现改为 `datetime.now().isoformat()`
- **[native] 修复时间戳显示逻辑**：`chat_web_display.py` 的 `append_user_msg`/`append_ai_msg` 正确处理三种情况：有效 ISO 时间戳→解析显示真实时间；无时间戳→使用当前时间作为兜底显示
- **[web] 修复 `_handle_history` 丢弃 `time` 字段**：WebSocket 发送历史记录时补上 `time` 字段
- **[native] 修复重启后对话历史重复加载**：`on_backend_ready()` 不再清空重载，仅当 `_load_chat_history()` 没有数据时才从 `backend.history` 加载
- **[native] 修复用户消息未记录到历史**：`_send_message()` 现在调用 `_record_message("user", text)`，用户消息也会保存到 `native_chat_history.json`
- **[native] 恢复被覆盖的对话历史**：从 `chat_history.json` 恢复了 `native_chat_history.json` 的完整数据
- **[native] 增大历史记录容量**：`_save_chat_history` 保存上限从 100→200 条，`_load_chat_history` 加载上限从 50→100 条
- **[main/native] 旧消息时间戳自动补全**：`_save_history` 和 `_save_chat_history` 保存时，为缺少 `time` 的旧消息自动补充推算时间戳

## 🟡 v1.9.88 (2026-05-07) 🔄 BETA

**关键 Bug 修复 — TTS 表达标记保护 + 主动说话修复 + 对话显示防御**

### 🔧 修复
- **[web] 修复 `_strip_tool_calls` 误删 TTS 表达标记**：`\[.*?\]` 正则把 `[laugh]`/`[uv_break]`/`[lbreak]` 等标记也删了，导致 `text_enhancer` 永远收不到标记，TTS 表达功能完全失效。现改为先保护已知标记再过滤，修复后标记能正确传递到 text_enhancer 处理
- **[proactive] 修复主动说话模块 `_lazy_modules` key 不匹配**：`proactive.py` 用 `get('ws')` 但 `main.py` 存的是 `'ws_server'`，导致主动说话在 pywebview/浏览器模式下完全失效（永远找不到 WS 服务器）
- **[proactive] 修复 `clients` 迭代方式错误**：`websocket_server.clients` 是 list 不是 dict，`.items()` 会抛 AttributeError，改为直接遍历 list
- **[web] 添加对话消息显示 fallback**：`text_done` 到达时如果 `streamingMsgEl` 为空（WS 重连/竞态条件），仍会创建新消息显示，防止"有声音没文字"；`text_chunk` 到达时如果占位元素丢失会自动重建

## 🟢 v1.9.87 (2026-05-06) ✅ STABLE

**ChatTTS 情感标记 → GPT-SoVITS 文本增强集成**

### ✨ 新增
- **[tts] ChatTTS 官方标记支持** (`text_enhancer.py`)：`[laugh]`→笑声、`[uv_break]`→短停顿、`[lbreak]`→长停顿，LLM 输出这些标记后由 text_enhancer 自动转换为 GPT-SoVITS 可合成的文本（笑声词+停顿标点）
- **[tts] 智能笑声变体** (`_enhance_laugh_variety`)：根据上下文情绪自动调整笑声强度——兴奋上下文→"哈哈哈哈"（大笑）、平淡上下文→"呵呵"（轻笑）、默认→"哈哈"（标准笑）
- **[tts] 更多中文情感标记**：新增 `[大笑]`→"哈哈哈哈"、`[轻笑]`→"呵呵"、`[偷笑]`→"嘻嘻"、`[苦笑]`→"唉哈哈"、`[啜泣]`→"呜" 等变体映射
- **[llm] TTS 语音表达提示词** (`TTS_EXPRESSION`)：系统提示词新增语音表达标记使用指令，告诉 LLM 可以在回复中使用 `[laugh]`/`[uv_break]`/`[lbreak]` 来控制语音情感

### 🐛 优化
- **[tts] 修复 `[uv_break]`/`[lbreak]` 被静默删除**：此前这两个 ChatTTS 标记不在 EMOTION_MARKERS 中，被 Step 5 的 `re.sub(r'\[[\w_]+\]', '', text)` 静默删除，零效果。现已加入映射，替换为逗号/省略号停顿
- **[tts] 修复笑词拆分问题**：`哈哈哈哈` 不再被错误拆分为 `哈哈，哈哈`（排除笑声延续字符 哈/嘻/嘿/呵）
- **[tts] 修复省略号被吃掉**：语气词停顿增强不再吃掉 `……`（省略号）等后续字符，且 `嗯……` 等组合不再被错误添加逗号

## 🟢 v1.9.86 (2026-05-06) ✅ STABLE

**竞品差距补齐 — Live2D 主动动画 + Function Calling + ChatTTS + CosyVoice**

### ✨ 新增
- **[live2d] Live2D 主动动画控制器** (`AnimationController`)：闲置动画（5-15s 随机触发）、情绪驱动动作+表情映射（7种情绪）、唇形同步计时器、打招呼挥手动画
- **[llm] OpenAI Function Calling 激活**：OpenAILLM / MiniMaxLLM 的 `stream_chat` 集成 `tools` 参数，SSE 流式累积 `tool_calls` delta，工具执行后自动反馈结果给 LLM 生成自然语言回复
- **[tools] 7个陪伴工具** (`app/tools/companion.py`)：GetTimeTool、GetWeatherTool、SetReminderTool、RememberThingTool、ChangeExpressionTool、SearchWebTool、PlayMusicTool
- **[tools] FC 执行器** (`app/tools/fc_executor.py`)：统一的工具调用执行循环，处理流式/非流式两种模式
- **[tts] ChatTTS 引擎** (`app/tts/chattts.py`)：对话优化 TTS，支持 [laugh]/[uv_break] 标记，懒加载单例模式
- **[tts] CosyVoice 引擎** (`app/tts/cosyvoice.py`)：阿里 CosyVoice TTS，FastAPI HTTP 客户端模式，支持指令/克隆/跨语言三种合成，7种情绪指令控制
- **[chat] TTS 引擎切换扩展**：TTS 下拉框新增 ChatTTS / CosyVoice 选项，动画控制器集成到聊天完成回调

### 🔄 变更
- ToolFactory 工具数量：9 → 16
- TTSFactory 新增 chattts / cosyvoice 引擎创建分支（不可用时优雅降级到 Edge TTS）
- 版本号从 v2.0.0 降级为 v1.9.86（小版本更新策略）

## 🟢 v1.9.85 (2026-05-06) ✅ STABLE

**对话时间戳持久化 — 历史消息时间不再重置**

### 🔧 修复
- **[chat] 历史消息时间戳重置修复**：`append_user_msg()`/`append_ai_msg()` 新增 `timestamp` 参数，加载历史消息时传入保存的原始时间（`msg.get("time")`），不再使用 `datetime.now()` 生成新时间戳。影响 `_load_chat_history`、`_on_session_switched`、`on_backend_ready` 三处历史加载逻辑
- **[session] 会话列表时间显示优化**：tooltip 新增"更新时间"显示，时间格式改为友好显示（今天 HH:MM / 昨天 HH:MM / MM-DD HH:MM / YYYY-MM-DD HH:MM）

## 🟢 v1.9.84 (2026-05-06) ✅ STABLE

**实时语音修复 + TTS流式分句 + 布局响应式优化**

### 🔧 修复
- **[voice] 实时语音 AI 回复不显示修复**：`_stop_streaming()` 未终结当前流式消息占位，且与 `_on_realtime_speech` 存在竞态条件。现在 `_stop_streaming` 会调用 `finish_streaming()` 终结当前消息；`_on_realtime_speech` 使用 `QTimer.singleShot(50ms)` 延迟发送新消息，确保状态清理完成；`_on_stream_finished` 增加防重复处理守卫
- **[layout] TTS 工具栏缩放重叠修复**：将单行固定宽度布局改为两行自适应布局（核心控件 + 速度/音量滑块），所有 `setFixedWidth` 改为 `setMinimumWidth`，滑块使用 `stretch=1` 自动填充；SessionManager 从 `setFixedWidth(200)` 改为 `setMinimumWidth(160)+setMaximumWidth(220)`；ChatPage 设置 `setMinimumSize(800,500)`；聊天卡片设置 `setMinimumHeight(200)`

### ✨ 新增
- **[tts] 流式/整段模式切换按钮**：TTS 工具栏新增"流式"切换按钮，默认开启流式分句合成（检测到句子结束标点即合成播放），关闭后为整段合成模式
- **[tts] StreamChatWorker 流式分句 TTS**：`StreamChatWorker` 新增 `streaming_tts` 参数和 `sentence_ready` 信号，流式模式下在 LLM 输出过程中检测完整句子并立即合成播放，大幅降低首句 TTS 延迟

## 🟢 v1.9.83 (2026-05-06) ✅ STABLE

**Qt6 渲染引擎修复 + Shiboken 类型转换修复**

### 🔧 修复
- **[core] QQuickWidget QRhi 初始化失败修复**：Windows 下 Qt6 默认使用 D3D11 RHI 后端，与 QOpenGLWidget（Live2D）所需 OpenGL 冲突，导致 `QQuickWidget: Failed to get a QRhi` 错误。在 QApplication 创建前调用 `QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)` 强制使用 OpenGL 后端
- **[settings] GPT-SoVITS 音色列表 Shiboken 转换错误修复**：`_populate_gptsovits_voices()` 中 `get_voices()` 返回的 dict 值可能不是字符串，传给 `QComboBox.addItem(userData=...)` 时触发 `Shiboken::Conversions: Cannot copy-convert (dict) to C++` 错误。已用 `str()` 包裹 value 和 label 参数

## 🟢 v1.9.82 (2026-05-05) ✅ STABLE

**聊天界面卡片式重构 — 三层视觉分区 + 紧凑TTS工具栏**

### ✨ 改进
- **[chat] 卡片式布局重构**：聊天区/输入栏/TTS工具栏各自独立卡片，视觉层次分明
- **[chat] 输入栏重设计**：附件按钮左置 + 竖分隔线 + 圆角输入框 + 渐变发送按钮，类现代聊天应用风格
- **[chat] TTS工具栏单行化**：两行控件压缩为一行紧凑工具栏，pill风格切换按钮，滑块用文字标签替代
- **[chat] 实时语音按钮缩短**："实时语音"→"语音"，"监听中..."→"监听中"
- **[theme] QSS新增卡片容器规则**：避免全局QWidget样式污染chatCard/inputCard/ttsCard


## 🟢 v1.9.81 (2026-05-04) ✅ STABLE

**对话 UI 全面升级 — 微信级消息分组 + SVG头像 + 打字光标**

### ✨ 新增
- **[chat] 微信级消息分组**：同一方连续发言自动合并，只显示一次头像，后续消息用占位符保持对齐
- **[chat] 条件时间戳**：仅在对话间隔>3分钟时显示居中胶囊时间标签，格式支持"昨天"/"月日"
- **[chat] SVG 内联头像**：AI 机器人轮廓图标 + 用户人形轮廓图标，替代旧的纯文字"AI"/"我"
- **[chat] 打字光标闪烁**：流式回复时尾部显示 ▍ 光标，530ms 闪烁，完成后自动消失
- **[chat] 三点跳动思考动画**：AI 思考中用 ●●● 轮转亮度动画替代骨架屏

### 🐛 优化
- **[chat] 气泡视觉升级**：AI气泡色#2a2d3a提高对比度、padding加大到12px16px、line-height1.7、font-size14px
- **[chat] 去除AI回复分隔线**：移除干扰阅读流的border-top分隔线
- **[chat] 系统消息胶囊化**：居中胶囊标签样式，与时间戳风格统一
- **[theme] v3.0**：新增消息分组颜色常量、SVG头像生成函数、时间戳格式化函数

