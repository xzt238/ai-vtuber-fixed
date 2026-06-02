# PRD — 咕咕嘎嘎 AI-VTuber 第二轮性能优化（增量）

| 字段 | 值 |
|---|---|
| 项目 | ai-vtuber-fixed |
| 版本基线 | v1.11.29 |
| PRD 类型 | 增量（第二轮优化） |
| 语言 | 中文 |
| 技术栈 | PySide6 + QWebEngineView + Python 3.10+ |
| 前置条件 | 第一轮优化（T01-T05）已完成 |
| 约束 | 不更换 LLM/TTS/ASR 模型 |

---

## 1. 产品目标（增量）

| # | 目标 | 说明 |
|---|---|---|
| G1 | **首屏渲染提速 30-40%** | 消除 ChatPage 中 ChatWebDisplay（QWebEngineView）同步创建对首屏渲染的阻塞 |
| G2 | **消除非首屏页面首次打开卡顿** | SettingsPage 10+ 处同步 JSON 读取改为异步，消除 500ms-1s 的 UI 冻结 |
| G3 | **降低后台资源占用** | 延迟创建非必需后端管理器 + 最小化时暂停 idle 动画，减少 200-500ms 启动耗时和 5-10% 后台 CPU |
| G4 | **建立性能可度量体系** | 在关键启动节点添加 `time.perf_counter()` 埋点，让优化效果可量化、可回归 |

---

## 2. 用户故事

1. **作为用户**，我希望启动应用后尽快看到对话界面，而不是盯着启动画面等待 QWebEngineView 初始化，以便我能更快开始与角色对话。

2. **作为用户**，我希望首次打开设置页面时不会出现明显卡顿，以便我能流畅地调整配置项。

3. **作为用户**，我希望应用在最小化到后台时不浪费 CPU 资源运行 Live2D idle 动画，以便我的电脑不会因后台应用而变慢。

4. **作为开发者**，我希望在启动时能通过日志看到各阶段精确耗时，以便我能量化每次优化效果并快速定位新的性能瓶颈。

---

## 3. 性能瓶颈补充表（仅新增项）

| 编号 | 瓶颈位置 | 现状 | 影响 | 优先级 |
|---|---|---|---|---|
| B1 | `ChatPage._init_ui()` → `ChatWebDisplay()` 创建 | QWebEngineView（Chromium 内核）在首屏 `__init__` 中同步创建 | 首屏渲染必须等 Chromium 初始化完毕（500ms-1.5s） | P0 |
| B2 | `SettingsPage._load_saved_config()` 及关联方法 | 10+ 处 `json.load()` 同步读取磁盘 | 首次打开设置页时 UI 冻结 500ms-1s | P0 |
| B3 | `GuguGagaApp.__init__` → VoiceManager/HotkeyManager | 在窗口显示前同步创建（L218/L223） | 启动到可交互时间多 200-500ms | P1 |
| B4 | `AnimationController._idle_timer` | 最小化时 idle 动画定时器（2s 间隔）持续运行 | 后台 CPU 空转 5-10% | P1 |
| B5 | 启动全链路 | 无量化数据，优化效果靠主观感受 | 无法回归验证，无法定位新增瓶颈 | P2 |

---

## 4. 优化目标（量化指标）

| 指标 | 当前基线（估） | 目标 | 验证方式 |
|---|---|---|---|
| 首屏渲染时间（App 启动 → 窗口可交互） | ~3-5s | 缩短 30-40% → ~2-3s | 启动埋点日志 |
| 设置页首次打开延迟 | 500ms-1s 卡顿 | <100ms（异步加载） | 手动测试 + 埋点 |
| 后台最小化 CPU 占用 | Live2D idle 动画持续运行 | 降低 5-10% | 任务管理器对比 |
| 启动到 VoiceManager 就绪 | 同步创建于 `__init__` | 延迟到 `showEvent` 后 | 埋点日志确认创建时机 |
| 优化可度量性 | 无数据 | 6 个关键节点均有耗时日志 | 检查日志输出 |

---

## 5. 优化方案详细描述

### 5.1 [P0] ChatPage ChatWebDisplay 延迟创建

**问题分析**

