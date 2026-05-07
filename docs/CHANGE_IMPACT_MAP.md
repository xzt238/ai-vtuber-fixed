# 🗺️ 咕咕嘎嘎 AI-VTuber — 修改影响地图

> **目的**：当你修改某一项内容时，需要知道还要同步修改哪些文件。
> 本文档列出所有"一处修改、多处联动"的配置项和数据，确保不会遗漏。

---

## 📋 快速索引

| 修改项 | 需同步文件数 | 严重度 |
|--------|-------------|--------|
| [版本号](#1-版本号) | 6 处 | 🔴 漏改会导致更新检查永远认为有新版本 |
| [LLM Provider 配置](#2-llm-provider-配置) | 2 处 Python + 1 处 JS | 🔴 漏改会导致模型列表/URL 不同步 |
| [Edge TTS 音色列表](#3-edge-tts-音色列表) | 2 处 Python + 1 处 JS | 🟡 漏改会导致音色选项不一致 |
| [表情关键词映射](#4-表情关键词映射) | 2 处 Python + 1 处 JS | 🟡 漏改会导致表情触发不一致 |
| [互斥体名称](#5-互斥体名称) | 1 处 | 🟢 已统一到 shared_config |
| [端口号](#6-端口号) | 5 处 | 🟡 改端口需改 5 处 |
| [Live2D 默认模型路径](#7-live2d-默认模型路径) | 2 处 | 🟢 路径相同但未统一 |
| [GPT-SoVITS 模型下载列表](#8-gpt-sovits-模型下载列表) | 2 处 | 🟡 完全相同数据两处维护 |
| [项目根目录路径计算](#9-项目根目录路径计算) | 18+ 处 | 🟢 结构变更时需逐一修改 |
| [单实例互斥逻辑](#10-单实例互斥逻辑) | 2 处 | 🟢 已统一名称 |
| [DLL 解锁逻辑](#11-dll-解锁逻辑) | 2 处 | 🟢 范围不同但逻辑重复 |
| [TTS 引擎重建逻辑](#12-tts-引擎重建逻辑) | 2 处 | 🟢 可抽取公共方法 |
| [ASR Worker 类](#13-asr-worker-类) | 2 处 | 🟢 相同逻辑重复实现 |
| [工具调用过滤逻辑](#14-工具调用过滤逻辑) | 3 处 | 🟢 三处过滤 TOOL:/ARG:/BASH: |

---

## 详细说明

### 1. 版本号

**唯一数据源**：`app/version.py` → `VERSION = "1.9.90"`

| # | 文件 | 位置 | 当前状态 | 说明 |
|---|------|------|----------|------|
| 1 | `app/version.py` | 全文件 | ✅ 唯一数据源 | 修改版本号只需改这里 |
| 2 | `app/main.py` | L1958 | ✅ 已改为 `from app.version import VERSION` | |
| 3 | `native/main.py` | L99 `setWindowTitle` | ✅ 已改为 `_get_version()` | |
| 4 | `native/main.py` | L184 `UpdateManager` | ✅ 已改为 `_get_version()` | 之前硬编码 "1.9.83" |
| 5 | `launcher/launcher.py` | L715 | ✅ 已改为 `from app.version import VERSION` | |
| 6 | `native/gugu_native/pages/settings_page.py` | L400 | ✅ 已改为 `from app.version import VERSION` | |
| 7 | `native/gugu_native/widgets/update_manager.py` | L146 默认值 | ✅ 已改为从 version.py 读取 | 之前硬编码 "1.9.64" |

**修改步骤**：
1. 修改 `app/version.py` 中的 `VERSION`
2. 其他文件自动读取，无需额外修改
3. 更新 `docs/VERSION.md` 添加版本记录

---

### 2. LLM Provider 配置

**唯一数据源**：`app/shared_config.py` → `PROVIDER_CONFIG`

| # | 文件 | 位置 | 说明 |
|---|------|------|------|
| 1 | `app/shared_config.py` | `PROVIDER_CONFIG` | ✅ 唯一数据源 |
| 2 | `native/gugu_native/pages/settings_page.py` | 顶部 import | ✅ 已改为 `from app.shared_config import PROVIDER_CONFIG` |
| 3 | `app/web/static/index.html` | L8983 `_providerConfig` | ⚠️ **需手动同步**（JS 无法 import Python） |

**修改步骤**：
1. 修改 `app/shared_config.py` 中的 `PROVIDER_CONFIG`
2. `settings_page.py` 自动读取，无需额外修改
3. ⚠️ 手动同步到 `index.html` 的 `_providerConfig` 对象（包括 label、baseUrl、models、defaultModel）

---

### 3. Edge TTS 音色列表

**唯一数据源**：`app/shared_config.py` → `EDGE_VOICES`

| # | 文件 | 位置 | 说明 |
|---|------|------|------|
| 1 | `app/shared_config.py` | `EDGE_VOICES` | ✅ 唯一数据源 |
| 2 | `native/gugu_native/pages/settings_page.py` | 顶部 import | ✅ 已改为 `from app.shared_config import EDGE_VOICES` |
| 3 | `app/tts/__init__.py` | `EdgeTTS.VOICES` | ⚠️ 格式不同（dict vs list），需手动同步 |
| 4 | `app/web/static/index.html` | L5599 `voiceOptions.edge` | ⚠️ **需手动同步**（JS 无法 import Python） |

**修改步骤**：
1. 修改 `app/shared_config.py` 中的 `EDGE_VOICES`
2. `settings_page.py` 自动读取
3. ⚠️ 手动同步 `app/tts/__init__.py` 的 `EdgeTTS.VOICES`（注意格式是 dict: `{"zh-CN": {"XiaoxiaoNeural": "中文女声 (标准)"}}` ）
4. ⚠️ 手动同步 `index.html` 的 `voiceOptions.edge` 数组

---

### 4. 表情关键词映射

**唯一数据源**：`app/shared_config.py` → `EXPRESSION_KEYWORDS` + `EXPRESSION_MAP`

| # | 文件 | 位置 | 说明 |
|---|------|------|------|
| 1 | `app/shared_config.py` | `EXPRESSION_KEYWORDS` / `EXPRESSION_MAP` | ✅ 唯一数据源 |
| 2 | `native/gugu_native/pages/chat_page.py` | `_EXPRESSION_KEYWORDS` / `_EXPRESSION_MAP` | ⚠️ 需手动同步或改为 import |
| 3 | `app/web/static/index.html` | L6824 `expressionKeywords` / `expressionMap` | ⚠️ **需手动同步**（JS 无法 import Python） |

---

### 5. 互斥体名称

**唯一数据源**：`app/shared_config.py` → `MUTEX_NAME_BASE`

| # | 文件 | 位置 | 说明 |
|---|------|------|------|
| 1 | `app/shared_config.py` | `MUTEX_NAME_BASE` / `MUTEX_NAME_LAUNCHER` / `MUTEX_NAME_NATIVE` | ✅ 唯一数据源 |
| 2 | `launcher/launcher.py` | L837 互斥体创建 | ✅ 已改为 `from app.shared_config import MUTEX_NAME_LAUNCHER` |
| 3 | `native/gugu_native/widgets/dual_mode_compat.py` | `DualModeCompat` | ✅ 已改为从 shared_config import |

两种模式使用不同后缀（`_Launcher` vs `_Native`），但共享同一前缀，因此可以互相检测。

---

### 6. 端口号

| # | 文件 | 位置 | 说明 |
|---|------|------|------|
| 1 | `app/config.yaml` | `web.port` / `web.ws_port` | 配置文件（运行时读取） |
| 2 | `app/main.py` | 默认值 | CLI 启动参数 |
| 3 | `launcher/launcher.py` | L78-79 `BACKEND_PORT=12393` / `BACKEND_WS_PORT=12394` | ⚠️ 硬编码，不读 config.yaml |
| 4 | `native/gugu_native/widgets/dual_mode_compat.py` | `WEBUI_HTTP_PORT=12393` / `WEBUI_WS_PORT=12394` | 硬编码 |
| 5 | `app/web/__init__.py` | 端口定义 | Web 服务器 |

**⚠️ 改端口时务必修改以上 5 处**

---

### 7. Live2D 默认模型路径

| # | 文件 | 位置 |
|---|------|------|
| 1 | `native/gugu_native/pages/chat_page.py` | L638-641 `_load_default_model()` |
| 2 | `native/gugu_native/widgets/desktop_pet.py` | L139-142 `_load_model()` |

路径相同：`PROJECT_DIR/app/web/static/assets/model/hiyori/Hiyori.model3.json`

---

### 8. GPT-SoVITS 模型下载列表

| # | 文件 | 位置 | 说明 |
|---|------|------|------|
| 1 | `native/gugu_native/pages/model_download_page.py` | L47-172 | 原生桌面模式下载页 |
| 2 | `scripts/setup.py` | L472-593 | 安装脚本 |

6 个模型的 URL、路径、大小阈值完全相同，需手动同步。

---

### 9. 项目根目录路径计算

18+ 个文件使用 `os.path.dirname(os.path.dirname(...))` 多层嵌套计算项目根目录。

示例：
```python
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
```

**涉及文件**：
- `app/main.py`, `app/tts/__init__.py`, `app/live2d/__init__.py`
- `launcher/launcher.py`
- `native/main.py`
- `native/gugu_native/pages/chat_page.py`, `settings_page.py`, `model_download_page.py`
- `native/gugu_native/widgets/desktop_pet.py`, `voice_manager.py`, `hotkey_manager.py`, `perf_manager.py`, `tray_manager.py`, `update_manager.py`, `dual_mode_compat.py`

**如果项目目录结构发生变化**，所有这些文件都需要修改。建议后续统一使用 `app.version` 或 `app.shared_config` 中的 `PROJECT_DIR` 常量。

---

### 10. 单实例互斥逻辑

| # | 文件 | 说明 |
|---|------|------|
| 1 | `launcher/launcher.py` L807-876 | `_acquire_single_instance_lock()` |
| 2 | `native/gugu_native/widgets/dual_mode_compat.py` L59-105 | `DualModeCompat.acquire_native_mutex()` |

✅ 已统一互斥体名称（见第 5 项）。代码逻辑仍有重复，但功能独立。

---

### 11. DLL 解锁逻辑

| # | 文件 | 说明 |
|---|------|------|
| 1 | `launcher/launcher.py` | `_unblock_dlls()` |
| 2 | `scripts/setup.py` | `unlock_dlls()` |

同一 PowerShell `Unblock-File` 命令，范围略有不同。

---

### 12. TTS 引擎重建逻辑

| # | 文件 | 位置 | 说明 |
|---|------|------|------|
| 1 | `native/gugu_native/pages/chat_page.py` | `_apply_tts_to_backend()` | pop _lazy_modules + cleanup + rebuild |
| 2 | `native/gugu_native/pages/settings_page.py` | `_save_tts_config()` | 相同的 pop + cleanup + rebuild 模式 |

---

### 13. ASR Worker 类

| # | 文件 | 说明 |
|---|------|------|
| 1 | `native/gugu_native/widgets/voice_manager.py` | `_ASRWorker` |
| 2 | `native/gugu_native/pages/chat_page.py` | `ASRWorker` |

相同的 recognize + emit + cleanup 逻辑，可抽取为公共类。

---

### 14. 工具调用过滤逻辑

| # | 文件 | 说明 |
|---|------|------|
| 1 | `app/web/__init__.py` | `_filter_reply()` |
| 2 | `app/web/__init__.py` | `WebSocketServer._strip_tool_calls()` |
| 3 | `app/proactive.py` L271 | 过滤 TOOL:/ARG:/BASH: |

三处过滤相同的标记前缀。

---

## 🔧 架构改进说明

### 已完成的统一

| 项目 | 统一前 | 统一后 |
|------|--------|--------|
| 版本号 | 3 个不同值（1.9.86/1.9.83/1.9.64）硬编码在 6 处 | `app/version.py` 单一数据源，所有文件引用 |
| LLM Provider 配置 | Python/JS 各一份，settings_page.py 独立维护 | `app/shared_config.py` 单一数据源 |
| Edge TTS 音色 | 3 处不一致列表 | `app/shared_config.py` 单一数据源，JS 需手动同步 |
| 互斥体名称 | launcher 和 native 名称不同，互相检测不到 | `app/shared_config.py` 统一前缀 |
| 表情关键词 | Python/JS 两份 | `app/shared_config.py` 单一数据源，JS 需手动同步 |
| Live2D os.chdir | 改变整个进程工作目录 | 使用 Handler directory 参数，不改变 CWD |
| TTS 类变量 | `_is_playing` 等直接类变量，实例可遮蔽 | 改用 property 桥接，确保始终操作类级别数据 |

### JS 同步注意事项

由于 `index.html` 中的 JS 无法 import Python 模块，以下数据需修改后**手动同步**：

1. **`_providerConfig`** ← `app/shared_config.py:PROVIDER_CONFIG`
2. **`voiceOptions.edge`** ← `app/shared_config.py:EDGE_VOICES`
3. **`expressionKeywords` / `expressionMap`** ← `app/shared_config.py:EXPRESSION_KEYWORDS/EXPRESSION_MAP`

修改 `app/shared_config.py` 后，搜索 index.html 中对应的变量名，逐一同步。

---

## 📝 版本发布检查清单

发布新版本时，按以下步骤操作：

- [ ] 修改 `app/version.py` 中的 `VERSION`
- [ ] 更新 `docs/VERSION.md` 添加版本记录
- [ ] 检查 `app/web/static/index.html` 中的 `_providerConfig` 是否与 `shared_config.py` 一致
- [ ] 检查 `app/web/static/index.html` 中的 `voiceOptions.edge` 是否与 `shared_config.py` 一致
- [ ] 检查 `app/web/static/index.html` 中的 `expressionKeywords` 是否与 `shared_config.py` 一致
- [ ] 检查 `app/tts/__init__.py` 的 `EdgeTTS.VOICES` 是否与 `shared_config.py` 一致
- [ ] 确认 `native/main.py` 和 `launcher/launcher.py` 不再有硬编码版本号
- [ ] 运行 `grep -rn "1\.9\.\|v1\.9\." --include="*.py" --include="*.html" app/ native/ launcher/` 检查遗漏
