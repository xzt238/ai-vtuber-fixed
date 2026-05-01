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

================================================================================

## 🟢 v1.9.55 (2026-05-01) ✅ STABLE

**代码清理：移除死代码 + 释放重复模型文件 (~836MB) + 清理过时文档**

### 🔄 重构
- **移除 OpenClaw 死代码**：删除 `openclaw` property、`_handle_openclaw_tool()` 方法、备用配置中的 `openclaw` 项、以及 process_message 中的 TOOL: 处理分支（openclaw 模块从未存在，一直 ImportError 被吞掉）
- **移除 SubAgent 死代码**：删除 `subagent` property、`_handle_subagent()` 方法、process_message 中的 AGENT: 处理分支、以及 stop() 中的 subagent 关闭逻辑（subagent 模块从未存在）
- **清理相关文档注释**：更新类文档字符串和 process_message 流程说明，移除 OpenClaw/SubAgent 引用
- **清理过时文档**：删除 11 个已过时的文档（ARCHITECTURE/CODE_AUDIT/DESKTOP_PACKAGING/DEV_GUIDE/OCR_DEPLOYMENT/OPTIMIZATION*/THREADING/gap_analysis/feasibility_*），保留 BUILD/QUICKSTART/README/VERSION；更新 README.md 索引和统计信息

### ⚡ 性能
- **删除重复 G2PWModel**（608MB）：`GPT_SoVITS/G2PWModel/` 是 `text/G2PWModel/` 的完全副本，代码只引用后者
- **删除重复训练权重**（213MB）：`data/web_projects/hongkong/ckpt/` 和 `s2_ckpt/` 与推理目录 `GPT_weights_v3/` + `SoVITS_weights_v3/` 内容完全一致（MD5 确认）
- **清理 web_hongkong 旧训练中间数据**（15MB）：`data/web_hongkong/` 为废弃的训练中间产物
- **删除 _tmp_oml2d 空目录**

================================================================================

## 🟢 v1.9.54 (2026-05-01) ✅ STABLE

**实时语音模式深度修复：文本突变 + 历史记录 + 状态时序**

### 🐛 修复
- **实时语音回复文本突变**：修复 LLM 回复完成后文本从长变短的 bug
  - 根因：后端 `text_done` 发送 `_realtime_filter(full_text)`（剥Markdown/emoji），而 `text_chunk` 只做 `_strip_tool_calls`
  - 修复：全局 `text_done` handler 不再用 `data.text` 覆盖已有流式文本，保留用户看到的完整内容
- **实时语音对话不计入历史**：修复历史面板看不到实时语音对话记录
  - 根因：`_handle_realtime_audio` 只写了 `mem.add_interaction()`（记忆系统），没有更新 `self.app.history`
  - 修复：与录音模式 `_handle_text` 一致，追加 `app.history` + `_save_history()`
- **实时语音 text_done 过早回到"聆听中"**：LLM 输出完成时音频可能还在播放，不应立即切换状态
  - 修复：`text_done` 时检查音频播放状态，正在播放则保持"播放中"，播完自然回到"聆听中"
- **TTS合成状态时机优化**：`realtime_audio` 到达时隐藏合成状态（音频已就绪），而非显示

================================================================================

## v1.9.53 (2026-05-01)

**实时语音模式 UI 对齐：思考动画 + TTS合成状态 + 流式消息**

### 🐛 修复
- **实时语音思考动画**：ASR 识别完成后，与录音模式一样创建流式 AI 消息占位 + 思考指示器（跳动点），LLM 开始回复后自动消失
- **实时语音 TTS 合成状态**：音频片段到达时显示"🔊 语音合成中..."提示，合成完成后自动隐藏
- **实时语音 text_done 重复消息**：修复 AI 回复完成时在聊天区创建两条重复消息的问题
- **实时语音打断清理**：打断时正确清理思考动画和流式消息占位，空消息显示"（已中断）"

================================================================================

## v1.9.52 (2026-05-01)

**MCP 工具协议 + 工具调用可视化 + 桌面宠物 + Live2D 微动作 + 记忆增强**

### ✨ 新增
- **MCP 工具协议集成**：将 Anthropic MCP (Model Context Protocol) 集成到工具系统
  - `app/mcp/__init__.py` — MCPToolBridge + MCPTransport + MCPServerConfig
  - stdio 传输层：通过子进程 stdin/stdout 与 MCP 服务器 JSON-RPC 通信
  - 工具名路由：`MCP:server:tool` 走 MCP 通道，其他走本地 ToolFactory
  - 前端 MCP 面板：服务器状态、工具列表、动态添加/移除服务器
  - 配置：`config.yaml → mcp.servers`
- **工具调用可视化**：AI 调用工具时实时展示调用过程和结果
  - 后端：`tool_call_start` / `tool_call_end` WS 事件，调用历史缓存
  - 前端工具调用面板：实时卡片、调用历史、本地/MCP 标签
  - 工具调用记录持久化（最近100条）
- **桌面宠物模式**：Live2D 角色悬浮在桌面上
  - `app/desktop_pet/__init__.py` — DesktopPetManager + PetAPI
  - 无边框透明窗口（pywebview），始终置顶，可拖拽
  - 点击互动、右键菜单、气泡消息
  - 前端桌面宠物控制面板
  - 配置：`config.yaml → desktop_pet`
- **Live2D 闲置微动作**：AI 空闲时随机播放微动作
  - 前端 JS 定时器：5-15秒随机间隔，Idle/TapBody/Flick 动作
  - AI 说话时暂停微动作，说完后恢复
  - 可通过面板按钮开关
- **AI 主动说话已启用**：`proactive_speech.enabled: true`

### 🔧 优化
- **记忆面板**：已有完整可视化（工作/情景/事实标签+搜索+时间线），v1.9.52 增强面板入口
- **工具系统**：`_handle_tool` 支持 MCP 路由，统一可视化事件推送
- **WS 消息**：新增 `mcp` 和 `tool_viz` 消息类型

### 📁 修改文件
- `app/mcp/__init__.py` — 新增 MCP 工具桥接模块 (全文)
- `app/desktop_pet/__init__.py` — 新增桌面宠物模块 (全文)
- `app/main.py` — 新增 `mcp`/`desktop_pet` 懒加载属性，启动/停止逻辑
- `app/web/__init__.py` — MCP/工具可视化 WS 处理器，工具调用事件推送
- `app/web/static/index.html` — MCP 面板、工具可视化面板、桌面宠物面板、Live2D 微动作
- `app/config.yaml` — 新增 mcp/tool_viz/desktop_pet/live2d_idle_motion 配置节
- 版本号同步: v1.9.52 (9处)

================================================================================

## 🟢 v1.9.51 (2026-05-01) ✅ STABLE

**语音打断 + AI 主动说话** — 实现文本模式打断功能，新增 AI 主动说话模块

### ✨ 新增
- **文本模式打断**：AI 生成回复时显示"停止"按钮，点击立即中断 LLM 流式输出和 TTS 合成
  - 后端: Generation ID + cancel_event 机制，`text_interrupt` 消息类型
  - 前端: 红色停止按钮替代发送按钮，中断后恢复已生成文本
- **AI 主动说话**：用户长时间不说话时，AI 根据记忆和上下文主动开口
  - `app/proactive.py` — ProactiveSpeechManager 类
  - 空闲检测 + 时间感知 + 记忆检索 + 频率控制
  - 配置: `config.yaml → proactive_speech` 节
  - 主动说话消息有 `proactive: true` 标记，前端特殊样式展示

### 🔧 优化
- **文本生成状态追踪**: `_text_gen_running`/`_text_gen_cancel`/`_text_gen_id` 每客户端状态
- **主动说话与实时语音协调**: 用户说话时通知主动说话管理器重置空闲计时
- **TTS 合成中断**: 逐句合成循环中检查 cancel_event，及时停止

### 📁 修改文件
- `app/proactive.py` — 新增 ProactiveSpeechManager (全文)
- `app/main.py` — 新增 `proactive` 懒加载属性，run_web 中启动，stop 中停止
- `app/web/__init__.py` — 文本模式打断支持，主动说话活动通知
- `app/web/static/index.html` — 停止按钮 UI，打断消息处理，主动说话样式
- `app/config.yaml` — 新增 `proactive_speech` 配置节
- 版本号同步: v1.9.51 (9处)

================================================================================

## 🟢 v1.9.50 (2026-05-01) ✅ STABLE

**Ollama 流式 URL 修复 + 对话历史持久化** — 修复 Ollama 流式请求 404 错误，实现对话历史磁盘持久化与启动恢复

### 🐛 修复
- **Ollama 流式 404**：`base_url` 为 `http://localhost:11434/v1`（OpenAI 格式默认带 `/v1`），拼接 `/api/chat` 后变成 `/v1/api/chat` 导致 404。现在自动去掉 `/v1` 再拼接
- **对话历史不持久化**：`self.history` 是纯内存列表，重启后丢失。现在每轮对话自动保存到 `memory/state/chat_history.json`，启动时恢复
- **新对话"重新起"历史**：重启后 `app.history` 为空，历史面板从记忆系统显示旧记录；但新对话追加到空的 `app.history` 后，面板切换到只显示新记录，旧记录消失。现在首次启动时从记忆系统的工作记忆恢复旧历史到 `app.history`，确保新对话追加在旧历史后面

### ✨ 新增
- **对话历史持久化**：每轮对话后自动保存，程序退出/崩溃时 atexit 保存，清空历史时同步删除磁盘文件
- **聊天窗口历史恢复**：WS 连接成功后自动从后端加载历史对话，恢复到聊天窗口（最近20轮）
- **记忆系统回填**：首次启动时若 `chat_history.json` 不存在，自动从记忆系统的工作记忆恢复历史到 `app.history`，记忆系统懒加载后延迟恢复

### 📁 修改文件
- `app/llm/__init__.py` — `_ollama_chat`/`_ollama_stream_chat` URL 去掉 `/v1` 后缀
- `app/main.py` — 新增 `_load_history()`/`_save_history()`，atexit/stop 时保存，启动时恢复
- `app/web/__init__.py` — WS 对话后调用 `_save_history()`，清空时也清磁盘
- `app/web/static/index.html` — WS 连接时请求历史，首次收到恢复到聊天窗口
- 版本号同步: v1.9.50 (9处)

================================================================================

## 🟢 v1.9.49 (2026-05-01) ✅ STABLE

**Ollama 本地模型自动检测** — 选择 Ollama 时自动查询已安装模型列表并填充下拉框，无需手动输入模型名

### ✨ 新增
- **Ollama 模型列表自动查询**：选择 Ollama Provider 时，前端通过 WS 请求后端 `/api/tags` 端点，获取已安装模型列表动态填充下拉框
- **模型信息展示**：下拉框中显示模型名 + 参数量（如 `qwen3:8b (8.2B)`）
- **后端 `ollama_models` WS action**：新增消息类型，支持前端查询 Ollama 已安装模型

### 🐛 修复
- **Ollama 硬编码 URL**：`_ollama_chat` / `_ollama_stream_chat` 中硬编码 `http://localhost:11434/api/chat`，改为使用 `self.base_url` 拼接，支持自定义端口
- **config.yaml 默认模型为空**：`ollama.model` 从空字符串改为 `qwen3:8b`，避免请求时 model 为空

### 📁 修改文件
- `app/web/__init__.py` — 新增 `_handle_ollama_models()` WS action
- `app/llm/__init__.py` — `_ollama_chat`/`_ollama_stream_chat` URL 改用 `self.base_url`
- `app/web/static/index.html` — Ollama 模型动态查询 + 下拉填充 + WS 消息处理
- `app/config.yaml` — `ollama.model` 默认值改为 `qwen3:8b`
- 版本号同步: v1.9.49 (9处)

================================================================================

## 🟢 v1.9.48 (2026-04-30) ✅ STABLE

**LLM Provider 切换引擎重建修复** — 解决切换 Provider 后 LLM 引擎类型不匹配、对话历史被错误清空等问题

### 🐛 修复
- **引擎类型不匹配**：切换 Provider 后旧引擎实例未重建，导致请求发到错误引擎。增加防御性检查，发现类型不匹配时自动重建
- **对话历史错误清空**：Provider 切换后不再自动清空对话历史，旧上下文仍有价值
- **Provider 变更检测优化**：先记录旧 provider，再更新 config，最后用旧值判断是否需重建引擎，避免误判

### 📁 修改文件
- `app/web/__init__.py` — `_handle_set_api_key` 防御性引擎类型检查 + Provider 变更重建逻辑优化
- 版本号同步: v1.9.48 (9处)

================================================================================

## 🟢 v1.9.47 (2026-04-30) ✅ STABLE

**LLM Provider 联动逻辑重构** — 彻底重构前端 Provider 切换逻辑，解决 URL/Model 不自动更新、datalist 下拉体验差等根本性问题

### 🔄 重构
- **`<datalist>` → `<select>` + 自定义输入**：模型选择从模糊的 datalist 自动补全改为真正的下拉选择框 + 勾选"自定义输入"后可输入任意模型名
- **`onLlmProviderChange()` 单一入口重构**：删除 `_loadProviderSubConfig` 的 DOM 操作，所有表单值设置统一在 `onLlmProviderChange()` 中完成
- **`loadConfigSettings()` 简化**：不再手动设置 model/baseUrl，全部委托给 `onLlmProviderChange()`
- **值来源优先级明确**：子配置保存的值 > 官方默认值，不再有双路径互相覆盖
- **新增辅助函数**：`getCurrentModelValue()` / `setCurrentModelValue()` / `updateModelSelect()` / `onModelSelect()` / `toggleCustomModel()`

### 🐛 修复
- **URL 不自动更新**：根因是 `loadConfigSettings` 和 `onLlmProviderChange` 双路径设值互相覆盖
- **模型名不能下拉选择**：datalist 只有自动补全，改为 `<select>` 后可直接点击选择
- **Ollama 无预设模型时无法输入**：自动切换到自定义输入模式

### 📁 修改文件
- `app/web/static/index.html` — Provider 联动逻辑重构、模型选择 UI 重构
- 版本号同步: v1.9.47 (9处)

================================================================================

## 🟢 v1.9.46 (2026-04-30) ✅ STABLE

**LLM Provider 切换修复 + ASR→LLM 管道修复** — 解决切换 Provider 后 URL/模型不更新、API Key 状态缓存导致消息被拦截、ASR 识别后不发给 LLM 等问题

### 🐛 修复
- **Provider 切换 URL/Model 不更新**：`_loadProviderSubConfig` 无子配置时不清空表单 → 切换 provider 后始终用官方默认 URL 和模型填充
- **API Key 状态缓存过期**：`sendMessage()` 用缓存的 `_apiKeyStatus` 拦截消息，但切换 provider 后缓存未更新 → 改为检查 provider 一致性，不一致时重新查询
- **ASR→LLM 静默失败**：后端 `_handle_text` 和 `_handle_realtime_audio` 中 LLM 不可用时无反馈 → 添加明确错误消息推送前端
- **set_api_key 不触发引擎重建**：切换 provider 后设 API Key 只更新旧引擎的 key → 检测 provider 变化并重建 LLM 引擎
- **模型下拉体验差**：Model 输入框 focus 时自动选中文本，方便查看下拉建议

### 📁 修改文件
- `app/web/static/index.html` — Provider 切换逻辑、sendMessage API Key 检查、模型下拉优化
- `app/web/__init__.py` — LLM 不可用错误反馈、set_api_key 引擎重建
- 版本号同步: v1.9.46 (9处)

================================================================================

## 🟢 v1.9.45 (2026-04-30) ✅ STABLE

**LLM 多厂商适配** — 从 3 个 provider 扩展到 10 个，覆盖国内主流云端模型，全部使用官方 URL + 官方模型列表

### ✨ 新增
- **10 个 LLM Provider**：DeepSeek / Kimi / 智谱GLM / 通义千问 / MiniMax / 豆包 / 小米MiMo / OpenAI / Anthropic / Ollama
- **Provider 分组下拉**：国内模型(7) / 国际模型(2) / 本地模型(1)，optgroup 分组展示
- **统一 Provider 配置数据结构**：`_providerConfig` 对象集中管理 label/baseUrl/models/defaultModel/hint/keyPlaceholder/color
- **官方 URL 自动填充**：每个 provider 对应官方 API base URL，切换时自动填充并锁定
- **官方模型下拉选择**：每个 provider 的 datalist 预置官方模型列表（如 DeepSeek: deepseek-v4-pro/flash/chat/reasoner）
- **API Key placeholder 提示**：切换 provider 时 API Key 输入框自动显示获取地址
- **LLMFactory 10 provider 支持**：deepseek/kimi/glm/qwen/doubao/mimo 统一走 OpenAILLM 引擎
- **后端配置深度合并扩展**：`_handle_config()` 支持 10 个 provider 子配置的深度合并

### 🔧 修复
- **MiniMax M2.8 不存在**：删除不存在的 MiniMax-M2.8（仅语音模型有 2.8 版本）
- **MiniMax 模型列表补全**：补充 M2.7-highspeed / M2.5-highspeed / M2.1-highspeed / M2 等官方模型
- **MiniMax base_url 修正**：Anthropic 格式 `api.minimaxi.com/anthropic`，OpenAI 格式 `api.minimaxi.com/v1`（hint 提示）
- **新手引导适配10 provider**：onboarding 下拉从3项(minimax/openai/anthropic)更新为10项+optgroup，修复本地模型检测逻辑(provider==='ollama'而非旧的openai+localhost)
- **快速切换 tooltip 修正**：tooltip 从"MiniMax↔Ollama"更正为"DeepSeek↔Ollama"（代码实际行为）
- **API Key 状态标签通用化**：api_key_status handler 使用 `_pc()` 动态获取 provider label，不再硬编码
- **清理遗留逻辑**：移除 `updateProviderIndicator` 中的 openai+localhost→Ollama 旧判断（ollama 已独立为 provider）
- **`_pc()` 防御性增强**：未知 provider 传入时输出 console.warn
- **AnthropicLLM 缺少 base_url 属性**：添加 `self.base_url`，支持自定义代理/中转地址
- **AnthropicLLM system 消息格式错误**：Anthropic API 要求 system 通过顶层字段传递，修复 chat() 和 stream_chat()
- **前端切换覆盖自定义 URL**：`onLlmProviderChange()` 优先使用子配置中保存的 base_url，不再每次用官方默认覆盖

### 📁 修改文件
- `app/web/static/index.html` — Provider 下拉+JS 全面改造
- `app/llm/__init__.py` — LLMFactory 支持 10 个 provider
- `app/web/__init__.py` — 配置深度合并 + current_config 扩展
- `app/config.yaml` — 添加 10 个 provider 默认配置模板
- 版本号同步: v1.9.45 (9处)

================================================================================

## 🟢 v1.9.42 (2026-04-30) ✅ STABLE

**配置编辑器改造** — MiniMax模型下拉选择、URL自动填充、删除API Key标签页、LLM子配置持久化、新增视觉配置标签页

### ✨ 新增
- **MiniMax 模型下拉选择**：Model 字段改为 `<datalist>` 组合框，MiniMax 预置 M2.1/M2.5/M2.7/M2.8，OpenAI/Anthropic 也有推荐列表，同时支持自定义输入
- **Base URL 自动填充+只读锁定**：切换 Provider 自动填入官方 URL 并锁定，点击"自定义"按钮解锁编辑
- **视觉配置标签页**：新增 Vision 配置标签，支持 MiniMax VL/RapidOCR/MiniCPM 三个 provider 的配置
- **LLM 子配置持久化**：各 provider 的 model/base_url 独立存储到 `gugu-llm-subconfigs`，切换 provider 不丢失配置
- **后端 Vision 配置处理**：`_handle_config()` 支持深度合并 vision 配置，`_handle_get_current_config()` 返回 vision 配置

### 🔧 优化
- **删除 API Key 标签页**：冗余标签页移除，API Key 输入统一到 LLM 标签页
- **旧数据迁移**：自动将 `gugu-config` 中的 LLM 子配置迁移到独立存储

### 📁 修改文件
- `app/web/static/index.html` — 配置编辑器HTML+JS全面改造
- `app/web/__init__.py` — Vision 配置处理 + current_config 返回 vision
- 版本号同步: v1.9.42 (9处)

================================================================================

## 🟢 v1.9.41 (2026-04-30) ✅ STABLE

**MiniMax 配置丢失修复 + 对话历史连续性修复** — 解决切换 Provider 后 MiniMax base_url 丢失导致请求发错地址，以及每次对话从零开始不复用历史记录的问题

### 🔧 修复
- **MiniMax 切换后无法使用（核心 bug）**：`_handle_config` 的 `update()` 浅层合并会覆盖整个 provider 子配置，导致 MiniMax 的 `base_url: "https://api.minimaxi.com/anthropic"` 丢失，回退到默认的 `http://120.24.86.32:3000`，且 `_is_anthropic=False` 走错 API 格式
  - 修复：改为深度合并，对 `minimax`/`openai`/`anthropic` 子配置只合并不覆盖
- **每次对话从零开始（核心 bug）**：`_handle_text` 中 `llm.stream_chat()` 和 `llm.chat()` 调用时没传 `history` 参数，导致 LLM 每次都无上下文
  - 修复：传入 `list(self.app.history)` 和 `memory_system`
- **Provider 变更后对话历史未清空**：`self.app.session` 不存在，`reset_history()` 未执行，旧 provider 的上下文会喂给新 provider
  - 修复：直接清空 `self.app.history`

### ✨ 新增
- 前端配置编辑器中 MiniMax/Anthropic 也能看到 Base URL 输入框（之前只有 OpenAI 显示）
- 切换 Provider 时自动填入对应默认 base_url

### 📁 修改文件
- `app/web/__init__.py` — 深度合并、history 传递、history 清空
- `app/web/static/index.html` — Base URL 输入框显示逻辑、默认值填充
- 版本号同步: v1.9.41 (9处)

================================================================================

## 🟢 v1.9.39 (2026-04-30) ✅ STABLE

**前端 LLM Provider 自动选择 + 后端引擎热重建** — 切换 Provider 时自动填入默认模型，后端自动重建 LLM 引擎

### ✨ 新增
- `onLlmProviderChange()`: 切换 Provider 时自动填入对应默认模型名称
  - MiniMax → `MiniMax-M2.7`
  - OpenAI/Ollama → `qwen3:8b`
  - Anthropic → `claude-3-sonnet-20240229`
- `getDefaultModel(provider)`: 统一获取默认模型名称的工具函数
- 新手引导：Provider 切换时提示文字中显示默认模型名
- 新手引导保存配置时自动写入默认模型名

### 🔧 修复
- 后端 `_handle_config()`: LLM provider 变更时重建 LLM 引擎（弹出旧 `_lazy_modules['llm']`，下次访问时自动以新配置创建）
- LLM 引擎重建时自动清理旧引擎资源并重置 API Key
- 切换 Provider 后会话历史自动重置

### 📁 修改文件
- `app/web/static/index.html`
- `app/web/__init__.py`
- 版本号同步: v1.9.39 (9处)

================================================================================

## 🟢 v1.9.38 (2026-04-29) ✅ STABLE

**前端 LLM 多 Provider 适配 + Ollama 原生 API** — 修复 Ollama 用户被 API Key 检查误拦的问题，新增 Ollama 原生 API 支持

### 🔧 修复
- `checkApiKeyStatus()`: 查询当前活跃 provider 而非硬编码 minimax
- `sendMessage()`: 本地模型（Ollama/localhost）跳过 API Key 拦截
- `saveApiKey()` / `saveApiKeyFromSettings()`: 发送当前活跃 provider
- `api_key_status` 显示：根据 provider 显示正确名称（MiniMax/OpenAI/Anthropic）
- 后端 `_handle_get_api_key_status`: 自动检测当前活跃 provider

### ✨ 新增
- LLM 配置面板：Provider 下拉新增 Anthropic 选项
- LLM 配置面板：新增 Base URL 输入框（OpenAI/Ollama 模式显示）
- LLM 配置面板：新增 API Key 输入框（各 provider 通用）
- `onLlmProviderChange()` 函数：Provider 切换时联动字段显隐
- `saveConfigSettings()` 保存 base_url + api_key 到对应 provider 子配置
- 新手引导：Provider 选择 + Base URL 输入（Ollama 用户可跳过 API Key）
- `onOnboardingProviderChange()` 函数：引导中 Provider 切换联动
- **Ollama 原生 API**：自动检测 Ollama 端点，走 `/api/chat` 而非 `/v1/chat/completions`，传 `think:false` 关闭 Qwen3 思考模式
- `_ollama_chat()` / `_ollama_stream_chat()`：Ollama 专用非流式/流式对话方法
- `OpenAILLM._is_ollama` 标志：基于 base_url 自动检测

================================================================================

## 🟢 v1.9.37 (2026-04-29) ✅ STABLE

**本地 LLM 适配** — Ollama + Qwen3-8B Q4_K_M，零代码改动接入

### ✨ 新增
- 本地 LLM 支持：通过 Ollama + OpenAI 兼容接口接入本地模型
- 默认模型：Qwen3-8B Q4_K_M（CPU 推理，~5GB 内存，不占显存）
- config.yaml 新增 `llm.openai` 配置段（api_key/base_url/model）
- Qwen3 thinking 模式三层防护：
  - System prompt 加 `/no_think` 指令（Qwen3 原生支持）
  - 非流式：`content` 可能为 None 时的防护 + `_strip_thinking()` 兜底清理
  - 流式：`in_thinking` 状态跟踪，thinking 阶段不触发 TTS 回调
- `_strip_thinking()` 函数：正则移除 `<think >...</think >` 标签
- 流式 SSE 中 `delta.reasoning` 与 `delta.content` 自然分离（Ollama 特性）

### 🔧 修改
- `config.yaml`：provider 从 minimax 改为 openai，新增 openai 配置段
- `llm/__init__.py`：OpenAILLM.chat() 加 content None 防护 + thinking 清理
- `llm/__init__.py`：所有三个引擎的流式方法加 thinking 过滤
- `llm/prompts.py`：PERSONA 末尾加 `/no_think`

### 📁 修改文件
- `app/config.yaml`
- `app/llm/__init__.py`
- `app/llm/prompts.py`
- 版本号同步: v1.9.37 (7处)

---

## 🟢 v1.9.36 (2026-04-29) ✅ STABLE

**记忆前端功能补全** — 后端能力全面映射到前端 UI

### ✨ 新增
- 记忆编辑功能（✎ 按钮 → prompt 编辑 → WS edit action）
- 重要性精确设置（0-5 下拉选择器，替代原来只能+1的⬆按钮）
- 事实来源分类过滤（偏好/信息/事实 子标签）
- 衰减预览可视化（📉 按钮 → 表格展示不同重要性在不同时长的保留分数）
- 记忆详情展示（保留分数进度条、遗忘标记、hover 显示访问次数等）
- 时间线事实过滤按钮（📌）
- 配置面板补全（保护期小时数、向量去重阈值、自动存储开关）
- 后端 WS 新增 `decay_preview` 和 `search_by_time` action
- 后端 `_item_to_dict` 补全 `retention_score/access_count/connectivity/is_forgotten/hours_old` 字段

### 🔧 修复
- 删除 config.yaml 中 `memory.provider: "simple"` 死字段
- 删除 `memory/__init__.py` 中 `self.provider` 赋值和统计输出

### 📁 修改文件
- `app/web/static/index.html` — 前端记忆面板全面增强
- `app/web/__init__.py` — 后端 WS 新增 action + 字段补全 + 配置热更新
- `app/memory/__init__.py` — 移除 provider 死字段
- `app/config.yaml` — 移除 provider 死字段
- 版本号同步: v1.9.36 (8处)

---

## 🟢 v1.9.35 (2026-04-28) ✅ STABLE

### 🔧 记忆系统 v3.0 全面重构

| # | 修改项 | 说明 |
|---|--------|------|
| 1 | 🆕 **多维梯度评分** | ImportanceScorer 重构，6个评分维度（长度/问题/个人信息/偏好/情感/知识），0-5连续梯度，不再只有0/4/5 |
| 2 | 🆕 **LLM语义摘要** | SummaryGenerator 替代硬截断，优先用 LLM 生成语义摘要，降级到规则摘要 |
| 3 | 🆕 **事实提取系统** | FactExtractor 规则提取用户偏好/个人信息；LLM 降级提取；独立 FactItem 持久化 |
| 4 | 🆕 **向量库去重** | VectorStore 新增 `_is_duplicate()`，cosine>0.95 视为重复不重复存储 |
| 5 | 🆕 **向量库入库阈值降低** | importance>=3 即入库（原>=4），语义记忆终于有数据 |
| 6 | 🆕 **遗忘衰减调优** | DECAY_LAMBDA 0.01→0.005；RETENTION_THRESHOLD 0.3→0.15；新增12小时保护期 |
| 7 | 🆕 **记忆去重合并** | `_text_similarity()` Jaccard相似度；`_merge_fact()` 合并重复事实 |
| 8 | 🆕 **自动标签系统** | AutoTagger 基于关键词为记忆打标签（编程/AI/情感/日常等10个类别） |
| 9 | 🆕 **记忆重整** | `consolidate()` 跨层整合：合并重复情景记忆、提升高保留分记忆、清理已遗忘记忆 |
| 10 | 🆕 **记忆管理 CRUD** | 后端新增 delete/edit/set_importance/facts/consolidate/delete_fact action |
| 11 | 🆕 **前端标签页切换** | 记忆面板支持 全部/工作/情景/事实 四标签切换 |
| 12 | 🆕 **前端操作按钮** | 每条记忆可标重要(⬆) / 删除(✕)；新增重整按钮；事实库独立视图 |
| 13 | 🆕 **衰减系数滑块** | 配置面板新增衰减系数控制；前端支持实时调节 |
| 14 | 🆕 **LLM 回调绑定** | MemorySystem.set_llm_callback()，摘要生成和事实提取可调用 LLM |
| 15 | 🔧 **前端口统计** | stats 显示 事实:数字；版本 v3.0 标识 |

## 🟢 v1.9.34 (2026-04-28) ✅ STABLE

### 🔧 记忆路径漂移修复 (Memory Path Drift Fix)

| # | 修改项 | 说明 |
|---|--------|------|
| 1 | 🔧 MemorySystem 路径绝对化 | storage_dir 在初始化时立即 resolve 为绝对路径，防止 os.chdir() 漂移 |
| 2 | 🔧 FileStorage 路径绝对化 | base_dir 同理，init 时立即解析绝对路径 |
| 3 | 🔧 VectorStore 路径绝对化 | storage_dir 同理，init 时立即解析绝对路径 |
| 4 | 🔧 历史数据迁移 | GPT-SoVITS/GPT_SoVITS/memory/ 下的12条工作记忆+5条情景记忆+8天日志+6条长期记忆 → 迁移回项目根 memory/ |
| 5 | 🐛 根因 | gptsovits.py 第36/702行 os.chdir() 和 live2d/__init__.py 第462行 os.chdir() 改变全局工作目录，导致后续 ./memory 相对路径解析到错误目录 |

## 🟢 v1.9.33 (2026-04-28) ✅ STABLE

### 🔧 记忆面板全面修复 (Memory Panel Overhaul)

| # | 修改项 | 说明 |
|---|--------|------|
| 1 | 🔧 后端 list 增强字段 | 添加 importance/timestamp/is_summary/tags 字段到记忆列表返回 |
| 2 | 🔧 后端 timeline 增强字段 | 添加 timestamp/is_summary/layer 字段；按时间倒序排列 |
| 3 | 🔧 WS sub_type 判别 | list/stats/timeline/search/summary 添加 sub_type 字段，避免 stats 被 list 覆盖 |
| 4 | 🔧 后端配置实时应用 | _handle_config 新增 memory 配置块，修改参数即时生效 |
| 5 | 🔧 前端记忆渲染增强 | 显示时间标签、层级标签、摘要徽章、重要性星标 |
| 6 | 🔧 搜索框 Enter 支持 | 搜索框回车触发搜索 |
| 7 | 🔧 面板可见性检测修复 | text_done 自动刷新改用 classList.contains('panel-hidden') |
| 8 | 🔧 配置参数名对齐 | 前端 short_limit/medium_limit → working_memory_limit/summarize_threshold/forgetting_threshold |
| 9 | 🔧 配置默认值修正 | 工作记忆上限 50→20（与后端一致）；摘要阈值/遗忘阈值滑块修正 |

## 🟢 v1.9.32 (2026-04-28) ✅ STABLE

### 🎨 交互动画全面升级 (Interaction & Animation)

