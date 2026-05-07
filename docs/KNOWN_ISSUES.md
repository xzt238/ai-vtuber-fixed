# 🐛 已知问题 & 技术债务 (KNOWN_ISSUES)

> **最后更新**: 2026-05-07 | **当前版本**: v1.9.90

本文档集中记录项目中所有已知的 Bug、技术债务和架构问题。每个条目包含唯一 ID、严重度、影响组件、当前状态、描述和变通方案。

---

## 严重度说明

| 标记 | 含义 |
|------|------|
| 🔴 高 | 会导致功能异常、数据丢失或崩溃 |
| 🟡 中 | 影响用户体验或维护效率，但不直接导致功能失败 |
| 🟢 低 | 代码质量或美观问题，不影响运行 |

---

## 活跃问题

### KI-001: JS-Python 数据手动同步
- **严重度**: 🟡 中
- **组件**: `app/shared_config.py` / `app/web/static/index.html`
- **状态**: OPEN
- **描述**: `shared_config.py` 中的 4 组数据（PROVIDER_CONFIG、EDGE_VOICES、EXPRESSION_KEYWORDS、EXPRESSION_MAP）必须手动同步到 `index.html` 中的 JS 变量（`_providerConfig`、`voiceOptions.edge`、`expressionKeywords`、`expressionMap`）。Python 无法 import JS 文件，JS 也无法 import Python，没有自动化验证机制。
- **变通方案**: 每次修改 `shared_config.py` 后，按 `CHANGE_IMPACT_MAP.md` 发布检查清单手动同步 `index.html`。
- **参见**: `CHANGE_IMPACT_MAP.md` 第 2-4 节

### KI-002: 端口号硬编码 5 处
- **严重度**: 🟡 中
- **组件**: `launcher/launcher.py`, `native/gugu_native/widgets/dual_mode_compat.py`, `app/main.py`, `app/web/__init__.py`, `app/config.yaml`
- **状态**: OPEN
- **描述**: HTTP 端口 12393 和 WS 端口 12394 在 5 个位置分别硬编码，未统一读取 `config.yaml`。修改端口需要同时改 5 处。
- **变通方案**: 使用 `MODIFICATION_GUIDE.md` 中的 M-006 操作手册。
- **参见**: `CHANGE_IMPACT_MAP.md` 第 6 节

### KI-003: index.html 单体文件 11,000+ 行
- **严重度**: 🔴 高
- **组件**: `app/web/static/index.html`
- **状态**: OPEN
- **描述**: Web UI 的全部 CSS、HTML、JS 集中在单个 HTML 文件中，超过 11,000 行。极其难以维护和调试。任何修改都需要在大文件中精确定位。
- **变通方案**: 使用浏览器 DevTools 和 VS Code 搜索功能定位代码。

### KI-004: GPT-SoVITS 模型列表重复维护
- **严重度**: 🟢 低
- **组件**: `native/gugu_native/pages/model_download_page.py`, `scripts/setup.py`
- **状态**: OPEN
- **描述**: 6 个模型的 URL、路径、大小阈值在 2 个文件中完全相同地维护，手动同步。
- **参见**: `CHANGE_IMPACT_MAP.md` 第 8 节

### KI-005: PROJECT_DIR 路径计算 18+ 处
- **严重度**: 🟢 低（目录结构不变时无影响） → 🔴 高（目录结构变化时）
- **组件**: 多个文件
- **状态**: OPEN
- **描述**: 18+ 个文件使用 `os.path.dirname(os.path.dirname(...))` 多层嵌套计算项目根目录。如果目录结构变化需要修改所有文件。
- **变通方案**: `app/shared_config.py` 中定义了 `PROJECT_DIR` 常量，但尚未被所有文件采用。
- **参见**: `CHANGE_IMPACT_MAP.md` 第 9 节

### KI-006: 重复代码模式
- **严重度**: 🟢 低
- **组件**: 多个
- **状态**: OPEN
- **描述**: 多处重复代码模式：DLL 解锁逻辑（2 处）、TTS 引擎重建逻辑（2 处）、ASR Worker 类（2 处）、工具调用过滤（3 处）、LLM 偏好设置保存/加载（3 处）。
- **参见**: `CHANGE_IMPACT_MAP.md` 第 11-14 节

### KI-007: WebSocket 客户端状态字典内存泄漏
- **严重度**: 🔴 高
- **组件**: `app/web/__init__.py` L1256-1273
- **状态**: OPEN
- **描述**: `_client_tts_no_split`、`_text_gen_running`、`_text_gen_cancel` 中的 `threading.Event` 在客户端断开后永不释放，导致内存泄漏。
- **变通方案**: 定期重启服务。

### KI-008: 多模态请求每次创建新 TTS 引擎
- **严重度**: 🔴 高
- **组件**: `app/web/__init__.py` L2629
- **状态**: OPEN
- **描述**: `_handle_multimodal` 每次调用 `TTSFactory.create()`，GPT-SoVITS 整个推理管线从零加载，造成 GPU 资源泄漏和严重性能问题。
- **变通方案**: 使用缓存机制（`_get_tts_for_client`），但缓存本身存在竞态问题（见 KI-009）。

### KI-009: TTS 引擎缓存无锁竞态
- **严重度**: 🔴 高
- **组件**: `app/web/__init__.py` L2139-2168
- **状态**: OPEN
- **描述**: `_get_tts_for_client` 的 `_tts_engine_cache` 读写无锁，多线程可同时创建重复引擎，导致 GPU 内存浪费。