`chat_page.py`（2101 行）的 `_init_ui()` 在第 321 行同步创建 `ChatWebDisplay(self)`，后者继承自 `QWebEngineView`（Chromium 内核），创建耗时 500ms-1.5s。由于 ChatPage 是首屏页面，此创建必须完成后窗口才能渲染。

**代码位置**

- `chat_page.py:321` — `self.chat_display = ChatWebDisplay(self)`
- `chat_web_display.py`（1298 行）— `ChatWebDisplay` 类

**当前状态**

Live2DWidget 已采用延迟创建模式（`_lazy_init_live2d()`，chat_page.py:587），先显示占位符，后通过 `QTimer.singleShot(100, ...)` 延迟创建。ChatWebDisplay 尚未采用相同策略。

**优化方案**

1. 在 `_init_ui()` 中，先用 `QLabel("⏳ 正在加载对话...")` 占位，将 `ChatWebDisplay` 的创建延迟到窗口显示后
2. 在 `on_backend_ready()` 回调中（或 `showEvent` 后），通过 `QTimer.singleShot(0)` 延迟创建 ChatWebDisplay 并替换占位符
3. 延迟创建后需调用 `invalidate()` + `activate()` 确保布局正确传播（参考 Live2D 延迟创建的三段式 repaint 逻辑）

**技术约束**

- ChatWebDisplay 在 `on_backend_ready()` 和其他方法中被直接引用（如 `self.chat_display.append_message()`），延迟创建期间需确保这些调用不崩溃
- 方案：将 chat_display 设为 property，未创建时返回 None，调用处加 None guard
- 替代方案：维护一个 `_pending_messages` 队列，创建后重放

**边界条件**

- 如果后端就绪前用户已在对话区（理论上不可能，因为后端是异步初始化），需防止操作空指针
- ChatWebDisplay 的 `action_copy`/`action_retry`/`action_quote`/`action_edit` 信号连接需在创建后立即绑定

**预期收益**：首屏渲染提速 30-40%（500ms-1.5s 的 QWebEngineView 创建从首屏关键路径移除）

---

### 5.2 [P0] SettingsPage 异步 JSON 加载

**问题分析**

`settings_page.py`（1638 行）有 10+ 处同步 `json.load()` 调用，分布在以下方法中：

| 行号 | 方法 | 读取文件 |
|---|---|---|
| 689 | `_load_api_key_for_provider()` | `api_keys.json` |
| 716 | `_save_llm_config()` | `llm_preferences.json`（保存前读取） |
| 760 | `_save_api_key()` | `api_keys.json`（保存前读取） |
| 1052 | `_save_tts_config()` | `tts_preferences.json`（保存前读取） |
| 1149 | `_load_tts_prefs()` | `tts_preferences.json` |
| 1198 | `_load_saved_config()` | `llm_preferences.json` |
| 1354 | `_on_backend_ready_impl()` | `vision_preferences.json` |
| 1449 | `_load_proactive_config()` | `proactive_prefs.json` |
| 1533 | `_load_asr_prefs()` | `asr_preferences.json` |

其中 `_load_saved_config()`（L1192）是主入口，在 `_on_backend_ready_impl()` 中被调用（L1252），其内部串联调用 `_load_api_key_for_provider()` + `_load_tts_prefs()` + `_load_asr_prefs()`，形成同步 I/O 链。

**优化方案**

1. **首要目标**：将 `_load_saved_config()` 的所有文件读取改为使用 `AsyncJsonWorker`
2. 在 `_on_backend_ready_impl()` 中，先一次性批量读取所有偏好文件（`llm_preferences.json` / `api_keys.json` / `tts_preferences.json` / `asr_preferences.json` / `vision_preferences.json` / `proactive_prefs.json`），通过 `AsyncJsonWorker` 在后台线程完成
3. `json_loaded` 信号回传结果后，在主线程批量更新所有 UI 控件
4. 保存路径的同步读取（L716/L760/L1052）暂不修改（保存是用户主动操作，不构成启动瓶颈），但标记为后续优化候选

**已有基础设施**