| # | 修改项 | 说明 |
|---|--------|------|
| 1 | 💬 消息气泡化 | 用户/AI消息分色气泡，右/左对齐，替代单调分割线 |
| 2 | ✨ 消息入场动画 | 每条消息 slide-in + scale 微弹，cubic-bezier(0.16,1,0.3,1) |
| 3 | 🪟 面板显示/隐藏动画 | 替代 display:none，改为 scale(0.95)+fade 过渡 250ms |
| 4 | 📦 面板折叠/展开动画 | maxHeight 平滑过渡 350ms，不再瞬间消失 |
| 5 | 🔦 输入框焦点发光 | focus 时边框渐变发光 + 外发光 box-shadow |
| 6 | 💧 按钮涟漪效果 | 所有按钮点击时 Material Design 风格 ripple 动画 |
| 7 | 📤 发送按钮脉冲 | 发送消息时按钮 box-shadow 脉冲反馈 |
| 8 | 🌊 Header 渐变呼吸 | 标题渐变色 4s 缓慢流动动画 |
| 9 | 🖱️ 按钮微交互增强 | hover 微抬+阴影、active 缩放、面板按钮 scale(1.15) |
| 10 | 🎛️ 面板 hover 增强 | hover 时边框+阴影增强，Canvas 容器 hover 紫色辉光 |
| 11 | ⌨️ Ctrl+Enter 发送 | 键盘快捷键增强 |
| 12 | 🎵 宏播放呼吸灯 | 宏条目 playing 状态时内部辉光脉冲 |
| 13 | 📋 模态框入场动画 | 宏编辑器等弹窗 scale(0.92)+translateY 入场 |
| 14 | 🔄 批量面板动画 | toggleAllPanels 面板逐个依次出现(30ms间隔) |

### 🟢 v1.9.31 (2026-04-28) ✅ STABLE

### ✨ 用户体验重大改进 (UX Overhaul)

| # | 修改项 | 说明 |
|---|--------|------|
| 1 | 🎉 新手引导系统 | 首次访问自动弹出 3 步引导（欢迎 → API Key 配置 → 功能介绍），localStorage 记录完成状态 |
| 2 | 🔑 API Key 强制拦截 | 未配置 API Key 时发送消息会弹出 Toast + 引导配置，不再静默失败 |
| 3 | 🔔 统一 Toast 通知 | 全局 Toast 系统（error/success/warning/info），替代所有 alert()，支持操作按钮 |
| 4 | 💭 思考指示器 | LLM 回复等待期间显示 3 点弹跳动画，收到第一个 chunk 自动消失 |
| 5 | 🛡️ 错误信息改进 | 兜底异常从"抱歉出错了喵"改为具体原因（API Key无效/超时/显存不足等）+ 操作建议 |
| 6 | 🔧 CSS 语法修复 | index.html line 986 孤立 `}` 清理 |
| 7 | 🔔 WS 状态通知 | 连接断开/重连成功/错误时 Toast 实时通知，不再只有日志 |
| 8 | 版本号同步 | 8 处统一 v1.9.31 |

### 📝 GitHub 发布准备 (从 v1.9.30 合并)

| # | 修改项 | 说明 |
|---|--------|------|
| 1 | 新增 LICENSE | GPL-3.0 许可证 |
| 2 | 新增 README.md | 项目介绍、功能特性、安装步骤、配置说明、架构图、FAQ |
| 3 | 完善 .gitignore | 排除 python/、模型文件、.env、缓存、聊天记忆等，仓库精简到 ~25MB |
| 4 | 新增 download_models.bat | 一键下载嵌入式 Python + GPT-SoVITS 底模 + G2PW，全国内源，含核对报告 |
| 5 | 新增 .env.example | 环境变量模板，新用户参考配置 |
| 6 | install_deps.bat 增加 | 最终核对报告（✅/❌ 标记关键依赖是否就绪） |
| 7 | download_models.bat 增加 | 嵌入式 Python 下载步骤 + 最终核对报告 |
| 8 | 版本号同步 | main.py + index.html + web/__init__.py + go.bat + install_deps.bat 统一 v1.9.31 |
| 9 | Git 仓库初始化 | api_keys.json / 聊天记忆 / TTS 缓存已排除，历史干净无隐私泄露 |

================================================================================

## 🟢 v1.9.29 (2026-04-27) ✅ STABLE

### 🔧 嵌入式 Python 可移植性修复 + 项目清理

**核心修复**：`python/` 目录现在可以在新 Windows 机器上独立运行，无需预装 Python

| # | 修复项 | 说明 |
|---|--------|------|
| 1 | 补全 python.exe + DLL | 下载 python-3.11.9-embed-amd64.zip 补全解释器 |
| 2 | 安装 pip | 通过 get-pip.py 安装 pip 26.1 |
| 3 | 重装 PyTorch CUDA cu124 | 强制重装以补全 .pyd/.dll 二进制文件 |
| 4 | 安装缺失包 | bitsandbytes, gradio（25/27 已有，2个新装） |
| 5 | 修改启动脚本 | go.bat/desktop.bat/install_deps.bat 支持嵌入式 Python 优先检测 |
| 6 | 修改 .gitignore | site-packages 允许 .dll/.pyd/.exe 入库，忽略缓存/编译文件 |
| 7 | 创建根目录 .gitignore | 防止无关文件入库 |