### KI-010: MiniMaxLLM 变量未初始化
- **严重度**: 🟡 中
- **组件**: `app/llm/__init__.py` L1223
- **状态**: OPEN
- **描述**: `_stream_openai` 方法中，如果流无有效行则 `choice`/`chunk` 未定义，会导致 `NameError`。

### KI-011: _sentence_buffer 竞态条件
- **严重度**: 🔴 高
- **组件**: `native/gugu_native/pages/chat_page.py` L92-197
- **状态**: OPEN
- **描述**: `StreamChatWorker` 中 `_buffer` 在两线程间访问，`_mutex` 只保护 `_stop_requested`，不保护 `_buffer`。

### KI-012: _asr_workers 列表无锁
- **严重度**: 🟡 中
- **组件**: `native/gugu_native/widgets/voice_manager.py` L369
- **状态**: OPEN
- **描述**: 录音线程 append、主线程 remove `_asr_workers` 列表，存在竞态条件。

### KI-013: _lazy_modules 从后台线程访问
- **严重度**: 🟡 中
- **组件**: `native/gugu_native/pages/settings_page.py` L702
- **状态**: OPEN
- **描述**: LLM/TTS RebuildWorker 访问 `backend._lazy_modules`，主线程也在读写，存在竞态。

### KI-014: Vision/OCR 调用阻塞主线程
- **严重度**: 🟡 中
- **组件**: `native/gugu_native/pages/chat_page.py` L1338-1346
- **状态**: OPEN
- **描述**: `_process_pending_image` 同步调用 vision，UI 冻结数秒。

### KI-015: config.yaml 加载不完整
- **严重度**: 🟡 中
- **组件**: `native/gugu_native/widgets/dual_mode_compat.py` — `migrate_webui_config`
- **状态**: OPEN
- **描述**: 使用 `yaml.safe_load` 读取 config.yaml 但不做 `${VAR}` 环境变量展开，与主 `Config._load()` 行为不一致。

---

## 已解决问题

### KI-R001: 版本号硬编码 6 处不一致 ✅ (v1.9.90)
- **原问题**: 6 个文件硬编码版本号，出现 3 个不同值（1.9.86 / 1.9.83 / 1.9.64）
- **修复**: 创建 `app/version.py` 作为唯一数据源，所有文件改为 import 引用

### KI-R002: Function Calling 条件永远为 True ✅ (v1.9.90)
- **原问题**: `tool_calls_accum and (finish_reason == "tool_calls" or tool_calls_accum)` 因短路求值恒为 True
- **修复**: 改为 `tool_calls_accum and finish_reason == "tool_calls"`

### KI-R003: TTS 类变量被实例变量遮蔽 ✅ (v1.9.90)
- **原问题**: `self._is_playing = True` 创建实例变量覆盖类变量，多实例状态不同步
- **修复**: 使用 property 桥接到 `_cls_*` 类变量

### KI-R004: Live2D os.chdir() 污染进程工作目录 ✅ (v1.9.90)
- **原问题**: `os.chdir(web_dir)` 改变整个进程工作目录
- **修复**: 使用 `SimpleHTTPRequestHandler(directory=web_dir)` 参数 + `allow_reuse_address = True`

### KI-R005: 主动说话绕过历史截断 ✅ (v1.9.90)
- **原问题**: `proactive.py` 直接 `history.append()` 绕过 `record_interaction()` 的 MAX_HISTORY 截断
- **修复**: 改为调用 `self.app.record_interaction("[主动说话触发]", reply)`

### KI-R006: 桌面宠物拖拽误触 ✅ (v1.9.90)
- **原问题**: 鼠标释放时无论移动距离都触发点击动作
- **修复**: 添加 `_drag_start_pos` 追踪，manhattan distance < 5px 才判定为点击

### KI-R007: 语音管理器持锁发信号 ✅ (v1.9.90)
- **原问题**: `_finalize_speech_segment` 在持锁时 emit Qt 信号，可能导致死锁
- **修复**: 先释放锁再 emit

### KI-R008: playbackStateChanged 信号泄漏 ✅ (v1.9.90)
- **原问题**: 每次 `_start_lipsync` 连接信号但不断开，N 次播放后触发 N 次回调
- **修复**: 连接前先 disconnect

### KI-R009: 魔法时间戳 ✅ (v1.9.90)
- **原问题**: 硬编码 `'2026-05-07T19:35:00'` 时间戳
- **修复**: 改为 `datetime.now().isoformat()`

### KI-R010: Windows-only API 无平台保护 ✅ (v1.9.90)
- **原问题**: `dual_mode_compat.py` 和 `perf_manager.py` 在非 Windows 平台会崩溃
- **修复**: 添加 `sys.platform != "win32"` 保护

### KI-R011: LLM Provider 配置三处维护 ✅ (v1.9.90)
- **原问题**: `settings_page.py` 中重复定义了 `PROVIDER_CONFIG` 和 `EDGE_VOICES`
- **修复**: 改为从 `app/shared_config` import

### KI-R012: Edge TTS 音色列表三处不同步 ✅ (v1.9.90)
- **原问题**: Python 端和 JS 端的音色列表不一致
- **修复**: 同步为 8 个语音，统一到 `shared_config.py`

### KI-R013: 表情关键词重复定义 ✅ (v1.9.90)
- **原问题**: `index.html` 中"哈哈"和"讨厌"重复定义
- **修复**: 清理去重

### KI-R014: health 端点版本号硬编码 ✅ (v1.9.90)
- **原问题**: `app/web/__init__.py` 健康检查端点硬编码版本号
- **修复**: 改为从 `app.version` 导入