`AsyncJsonWorker`（`async_json_worker.py`，31 行）已实现：
- 接受 `file_paths: list[str]`
- 在 `QThread` 中批量读取
- 通过 `json_loaded = Signal(dict)` 回传 `{file_path: data_dict}`

**技术约束**

- `AsyncJsonWorker` 返回的是 `{file_path: data_dict}`，需要在回调中按路径匹配解析
- 批量读取需处理文件不存在的情况（`AsyncJsonWorker` 已处理，返回 `None`）
- 确保 UI 控件在 `lazy_init()` 完成后才更新（SettingsPage 使用 LazyPageMixin）

**边界条件**

- 异步加载期间用户可能切换离开设置页，需确保回调安全（检查 `self._is_initialized`）
- 文件损坏（非法 JSON）场景：`AsyncJsonWorker` 已 catch 为 `None`，回调中需同样处理

**预期收益**：消除设置页首次打开时 500ms-1s 的 UI 冻结

---

### 5.3 [P1] 后端管理器延迟初始化

**问题分析**

`main.py` L218/L223 在 `GuguGagaApp.__init__` 中同步创建：

```python
# L218
self.voice_manager = RealtimeVoiceManager(parent=self)
# L223
self.hotkey_manager = HotkeyManager(self)
self.hotkey_manager.start()
```

- `RealtimeVoiceManager` 初始化时加载 Silero VAD ONNX 模型（`voice_manager.py:35-42`），需创建 ONNX Runtime Session
- `HotkeyManager` 初始化时读取 `hotkeys.json` 并启动 pynput 监听线程

两者在窗口显示前创建，但用户至少 3-5 秒后才会使用语音/快捷键功能。

**优化方案**

1. 将 VoiceManager 和 HotkeyManager 的创建从 `__init__` 移至窗口 `showEvent` 后
2. 通过 `QTimer.singleShot(500, self._init_backend_managers)` 延迟 500ms 执行，确保窗口完全渲染后再创建
3. `_init_backend_managers()` 中依次创建 VoiceManager 和 HotkeyManager，保持原有信号连接
4. 在延迟创建前，所有引用 `self.voice_manager` 或 `self.hotkey_manager` 的代码需加 None guard 或使用 property 延迟访问

**技术约束**

- `voice_manager` 和 `hotkey_manager` 在 `perf_manager.register_cleanup_target()`（L249-250）中被引用，需确保在注册前已创建
- `voice_manager.vad_state_changed` / `hotkey_manager.hotkey_triggered` 信号连接可在延迟创建时绑定
- 桌面宠物（`_pet_window`）的语音功能依赖 `voice_manager`，需确保宠物创建在语音管理器之后

**边界条件**

- 如果用户在 500ms 内触发快捷键（理论上不可能），不会崩溃（manager 尚未创建，信号未连接）
- 托盘菜单中的"切换录音"等操作需检查 `voice_manager` 是否已创建

**预期收益**：启动到窗口可交互时间缩短 200-500ms

---

### 5.4 [P1] AnimationController 最小化降频

**问题分析**

`animation_controller.py`（388 行）的 `_idle_timer`（QTimer，2s 间隔）在 `start()` 后持续运行（L186），即使窗口最小化也不停止。每次 tick 执行 `_on_idle_tick()` 检查是否触发 idle 动画，对 Live2D 模型发送动作指令。

**优化方案**

1. 在 `AnimationController` 中添加 `pause_idle()` / `resume_idle()` 方法
2. `pause_idle()`：停止 `_idle_timer`，标记 `_idle_paused = True`
3. `resume_idle()`：重新启动 `_idle_timer`，重置 `_last_idle_time`，标记 `_idle_paused = False`
4. 在 `GuguGagaApp` 中监听 `changeEvent`（`QEvent.Type.WindowStateChange`），窗口最小化时调用 `controller.pause_idle()`，恢复时调用 `controller.resume_idle()`

**技术约束**

- 情绪动画（`trigger_emotion()`）在对话中触发，最小化时不应暂停——只暂停 idle 定时器
- 口型同步（`set_mouth_open()`）由 TTS 播放驱动，不受 idle 暂停影响
- 需确保 `resume_idle()` 后不会立即触发大量积压的 idle 动画（重置 `_last_idle_time` 即可）