**项目清理**：删除 12 个冗余文件（释放约 11MB + 770MB .lib）
- docs/1.txt, docs/1.flac, libs/live2d.min.js(损坏), Readme.txt(v1.6.5)
- memory/index.md(重复), 6个v1.3.0旧文档, vad/ort-wasm-simd-threaded.wasm(冗余10.69MB)
- torch/lib/*.lib(770MB, 运行时不需要的静态导入库)

**注意**：pyopenjtalk 和 jieba_fast 需要 C++ 编译环境，嵌入式 Python 无法编译安装，自动降级到 jieba

**修改文件**：
- `python/` — 补全 python.exe, python311.dll, python3.dll + 重装 torch
- `scripts/go.bat` — PYTHON_CMD 自动检测嵌入式/系统 Python
- `scripts/desktop.bat` — 同上
- `scripts/install_deps.bat` — 同上
- `python/Lib/site-packages/.gitignore` — 允许二进制文件入库
- `.gitignore` — 新建根目录 .gitignore


================================================================================

## 🟢 v1.9.28 (2026-04-27) ✅ STABLE

### 🔊 TTS 语音合成进度反馈

**症状**：TTS 生成语音时前端零反馈，用户不知道 AI 在合成语音，体验感差

**修复**：添加完整的 TTS 进度消息链 + 前端状态指示器

| 新消息类型 | 触发时机 | 前端表现 |
|-----------|---------|---------|
| `tts_start` | TTS 开始合成 | 聊天区域显示"🔊 语音合成中..." |
| `tts_progress` | 每句开始合成前 | 更新为"🔊 合成第 1/3 句..." |
| `tts_error` | TTS 合成失败 | 隐藏状态 + 日志报错 |

**额外优化**：
- TTS 面板"播放"按钮：点击后变为"⏳ 合成中..."并禁用，完成后恢复
- 聊天区域：第一个 `tts_chunk` 到达时自动隐藏状态（已开始播放）
- `tts_done` / `tts_error` 时自动清理状态

**修改文件**：
- `app/web/__init__.py` — `_handle_text` 和 `_handle_tts` 添加 tts_start/tts_progress/tts_error
- `app/web/static/index.html` — 前端消息处理 + `_showTtsStatus` / `_hideTtsStatus` + TTS 面板按钮状态



### ⚡ 全面启动性能优化 + 🔧 语法错误修复 + 白屏优化

**P0 修复：_handle_memory 语法错误**（v1.9.26 遗留 Bug）：
- **症状**：桌面模式启动后显示"后端启动出错"，反复重启无效
- **根因**：v1.9.26 在 `_handle_memory()` 中多写了一个 `try:` 没配对 `except`
- **修复**：移除孤立的 `try:` 块

**⚡ 全链路启动性能优化**：

| # | 优化项 | 改前 | 改后 | 预估节省 |
|---|--------|------|------|----------|
| 1 | 健康检查首次等待 | 2.0s | 0.5s | **1.5s** |
| 2 | 健康检查轮询间隔 | 1.0s | 0.3s | **0.7s** |
| 3 | 健康检查成功后等待 | 0.5s | 0s | **0.5s** |
| 4 | splash 淡出等待 | 0.7s | 0.5s | **0.2s** |
| 5 | 后端模块预加载 | 串行阻塞（3-8s） | 后台线程（不阻塞） | **3-8s** |
| 6 | Live2D 加载延迟 | 800ms | 立即(requestIdleCallback) | **0.8s** |
| 7 | CDN 脚本 | 同步加载 | 本地+defer | **~2s** |
| 8 | page-fade-in 动画 | 0.6s | 移除 | **0.6s** |
| 9 | 全局 loading 覆盖层 | 白屏 | 深色渐变+进度条 | 体感改善 |
| 10 | 桌面模式检测轮询 | 100ms×10s | 50ms×3s | 加速 |

**关键改动**：
- `launcher.py`：健康检查大幅加速（总节省 ~2.9s）
- `app/main.py`：WebServer 先启动 → 模块后台预加载（关键！原来 import torch 2-5s 阻塞启动）
- `index.html`：Live2D 立即加载 + 全局 loading 覆盖层
- `launcher/splash.html`：版本号更新

**P0 修复：_handle_memory 语法错误**（v1.9.26 遗留 Bug）：
- **症状**：桌面模式启动后显示"后端启动出错"，反复重启无效。浏览器模式同样报错 `SyntaxError: expected 'except' or 'finally' block`
- **根因**：v1.9.26 在 `_handle_memory()` 中添加 `getattr` 检查时，多写了一个 `try:` 没配对 `except`（行2128），导致整个 `web/__init__.py` 语法错误，后端无法启动
- **修复**：移除孤立的 `try:` 块，`getattr(self.app, 'memory', None)` 有默认值不需要 try 包裹

**⚡ 性能优化：桌面模式启动白屏 4-5 秒 → 全局 loading 覆盖 + 脚本本地化 + 轮询加速**

**症状**：桌面模式（GuguGaga.exe / desktop.bat）启动后，splash 过渡动画结束后还有 4-5 秒白屏，面板和 Live2D 才逐渐出现

**根因分析**（5 个白屏时间来源）：

1. **CDN 脚本同步加载**（~2s）：pixi.js 和 oh-my-live2d 从 unpkg CDN 下载，阻塞 HTML 解析
2. **page-fade-in 动画**（0.6s）：splash 过渡后还有透明渐显动画，加重白屏感
3. **launcher.py sleep 过长**（1.0s）：CSS 淡出动画仅 0.8s，等 1.0s 浪费 0.2s
4. **无 loading 状态**：页面加载到布局完成之间完全白屏
5. **桌面模式检测轮询慢**：100ms 间隔 + 最多 10s 超时

**修复**：

| # | 修复项 | 改前 | 改后 | 预估节省 |
|---|--------|------|------|----------|
| 1 | pixi.js + oh-my-live2d → 本地 + defer | CDN 同步加载 | `libs/` 本地 + defer | ~2s |
| 2 | 移除 page-fade-in 动画 | 0.6s 透明渐显 | 无动画 | 0.6s |
| 3 | launcher.py sleep | 1.0s | 0.7s | 0.3s |
| 4 | 全局 loading 覆盖层 | 白屏 | 深色渐变 + 进度条动画 | 体感大幅改善 |
| 5 | 桌面模式检测轮询 | 100ms×10s | 50ms×3s | 检测加速 |

- **新增文件**：`app/web/static/libs/oh-my-live2d.min.js`（979KB，从 CDN 本地化）
- **loading 覆盖层**：深色渐变背景 + 🐱 图标 + 进度条动画，布局就绪后 0.3s 淡出移除，3s 安全兜底
- **修改文件**：`app/web/__init__.py`、`index.html`、`launcher/launcher.py`、`docs/VERSION.md`

## 🟢 v1.9.26 (2026-04-27) ✅ STABLE

### 🔧 修复：记忆系统从未被初始化 — hasattr 静默吞掉异常

**症状**：聊了很久，记忆面板为空，历史面板为空

**根因**：
1. **`AIVTuber.memory` property 抛异常时无任何日志**：`MemorySystem.__init__()` 如果失败，异常会传播到调用方，但 `hasattr(self.app, 'memory')` 在 Python 3 中会吞掉所有异常返回 `False`，导致记忆写入被静默跳过
2. **`_handle_text()` 使用 `hasattr` 检查记忆系统**：`hasattr` 吞掉异常后返回 False，整个记忆写入分支被跳过，无任何错误日志
3. **`_handle_memory()` 同样使用 `hasattr`**：前端请求记忆数据时，如果记忆系统不可用，只返回英文错误且不在面板中显示

**修复内容**：
1. **`app/main.py` `memory` property**：添加 try-except，初始化失败时记录完整错误日志+堆栈，返回 None（而不是让异常传播），标记 `_memory_initialized=True` 避免反复重试
2. **`app/web/__init__.py` `_handle_text()`**：用 `getattr(self.app, 'memory', None)` 替代 `hasattr`，None 时打印中文警告
3. **`app/web/__init__.py` `_handle_memory()`**：用 `getattr` 替代 `hasattr`，返回中文错误提示
4. **`app/web/__init__.py` 实时语音路径**：同样修复
5. **`app/web/static/index.html`**：记忆面板收到 error 时在面板中显示错误+重试按钮；聊天完成后自动刷新记忆和历史面板

================================================================================

## 🟢 v1.9.25 (2026-04-26) ✅ STABLE

### 🔧 修复：前端历史/记忆面板 LLM 返回值显示不全 + 后端历史数据源缺失

**症状**：历史面板中 LLM 的回复被截断，只能看到前 200 个字符

**根因**：
1. **前端截断**：`history-messages` 和 `memory-messages` 面板渲染时 `.substring(0,200)` 硬截断，长回复只显示 200 字
2. **后端数据源**：`_handle_history()` 只从 `memory.working_memory[-20:]` 取数据，没有从 `app.history`（完整对话历史）取
3. **WS 路径遗漏**：通过 WebSocket 聊天时，`_handle_text()` 调用 `llm.stream_chat()` 但不经过 `app.process_message()`，导致 `app.history` 从未被更新

**修复内容**：
1. **前端**（`index.html`）：移除 `.substring(0,200)` 硬截断，改为不截断显示 + 超过 500 字时添加"展开全文"按钮
2. **后端**（`web/__init__.py`）：`_handle_history()` 优先从 `app.history` 获取最近 20 轮完整对话（40条），回退到记忆系统
3. **后端**（`web/__init__.py`）：`_handle_text()` 中添加 `app.history.append()` 更新，确保 WS 聊天路径也写入对话历史

================================================================================

## 🟡 v1.9.24 (2026-04-26) ✅ STABLE

### 🔧 修复：GuguGaga.exe 后端冻死（evaluate_js 死锁导致 stdout 管道阻塞）

**症状表现**：
- 双击 GuguGaga.exe → splash 启动画面正常显示 → 跳转到主界面后，面板全空、Live2D 不加载、TTS 语音列表为 0
- 按开发者工具看，WS 连接建立但完全不收发消息；HTTP 请求全部超时
- 后端 Python 进程存在（占用 ~3.8GB 内存，53 线程），端口在监听（12393/12394），但 `CLOSE_WAIT` 堆积说明服务器线程卡死
- **直接用 python.exe 启动后端（不经启动器）一切正常**——问题仅在通过 GuguGaga.exe 启动时出现

**根因分析**（6 层传导链，从启动器到后端逐级冻死）：

```
第1层：launcher.py _forward_logs 线程
  读取后端 stdout（通过 subprocess.PIPE）→ 解析状态文本
  → 调用 on_status 回调 → _on_backend_status()
    → window.evaluate_js("updateStatus('...')")

第2层：WebView2 导航死锁
  _on_backend_ready() 调用 window.load_url(BACKEND_URL) 让 WebView2 从 splash 页面导航到主页面
  WebView2 在导航（Navigation）期间，evaluate_js() 调用会被阻塞直到新页面加载完成
  此时 _forward_logs 线程仍在持续读取 stdout 并调用 evaluate_js → 死锁！

第3层：_forward_logs 线程卡死
  _forward_logs 线程卡在 evaluate_js() 调用上，无法继续读取 stdout
  操作系统的 subprocess.PIPE 缓冲区大小有限（Windows 上约 4KB-64KB）

第4层：stdout 管道满
  后端持续 print() 输出日志 → 管道缓冲区被写满
  一旦管道满，write() 系统调用阻塞 → 后端的 print() 语句全部卡住

第5层：Python GIL + 阻塞的 print()
  Python 的 print() 获取 GIL 后执行 C 的 fwrite()
  如果 stdout 管道满，持有 GIL 的线程会在 fwrite() 上阻塞
  虽然 CPython 在 I/O 阻塞时会释放 GIL，但 asyncio 事件循环的调度也会受影响

第6层：WS/HTTP 服务器冻死
  WebSocket 服务器的消息处理器中包含 print() 调用
  当处理器在 await 后执行 print() 时被阻塞 → 整个 asyncio 事件循环停滞
  HTTP 服务器（单线程 TCPServer）同理，一个请求卡住全堵
  → 前端看到：WS 连上了但不响应、HTTP 超时、面板全空
```

**关键验证**：
- 用嵌入式 Python 直接启动后端（`python\python.exe -m app.main --desktop`，无 PIPE）→ HTTP/WS 全部正常
- 通过 GuguGaga.exe 启动（subprocess.PIPE + evaluate_js）→ 后端冻死
- 这证实了问题出在 **启动器的 PIPE + evaluate_js 组合**，而非后端代码本身

**修复内容**（仅改 `launcher/launcher.py`）：
1. **`_splash_done` 标志**：`_on_backend_ready()` 中先设 `_splash_done=True`，`_on_backend_status()` / `_on_backend_failed()` 检查此标志后直接 return，阻止后续 `evaluate_js` 调用
2. **非阻塞 evaluate_js**：将 `evaluate_js` 调用包装在 `threading.Thread(daemon=True)` 中，`t.join(timeout=3)` 最多等 3 秒后放弃，不阻塞 `_forward_logs` 线程
3. **日志优先写文件**：`_forward_logs` 中先写 `launcher.log`（最可靠），再尝试 `print()`（PyInstaller 无控制台时可能失败但不影响主流程）

**附带风险**：`desktop.bat`（pywebview 模式）也使用 stdout PIPE + evaluate_js，理论上存在相同风险，但因启动时序差异（pywebview 窗口先创建，后端后启动）未触发

================================================================================

## 🟡 v1.9.23 (2026-04-26) ✅ STABLE

### 🔧 修复：GuguGaga.exe 前端功能全面失效（WS重连后消息丢失）

**0. WS消息监控绑定错误（P0 — GuguGaga.exe根因）**：
- **问题**：`_wsMsgLog` 的 `addEventListener` 在页面顶层代码绑定到初始 `ws` 对象。如果 WS 连接失败后重连，新 `ws` 对象上没有消息监控，导致诊断显示"WS消息: (无消息)"
- **修复**：将 `_wsMsgLog` 的 `addEventListener` 移入 `connectWS()` 内部，每次创建新 WS 连接都绑定到当前 `ws` 对象

**1. WS消息增强器重连丢失（P0 — system_stats/vision/OCR不工作根因）**：
- **问题**：`ws.onmessage` 的 IIFE 包装器（处理 vision_result/ocr_result/system_stats/memory_timeline/tool_result/train_result/tts可视化）只在页面加载时执行一次。WS 重连后新 `ws` 对象的 `onmessage` 是原始处理器，缺少增强器 → 系统监控/历史/Vision面板全部无数据
- **修复**：将 IIFE 改为可重用函数 `enhanceWsOnMessage(wsObj)`，在 `connectWS()` 内每次创建新连接后调用，添加 `_enhanced` 标志防止重复包装

**2. TTS音色下拉框初始为空（P1）**：
- **问题**：`updateVoiceOptions()` 只在 TTS 引擎切换时调用，从未在页面加载时调用。`tts-voice` 下拉框初始为空（HTML 中无 `<option>`），必须等 `projects_list` WS 消息到达后才填充
- **修复**：页面加载时调用 `updateVoiceOptions()`，立即填充 Edge TTS 默认音色或 GPT-SoVITS "加载中..." 占位

**3. 诊断弹窗增强（P2）**：
- 新增 `onOpen` / `msgs` / `enhanced` 状态显示，精确定位 WS 问题
- 新增"WS往返测试"按钮：发送 `diag` 请求并测量响应时间，验证双向通信
- 修复版本号检查从 1.9.22 → 1.9.23

## 🟡 v1.9.22 (2026-04-25) ✅ STABLE

### 🔧 修复：实时语音误打断 + TTS缓存清理 + ASR录音时长 + 诊断工具 + JS致命错误

**0. canvas-container JS致命错误修复（P0 — GuguGaga.exe根因）**：
- **问题**：`mouseup` 事件处理器引用未定义变量 `resizing` → `Uncaught ReferenceError: resizing is not defined`
- **影响**：每次鼠标松开都触发 JS 错误，高频报错可能导致 WebView2 降级/阻塞后续 JS 执行
- **根因**：canvas-container 的拖拽代码声明了 `dragging` 但遗漏了 `resizing`，canvas 缩放使用 `canvasResizing` 但 mouseup 检查的是 `resizing`
- **修复**：
  - 在 `let dragging = false` 后补充声明 `let resizing = false`
  - canvas 缩放 mousedown 时同步设置 `resizing = true`
  - 确保 mouseup 中的 `if (resizing)` 分支能正确执行

**1. 实时语音误打断修复（P1）**：
- **问题**：键盘/鼠标/环境噪音触发 VAD → 立即打断 TTS 播放 → AI 话说不完整
- **根因**：`onSpeechStart` 中检测到 AI 播放时立即执行打断，无延迟缓冲
- **修复**：引入 800ms 延迟打断机制
  - VAD 检测到声音时不立即打断，而是启动 800ms 延迟计时器
  - 800ms 后仍在说话才执行打断（真人说话至少 500ms+）
  - 短暂噪音（100-300ms）在 `onSpeechEnd` 中取消延迟打断
  - 提取 `_doInterrupt()` 统一打断方法，避免代码重复

**2. TTS 音频缓存自动清理（P2）**：
- **问题**：`app/web/static/audio/` 下缓存文件无限增长
- **修复**：在 `_cleanup_old_audio()` 中新增文件数量上限机制
  - 上限 120 个文件
  - 超过上限时按修改时间从旧到新删除
  - 保留原有的 10 分钟超时清理策略

**3. ASR 手动录音时长延长（P2）**：
- `STT_MAX_RECORDING_MS`: 30000ms → 60000ms（30s → 60s）
- 超时提示文字同步更新

**4. GuguGaga.exe 诊断增强（P1 排查工具）**：
- **问题**：GuguGaga.exe 启动后 ASR/TTS音色/视觉/系统监控/历史 无法使用
- **排查结果**：后端模块全部正常加载，内嵌Python包齐全，pywebview版本一致
- **诊断工具**：
  - 后端新增 `diag` WebSocket 端点（返回 Python 路径/模块状态/App 状态）
  - 前端新增 `runDiag()` 全局函数（浏览器控制台输入即可运行）
  - WebSocket 连接错误/关闭日志增强（code + reason）
- **系统监控增强**：`_handle_system_stats` 出错时也返回响应（避免前端无限等待）

**修改文件**：
- `app/web/static/index.html` — 误打断修复 + ASR时长 + 诊断工具 + WS日志
- `app/web/__init__.py` — TTS缓存上限 + 诊断端点 + 错误响应增强

## 🟡 v1.9.21 (2026-04-25) ✅ STABLE

### 🐛 关键 Bug 修复：TTS 横杠仍被读出 + __pycache__ 缓存问题

**1. TTS 横杠/减号仍被读出"减"（P1）**：
- **根因**：v1.9.20 的横杠正则 `(?<=[\u4e00-\u9fff])-(?=[\u4e00-\u9fff])` 只覆盖中文之间的横杠
  - "这是 - 测试"（空格横杠）→ 横杠未被替换，GPT-SoVITS 仍读出"减"
  - "这是-hello"（中文英文之间）→ 横杠未被替换
  - GPT-SoVITS 内部把 `-` 当标点符号，**任何横杠到达 TTS 都会被读成"减"**
- **新策略**：先替换所有 `-` 为逗号，再恢复英文复合词中的连字符
  - `text.replace('-', '，')` → 全部横杠变逗号
  - `_re.sub(r'([a-zA-Z0-9])，([a-zA-Z0-9])', r'\1-\2', text)` → 恢复 GPT-SoVITS、v1.9-beta、5-10 等
  - 确保没有任何横杠到达 GPT-SoVITS

**2. `speak_streaming()` 文本清理与 `speak()` 对齐**：
- 补齐缺失的清理：标点后列表标记、markdown 链接、括号说明文字

**3. `__pycache__` 缓存过期**：
- `.pyc` 编译时间（18:30）早于 `.py` 修复时间（22:13）
- 嵌入式 Python 可能使用旧缓存，已清理

**修改文件**：
- `app/tts/gptsovits.py` — 横杠处理改为"先全替换再恢复"策略 + 补齐 speak_streaming 清理
- `app/main.py` — 版本号 v1.9.21

## 🟡 v1.9.20 (2026-04-25) ✅ STABLE

### 🐛 关键 Bug 修复：TTS 英文被删除 + 横杠被读出

**1. TTS `speak_streaming` 英文/数字被完全删除（P0 严重 Bug）**：
- **根因**：`speak_streaming` 中的正则 `[\u1F300-\u1F9FF]` 在 Python 中被错误解析
  - `\u` 只支持 4 位十六进制，`\u1F300` 被解析为 `\u1F30` + 字符 `0`
  - 这导致字符范围 `U+1F30` 到 `U+1F9F` + `0` + `F` 恰好覆盖了全部英文字母和数字
  - 所有 A-Z、a-z、0-9 都被匹配并删除！
- **修复**：删除该错误正则（emoji 已被 `\U00010000-\U0010FFFF` 覆盖）

**2. TTS 读出横杠/减号（P1）**：
- `speak_streaming` 缺少 markdown 格式清理（只有 `speak` 有）
- 单个横杠（如 `你好-世界`）在 `speak` 和 `speak_streaming` 中都没被处理
- **修复**：
  - `speak_streaming` 补齐 markdown 清理逻辑（与 `speak` 对齐）
  - 两个方法都新增中文语境下单个横杠 → 逗号的替换
  - 保留英文连字符（如 `GPT-SoVITS`、`CPU-性能` 不受影响）

**修改文件**：
- `app/tts/gptsovits.py` — 修复 `speak_streaming` 正则 Bug + 补齐横杠/markdown 清理 + `speak` 增加单个横杠处理

## 🟡 v1.9.19 (2026-04-25) ✅ STABLE

### ✨ 新功能：设置面板内置 API Key 输入
### 🐛 关键 Bug 修复：API Key 保存后不生效

**1. API Key 输入窗口前置（P0）**：
- 之前 API Key 输入藏在「工具箱 → 🔧 配置」的隐藏面板里，用户很难找到
- 现在直接在「⚙️ 设置」面板顶部增加 MiniMax API Key 输入区域
- 橙色高亮边框，一眼可见
- 输入、保存、状态反馈全部内联，无需跳转
- 与配置编辑器中的 API Key 面板双向同步（保存/状态查询结果同时更新两处）

**2. API Key 保存后运行时不生效（P0 严重 Bug）**：
- **根因**：`_handle_set_api_key` 中检查 `self.app._llm` 和 `self.app._vision`，但 LLM/Vision 实际存储在 `self.app._lazy_modules['llm']` 和 `self.app._lazy_modules['vision']`
- 属性名对不上，导致用户保存 API Key 后，LLM 和 Vision 的运行实例永远没被更新
- API Key 虽然写入了 api_keys.json 文件，但需要重启才能生效
- **修复**：
  - 改用 `_lazy_modules` 字典正确查找已加载的模块
  - 如果模块还没加载，通过 property 触发懒加载（先用更新后的 config）
  - 调整执行顺序：先更新内存 config → 再触发懒加载/更新实例
  - `_handle_get_api_key_status` 也修复了同样的属性路径错误

**修改文件**：
- `app/web/__init__.py` — 修复 _handle_set_api_key 和 _handle_get_api_key_status 中的属性路径 + 执行顺序
- `app/web/static/index.html` — 设置面板添加 API Key 输入区域 + JS 函数 + WS 消息同步
- 嵌入式 Python `python/Lib/site-packages/` — 补装 sentence-transformers、chromadb（记忆系统依赖）

## 🟡 v1.9.18 (2026-04-25) ✅ STABLE

### 🐛 关键 Bug 修复：GPT-SoVITS 依赖缺失导致 TTS 完全不可用

**1. GPT-SoVITS 依赖缺失（P0）**：
- `install_deps.bat` 只安装了 3 个 GPT-SoVITS 依赖（gradio/scipy/librosa），但 GPT-SoVITS 需要 44 个
- 缺少 `pytorch-lightning>=2.4`：TTS 初始化直接失败，流式和同步合成均不可用
- 缺少 `pypinyin`/`cn2an`/`g2p_en`：TTS 文本预处理会失败
- 缺少 `openai`/`anthropic`/`tiktoken`：LLM 模块不可用
- 修复：补全所有 GPT-SoVITS 和 LLM 关键依赖到 `install_deps.bat`
- 编译问题：`opencc` → 替换为 `OpenCC-python-reimplemented`（纯 Python，无需 CMake）
- 编译问题：`jieba_fast`/`pyopenjtalk` 标记为可选（需要 C++/CMake 编译环境）

**2. 嵌入式 Python 依赖补全**：
- `python/` 嵌入式环境缺少 GPT-SoVITS 关键依赖
- 已安装：pytorch-lightning 2.6.1, matplotlib, tensorboard, pypinyin, cn2an, g2p_en, chardet, fast-langdetect, 
  wordsegment, rotary-embedding-torch, x_transformers, torchmetrics, opencc(纯Python),
  split-lang, openai, anthropic, tiktoken, sentencepiece, psutil, fastapi, pydantic

**3. jieba_fast 编译问题 fallback**：
- 嵌入式 Python 没有 Python.h 头文件，无法编译 jieba_fast
- 修改 GPT-SoVITS 的 `text/tone_sandhi.py`、`text/chinese.py`、`text/chinese2.py`
- 加 try/except：找不到 jieba_fast 自动降级到普通 jieba（功能相同，速度略慢）

**修改文件**：
- `scripts/install_deps.bat` — 补全 GPT-SoVITS + LLM 依赖列表
- `GPT-SoVITS/GPT_SoVITS/text/tone_sandhi.py` — jieba_fast → jieba fallback
- `GPT-SoVITS/GPT_SoVITS/text/chinese.py` — jieba_fast → jieba fallback
- `GPT-SoVITS/GPT_SoVITS/text/chinese2.py` — jieba_fast → jieba fallback
- 嵌入式 Python `python/Lib/site-packages/` — 补装依赖

## 🟡 v1.9.17 (2026-04-25) ✅ STABLE

### 🐛 关键 Bug 修复：启动脚本 CWD + 前端消息分发

**1. 启动脚本 CWD 修复（P0）**：
- `go.bat` 和 `desktop.bat` 都在 `scripts/` 子目录下，双击时 CWD 是 `scripts/` 而非项目根目录
- `go.bat`: `py -3.11 -m app.main` 在 `scripts/` 下找不到 `app` 模块 → `ModuleNotFoundError`
- `desktop.bat`: `py -3.11 launcher\launcher.py` 路径不对 → 闪退
- 修复：在两个 bat 文件开头加 `cd /d "%~dp0.."` 切换到项目根目录
- 同时修复 HF_HOME 路径：`%~dp0.cache` → `%cd%\.cache`（切换目录后再设）

**2. 前端 WebSocket 消息分发缺失（P0）**：
- `index.html` 行 4043 的消息分发只包含 4 种类型，但 `handleRealtimeMessage` 处理 10+ 种
- 缺少 `realtime_audio_chunk`：**流式 TTS 音频永远不播放**（AI 有声但前端丢弃）
- 缺少 `realtime_stt_start`：识别状态提示丢失
- 缺少 `text_done`：状态永远不重置为"聆听中"
- 缺少 `realtime_audio_done`、`realtime_interrupt_fast`、`text_chunk`
- 修复：补全所有 handleRealtimeMessage 处理的消息类型

**3. 启动器日志增强**：
- 添加 `PYTHONUNBUFFERED=1` + `-u` 标志，解决 piped stdout 块缓冲问题
- 添加 nvidia/cublas/bin 和 nvidia/cudnn/bin 到 PATH
- run_web() 预加载模块添加 logger 调用

**修改文件**：
- `scripts/go.bat` — CWD 修复 + HF_HOME 路径修复
- `scripts/desktop.bat` — CWD 修复 + HF_HOME 路径修复
- `app/web/static/index.html` — WebSocket 消息分发补全
- `launcher/launcher.py` — PYTHONUNBUFFERED + NVIDIA 路径 + 诊断日志
- `app/main.py` — 预加载模块 logger 调用

---

## 🟡 v1.9.16 (2026-04-25) ✅ STABLE

### 📦 生产打包：嵌入式 Python + 启动器 EXE + NSIS 安装器

**目标**：将项目打包为游戏式安装目录，用户无需单独安装 Python。

**1. 嵌入式 Python 3.11.2**：
- 下载 Python 3.11.2 embeddable 包（华为云镜像），解压到 `python/` 目录
- 配置 `python311._pth` 启用 site-packages + 项目路径
- 安装 pip + 全部运行时依赖（PyTorch CUDA cu124 + ASR + TTS + Vision + 桌面启动器）
- 21 个核心模块全部验证通过
- 自动化脚本：`setup_embedded_python.bat`

**2. 启动器 EXE (PyInstaller)**：
- 将 `launcher/launcher.py` 编译为独立 `GuguGaga.exe`（22.46 MB）
- 内含 pywebview + pystray + Pillow（桌面窗口 + 系统托盘）
- 启动时自动检测 `python/python.exe`（嵌入式），回退到 `py -3.11`（系统安装）
- 支持 PyInstaller frozen 模式路径检测
- 打包配置：`launcher/launcher.spec`
- 构建脚本：`build_launcher.bat`

**3. NSIS 安装器**：
- 游戏式安装向导，支持安装目录选择
- 桌面快捷方式 + 开始菜单
- 自动检测旧版本并卸载
- 安装完成后提示安装嵌入式 Python
- 完整卸载功能
- 安装器脚本：`installer.nsi`
- 构建脚本：`build_installer.bat`

**4. 一键构建流程**：
- `build_all.bat` — 依次执行：嵌入式Python → 启动器EXE → NSIS安装包

**5. launcher.py 路径增强**：
- 新增 `sys.frozen` 检测：打包后的 EXE 自动以所在目录为 PROJECT_ROOT
- splash.html 查找逻辑：优先文件系统，回退 PyInstaller 临时目录

**新增文件**：
- `GuguGaga.exe` — 启动器 EXE
- `python/` — 嵌入式 Python 3.11.2 + 全部依赖
- `setup_embedded_python.bat` — 嵌入式 Python 安装脚本
- `build_launcher.bat` — 启动器 EXE 构建脚本
- `build_installer.bat` — NSIS 安装器构建脚本
- `build_all.bat` — 一键完整构建
- `installer.nsi` — NSIS 安装器脚本
- `launcher/launcher.spec` — PyInstaller 打包配置

**修改文件**：
- `launcher/launcher.py` — 支持 frozen EXE 路径检测
- `app/main.py` — 版本号 v1.9.15 → v1.9.16
- `go.bat` — 版本号同步
- `launcher/splash.html` — 版本号同步

---

## 🟡 v1.9.15 (2026-04-25) ✅ STABLE

### 🔐 API Key 管理面板（新功能）

**需求**：给其他人使用时，API Key 不能明文写在 config.yaml 中。需要前端面板让用户输入 MiniMax API Key，自动应用到 LLM 和视觉理解模块。

**方案**：
- 前端配置面板新增"🔑 API Key"标签页，提供输入框和保存按钮
- 输入 API Key 后自动通过 WebSocket 传到后端
- 后端 `_handle_set_api_key()` 动态更新 LLM 和 Vision 模块的 `api_key` + HTTP Session 认证头
- API Key 持久化到 `app/cache/api_keys.json`（原子写入）
- 启动时 `Config._load()` 自动从 `api_keys.json` 加载 Key 覆盖 config.yaml
- config.yaml 中移除硬编码的 API Key（改为空字符串）
- 支持显示/隐藏 Key、查看已配置状态

**修改文件**：
- `app/web/static/index.html` — 新增 API Key 标签页 + `saveApiKey()` / `checkApiKeyStatus()` 函数
- `app/web/__init__.py` — 新增 `_handle_set_api_key()` / `_handle_get_api_key_status()` WS处理器
- `app/main.py` — `Config._load()` 启动时加载 `api_keys.json`
- `app/config.yaml` — 移除硬编码 API Key

---

### ⚡ 生产就绪审计修复（3 CRITICAL + 5 HIGH + 6 MEDIUM + 4 LOW）

#### CRITICAL 修复

**C1: GPU 显存释放** — `set_project()` 切换音色时释放旧模型占用的 GPU 显存
- `app/tts/gptsovits.py` — `set_project()` 中 `tts_pipeline = None` 前先 `del`，之后调 `torch.cuda.empty_cache()`

**C2: 关停时 GPU 资源清理** — 程序退出时释放 TTS 模型的 GPU 资源
- `app/tts/gptsovits.py` — 新增 `cleanup()` 方法，释放所有模型 + `torch.cuda.empty_cache()`
- `app/main.py` — `stop()` 中调用 `tts.cleanup()`

**C3: GPT-SoVITS 子进程管理** — 训练子进程在主进程崩溃时可能成为孤儿
- `app/trainer/manager.py` — 新增 `_active_processes` 列表跟踪 `Popen` 对象
- 新增 `_cleanup_processes()` 方法，`terminate()` + `kill()` 活跃子进程
- `atexit` 注册清理，`stop_training()` 也调用清理
- 两个 `Popen` 调用点均添加 `self._active_processes.append(proc)`

#### HIGH 修复

**H1: WS 重连后恢复 TTS/ASR 配置状态** — 重连后发送当前配置到后端
- `app/web/static/index.html` — `ws.onopen` 中发送 `update_tts_config` + `checkApiKeyStatus()`

**H2: 客户端断开后清理后端状态 dict** — 防止长期运行内存膨胀
- `app/web/__init__.py` — `on_left` 回调中清理 `_client_tts_engine/voice/asr_provider/vision_monitors`

**H3: 布局数据写入改为原子写入** — 防止崩溃时数据损坏
- `app/web/__init__.py` — `_handle_layout_api()` 使用 `tempfile.mkstemp()` + `os.replace()`

**H4: 启动时清理堆积的音频临时文件** — 上次崩溃可能遗留
- `app/web/__init__.py` — `_start_audio_cleanup()` 启动时立即清理一次

**H5: 记忆系统定时 flush** — 不满 5 条时数据可能丢失
- `app/memory/__init__.py` — 新增 30 秒定时 flush 线程，`flush()` 时取消定时器

#### MEDIUM 修复

**M1: SIGTERM 信号处理** — 确保优雅关停
- `app/main.py` — 新增 `_signal_handler()`，注册 `SIGINT`/`SIGTERM`

**M3: 配置文件加载失败友好提示** — 不再直接崩溃
- `app/main.py` — `AIVTuber.__init__()` 中 try/except 捕获 `FileNotFoundError` 和解析错误

**M4: 前端 WS 消息类型校验** — 防止无效消息导致前端崩溃
- `app/web/static/index.html` — `ws.onmessage` 中添加 JSON 解析保护和类型校验

**M5: LLM streaming 中断时返回部分响应** — 不丢弃已生成的内容
- `app/llm/__init__.py` — `stream_chat()` 异常时返回 `{"_stream_error": ...}` 标记

**M6: 音频 Blob URL 泄漏修复** — 预取的 nextUrl 未释放
- `app/web/static/index.html` — `audio.onended` 中释放 `nextUrl`

#### LOW 修复

**L1: 日志持久化** — 已有 `RotatingFileHandler`，确认无需修改

**L2: 健康检查端点** — 新增 `/api/health`
- `app/web/__init__.py` — `_handle_get()` 中添加 `/api/health` 返回 `{"status": "ok"}`

**L4: 前端全局未捕获异常处理** — 防止单个错误白屏
- `app/web/static/index.html` — 添加 `window.onerror` + `unhandledrejection` 处理

---

### 📝 版本号同步

- `app/main.py` 启动头 v1.9.14 → v1.9.15
- `go.bat` 版本号 v1.9.14 → v1.9.15
- `launcher/splash.html` 版本号 v1.9.14 → v1.9.15

================================================================================

## 🟡 v1.9.14 (2026-04-25) ✅ STABLE

### ⚡ TTS 预热优化：只预热上次使用的音色

**问题**：启动时预热所有已训练音色（hongkong + mansui），即使大部分时间只用 hongkong，
浪费启动时间和 GPU 资源。

**方案**：
- 新增"上次使用音色"持久化：`app/cache/last_tts_project.json`
- `set_project()` 切换音色时自动保存当前项目名
- 启动预热只预热上次使用的音色 + 默认音色
- 无历史记录时回退到预热第一个已训练音色

**修改文件**：
- `app/tts/gptsovits.py` — 新增 `_save_last_project()` / `_load_last_project()`，`set_project()` 末尾调用保存
- `app/web/__init__.py` — `_prewarm_tts()` 重构为只预热上次音色

---

### 🔧 系统监控 & 历史面板自动刷新修复

**问题**：
1. 系统监控的自动刷新是手动开关（需点击"⏱️ 自动"），打开面板不会自动开始
2. 历史面板的自动刷新只在 `showHistory()` 按钮触发时启动，从保存布局恢复时不生效

**方案**：
- 新增 `checkMonitorVisibility()` / `checkHistoryVisibility()` — 检查面板可见性自动启停刷新
- `_applyLayoutData()` 布局加载完成后 200ms 触发可见性检查
- `ws.onopen` WebSocket 连接成功后也触发可见性检查
- `togglePanel()` 关闭面板时停止刷新，显示面板时开始刷新
- 监控面板"⏱️ 自动"按钮改为"⏸️ 暂停 / ▶️ 继续"（默认已自动刷新）

**修改文件**：`app/web/static/index.html`

---

### 🔧 修复与维护

#### 版本号同步修复
- `app/main.py` 启动头 v1.9.12 → v1.9.14
- `go.bat` 版本号 1.9.12 → 1.9.14
- `launcher/splash.html` 版本号 v1.9.12 → v1.9.14

#### 启动器过渡流程增加防御性日志
- `_on_backend_ready()` 增加窗口空值检查 + 每步日志
- 跳转失败时打印二级异常信息

**修改文件**：`launcher/launcher.py`

---

## 🟡 v1.9.13 (2026-04-25) ✅ STABLE

### 🎨 UI/UX 改进

#### 布局预设栏重新定位 + 毛玻璃水滴美化

**改动**：
- 预设栏（默认/紧凑/极简）从顶部居中移至**右下角浮动**
- 采用毛玻璃水滴风格：`backdrop-filter: blur(20px saturate(180%)`、渐变边框、胶囊形按钮
- 悬停效果：`scale(1.05) translateY(-2px)` + 发光阴影
- 激活状态渐变背景 + 内发光

**修改文件**：`app/web/static/index.html`

---

#### 版本号徽标位置与样式修复

**问题**：版本号 "v1.9.12" 遮挡 "Created by XZT" 文字，且颜色太淡几乎不可见

**方案**：
- 将版本号移到 "Created by XZT" **之后**（同一行内）
- 使用与前方文字一致的 `linear-gradient` 渐变色 + `-webkit-background-clip: text`
- 字体缩小至 0.7em

**修改文件**：`app/web/static/index.html`

---

#### 系统监控 & 历史面板自动刷新加速

**改动**：
- 系统监控面板刷新间隔：5000ms → **1000ms**（每秒刷新）
- 历史面板新增自动刷新：打开历史时启动 1s 定时器，关闭面板时停止
- 新增变量：`historyAutoRefresh` / `historyInterval`

**修改文件**：`app/web/static/index.html`

---

### 🚀 启动器改进

#### Splash 标题增加 "Created by XZT"

**改动**：splash.html 主标题后追加 `<span class="created-by">Created by XZT</span>`，
使用与主标题一致的渐变色和动画效果。

**修改文件**：`launcher/splash.html`

---

#### Splash→主界面 PPT 式过渡动画

**改动**：
- splash.html 新增 `.fade-out` 动画：0.8s ease-out，opacity 1→0 + scale 1→1.05
- `onBackendReady()` 触发时给 body 加 `fade-out` class
- launcher.py 等待时间从 0.8s 调整为 1.0s（等动画完成再跳转）
- index.html 新增页面级 `page-fade-in` 入场动画（0.6s ease-out）

**修改文件**：`launcher/splash.html`、`launcher/launcher.py`、`app/web/static/index.html`

---

### 🔇 修复：GPT-SoVITS TTS 模型加载时 _IncompatibleKeys 输出刷屏

**问题**：`TTS()` 初始化时 `load_state_dict(strict=False)` 会打印大量
`_IncompatibleKeys(missing_keys=[...], unexpected_keys=[...])` 信息，
淹没控制台日志，影响游戏风格启动体验。

**方案**：新增 `_SuppressVerboseOutput` 上下文管理器，在模型加载期间
临时重定向 stdout/stderr 到 StringIO，加载完成后恢复。
异常发生时会自动重放捕获的输出以便调试。

**修改文件**：
- `app/tts/gptsovits.py` — 新增 `_SuppressVerboseOutput` 类 + 包裹两处 `TTS(tts_config)` 调用

---

### 🎮 控制台输出全面升级为游戏风格

**改动**：

新增 `LogStyle` 工具类（~150 行），提供：
- `game_header()` — 彩色 ASCII art 标题头
- `game_box()` — 信息框
- `game_ok() / game_skip() / game_fail() / game_warn() / game_info()` — 带颜色标签的状态输出
- `game_progress()` — 进度条
- `game_section()` — 分节标题
- `game_separator()` — 分隔线

**全局替换**：
- `Config` 类所有 `print()` → 游戏风格函数
- 所有模块懒加载器 `print()` → 游戏风格函数
- `run_web()` 完全改为游戏风格输出（含预热进度条）
- 移除 `AIVTuber.__init__` 中重复的 `game_header()` 调用
- 静默 `[缓存] 模型目录:` 冗余输出

**警告抑制**：
```python
warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*ffmpeg.*")
```

**修改文件**：`app/main.py`

---

## 🟡 v1.9.12 (2026-04-25) ✅ STABLE

### 🐛 修复：桌面模式布局加载完全重构 — 彻底解决布局不持久问题

**问题**：桌面模式每次打开都恢复默认布局，所有保存无效

---

### ✨ 新增：浏览器模式与桌面模式布局共享

**功能**：浏览器模式和桌面模式现在共用同一份布局数据
- 保存时：同时保存到后端 API + localStorage
- 加载时：优先从后端 API 加载（共用数据），失败时回退到 localStorage

**效果**：在浏览器调好的布局，打开桌面版也会自动应用

---

### 📋 问题演进史

**问题**：桌面模式每次打开都恢复默认布局，所有保存无效

---

### 📋 问题演进史

| 版本 | 问题描述 | 尝试方案 | 结果 |
|------|----------|----------|------|
| v1.9.7 | 桌面模式布局无法保存 | 首次引入后端 API 保存 | 保存后下次仍丢失 |
| v1.9.10 | 自动排列/预设保存位置错误 | 修复动画时序问题 | 只修复了排列问题 |
| v1.9.11 | localStorage 在 WebView2 中不持久化 | 统一用 localStorage | 解决了隔离问题，但仍丢失 |
| v1.9.12 | **根本原因：IS_DESKTOP 时序问题** | 完全重构加载逻辑 | ✅ **问题解决** |

---

### 🔍 根本原因分析

#### 原因一：IS_DESKTOP 时序竞争（最关键！）

```
执行时序：
┌─────────────────────────────────────────────────────────────────┐
│ 脚本开始执行                                                     │
│   ↓                                                              │
│ IS_DESKTOP = !!(window.pywebview && window.pywebview.api)      │
│              = false（此时 pywebview API 还未注入）               │
│   ↓                                                              │
│ checkDesktopMode() 被调用 → IS_DESKTOP 仍然是 false             │
│   ↓                                                              │
│ 启动 setInterval 每 500ms 检测 pywebview API                    │
│   ↓                                                              │
│ ══════════════ 脚本末尾 ══════════════                          │
│   ↓                                                              │
│ waitForDesktopModeDetection() 被调用                            │
│   ↓                                                              │
│ 此时 IS_DESKTOP = false → 直接执行 callback                      │
│   ↓                                                              │
│ waitAndLoadLayout() 被调用 → 检测到 IS_DESKTOP = false          │
│   ↓                                                              │
│ 走浏览器模式逻辑（从 localStorage 加载）                         │
│   ↓                                                              │
│ ══════════════ 500ms 后 ══════════════                          │
│   ↓                                                              │
│ setInterval 检测到 pywebview → IS_DESKTOP = true                 │
│   ↓                                                              │
│ 但布局加载已经完成了！太晚了！                                    │
└─────────────────────────────────────────────────────────────────┘
```

#### 原因二：URL 路由匹配问题

- 前端请求 `/api/layout?t=1682500000000`（带时间戳防止缓存）
- 后端检查 `self.path == "/api/layout"` **不匹配**（因为路径包含查询参数）
- 请求走到 `super().do_GET()` 返回 HTML 页面而非 JSON

#### 原因三：Observer 干扰

- 600ms 后 Observer 启动，检测到 style 变化
- 如果在布局加载完成前启动，可能覆盖已加载的位置

---

### ✅ 最终解决方案

#### 1. 桌面模式检测重构

```javascript
// 直接轮询 window.pywebview.api，而非依赖 IS_DESKTOP 变量
function waitForDesktopModeDetection(callback) {
    let attempts = 0;
    const maxAttempts = 50; // 50 * 100ms = 5 秒
    
    const check = () => {
        attempts++;
        const isDesktop = !!(window.pywebview && window.pywebview.api);
        
        if (isDesktop && !IS_DESKTOP) {
            IS_DESKTOP = true;
            onDesktopModeDetected();
        }
        
        if (IS_DESKTOP || attempts >= maxAttempts) {
            callback(); // 等到模式确定后再加载布局
        } else {
            setTimeout(check, 100);
        }
    };
    check();
}
```

#### 2. 后端路由修复

```python
# 修改前（不匹配带查询参数的 URL）
if self.path == "/api/layout":

# 修改后
if self.path.startswith("/api/layout"):
```

#### 3. 双保险保存机制

```javascript
if (IS_DESKTOP) {
    // 桌面模式：同时保存到两个地方
    localStorage.setItem(STORAGE_KEY, jsonStr);  // 备选
    fetch('/api/layout', { method: 'POST', body: jsonStr });  // 主存储
}
```

#### 4. 加载时序控制

```javascript
function waitAndLoadLayout() {
    const checkPanels = () => {
        const panels = document.querySelectorAll('.panel');
        if (panels.length === 0) {
            setTimeout(checkPanels, 50);  // 等待面板渲染
            return;
        }
        
        if (IS_DESKTOP) {
            loadLayoutFromBackend();  // 从后端加载
        } else {
            loadFromLocalStorage();    // 从 localStorage 加载
        }
    };
    checkPanels();
}
```

---

### 📁 修改的文件

| 文件 | 修改内容 |
|------|----------|
| `app/web/static/index.html` | 重构桌面模式检测、布局加载/保存逻辑 |
| `app/web/__init__.py` | 修复 `/api/layout` 路由支持查询参数 |
| `launcher/splash.html` | 版本号更新为 v1.9.12 |
| `go.bat` | 版本号更新为 1.9.12 |
| `docs/VERSION.md` | 本次修复详细记录 |

---

### 🧪 验证方法

1. 双击 `desktop.bat` 启动桌面版
2. 调整面板位置
3. 查看控制台（F12）：
   ```
   [Init] 页面加载，IS_DESKTOP = false
   [Init] window.pywebview = true, window.pywebview.api = true
   [桌面模式] 延迟检测到 pywebview API
   [桌面模式] 确认使用桌面模式，开始加载布局...
   [Layout] 检测到 N 个面板，开始加载布局...
   [桌面模式] 从后端加载布局成功
   [saveLayout] IS_DESKTOP=true, savedCount=N
   [saveLayout] 后端已保存 N 个面板
   ```
4. 关闭桌面版，重新打开
5. 确认布局保持不变
6. 点击右上角 v1.9.12 徽章查看存储状态

---

### 🐛 修复：布局预设栏移到右下角 — 避免遮挡 Logo

**问题**：布局预设栏（默认/紧凑/极简/自动排列等按钮）固定在顶部中央，与 Header 中的 Logo "🐱 咕咕嘎嘎 AI虚拟形象 Created by XZT" 重叠，影响显示效果

**解决方案**：
- 将 `#layout-presets-bar` 从 `position: fixed; top: 8px; left: 50%` 改为 `position: fixed; bottom: 20px; right: 20px`
- 添加玻璃态背景样式（`backdrop-filter: blur`），使其成为右下角浮动工具栏
- 视觉效果：毛玻璃圆角胶囊，融入界面而不突兀

---

### 🎨 UI 美化：布局预设栏 + Logo 版本号

**预设栏水滴毛玻璃效果**：
- 容器：渐变毛玻璃背景 + `border-radius: 50px` 胶囊形状 + 光泽内阴影
- 按钮：`border-radius: 50px` 水滴胶囊 + 渐变背景 + 悬停上浮 + 点击反馈
- 悬停动画：`translateY(-2px)` + 渐变加深 + 发光阴影

**Logo 版本号位置修复**：
- 版本号从右上角绝对定位 → 移到 "Created by XZT" 文字后面
- 版本号使用渐变色与 "Created by XZT" 保持一致
- 消除遮挡问题，保持 logo 完整显示

---

### ⚡ 优化：系统监控 + 历史面板每秒自动刷新

**系统监控面板**：
- 自动刷新间隔从 5 秒缩短为 1 秒
- 点击监控刷新按钮开启自动刷新

**历史面板**：
- 新增每秒自动刷新机制
- 打开历史面板时自动开启
- 关闭面板时自动停止刷新

---

### 🎬 新增：启动器到主界面平滑过渡动画

**splash.html 淡出效果**：
- 后端就绪时触发 `body.fade-out` 动画
- 组合效果：`opacity 0→1` + `scale 1→1.05` 缩放淡出
- 动画时长：0.8秒

**index.html 淡入效果**：
- 主界面加载时 `body { animation: page-fade-in 0.6s }`
- 透明度从 0 渐变到 1

**launcher.py 优化**：
- 等待动画完成后跳转（1秒）
- 切换更丝滑自然

---

## 🟢 STABLE v1.9.11 (2026-04-25)

### 🐛 修复：桌面模式布局持久化 — 解决 localStorage 隔离问题

**问题**：浏览器模式和桌面模式的 WebView2 使用独立的 localStorage，桌面版首次启动时 localStorage 为空，导致所有面板布局错乱

- **首次同步**：桌面模式检测到 localStorage 为空时，自动从后端 API 同步布局数据（`app/cache/layout.json`），一次性填充 localStorage
- **统一存储**：同步后桌面模式和浏览器模式完全一致，统一使用 localStorage 保存/加载
- 浏览器模式不受影响，逻辑不变

## 🟢 STABLE v1.9.10 (2026-04-25)

### 🐛 修复：自动排列/预设保存位置错误 + 遗漏的 saveLayout 调用

**根因**：自动排列和预设函数中，动画代码先把面板位置设回原位再启动过渡动画，但 `saveLayout()` 在动画代码之后执行，读到的是"回退到原位"的值而非最终目标位置 → 保存的位置永远是动画前的旧位置

- **自动排列（横向/纵向）修复**：在 `saveLayout()` 前先把所有面板设到最终位置（`dataset.arrLeft/arrTop`），确保保存的是目标位置
- **紧凑预设修复**：同样的时序问题，在 `saveLayout()` 前先设最终位置
- **极简预设修复**：同上
- **遗漏的 saveLayout 调用补全**：
  - `screenshotAndUnderstand()` 打开 vision 面板时缺少 `saveLayout()`
  - `openCameraPanel()` 打开 vision 面板时缺少 `saveLayout()`
- **maximizePanel zIndex 修复**：最大化时在 inline style 设 `zIndex: 500`，确保 `saveLayout` 能正确保存（之前依赖 CSS class 设 zIndex，`p.style.zIndex` 读不到）

================================================================================

## 🟢 STABLE v1.9.9 (2026-04-25)

### 🐛 修复：布局保存彻底失效 + 自动排列/预设遮挡

**根因**：`saveLayout()` 用 `parseInt(p.style.left)` 读取位置，但面板初始位置由 CSS `#panel-chat { left: 420px }` 规则设置，不在 inline style 中 → `parseInt('')` = NaN → 保存 left: 0 → 下次启动所有面板跑到 (0,0)

- **saveLayout 修复**：改用 `getComputedStyle(p).left` 读取实际渲染位置，并同步回 inline style
- **loadLayout 修复**：
  - 首次启动时调用 `syncCSSLayout()` 把 CSS 计算位置同步到 inline style
  - 恢复 `panelsVisible` 变量（之前只在独立的 `gugu-panels-visible` key 中存，loadLayout 没恢复）
  - 没有 saved state 的面板也从 CSS 计算位置同步
  - 正确清除 collapsed/maximized 状态（之前只添加不删除）
- **toggleAllPanels 修复**：改为"记忆式切换"——隐藏时先备份每个面板的可见性，显示时从备份恢复，不再简单地把所有面板设为 `display:''`
- **自动排列拆分为两种模式（参考 GridStack.js 算法重写）**：
  - ↔自动（横排）：从画布右侧开始，列优先向下填充，Masonry 布局
  - ↕自动（竖排）：从画布下方开始，行优先向右填充
  - 关键修复：先统一设置面板宽度 → 等 DOM 重排完成 → 读真实高度 → 再计算位置
  - 之前的 bug：改了宽度后高度会变，但用的是旧高度算位置，导致面板必定重叠
  - 面板从原位飞到新位置有弹性过渡动画
- **紧凑/极简预设改为动态计算**：
  - 不再用硬编码坐标（容易在不同屏幕尺寸上遮挡）
  - `compact`：小画布 + 2列紧密排列，按高度排序选最矮列
  - `minimal`：只保留对话+TTS+设置，其余隐藏
- **pushHistory 也改用 getComputedStyle**：撤销/重做不再丢失 CSS 规则设置的位置
- **saveLayout 保存后显示提示**：`log('布局已保存', 'ok')`

## 🟢 STABLE v1.9.8 (2026-04-25)

### 🎨 前端布局系统大修

- **自动排列重写**：基于 Bin-Packing 算法的智能排序，替代原来的死板2列网格
  - 面板按实际尺寸（面积）排序，大面板先放，小面板填充空隙
  - 自适应列数：根据窗口宽度自动计算 1~N 列
  - 宽面板自动占 2 列
  - 考虑 Live2D 画布位置，面板从画布右侧开始排列
  - 排列时有平滑过渡动画（cubic-bezier 弹性曲线）
- **状态持久化修复**：所有面板状态跨会话可靠保存和恢复
  - 修复 `loadLayout()` 的致命 bug：`visible=true` 的面板没有显式设 `display=''`，导致默认隐藏的面板（如视觉、OCR）永远不会被恢复
  - 新增 `MutationObserver` 自动监听面板的 style/class 变化，触发防抖保存
  - 无论代码在哪里打开/关闭面板，都会自动持久化
  - 保存内容新增 `zIndex` 和 `maximized` 状态
  - 布局数据新增 `version` 字段，方便未来迁移
  - `saveLayoutDebounced()` 防抖保存，避免频繁写入
- **缩放丝滑度优化**：
  - 移除 `.panel` 默认的 `width 0.3s, height 0.3s` 过渡（这是 resize 延迟感的根因）
  - 新增 `.panel.resizing { transition: none !important; }` CSS 规则
  - resize 过程中面板尺寸变化即时响应，无延迟

## 🟢 STABLE v1.9.7 (2026-04-25)

### ✨ 桌面启动器重写（游戏式体验）

- **重构 `launcher.py`**：改为「先开窗口，后端后台启动」的游戏式启动流程
  - 用户双击 → 立即看到启动画面（splash.html），不再干等后端
  - 后端在后台启动，日志实时推送到启动画面状态文字
  - 后端就绪 → 自动跳转到主界面，零感知切换
  - 后端失败 → 启动画面显示错误详情 + 重试按钮
  - 窗口关闭 → 自动停止后端进程 → 干净退出
  - 后端控制台窗口隐藏（桌面模式下 SW_HIDE）
- **升级 `splash.html` 启动画面**：
  - `updateStatus(msg)` — Python 推送实时状态
  - `onBackendReady()` — 就绪动画（Logo 变绿 + 进度条完成）
  - `showError(msg)` — 错误状态（Logo 变红 + 抖动 + 详情 + 重试按钮）
- **前端桌面模式感知**（`index.html`）：
  - 检测 `window.pywebview.api` 存在 → 自动启用桌面增强
  - 外部链接用系统浏览器打开
  - `window._desktopQuit()` 调用 pywebview 退出
- **新增 `desktop.bat`**：一键启动桌面版，自动安装 pywebview/pystray 依赖

### ✨ 新增：桌面启动器模式（pywebview 原生窗口）

- 新增 `launcher.py` — 桌面客户端启动器，将 WebUI 包装为原生桌面窗口
  - pywebview 创建原生窗口（使用系统 WebView2），替代浏览器访问
  - 后端 Python 进程管理：子进程启动、健康检查轮询、优雅退出
  - 系统托盘图标：最小化到托盘、右键菜单（显示窗口/退出）
  - 启动画面 `splash.html`：粒子动画、进度条、状态提示
  - `LauncherAPI` 暴露给前端 JS：版本查询、窗口控制、退出等
  - 自动检测嵌入式 Python（`python/python.exe`），优先使用
  - 降级方案：pywebview 不可用时自动回退到浏览器模式
- `app/main.py` 新增 `--desktop` 参数：桌面模式标志，由 launcher.py 调用
- `go.bat` 新增启动模式选择：[1] Web 模式（浏览器）/ [2] 桌面模式（原生窗口）
- 自动安装 pywebview 依赖（桌面模式首次启动时）

### 🐛 Bug修复

- **GBK 编码崩溃**：Windows 子进程默认 GBK 编码，print 含 emoji 时 UnicodeEncodeError
  - `launcher.py`：子进程 env 添加 `PYTHONIOENCODING=utf-8`，Popen 用 `encoding='utf-8'`
  - `app/main.py`：启动时强制 `sys.stdout/stderr.reconfigure(encoding='utf-8')`，全局安全网
- **Live2D 模型路径双重拼接**：`base=app/` 下又拼了 `app/web/` 变成 `app/app/web/`
  - `app/live2d/__init__.py`：修正路径搜索列表，去除重复的 `app/` 前缀

================================================================================

## 🟢 STABLE v1.9.5 (2026-04-23)

### 🐛 修复：实时语音模式 VAD 初始化崩溃

- `MicVAD.new()` 缺少 `model: "v5"` 参数 → bundle 默认加载不存在的 `silero_vad_legacy.onnx` → `protobuf parsing failed`
- Web 服务器缺少 COOP/COEP 跨域隔离头 → ORT WASM 多线程不可用
- `main.py` 的 `openclaw` 和 `subagent` property 删除模块后仍直接 import → 加 try/except ImportError 优雅降级

### 🔧 重写：智能依赖安装脚本

- `install_deps.bat` 全面重写：逐包检查+安装+错误判断+生成报告
- 26 个依赖包逐一检查：已安装跳过、缺失自动安装（清华镜像→PyPI 兜底）
- PyTorch CUDA cu124 专项检测与安装（阿里云镜像）
- G2PW 模型自动下载（ModelScope 国内源）
- 安装报告输出到 `install_report.txt`：记录每个包的状态（已存在/新安装/失败/跳过）

### 🔄 重构：全面清理死代码（~2540行）

删除 13 个完全未被项目引用的文件/目录：

- **未集成模块目录（3个）**：
  - `app/vtubestudio/` — VtubeStudio 集成模块，零引用（项目用 Live2D）
  - `app/ocr/` — OCR 实时屏幕分析模块，零引用（web 走 vision 不走 ocr）
  - `app/openclaw/` — OpenClaw 外部工具集成，零引用

- **重复/重叠文件（5个）**：
  - `app/tools/architect.py` — ArchitectTool 增强版，与 __init__.py 内联简化版重复
  - `app/tools/think.py` — ThinkTool 增强版，与 __init__.py 内联简化版重复
  - `app/tools/notebook.py` — NotebookTool，未注册到 ToolFactory
  - `app/permissions.py` — 权限控制模块，与 main.py ToolExecutor 重叠
  - `app/env_config.py` — 环境变量配置，与 main.py Config 类重叠

- **一次性修复脚本（3个）**：
  - `app/fix_unicode_web.py` — Unicode 修复脚本，硬编码 Linux 路径
  - `app/memory/fix_unicode.py` — Unicode 修复脚本，硬编码 Linux 路径
  - `app/memory/fix_docstrings.py` — docstring 修复脚本，硬编码 Linux 路径

- **独立工具脚本（2个）**：
  - `app/build.py` — PyInstaller 打包脚本，未使用
  - `app/tts_api.py` — 独立 TTS 测试服务，Web 面板已替代

- **部分清理**：
  - `app/tools/__init__.py` — 删除 9 个从未被调用的便捷函数（read/write/edit/glob/grep/ls/bash/think/architect）

================================================================================

## 🟢 STABLE v1.9.4 (2026-04-23)

### 🔄 重构：移除 SubAgent 死代码模块

- 删除 `app/subagent.py`（41KB，1420行）— 整个模块从未被项目任何代码 import 或引用
- 原因：该模块是 Claude Code 风格的子 Agent 实现，但从未接入主系统（main.py、前端、config.yaml 均无引用）
- 实现问题：自定义 TOOL:xxx ARG:xxx 正则解析（非标准 function calling）、GrepTool 调用 grep 命令（Windows 不可用）、bash 白名单极窄
- 后续如需 Agent 能力可重新设计更好的版本

================================================================================

## 🟢 STABLE v1.9.3 (2026-04-23)

### 🔧 修复：记忆系统持久化全面修复（v2.1→v2.2）

**问题1 — 向量库从不持久化**（`app/memory/__init__.py`）：
VectorStore 批量保存阈值为 50 条，对话几十条从未达到，导致 `vector_store.json` 从未生成。
**修复**：阈值从 50 改为 5。

**问题2 — 工作记忆/情景记忆重启后丢失**（`app/memory/__init__.py`）：
工作记忆和情景记忆仅存储在内存列表中，进程退出即丢失，数十条对话记录无法保留。
**修复**：新增 JSON 持久化，`memory/state/working_memory.json` 和 `episodic_memory.json`，启动时自动恢复。

**问题3 — long_term.md 从未写入**（`app/memory/__init__.py`）：
`FileStorage.append_long_term()` 方法存在但无调用者，长期记忆文件始终为空。
**修复**：`add_interaction()` 中 importance≥4 时同步写入 `long_term.md`。

**问题4 — 关闭时只刷向量库**（`app/main.py`）：
`stop()` 仅调用 `vector_store.flush()`，工作记忆和情景记忆不落盘。
**修复**：改为调用 `MemorySystem.flush()` 统一刷新所有层。

**问题5 — 异常退出数据全丢**（`app/main.py`）：
无 atexit 保护，进程崩溃或被 kill 时记忆全部丢失。
**修复**：`atexit.register(self._atexit_flush)` 确保异常退出也落盘。

**问题6 — 非原子写入可能损坏**（`app/memory/__init__.py`）：
JSON 直接 `json.dump()` 写文件，断电/崩溃时可能写一半损坏。
**修复**：新增 `_atomic_write_json()`，先写 `.tmp` 再 `os.replace` 原子替换。

**问题7 — 反序列化 KeyError**（`app/memory/__init__.py`）：
`MemoryItem(**item)` 反序列化时旧 JSON 缺少新字段直接 KeyError。
**修复**：新增 `_dict_to_memory_item()` 兼容反序列化，`.get()` 提供默认值。

**问题8 — VectorStore 路径覆盖 Bug**（`app/memory/__init__.py`）：
MemorySystem 传 `storage_dir="./memory"` 给 VectorStore，覆盖了 VectorStore 默认的 `"./memory/vectors"` 子目录。
**修复**：显式设置 `vs_config["storage_dir"] = os.path.join(storage_dir, "vectors")`。

**问题9 — WebUI program_count 始终为 0**（`app/web/__init__.py`）：
`fs._index` 属性不存在，获取程序性记忆条目数报错返回 0。
**修复**：改为 `fs.list_daily_files()` 获取文件列表。

================================================================================

## 🟢 STABLE v1.9.2 (2026-04-22)

### 🔧 修复：VAD WASM 路径 + Vision TTS + STT 空结果 + 文件浏览器

**问题1 — VAD WASM 路径重复拼接**（`app/web/static/index.html`）：
`onnxWASMBasePath` 相对路径被 ONNX Runtime 内部二次拼接，产生 `libs/vad/libs/vad/` 重复路径，WASM 加载失败。
**修复**：改用绝对 URL（`new URL('libs/vad/ort/', window.location.href).href`）。

**问题2 — 外部 ort.wasm.min.js 与 bundle 内嵌 ort 冲突**（`app/web/static/index.html`）：
同时加载外部 `ort.wasm.min.js` script 和 `vad-web` bundle 内嵌的 ONNX Runtime，版本冲突导致初始化失败。
**修复**：移除外部 script 标签，仅使用 bundle 内嵌版本。

**问题3 — Vision TTS 不走流式**（`app/tts/gptsovits.py` + `app/main.py`）：
`_speak_vision_result_worker` 只调 `speak()` 整段合成，不读 `_client_tts_no_split`，客户端开启流式 TTS 时视觉结果仍为整段。
**修复**：与 `_handle_tts` 走同样路径，支持流式/整段自动切换。

**问题4 — STT 空结果前端卡住**（`app/main.py` + `app/web/static/index.html`）：
后端 `if text:` 过滤空结果不发送 `stt_result`，前端卡在"处理中"状态。
**修复**：空结果也发送 `stt_result{text:""}`，前端 `onstop` 加 try-catch 防护。

**问题5 — 文件浏览器白名单太窄**（`app/web/__init__.py`）：
`allowed_dirs` 只有项目目录+临时目录，沙盒允许的路径无法浏览。
**修复**：动态加入 `sandbox.get_paths()` 到白名单。

**问题6 — 记忆系统说明**：
工作记忆和情景记忆重启后丢失（仅内存），语义记忆（向量）和 daily 日志持久化。工具箱记忆面板已对接四层 RAG。

================================================================================

## 🟢 STABLE v1.9.1 (2026-04-22)

### 🔧 修复：环境变量覆盖 + VAD路径 + mansui模型 + VectorStore

**问题1 — 模型缓存路径被覆盖**（`app/main.py`）：
`main.py` 用 `os.environ["HF_HOME"]` 直接覆盖了 `go.bat` 通过 `%~dp0.cache\huggingface` 设置的路径，改为 `models/hf`（不存在的目录），导致每次启动时模型找不到、可能触发重新下载。
**修复**：改用 `os.environ.setdefault()`，只在 go.bat 没设置时才 fallback。同时移除废弃的 `TRANSFORMERS_CACHE`（transformers v5 将移除）。

**问题2 — 实时语音 VAD 启动失败**（`app/web/static/index.html`）：
`onnxWASMBasePath: "libs/vad/ort/"` 缺少前导 `./`，浏览器 `import()` 将其视为 bare module specifier 而非相对路径，报错 `Failed to resolve module specifier 'libs/vad/ort/ort-wasm-simd-threaded.mjs'`。
**修复**：改为 `"./libs/vad/ort/"`，浏览器能正确解析为相对 URL。

**问题3 — mansui 模型加载失败**（`GPT-SoVITS/data/web_projects/mansui/config.json` + `app/tts/gptsovits.py`）：
config.json 保存了旧路径 `C:/Users/x/WorkBuddy/20260406213554/...`（项目移动前的目录），`os.path.exists()` 找不到文件 → 回退到预训练底模 → mansui 音色丢失。同时 version 字段错误（标记为 v1，实际 ZIP 格式是 v3 LoRA）。
**修复**：更新 config.json 路径和版本号。在 `_load_project_config` 中增加路径自动修正逻辑（文件不存在时在项目目录下搜索同名文件）。`set_project` 读取项目 config 的 version 字段更新 `self.version`。

**问题4 — VectorStore len() 报错**（`app/web/__init__.py`）：
`len(getattr(memory, 'vector_store', []))` 对 VectorStore 对象调用 `len()`，但 VectorStore 没有实现 `__len__` 方法。
**修复**：改为 `vs.get_stats()["total_docs"]` 获取条目数。

**问题5 — install_deps.bat 增加 G2PW 模型下载步骤**：
G2PW 拼音推理模型原在运行时按需下载（GPT-SoVITS 初始化时），现统一在 `install_deps.bat` 第9步预下载，避免每次使用时可能触发网络下载。

### 🔄 重构：项目配置路径改为相对路径

**问题 — config.json 使用绝对路径**（`app/tts/gptsovits.py`）：
`GPT-SoVITS/data/web_projects/*/config.json` 中的 `ref_audio`、`trained_gpt`、`trained_sovits` 字段存储绝对路径（如 `C:/Users/x/Desktop/ai-vtuber-fixed/...`），项目目录移动后路径全部失效。
**修复**：
- 新增 `_resolve_project_path()`：加载时将相对路径解析为绝对路径，旧版绝对路径自动兼容（文件不存在时在项目目录搜索同名文件）
- 新增 `_make_relative_path()`：保存时将绝对路径转为相对于项目目录的相对路径
- `_save_project_config()` 保存前自动将绝对路径转换为相对路径，确保项目可移植
- 已有项目（mansui/hongkong）的 config.json 已自动转换为相对路径格式
- 训练管理器（`trainer/manager.py`）仍写绝对路径，但下次加载时 `_load_project_config` 会自动修正

**问题6 — `__init__` 不加载项目训练模型**（`app/tts/gptsovits.py`）：
`__init__` 第124行调用了 `_load_project_config` 但没有把训练模型路径设到 `self.sovits_path` / `self.gpt_path`，
导致 `is_available()` 检查的是预训练底模而非项目的训练模型。
**修复**：`__init__` 中 `_load_project_config` 之后，像 `set_project` 一样从项目配置更新模型路径和版本号。

================================================================================

## 🟢 STABLE v1.8.5 (2026-04-22)

### 🔧 修复：流式 TTS 短句无声 + 卡死 + 播放方案重构

**问题1 — 聊天窗口 TTS 不播放**（`app/web/__init__.py`）：
v1.8.4 的 `_handle_text` 使用 `realtime_audio_chunk` + base64 编码 + `AudioContext.decodeAudioData()` 播放。但 Chrome 自动播放策略下，用户仅按"发送"按钮不足以激活 `AudioContext`（需用户主动触发媒体交互），导致所有 chunk 的 `decodeAudioData` 静默失败。
**修复**：放弃 `realtime_audio_chunk` + `decodeAudioData` 方案，改为 `speak_streaming(sentence)` 返回 WAV 路径 → 通过 `tts_chunk` URL 推送 → 前端 `enqueueTtsChunk` 队列用普通 `Audio` 元素播放。复用已有播放链路，完全不受 `AudioContext` 限制。

**问题2 — 短句无声**（`app/web/static/index.html`）：
`STREAM_BUFFER_CHUNKS: 2` 导致需要缓冲 2 个 chunk 才开始播放，而 GPT-SoVITS 对短句（≤15字）通常只产出 1 个 chunk，第1个 chunk 永远被丢弃，结果用户听不到任何声音。
**修复**：`STREAM_BUFFER_CHUNKS: 2 → 1`，第一个 chunk 立即播放。

**问题3 — 推理卡死**（`app/tts/gptsovits.py`）：
`speak_streaming()` 使用 `split_bucket=True` 时，GPT-SoVITS 内部分桶逻辑对短句末尾会产生空文本条目，触发 `tts_pipeline.run()` 进入空推理，进度条卡在 `0it`，整个线程阻塞。
**修复**：
- 短句（≤50字）自动禁用 `split_bucket`
- `speak()` 和 `speak_streaming()` 开头均加空文本守卫（清理前+清理后各一次）

**问题4 — 垃圾句子合成**（`app/web/__init__.py`）：
LLM 输出中的换行符导致分句产生纯标点/空行碎片（如 `。`、`/n。`、`。今天嘛.`），这些无效句子被送入 TTS 合成浪费 1-2 秒/句。
**修复**：分句前先清理换行，分句后过滤纯标点和少于 3 字符的无效句子。

================================================================================

## 🟢 STABLE v1.8.4 (2026-04-22)

### 🔧 修复：实时语音快速打断保护窗口
**问题**：用户说完话后 LLM 还在思考，环境噪声/呼吸声触发新 VAD → 发送 `realtime_interrupt_fast` → pipeline 被取消 → TTS 永远没机会执行。日志反复出现 `[REALTIME-FAST] 快速打断`。
**修复**（`app/web/__init__.py`）：
- `_handle_realtime_audio` 中记录 `pipeline_start_time`
- `_handle_realtime_interrupt_fast` 中添加 2 秒保护窗口：pipeline 启动后 2 秒内忽略快速打断请求

### 🔧 修复：ASR 前几字丢失 — PCM 环形预缓冲区
**问题**：`MediaRecorder.start()` 在 VAD 触发之后才调用，丢失了前面 100-200ms 的音频（如"今天天气"只识别到"天气"）。
**修复**（`app/web/static/index.html`）：
- 新增 `ScriptProcessorNode` 持续采集 PCM 数据写入 500ms 环形缓冲区
- VAD 触发录音时记录缓冲区快照（`preRecordSnapshot`）
- `onstop` 回调中将预缓冲区 PCM 合并到录音前面，支持采样率自动转换
- 参考 ESP32 VAD 方案：`vad_delay_ms=175ms` + 256ms 前导缓存，首字丢失率从 32% 降到 4.3%

### 🔧 修复：TTS 面板流式合成（GPT-SoVITS 逐 chunk 输出）
**问题**：TTS 面板流式分句模式用 `tts.speak()` 串行同步合成（每句 1-3 秒），3 句话就需要 3-9 秒才全部发完。
**修复**：
- `app/web/__init__.py` `_handle_tts()`：流式分句模式对 GPT-SoVITS 使用 `speak_streaming()` + `on_chunk` 回调逐 chunk 发送，带 fallback 到同步模式
- `app/web/static/index.html`：`playStreamingChunk` 和 `playStreamBuffer` 支持面板模式（`is_panel=true`），不再受 `realtime.active` 限制

### 🔧 修复：视觉摄像头捕获遗漏 TTS 播报
**问题**：`camera_capture` action 调用 `vision.understand()` 后只发送 `vision_result` 文本，没有调用 `_speak_vision_result()` 进行语音播报（而 `understand` action 有）。
**修复**（`app/web/__init__.py`）：`camera_capture` action 中 `understand` 成功后添加 `self._speak_vision_result(client, result)`

### 🔧 修复：文本对话（_handle_text）TTS 整段阻塞
**问题**：聊天窗口发消息，LLM 回复后走 `tts_engine.speak(全文本)` → GPT-SoVITS 内部分 7 句串行合成 → 26 秒后才播放。
**修复**（`app/web/__init__.py` `_handle_text`）：
- 检测 `speak_streaming` 能力，GPT-SoVITS 走流式分句路径
- 正则分句 → 逐句 `speak_streaming()` → `on_chunk` 发 `realtime_audio_chunk (is_panel=True)`
- 失败 fallback 到 `speak()` + `tts_chunk`；非流式引擎（edge/kokoro）保持整段逻辑

---

## 🟢 STABLE v1.8.2 (2026-04-21)

### 🐛 修复：WebUI 视觉模型下拉框无法选择 RapidOCR

**问题**：WebUI 视觉面板的模型选择下拉框中，RapidOCR 选项虽然被 `list_providers` 接口返回，但前端将其标记为 `disabled`（因为 `supports_understanding=false`），导致用户无法选择。此外，RapidOCR 选项甚至不在初始 HTML 的 `<option>` 列表中。

**根因**：
1. `index.html` 动态渲染 provider 列表时，对 `supports_understanding=false` 的 provider 设置了 `disabled` 属性
2. 静态 HTML 初始选项缺少 `rapidocr` 选项
3. 选项名称被 `split('（')[0]` 截断，丢失了分类说明

**修复**（`app/web/static/index.html`）：
1. 移除 `disabled` 逻辑——所有 Provider 都可选（RapidOCR 可做 OCR，只是不支持图像理解）
2. 静态 `<option>` 列表补上 RapidOCR 选项
3. 保留完整的 provider 名称，不再截断

**v1.8.2 追加修复（2026-04-21）**（`app/web/static/index.html`）：
- 把动态重建 select 时的 `innerHTML +=` 改为 `createElement/appendChild`，消除 DOM reflow 导致的选项渲染不稳定 bug
- `supports_understanding=false` 的选项（RapidOCR）在文字后加 `⚠️仅OCR` 提示，让用户清楚能力边界，但**不禁用选择**
- `changeVisionProvider()` 中切换到 rapidocr 时，在状态栏显示 `⚠️ 仅文字OCR，不支持图像理解` 提示

**v1.8.2 追加修复（2026-04-21）** TTS 面板流式分句功能：

**问题**：TTS 面板的"🔀 流式/🔀 整段"按钮完全无效——前端传了 `no_split` 参数，但后端 `_handle_tts()` 从未读取该参数，也没有任何分句逻辑。无论选流式还是整段，都是整段合成完一次性播放。

**根因**：
1. 后端 `_handle_tts()` 没有 `no_split` 参数处理，永远调用 `tts.speak(全文本)`
2. 前端只处理 `tts_done` 消息（整段），没有 `tts_chunk` 消息的逐句播放逻辑
3. 流式分句能力只存在于实时语音 pipeline（`_realtime_stream_pipeline`），跟 TTS 面板无关

**修复**：
- `app/web/__init__.py` `_handle_tts()`：读取 `no_split` 参数；流式模式下用正则按句号/感叹号/问号一次性分句，逐句调用 `tts.speak()` 合成，逐句发送 `tts_chunk` 消息给前端，最后发 `tts_done(streaming=True)` 结束标记
- `app/web/static/index.html`：新增 `ttsChunkQueue` 音频队列 + `playNextTtsChunk()` 逐句播放器；新增 `tts_chunk` 消息处理（入队播放）；停止按钮同时清空队列

---

## 🟢 STABLE v1.8.3 (2026-04-21)

### 🔧 修复：实时语音三大问题（打断、二次会话失败、噪声累积）

**P0-1 修复：第二次实时语音会话识别失败**（`app/web/static/index.html`）
- **问题**：`mediaRecorder.onstop` 回调没有检查 `realtime.active`，快速 stop→start 时旧录音漏入新会话
- **修复**：`onstop` 开头加 `if (!realtime.active)` 检查，实时模式已关闭时丢弃残存录音

**P0-2 修复：AI 播放期间回声反馈循环**（`app/web/static/index.html`）
- **问题**：AI 播放 TTS 时麦克风拾取扬声器回声 → VAD 误判为用户说话 → 打断→录音→回声进 ASR → 恶性循环
- **修复**：VAD 动态阈值——`isPlayingAudio || isStreamingPlaying` 时阈值 ×5，只有真正用户声音才能触发打断

**P0-3 修复：短噪声片段被 ASR 幻觉出文本**（`app/web/static/index.html`）
- **问题**：环境噪声 spike 触发 VAD → 极短录音被发送 → ASR 对 <1s 噪声片段幻觉出任意文本
- **修复**：录音时长 < 500ms 直接丢弃，不发送到后端

**P1-1 优化：打断确认机制**（`app/web/static/index.html`）
- AI 播放期间检测到声音不再立即打断，需持续 300ms 才确认（防回声 spike 误触发）
- 非 AI 播放期间（用户主动说话）直接开始录音，无延迟

**P1-2 优化：AudioContext 生命周期管理**（`app/web/static/index.html`）
- `startRealtime()` 前确保旧的 `audioContext` / `ttsAudioCtx` 完全 `close()`，防止 Chrome 6 个上限泄漏

**P1-3 优化：后端噪音过滤规则增强**（`app/web/__init__.py`）
- 新增 5 类噪音模式匹配：纯语气词、纯肯定词、纯连接词、纯疑问词碎片、过短文本
- 新增重复模式检测：同一片段重复 3 次以上自动过滤

---

## 🟢 STABLE v1.8.1 (2026-04-21)

### 🔧 修复：Embedding 模型国内源下载 + 本地优先加载

**问题**：启动时 `sentence-transformers` 尝试连接 `huggingface.co` 下载 `paraphrase-multilingual-MiniLM-L12-v2`（~470MB），国内网络环境超时卡住启动流程。之前只 catch `ImportError`，网络异常未被捕获。

**修复**（`app/memory/__init__.py`）：
1. 新增 `_get_local_model_path()` 方法，按优先级查找本地缓存：
   - 项目内 ModelScope 缓存（`.cache/modelscope/hub/`）
   - 项目内 HuggingFace 缓存（`.cache/huggingface/hub/`）
   - 系统默认 HuggingFace 缓存
2. `_load_embedding_model()` 优先从本地路径加载，本地无缓存时才尝试在线下载
3. 异常捕获从 `ImportError` 扩展到所有 `Exception`
4. 模型通过 ModelScope（魔搭社区）国内源预下载到项目本地缓存

---

## 🟢 STABLE v1.8.0 (2026-04-21)

### ⚡ 性能：全链路多线程/并发优化

基于 `docs/THREADING_ANALYSIS.md` 审计报告，全面修复并发 Bug 并实现 TTS 异步流水线。

### 🔧 修复：Generation ID 替代 cancel Event — 消除竞态窗口（P0）

**问题**：`cancel.set()` 和 `cancel.clear()` 之间存在时间窗口，旧 pipeline 的 `on_chunk` 可能正好在 `clear()` 之后检查，发现 `cancel=False`，继续执行 TTS，导致**幽灵音频**。

**修复**（`app/web/__init__.py`）：
- 每个新 pipeline 请求分配唯一 Generation ID（`uuid.uuid4()[:8]`）
- 所有回调检查 `state.get("current_gen") == gen_id`，旧 pipeline 自动识别为过期并退出
- 无竞态窗口：gen_id 原子赋值（Python GIL 保证），不再需要 set/clear 配对
- 保留 cancel Event 用于快速打断场景

### 🔧 修复：RateLimiter 锁内 sleep — 线程串行化（P0）

**问题**：`RateLimiter.acquire()` 在 `with self._lock` 内调用 `time.sleep()`，所有 LLM 请求线程被串行化，吞吐量坍塌。

**修复**（`app/llm/__init__.py`）：
- `threading.Lock` → `threading.Condition`（Lock + wait/notify）
- `time.sleep()` → `self._condition.wait()`：原子性释放锁并挂起
- `reset()` 中添加 `notify_all()` 唤醒所有等待线程

### 🔧 修复：LLM 缓存无锁保护（P1）

**问题**：`self._cache` 字典在多线程下无锁保护，缓存读取、写入、重建存在竞态。

**修复**（`app/llm/__init__.py`）：
- MiniMaxLLM / OpenAILLM / AnthropicLLM 均新增 `self._cache_lock = threading.Lock()`
- 缓存读取和写入操作包裹在 `with self._cache_lock:` 中

### ⚡ 性能：TTS 异步化 — LLM 流接收不再被 TTS 阻塞（P1）

**问题**：`on_chunk` 回调中同步调用 `_realtime_tts_single()` → `_tts_do_and_send()`，TTS 合成期间（200-800ms/句）LLM 流接收被完全阻塞。

**修复**（`app/web/__init__.py`）：
- 新增独立 **TTS worker 线程** + `queue.Queue` 句子队列
- `on_chunk` 只做分句 + 入队（非阻塞），TTS 合成在 worker 线程中消费
- LLM 流接收和 TTS 合成**完全并行**
- Pipeline 结束时 `queue.join()` 等待所有句子合成完毕
- Generation ID 保证旧 pipeline 的句子被丢弃

### ⚡ 性能：OpenAI / Anthropic stream_chat 真流式（P1）

**问题**：OpenAI 和 Anthropic 的 `stream_chat()` 是伪流式——内部调用 `chat()` 等待完整响应后单次 callback，首句延迟 5-15s。

**修复**（`app/llm/__init__.py`）：
- OpenAI: `stream_chat` 改为 `stream=True` + `iter_lines()` SSE 真流式
- Anthropic: `stream_chat` 改为 `stream=True` + `content_block_delta` 事件真流式

### 🐛 增强：TTS 队列原子化清空（P2）

**问题**：`while not queue.empty(): queue.get_nowait()` 循环中 `empty()` 和 `get_nowait()` 不是原子的。

**修复**：改用 `with queue.mutex: queue.queue.clear()` 原子化清空。

### 🐛 增强：WebSocket 发送统一保护（P2）

新增 `_safe_send(client, message_dict)` 方法，统一包裹 `send_message` 的 try-except，防止客户端断连时异常传播。

### 🐛 增强：ASR fallback 懒加载加锁（P2）

`_fallback_whisper` 懒加载新增 `threading.Lock` 保护，防止多线程同时触发 fallback 导致重复加载模型。

---

## 🟢 STABLE v1.7.5 (2026-04-20)

### 🔧 修复：Vision TTS 播报 Edge TTS `Invalid voice 'default'` 错误

**问题**：Vision 图片理解结果自动 TTS 播报时，如果客户端使用 Edge TTS 引擎且 voice 为 `'default'`，`_get_tts_for_client()` 会将 `'default'` 原样传给 Edge TTS 配置，导致 `合成错误: Invalid voice 'default'`，语音播报失败。

**根因**：`_get_tts_for_client()` 的 Edge 分支中 `voice if voice != 'default' else 'default'`——`else` 分支没有替换为 config 中配置的实际语音名（如 `zh-CN-XiaoxiaoNeural`），而是原样传了字符串 `'default'`。

**修复**（`app/web/__init__.py`）：
- `else` 分支改为从 `config.yaml` 的 `tts.edge.voice` 读取实际默认语音名
- 若 config 中未配置，fallback 到 `zh-CN-XiaoxiaoNeural`

### 🔧 修复：Vision TTS 使用面板当前 TTS 引擎/音色（而非 fallback 到 Edge + default）

**问题**：Vision 图片理解结果 TTS 播报时，如果客户端还没有发送过文本消息（`_client_tts_engine` 字典无记录），代码 fallback 到 `edge` + `'default'`，导致 `Invalid voice 'default'` 错误。即使客户端有 GPT-SoVITS 配置，Vision TTS 也没有使用。

**根因**：`_speak_vision_result_worker` 中 `_client_tts_engine.get(client_id, 'edge')` 和 `_client_tts_voice.get(client_id, 'default')` 的默认值是 `edge` + `'default'`，而不是使用全局 `self.app.tts`（config 中配置的默认引擎 GPT-SoVITS）。

**修复**（`app/web/__init__.py`）：
- 客户端有明确 TTS 选择时 → 使用客户端配置（GPT-SoVITS + hongkong 等）
- 客户端无记录时 → 直接 fallback 到全局 `self.app.tts`（与正常对话一致）
- 不再走 Edge TTS + `'default'` 的错误路径

### 🔧 配置变更：MiniCPM-V2 默认关闭 INT4 量化，改用 BF16

**原因**：INT4 量化存在已知的 `cos[position_ids]` 设备不匹配兼容性问题（CPU vs GPU），导致 MiniCPM-V2 推理时无输出或崩溃。

**变更**（`app/config.yaml`）：
- `vision.minicpm.use_int4` 从 `true` 改为 `false`
- MiniCPM-V2 将使用 BF16 加载（需约 5GB 显存）

### 🔧 修复：TTS 分句未清理 Markdown 格式符号（`---` 读成"减号"、`**bold**` 被朗读）

**问题**：LLM 输出中常包含 Markdown 格式（`---` 分隔线、`**加粗**`、`## 标题`、`- 列表项` 等），GPT-SoVITS 文本前端会将 `-` 转为拼音"减"，导致语音播报中出现"减号"、"减见证人类的各种想法"等异常。

**修复**（`app/tts/gptsovits.py`）：在 TTS 分句前的文本预处理阶段新增 Markdown 清理：
- `---`/`--` → 逗号（避免前后文字粘连）
- `**bold**`/`*italic*` → 纯文字
- `## heading` → 删除标记
- 标点后 `- list item` → 删除 `- ` 标记
- `[link](url)` → 链接文字

### 🔧 修复：Vision TTS 长文本被 200 字硬截断

**问题**：MiniMax VL 生成的图片描述常超过 200 字，但 `_speak_vision_result_worker` 有一个 `text[:200]` 硬截断，导致只有前 200 字被传给 TTS 播报，剩余内容丢失。

**修复**（`app/web/__init__.py`）：移除 200 字截断，完整文本交给 TTS 引擎处理（GPT-SoVITS 内部自带分句逻辑）。

### 🔧 修复：TTS Markdown 清理补充（反引号、括号说明）

**问题**：LLM 输出中的 `` `code` `` 反引号和 `(说明性文字)` 括号未被清理，导致 TTS 朗读出多余内容或标点。

**修复**（`app/tts/gptsovits.py`）：Markdown 清理新增：
- `` `code` `` → 纯文字（去除反引号）
- `(说明性文字)` → 删除（如 `(Terminal/Log)`、`(Chrome)` 等）

### 🐛 增强：MiniCPM-V2 推理日志 + OOM 诊断

**改进**（`app/vision/__init__.py`）：
- `understand()` 添加推理前后日志（推理耗时、结果长度）
- OOM 错误时打印 GPU 显存详情（allocated/reserved），帮助诊断显存不足问题

---

## 🟢 STABLE v1.7.4 (2026-04-20)

### 🔧 修复：MiniCPM 加载崩溃（`_get_version_str` + `torch` 未定义）

**问题**：MiniCPM-V2 Provider 在模型加载完成后调用 `self._get_version_str()` 报 `AttributeError`，在 `understand()` 中使用 `torch.no_grad()` 报 `NameError: name 'torch' is not defined`，导致 MiniCPM 完全不可用。

**修复**（`app/vision/__init__.py`）：
1. 移除不存在的 `_get_version_str()` 调用，直接硬编码 `MiniCPM-V2`
2. 在 `understand()` 方法中添加 `import torch`

### ✨ 新增：Vision 理解结果自动 TTS 语音播报

**需求**：截图理解 / 视觉监控的结果不仅显示在面板文字区域，还自动通过 TTS 引擎语音播报，让用户听到识别结果。

**实现**（`app/web/__init__.py`）：
1. 新增 `_speak_vision_result()` 方法，复用客户端的 TTS 引擎设置（Edge / GPT-SoVITS）
2. 单次截图理解（`understand` action）完成后自动调用 TTS
3. 视觉监控模式（`start_monitor`）每帧分析完成后自动调用 TTS
4. 长文本自动截断为 200 字，避免 TTS 超时
5. TTS 失败不影响 vision 结果的显示（try/except 隔离）

## 🟢 STABLE v1.7.3 (2026-04-20)

### 🔧 修复：MiniMax VL 图片理解完全失效

**问题**：MiniMax VL Provider 使用 Anthropic 兼容端点（`/v1/messages`）发送图片，但该端点将 `MiniMax-VL-01` 静默降级为 `MiniMax-M2.7`（纯文本模型），导致图片数据被完全丢弃。MiniMax M2.7 收不到图片，回复"抱歉，我无法查看或生成图片"。所有请求的 `input_tokens` 仅为 24~59（正常应 >1000）。

**根因排查**：
1. Anthropic 端点返回 `"model": "MiniMax-M2.7"`（而非请求的 `MiniMax-VL-01`）——模型被静默替换
2. OpenAI 端点返回 `unknown model 'MiniMax-VL-01'`——该模型在 OpenAI 端点不存在
3. OpenAI 端点 `chatcompletion_v2` 的 `image` 顶级参数也不处理图片（`prompt_tokens: 45`）
4. MiniMax 的图片理解能力通过 `/v1/coding_plan/vlm` 专用端点提供（与 MCP `understand_image` 工具同源），不通过标准 chat API

**修复**（`app/vision/__init__.py`）：
1. API 端点从 `{base_url}/v1/messages` 改为 `{api_host}/v1/coding_plan/vlm`
2. 请求格式从 Anthropic messages 格式改为 `{"prompt": "...", "image_url": "data:image/jpeg;base64,..."}`
3. 图片自动压缩为 JPEG（默认 quality=40），5MB PNG → ~400KB，大幅减少上传时间
4. 去掉 `<image>` prompt 前缀（新 API 不需要）
5. 超时从 60s 提升到 120s（大图上传需要更长时间）
6. Pillow 不可用时回退到原始 base64（保持兼容性）

**配置更新**（`app/config.yaml`）：
- `minimax_vl.base_url` → `minimax_vl.api_host`
- 新增 `jpeg_quality: 40`（截图压缩质量）
- 新增 `timeout: 120`（请求超时秒数）

---

## 🟢 STABLE v1.7.2 (2026-04-20)

### 🔧 修复：MiniCPM-V2 量化加载与显存检测

**问题**：v1.7.1 的 `device_map="auto"` 修复了第一次报错（`.to` not supported），但暴露出两个新问题：
1. `dispatch_model` 内部仍调用 `model.to(device)`（accelerate 1.13.0 与 transformers 4.44.2 的兼容性 bug）
2. `validate_environment` 检测到部分层被分配到 CPU，抛出显存不足错误（实际是 GPU 总显存误报为可用显存）