**边界条件**

- 窗口从最小化恢复时，Live2D 模型可能需要重新渲染（Chromium 进程可能被 OS 回收），idle 动画触发可帮助确认模型活跃状态
- 桌面宠物模式下，窗口最小化不影响宠物窗口的 idle 动画（宠物窗口独立）

**预期收益**：后台 CPU 占用降低 5-10%

---

### 5.5 [P2] 启动性能埋点

**问题分析**

当前无量化数据衡量各阶段耗时，优化效果依赖主观感受。需在关键节点添加 `time.perf_counter()` 埋点，输出到日志。

**埋点位置**

| 节点 | 文件 | 说明 |
|---|---|---|
| T1 | `main.py` — `GuguGagaApp.__init__` 开始 | `self._perf_t1 = time.perf_counter()` |
| T2 | `main.py` — `_create_pages()` 开始 | ChatPage 创建前 |
| T3 | `main.py` — `_create_pages()` 结束 | ChatPage 创建后 |
| T4 | `chat_page.py` — `ChatWebDisplay` 创建前/后 | 量化 QWebEngineView 创建耗时 |
| T5 | `main.py` — 后端初始化完成 | `_on_backend_ready_async` 回调中 |
| T6 | `main.py` — 窗口 `show()` 时刻 | 首次 showEvent |

**输出格式**

```
[PERF] T1→T2: _create_pages前置 0.045s | T2→T3: ChatPage创建 1.234s | T3→T4: ChatWebDisplay创建 0.856s | T4→T5: 后端初始化 2.345s | T5→T6: 窗口显示 0.012s | T1→T6: 总计 4.492s
```

**优化方案**

1. 在 `GuguGagaApp.__init__` 入口记录 T1
2. 在各关键位置记录时间戳，使用 `logger.info()` 输出增量耗时
3. 窗口 `showEvent` 中输出总耗时汇总
4. 使用 `time.perf_counter()` 而非 `time.time()`（更高精度）

**技术约束**

- 埋点代码必须极轻量，不能影响被测量的性能（`perf_counter()` 本身 <1μs）
- 日志级别使用 `INFO`，可通过 logging 配置控制开关
- 避免在循环或高频回调中添加埋点

**边界条件**

- 首次启动（冷启动）vs 热启动数据差异大，测试时应区分
- 打包后的 `.exe` 启动比源码运行慢（PyInstaller 解压开销），埋点应能反映

**预期收益**：为后续优化迭代提供量化依据，支持性能回归检测

---

## 6. 待确认问题

| # | 问题 | 影响范围 | 建议 |
|---|---|---|---|
| Q1 | ChatWebDisplay 延迟创建期间，`append_message()` 等方法被调用如何处理？ | 5.1 | 建议使用 `_pending_messages` 队列方案，创建后重放，比 property + None guard 更安全 |
| Q2 | AsyncJsonWorker 批量读取 6 个文件时，如果部分文件不存在，UI 更新逻辑是否需要分步？ | 5.2 | 建议：一次性返回结果，回调中按 key 存在性逐项更新，不存在则跳过 |
| Q3 | VoiceManager 延迟创建后，托盘菜单的"切换录音"操作在 500ms 窗口内点击是否会崩溃？ | 5.3 | 建议：托盘操作加 `if not self.voice_manager: return` guard |
| Q4 | AnimationController 的 `pause_idle()` 是否需要同步暂停问候动画定时器？ | 5.4 | 建议：不暂停（`_greet_timer` 是一次性定时器，已触发则无效，未触发则保留——最小化后恢复时的问候体验更好） |
| Q5 | 性能埋点数据是否需要持久化到文件（如 JSON/CSV），还是仅输出日志？ | 5.5 | 建议：本轮仅输出日志，后续可扩展为 JSON 持久化 + 历史对比 |
| Q6 | ChatWebDisplay 延迟创建后，如果延迟期间用户已开始输入并发送消息，消息是否需要先缓存到队列？ | 5.1 | 与 Q1 合并考虑；后端初始化本身也是异步的，理论上不会出现"UI 已渲染但 ChatWebDisplay 未就绪且用户已发送消息"的场景 |