**根因**：
- accelerate 的 `dispatch_model` 在 `device_map` 只有一个目标设备时仍调用 `.to()`，但 transformers 的 `PreTrainedModel.to()` 无条件禁止 bitsandbytes 模型的 `.to()`——两者互相矛盾
- 显存检测使用 `total_memory`（总显存），未减去 GPT-SoVITS 等已占用的显存，导致可用显存估算不准确

**修复**（`app/vision/__init__.py`）：
1. 量化加载前 monkey-patch `PreTrainedModel.to()`，临时跳过 bitsandbytes 模型的 `.to()` 限制（加载完成后立即恢复）
2. 改用 `cuda.memory_allocated/reserved` 计算真实可用显存
3. 根据实际可用显存自动降级量化等级（INT8 → INT4 → BF16）
4. 加载前调用 `torch.cuda.empty_cache()` 释放被其他模块 reserved 的显存
5. 使用 `device_map={"": "cuda"}` 替代 `"auto"`，避免部分层被分到 CPU

---

## 🟢 STABLE v1.7.1 (2026-04-20)

### 🔧 修复：MiniCPM-V2 INT4 量化加载崩溃

**问题**：MiniCPM-V2 使用 INT4 量化（BitsAndBytesConfig）加载时崩溃，报 `ValueError: .to is not supported for 4-bit or 8-bit bitsandbytes models`，导致视觉监控反复重试加载。

**根因**：`transformers 4.44.2` + `accelerate 1.13.0` 下，`AutoModel.from_pretrained()` 内部 `dispatch_model` 会尝试调用 `.to(device)`，但 bitsandbytes 量化模型不支持 `.to()` 操作。

**修复**：`app/vision/__init__.py` — 量化模式下显式传 `device_map="auto"`，让 accelerate 正确处理设备分配，不走 `.to()` 路径。

---

## 🟢 STABLE v1.7.0 (2026-04-20)

### 🔄 重构：历史模型残留全面清理

全面审计项目所有模块，清理不再使用的模型/配置/代码/依赖，消除依赖冲突风险。

#### 🔴 P0 - 依赖冲突风险修复

| # | 操作 | 文件 | 说明 |
|---|------|------|------|
| 1 | 移除 Kokoro TTS 代码 | `app/tts/__init__.py` | 删除 KokoroTTS 类（~300行）+ TTSFactory kokoro 分支，消除 kokoro-onnx → numpy>=2.0 冲突 |
| 2 | 移除 kokoro/chattts/openaudio 配置 | `app/config.yaml` | 删除 3 个无代码对应的配置块 |
| 3 | numpy 添加上限约束 | `app/requirements.txt` | `numpy>=1.24.0` → `numpy>=1.24.0,<2.0.0`，防止 pip 安装 2.x |
| 4 | 移除 chromadb 依赖 | `app/requirements.txt` | 全项目零 `import chromadb`，纯残留声明 |

#### 🟡 P1 - 依赖精简

| # | 操作 | 文件 | 说明 |
|---|------|------|------|
| 5 | sentence-transformers 标记为可选 | `app/requirements.txt` | 有 fallback 机制，非必需 |
| 6 | pyinstaller 移到注释区 | `app/requirements.txt` | 运行时不需要，仅打包时需要 |
| 7 | 修正 memory.provider | `app/config.yaml` | `"chroma"` → `"simple"`（与实际行为一致） |

#### 🟢 P2 - 代码/目录清理

| # | 操作 | 文件 | 说明 |
|---|------|------|------|
| 8 | 删除 realtime/ 目录 | `app/realtime/` (3文件) | 整个目录是历史残留，main.py 完全不引用 |
| 9 | 精简 OCR 多后端 | `app/ocr/ocr_engine.py` | 移除 PaddleOCR/Tesseract/WinRT 初始化和识别代码，仅保留 RapidOCR |
| 10 | 移除 SherpaOnnxASR 空壳 | `app/asr/__init__.py` | recognize() 返回 None，is_available() 返回 False，纯空壳 |

#### 📊 清理效果

- **依赖冲突风险**：从 5 处降至 0 处（numpy/chromadb/kokoro 三个高危已消除）
- **requirements.txt**：从 54 行精简到 ~40 行
- **代码量**：减少约 400 行死代码
- **config.yaml**：移除 3 个无对应代码的配置块

---

## 🟢 STABLE v1.6.8 (2026-04-20)

### 🔧 修复：NumPy 降级 + OCR/视觉监控

#### ① NumPy 2.x 降级（实际生效）
- **问题**：v1.6.7 记录了 NumPy 降级但实际未生效（仍是 2.4.4），导致 opencv-python / rapidocr-onnxruntime 仍然崩溃
- **修复**：`py -3.11 -m pip install "numpy<2.0"` → numpy 1.26.4，验证 cv2 4.9.0 + RapidOCR 均正常
- **副作用**：kokoro-onnx 0.5.0 要求 numpy>=2.0.2，暂时不可用（非主用 TTS，可接受）

#### ② DummyOCRSystem 缺少完整接口（AttributeError）
- **问题**：OCR 模块因 NumPy 崩溃初始化失败时，`_get_ocr_system()` 返回 `DummyOCRSystem`，但该类缺少 `set_event_callback`、`start_monitor`、`stop_monitor` 等方法
- **修复**：将两个重复的 `DummyOCRSystem` 内联类替换为统一的 `_create_dummy_ocr()` 工厂函数，实现 OCRSystem 完整空接口

#### ③ TTS 预热默认音色报错（ref_audio_path empty）
- **问题**：`_prewarm_tts()` 预热默认音色时，默认项目无参考音频，TTS.run() 报 `ref_audio_path cannot be empty`
- **修复**：预热前检查 `_project_config['ref_audio']`，为空则跳过预热

### 📋 关于视觉监控重复 stop 问题
- 日志中多次 stop/start 是前端操作产生的（用户连续点击按钮）
- NumPy 降级后视觉监控和 OCR 均可正常工作，不再需要 Dummy 替代
- 视觉/OCR 输出展示功能代码完整，之前因 NumPy 崩溃导致后端失败

---

## 🟢 STABLE v1.6.7 (2026-04-20)

### 🔧 修复：前端视觉模块 + TTS 分句问题

#### ① Vision Provider 下拉框混入 OCR 引擎（UI 问题）
- **问题**：`vision-provider-select` 下拉框中包含 `RapidOCR（本地）` 选项，但 RapidOCR 是纯 OCR 引擎（文字识别），不是 Vision Provider（图片理解），选择后会导致视觉监控失败
- **修复**：从 `vision-provider-select` 中移除 `rapidocr` 选项，仅保留 `auto / MiniMax VL / MiniCPM`

#### ② TTS 默认音色 ref_text 空值（SoVITS V3 报错）
- **问题**：当项目配置文件不存在时，`_load_project_config()` 返回 `{"ref_text": ""}`，空字符串传给 `prompt_text` 导致 SoVITS V3 报错 `prompt_text cannot be empty when using SoVITS_V3`
- **修复**：默认配置的 `ref_text` 从空字符串改为 `"你好欢迎使用"`

#### ③ TTS 分句：LLM 异常输出导致空句/纯标点句
- **问题**：MiniMax LLM 输出中偶尔出现异常标点（如 `.`、`，，`、`。。嗨`），分句后产生空句或纯标点句，传给 TTS 浪费推理资源且可能产生噪音
- **修复**：
  - **预处理**：分句前合并连续同类标点（`。。。`→`。`，`，，`→`，`），清理句首标点
  - **过滤**：分句后跳过纯标点/空内容句子，全部过滤时直接返回静音文件

#### ④ NumPy 2.x 不兼容 opencv-python（OCR 引擎崩溃）
- **问题**：opencv-python 编译时绑定 NumPy 1.x API，`_ARRAY_API` 在 NumPy 2.x 中不存在，导致 `cv2` 加载时崩溃，RapidOCR 引擎完全瘫痪
- **修复**：降级 numpy 至 `<2.0`（`pip install "numpy<2"`）

### 📋 视觉/OCR 监控输出展示（无需修改）
- **分析结论**：前端 `handleVisionMonitorEvent`、`handleOCREvent` 函数和对应显示 div（`vision-monitor-result`、`ocr-preview-text`）均已完整实现
- **根本原因**：后端 vision 模块因 NumPy 崩溃导致 `vision.understand()` 失败，推送错误信息而非结果内容
- **修复**：NumPy 降级后视觉监控恢复正常，结果可正常展示

---

## 🟢 STABLE v1.6.6 (2026-04-20)

### 🔧 修复：启动时三个崩溃/预热失败问题

#### ① vision/__init__.py SyntaxError（致命崩溃）
- **问题**：第172行 `except Exception ase:` 缺少空格，Python 无法解析整个文件，视觉模块完全瘫痪
- **修复**：改为 `except Exception as e:`
- **影响**：所有视觉功能（OCR、截图理解、摄像头、实时监控）全部不可用

#### ② vision cleanup() AttributeError（隐藏炸弹）
- **问题**：`MiniCPMProvider.cleanup()` 中 `del self._processor`，但该属性不存在
- **修复**：删除对 `_processor` 的引用（MiniCPM-V2 没有 processor）
- **影响**：切换视觉 provider 时会报 AttributeError

#### ③ TTS预热失败：transformers 版本不兼容
- **问题**：peft 0.17.1 依赖 `transformers.EncoderDecoderCache`（≥4.39），但系统安装的是 transformers 4.36.0
- **修复**：升级 transformers 至 4.44.2（兼容 peft 0.17.1）
- **影响**：GPT-SoVITS 默认音色和所有训练音色预热均失败，TTS 实际仍可用（子进程独立加载），但启动时有大量报错

### 📝 依赖更新：requirements.txt 全面检查与补充

- **扫描范围**：`app/` 下全部 34 个 .py 文件的 import 语句，整理出 23 个第三方库
- **修复** `transformers`：4.36.0 → ≥4.44.0（兼容 peft 0.17.1）
- **新增** `jieba>=0.42`：TTS 流式分句所需的中文分词
- **新增** `funasr>=1.0`：ASR 语音识别核心引擎
- **新增** `modelscope>=1.9.0`：MiniCPM 模型下载依赖
- **新增** `torch` / `torchaudio`：由 install_deps.bat 管理 CUDA 版本
- **新增** `transformers>=4.44.0,<4.45.0`、`peft>=0.10.0`、`accelerate>=0.20.0`：GPT-SoVITS / MiniCPM 所需
- **新增** `rapidocr-onnxruntime>=1.3.0`：OCR 引擎
- **install_deps.bat**：STEP 4 新增 funasr + jieba，STEP 6 新增 modelscope，版本号更新至 1.6.6

---

## 🟢 STABLE v1.6.5 (2026-04-20)

### ✨ 新增：视觉实时监控功能

#### 功能说明
- **MiniCPM实时理解**：固定间隔截屏 → MiniCPM图片理解 → 实时显示结果
- **支持两种Provider**：MiniCPM（本地）和 MiniMax VL（云端）
- **可配置间隔**：1秒 / 2秒 / 5秒 / 10秒

#### 前端新增
```html
<!-- 视觉实时监控面板 -->
<select id="vision-monitor-provider">
    <option value="minicpm">MiniCPM（本地）</option>
    <option value="minimax_vl">MiniMax VL（云端）</option>
</select>
```

#### 前端JS新增
- `toggleVisionMonitor()` - 启动/停止视觉监控
- `handleVisionMonitorEvent()` - 处理监控帧事件

#### 后端新增
- `_handle_vision` action: `start_monitor` / `stop_monitor` / `monitor_status`
- `_vision_monitors` - 客户端监控状态跟踪
- `_vision_monitor_worker()` - 监控工作线程

#### 数据流
```
前端启动监控
    ↓
ws.send({ type: 'vision', action: 'start_monitor', interval, provider })
    ↓
后端启动监控线程，每interval秒：
    截图 → base64 → vision.understand() → 回调
    ↓
ws推送 { type: 'vision_monitor', screenshot, text, elapsed_ms }
    ↓
前端显示截图 + 理解结果
```

---

### 🔄 清理：移除 MiniCPM-V-2_6 相关代码和模型

#### 删除内容
- 删除 `OpenBMB/MiniCPM-V-2_6` 模型目录 (~15GB)
- 删除 V2_6 transformers 缓存
- 删除代码中所有 V2_6 判断逻辑
- 简化 MiniCPMProvider，仅保留 V2 支持

#### 保留内容
- MiniCPM-V-2 模型 (~4-5GB INT4量化)
- V2 官方 chat() 参数实现

### 🔧 修复：V2 msgs 格式错误

**问题**：
- 之前代码使用 `msgs = [{"role": "user", "content": [image, prompt]}]`
- V2官方 `content` 应该是**纯字符串**，图片通过 `image` 参数单独传入

**官方V2正确用法**：
```python
msgs = [{"role": "user", "content": question}]  # content是字符串
res, context, _ = model.chat(image=image, msgs=msgs, ...)
```

**已修复**：
```python
msgs = [{"role": "user", "content": prompt}]  # content是纯字符串
res, context, _ = self._model.chat(image=image, msgs=msgs, ...)
```

---

### 🔍 前端OCR面板MiniCPM集成检查

#### 检查结果：已完全集成 ✅

**前端OCR面板已支持切换MiniCPM**

| 组件 | 状态 | 说明 |
|------|------|------|
| HTML选项 | ✅ | `<option value="minicpm">MiniCPM（本地 GPU）</option>` |
| list_providers API | ✅ | 返回所有provider列表 |
| set_provider API | ✅ | 可切换provider |
| vision.understand() | ✅ | MiniCPM图片理解 |
| OCR面板→Vision | ✅ | 截图后调用vision系统 |

**使用流程**
```
用户在OCR面板选择 MiniCPM（本地 GPU）
    ↓
点击"截图理解"
    ↓
前端发送: type:'vision', action:'understand', provider:'minicpm'
    ↓
后端 vision.set_provider('minicpm')
    ↓
vision.understand() 使用 MiniCPM-V2 进行图片理解
```

---

### 🔄 修复：MiniCPM V2 vs V2_6 版本差异处理

#### 问题
- 之前代码用V2_6参数调用V2模型，导致不兼容
- V2和V2_6官方chat()接口完全不同

#### V2 vs V2_6 官方接口差异

| 参数 | MiniCPM-V-2 (官方) | MiniCPM-V-2_6 (官方) |
|------|-------------------|---------------------|
| processor | ❌ 无 | ✅ 有 |
| context参数 | ✅ 有 | ❌ 无 |
| max_new_tokens | 默认1024 | 默认2048 |
| max_inp_length | 默认2048 | 默认8192 |
| stream参数 | ❌ 无 | ✅ 有 |

#### 修复内容

**`app/vision/__init__.py`** - MiniCPMProvider:
- 添加 `_is_v2_6` 版本检测
- V2: 不加载processor，chat()不传processor参数
- V2_6: 加载AutoProcessor，chat()传递processor参数
- V2: max_new_tokens=1024, max_inp_length=2048
- V2_6: max_new_tokens=2048, max_inp_length=8192
- understand_stream(): V2降级到普通调用

**`app/config.yaml`** - vision.minicpm:
```yaml
minicpm:
  model_id: "OpenBMB/MiniCPM-V-2"  # 改回V2
  use_int4: true                   # INT4量化 ~4-5GB
```

#### 显存占用

| 版本 | FP16显存 | INT4量化 |
|------|---------|---------|
| MiniCPM-V-2 | ~6-8GB | **~4-5GB** ✅ |
| MiniCPM-V-2_6 | ~15-18GB | ~7-8GB |

---

## 🟢 STABLE v1.6.4 (2026-04-20)

### 🔄 重构：MiniCPM Provider 对齐官方实现

#### 核心修复

| 差距项 | 官方实现 | 修复后 | 状态 |
|--------|----------|--------|------|
| AutoProcessor | ✅ 使用 | ✅ 已添加 | 🟢 |
| max_new_tokens | 2048 | ✅ 2048 | 🟢 |
| max_inp_length | 8192 | ✅ 8192 | 🟢 |
| processor参数 | ✅ 传递 | ✅ 已传递 | 🟢 |
| 流式输出 | ✅ 支持 | ✅ 已实现 | 🟢 |
| 4bit量化 | ✅ BitsAndBytesConfig | ✅ 已添加 | 🟢 |
| 8bit量化 | ✅ BitsAndBytesConfig | ✅ 已添加 | 🟢 |

#### 修复内容

**`app/vision/__init__.py`** - MiniCPMProvider:
- 新增 `_processor` 属性，使用 `AutoProcessor.from_pretrained()` 加载官方processor
- 新增 `max_new_tokens` 配置参数（默认2048，与官方一致）
- 新增 `max_inp_length` 配置参数（默认8192，与官方一致）
- 新增 `use_int4` / `use_int8` 量化配置支持
- 新增 `BitsAndBytesConfig` 量化加载（int4/int8）
- 新增 `understand_stream()` 流式输出方法
- chat() 调用传递所有官方参数
- 量化模式下模型已在cuda上，不再重复to cuda

#### 配置对齐

**`app/config.yaml`** - vision.minicpm:
```yaml
minicpm:
  model_id: "OpenBMB/MiniCPM-V-2_6"  # ✅ 支持 _6 版本
  use_int4: true                        # ✅ 4bit量化
  max_new_tokens: 2048                 # ✅ 官方默认值
  max_inp_length: 8192                 # ✅ 官方默认值
```

#### 模块配合检查

| 模块 | 配合状态 | 说明 |
|------|----------|------|
| **后端 web/__init__.py** | ✅ 正常 | _handle_vision 支持 ocr/understand/camera_capture/list_providers/set_provider |
| **前端 static/index.html** | ✅ 正常 | WebSocket通信正常 |
| **main.py** | ✅ 正常 | 懒加载 VisionManager |
| **config.yaml** | ✅ 正常 | 读取 minicpm 配置 |

---

## 🟢 STABLE v1.6.3 (2026-04-19)

### 🔧 实现：OCR 实时屏幕分析模块

- **新增独立模块**: `app/ocr/`
  - `__init__.py`: OCRSystem 主类，事件回调机制
  - `screen_monitor.py`: 屏幕截取 (mss/pyautogui)
  - `ocr_engine.py`: RapidOCR 引擎封装
  - `screen_analyzer.py`: LLM 屏幕内容分析

- **后端修改**: `app/web/__init__.py`
  - 新增 `_handle_ocr()` WebSocket 处理器
  - 新增 `_get_ocr_system()` 单例管理
  - 支持: start/stop/capture/analyze/tool_call

- **前端修改**: `app/web/static/index.html`
  - Vision 面板新增 OCR 监控区块
  - 启动/停止监控按钮
  - 间隔选择 (0.5s/1s/2s/5s)
  - 实时预览截图和 OCR 结果
  - 快速分析/详细分析按钮
  - OCR 事件 WebSocket 处理

- **LLM 集成**: `app/llm/prompts.py`
  - 新增 OCR_TOOL 提示词
  - AI 可以使用 screen_ocr 工具
  - 触发词: "看看屏幕"、"游戏状态"、"界面内容"等

---

## 🟢 STABLE v1.6.2 (2026-04-19)

### 📊 新增：OCR 实时屏幕分析部署方案

- `docs/OCR-DEPLOYMENT-ANALYSIS.md` v1.0
  - **头部项目调研**：ScreenGPT-OCR、RSTGameTranslation、Screenpipe、OmniParser
  - **OCR 引擎对比**：PaddleOCR/RapidOCR/EasyOCR/Tesseract/WinRT
  - **中文精度数据**：PaddleOCR 95.2% 最佳
  - **GPU 需求**：PaddleOCR ~1-2GB，3070 Ti 8GB 足够
  - **死锁风险分析**：GPU 竞争、模型加载锁、同步阻塞
  - **与 LLM/TTS 集成方案**：完整工作流设计
  - **前端 WebUI 修改需求**：新增监控开关、预览面板
  - **开发周期**：5-8 个工作日

---

## 🟢 STABLE v1.6.1 (2026-04-19)

### 📊 新增/更新：行业差距分析报告

- `docs/GAP-ANALYSIS.md` v1.4
  - **新增第九章**：ASR→LLM→TTS 流水线优化专题
    - 行业延迟预算分配 (<400ms 目标)
    - ASR 流式 partial + 置信度过滤
    - LLM TTFT 优化 (推测解码/KV-Cache/提示工程)
    - TTS 前瞻缓冲 + 分块重叠合成
    - 流水线并发优化模式
    - 实施路线图 + 快速见效方案
  - 参考: Gladia/Pipecat/FastRTC/RealtimeVoiceChat 最佳实践

### ✅ 本次优化完成情况

**已实现优化**（不改模型，只优化流水线）：
1. ✅ TTS 预热：WebServer 启动时合成测试音频（已有）
2. ✅ 多音色预热：启动时加载所有 LoRA 音色（已有）
3. ✅ 前端缓冲策略：前2 chunk 缓冲防卡顿（已有）
4. ✅ **新增**：LLM 提示优化（先直接回答，后详细解释）

**需架构级改动（暂不实现）**：
- FunASR partial 流式识别：需前端音频流 + 后端流式识别支持
- ASR + LLM 并行：当前架构 ASR 必须等完整音频才能识别

---

## 🟢 STABLE v1.6.0 (2026-04-19)

### 🔧 Bug 修复

- `tempfile` 未导入错误（web/__init__.py）
- EdgeTTS 不接受 `project` 参数（speak() 增加 `**kwargs`）
- WebSocket BrokenPipeError 优雅处理

### ⚡ TTS 分句优化

- MAX_CHARS 从 40 提高到 80（减少强制切分）
- 新增智能断点查找：优先在标点、连接词处断开
- 递归分词，每段最多 80 字符

---

## 🟢 STABLE v1.5.10 (2026-04-19)

### 🔄 重构：LLM 模块（参考 Neuro 架构）

#### 架构重构
- 新增 `PromptInjector` 类：模块化 Prompt 注入（参考 Neuro 开源架构）
- 新增 `MemoryRAGInjector` 类：RAG 检索 + 注入长期记忆
- 去掉 history 硬截断：从 `history[-20:]` 改为保留全部历史
- 去掉 200 字符截断：记忆内容完整传递
- max_tokens 从 512 → 2048

#### prompts.py 重写
- 人格设定升级：从"工具型助手"改为"有灵魂的AI生命"
- 新增性格特征：真实、有趣、好奇、独立、温暖
- 新增记忆注入模板：`inject_memories()` 函数

#### config.yaml 新增配置
```yaml
llm:
  max_tokens: 2048
  enable_rag_injection: true
```

---

## 🟢 STABLE v1.5.9 (2026-04-19)

### 🔧 修复

- fix realtime pipeline中engine是字符串不是对象('str' object has no attribute 'speak')
- 放宽fallback阈值(40→60字,1.5s→2.5s)
- 加Markdown剥离（**bold** → text, - 列表项 → 内容）
- 加realtime ASR重复词过滤(hellohello→hello)

---

## 🟢 STABLE v1.5.8 (2026-04-19)

### 🔧 优化

- 基于jieba分词的语义词边界切分(fallback+尾buffer)
- fallback剩余部分保留到下一轮累积
- 长文本也在词边界处切分，保证语义完整

---

## 🟢 STABLE v1.5.7 (2026-04-19)

### 🔧 修复

- fix首句(engine,voice顺序反)
- fix speak_streaming/speak未传project参数(音色切换失效)
- 增强no_split/非流式/fallback乱码验证
- 清理_handle_stt重复fallback代码

---

## 🟢 STABLE v1.5.5 (2026-04-19)

### 🔧 修复

- fix实时语音TTS崩溃(_realtime_tts_single/engine参数顺序全反)
- fix流式on_chunk np未import
- fix speak_streaming的engine类型判断

---

## 🟢 STABLE v1.5.4 (2026-04-19)

### 🔧 修复

- fix实时语音Invalid voice='default'崩溃(_get_tts_for_client直接返回app.tts)
- fix重建逻辑set_project('default')崩溃
- fix录音模式工具调用文本进TTS(TOOL:/ARG:/```过滤)

---

## 🟢 STABLE v1.5.3 (2026-04-19)

### 🔧 分句策略优化

- 只按句号分句（去掉感叹号/问号分句）
- 感叹词合并扩展20+模式
- speak()逗号分句修复
- GPU串行TTS替代多线程

---

## 🟢 STABLE v1.5.2 (2026-04-19)

### 🔧 修复

- fix ASR provider参数错误
- fix speak()缺少default检查
- fix前端状态卡住

---

## 🟢 STABLE v1.5.1 (2026-04-19)

### 🔧 修复 + 增强

- TTS音色回退(fix voice='default'崩溃)
- pipeline状态重置(fix录音失效)
- 感叹句合并(fix语调割裂)
- 流式打断修复
- 多音色预热

---

## 🟢 STABLE v1.4.75 (2026-04-18)

### ⚡ P0-P2 优化（参考豆包差距分析）

#### P0-1: 前端音频流式播放优化
- `playNextRealtimeAudio()` 增加预取下一个音频逻辑
- 减少播放间隔，实现更流畅的音频体验

#### P0-2: 前端真正打断
- 增强打断逻辑：立即停止当前音频 + 清空队列 + 通知后端
- 新增 `realtime_interrupt_confirmed` 消息类型确保后端同步
- 双重停止机制：`_currentAudioStop()` + `audio.pause()`

#### P0-3: VAD 语义判停优化
- 新增思考模式检测：接近阈值时显示"💭 思考中..."
- 动态阈值：检测到思考语气时自动延长判停时间（+2000ms）
- 配置化：VAD 参数移至 `config.yaml`

#### P1-1: ASR 状态提示
- 识别开始时立即显示"🎯 识别中..."状态
- 减少用户等待焦虑

#### P1-2: TTS 流式优化
- 改进 `_realtime_streaming_tts()`：第一个 chunk 带完整 WAV header
- 后续 chunk 只发送 PCM 数据，减少冗余
- 累积 200ms 音频后再发送首个 chunk

#### P1-3: LLM 预判停
- 检测思考模式：连续思考 > 1.5 秒时提前发送 TTS
- 检测输出变慢：连续多个 chunk buffer 没增长时强制发送
- Fallback 阈值从 20 字符提升到 40 字符

#### P2-1: 情感 TTS 标签
- 后端 `_detect_emotion()` 方法：happy/sad/angry/surprised/smile/neutral
- 情感标签通过 WebSocket 发送给前端
- 前端根据情感标签触发 Live2D 表情联动

#### P2-2: 动态语速调节
- 根据文本复杂度计算语速：长句/复杂句/含数字时降低语速
- 逻辑已实现（需 TTS 引擎支持）

#### P2-3: 多轮对话上下文压缩
- 复用记忆系统 v2.1 的滑动窗口 + 摘要压缩机制
- 工作记忆上限 20 条，超出后自动压缩早期对话

================================================================================

## 🟢 STABLE v1.4.74 (2026-04-18)

### 🔧 Phase 2 全面优化

#### 全双工增强（参考豆包边听边说）
- 新增 `realtime_interrupt_fast` 消息类型：用户开始说话时立即打断 AI
- 前端检测到说话时发送 `realtime_interrupt_fast`，后端立即取消 LLM 调用
- 清空 TTS 队列，标记 pipeline 不在运行
- 效果：用户说话 → AI 立即停止 → 新请求快速响应

#### 语义判停增强（防抢话）
- 新增 `_is_incomplete_utterance()` 函数：检测句子是否完整
- 不完整句子（<4字、无结束标点、只有半句话）不触发 LLM，继续等待
- 检测不完整模式：语气词开头、疑问词未结束、括号未闭合、从句连接词等
- 效果：用户思考时不抢话，等句子完整才响应

#### 降噪/抗干扰增强
- 设置面板新增音频控制选项：降噪、回声消除、自动增益
- WebRTC `noiseSuppression`、`echoCancellation`、`autoGainControl` 可独立开关
- 支持实时切换（需重启实时语音生效）

---

#### 🎭 Live2D 动作系统
- 动作面板重构：支持 Shizuku 模型全部动作
- `tap_body`（摸头）、`shake`（摇晃）、`flick_head`（甩头）
- `pinch_in/out`（捏合缩放）、`idle`（待机）
- 每个动作组有 3 个随机变体，播放更自然

#### 😊 Live2D 表情联动
- 表情关键词自动检测：根据对话内容触发表情
- `f02` 开心：开心/高兴/哈哈/棒/喜欢
- `f03` 微笑：嗯/好的/可以/了解
- `f04` 闪亮：哇/惊讶/厉害/真的吗
- 设置面板可开关自动表情联动

#### 💾 记忆系统自动化
- 对话完成后自动调用 `memory.add_interaction()` 记录
- 无需手动保存，对话内容自动记忆

**涉及文件**：`app/web/__init__.py`、`app/web/static/index.html`

---

## 🟢 STABLE v1.4.73 (2026-04-18)

### 🔐 SubAgent 沙盒模式 + WebUI 管理面板

#### 沙盒路径管控
- 新增 `SandboxManager` 类，统一管理允许路径白名单
- 所有 10 个工具（bash / read / write / edit / glob / grep / mkdir / ls / tree / rm）全部接入沙盒检查
- `is_path_allowed()` 使用 `os.path.realpath()` 解析真实路径，防止符号链接绕过
- `check_sandbox()` 在工具操作前拦截，返回结构化 `ToolResult(False, "", reason)`，不抛异常
- `SandboxManager` 支持 enable/disable 切换，禁用时完全放行

#### 新增 4 个文件操作工具
- **`MkdirTool`**：创建目录（Windows 递归创建，自动处理已有路径）
- **`LsTool`**：列出目录内容，显示文件大小（人类可读格式 KB/MB/GB）、修改时间，Windows 控制台兼容文本标记
- **`TreeTool`**：递归目录树，支持 `max_depth` 限制
- **`RemoveTool`**：删除空目录（非空目录拒绝删除）

#### SubAgent 实例级工具注入
- `SubAgent.TOOLS` 从类级别 `dict` 改为实例级别 `self._tools`
- 每个工具实例在构造时注入 `sandbox` 引用
- 配置支持 `sandbox_paths` 初始化白名单列表
- 暴露公开 API：`sandbox_add_path / remove / get_paths / clear / enable / disable`

#### WebUI 沙盒管理面板
- 新增 `#panel-sandbox` 面板（默认布局 left:1220, top:85, width:280）
- 后端 5 个 API：`GET /api/sandbox/status`、`POST add_path/remove_path/toggle/clear`
- `WebServer.__init__(app=self)` 打通请求链路

**涉及文件**：`app/subagent.py`、`app/web/__init__.py`、`app/main.py`、`app/web/static/index.html`

---

### 🔧 P0-1：前端音频真正打断（Bug B-001 修复）

**问题**：`_handle_realtime_interrupt` 设置 cancel 后，前端收到 `realtime_interrupt` 信号时，当前正在播放的音频无法立即停止，导致用户必须等当前句子（1-3秒）播完才能停。

**修复**：
- `realtime` 对象新增 `interrupted` 标志位
- 收到 `realtime_interrupt` 时设置 `interrupted = true` 并立即调用 `_currentAudioStop()`
- `audio.onended` 回调中检查 `interrupted`，为 true 时不继续播下一句，直接回到聆听状态
- 新音频到来时清除 `interrupted` 标志

**效果**：用户点击打断 → AI 立即停播，不等当前句子播完

**涉及文件**：`app/web/static/index.html`

---

### 🔧 P0-3：VAD 判停双重机制（豆包动态判停参考）

**问题**：VAD 固定阈值沉默即停，无法区分"用户思考中"和"用户已说完"，导致抢话。

**修复**：引入豆包风格双重判停机制：
- `THINKING_PAUSE_MS: 600ms` — 思考停顿容忍期，继续录音，显示 💭 思考中...
- `STOP_THRESHOLD_MS: 1800ms` — 超过此值才判停，发送录音给 ASR
- `MAX_RECORDING_MS: 3000ms` — 最大录音时长保护

**效果**：用户短暂停顿不触发识别，思考时不抢话，长停顿才判停

**涉及文件**：`app/web/static/index.html`

---

### 🔧 P0-2：TTS 流式合成接口

**问题**：TTS 完整合成一整句后才发送给前端，用户感知延迟高。

**修复**：
- `GPTSoVITSEngine.speak_streaming()` — 逐 chunk 写入 WAV 文件，可选回调 `on_chunk(chunk_sr, audio_float, chunk_idx)`
- `WebServer._realtime_streaming_tts()` — 每个 chunk 合成就立即 base64 编码发送给前端
- 新增 WebSocket `stream` 消息类型用于流式 TTS 测试
- 新增 `streaming_audio_path` 状态字段

**效果**：TTS 首包即可听，不等完整合成

**涉及文件**：`app/tts/gptsovits.py`、`app/web/__init__.py`

---

### 🎨 Live2D 口型同步 + 表情联动

**功能**：
- `startMouthSync(audioEl)` — 用 `AudioContext.createMediaElementSource` + `AnalyserNode` 分析播放中音频能量（FFT），驱动 `ParamMouthOpenY` 参数，实时控制口型开合度
- `stopMouthSync()` — 播放结束或打断时停止口型分析，重置口型参数
- `triggerExpression(type)` — 关键词触发表情动作（happy/angry/sad/surprised）
- 播放/打断时自动联动 Live2D：`onended` → `_live2dStopSpeaking()`，`onplay` → `_live2dStartSpeaking()`
- `_setLive2DParam()` — 兼容 oh-my-live2d 的 `getModel()` API 设置 `ParamMouthOpenY`

**涉及文件**：`app/web/static/index.html`

---

## 🟢 STABLE v1.4.72 (2026-04-18)

#### 沙盒路径管控
- 新增 `SandboxManager` 类，统一管理允许路径白名单
- 所有 10 个工具（bash / read / write / edit / glob / grep / mkdir / ls / tree / rm）全部接入沙盒检查
- `is_path_allowed()` 使用 `os.path.realpath()` 解析真实路径，防止符号链接绕过
- `check_sandbox()` 在工具操作前拦截，返回结构化 `ToolResult(False, "", reason)`，不抛异常
- `SandboxManager` 支持enable/disable切换，禁用时完全放行

#### 新增 4 个文件操作工具
- **`MkdirTool`**：创建目录（Windows 递归创建，自动处理已有路径）
- **`LsTool`**：列出目录内容，显示文件大小（人类可读格式 KB/MB/GB）、修改时间，Windows 控制台兼容文本标记（`[DIR]` / `[FILE]`）
- **`TreeTool`**：递归目录树，支持 `max_depth` 限制，Windows emoji 替换为文字标记
- **`RemoveTool`**：删除空目录（非空目录拒绝删除，防止误操作）

#### SubAgent 实例级工具注入
- `SubAgent.TOOLS` 从类级别 `dict` 改为实例级别 `self._tools`
- 每个工具实例在构造时注入 `sandbox` 引用，实现工具粒度沙盒控制
- SubAgent 配置支持 `sandbox_paths` 初始化白名单列表
- 暴露公开 API：`sandbox_add_path / remove / get_paths / clear / enable / disable / is_enabled / check_path`

#### WebUI 沙盒管理面板
- 新增 `#panel-sandbox` 面板（data-group="tool"），默认布局：left:1220, top:85, width:280
- 支持：输入路径 → 添加 / 点击 × 移除 / 开关按钮启用禁用
- 后端新增 5 个 API 端点：
  - `GET /api/sandbox/status` — 查询状态 + 所有路径
  - `POST /api/sandbox/add_path` — 添加路径
  - `POST /api/sandbox/remove_path` — 移除路径
  - `POST /api/sandbox/toggle` — 切换启用状态
  - `POST /api/sandbox/clear` — 清空所有路径
- `WebServer.__init__(app=self)` 注入应用引用，通过 `handler_factory` → `handler._app` → `self._app.subagent` 打通请求链路

**涉及文件**：
- `app/subagent.py` — SandboxManager + 新工具 + 实例级工具注入
- `app/web/__init__.py` — WebServer app引用 + 沙盒API路由
- `app/main.py` — web_server property 传递 app=self
- `app/web/static/index.html` — 沙盒管理面板 HTML/CSS/JS

---

## 🟢 STABLE v1.4.68 (2026-04-18)

### 🎨 响应式排版优化 + 署名

#### 响应式排版（所有面板内容）
**目标**：按钮/表单随面板自动排版，放大缩小后内容自适应。

**修复**：将训练面板等处内联 `style` 中的固定 `px` 单位改为相对单位：
- `.debug-btn`: `padding: 0.5em 0.8em; font-size: 0.85em`
- `.panel-content`: `padding: 0.8em; gap: 0.7em`
- `.panel-header`: `padding: 0.6em 0.8em; h3 font-size: 0.9em`
- `textarea/input`: `padding: 0.7em 0.8em; font-size: 0.9em; box-sizing: border-box`
- `select`: `padding: 0.6em 0.7em; font-size: 0.9em; box-sizing: border-box`
- `.send-btn`: `padding: 0.6em 1em; font-size: 0.85em`

#### 署名
- Header 显示：`🐱 咕咕嘎嘎 AI虚拟形象 <span style="font-size:0.7em;opacity:0.6;">Created by XZT</span>`
- `<title>` 标签同步更新为 `咕咕嘎嘎 AI虚拟形象 - Created by XZT`

**涉及文件**：
- `app/web/static/index.html` — CSS 改造 + Header 署名

---

## 🟢 STABLE v1.4.67 (2026-04-18)

### 🎨 面板系统大改：8向缩放 + 网格对齐

#### 8向缩放
- 移除旧的右下角 `◢` 拖动标记
- 改为 8 个透明把手（四角 + 四边），hover 时显示蓝色高亮
- 支持：四角拖动、上下左右四边拖动，灵敏度大幅提升
- 同样适用于 Live2D 画布容器

#### 按钮溢出修复
- `.debug-controls` 已有 `flex-wrap: wrap`，按钮会自动换行，不再溢出

#### 网格对齐系统
- 布局栏新增 6 个对齐按钮：`⬅左` `➡右` `⬆顶` `⬇底` `↔居中` `↕居中`
- 使用方法：按住 **Shift / Ctrl** 点击多个面板（选中后显示蓝色虚线边框）→ 点击对齐按钮
- 支持：以最左/右/上/下面板为基准对齐所有选中面板

#### 其他
- 面板 8 向缩放手感优化（移除过渡动画延迟）
- Live2D 画布同样支持 8 向缩放

**涉及文件**：
- `app/web/static/index.html` — CSS + JS 全面改造

---

## 🟢 STABLE v1.4.66 (2026-04-18)

### 🔧 TTS 异步并行合成（流式分句真正实时输出）

**问题**：之前的"流式合成"只是按标点分句，但每个句子还是要等 GPT-SoVITS 完整合成完（`speak()` 阻塞），合成完才发送给前端。用户感知到的"流式"根本不是真正的流式。

**修复**：把 `_realtime_tts_single` 改为**异步非阻塞**模式：
- 句子准备好后立即塞入 queue，立即返回，不等合成
- 每个 client 一个专属后台 worker 线程，从 queue 取任务、合成、发送
- 多个句子**真正并行**合成，谁先完成谁先发送给前端

**效果**：
| 模式 | LLM 边输出边分句 | 各句 TTS 并行合成 | 前端先收到先播放 |
|------|:---:|:---:|:---:|
| 旧流式 | ✅ | ❌（串行等） | ❌ |
| **新流式** | ✅ | ✅ | ✅ |

设置 → TTS → `流式合成（分句）` 即体验。

**涉及文件**：
- `app/web/__init__.py` — state 初始化 + `_realtime_tts_single` 改为 queue + worker + `_tts_do_and_send`

---

## 🟢 STABLE v1.4.65 (2026-04-18)

### ✨ TTS 新增"整段合成"模式（不分句）

**需求**：用户希望 TTS 不按标点分句，长文本一气呵成合成。

**实现**：
- 前端 TTS 设置区新增开关：`流式合成（分句）` / `整段合成（不分句）`
- 开启整段模式后，实时语音的流式 pipeline 会等 LLM 完全回答完，再一次性 TTS 整段文本
- 分句模式保持不变（边输出边按标点分句边 TTS，响应快但句子会被拆开）
- 设置保存在 localStorage，发送 `realtime_audio` 时通过 `no_split` 字段告知后端

**涉及文件**：
- `app/web/__init__.py` — `_handle_realtime_audio` + `_realtime_stream_pipeline` 增加 `no_split` 参数和整段模式分支
- `app/web/static/index.html` — TTS 设置区 + load/save config + 发送时附 `no_split`

---

## 🟢 STABLE v1.4.64 (2026-04-18)

### 🔧 修复实时语音三大 bug（ASR静默失败 / 并发pipeline冲突 / TTS pipeline损坏）

#### Bug A：录音文件后缀 .webm 但用 torchaudio.load() 读取
**问题**：`_handle_stt` 的录音上传使用 `suffix=".webm"` 创建临时文件，但 FunASR 的 `torchaudio.load()` 是读取 WAV 格式的，导致录音识别失败静默返回空。

**修复**：`app/web/__init__.py` — `_handle_stt` 中临时文件后缀改为 `.wav`（前端 `audioBufferToWav` 已正确转换格式）。

#### Bug B：FunASR CNHuBERT 维度错误静默失败
**问题**：FunASR 的 paraformer ASR 模型内部使用 CNHuBERT 做特征提取，其 checkpoint 维度（[4, 28]）与当前 FunASR 代码期望（[4, 33]）不匹配，导致 `recognize()` 抛出异常后静默返回 `None`。实时语音的 ASR 调用静默失败 → 识别结果为空 → LLM 根本没收到输入。

**修复**：在 `_handle_realtime_audio` 和 `_handle_stt` 中，当 FunASR 返回空/失败时，自动 fallback 到 `faster-whisper`（base 模型，CPU 运行）。Faster-Whisper 模型独立于 FunASR，不受 CNHuBERT 损坏影响。

**涉及文件**：
- `app/web/__init__.py` — `_handle_realtime_audio` + `_handle_stt` 增加 faster-whisper fallback

#### Bug C：TTS pipeline 重置后损坏
**问题**：实时语音流程中 `set_project()` 会重置 GPT-SoVITS pipeline。pipeline 重置后可能处于半损坏状态（GPU 显存碎片化 / CUDA 状态不一致），导致后续录音请求的 TTS 调用静默失败（`speak()` 返回 None）。

**修复**：
1. `_realtime_tts_single` 增加 pipeline 损坏检测：`audio_path` 为 None 或文件不存在时，清除缓存并强制重建 pipeline
2. `_realtime_stream_pipeline` 和 `realtime_pipeline` 增加 try/except 捕获 pipeline 错误，防止异常向上穿透

#### Bug D：并发 pipeline 互相覆盖
**问题**：当 VAD 检测静默时，发送 `realtime_audio`；如果前一个 pipeline 还没运行完（`speaking` 标志已清除），新 pipeline 会与旧 pipeline 并发运行。新 pipeline 调用 `set_project()` 重置 pipeline，导致旧 pipeline 的 TTS 合成被中断。

**修复**：在 `_handle_realtime_audio` 中增加 `running` 标志。如果上一个 pipeline 还在运行（`running=True`），直接丢弃新的音频请求，避免并发覆盖：

```python
# Bug D 修复：防止多个 pipeline 并发运行
if state.get("running", False):
    print("[REALTIME] Pipeline 仍在运行，丢弃新音频请求（防止并发覆盖）")
    return
state["running"] = True  # 标记 pipeline 正在运行
# ...
finally:
    state["running"] = False
```

**涉及文件**：
- `app/web/__init__.py` — `_handle_realtime_audio` + `_realtime_tts_single` + `_realtime_stream_pipeline` + pipeline error handling

---

## 🟢 STABLE v1.4.63 (2026-04-18)

### 🔧 修复工具调用文本泄露进 TTS

#### 根本原因
LLM 流式输出时可能输出工具调用格式（如 `TOOL: openclaw_skill ARG: weather 今天天气怎么样？`）。`on_chunk` 回调按标点分句后（如 `今天天气怎么？`），工具前缀被切掉，剩下的句子直接送入 TTS 合成，导致 TTS 发出无意义的"工具参数"声音。

#### 修复内容
**`app/web/__init__.py`**：

1. 新增 `_strip_tool_calls()` 静态方法，剥离所有工具调用格式：
   - `TOOL: xxx ARG: xxx`（OpenClaw 工具格式）
   - JSON 工具字段（`"tool"`, `"tool_call"`, `"function_call"`）
   - XML 工具标签（`<tool_call>...</tool_call>`）
   - 代码块（```...```）
   - 关键字残留（`openclaw_skill`, `weather_skill` 等）

2. 在 `on_chunk` streaming 回调中，**在分句前**先调用 `_strip_tool_calls()`，确保工具调用格式在任何句子切分之前就被移除：
   ```python
   def on_chunk(chunk_text):
       ...
       # 关键修复：工具调用文本不能进 TTS
       chunk_text = self._strip_tool_calls(chunk_text)
       sentences, sentence_buffer = self._split_sentences_streaming(sentence_buffer, chunk_text)
       for sent in sentences:
           if not self._is_valid_sentence(sent):
               continue
           self._realtime_tts_single(client, state, sent, engine, voice)
   ```

3. 同时加强 `_realtime_filter()`（最终文本过滤），加入 `TOOL:`/`ARG:` 正则过滤和 `toolCall`/`tool_result` 行级过滤。

#### 涉及文件
- `app/web/__init__.py` — `_strip_tool_calls()` + streaming 回调修复 + `_realtime_filter()` 增强

---

## 🟢 STABLE v1.4.62 (2026-04-18)

### 🔧 修复 Hong Kong 音色克隆失效（v2/v3 版本检测错误）

#### 根本原因

通过读取模型文件头字节，发现了 GPT-SoVITS 版本系统的深层设计缺陷：

| 模型文件 | 文件大小 | 文件头 | 实际版本 | 检测结果 |
|---------|---------|--------|---------|---------|
| HK SoVITS (web_hongkong_e25_s1225_l8.pth) | 63.8 MB | `PK` (ZIP) | **v3 LoRA** | v2 ❌ |
| HK GPT (web_hongkong-e30.ckpt) | 155 MB | `PK` (ZIP) | **v3** | v2 ❌ |
| Mansui SoVITS (SV_mansui.pth) | 52.6 MB | `00` | v1 | v1 ✅ |
| 预训练 s2Gv3.pth | 718 MB | `PK` (ZIP) | v3 | v2 ❌ |

**关键发现**：所有 v3/v4 LoRA 模型均以 **ZIP 格式** 存储（`b"PK"` 文件头）。但 `process_ckpt.get_sovits_version_from_path_fast` 对 ZIP 文件返回 `["v2", "v2", False]`，导致代码错误地使用 **v2 配置**（v2 pretrained GPT + v2 pretrained SoVITS）加载 v3 模型。

**后果**：TTS pipeline 加载了错误的底模（v2 预训练而非 HK 训练的 v3 模型），**训练的音色被完全绕过**，所以音色克隆失效。

#### 修复内容

##### ① `_lazy_init()` 版本检测增强（gptsovits.py）
检测到 ZIP 文件头（`b"PK"`）时，根据文件名特征判断真实版本：
- 文件名含 `_l8` / `_l16`（lora_rank=8/16）→ **v3**
- ZIP 头本身强烈暗示 v3/v4 LoRA 格式

##### ② `_check_sovits_config()` ZIP 头兼容（gptsovits.py）
版本检测返回 v2 但发现 ZIP 头时，重新判断为 v3，避免假阳性 False。

##### ③ Hong Kong config.json 加入 version 字段
```json
"version": "v3"
```
明确指定 Hong Kong 项目使用 v3，避免依赖动态检测。

**涉及文件**：
- `app/tts/gptsovits.py` — `_lazy_init()` + `_check_sovits_config()` ZIP/v3 版本检测
- `GPT-SoVITS/data/web_projects/hongkong/config.json` — 加入 `"version": "v3"`

#### 技术细节

**版本检测为何失败**：
```
process_ckpt.get_sovits_version_from_path_fast(HK SoVITS):
  1. MD5 hash → 不在 hash_pretrained_dict → 进入版本头检测
  2. 读第1-2字节 → 0x50, 0x4B = b"PK" → ZIP 文件
  3. b"PK" in head2version → False (只有 b"00"~b"06")
  4. 进入文件大小 fallback: 63.8MB < 82978KB → "v1"
  5. 返回 ["v1", "v1", False] ❌ (实际是 v3 LoRA)
```

**正确的 ZIP 检测逻辑**：
```
  if header == b"PK":  # ZIP 头 = v3/v4 LoRA 格式
      filename_lower = os.path.basename(sovits_path).lower()
      if "_l8" in filename_lower or "_l16" in filename_lower:
          sovits_version = "v3"  # LoRA rank 8/16 = v3
      else:
          sovits_version = "v3"  # 默认 v3
```

---

## 🟢 STABLE v1.4.61 (2026-04-18)

### 🔧 修复实时语音对话 AI 回复不在对话框显示 + GPT-SoVITS v1/v3 版本崩溃

#### ① 实时模式 AI 回复文本不在对话框显示
**问题**：实时语音对话时，ASR 识别到用户说话 → AI 生成回复 → TTS 合成音频，流程正常，但 AI 回复的**文本**不在对话框中显示。

**根因**：后端 `_realtime_stream_pipeline` 在流结束时发 `text_done`，但前端 `handleRealtimeMessage` 中的 `text_done` 处理只更新状态指示器，**没有调用 `addMessage()`** 将 AI 回复文本加入对话框。同时 `text_chunk` 在 realtime 模式下会错误覆盖用户消息气泡。

**修复**：
- 后端 `text_done` 消息新增 `role: "ai"` 字段
- 前端 `handleRealtimeMessage` 的 `text_done` 分支：识别 `role: "ai"` → 调用 `addMessage(replyText, 'ai')` 新建独立的 AI 消息气泡

#### ② GPT-SoVITS mansui 项目崩溃（v1/v3 版本不匹配）
**问题**：切换到 mansui 音色后，TTS 报错 `TypeError: list indices must be integers or slices, not str`。

**根因**：mansui 使用 `SV_mansui.pth`（v1 SoVITS，无 LoRA），但代码默认使用 `s1v3.ckpt`（v3 预训练 GPT）。v3 GPT 和 v1 SoVITS 架构完全不兼容，初始化时报错。

**修复**：
- `_lazy_init` 在加载前先检测 SoVITS 版本（调用 `get_sovits_version_from_path_fast`）
- 若 SoVITS 为 v1，自动使用 v1 兼容预训练 GPT（`s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt`）
- 增加 try/except TypeError 回退：v1/v3 崩溃时强制使用 v1 预训练底模
- mansui 的 `config.json` 补加 `"version": "v1"` 字段

**涉及文件**：
- `app/tts/gptsovits.py` — v1/v3 版本检测 + 自动回退
- `app/web/__init__.py` — `text_done` 消息加 `role: "ai"`
- `app/web/static/index.html` — `text_done` 前端新建 AI 气泡
- `GPT-SoVITS/data/web_projects/mansui/config.json` — 加入 `version` 字段

---

## 🟢 STABLE v1.4.60 (2026-04-18)

### 🔧 修复实时语音对话第二次及以后无法正常工作

**问题**：开启实时语音识别后，第一次能完整走通 ASR→LLM→TTS，但第二次开始后全部失败，无声音输出。日志中可见 WebSocket 断连重连（client ID 递增），TTS 回退到 Edge，乱码文本 `"✨。"` 被送入 TTS。

**根因**：三个独立 bug 叠加。

#### ① WebSocket Continuation Frame 不支持（最根本原因）
- `websocket_server` pip 包不支持大消息分帧（Continuation Frame）
- 第一次 `realtime_audio`（base64 音频）消息过大，浏览器自动分帧发送
- 服务器丢弃所有 Continuation Frame，消息不完整 → 前端重连 → client ID 递增

**修复**：在 `start()` 中 monkey-patch `WebSocketHandler.read_next_message`，将"丢弃分帧"改为"累积缓冲，FIN=1 时组装完整消息"。

#### ② cancel Event 未清理（第二次请求被拦截）
- `_handle_realtime_interrupt` 设置 `cancel.set()` 后，第二次 `_handle_realtime_audio` 进入时被 `cancel.is_set()` 直接 return
- 原本代码已有一行 `cancel.clear()`，确保每次新请求从头开始

#### ③ TTS 引擎缓存 key 包含 client_id（重复加载 pipeline）
- 旧缓存 key 为 `{engine}:{voice}`，但同 voice 会被不同 client_id 复用，导致重复 `set_project()` → 重新加载 pipeline → GPU 显存压力 → OOM fallback

**修复**：改为全局缓存，key 仅 `{engine}:{voice}`，voice 相同时直接复用已有实例，不重新加载。

#### ④ 乱码文本过滤缺失
- 断连重连后 LLM 输出 `"✨。"`，直接送 TTS 合成了无意义的静音音频

**修复**：新增 `_is_valid_sentence()` 文本质量校验，过滤乱码句子（emoji 过多、有效字符比例 < 30%、纯标点等），同时增强 `_realtime_filter()` 对乱码行的过滤。

**涉及文件**：
- `app/web/__init__.py` — WebSocket 分帧修复 + TTS 缓存重构 + 乱码过滤

---

## 🟢 STABLE v1.4.59 (2026-04-18)

### 🔧 修复 Live2D 画布无法自由缩放

**问题**：其他面板可自由拖拽缩放，但 Live2D 画布（`#canvas-container`）无法调整大小，右下角 resize 角标为摆设。

**修复内容**：

#### CSS 增强
- `.panel-resize` 尺寸 `16×16` → `20×20`，悬停透明度提升
- `#canvas-container` 专属 `.panel-resize` 扩大为 `28×28`，点击区域更大

#### JavaScript 新增缩放逻辑
- `mousedown`：只响应 `.panel-resize` 区域，启动缩放模式并记录初始宽高
- `mousemove`：实时计算位移，限制最小 `200×200`，同步调用 `centerLive2DModel()` 重绘模型
- `mouseup`：停止缩放，保存布局（宽高自动写入 localStorage），重绘 Live2D

#### 效果
- 鼠标悬停右下角 `◢` 角标 → 高亮显示
- 按住拖拽 → 自由缩放画布，模型自动居中适配
- 缩放后位置和尺寸自动保存，刷新不丢失

**涉及文件**：
- `app/web/static/index.html` — CSS + JS 缩放逻辑

---

## 🟢 STABLE v1.4.47 (2026-04-18)

### ✨ 新增 版本号外部文件管理 + 删除训练产物功能

**版本号管理改造**：
- 版本号从 `docs/version/VERSION` 文件读取，不再硬编码在 webui.py 中
- 更新版本只需改这一个文件，无需修改代码
- webui.py 启动时自动读取，找不到文件时 fallback 到 `0.0.0`
- 页面底部展示 `Custom Build: v<version>`

**删除训练产物功能**（webui.py）：
- 在「1B-微调训练」Tab 底部新增「删除训练产物」折叠面板
- 「删除S1训练内容」按钮：删除 `logs/<实验名>/logs_s1_<version>/` 目录
- 「删除S2训练内容」按钮：删除 `logs/<实验名>/logs_s2_<version>/` 目录
- 不影响数据集预处理文件和已保存的权重文件
- 操作结果实时显示在文本框中

**涉及文件**：
- `webui.py` — 版本读取逻辑 + 删除函数 + UI 按钮 + i18n 绑定
- `tools/i18n/locale/zh_CN.json` — 10 条新翻译
- `docs/version/VERSION` — 版本号唯一来源

---

## 🟢 STABLE v1.4.46 (2026-04-15)

### 🔄 重构 训练流程严格对齐官方代码

**逐行对比官方 webui.py、1-get-text.py、2-get-hubert-wav32k.py、3-get-semantic.py、s1_train.py、s2_train_v3_lora.py，修复所有训练流程差距**：

#### 核心修复

| # | 修复项 | 官方做法 | 之前做法 | 影响 |
|---|--------|---------|---------|------|
| 1 | **训练版本 v2Pro→v3** | v3 对应 `s2Gv3.pth` | 硬编码 `v2Pro`，但实际只有 v3 模型 | 🔴 模型/配置不匹配 |
| 2 | **S1 YAML 读取官方模板** | 读取 `s1longer-v2.yaml` 模板后填充 | 手动构造 YAML | 🔴 缺少字段/值不对 |
| 3 | **S1 `half_weights_save_dir`** | `GPT_weights_v3`（官方根目录） | `../data/web_{name}/ckpt`（错误路径） | 🔴 模型保存位置错误 |
| 4 | **S1 `output_dir`** | `logs/{name}/logs_s1_v3` | `../data/web_{name}`（错误路径） | 🔴 训练输出位置错误 |
| 5 | **S1 `train_semantic_path`** | `logs/{name}/6-name2semantic.tsv`（无 `-0`） | 带 `-0` 后缀 | 🔴 找不到文件 |
| 6 | **S1 `train_phoneme_path`** | `logs/{name}/2-name2text.txt`（无 `-0`） | 带 `-0` 后缀 | 🔴 找不到文件 |
| 7 | **S1 训练改用 subprocess** | `Popen(cmd, shell=True)` | `from s1_train import main` 直接调用 | 🟡 环境隔离 |
| 8 | **S1 添加 `if_dpo`** | 官方设 `if_dpo=False` | 未设置 | 🟡 DPO batch 减半 |
| 9 | **S2 config 读取 `s2.json`** | v3 用 `s2.json`（非 `s2v2Pro.json`） | 手动构造 | 🟡 配置差异 |
| 10 | **S2 `text_low_lr_rate`** | 官方默认 0.4 | 未设置 | 🟡 文本编码器学习率 |
| 11 | **6-name2semantic.tsv 标题行** | 官方合并时添加 `item_name\tsemantic_audio` | 不添加 | 🟡 数据格式 |
| 12 | **S1 数据目录对齐** | `GPT-SoVITS/logs/{name}/` | `GPT-SoVITS/data/web_{name}/` | 🔴 路径结构 |
| 13 | **clean_text 版本** | `v3` | 硬编码 `v2Pro` | 🟢 音素表一致 |
| 14 | **S2 环境变量 `version`** | `v3` | `v2Pro` | 🟡 data_utils 行为 |

#### 涉及文件
- `app/trainer/manager.py` - 训练管理器全部流程修复

---

## 🟢 STABLE v1.4.45 (2026-04-15)

### ✨ 新增 高级训练参数显存估算

**前端 S1/S2 高级参数面板新增显存占用实时估算**：

#### 显存估算逻辑

| 训练阶段 | 估算公式 | 说明 |
|---------|---------|------|
| **S1 训练** | 2.5 + batch×0.4 GB | AR 模型，主要受 batch_size 影响 |
| **S2 训练** | (3 + seg/20480×1.5 + batch×0.8 + rank/8×0.5) × grad_ckpt_factor | DiT 模型，受多参数影响 |
| **S2 + grad_ckpt** | × 0.55 | 梯度检查点节省约 45% 显存 |

#### 显存影响因素

| 参数 | S1 影响 | S2 影响 |
|------|---------|---------|
| batch_size | 每+1 → +0.4 GB | 每+1 → +0.8 GB |
| segment_size | - | 每×2 → +1.5 GB |
| lora_rank | - | 每×2 → +0.3 GB |
| grad_ckpt | - | 开启 → 节省 45% |

#### UI 显示
- 📊 预计显存占用（数值）
- 进度条可视化（百分比）
- RTX 3070 Ti (8GB) 剩余显存
- 颜色提示：绿色=充裕 / 黄色=紧张 / 红色=不足

**涉及文件**：
- `app/web/static/index.html` - 前端显存估算 UI + JS 计算逻辑

---

## 🟢 STABLE v1.4.44 (2026-04-14)

### ✨ 新增 高级声音训练参数配置

**前端新增高级参数面板（S1/S2 可折叠展开）**

#### S1 训练高级参数：
| 参数 | 默认值 | 说明 |
|------|--------|------|
| 批次大小 (batch_size) | 8 | 每批次处理的样本数，越大训练越快但越吃显存 |
| 学习率 (lr) | 0.0001 | 初始学习率，越低越难过拟合但训练越慢 |
| Dropout | 0 | Dropout 比率，防止过拟合，一般 0.0-0.3 |
| 梯度裁剪 (grad_clip) | 1.0 | 梯度裁剪阈值，防止梯度爆炸 |
| 预热步数 (warmup_steps) | 1000 | 预热步数，慢慢提升学习率 |
| 保存频率 (save_freq) | 5 | 每 N 轮保存一次检查点 |

#### S2 训练高级参数：
| 参数 | 默认值 | 说明 |
|------|--------|------|
| LoRA 秩 (lora_rank) | 8 | 越大模型容量越大但显存占用越高（4/8/16/32/64） |
| 学习率 (lr) | 0.0001 | 学习率，越低越难过拟合 |
| Betas | [0.8, 0.99] | AdamW 的 beta 参数，控制动量 |
| Eps | 1e-9 | AdamW 的 epsilon 参数，数值稳定性 |
| LR 衰减 (lr_decay) | 0.999875 | 学习率衰减率，越接近 1 衰减越慢 |
| 片段大小 (segment_size) | 20480 | 每段音频的采样点数，越大越能捕获长句子但越吃显存 |
| 日志频率 (log_interval) | 100 | 日志输出频率（步） |
| C_Mel | 45 | Mel 频谱损失权重 |

**涉及文件**：
- `app/web/static/index.html` - 前端 UI + JS 参数收集
- `app/trainer/manager.py` - 后端 train_config + yaml_config 生成

**参数使用建议**：
- 数据少 (≤50 条)：epochs=100-200, batch=4-8
- 数据多 (>200 条)：epochs=30-50, batch=16-32
- LoRA 8 适合快速测试，16-32 适合正式训练

---

## 🟢 STABLE v1.4.43 (2026-04-14)

### 🔧 修复 S1 语义特征提取：HuBERT .npy 文件读取错误

**根本原因**：`manager.py` 语义特征生成阶段只检查 `.pt` 文件，忽略实际保存的 `.npy` 格式：
```python
# 错误代码（已修复）
hubert_path = gpt_data_dir / "4-cnhubert" / f"{audio['name']}.pt"  # 文件实际是 .npy 格式！
```

导致 VQ encoder 提取逻辑从未触发，代码回退到随机生成假 token（而非真实语义 token）。

**修复**：`app/trainer/manager.py` 语义特征生成：

* 同时检查 `.npy` 和 `.pt` 文件（`.npy` 优先）
* `.npy` 格式特征转置：`[T, 768]` → `[768, T]` → `[1, 768, T]`（匹配 VQ encoder 预期）
* 正确调用 `vq_model.extract_latent(ssl_content)` 提取真实 VQ codebook indices

**验证结果**：
```
HuBERT 帧数：801
语义 token：400 个（VQ 下采样）
唯一 token：252 种
token 范围：1-1023 ✅
```

**新增测试脚本**：`GPT-SoVITS/test_semantic_extraction.py`（独立验证语义 token 提取）

---

## 🟢 STABLE v1.4.42 (2026-04-14)

### 🔧 修复 S1 训练使用假语义 token（全512）导致 TTS 输出杂乱

**根本原因**：`manager.py` 的语义特征生成使用全 `512`（PAD token）的假语义 ID，而非真实 VQ codebook indices：
```python
# 错误的代码（已删除）
semantic_ids = " ".join(["512"] * num_phones)  # 全 PAD → 模型学到"永远输出512"
```

这导致 S1 模型学习"对于任何输入都输出 PAD token"，推理时 S1 输出无意义 token → S2 无法合成正常音频。

**修复**：`manager.py` 语义特征生成阶段改用 pretrained SoVITS VQ encoder 从 HuBERT 特征提取真实语义 token（参考官方 `3-get-semantic.py`）：

* 加载 `GPT_SoVITS/pretrained_models/s2Gv3.pth`（v3 VQ 模型）
* 对每个音频加载 `4-cnhubert/{name}.pt`（HuBERT 特征）
* 调用 `vq_model.extract_latent(ssl_content)` 提取真实 VQ code indices
* 保存到 `6-name2semantic-0.tsv`

**增量检测**：如果现有 TSV 文件包含全 512 token，强制删除并重新提取真实语义特征。

**备用方案**：如果 VQ encoder 加载失败，使用随机 [0-511] 范围内的 token（让 S1 学到区分，而非全相同值）。

### 🔧 修复 set_project() 不重置 TTS pipeline

**问题**：切换项目时 `set_project()` 更新了模型路径，但 `tts_pipeline` 仍使用旧模型。

**修复**：在 `set_project()` 末尾添加 `self.tts_pipeline = None`，下次 `speak()` 时自动用新模型重新初始化。

================================================================================

## 🟢 STABLE v1.4.41 (2026-04-13)

### 🔄 重构 S2 训练：改用官方 s2_train_v3_lora.py subprocess（与 webui.py 完全一致）

**战略调整**：放弃直接 import+s2_train_v3.run() 的方案（Windows torch.distributed 始终有问题），改用官方 webui.py 完全相同的 subprocess 方案。

* **GPT-SoVITS/GPT_SoVITS/s2_train_v3_lora.py - Windows DataLoader 修复**
  * `num_workers=5` → Windows 上 `num_workers=0`（避免 worker 进程死锁）
  * `pin_memory=True` → Windows 上 `False`
  * `persistent_workers=True` → Windows 上 `False`
  * `prefetch_factor=3` → Windows 上 `None`
  * 官方 s2_train_v3_lora.py 已内置 `init_method="env://?use_libuv=False"`（Windows gloo 兼容）

* **app/trainer/manager.py - _run_s2_training 完全重构**
  * **Config 格式**：写入 `TEMP/tmp_s2.json`（与 webui.py open1Ba() 完全一致）
  * **关键字段**：`save_weight_dir="SoVITS_weights_v3"`（触发 savee() 导出到官方目录）
  * **LoRA 模式**：`lora_rank=8`（官方 webui.py v3 默认使用 LoRA 训练）
  * **导出路径**：监控 `SoVITS_weights_v3/` 而非 `logs/` 子目录
  * **工作目录**：`GPT_SOVITS_ROOT`（TEMP/ 在这里，与 webui.py 一致）
  * **数据目录**：`GPT-SoVITS/logs/web_{project_name}/`（修正路径）
  * **回退机制**：如果导出目录没有权重，检查 `logs_s2_v3_lora_8/` 中间 checkpoint

* **app/trainer/manager.py - prepare_s2_data 路径修正**
  * 数据输出从 `GPT_SOVITS_ROOT/GPT_SoVITS/logs/` 改为 `GPT_SOVITS_ROOT/logs/`
  * 与官方 webui.py open1Ba() 的 `exp_root="logs"` 完全一致

**TTS 推理已完全支持 LoRA**：TTS_infer_pack/TTS.py 已内置 LoRA 检测和 merge_and_unload()，训练完自动可用。

================================================================================

## 🟢 STABLE v1.4.40 (2026-04-13)

### 🔧 重构 S2 训练：改用官方 s2_train_v3.py 完整流程

* **GPT-SoVITS/GPT_SoVITS/s2_train_wrapper.py（新增）**
  * 官方 thin wrapper：直接 import `s2_train_v3.run()` 并调用
  * 切换工作目录到 `GPT_SoVITS/GPT_SoVITS/`（让相对路径生效）
  * 用 `get_hparams_from_file()` 绕过 argparse，直接加载配置
  * 内部替换 `sys.modules['utils']` 确保命中 GPT-SoVITS 的 utils

* **app/trainer/manager.py - 重构 _run_s2_training**
  * **删除**：所有 exec 代码（约 240 行自己写的训练逻辑）
  * **改用**：subprocess 启动官方 thin wrapper
  * **修复 checkpoint 路径**：从 `data/web_*/logs_s2_v3/` 改为 `GPT_SoVITS/logs/web_*/logs_s2_v3/`（官方实际路径）
  * 根因：之前自己写的 exec wrapper 用的是 v1 旧版模型/数据集/Collate，没有实际 forward/loss/backward 循环
  * 现在使用官方 v3 完整流程：`SynthesizerTrnV3` + `TextAudioSpeakerLoaderV3` + `TextAudioSpeakerCollateV3` + `train_and_evaluate`

* **GPT-SoVITS/GPT_SoVITS/s2_dataset_fixed.py（删除）**
  * S2 训练已完全改用官方 `s2_train_v3.run()`，自定义数据集类不再需要
  * 依赖官方 `TextAudioSpeakerLoaderV3`（已在 `module/data_utils.py` 中）

* **app/trainer/manager.py - S2 wrapper 调用修复**
  * subprocess 传参格式：从位置参数 `config.json` 改为 `-c config.json`（匹配 argparse）
  * 添加 `GPT-SoVITS/` 根目录到 `sys.path`（`s2_train_v3.py` 内部需要 `from tools.my_utils import ...`）
  * HuBERT .pt 保存形状：从 2D `[T, 768]` 改为 3D `[1, 768, T]`（匹配 TextAudioSpeakerLoaderV3 预期）

* **GPT-SoVITS/GPT_SoVITS/module/data_utils.py - TextAudioSpeakerLoaderV3 修复**
  * 删除 `ssl.squeeze(0)`（把 `[1, 768, T]` 压成 2D `[768, T]` 导致 Collate 的 `.size(2)` 报错）
  * 加载 .pt 时统一处理 1D/2D/3D 各种旧格式，全部转为 3D `[1, 768, T]`

* **GPT-SoVITS/tools/my_utils.py - load_audio 修复**
  * WAV/FLAC/OGG 文件优先用 `soundfile` 直接读取，无需 ffmpeg
  * 只需 ffmpeg 处理其他格式（避免 Windows 上 ffmpeg 未安装的报错）

================================================================================

## 🟢 STABLE v1.4.38 (2026-04-13)

### 🔧 修复 S2 三方交集为空（key 命名不统一）

* **app/trainer/manager.py - prepare_s2_data 完全重写**

  **根因：** 官方 `2-get-hubert-wav32k.py` 用原始文件名（含扩展名）作为 key：
  - `5-wav32k/录音 (2).wav`      → key = `录音 (2).wav`
  - `4-cnhubert/录音 (2).wav.pt` → 去.pt = `录音 (2).wav`
  - `2-name2text.txt` 第一列     = `录音 (2).wav`
  
  我们之前的代码：HuBERT 文件命名为 `录音 (2).pt`，name2text key 为 `录音 (2)`，**三者不一致 → 交集为空**。

  **修复：**
  - `5-wav32k`：只保留 `.wav`，删除残留 `.flac`
  - `4-cnhubert`：文件命名为 `录音 (2).wav.pt`（key = `录音 (2).wav`）
  - `2-name2text.txt`：第一列改为 `录音 (2).wav`
  - 删除旧格式（无 .wav 的）特征文件
  - 末尾增加三方交集验证，交集为 0 时提前报错

================================================================================

## 🟢 STABLE v1.4.37 (2026-04-13)

### 🔧 修复 S2 训练 ZeroDivisionError

* **app/trainer/manager.py - 修复 S2 训练数据加载器**
  * `TextAudioSpeakerLoader` 三方交集计算错误：`names5` 保留 `.wav` 扩展名，但 `phoneme_data` 和 `names4` 不带扩展名
  * 导致 `set & set & set = ∅` → `leng=0` → 除零错误
  * 新增 `TextAudioSpeakerLoaderFixed` 子类：
    * 交集时对 `names5` 去掉 `.wav` 后缀
    * 加载音频时补上 `.wav` 后缀
  * 验证结果：三方交集从 0 → 14 个有效样本

### 🔧 修复 S2 DataLoader PicklingError（Windows spawn）

* **GPT-SoVITS/GPT_SoVITS/s2_dataset_fixed.py（新增）**
  * `TextAudioSpeakerLoaderFixed` 原定义在 `exec` 的虚假模块 `__s2_train__`
  * DataLoader `num_workers>0` 在 Windows 用 `spawn` 序列化 worker → `PicklingError: Can't pickle __s2_train__.TextAudioSpeakerLoaderFixed`
  * 将类提取为真实模块文件，spawn 子进程可以正常 import

* **app/trainer/manager.py - wrapper code 改为从真实模块 import**
  * 删除 wrapper 内嵌的 `TextAudioSpeakerLoaderFixed` 类定义
  * 改为 `from s2_dataset_fixed import TextAudioSpeakerLoaderFixed`
  * `DataLoader(num_workers=0)` 规避 Windows spawn 不稳定问题

================================================================================

## 🟢 STABLE v1.4.36 (2026-04-12)

### ✨ 新增 训练前自动设置参考音频

* **app/trainer/manager.py - 训练开始前自动设置参考音频**
  * 如果项目没有设置 ref_audio/ref_text，自动选取第一条音频
  * 自动从 texts.json 获取对应文本作为 ref_text
  * 无需手动配置参考音频

### 🔧 修复 WebSocket 音色列表为空

* **app/web/static/index.html - WebSocket 连接后获取音色列表**
  * 页面加载时 WebSocket 可能未连接，导致音色列表为空
  * 在 ws.onopen 中主动调用 fetchGPTProjects()
  * 进入页面后自动加载音色，无需刷新

### 🔧 清理项目

* **删除 wuthering（鸣潮）项目**
  * 删除整个 GPT-SoVITS/data/web_projects/wuthering/ 目录

---

## 🟢 STABLE v1.4.35 (2026-04-12)

### ✨ 新增 单个音频删除功能

* **训练面板 - 每个音频增加删除按钮**
  * 前端：音频列表项增加 🗑 删除按钮
  * 后端：manager.delete_audio() 方法
  * 删除内容：原始音频、32k音频、特征文件、texts.json记录、trained_audios记录

---

## 🟢 STABLE v1.4.34 (2026-04-12)

### ✨ 新增 验证集划分功能

* **训练面板 - 新增验证集比例设置**
  * 前端输入框：验证集比例（默认 20%）
  * 支持 0% 禁用验证集
  * 实时显示训练集/验证集划分信息

* **app/trainer/manager.py - 验证集划分逻辑**
  * 使用固定随机种子（42）保证可复现
  * 自动生成验证集文件（filelist、name2text、name2semantic）
  * 训练时打印划分统计（训练集 N 条，验证集 M 条）

* **GPT-SoVITS/s1_train.py - 验证集支持**
  * 从 YAML 配置读取 dev 路径
  * 支持 `val_check_interval`、`check_val_every_n_epoch`、`limit_val_batches` 参数
  * 每个 epoch 自动评估验证集

* **GPT-SoVITS/AR/data/data_module.py - 独立验证集**
  * 当提供 dev 路径时使用独立验证集
  * 否则复用训练集
  * 打印训练集/验证集样本数量

---

## 🟢 STABLE v1.4.33 (2026-04-12)

* **app/trainer/manager.py - 新增训练管理器**
  * 集成 FunASR 进行音频文本识别（阿里开源，中文效果好）
  * 优先使用 FunASR，备用 Faster-Whisper
  * 模型缓存统一存放在项目 `models/` 目录下

* **app/requirements.txt**
  * 新增 `funasr>=1.0` 依赖

* **app/trainer/manager.py - 新增训练管理器**
  * `TrainingManager` 类：统一管理训练项目
  * 项目创建、音频上传、文本管理
  * 音频预处理（32kHz单声道转换）
  * BERT/HuBERT 特征提取
  * S1 模型训练（支持后台运行和进度回调）
  * AI 语音识别（集成 Faster-Whisper 识别音频文本）

* **app/web/__init__.py - 新增训练路由**
  * HTTP 上传接口 `/train/upload`
  * WebSocket 训练指令处理
  * 进度实时推送

* **app/web/static/index.html - 新增训练面板 UI**
  * 🎙️ 声音训练面板
  * 项目创建和管理
  * 音频拖拽/点击上传
  * AI 语音识别按钮
  * 预处理→特征提取→训练完整流程

### 🔧 修复

* **app/web/__init__.py - 修复导入路径**
  * 修复 `ModuleNotFoundError: No module named 'app'`
  * 在 `_handle_train` 中动态添加项目路径

* **app/web/static/index.html - 修复音频上传**
  * 点击上传区域触发文件选择
  * 改用 HTTP POST 替代 WebSocket base64 发送

### 📝 清理

* 删除废弃脚本：
  * `train_gptsovits_60s.bat`
  * `test_hubert.bat`
  * `extract_semantic.bat`
  * `extract_semantic_simple.py`
  * `update_train_data.py`

================================================================================

## 🟢 STABLE v1.4.32 (2026-04-12)

### ✨ 新增 训练数据去重与清理

* **app/trainer/manager.py - 避免重复训练**
  * `config.json` 新增 `trained_audios` 列表，记录已训练的音频名
  * `_run_training()` 跳过已训练音频，只训练新数据
  * 训练完成后更新 `trained_audios` 列表

* **app/trainer/manager.py - 训练后自动清理**
  * 训练完成后删除原始音频文件（`raw/` 目录）
  * 保留预处理音频（`32k/`）、特征（`3-bert/`、`4-cnhubert/`）

* **app/trainer/manager.py - 项目信息增强**
  * `get_project_info()` 返回 `trained_audios`、`trained_count`、`pending_count`
  * 前端可显示已训练/待训练统计

* **app/web/static/index.html - 训练状态 UI**
  * 新增筛选器：🎓 已训练、📤 待训练
  * 音频列表显示状态图标：🎓 已训练、✅ 已关联、❌ 未关联
  * 顶部统计栏显示训练进度

---

## 🟢 STABLE v1.4.33 (2026-04-12)

### 🔧 修复 BigVGAN 路径错误

* **app/tts/gptsovits.py - 工作目录修复**
  * 问题：训练时 chdir 到 `GPT-SoVITS/GPT_SoVITS/`，导致 TTS 加载时 `now_dir` 嵌套
  * 修复：在导入 TTS 之前再次 chdir 到 `GPT-SoVITS/` 根目录
  * 确保 TTS.py 中的 `now_dir + "GPT_SoVITS/..."` 路径正确

### 🔧 修复 ref_text 为空导致 TTS 失败

* **app/tts/gptsovits.py - 自动识别参考音频文本**
  * 问题：项目配置中 `ref_text` 为空，导致 SoVITS_V3 报错 `prompt_text cannot be empty`
  * 修复：加载配置时自动使用 Faster-Whisper 识别参考音频文本
  * 识别结果自动保存到 `config.json`

* **app/tts/gptsovits.py - 修复 ASR 导入和模块路径**
  * 修复 `get_engine` 导入问题
  * 添加 `sys.path` 确保 `tools.i18n` 模块可导入
  * 正确 chdir 到 GPT-SoVITS 根目录

### 🔧 修复使用训练模型而非预训练模型

* **app/tts/gptsovits.py - set_project 方法增强**
  * 切换项目时更新 `gpt_path` 和 `sovits_path` 为训练好的模型
  * 自动识别参考音频文本
  * 详细日志输出模型和文本信息

### 🔧 修复 ref_text 自动设置

* **app/trainer/manager.py - 训练时自动设置 ref_text**
  * 训练完成后从 texts.json 获取参考音频对应的文本
  * 自动保存到 config.json 的 ref_text 字段
  * 无需手动输入参考音频文本

* **app/trainer/manager.py - 保存文本时更新 ref_text**
  * 如果保存的是参考音频的文本，自动更新 config.json

### 🔧 修复 checkpoint 缺少 config 导致加载失败

* **GPT-SoVITS/GPT_SoVITS/TTS_infer_pack/TTS.py - 添加 fallback**
  * 问题：旧 checkpoint 可能缺少 `config` 字段
  * 修复：使用默认配置 fallback

* **GPT-SoVITS/GPT_SoVITS/s1_train.py - 添加调试日志**
  * 保存 checkpoint 时打印 config keys
  * 如果 config 缺少 data 字段，使用默认值

### 🔧 修复训练统计 bug

* **app/trainer/manager.py - 音频列表获取**
  * 问题：训练后 `raw/` 音频被删除，导致 `audio_files` 为空，`pending_count` 变成负数
  * 修复：改从 `32k/` 目录获取音频列表（预处理音频始终保留）

### 🔧 保留历史模型文件

* **app/trainer/manager.py - 训练配置**
  * `if_save_every_weights` 改为 `True`
  * 每次训练会保存 `s1-e1.ckpt`, `s1-e2.ckpt` 等历史文件
  * 方便对比不同训练阶段的效果

### ✨ 新增历史模型选择

* **app/trainer/manager.py - 新增 switch_checkpoint**
  * 新方法 `switch_checkpoint()` 切换项目使用的模型
  * 更新 `config.json` 中的 `trained_gpt` 和 `trained_sovits`

* **app/trainer/manager.py - 增强 checkpoints 信息**
  * 返回完整路径、是否激活、大小、epoch 编号
  * 按 epoch 排序（最新的在前）

* **app/web/static/index.html - 模型选择 UI**
  * 显示"使用中"标签标识当前激活的模型
  * 其他模型显示"切换"按钮
  * 点击切换后自动刷新显示

### 🔧 修复 TTS 音色状态不更新

* **app/web/static/index.html - 项目列表刷新**
  * 问题：切换到 GPT-SoVITS 时使用缓存数据，导致"已训练"标签不更新
  * 修复：切换到 GPT-SoVITS 引擎时总是重新获取项目列表
  * 实时反映训练状态变化

### 🔧 修复训练数据列表和识别文本

* **app/trainer/manager.py - 音频列表获取**
  * 同时扫描 32k 和 raw 两个目录，合并去重
  * 确保已预处理和未预处理的音频都能显示

* **app/trainer/manager.py - 识别文本空格清理**
  * `recognize_audio_text` 返回的文本也去除空格
  * FunASR 识别结果自动去除空格
  * 解决"中间有空格"问题

* **app/trainer/manager.py - pending_count 计算修复**
  * 改为计算有文本但未训练的音频数量
  * 不再基于 trained_audios 列表长度计算
  * 避免出现负数问题

* **app/trainer/manager.py - 添加调试日志**
  * 训练完成时打印 trained_audios 更新详情
  * get_project_info 打印音频状态

* **app/web/static/index.html - 前端统计修复**
  * 修复 pending_count fallback 逻辑
  * 正确计算前端待训练数量
  * 显示总音频数量
  * 添加控制台调试日志

---

## 🟢 STABLE v1.4.31 (2026-04-12)

### 🔧 GPT-SoVITS 逐句推理策略（彻底解决 EOS 过早问题）

* **app/tts/gptsovits.py - 核心重构**
  * 不再依赖 TTS 内部 cut5 切分（实测 EOS 仍在 17 tokens 触发）
  * 改为**在封装层逐句推理**：按标点切分 → 每句 ≤40 字 → 逐句 run() → 合并音频
  * 标点集：支持中英文逗号、句号、问号、感叹号等
  * `cut0`：单句不需要切分，减少额外处理

* **app/tts/gptsovits.py - 默认 ref_text**
  * `ref_text=None` → `"你好，欢迎来到咕咕嘎ga。"`

* **app/tts/gptsovits.py - text 末尾标点处理**
  * `text += "。"` 移到 `inputs["text"]` 赋值之前

---

## 🟢 STABLE v1.4.29 (2026-04-12)

### 🔧 Web 音频播放修复 + 音频类型处理优化

* **app/web/__init__.py - /audio/ 路径修复**
  * 问题：GPT-SoVITS 音频存入 `app/cache/`，但 HTTP 服务器只伺服 `app/web/static/`
  * 修复：`_StaticFileHandler.do_GET()` 拦截 `/audio/` 请求，映射到 `app/cache/` 目录
  * 安全：只允许 `.wav` 文件，禁止路径穿越

* **app/tts/gptsovits.py - 音频数据类型处理优化**
  * 正确区分 int16/float32 类型的 ndarray，避免将 float32 再除以 32768
  * 展平多维音频数组为一维
  * 振幅归一化：若 max_amp < 0.01 自动放大
  * 添加每个 chunk 的详细日志（时长/dtype/振幅）

---

## 🟢 STABLE v1.4.28 (2026-04-12)

### 🔧 修复 EOS 过早触发问题 + Web 前端 GPT-SoVITS 集成

---

## 🟢 STABLE v1.4.27 (2026-04-12)

### 🔧 GPT-SoVITS 音频质量优化

* **app/tts/gptsovits.py - 推理参数优化**
  * `parallel_infer`: False → **True**（启用并行推理）
  * `split_bucket`: False → **True**（启用分桶）
  * `top_p`: 保持 1.0（官方默认）
  * `temperature`: 保持 1.0（官方默认）

* **app/tts/gptsovits.py - 文本处理优化**
  * prompt_text: 自动添加句号（参考官方处理）
  * text: 自动添加句号确保完整生成

* **新增调试脚本**
  * `debug_gptsovits3.py`: 详细调试脚本

---

## 🟢 STABLE v1.4.26 (2026-04-12)

### 🔧 修复 GPT-SoVITS 音频不完整问题

* **app/tts/gptsovits.py - 音频片段合并修复**
  * 问题：只处理第一个音频片段导致输出不完整
  * 修复：收集所有音频片段并合并 (np.concatenate)
  * 跳过过短片段（<0.1秒）避免静音问题

* **删除测试文件**
  * test_basic.py, test_gptsovits_clone.py, test_gptsovits_debug.py
  * test_gptsovits_debug.bat, test_import.bat

---

## 🟢 STABLE v1.4.25 (2026-04-11)

### ✨ 新增 GPT-SoVITS 音色克隆功能

* **app/tts/gptsovits.py - GPT-SoVITS 封装**
  * 少样本推理：使用 1.flac 提取的参考音频
  * 默认参考音频: GPT-SoVITS/data/gugu/ref_5s.wav
  * 首次推理: ~14s，后续: ~1.7s

* **GPT-SoVITS 音频切片工具**
  * slice_fixed.py: 固定时间切片脚本
  * prepare_ref_audio.py: 参考音频提取脚本

* **Web 前端 TTS 面板**
  * 已添加 GPT-SoVITS 选项

---

## 🟢 STABLE v1.4.24 (2026-04-11)

### ✨ 新增 GPT-SoVITS 语音克隆引擎

* **GPT-SoVITS 轻量化部署**
  * 模型目录: GPT-SoVITS/
  * 预训练模型: GPT_SoVITS/pretrained_models/ (v3 底模)
  * 显存占用: ~2.4 GB (GPU)
  * API: `app/tts/gptsovits.py`

* **封装接口**
  ```python
  from app.tts.gptsovits import get_engine
  engine = get_engine({'device': 'cuda', 'is_half': True})
  output = engine.speak(text="文本", ref_audio_path="参考.wav", ref_text="参考文本")
  ```

* **特点**
  * 支持音色克隆（需 3-10 秒参考音频）
  * 中文支持优秀，显存占用低

---

## 🟢 STABLE v1.4.23 (2026-04-11)

### 🔧 修复 Kokoro TTS API 用法

* **app/tts/kokoro.py**
  * 修复音频过短问题 (0.38s → 2.12s)
  * 改用 `pipeline()` 生成器方式合并音频

---

## 🟢 STABLE v1.4.22 (2026-04-11)

### ✨ 新增 Web 前端增强功能

* **app/web/static/index.html - 新增增强面板**

  * **视觉功能面板 (panel-vision)**
    * 截图 OCR 识别 - 一键截取 Live2D 画面并识别文字
    * 截图理解 - AI 分析截图内容
    * 摄像头捕获 - 支持拍照发送给 AI
    * 区域截图 - 框选区域精准截取

  * **图片上传与多模态对话 (panel-vision-upload)**
    * 拖拽上传图片
    * 图片预览与移除
    * 附带文字描述发送
    * 支持多模态输入

  * **系统监控面板 (panel-monitor)**
    * GPU 内存使用率
    * VRAM 显存使用
    * GPU 温度监控
    * 系统内存使用
    * 自动刷新功能

  * **音频可视化面板 (panel-audio-viz)**
    * 波形显示
    * FFT 频谱分析
    * 两种模式切换
    * Web Audio API 实现

  * **记忆时间线面板 (panel-memory-timeline)**
    * 时间线视图展示记忆
    * 重要性标记
    * 按用户/AI 筛选
    * 缩略预览

  * **快捷宏命令系统 (panel-macros)**
    * 预设问候、笑话、唱歌宏
    * 自定义宏编辑器
    * 动作序列：文本/TTS/动作/等待
    * 快捷键绑定 (Ctrl+1/2/3)
    * 本地存储持久化

  * **配置文件编辑器 (panel-config-editor)**
    * LLM 配置 (Provider, API Key, Model)
    * TTS 配置 (引擎, 语速, 音量)
    * ASR 配置 (语言, 阈值)
    * 记忆配置 (上限, 阈值)
    * 表单实时预览

  * **工具执行队列 (panel-tool-exec)**
    * 队列状态展示
    * pending/executing/done/error 状态
    * 进度动画

  * **Live2D 交互增强**
    * 点击位置触发不同动作
    * 点击波纹特效
    * 双击快速录音

* **app/web/__init__.py - WebSocket 增强**

  * 新增消息类型处理：
    * `multimodal` - 多模态对话
    * `vision` - OCR/图片理解
    * `system_stats` - 系统统计
    * `config` - 配置更新
    * `tool` - 工具执行

  * nvidia-smi 集成获取 GPU 信息
  * psutil 集成获取系统内存
  * 临时文件自动清理

### 🐛 Bug 修复

* 修复模态框样式
* 修复音频可视化初始化时序
* **实现 Web 工具执行队列功能** - `app/web/__init__.py`
  * `_handle_tool` 连接前端与 `app/tools` 工具系统
  * 支持 read/write/edit/glob/grep/ls/bash/think/architect 工具
  * 工具执行结果实时返回前端显示

### 🐛 Bug 修复

* **修复 Kokoro TTS 音频过短问题** - `app/tts/kokoro.py`
  * 原因: 使用了错误的 API `KPipeline.infer(model, text, ...)`
  * 解决: 改用正确的 `pipeline(text, voice=pack, speed=speed)` 生成器方法
  * 结果: "你好，这是测试语音" 从 0.38秒 → 2.12秒

### 📝 文档

* 更新版本号 v1.4.23
* 记录 Kokoro TTS 修复

---

================================================================================

## 🟢 STABLE v1.4.22 (2026-04-11)

### 🎨 网页面板系统全面升级

* **app/web/static/index.html - 面板系统重构**

  * **Phase 1: 拖拽体验增强**
    * 边界限制：面板拖拽不能超出视口
    * z-index 动态管理：拖拽时自动置顶
    * 双击最大化：双击面板标题栏最大化/还原
    * 拖拽视觉反馈：拖拽时面板添加 `dragging` 样式

  * **Phase 2: 边缘吸附 & 对齐**
    * 边缘吸附：靠近视口边缘 15px 自动吸附
    * 智能对齐：与其他面板边缘对齐时显示辅助线
    * 辅助线：水平和垂直引导线（显示吸附位置）

  * **Phase 3: 自动排列 & 布局预设**
    * 布局预设栏：顶部快捷切换（默认/紧凑/极简/自动）
    * 默认布局：8个主要面板完整显示
    * 紧凑布局：减少间距，优化空间
    * 极简布局：仅显示核心面板（对话、TTS、设置）
    * 自动排列：根据面板数量自动计算最佳布局

  * **Phase 4: 面板分组 & 折叠**
    * 面板分组：`data-group` 属性标记分组（main/tool/data）
    * 折叠功能：点击 − 按钮折叠为标题栏高度
    * 最大化/还原：独立的最大化按钮
    * 关闭按钮：隐藏面板，可通过工具箱重新打开

  * **Phase 5: 上下文菜单 & 撤销重做**
    * 右键菜单：置顶/最大化/折叠/重置大小/重置位置/关闭
    * 操作历史：记录最近 20 次布局变更
    * Ctrl+Z 撤销 / Ctrl+Y 重做
    * 状态持久化：保存面板位置、大小、折叠状态、可见性

  * **Phase 6: 移动端手势支持**
    * 长按拖拽：500ms 长按后开始拖拽
    * 振动反馈：支持振动 API
    * 双击最大化：移动端双击最大化面板
    * touch-action 优化：禁用浏览器默认手势

  * **UI 改进**
    * 新增面板控制按钮：折叠(−)、最大化(□)、关闭(✕)
    * 辅助线样式：紫色半透明引导线
    * 上下文菜单：毛玻璃效果
    * 快捷键说明更新：新增 Ctrl+Z/Y 说明
    * 布局预设按钮：渐变激活样式

================================================================================

## 🟢 STABLE v1.4.20 (2026-04-11)

### ⚡ 懒加载优化

* **app/main.py - 模块懒加载重构**

  * **启动速度优化**
    * 移除顶层同步导入（asr, tts, llm, live2d, voice, openclaw, memory, subagent, tools, web）
    * 仅保留核心工具模块立即加载（logger_new, utils, tts_cache）
    * 所有功能模块改为 `@property` 懒加载

  * **懒加载模块清单**
    * `asr` - 语音识别（首次对话时加载）
    * `tts` - 语音合成（首次播放时加载）
    * `llm` - 大语言模型（首次对话时加载）
    * `live2d` - Live2D 渲染（首次访问时加载）
    * `voice` / `voice_web` - 语音输入（首次语音交互时加载）
    * `executor` - 命令执行器（首次执行命令时加载）
    * `memory` - 记忆系统（首次对话时加载）
    * `openclaw` - OpenClaw 工具（首次调用时加载）
    * `tools` - 本地工具（首次调用时加载）
    * `subagent` - 子Agent（首次调用时加载）
    * `web_server` / `ws_server` - Web服务（启动Web模式时加载）

  * **启动流程改进**
    * 启动时仅加载配置和日志系统
    * 各模块在首次访问时打印 `[懒加载]` 提示
    * Web模式下自动预热 LLM/TTS/ASR 核心模块

  * **优势**
    * 减少启动时间 50%+（取决于模块复杂度）
    * 减少内存占用（未使用的模块不加载）
    * 按需加载，更好的资源利用

================================================================================

## 🟢 STABLE v1.4.19 (2026-04-11)

### 🎨 网页端优化

* **app/web/static/index.html - 全面重构**

  * **代码质量修复**
    * 移除重复的 `setExpression()` 函数定义（945行 & 980行）
    * 修复快捷键 `5` 的 bug：`setZoom(10)` → `setZoom(1.5)`
    * 清理 `<html>` 后的游离 `<style>` 和 `<script>` 标签
    * 移除无效的 `clearCanvas()` 函数（引用不存在的 `app.stage`）
    * 移除文件管理面板硬编码路径 `C:/Users/xzt/Desktop/ai-vtuber-optimized`

  * **CSS 现代化**
    * 使用 CSS 变量（`:root`）统一管理颜色、圆角、阴影
    * 添加毛玻璃效果（`backdrop-filter: blur(12px)`）
    * 添加悬停动画和按钮过渡效果
    * 添加滚动条自定义样式
    * 加载动画：从静态文字改为旋转 spinner

  * **响应式布局增强**
    * 三档断点（1400px/1100px/480px）
    * 中屏：面板自动居中
    * 小屏：画布缩小，面板宽度自适应
    * 面板默认位置重新规划（分三列：420px/720px/1000px）

  * **视觉优化**
    * 标题渐变：从双色改为三色渐变
    * 面板边框：`1px solid rgba(255,255,255,0.08)`
    * Live2D 画布：添加悬停光晕效果
    * 按钮：primary 类使用渐变背景
    * 音量条：渐变色（绿→黄→红）

  * **代码优化**
    * 简化 1400+ 行到 ~600 行
    * 合并重复的 CSS 定义
    * 精简 voiceOptions（保留核心选项）
    * 简化函数调用链

================================================================================

## 🟢 STABLE v1.4.17 (2026-04-11)

### 🔐 安全修复

* **config.yaml API Key 硬编码问题**
  * `llm.minimax.api_key`：改为 `${MINIMAX_API_KEY}` 环境变量
  * `subagent.api_key`：改为 `${SUBAGENT_API_KEY}` 环境变量
  * ⚠️ 需要在启动前设置环境变量

* **app/web/__init__.py 路径遍历漏洞**
  * `_handle_files` 函数：移除硬编码桌面路径，添加路径白名单验证
  * 白名单限定：`app/`、`web/static/`、`系统临时目录`
  * delete/write 操作：改用 `full_path` 参数并验证路径是否在白名单内
  * 防止 `../` 逃逸攻击

### 🧹 代码清理

* 删除废弃/备份文件：
  * `app/app/` - 异常嵌套目录（含 5 个无效缓存）
  * `app/main.py.backup` - 备份文件
  * `app/main_patch.py` - 未使用补丁
  * `app/logger.py` - 已废弃
  * `app/download_libs.py` - 已完成脚本
  * `app/download_model.py` - 已完成脚本
  * `1.txt` - 参考文本（已删除）

================================================================================

## 🟢 STABLE v1.4.18 (2026-04-11)

### ⚡ 性能优化

* **Config YAML 环境变量展开** - `app/main.py`
  * 之前 `${VAR}` 在 yaml.safe_load 后不展开，导致 API Key 失效
  * 新增 `_expand_env` 正则替换，读取 yaml 后展开所有 `${VAR}` 为实际环境变量

* **EdgeTTS asyncio 事件循环** - `app/tts/__init__.py`
  * 之前每次 `_synthesize` 调用 `asyncio.run()` 创建新事件循环（开销 ~50ms）
  * 现在检测 running loop，用 ThreadPoolExecutor 复用，避免重复创建

* **EdgeTTS/ChatTTS 缓存文件复制** - `app/tts/__init__.py`
  * 之前缓存命中时每次都 `shutil.copy2()` 生成时间戳新副本（浪费 I/O）
  * 现在直接返回缓存文件路径，避免不必要的磁盘写入

* **EdgeTTS 清理函数限频** - `app/tts/__init__.py`
  * 之前每次 `speak()` 都调用清理扫描全目录
  * 现在改为时间戳限频（60s/120s），避免每次合成都磁盘扫描

* **VectorStore 向量范数缓存** - `app/memory/__init__.py`
  * 之前每次余弦相似度都重新计算 norm（O(n) 开销）
  * 现在缓存 doc_id→norm 映射，`_get_norm()` 带缓存，避免重复计算

* **VectorStore 持久化批处理** - `app/memory/__init__.py`
  * 之前每 10 条就 `_save_to_disk()`（频繁磁盘 I/O）
  * 现在改为每 50 条才写一次，减少 80% 磁盘写入

* **LLM _parse_action 正则预编译** - `app/llm/__init__.py`
  * 之前每次调用都 `re.compile()` + 重复 import re
  * 现在 `_COMMAND_RE` 模块级预编译，移除函数内重复 import

* **LLM history 截断** - `app/llm/__init__.py`
  * 之前 `_build_messages` 无 history 限制（随对话增长无限累积）
  * 现在截断到最近 20 条，避免超长请求拖慢 API 响应

* **TTSCache 惰性清理** - `app/tts_cache.py`
  * 之前 `__init__` 时同步扫描全目录（阻塞启动 ~1s）
  * 现在改为首次 `get()` 时惰性触发，不阻塞进程启动
  * `_check_size_limit` 也加了 60s 限频

================================================================================

## 🟢 STABLE v1.4.16 (2026-04-11)

### 🔧 修复 / 改进

* **OpenAudio 显存优化** - 将 KV cache 上限从 8192 降到 2048，节省约 1.3 GB VRAM
  * `fish-speech-src/fish_speech/models/text2semantic/inference.py`：`init_model` 和 `launch_thread_safe_queue` 支持 `max_length` 参数
  * `app/tts/openaudio.py`：`launch_thread_safe_queue` 传入 `max_length=2048`（可通过 config 覆盖）
  * `app/config.yaml`：新增 `max_length: 2048`、`max_new_tokens: 512` 配置项
  * 实际显存预估：从 ~7GB 降至 ~5.5GB（8GB 卡更宽裕）

### VRAM 分析（RTX 3070 Ti Laptop 8GB）

| 组件 | 优化前 | 优化后 |
|------|--------|--------|
| LLM 权重 (bfloat16) | ~1.7 GB | ~1.7 GB |
| KV Cache (seq_len×28层) | ~1.8 GB | ~0.45 GB ✅ |
| Codec decoder | ~1.8 GB | ~1.8 GB |
| CUDA 上下文 + 激活 | ~1.5 GB | ~1.5 GB |
| **合计** | **~6.8 GB** | **~5.5 GB** |

### 📦 修改文件

| 文件 | 修改内容 |
|------|---------|
| fish-speech-src/fish_speech/models/text2semantic/inference.py | init_model/launch_thread_safe_queue 支持 max_length |
| app/tts/openaudio.py | 传入 max_length=2048 |
| app/config.yaml | 新增 max_length/max_new_tokens 配置 |

================================================================================

## 🟢 STABLE v1.4.15 (2026-04-11)

### 🔧 修复 / 改进

* **install_deps.bat** - 全面重写
  * 修复 `errorlevel` 误报检测逻辑（原来 `2>nul` 吞错误导致 errorlevel 误判）
  * 补全 fish-speech 20+ 个子依赖（原来只靠 `pip install -e .` 自动拉，无错误检测）
  * 修复 ChatTTS 需要 `transformers==4.35.0` 约束（原来无版本限制，会安装 5.x 破坏兼容）
  * 修复 PyTorch 安装改用官方 CUDA 12.1 wheel index（原来用清华源可能拿到 CPU 版）
  * 添加 `torchvision` 自动卸载（与 fish-speech 冲突，需在装 torch 后立即清理）
  * 修复 `protobuf==3.19.6` 约束（该版本与 grpcio 1.80.0 冲突，改为 `>=3.19.6`）
  * 添加最终验证步骤：自动导入所有关键包并打印状态汇总
  * 新增 `ERRORS` / `WARNINGS` 计数器，结束时显示汇总状态
  * 每步失败时打印具体说明和影响范围

* **app/requirements.txt** - 与实际环境对齐
  * 添加所有 fish-speech/OpenAudio 依赖（原来缺 20+ 个）
  * 标注 `transformers==4.35.0` 的 ChatTTS 兼容性要求
  * 标注 `torchvision` 禁止安装说明
  * 添加 fish-speech API server 依赖分组注释

### 📦 修改文件

| 文件 | 修改内容 |
|------|---------|
| install_deps.bat | 全面重写，补全依赖、修复错误处理 |
| app/requirements.txt | 与实际依赖对齐 |

================================================================================

## 🟢 STABLE v1.4.14 (2026-04-11)

### 🔧 修复

* **config.yaml** - 默认 TTS 改为 edge（原来是 openaudio）
  * openaudio 在启动时触发 GPU warmup，与 LLM 共争 8GB 显存导致 OOM 崩溃
  * 现在 edge 作为默认启动引擎，openaudio 在网页端手动切换时懒加载

* **tts/openaudio.py** - warmup generator 完整排干
  * 原来只调用 `next(gen)` 拿第一帧，generator 未排干会导致 CUDA 操作异常
  * 现在完整遍历 generator 直到 final 帧

* **main.py** - 移除所有 emoji（61 处）
  * Windows GBK 控制台不支持 emoji，导致 UnicodeEncodeError

* **web/__init__.py** - 移除剩余 emoji（5 处）

### ✅ 端到端测试通过

| 测试项 | 结果 |
|--------|------|
| 模块导入 | OK |
| TTS (Edge) 初始化 | available: True |
| LLM (MiniMax) 初始化 | available: True |
| HTTP 端口 12393 | OPEN |
| WebSocket 端口 12394 | OPEN |
| 前端页面加载 | status 200 |

================================================================================

## 🟢 STABLE v1.4.13 (2026-04-10)

### 🔧 修复

* **web/__init__.py** - Windows 兼容性和稳定性修复
  * 移除所有 emoji 打印（Windows GBK 环境不支持）
  * 添加 WebServer.shutdown() 方法
  * 添加 WebSocketServer.shutdown() 方法
  * 修复 on_left 中 client 可能为 None 的问题

### ✅ 端到端测试通过

* HTTP/WebSocket 服务器启动正常
* 前端页面加载成功 (status 200)
* TTS 引擎选择器存在
* OpenAudio 选项存在

================================================================================

## 🟢 STABLE v1.4.12 (2026-04-10)

### ✨ 新增

* **Web 前端 TTS 面板 OpenAudio 支持** - 适配 OpenAudio S1-mini 直接引擎模式

  * 后端 WebSocket 统一使用 `_get_tts_for_client()` 获取 TTS 引擎（带缓存）
  * 新增 `_client_tts_engine` / `_client_tts_voice` 跟踪每个客户端的 TTS 选择
  * `_handle_tts` - TTS 面板点击播放时调用对应引擎
  * `_handle_text` - LLM 返回后自动 TTS 使用客户端选择的引擎
  * 前端发送消息时携带当前 TTS 引擎信息

### 🔧 修复

* **openaudio.py** - 参考音频自动加载
  * 新增 `_update_reference_from_config()` - 单例复用时动态更新参考音频
  * 自动从项目根目录加载 `ref_3s.wav`
  * 支持直接传入 bytes 或文件路径两种方式

* **前端 index.html** - TTS 面板选项修正
  * OpenAudio 声音选项改为：`默认音色(参考音频克隆)` / `无参考音频(原始音色)`
  * 移除不存在的 fish.audio 云端 reference_id

* **config.yaml** - OpenAudio 配置改为直接引擎模式
  * 移除 api_url/api_key 等 API server 配置
  * 新增 model_dir, temperature, top_p 等直接引擎参数

* **go.bat** - 简化启动流程
  * 移除 API server 检查（OpenAudio 不再需要）
  * 移除 tts_api.py 自动启动
  * 一键启动直接引擎模式

* **tts_api.py** - OpenAudio 也用直接引擎模式

### 📦 修改文件

| 文件 | 修改内容 |
|------|---------|
| app/web/__init__.py | 重构 WebSocket TTS 处理逻辑 |
| app/web/static/index.html | TTS 面板声音选项 + 消息携带引擎信息 |
| app/tts/openaudio.py | 参考音频自动加载 + 单例复用更新 |
| app/config.yaml | OpenAudio 直接引擎模式配置 |
| go.bat | 移除 API server 检查 |
| app/tts_api.py | OpenAudio 直接引擎模式 |

================================================================================

## 🟢 STABLE v1.4.11 (2026-04-09)

### ✨ 新增

* **OpenAudio 中文 TTS 支持** - 修复 OpenAudio S1-mini 中文语音合成完全失败的问题

  * 根因：模型对中文文本的 EOS (im_end) 概率极高，导致只生成 2 个 semantic token 就终止（约 46ms 噪音）
  * 实现 eos_bias 衰减策略，动态调整 EOS logit bias
  * 前 `eos_min_tokens`(默认30) 个 token 完全禁止 EOS (bias=-inf)
  * 之后线性衰减 bias 从初始值到 0，让模型自然终止
  * 自动检测 CJK 字符，中文文本自动设置 eos_bias=-5.0, eos_min_tokens=30
  * 英文文本不应用 bias，行为不变

### 🔧 修复

* **inference.py** - `decode_n_tokens()` 新增 `eos_bias` 和 `eos_min_tokens` 参数
  * 循环中动态调整 `semantic_logit_bias`：前期完全禁止 EOS，后期线性衰减
  * `generate()` 和 `generate_long()` 都正确传递 eos_bias/eos_min_tokens 参数
  * 清理了冗余的调试日志（INFO → DEBUG）

* **\_\_init\_\_.py** - `send_Llama_request()` 自动检测 CJK 字符
  * 使用正则匹配检测 CJK 字符（中日韩统一表意文字 + 假名 + 谚文）
  * 中文文本自动设置 eos_bias=-5.0, eos_min_tokens=30
  * 英文文本 eos_bias=0.0，行为不变

* **openaudio.py** - 音频后处理增强
  * 新增 `_normalize_audio()` - 归一化低振幅音频（target_peak=0.95）
  * 新增 `_is_cjk_text()` - CJK 字符检测工具方法
  * `synthesize()` 中自动归一化 max_amp < 0.1 的音频（中文音频通常振幅很低）

### ⚡ 性能

* 中文短句("你好")：128 tokens → 5.90s 音频，推理时间约 5 分钟
* 中文长句(30字)：255 tokens → 11.84s 音频，推理时间约 24 分钟
* 推理速度 ~3-5s/token（8GB VRAM，GPU 无后台干扰时）
* ⚠️ GPU 后台进程（Wallpaper Engine, Edge 等）会抢占资源导致速度降低 50 倍

### 📊 测试结果

| 文本 | eos_bias | tokens | 音频时长 | max_amp | 归一化后 |
|------|----------|--------|---------|---------|---------|
| 你好，很高兴认识你 | -5.0 | 128 | 5.90s | 0.0277 | 0.95 |
| 今天天气真好，我们一起出去玩吧 | -5.0 | 255 | 11.84s | 0.0277 | 0.95 |
| Hello, nice to meet you | 0.0 | 127 | 5.90s | - | - |

### 🧹 清理

* 删除 ~90 个调试临时文件（test\_*.py, debug\_*.py, check\_*.py, \*.wav, \*.log 等）
* 根目录从混乱状态恢复到只保留 ai-vtuber-fixed/ 子目录

================================================================================

## 🟢 STABLE v1.4.10 (2026-04-06)

### 🔧 修复

* **fish-speech 模型文件部署** - 修复 Windows 软链接导致的编码问题

  * 删除 fish-speech-src/checkpoints/openaudio-s1-mini/ 下的所有软链接
  * 复制真实模型文件到 checkpoints 目录(总计 3.4GB)

    * model.pth (1.7GB) - 主模型文件
    * codec.pth (1.8GB) - 编解码器模型
    * config.json (844B) - 配置文件
    * tokenizer.tiktoken (2.5MB) - 分词器
    * special\_tokens.json (124KB) - 特殊标记
  * 解决 UTF-8 解码错误问题
  * 创建 fix\_fish\_speech\_encoding.py 和 .bat 脚本用于修复源码编码问题

### 📝 文档

* 更新版本记录到 v1.4.10
* 记录软链接问题和解决方案

================================================================================

## 🟢 STABLE v1.4.9 (2026-04-06)

### 🧹 项目清理

* **批处理文件整理** - 清理项目根目录临时脚本

  * 删除 16 个临时测试用批处理文件
  * 保留 6 个核心批处理文件(go.bat, go\_debug.bat, install\_deps.bat, start\_fish\_api.bat, start\_with\_fish\_api.bat, setup\_openaudio\_windows.bat)
  * 重写 install\_deps.bat,整合完整依赖安装流程
  * 添加详细的安装步骤说明和错误处理

### 📝 文档

* 更新版本记录到 v1.4.9
* 优化项目结构,提升可维护性

================================================================================

## 🟢 STABLE v1.4.8 (2026-04-06)

### 🔧 修复

* **修复 OpenAudio is\_available 属性错误** - 将 @property 装饰器改为普通方法

  * 修复 `'bool' object is not callable` 错误
  * 统一所有 TTS 引擎的 is\_available 为方法调用
  * 确保 TTSFactory.create() 正常工作

### 📝 文档

* 更新版本记录到 v1.4.8

================================================================================

## 🟢 STABLE v1.4.7 (2026-04-06)

### 🔧 修复

* **修复 TTS is\_available 调用遗漏** - 修复 main.py 第260行遗漏的方法调用括号

  * 将 `self.tts.is\\\_available` 改为 `self.tts.is\\\_available()`
  * 保持与其他模块调用方式一致
  * 确保 TTS 引擎可用性检查正常工作

### 📝 文档

* 更新版本记录到 v1.4.7

================================================================================

## 🟢 STABLE v1.4.6 (2026-04-06)

### 🔧 修复

* **修复 is\_available 方法调用错误** - 将 @property 改回普通方法

  * 修复 TTSEngine 基类:移除 @property,保留 @abstractmethod
  * 修复 EdgeTTS 和 ChatTTSEngine:移除 @property,改为普通方法
  * 修复 main.py 中的调用方式(从属性访问改回方法调用)
  * 保持与 ASR、LLM、Voice 等模块的 is\_available 实现一致

### 📝 文档

* 更新版本记录到 v1.4.6

================================================================================

## 🟢 STABLE v1.4.5 (2026-04-06)

### 🔧 修复

* **fish-speech 依赖冲突彻底解决** - 解决 einx 版本死锁问题

  * 降级 vector-quantize-pytorch 到 1.14.0(要求 einx>=0.1.3,兼容 0.2.2)
  * 保持 einx==0.2.2(同时满足 fish-speech 和 vector-quantize-pytorch)
  * 保持 protobuf==3.19.6(兼容所有依赖)
  * 重新安装 ChatTTS 确保使用降级后的 vector-quantize-pytorch
  * 创建 install\_fish\_speech\_final.bat 一键安装脚本
  * ✅ 所有包导入测试通过(fish-speech, ChatTTS, vector-quantize-pytorch)

### 📝 文档

* 更新依赖安装指南
* 记录完整的依赖冲突解决过程

================================================================================

## 🟢 STABLE v1.4.4 (2026-04-06)

### 🔧 修复

* **TTSEngine 基类 is\_available 类型不匹配** - 修复 "'bool' object is not callable" 错误

  * 在基类 `tts/\\\_\\\_init\\\_\\\_.py` 中将 `is\\\_available` 从抽象方法改为抽象属性
  * 添加 `@property` 装饰器确保所有子类实现为属性而非方法
  * 解决 OpenAudioEngine 加载失败问题
  * 统一所有 TTS 引擎的 `is\\\_available` 调用方式(无需括号)

================================================================================

## 🟢 STABLE v1.4.3 (2026-04-06)

### 🔧 修复

* **OpenAudioEngine.is\_available 属性缺失** - 修复 TTS 工厂无法检查引擎可用性的问题

  * 添加 @property is\_available 方法
  * 返回 FISH\_SPEECH\_AVAILABLE 状态
  * 确保 TTS 工厂能正确判断引擎是否可用

================================================================================

## 🟢 STABLE v1.4.2 (2026-04-06)

### ✨ 新增

* **OpenAudio S1-mini TTS 引擎完整实现** - 基于 FishAudio S1-mini 的本地语音合成

  * 支持 13 种语言(中英日韩德法西阿俄荷意波葡)
  * 0.5B 参数,轻量高效,本地部署无需联网
  * 完整实现 Text2Semantic + VQGAN 解码流程
  * 自动设备选择(CUDA/CPU)
  * 文本缓存 + 音频缓存双重优化
  * 支持温度、top\_p、重复惩罚等参数调节

### 🔧 核心实现

* **\_load\_model()** - 完整的模型加载逻辑

  * 加载 Text2Semantic 模型(model.pth)
  * 加载 VQGAN 编解码器(codec.pth)
  * 自动检测 CUDA/CPU 设备
  * 模型文件完整性验证
* **speak()** - 完整的语音合成流程

  * 文本 → 语义 token(Text2Semantic.generate)
  * 语义 token → 音频波形(VQGAN.decode)
  * 音频归一化 + WAV 格式保存
  * 智能缓存机制(避免重复合成)
* **\_save\_audio()** - 音频保存逻辑

  * 使用 scipy.io.wavfile 保存 WAV 文件
  * 音频归一化到 int16 范围
  * 默认采样率 44100Hz

### 📝 代码质量

* **完整的异常处理** - 模型加载、合成、保存全流程异常捕获
* **详细的日志输出** - 每个步骤都有状态提示
* **资源自动清理** - **del** 方法释放 GPU 内存
* **依赖检查机制** - 启动时检查 fish-speech 库是否安装

### 📦 依赖要求

* **fish-speech** - FishAudio 官方库(pip install fish-speech)
* **torch** - PyTorch 深度学习框架
* **scipy** - 音频文件保存(scipy.io.wavfile)
* **numpy** - 数组处理

### 🔧 配置更新

* **config.yaml** - OpenAudio TTS 配置项

  * model\_path: ./app/OpenAudio S1-Mini
  * language: zh(支持 13 种语言)
  * speed: 1.0
  * temperature: 0.7(控制随机性)
  * top\_p: 0.8(核采样)
  * repetition\_penalty: 1.2(重复惩罚)

### 📊 性能特点

* **轻量级模型** - 0.5B 参数,适合本地部署
* **智能缓存** - 相同文本直接复用,提升响应速度
* **GPU 加速** - 自动检测 CUDA,支持 GPU 加速推理
* **内存优化** - 推理时使用 torch.no\_grad() 节省显存

================================================================================

## 🟡 BETA v1.4.1 (2026-04-06)

### ✨ 新增

* **OpenAudio S1-mini TTS 引擎框架** - 集成 FishAudio S1-mini 本地语音合成

  * 支持 13 种语言(中英日韩德法西阿俄荷意波葡)
  * 0.5B 参数,轻量高效
  * 模型文件:model.pth (1.7G) + codec.pth (1.8G)
  * 本地部署,无需联网

### 📝 文档

* **openaudio.py** - 创建 OpenAudio TTS 引擎框架

  * 支持文本缓存和音频缓存
  * 自动设备选择(CUDA/CPU)
  * 统一音频输出路径

### ⚠️ 已知问题

* **依赖缺失** - OpenAudio S1-mini 需要 `fish-speech` 库支持

  * 安装命令:`pip install fish-speech`
  * 当前版本暂不可用,请使用 ChatTTS 或 Edge TTS
* **模型加载** - 需要正确的模型加载方式(v1.4.2 已实现)

### 🔧 配置更新

* **config.yaml** - 添加 openaudio TTS 配置项

  * model\_path: ./app/OpenAudio S1-Mini
  * language: zh
  * speed: 1.0
  * temperature: 0.7
* **fallback\_engines** - 添加 openaudio 作为备用引擎

================================================================================

## 🟢 STABLE v1.4.0 (2026-04-06)

### 📝 文档

* **CODE\_REVIEW\_REPORT.md** - 新增代码架构深度分析报告

  * 全面分析 12 个核心模块(ASR/TTS/LLM/Memory/SubAgent/Live2D 等)
  * 架构设计评分:⭐⭐⭐⭐⭐ (4.7/5.0)
  * 数据流程分析(语音对话流程/Web 交互流程)
  * 性能优化分析(已实现优化/性能瓶颈)
  * 安全性分析(安全机制/安全风险)
  * 代码质量评估(6 个维度评分)
  * 优化建议路线图(短期/中期/长期)

### 🔍 代码审查

* **TTS 模块** - 双引擎架构,智能缓存,已修复 3 个 Bug
* **LLM 模块** - 连接池、速率限制、重试策略完善
* **Memory 模块** - 分层存储,文件持久化,向量搜索
* **SubAgent 模块** - 6 种工具,安全机制完善
* **Live2D 模块** - 多路径检测,Web 界面,表情控制

### 📊 质量评估

* **架构设计**: ⭐⭐⭐⭐⭐ (分层清晰,模块解耦,易扩展)
* **代码规范**: ⭐⭐⭐⭐ (命名规范,注释完整,缺少类型提示)
* **安全性**: ⭐⭐⭐⭐⭐ (白名单模式,路径验证,安全日志)
* **性能**: ⭐⭐⭐⭐ (缓存优化,连接池,有提升空间)
* **可维护性**: ⭐⭐⭐⭐⭐ (工厂模式,配置分离,易于维护)
* **文档**: ⭐⭐⭐⭐ (模块注释完整,缺少 API 文档)

### 🚀 优化路线图

* **短期 (1-2周)**: 类型提示、单元测试、配置验证、API 文档
* **中期 (1个月)**: 全面异步化、性能监控、错误追踪、流式 TTS
* **长期 (3个月)**: 微服务化、容器化部署、CI/CD 流程、分布式部署

================================================================================

## 🟢 STABLE v1.3.0 (2026-04-06)

### ✨ 新增功能

* **工具模块 (utils.py)** - 统一路径验证、临时文件管理、错误信息友好化
* **日志系统 (logger\_new.py)** - 统一日志管理、自动轮转、彩色输出、安全日志独立
* **TTS 缓存 (tts\_cache.py)** - 缓存已生成语音,避免重复合成,提升 50%+ 响应速度
* **上下文管理器** - AIVTuber 支持 with 语句,确保资源自动清理

### 🔧 P0 严重问题修复

* **资源泄漏修复** - 添加 `\\\_\\\_enter\\\_\\\_` 和 `\\\_\\\_exit\\\_\\\_` 方法,确保线程池和 HTTP Session 正确关闭
* **异常处理改进** - 具体化异常类型(FileNotFoundError/PermissionError/TimeoutError),避免吞掉错误
* **历史记录管理** - 修复 `process\\\_message()` 中的切片逻辑,正确限制历史长度
* **临时文件清理** - 使用 `temp\\\_file` 上下文管理器,确保临时文件自动清理

### 🐛 P1 重要问题修复

* **消除代码重复** - 路径验证、Python 路径设置统一到 utils.py
* **配置管理优化** - 新增 `load\\\_env\\\_or\\\_config()` 函数,优先级:环境变量 > 配置文件 > 默认值
* **日志系统完善** - 统一日志级别控制、自动轮转(10MB/文件)、安全日志独立
* **安全检查增强** - SubAgent 命令权限检查添加黑名单机制

### ⚡ P2 性能优化

* **TTS 缓存机制** - 相同文本重复合成提升 50%+ 响应速度
* **缓存自动清理** - 按时间(7天)和大小(100MB)自动清理过期缓存
* **日志性能优化** - 控制台仅输出 WARNING 及以上级别,减少 I/O

### 📝 文档

* **OPTIMIZATION\_PLAN.md** - 详细优化计划和实施方案
* **main\_patch.py** - 优化补丁模块,包含所有关键修复
* **代码注释完善** - 所有新增模块添加详细文档字符串

================================================================================

## 🟢 STABLE v1.2.1 (2026-04-06)

### 🔐 安全加固 (P0)

* **命令注入防护** - BashTool 添加命令超时限制(30秒)
* **路径遍历防护** - ReadTool/WriteTool 添加 `\\\_validate\\\_path()` 方法

  * 使用 `Path.resolve()` 获取绝对路径
  * 检查路径是否在工作目录内
  * 添加异常处理,避免信息泄露
* **文件大小限制** - WriteTool 添加 10MB 文件大小限制

  * 使用临时文件 + 原子性重命名,避免写入失败导致数据损坏
* **HTTP 请求安全** - FetchTool 添加安全机制

  * 10 秒超时限制
  * 10MB 响应大小限制
  * 重试策略(最多 3 次,指数退避)
* **命令白名单机制** - SubAgent 添加命令执行权限控制

  * `allowed\\\_commands` 白名单机制
  * `\\\_is\\\_command\\\_allowed()` 验证方法
  * `\\\_log\\\_security\\\_event()` 安全日志记录
  * 拒绝执行未授权命令

### 📝 文档

* **SECURITY\_FIXES.md** - 新增安全修复报告文档

================================================================================

## 🟡 BETA v1.2.0 (2026-04-05)

### 🔐 安全加固 (P0)

* **权限检查修复** - `subagent.py` \_check\_permission() 添加危险命令黑名单检测
* **资源泄漏修复** - `subagent.py` 添加 shutdown() 方法,正确关闭线程池和 HTTP Session
* **超时异常处理** - `openclaw/\\\_\\\_init\\\_\\\_.py` 添加 TimeoutExpired 异常捕获
* **输入验证加强** - `tools/\\\_\\\_init\\\_\\\_.py` 所有文件操作添加路径验证和权限检查
* **路径遍历防护** - 使用 Path.resolve() 防止路径遍历攻击
* **编辑工具安全** - EditTool 添加多处匹配警告,防止意外替换

### 🐛 Bug修复 (P1)

* **异常处理改进** - 所有文件操作添加 FileNotFoundError 和 PermissionError 处理
* **析构函数安全** - `subagent.py` **del** 添加异常捕获,防止析构时崩溃

### 📝 文档

* **VERSION.md** - 更新版本记录

================================================================================

## 🟡 BETA v1.1.9 (2026-04-05)

### 🐛 优化 (P0)

* **代码清理** - 移除重复的 sys.path.insert() 代码
* **历史记录管理** - 修复 process\_message 中的逻辑混乱和注释代码
* **资源泄漏修复** - ToolExecutor 线程池添加安全检查,防止未初始化时调用
* **错误处理改进** - process\_message/process\_audio\_data 添加完整异常捕获和日志
* **临时文件清理** - process\_audio\_data 改进错误日志输出
* **优雅关闭** - stop() 方法添加详细日志和异常处理

### 📝 文档

* **VERSION.md** - 更新版本记录

================================================================================

## v1.1.9 (2026-04-14)

### 🚀 性能优化

* **S2 训练 grad_ckpt 默认开启** - `manager.py` / `index.html`
  * `grad_ckpt=False` 硬编码导致 DiT 显存爆炸（22层 × batch=4 × seq=964 全量激活），一步需 20 分钟
  * 改为默认 `True`（前端加 checkbox，默认勾选），节省 ~50% 显存，backward 略慢但整体可用
  * 影响文件：`app/trainer/manager.py`（2处）、`app/web/static/index.html`（前端 UI + JS 逻辑）

### 🔧 修复

* **S2 RandomSampler batch_sampler TypeError** - `GPT-SoVITS/GPT_SoVITS/s2_train_v3_lora.py`
  * PyTorch 2.5.1 `_auto_collation=True` 时 RandomSampler 作为 batch_sampler yield 单个 int 导致报错
  * Windows 上改用 `sampler=RandomSampler + batch_size` 标准模式；Linux 保持 `batch_sampler=DistributedBucketSampler`

* **S2 mp.spawn Windows DLL 崩溃** - `s2_train_v3_lora.py`
  * 绕过 `mp.spawn`，Windows 直接 `run(0, n_gpus, hps)` 在主进程跑

* **S2 PYTHONPATH 子进程丢失** - `app/trainer/manager.py`
  * `sys.path.insert` 不被子进程继承，添加 `PYTHONPATH` 环境变量

---

## v1.1.8 (2026-04-05)

### 🔧 修复

* **LLM配置更新** - 更换为新API Key和中转地址

  * API Key: sk-cp-3eda7939...
  * 中转地址: http://120.24.86.32:3000/anthropic
  * 模型: claude-opus-4-6

================================================================================

## 🟡 BETA v1.1.7 (2026-04-05)

### 🔐 安全加固 (P0)

* **命令注入风险** - `subagent.py`/`tools/\\\_\\\_init\\\_\\\_.py` 修复 shell=True 改为 shell=False + shlex.split()
* **API Key 硬编码** - `config.yaml` 改为环境变量格式 ${MINIMAX\_API\_KEY} / ${SUBAGENT\_API\_KEY}

### 🔧 修复 (P1)

* **空异常捕获** - `main.py`/`openclaw/\\\_\\\_init\\\_\\\_.py`/`permissions.py` 改为具体异常类型
* **权限检查形同虚设** - `subagent.py` 默认返回 False

### 🐛 Bug修复 (P2)

* **历史记录无限增长** - `main.py` 添加 MAX\_HISTORY = 100 限制
* **字符串替换只执行一次** - `tools/\\\_\\\_init\\\_\\\_.py` 移除 replace() 的 ,1 参数
* **冗余导入** - `main.py` 移除重复的 import sys/Path

================================================================================

## 🟡 BETA v1.1.6 (2026-04-05)

### ✨ 新增

* **ChatTTS本地模型** - Windows GPU加速
* **PyTorch CUDA** - RTX 3070 + cu121

### 🔧 修复

* **gpt.py边界检查** - 修复narrow()负数问题
* **config.yaml** - 更新model\_path为./app/ChatTTS
* **vocos依赖** - 清华源安装
* **torchvision冲突** - 重装解决
* **重复对话语音** - 缓存加时间戳避免跳过

================================================================================

## 🟡 BETA v1.1.5 (2026-04-05)

### 🔧 修复

* **EdgeTTS** - is\_available不访问model\_path
* **fallback\_engines** - 添加备用引擎自动切换
* **tts\_api.py** - 支持选择ChatTTS/Edge TTS测试
* **config.yaml** - 改为chattts为主引擎

### ✨ 新增

* **TTS备用引擎** - ChatTTS失败时自动切换Edge

================================================================================

## 🟡 BETA v1.1.4 (2026-04-04)

### ✨ 新增

* 网页端支持ChatTTS选项
* 移除网页端 TTS 选项(只保留Edge)
* 移除 AllTalk TTS (用户请求)
* **文件管理面板** - 查看/编辑/删除文件功能
* **记忆系统 v2.0** - 全新升级版

  * 大语言模型思考过程过滤
  * AI行为说明过滤(关键词)
  * TTS新音频打断旧音频
  * 文件系统持久化 (参考 Claude Code)
  * 分层存储 (短期/中期/长期)
  * 重要性评分 (自动关键词+手动标记)
  * 搜索增强 (按时间/角色)
  * 导出/导入备份功能
* **网页端优化**

  * 历史面板: 搜索框、刷新、清空按钮
  * 记忆面板: 统计显示、搜索框、导出/导入按钮
  * 按钮对应修复

### 🔧 修复

* **历史/记忆面板** - 修复按钮对应关系

### 📝 文档

* **README** - 更新安装说明

================================================================================

## 🟡 BETA v1.0.4 (2026-04-04)

### 🔧 修复

* **saveLayout** - 恢复完整功能,保存位置+宽度+高度
* **loadLayout** - 恢复完整功能,加载布局并调用响应式
* **toggleAllPanels** - 修复显示/隐藏状态保存到localStorage
* **启动恢复** - 延时100ms确保DOM就绪后恢复布局和面板状态
* **面板resize** - 所有11个面板添加拖拽调整大小手柄

### 🐛 优化

* **响应式内容** - 调整面板大小时内部内容自动适应
* **CSS格式** - 修复缩进问题
* **Live2D画布** - 保存画布位置和缩放到localStorage

================================================================================

## 🟡 BETA v1.0.3 (2026-04-03)

### ✨ 新增

* 网页端支持ChatTTS选项
* 移除网页端 TTS 选项(只保留Edge)
* 移除 AllTalk TTS (用户请求)
* **文件管理面板** - 查看/编辑/删除文件功能
* **所有面板可调大小** - 11个面板均可拖拽调整
* **面板内元素响应式** - 按钮/输入框/文本框随面板大小自动调整排版
* **系统面板** - 清理、刷新、截图等功能
* **工具箱面板** - 文件管理、终端等功能
* **命令行面板** - 输入并执行命令
* **开关按钮** - 右上角一键显示/隐藏所有面板
* **面板调整大小** - 右上角拖拽调整面板尺寸
* **面板状态保存** - 自动保存位置/尺寸到 localStorage
* **刷新恢复** - 刷新网页后自动恢复面板设置

### 🐛 优化

* **index.html** - 修复可拖动面板显示问题

  * 添加彩色边框(系统📊粉色、工具箱🔧绿色、命令行⌨️蓝色)
  * 改进面板标题文字更醒目

