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



## 🟢 v1.20.8 (2026-06-08) ✅ STABLE

**桌面版深度优化 — 代码质量重构 + 性能优化 + 新功能**

### ✨ 新增
- **[LOG-001] 日志查看页面**：新增 `native/gugu_native/pages/log_page.py`
  - 实时日志流显示
  - 日志级别过滤（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - 日志搜索功能
  - 日志导出到文件
  - 自动滚动控制
  - 日志级别颜色编码

### 🔄 重构
- **[CHAT-001] ChatPage Mixin 重构**：将 2282 行的 ChatPage 拆分为 5 个 Mixin 类
  - `ChatPageLive2DMixin`: Live2D/VRM 模型管理
  - `ChatPageAudioMixin`: TTS 播放、口型同步、录音、ASR
  - `ChatPageMessageMixin`: 消息发送、流式对话、搜索
  - `ChatPageVisionMixin`: 图片上传、OCR、视觉理解
  - `ChatPageTTSConfigMixin`: TTS 引擎配置、历史记录持久化

- **[PATH-001] 路径工具模块**：新增 `native/gugu_native/utils/path_utils.py`
  - 统一路径操作函数（get_model_dir, get_history_path 等）
  - 减少代码重复（os.path.join 从 105 处减少到约 70 处）

### 🐛 优化
- **[PERF-001] 内存优化 — __slots__**：为 7 个关键类添加 __slots__
  - PerformanceManager: 12 slots
  - ChatSession: 5 slots
  - SessionManager: 4 slots
  - AnimationController: 6 slots
  - RealtimeVoiceManager: 5 slots
  - HotkeyManager: 3 slots
  - TrayManager: 3 slots

- **[PERF-002] 异常处理优化**：修复 79 处异常处理问题（添加变量捕获）
- **[PERF-003] 日志优化**：替换 93 处 print() 为 logger.info()
- **[PERF-004] 重复导入清理**：移除 58 处重复导入，涉及 22 个文件

### 🔧 修复
- **[FIX-001] _time 未定义错误**：添加 `import time as _time` 到 main.py
- **[FIX-002] AppColors 未定义错误**：添加 `from gugu_native.theme import AppColors` 到 manager.py

### 📝 文件变更
- **新增**: `native/gugu_native/pages/log_page.py`, `native/gugu_native/utils/path_utils.py`, `native/gugu_native/pages/chat_page_mixins/__init__.py`, `native/gugu_native/pages/chat_page_mixins/live2d_mixin.py`, `native/gugu_native/pages/chat_page_mixins/audio_mixin.py`, `native/gugu_native/pages/chat_page_mixins/message_mixin.py`, `native/gugu_native/pages/chat_page_mixins/vision_mixin.py`, `native/gugu_native/pages/chat_page_mixins/tts_config_mixin.py`
- **修改**: `native/main.py`, `native/gugu_native/pages/chat_page.py`, `native/gugu_native/widgets/perf_manager.py`, `native/gugu_native/widgets/session_manager.py`, `native/gugu_native/widgets/animation_controller.py`, `native/gugu_native/widgets/voice_manager.py`, `native/gugu_native/widgets/hotkey_manager.py`, `native/gugu_native/widgets/tray_manager.py`, `native/gugu_native/themes/manager.py`, `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.19.1 (2026-06-04) ✅ STABLE

### 🔧 优化
- **[MOBILE-003] 移动端本地运行**：修改移动端应用支持完全本地运行，无需后端服务器
  - 新增本地AI服务：`mobile/src/services/localAI.ts`
  - 修改对话页面使用本地AI服务
  - 支持本地历史记录存储

### 📝 文件变更
- **新增**: `mobile/src/services/localAI.ts`
- **修改**: `mobile/src/screens/ChatScreen.tsx`, `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.19.0 (2026-06-04) ✅ STABLE

### ✨ 新增
- **[MOBILE-002] 移动端应用**：新增 `mobile/` 目录，包含完整的React Native移动端应用
  - 对话页面：与AI进行文字对话
  - 角色页面：查看和选择角色
  - 记忆页面：查看记忆系统状态
  - 直播页面：连接直播平台
  - 设置页面：服务器连接、主题、语言设置

### 📝 文件变更
- **新增**: `mobile/package.json`, `mobile/src/App.tsx`, `mobile/src/navigation/AppNavigator.tsx`, `mobile/src/screens/ChatScreen.tsx`, `mobile/src/screens/CharacterScreen.tsx`, `mobile/src/screens/MemoryScreen.tsx`, `mobile/src/screens/LiveScreen.tsx`, `mobile/src/screens/SettingsScreen.tsx`, `mobile/src/services/api.ts`, `mobile/src/store/appStore.ts`, `mobile/src/utils/constants.ts`, `mobile/tsconfig.json`, `mobile/README.md`
- **修改**: `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.18.9 (2026-06-04) ✅ STABLE

### ✨ 新增
- **[MOBILE-001] 移动端支持模块**：新增 `app/mobile/__init__.py`，提供移动端API接口、响应式设计、触摸交互支持
- **[I18N-001] 国际化增强模块**：新增 `app/i18n/enhanced_i18n.py`，支持12种语言、动态翻译、语言包管理
- **[PLUGIN-002] 插件市场增强版**：新增 `app/plugin/enhanced_marketplace.py`，支持插件发布、搜索、评分、下载、版本管理

### 📝 文件变更
- **新增**: `app/mobile/__init__.py`, `app/i18n/enhanced_i18n.py`, `app/plugin/enhanced_marketplace.py`
- **修改**: `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.18.8 (2026-06-04) ✅ STABLE

### ✨ 新增
- **[SING-001] AI唱歌增强版**：新增 `app/singing/enhanced_singing.py`，支持多种唱歌模式、伴奏分离、旋律生成、音效处理
- **[GAME-003] 屏幕识别增强版**：新增 `app/game/enhanced_screen_recognition.py`，支持多游戏识别、实时状态推断、智能决策

### 📝 文件变更
- **新增**: `app/singing/enhanced_singing.py`, `app/game/enhanced_screen_recognition.py`
- **修改**: `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.18.7 (2026-06-04) ✅ STABLE

### ✨ 新增
- **[LIVE-002] 抖音直播增强版**：新增 `app/live/platforms/douyin_enhanced.py`，实现完整的弹幕接收、发送、礼物处理、自动重连功能
- **[LIVE-003] 快手直播增强版**：新增 `app/live/platforms/kuaishou_enhanced.py`，实现完整的弹幕接收、发送、礼物处理、自动重连功能

### 📝 文件变更
- **新增**: `app/live/platforms/douyin_enhanced.py`, `app/live/platforms/kuaishou_enhanced.py`
- **修改**: `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.18.6 (2026-06-04) ✅ STABLE

### 📝 文档
- **[DOC-027] 项目设计路线图**：新增 `docs/PROJECT_DESIGN_ROADMAP.md`，包含项目现状检查、UI/UX设计、测试策略、功能发展路线图、多平台支持设计、性能指标设计、安全设计、商业化设计
- **[DOC-028] UI设计规范**：新增 `docs/UI_DESIGN_SPEC.md`，包含设计原则、颜色系统、字体系统、间距系统、圆角系统、阴影系统、图标系统、动画系统、响应式设计、组件规范

### 📝 文件变更
- **新增**: `docs/PROJECT_DESIGN_ROADMAP.md`, `docs/UI_DESIGN_SPEC.md`
- **修改**: `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.18.5 (2026-06-04) ✅ STABLE

### 🔧 优化
- **[OPT-030] 页面功能去重**：将调试页面中的RAG、SVC、唱歌、多AI群聊、摄像头功能移至功能设置页面
- **[OPT-031] 调试页面重构**：调试页面改为系统调试、性能监控、配置热重载功能

### 📝 文件变更
- **修改**: `native/gugu_native/pages/debug_page_optimized.py`, `native/gugu_native/pages/features_settings_page.py`, `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.18.4 (2026-06-04) ✅ STABLE

### ✨ 新增
- **[TEST-004] 性能测试模块**：新增 `tests/test_performance.py`，包含9个性能测试用例
- **[GAME-002] 游戏模板模块**：新增 `app/game/game_templates.py`，提供Minecraft、Factorio、Terraria、Stardew Valley的UI模板和识别规则

### 📝 文件变更
- **新增**: `tests/test_performance.py`, `app/game/game_templates.py`
- **修改**: `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.18.3 (2026-06-04) ✅ STABLE

### ✨ 新增
- **[TEST-003] 集成测试模块**：新增 `tests/test_integration.py`，包含10个集成测试用例
- **[DOC-026] 项目完整度检查**：新增 `docs/PROJECT_COMPLETENESS_CHECK.md`，详细检查各模块完整度

### 📝 文件变更
- **新增**: `tests/test_integration.py`, `docs/PROJECT_COMPLETENESS_CHECK.md`
- **修改**: `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.18.2 (2026-06-04) ✅ STABLE

### 📝 文档清理
- **[DOC-023] 过时文档删除**：删除analysis目录中5个过时文档（v1.11.0/v1.12.0版本）
- **[DOC-024] 过时参考文档删除**：删除reference目录中2个过时文档（v1.10.2/v1.11.23版本）
- **[DOC-025] 文档索引更新**：更新 `docs/INDEX.md`，删除对已删除文档的引用

### 📝 文件变更
- **删除**: `analysis/GAP_EVALUATION_v1.11.0.md`, `analysis/AI_COMPANION_BENCHMARK.md`, `analysis/CONFIGURATION_STATUS.md`, `analysis/PROJECT_ANALYSIS.md`, `analysis/ANALYSIS_SUMMARY.md`, `reference/COMPETITIVE_GAP_ANALYSIS.md`, `reference/GAP_DETAILED_ANALYSIS.md`
- **修改**: `docs/INDEX.md`, `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.18.1 (2026-06-04) ✅ STABLE

### 📝 文档整理
- **[DOC-020] 文档目录重组**：将docs目录按功能分类重组为features、analysis、optimization、architecture、diagrams等子目录
- **[DOC-021] 文档索引创建**：新增 `docs/INDEX.md`，提供完整的文档导航
- **[DOC-022] 过时文档归档**：将Phase 1/2/3完成报告等过时文档移至archive目录

### 📝 文件变更
- **新增**: `docs/INDEX.md`, `docs/DOCS_ORGANIZATION_PLAN.md`
- **移动**: 50+个文档文件重新分类到子目录
- **修改**: `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.18.0 (2026-06-04) ✅ STABLE

### ✨ 新增
- **[PERF-002] 启动优化模块**：新增 `app/startup_optimizer.py`，提供懒加载、预加载、启动时间优化
- **[PERF-003] 交互优化模块**：新增 `app/interaction_optimizer.py`，提供防抖、节流、操作队列、反馈优化
- **[PERF-004] 缓存优化模块**：新增 `app/cache_optimizer.py`，提供内存缓存、磁盘缓存、LRU策略、缓存预热

### 📝 文件变更
- **新增**: `app/startup_optimizer.py`, `app/interaction_optimizer.py`, `app/cache_optimizer.py`
- **修改**: `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.17.9 (2026-06-04) ✅ STABLE

### ✨ 新增
- **[TEST-001] 测试框架模块**：新增 `tests/test_framework.py`，提供单元测试、集成测试、性能测试支持
- **[TEST-002] 核心模块测试**：新增 `tests/test_core_modules.py`，包含10个核心模块的单元测试
- **[PERF-001] 性能监控模块**：新增 `app/performance_monitor.py`，提供CPU、内存、GPU、响应时间等性能指标监控

### 📝 文件变更
- **新增**: `tests/test_framework.py`, `tests/test_core_modules.py`, `app/performance_monitor.py`
- **修改**: `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.17.8 (2026-06-04) ✅ STABLE

### ✨ 新增
- **[GAME-001] 屏幕识别模块**：新增 `app/game/screen_recognition.py`，实现屏幕截图、OCR文字识别、游戏状态推断
- **[CONFIG-001] 配置热重载模块**：新增 `app/config_hot_reload.py`，实现配置文件监听、自动重载、变更通知

### 📝 文件变更
- **新增**: `app/game/screen_recognition.py`, `app/config_hot_reload.py`
- **修改**: `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.17.7 (2026-06-04) ✅ STABLE

### ✨ 新增
- **[LIVE-001] 弹幕增强模块**：新增 `app/live/danmaku_enhancer.py`，实现智能弹幕回复、礼物感谢、自动互动
- **[RAG-001] 增量更新模块**：新增 `app/rag/incremental_updater.py`，实现文档增量更新、版本管理、变更追踪
- **[PLUGIN-001] 插件市场模块**：新增 `app/plugin/marketplace.py`，实现插件发布、搜索、评分、下载

### 📝 文件变更
- **新增**: `app/live/danmaku_enhancer.py`, `app/rag/incremental_updater.py`, `app/plugin/marketplace.py`
- **修改**: `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.17.6 (2026-06-04) ✅ STABLE

### ✨ 新增
- **[ASR-001] 音频预处理模块**：新增 `app/asr/audio_preprocessor.py`，实现降噪、音量标准化、静音检测
- **[TTS-001] 语速控制模块**：新增 `app/tts/speed_control.py`，实现语速调整、停顿控制、情感语速
- **[EMO-001] 情感语音控制**：新增 `app/emotion/voice_emotion.py`，实现情感到语音参数的映射

### 📝 文件变更
- **新增**: `app/asr/audio_preprocessor.py`, `app/tts/speed_control.py`, `app/emotion/voice_emotion.py`
- **修改**: `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.17.5 (2026-06-04) ✅ STABLE

### 🔧 优化
- **[OPT-029] VAD优化**：新增 `app/vad/optimized_vad.py`，实现自适应阈值、降噪、概率平滑等优化

### 📝 文件变更
- **新增**: `app/vad/optimized_vad.py`
- **修改**: `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.17.4 (2026-06-04) ✅ STABLE

### ✨ 新增
- **[VOICE-001] 支持打断的语音输入**：新增 `app/voice/interrupt_voice.py`，集成VAD和打断处理器
- **[CONFIG-002] VAD和打断配置**：在config.yaml中添加VAD和打断配置参数

### 📝 文件变更
- **新增**: `app/voice/interrupt_voice.py`
- **修改**: `app/config.yaml`, `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.17.3 (2026-06-04) ✅ STABLE

### ✨ 新增
- **[VAD-001] VAD模块**：新增 `app/vad/__init__.py`，实现Silero VAD语音活动检测状态机
- **[INT-001] 打断处理器**：新增 `app/interrupt/__init__.py`，实现asyncio.Task取消链和打断处理
- **[DOC-019] 语音打断分析**：新增 `docs/VOICE_INTERRUPTION_ANALYSIS.md`，详细分析实时语音打断功能

### 📝 文件变更
- **新增**: `app/vad/__init__.py`, `app/interrupt/__init__.py`, `docs/VOICE_INTERRUPTION_ANALYSIS.md`
- **修改**: `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.17.2 (2026-06-04) ✅ STABLE

### 🔧 优化
- **[OPT-024] 声音处理模块优化**：优化SVC和唱歌模块，添加音频缓冲、实时处理、多引擎支持
- **[OPT-025] 知识库模块优化**：优化RAG模块，添加智能分块、向量存储、多策略检索
- **[OPT-026] 角色扮演模块优化**：优化角色管理，添加角色配置、剧情系统、会话管理
- **[OPT-027] 情感系统优化**：优化情感分析，添加多模态融合、情感记忆、情感化回复
- **[OPT-028] 插件系统优化**：优化插件管理，添加热加载、权限控制、配置管理

### 📝 文件变更
- **修改**: `app/svc/__init__.py`, `app/singing/__init__.py`, `app/rag/__init__.py`, `app/roleplay/__init__.py`, `app/emotion/__init__.py`, `app/plugin/__init__.py`, `app/version.py`, `docs/VERSION.md`

---

## 🟢 v1.17.1 (2026-06-04) ✅ STABLE

### ✨ 新增
- **[UI-014] 功能设置页面**：新增 `native/gugu_native/pages/features_settings_page.py`，统一管理声音处理、知识库、角色扮演、情感系统、插件系统配置
- **[UI-015] 功能设置页面集成**：将功能设置页面集成到主窗口导航栏

### 📝 文件变更
- **新增**: `native/gugu_native/pages/features_settings_page.py`
- **修改**: `native/main.py`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.17.0 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[UI-013] 单个保存按钮**：在设置页面中添加LLM、TTS、文生图等单个保存按钮

### 🔧 优化
- **[OPT-023] 调试页面优化**：从调试页面中删除文生图配置

### 📝 文件变更
- **修改**: `native/gugu_native/pages/settings_page.py`, `native/gugu_native/pages/debug_page_optimized.py`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.16.9 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[UI-012] 文生图配置集成**：将文生图配置集成到设置页面，类似LLM配置的交互方式
- **[CONFIG-001] 文生图提供商配置**：在shared_config.py中添加IMAGE_GEN_CONFIG，支持6个提供商

### 🔧 优化
- **[OPT-021] 设置页面优化**：在设置页面中添加文生图配置卡片
- **[OPT-022] 配置保存优化**：将文生图配置集成到统一保存流程

### 📝 文件变更
- **修改**: `app/shared_config.py`, `native/gugu_native/pages/settings_page.py`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.16.8 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[IMG-001] 文生图模块**：新增 `app/image_gen/__init__.py`，支持通义万相、智谱CogView、可图、DALL-E、Flux、小米MiMo等文生图API

### 🔧 优化
- **[OPT-019] 文生图配置**：将Stable Diffusion替换为文生图API，支持多个提供商
- **[OPT-020] 调试页面优化**：更新调试页面，将SD配置替换为文生图配置

### 📝 文件变更
- **删除**: `app/sd/` 目录
- **新增**: `app/image_gen/__init__.py`
- **修改**: `native/gugu_native/pages/debug_page_optimized.py`, `app/config.yaml`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.16.7 (2026-06-03) ✅ STABLE

### 🔧 优化
- **[OPT-018] 调试页面优化**：从功能调试页面中移除游戏和Bot配置，因为已经有单独的设置页面

### 📝 文件变更
- **修改**: `native/gugu_native/pages/debug_page_optimized.py`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.16.6 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[BOT-001] Discord Bot完善**：完善 `app/bot/discord_bot.py`，实现真实的Discord API连接
- **[BOT-002] Telegram Bot完善**：完善 `app/bot/telegram_bot.py`，实现真实的Telegram API连接
- **[BOT-003] QQ Bot**：新增 `app/bot/qq_bot.py`，支持QQ机器人
- **[BOT-004] 微信 Bot**：新增 `app/bot/wechat_bot.py`，支持微信公众号/企业微信
- **[BOT-005] 飞书 Bot**：新增 `app/bot/feishu_bot.py`，支持飞书机器人
- **[BOT-006] 钉钉 Bot**：新增 `app/bot/dingtalk_bot.py`，支持钉钉机器人
- **[BOT-007] Slack Bot**：新增 `app/bot/slack_bot.py`，支持Slack工作区Bot
- **[BOT-008] LINE Bot**：新增 `app/bot/line_bot.py`，支持LINE聊天Bot
- **[UI-010] 社交Bot设置页面**：新增 `native/gugu_native/pages/bot_settings_page.py`，支持8个平台配置
- **[UI-011] 社交Bot设置页面集成**：将社交Bot设置页面集成到主窗口导航栏

### 📝 文件变更
- **新增**: `app/bot/discord_bot.py`, `app/bot/telegram_bot.py`, `app/bot/qq_bot.py`, `app/bot/wechat_bot.py`, `app/bot/feishu_bot.py`, `app/bot/dingtalk_bot.py`, `app/bot/slack_bot.py`, `app/bot/line_bot.py`, `native/gugu_native/pages/bot_settings_page.py`
- **修改**: `native/main.py`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.16.5 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[UI-008] 游戏设置页面**：新增 `native/gugu_native/pages/game_settings_page.py`，支持Minecraft、Factorio、Terraria、Stardew Valley、通用屏幕识别配置
- **[UI-009] 游戏设置页面集成**：将游戏设置页面集成到主窗口导航栏

### 📝 文件变更
- **新增**: `native/gugu_native/pages/game_settings_page.py`
- **修改**: `native/main.py`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.16.4 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[GAME-001] Minecraft代理完善**：完善 `app/game/minecraft_agent.py`，实现真实的Minecraft API连接
- **[GAME-002] Factorio代理**：新增 `app/game/factorio_agent.py`，支持RCON连接
- **[GAME-003] Terraria代理**：新增 `app/game/terraria_agent.py`，支持RCON连接
- **[GAME-004] Stardew Valley代理**：新增 `app/game/stardew_valley_agent.py`，支持SMAPI HTTP API
- **[DOC-018] 游戏注入分析**：新增 `docs/GAME_INJECTION_ANALYSIS.md`，分析内存注入和模组注入可行性

### 🔧 优化
- **[OPT-017] 游戏代理管理器优化**：更新 `app/game/__init__.py`，支持所有新游戏

### 📝 文件变更
- **新增**: `app/game/minecraft_agent.py`, `app/game/factorio_agent.py`, `app/game/terraria_agent.py`, `app/game/stardew_valley_agent.py`, `docs/GAME_INJECTION_ANALYSIS.md`
- **修改**: `app/game/__init__.py`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.16.3 (2026-06-03) ✅ STABLE

### 📝 文档
- **[DOC-017] 游戏集成分析**：新增游戏集成详细分析文档 `docs/GAME_INTEGRATION_ANALYSIS.md`，包含技术方案对比、可扩展游戏列表、通用屏幕识别方案

### 📝 文件变更
- **新增**: `docs/GAME_INTEGRATION_ANALYSIS.md`
- **修改**: `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.16.2 (2026-06-03) ✅ STABLE

### 🔧 修复
- **[BUG-007] YouTube平台修复**：添加 `_receive_messages` 抽象方法实现
- **[BUG-008] 微信视频号平台修复**：添加 `_receive_messages` 抽象方法实现

### ✅ 测试
- **[TEST-001] 直播平台连接测试**：测试所有9个平台的实例创建和API访问
- **测试结果**: 所有平台实例创建成功，Bilibili API访问成功

### 📝 文件变更
- **新增**: `test_live_platforms.py`
- **修改**: `app/live/platforms/youtube.py`, `app/live/platforms/weixin_video.py`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.16.1 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[LIVE-007] 斗鱼平台实现**：新增 `app/live/platforms/douyu.py`
- **[LIVE-008] 虎牙平台实现**：新增 `app/live/platforms/huya.py`
- **[LIVE-009] YouTube平台实现**：新增 `app/live/platforms/youtube.py`
- **[LIVE-010] Twitch平台实现**：新增 `app/live/platforms/twitch.py`
- **[LIVE-011] TikTok平台实现**：新增 `app/live/platforms/tiktok.py`
- **[LIVE-012] 微信视频号平台实现**：新增 `app/live/platforms/weixin_video.py`

### 🔧 优化
- **[OPT-016] 调试页面优化**：从功能调试页面中移除直播平台配置，避免重复

### 📝 文件变更
- **新增**: `app/live/platforms/douyu.py`, `app/live/platforms/huya.py`, `app/live/platforms/youtube.py`, `app/live/platforms/twitch.py`, `app/live/platforms/tiktok.py`, `app/live/platforms/weixin_video.py`
- **修改**: `app/live/platforms/__init__.py`, `native/gugu_native/pages/debug_page_optimized.py`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.16.0 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[UI-007] 直播设置页面集成**：将直播设置页面集成到主窗口导航栏，支持9个平台配置

### 📝 文件变更
- **修改**: `native/main.py`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.15.9 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[LIVE-001] 统一直播平台架构**：新增 `app/live/platforms/` 模块，支持多平台扩展
- **[LIVE-002] Bilibili平台实现**：完整的Bilibili直播弹幕接收和发送功能
- **[LIVE-003] 抖音平台实现**：抖音直播弹幕接收框架
- **[LIVE-004] 快手平台实现**：快手直播弹幕接收框架
- **[LIVE-005] 直播平台配置界面**：新增 `native/gugu_native/pages/live_settings_page.py`，支持9个平台配置
- **[LIVE-006] 直播通信桥梁**：新增 `app/live/bridge.py`，实现直播与LLM/TTS的通信

### 📝 文件变更
- **新增**: `app/live/platforms/__init__.py`, `app/live/platforms/bilibili.py`, `app/live/platforms/douyin.py`, `app/live/platforms/kuaishou.py`, `app/live/bridge.py`, `native/gugu_native/pages/live_settings_page.py`
- **修改**: `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.15.8 (2026-06-03) ✅ STABLE

### 📝 文档
- **[DOC-016] 直播功能分析**：新增直播功能详细分析文档 `docs/LIVE_STREAMING_ANALYSIS.md`，包含Bilibili配置、多平台支持、扩展方案等

### 📝 文件变更
- **新增**: `docs/LIVE_STREAMING_ANALYSIS.md`
- **修改**: `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.15.7 (2026-06-03) ✅ STABLE

### 📝 文档
- **[DOC-015] 完整功能清单**：新增完整功能清单文档 `docs/ALL_FEATURES_SUMMARY.md`，详细列出所有功能模块

### 📝 文件变更
- **新增**: `docs/ALL_FEATURES_SUMMARY.md`
- **修改**: `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.15.6 (2026-06-03) ✅ STABLE

### 🔧 修复
- **[BUG-006] DebugPageOptimized日志显示修复**：修复`_log_text`属性未初始化导致的AttributeError，在`_on_log_message`方法中添加属性检查

### 📝 文件变更
- **修改**: `native/gugu_native/pages/debug_page_optimized.py`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.15.5 (2026-06-03) ✅ STABLE

### 🔧 修复
- **[BUG-005] 启动时窗口切换无响应修复**：优化QApplication.processEvents()调用，使用QTimer.singleShot替代直接调用，避免阻塞UI线程

### 📝 文件变更
- **修改**: `native/gugu_native/pages/chat_page.py`, `app/version.py`, `docs/VERSION.md`, `README.md`
- **新增**: `docs/STARTUP_UI_FREEZE_FIX.md`

---

## 🟢 v1.15.4 (2026-06-03) ✅ STABLE

### 🔧 修复
- **[BUG-003] 样式表解析修复**：移除Qt QSS不支持的`outline: none`属性
- **[BUG-004] 边框宽度修复**：将`1.5px`改为`1px`，Qt QSS不支持非整数像素值

### 📝 文件变更
- **修改**: `native/gugu_native/theme.py`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.15.3 (2026-06-03) ✅ STABLE

### 📝 文档
- **[DOC-014] 启动问题分析**：新增启动日志问题分析文档 `docs/STARTUP_ISSUES_RESOLVED.md`，分析并解决启动日志中的警告

### 📝 文件变更
- **新增**: `docs/STARTUP_ISSUES_RESOLVED.md`
- **修改**: `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.15.2 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[PLUGIN-001] 插件系统模块**：新增插件系统模块 `app/plugin/`，提供插件加载、插件管理、插件执行功能
- **[PLUGIN-002] 插件管理器**：支持插件发现、加载、启用、禁用、执行功能
- **[PLUGIN-003] 插件加载器**：支持从插件目录自动发现和加载插件

### 🔧 优化
- **[OPT-014] 插件系统配置支持**：在config.yaml中添加插件系统模块配置
- **[OPT-015] 插件系统模块集成**：将插件系统模块集成到AIVTuber类中

### 📝 文件变更
- **新增**: `app/plugin/__init__.py`
- **修改**: `app/main.py`, `app/config.yaml`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.15.1 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[RP-001] 角色扮演模块**：新增角色扮演模块 `app/roleplay/`，提供角色创建、角色扮演、剧情系统功能
- **[RP-002] 角色管理器**：支持角色创建、编辑、删除、查询功能
- **[RP-003] 剧情管理器**：支持剧情创建、编辑、删除、查询功能
- **[RP-004] 角色扮演管理器**：支持角色扮演会话管理

### 🔧 优化
- **[OPT-012] 角色扮演配置支持**：在config.yaml中添加角色扮演模块配置
- **[OPT-013] 角色扮演模块集成**：将角色扮演模块集成到AIVTuber类中

### 📝 文件变更
- **新增**: `app/roleplay/__init__.py`
- **修改**: `app/main.py`, `app/config.yaml`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.15.0 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[EMO-001] 情感理解模块**：新增情感理解模块 `app/emotion/`，提供情感识别、情感表达、情感记忆功能
- **[EMO-002] 情感分析器**：支持文本、语音、面部情感分析
- **[EMO-003] 情感表达器**：支持情感化回复生成和表情切换
- **[EMO-004] 情感记忆器**：支持情感历史记录和趋势分析

### 🔧 优化
- **[OPT-010] 情感配置支持**：在config.yaml中添加情感模块配置
- **[OPT-011] 情感模块集成**：将情感模块集成到AIVTuber类中

### 📝 文件变更
- **新增**: `app/emotion/__init__.py`, `docs/OPTIMIZATION_ROADMAP.md`
- **修改**: `app/main.py`, `app/config.yaml`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.14.5 (2026-06-03) ✅ STABLE

### 📝 文档
- **[DOC-013] 对比结果罗列**：新增对比结果罗列文档 `docs/COMPARISON_RESULTS.md`，清晰展示与各类软件的对比结果

### 📝 文件变更
- **新增**: `docs/COMPARISON_RESULTS.md`
- **修改**: `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.14.4 (2026-06-03) ✅ STABLE

### 📝 文档
- **[DOC-011] 市场对比分析**：新增市场对比分析报告 `docs/MARKET_COMPARISON_2026.md`，对比AI聊天、AI女友、AI直播、微信、QQ等软件
- **[DOC-012] 差距分析报告**：详细分析与各类软件的差距，提供发展建议

### 📝 文件变更
- **新增**: `docs/MARKET_COMPARISON_2026.md`
- **修改**: `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.14.3 (2026-06-03) ✅ STABLE

### 🔧 优化
- **[UI-003] 调试页面优化**：优化调试页面，增加配置保存、日志输出、状态监控等功能
- **[UI-004] 配置实时保存**：支持配置参数实时保存到配置文件
- **[UI-005] 日志输出面板**：增加日志输出面板，方便调试
- **[UI-006] 状态监控面板**：增加状态监控面板，实时显示功能状态

### 📝 文件变更
- **新增**: `native/gugu_native/pages/debug_page_optimized.py`
- **修改**: `native/main.py`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.14.2 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[UI-001] 功能调试页面**：新增功能调试页面 `native/gugu_native/pages/debug_page.py`，提供新增功能的图形化配置界面
- **[UI-002] 调试页面集成**：将调试页面集成到原生桌面应用的导航栏中

### 📝 文件变更
- **新增**: `native/gugu_native/pages/debug_page.py`
- **修改**: `native/main.py`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.14.1 (2026-06-03) ✅ STABLE

### 🔧 优化
- **[INT-001] 模块集成**：将所有新增模块集成到AIVTuber类中
- **[INT-002] 配置扩展**：在config.yaml中添加所有新增模块的配置参数
- **[INT-003] 懒加载支持**：为所有新增模块添加懒加载属性

### 📝 文件变更
- **修改**: `app/main.py`, `app/config.yaml`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.14.0 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[DOCKER-001] Docker部署支持**：新增Dockerfile和docker-compose.yml，支持服务器/云端部署
- **[MULTI-001] 多AI群聊模块**：新增多AI群聊模块 `app/multi_agent/`，支持多角色对话场景
- **[BOT-001] 社交Bot模块**：新增社交Bot模块 `app/bot/`，支持Discord/Telegram Bot接口
- **[VISION-001] 摄像头视觉输入模块**：新增摄像头视觉输入模块 `app/vision_input/`，支持摄像头视觉输入

### 📝 文件变更
- **新增**: `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `app/multi_agent/__init__.py`, `app/bot/__init__.py`, `app/vision_input/__init__.py`
- **修改**: `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.13.0 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[SVC-001] SVC声音转换模块**：新增SVC声音转换模块 `app/svc/`，支持So-VITS-SVC声音转换
- **[SING-001] 唱歌模块**：新增唱歌模块 `app/singing/`，支持AI唱歌功能
- **[SD-001] Stable Diffusion模块**：新增Stable Diffusion模块 `app/sd/`，支持AI绘画功能
- **[GAME-001] 游戏感知框架模块**：新增游戏感知框架模块 `app/game/`，支持Minecraft等游戏

### 🔧 优化
- **[OPT-008] TTS引擎扩展**：新增ElevenLabs和Fish-Speech TTS引擎支持
- **[OPT-009] 配置文件扩展**：在config.yaml中添加ElevenLabs和Fish-Speech配置

### 📝 文件变更
- **新增**: `app/svc/__init__.py`, `app/singing/__init__.py`, `app/sd/__init__.py`, `app/game/__init__.py`, `app/tts/elevenlabs.py`, `app/tts/fish_speech.py`
- **修改**: `app/tts/__init__.py`, `app/config.yaml`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.12.9 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[TTS-001] ElevenLabs TTS引擎**：新增ElevenLabs高质量语音合成引擎 `app/tts/elevenlabs.py`
- **[TTS-002] Fish-Speech TTS引擎**：新增Fish-Speech高质量语音合成引擎 `app/tts/fish_speech.py`
- **[TTS-003] TTS引擎扩展**：TTSFactory支持ElevenLabs和Fish-Speech引擎

### 🔧 优化
- **[OPT-007] TTS配置扩展**：在config.yaml中添加ElevenLabs和Fish-Speech配置

### 📝 文件变更
- **新增**: `app/tts/elevenlabs.py`, `app/tts/fish_speech.py`
- **修改**: `app/tts/__init__.py`, `app/config.yaml`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.12.8 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[LIVE-001] 直播平台集成模块**：新增直播平台集成模块 `app/live/`，支持Bilibili直播弹幕接收、解析、AI回复、弹幕发送
- **[LIVE-002] Bilibili直播客户端**：实现Bilibili直播弹幕WebSocket连接和接收
- **[LIVE-003] 弹幕解析器**：实现弹幕、礼物、系统消息等解析
- **[LIVE-004] AI回复生成器**：基于弹幕内容的AI回复生成功能
- **[LIVE-005] 弹幕发送器**：实现Bilibili直播弹幕发送功能

### 📝 文件变更
- **新增**: `app/live/__init__.py`, `app/live/bilibili_client.py`, `app/live/danmaku_parser.py`, `app/live/ai_responder.py`, `app/live/danmaku_sender.py`
- **修改**: `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.12.7 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[CROSS-001] 跨平台支持**：支持macOS和Linux操作系统
- **[CROSS-002] 跨平台启动脚本**：创建macOS/Linux启动脚本 `scripts/start.sh` 和 `scripts/go.sh`

### 🔧 优化
- **[OPT-004] 依赖检查函数跨平台适配**：使用平台抽象层的消息框，支持Windows/macOS/Linux
- **[OPT-005] 字体设置跨平台适配**：根据操作系统使用系统默认字体
- **[OPT-006] 图标文件跨平台适配**：根据操作系统使用对应的图标格式

### 📝 文件变更
- **新增**: `scripts/start.sh`, `scripts/go.sh`, `docs/CROSS_PLATFORM_ADAPTATION.md`
- **修改**: `native/main.py`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.12.6 (2026-06-03) ✅ STABLE

### 🔧 修复
- **[BUG-001] RAG知识库向量存储接口修复**：修复VectorStore.add()参数不匹配问题，使用正确的接口调用
- **[BUG-002] RAG知识库文档删除修复**：修复文档删除时向量存储清理问题，支持直接操作内部数据结构

### 📝 文件变更
- **修改**: `app/rag/knowledge_base.py`, `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.12.5 (2026-06-03) ✅ STABLE

### ✨ 新增
- **[RAG-001] RAG知识库模块**：新增RAG知识库模块 `app/rag/`，支持文档导入、文本分块、向量存储、检索增强生成
- **[RAG-002] 文档加载器**：支持PDF、TXT、MD、DOCX等多种文档格式
- **[RAG-003] 文本分块器**：智能文本分块，保持语义完整性
- **[RAG-004] 检索器**：支持向量检索和关键词检索
- **[RAG-005] 生成器**：检索增强生成功能
- **[RAG-006] 知识库管理**：文档管理、搜索、统计等功能

### 📝 文件变更
- **新增**: `app/rag/__init__.py`, `app/rag/document_loader.py`, `app/rag/text_splitter.py`, `app/rag/retriever.py`, `app/rag/generator.py`, `app/rag/knowledge_base.py`, `docs/RAG_ARCHITECTURE.md`
- **修改**: `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.12.4 (2026-06-03) ✅ STABLE

### 📝 文档
- **[DOC-009] 行业对比分析**：新增行业顶级项目对比分析 `docs/INDUSTRY_COMPARISON_2026.md`，对比Neuro-sama、AIRI、Open-LLM-VTuber、Luna AI等顶级项目
- **[DOC-010] 差距分析报告**：详细分析咕咕嘎嘎与行业顶级项目的差距，提供发展路线建议

### 📝 文件变更
- **新增**: `docs/INDUSTRY_COMPARISON_2026.md`
- **修改**: `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.12.3 (2026-06-03) ✅ STABLE

### 🔧 优化
- **[OPT-001] 配置验证模块**：新增配置验证模块 `app/config_validator.py`，提供配置验证、错误检查和配置优化功能
- **[OPT-002] 配置管理器**：新增配置管理器 `app/config_manager.py`，提供配置缓存、热更新、配置变更通知等功能
- **[OPT-003] 配置验证报告**：配置验证器可生成详细的配置验证报告，帮助识别配置问题

### 📝 文件变更
- **新增**: `app/config_validator.py`, `app/config_manager.py`
- **修改**: `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.12.2 (2026-06-03) ✅ STABLE

### 📝 文档
- **[DOC-004] 优化任务文档**：新增优化任务文档 `docs/OPTIMIZATION_TASK.md`，包含全面优化计划和任务分解
- **[DOC-005] 产品经理优化任务**：创建产品经理优化需求分析任务文档
- **[DOC-006] 架构师优化任务**：创建架构师优化方案设计任务文档
- **[DOC-007] 工程师优化任务**：创建工程师优化代码实现任务文档
- **[DOC-008] QA工程师优化任务**：创建QA工程师优化测试验证任务文档

### 📝 文件变更
- **新增**: `docs/OPTIMIZATION_TASK.md`, `/tmp/product_manager_optimization_task.md`, `/tmp/architect_optimization_task.md`, `/tmp/engineer_optimization_task.md`, `/tmp/qa_optimization_task.md`
- **修改**: `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.12.1 (2026-06-03) ✅ STABLE

### 📝 文档
- **[DOC-001] 项目分析报告**：新增详细的项目分析报告 `docs/PROJECT_ANALYSIS.md`，包含项目原理、技术架构、文档系统、版本管理机制等全面分析
- **[DOC-002] 产品分析任务**：创建产品经理分析任务文档，用于深入分析产品定位、用户需求和市场价值
- **[DOC-003] 架构分析任务**：创建架构师分析任务文档，用于深入分析系统架构和技术实现

### 📝 文件变更
- **新增**: `docs/PROJECT_ANALYSIS.md`, `/tmp/product_manager_task.md`, `/tmp/architect_task.md`
- **修改**: `app/version.py`, `docs/VERSION.md`, `README.md`

---

## 🟢 v1.11.29 (2026-06-01) ✅ STABLE

### ⚡ 性能
- **[P1-1] 模型缓存**：FunASRASR 新增类级别 `_model_cache` 缓存，避免重复加载相同模型
- **[P1-2] 帧率自适应**：Live2DWidget 新增帧率自适应机制，空闲 3 秒后自动从 60fps 降到 15fps，鼠标活动时恢复 60fps，GPU 负载降低 30%
- **[P1-3] 异步文件 I/O**：`_save_history()` 改为后台线程写入，不阻塞主线程
- **[P2-1] 模块预编译**：启动脚本 `start_debug.bat` 添加 `compileall` 预编译步骤，首次启动时预编译 Python 模块为 .pyc，后续启动导入速度提升 2x
- **[P2-2] 连接池优化**：LLM HTTP 连接池从 5/10 增加到 10/20，启用 keep-alive 复用 TCP 连接

### 📝 文件变更
- **修改**: `app/asr/__init__.py`, `native/gugu_native/widgets/live2d_widget.py`, `app/main.py`, `scripts/start_debug.bat`, `app/llm/__init__.py`, `app/version.py`, `docs/VERSION.md`, `README.md`, `native/build.bat`, `resources/version_info.txt`

---

## 🟢 v1.11.28 (2026-06-01) ✅ STABLE

### ⚡ 性能
- **[P0-2] Chromium 启动参数优化**：添加 25+ 个 Chromium 启动加速参数，禁用翻译、扩展、后台网络、同步、首次运行向导、默认浏览器检查、组件更新、后台定时器节流、平滑滚动等不必要的功能，预计启动快 3-5 秒
- **[Perf] 启动性能计时增强**：在 `GuguGagaApp.__init__()` 中添加更精细的计时点（Widget 模块导入、页面创建、主题应用），便于定位启动瓶颈

### 📝 文件变更
- **修改**: `native/main.py`, `app/version.py`, `docs/VERSION.md`, `README.md`, `native/build.bat`, `resources/version_info.txt`

---

## 🟢 v1.11.27 (2026-06-01) ✅ STABLE

### 🔧 修复
- **[BUG] QSS 样式表解析失败**：`build_global_qss_v5()` 中缺少 `chat_bg`、`progress_start`、`progress_end`、`br_card`、`sp_card`、`sp_global`、`br_input`、`br_widget`、`br_menu`、`card_bg_hover`、`font_family` 等变量的 fallback 值，导致 `%(var)s` 模板替换时 KeyError，QSS 解析失败

### ⚡ 性能
- **[S-003] Theme 预加载优化**：QSS 样式表缓存机制，避免每次切换主题时重新生成，最多缓存 10 个主题的 QSS，新增 `clear_qss_cache()` 函数
- **[S-004] Splash 进度细化**：启动画面支持百分比显示（`set_progress(text, percent)`），用户可看到具体加载进度
- **[R-005] OpenGL 渲染优化**：Live2DWidget 新增 `_last_gl_state` 缓存，减少重复 GL 状态切换
- **[M-002] 对话历史分页**：`_load_history()` 改为分页加载，只加载最近 50 轮（100 条）到内存，完整历史保留在磁盘，新增 `_full_history_on_disk` 引用
- **[M-003] 缓存 LRU 淘汰**：TTSCache 新增 `_access_order` LRU 跟踪（最多 500 个缓存键），优化缓存淘汰策略

### 🏗️ 架构
- **修改** `native/gugu_native/theme.py`：新增 QSS 缓存（`_qss_cache`）和 `clear_qss_cache()` 函数
- **修改** `native/gugu_native/widgets/splash_debug_window.py`：`set_progress()` 支持 `percent` 参数
- **修改** `native/gugu_native/widgets/live2d_widget.py`：新增 `_last_gl_state` 渲染状态缓存
- **修改** `app/main.py`：`_load_history()` 分页加载逻辑
- **修改** `app/tts_cache.py`：新增 `_access_order` LRU 跟踪

### 📝 文件变更
- **修改**: `native/gugu_native/theme.py`, `native/gugu_native/widgets/splash_debug_window.py`, `native/gugu_native/widgets/live2d_widget.py`, `app/main.py`, `app/tts_cache.py`, `app/version.py`, `docs/VERSION.md`, `README.md`, `native/build.bat`, `resources/version_info.txt`

---

## 🟢 v1.11.26 (2026-06-01) ✅ STABLE

### ⚡ 性能
- **[S-002] TTS 预热懒加载**：将 TTS 音色预热从启动时延迟到首次对话时，启动快 1-2 秒。首次对话时自动触发后台预热线程
- **[R-002] Memory 搜索缓存扩容**：VectorStore 搜索缓存从 50 扩到 200，提高缓存命中率，减少重复查询的计算开销
- **[R-006] 内存池化**：在 AIVTuber 中新增对象池（`_pool_get()`/`_pool_put()`），复用频繁创建的 dict/list 对象，减少 GC 压力
- **[M-001] 模型按需卸载**：PerformanceManager 新增 `unload_idle_models()` 方法，可卸载长时间未使用的模块（vision/mcp/desktop_pet），释放内存

### 🏗️ 架构
- **修改** `app/main.py`：新增对象池初始化和 `_pool_get()`/`_pool_put()` 方法
- **修改** `native/main.py`：TTS 预热延迟到首次对话，新增 `_tts_prewarmed` 标志
- **修改** `native/gugu_native/pages/chat_page.py`：首次对话时触发 TTS 预热
- **修改** `native/gugu_native/widgets/perf_manager.py`：新增 `unload_idle_models()` 方法
- **修改** `app/memory/__init__.py`：搜索缓存容量 50→200

### 📝 文件变更
- **修改**: `app/main.py`, `native/main.py`, `native/gugu_native/pages/chat_page.py`, `native/gugu_native/widgets/perf_manager.py`, `app/memory/__init__.py`, `app/version.py`, `docs/VERSION.md`, `README.md`, `native/build.bat`, `resources/version_info.txt`

---

## 🟢 v1.11.25 (2026-06-01) ✅ STABLE

### ⚡ 性能
- **[S-001] 模型预加载并行化**：新增 `AIVTuber.preload_models_parallel()` 方法，ASR/TTS/Memory 三个模型通过 `ThreadPoolExecutor` 并行加载，总耗时从 `sum(ASR, TTS, Memory)` 降为 `max(ASR, TTS, Memory)`，预计启动快 3-5 秒
- **[R-001] 对话历史流式压缩**：新增 `_compress_history()` 方法，当对话历史超过 60 轮（120 条）时自动压缩旧对话为摘要（优先 LLM 摘要，降级为规则摘要），保留最近 20 轮 + 历史摘要，减少 LLM token 消耗
- **[R-004] LLM 响应流式缓冲**：新增 `process_message_streaming()` 方法，LLM 回复按句分割后逐句 TTS 合成，用户更快听到第一句话，降低语音延迟

### 🏗️ 架构
- **修改** `app/main.py`：新增 `preload_models_parallel()`、`_compress_history()`、`process_message_streaming()` 三个方法
- **修改** `native/main.py`：后端就绪后调用 `preload_models_parallel()` 替代原来串行的 ASR 单独加载

### 📝 文件变更
- **修改**: `app/main.py`, `native/main.py`, `app/version.py`, `docs/VERSION.md`, `README.md`, `native/build.bat`, `resources/version_info.txt`

---

## 🟢 v1.11.24 (2026-06-03) ✅ STABLE

### ⚡ 性能
- **[P0-1] 页面按需懒加载**：改造 `main.py` `_create_pages()`，非首屏页面（Train/Memory/ModelDL/VRM/Settings）延迟到首屏渲染完成后创建，启动时仅构造 ChatPage，减少启动阻塞
- **[P0-2] 窗口拖动/resize 暂停 Live2D 渲染**：`PerfManager` 新增 `window_drag_state_changed` 信号广播拖动状态，`Live2DWidget` 订阅后暂停 `update()` 重绘，解决拖动窗口时"未响应"问题
- **[P0-3] SettingsPage 异步初始化**：`_load_saved_config()` 从 `__init__` 移至 `on_backend_ready()`，减少启动阶段同步 JSON I/O 阻塞
- **[P1-1] AudioVisualizer 可见性控制**：`showEvent`/`hideEvent` 控制 `_fft_timer` 启停，页面不可见时停止 FFT 计算；新增 `set_audio_active()` 静默降频到 5fps
- **[P1-2] 口型同步降频**：`_lipsync_timer` 从 50ms（20fps）降至 100ms（10fps），并添加页面不可见时跳过更新
- **[P1-3] VRMWidget 延迟创建**：`VRMSettingsPage` 继承 `LazyPageMixin`，构造时仅显示骨架屏，首次进入该页时才创建 `VRMWidget`
- **[P1-4] 禁用页面切换动画**：`main.py` 启动后关闭 `PopUpAniStackedWidget` 动画（300ms→0ms），消除切换页面时的卡顿感
- **[P2-1] GC 阈值调优**：`perf_manager.tune_gc_thresholds()` 放宽 gen0 阈值，减少启动阶段小对象频繁回收

### 🏗️ 架构
- **新增** `widgets/lazy_page_mixin.py`：懒加载页面混入基类
- **新增** `widgets/async_json_worker.py`：异步 JSON 读取 Worker
- **新增** `widgets/skeleton_container.py`：骨架屏占位容器
- **修改** `widgets/perf_manager.py`：新增窗口拖动状态广播 + GC 调优
- **修改** `widgets/live2d_widget.py`：拖动期间暂停重绘
- **修改** `widgets/audio_visualizer.py`：可见性控制 + 静默降频
- **修改** `pages/chat_page.py`：口型同步降频 + 可见性判断 + 拖动信号连接
- **修改** `native/main.py`：懒加载框架 + 拖动状态广播 + 禁用动画
- **修改** `pages/vrm_settings_page.py`：继承 LazyPageMixin 延迟创建
- **修改** `pages/settings_page.py`：配置加载延迟到 on_backend_ready

### 📝 文件变更
- **新增**: `widgets/lazy_page_mixin.py`, `widgets/async_json_worker.py`, `widgets/skeleton_container.py`
- **修改**: `native/main.py`, `widgets/perf_manager.py`, `widgets/live2d_widget.py`, `widgets/audio_visualizer.py`, `pages/chat_page.py`, `pages/settings_page.py`, `pages/vrm_settings_page.py`, `app/version.py`, `docs/VERSION.md`, `README.md`, `native/build.bat`, `resources/version_info.txt`

## 🟢 v1.11.23 (2026-06-02) ✅ STABLE

### 🔧 修复
- **[BUG-001] PageInitWorker 非主线程 UI 崩溃**：PageInitWorker 将 page.on_backend_ready() 放入 QThreadPool 执行，但 train_page/memory_page/settings_page 的 on_backend_ready() 中包含大量 Qt UI 操作（QComboBox.clear/addItem, QTreeWidget.takeChildren 等），PySide6 中从非主线程操作 UI 控件导致崩溃。修复：取消 PageInitWorker，改为 QTimer.singleShot 错峰调度到主线程（每个页面间隔 50ms）
- **[WARN-001] QRunnable setAutoDelete**：StatsResultWorker 的 setAutoDelete(True) 改为 setAutoDelete(False)，由调用方管理生命周期；_on_stats_ready/_on_stats_error 回调中手动释放 worker 引用

### 🏗️ 架构
- **删除** `PageInitWorker` 和 `_SignalBridge` 类（不再使用）
- **修改** `native/main.py`：QThreadPool 并行初始化 → QTimer.singleShot 错峰调度（所有页面 on_backend_ready() 都在主线程执行）
- **修改** `native/gugu_native/pages/memory_page.py`：StatsResultWorker 生命周期管理增强

### 📝 文件变更
- **修改**: `workers/init_workers.py` (删除 PageInitWorker/_SignalBridge, StatsResultWorker setAutoDelete=False)
- **修改**: `workers/__init__.py` (移除 PageInitWorker 导出)
- **修改**: `native/main.py` (QTimer.singleShot 错峰调度 + 删除 _on_page_init_done/_on_page_init_failed + 删除 _page_workers)
- **修改**: `pages/memory_page.py` (StatsResultWorker 生命周期管理)
- **修改**: `app/version.py`, `docs/VERSION.md`, `README.md`, `resources/generate_icons.py`, `widgets/update_manager.py` (版本号 1.11.22 → 1.11.23)

## 🟢 v1.11.22 (2026-06-02) ✅ STABLE

### ⚡ 性能
- **[P0-1] 后端初始化异步化**：AIVTuber() 构造从主线程移至 QThread（MoveToThread 模式），5-15s 主线程冻结 → 0ms（GUI 立即可交互/拖动）
- **[P0-2] 页面 on_backend_ready 并行化**：Train/Memory/ModelDL/Settings 4 个页面通过 QThreadPool + PageInitWorker 并行初始化，串行 3-8s → 并行 <2s
- **[P0-3] 增量 GC 分代定时器**：全量 gc.collect() 60s（100-500ms 暂停）→ gen0:5s / gen1:30s / gen2:120s（<5ms / <16ms / <50ms）
- **[P0-4] MemoryPage 异步刷新**：_refresh_stats() 从同步阻塞改为 StatsResultWorker 异步读取，主线程 0ms 阻塞
- **[P1-1] GIL 争抢缓解**：TTS 预热/ASR 预加载线程添加 time.sleep(0.01) 让出 GIL，降低后台线程对主线程的争抢
- **[P1-2] 统一异步任务框架**：新增 AsyncJobManager，借鉴 Calibre JobManager，统一管理后台任务（提交/追踪/取消/Signal 通知）
- **[P1-4] 启动进度展示增强**：BackendInitWorker.init_progress Signal 连接到 SplashDebugWindow.set_progress()，后端初始化进度实时更新

### 🏗️ 架构
- **新增** `native/gugu_native/workers/init_workers.py`：BackendInitWorker + PageInitWorker + StatsResultWorker
- **新增** `native/gugu_native/workers/async_job_manager.py`：AsyncJobManager 统一异步任务框架
- **修改** `native/gugu_native/widgets/perf_manager.py`：增量 GC + schedule_backend_init_async() + cleanup() 恢复 gc.enable()
- **修改** `native/main.py`：异步初始化流程 + 并行页面回调 + 启动进度展示 + 退出清理
- **修改** `native/gugu_native/pages/memory_page.py`：_refresh_stats() 异步化 + StatsResultWorker

### 🔧 修复
- **[GC] 退出时恢复自动 GC**：应用关闭时 gc.enable() + gc.collect(2)，防止影响其他代码
- **[GC] force_cleanup() 改显式全量**：gc.collect() → gc.collect(2)

### 📝 文件变更
- **新增**: `workers/init_workers.py`, `workers/async_job_manager.py`
- **修改**: `workers/__init__.py`, `widgets/perf_manager.py`, `native/main.py`, `pages/memory_page.py`, `app/version.py`, `docs/VERSION.md`, `README.md`, `resources/generate_icons.py`, `widgets/update_manager.py`

## 🟢 v1.11.21 (2026-06-01) ✅ STABLE

### ⚡ 性能
- **[P0-1] VectorStore.search() NumPy 向量化**：余弦相似度从纯 Python 循环改为 NumPy 矩阵批量运算，500条×768维从~500ms降至~5ms（100x 加速），无 NumPy 时自动回退
- **[P0-2] VectorStore._is_duplicate() NumPy 优化**：去重检查改为 NumPy 批量计算，避免逐条 Python 循环
- **[P1-5] VectorStore 序列化改 NumPy 二进制**：向量数据保存为 vectors.npy（二进制），元数据保存为 vectors_meta.json，加载速度提升 10x+，自动兼容迁移旧 JSON 格式
- **[P2-8] Config 5 个 JSON 并行加载**：api_keys/llm/asr/tts/vision_preferences 从串行读取改为 ThreadPoolExecutor 并行读取，总 IO 时间降为 ~1/5

### 🔧 修复
- **[P1-3] _history_file CWD 路径修复**：`Path("./memory/state/chat_history.json").resolve()` 改为 `Path(PROJECT_DIR) / "memory" / "state" / "chat_history.json"`，不再依赖 CWD（防止 GPT-SoVITS os.chdir() 污染）
- **[P1-4] search_cache add 后失效**：add()/delete() 成功后清除搜索缓存，避免返回过时结果
- **[P1-6] _cosine_similarity 复用 norm 缓存**：签名扩展为 `_cosine_similarity(a, norm_a, b, norm_b=None)`，支持传入预计算的 norm_b
- **[P2-9] GPT-SoVITS os.chdir 改 save/restore**：删除模块级 `os.chdir()`，改为 `_lazy_init()` 中 try/finally 临时切换 + 恢复 CWD，不再永久污染进程工作目录

### 🐛 优化
- **[P2-7] ToolExecutor._BLOCKLIST 改类常量**：危险命令黑名单从方法内局部 set 改为类级 `frozenset` 常量，避免每次 can_execute() 重复创建
- **[P2-10] Embedding 模型后台预热**：MemorySystem 初始化后启动 daemon 线程预热 embedding 模型，避免首次对话延迟 5-10 秒

## 🟢 v1.11.20 (2026-05-31) ✅ STABLE

### 🔧 修复
- **[BUG-1] SplashDebugWindow.set_progress() 重复定义**：合并两个同名方法为一个，恢复 `QApplication.processEvents()` UI 强制刷新和 `_center_on_screen()` 窗口居中逻辑，启动画面进度更新不再卡顿
- **[ARCH-1] VisionWorker 破坏封装**：VisionManager 新增 `current_provider` / `has_provider` / `get_provider()` 三个公开接口，OCRWorker 和 VisionWorker 不再直接访问 `_current_provider` / `_providers` 私有属性
- **[ARCH-2] StreamChatWorker 双记忆检索**：删除 Worker 层的 `backend.memory.search()` 调用，统一由 LLM 内部 MemoryRAGInjector 处理记忆检索（消除 token 浪费和记忆重复注入）
- **[ARCH-3] LLM 重试无退避**：添加 2 秒分段延迟（每 0.5 秒检查 stop 标志）+ 最多重试 1 次，限流场景下不再立即重试
- **[MINOR-1] chat_page.py 重复注释**：删除重复的注释分隔线

### 📝 文件变更
- **修改**: `splash_debug_window.py` (合并 set_progress)、`app/vision/__init__.py` (+3 公开接口)、`vision_workers.py` (改用公开接口)、`chat_workers.py` (删记忆检索+加重试退避)、`chat_page.py` (删重复注释)
- **新增**: `docs/pr-fix-2025-05.md` (修复 PRD)、`docs/arch-fix-2025-05.md` (修复架构设计)

## 🟢 v1.11.19 (2026-05-31) ✅ STABLE

### 🔧 修复
- **[startup] start.bat 修复**：CMD 不再滞留——改用 `start /B` 后台启动，窗口闪即没
- **[startup] 跳过等待硬退出**：`QApplication.quit()` → `os._exit(0)`，点击跳过不再残留僵尸进程
- **[startup] 启动进度提示**：启动画面新增 6 阶段进度（加载界面→应用主题→语音引擎→AI引擎→语音合成→语音识别），SplashDebugWindow 新增 `set_progress()` 和 `mark_backend_ready()` 方法
- **[ux] 按钮图标重叠**：保存/检查更新按钮去掉 FluentIcon，改用 emoji（💾/🔄），文字不再与图标挤压
- **[startup] pydub FFmpeg 扫描加速**：`subprocess.check_output` 拦截补丁前置到 `main.py` 顶部（Qt 初始化前），ASR 导入从 10-20s → 0.06s
- **[theme] QSS `font-weight: 500` → `bold`**：Qt 不支持数值 font-weight，消除 "Could not parse stylesheet" 警告

### 📝 文件变更
- **修改**: `scripts/start.bat` (CMD 无滞留)、`main.py` (补丁前置+进度提示+惰加载)、`splash_debug_window.py` (硬退出+进度)、`app/asr/__init__.py` (ffmpeg 补丁)、`theme.py` (font-weight 修复)、`settings_page.py` (emoji 按钮)


## 🟢 v1.11.18 (2026-05-31) ✅ STABLE

### ⚡ 性能
- **[startup] ASR 模块导入提速 200x**：pydub（torchaudio 传递依赖）在 Windows 上用 `subprocess.check_output` 扫描系统 PATH 找 ffmpeg，每个子进程耗时 2-5s，累计 10-20s。新增 `subprocess.check_output` 拦截补丁，毫秒级跳过扫描，ASR 导入从 10-20s → 0.06s
- **[startup] 惰加载优化**：ChatPage + 7 个重量 Widget（TrayManager / VoiceManager / HotkeyManager / DesktopPet / AutoStartManager / UpdateManager / PerfManager）从模块级导入改为方法内按需导入，减少 ~3s 冷启动时间

### 🔧 修复
- **[ux] 设置页脏标记优化**：文字追加 "●" → 橙色边框（`PushButton[dirty="true"]`），不占文字空间无重叠
- **[theme] 全局 QLabel 透明背景**：解决 Qt QSS 继承丢失导致亮色主题下标签黑底

### 🧹 代码清理
- **[workers] 5 个 Worker 类拆分**：`StreamChatWorker / TTSWorker / ASRWorker / OCRWorker / VisionWorker` 从 chat_page.py（2401→2092 行）移至独立 `gugu_native/workers/` 包
- **[shared] 新建 utils.py 共享模块**：`show_info / show_warning / show_error / deferred_call` 统一封装修复重复代码
- **[dead] 删除 25 项冗余**：废弃 live2d_web_widget.py、4 个旧测试文件、14 个空日志、5 个空目录、29 个 TTS 临时 wav、rebuild_tts_engine() 死代码、sys/QMutex 未用导入
- **[path] 统一 PROJECT_DIR**：5 个 Widget 文件（tray / perf / update / hotkey / theme）的手动 `os.path.dirname(...)` 链式调用统一切换到 `from app.shared_config import PROJECT_DIR`
- **[imports] 清理冗余 sys.path**：chat_page / settings_page 的 `_LOCAL_PROJECT_DIR` + `sys.path.insert` 冗余代码移除
- **[models] 释放 130MB**：删除与 `app/web/static/assets/model/` 重复的 `VRM/Asmodeus_*.vrm` × 3
- **[mutex] 互斥锁重试**：进程被杀后 3 秒自动重试，避免启动卡死
- **[vision] RapidOCR 包名兼容 + MiMo is_available() 补全 + Provider 自动降级**
- **[voice] 实时语音 Worker 身份校验**：防止旧 worker 信号污染新流导致闪退

### 📝 文件变更
- **新建**: `gugu_native/workers/__init__.py`、`chat_workers.py`、`vision_workers.py`、`gugu_native/utils.py`、`gugu_native/widgets/screenshot_selector.py`
- **修改**: `app/main.py` (ffmpeg warning 抑制)、`app/asr/__init__.py` (subprocess 补丁 + 启动提速)、`app/vision/__init__.py` (RapidOCR 兼容 + MiMo 降级)、`native/main.py` (惰加载)、`gugu_native/theme.py` (QLabel 透明)、`chat_page.py` (Worker 提取)、`settings_page.py` (脏标记边框)、`tray_manager.py` / `perf_manager.py` / `update_manager.py` / `hotkey_manager.py` (PROJECT_DIR 统一)、`session_manager.py` (日志补全)、`model_download_page.py` (主题颜色)、`desktop_pet.py` (QMenu 主题)
- **删除**: `live2d_web_widget.py`、4 个旧测试文件、`VRM/Asmodeus_*.vrm` × 3


## 🟢 v1.11.17 (2026-05-29) ✅ STABLE

### 🔧 修复
- **[vision] RapidOCR 包名兼容**：`_get_engine()` 增加 `rapidocr_onnxruntime` 降级导入，OCR 不再"未识别到文字"
- **[vision] MiMoVisionProvider 补全 `is_available()`**：修复 `set_provider("mimo_vision")` 抛 `AttributeError` 导致视觉模块加载失败
- **[vision] OCR/Vision Worker 错误提示增强**：显示具体失败原因（Provider未配置/API不可用/OCR无文字等），而非静默失败
- **[theme] 全局 QLabel 透明背景**：全局 QSS 增加 `QLabel { background-color: transparent }` 规则，解决单个 widget `setStyleSheet` 后丢失背景继承导致黑底
- **[theme] model_download_page + desktop_pet 硬编码暗色清理**：所有 `#37b24d`、`#1a3a2a` 等替换为主题变量
- **[startup] 互斥锁重试机制**：进程被杀后 Windows 互斥锁有延迟清理，增加 3 秒重试避免启动卡死

### ✨ 新增
- **[ocr] 区域截图选择器**：替代全屏截图（`grabWindow(0)`），拖拽选择区域后 OCR，右键或 Esc 取消。新建 `ScreenshotSelector` 组件（半透明遮罩 + 紫色选框 + 尺寸提示）
- **[voice] 实时语音闪退修复**：`_on_stream_finished` 增加 worker 身份校验（`self.sender() is self._worker`），防止旧 worker 信号污染新流状态导致崩溃

### 📝 文件变更
- **修改**: `app/vision/__init__.py`（RapidOCR兼容 + is_available补全）
- **修改**: `native/gugu_native/pages/chat_page.py`（worker身份校验 + OCR/Vision错误提示增强）
- **修改**: `native/gugu_native/pages/model_download_page.py`（硬编码颜色→主题变量）


## 🟢 v1.11.16 (2026-05-28) ✅ STABLE

### ✨ 新增
- **[startup] CMD 隐藏 + 启动画面内嵌运行调试窗口**：`start.bat` 改用 `pythonw.exe` 无窗口启动，全程无 CMD 黑窗口。新建 `SplashDebugWindow` 替代 `QSplashScreen`，启动画面内嵌实时运行调试窗口（stdout 重定向），日志行自动着色。启动完成后自动隐藏，可从系统托盘菜单重新打开。支持 Escape 关闭、10s 自动显示跳过按钮、错误时显示完整 traceback
- **[theme] 主题系统 v5 多维度升级**：10 个主题各具独立风格——圆角(rounded/soft/sharp)、间距(compact/comfortable/spacious)、阴影(flat/material/neumorphic/glow)、字体(msyh/inter/jetbrains)、控件(solid/outline/ghost)。新增 vscode_dark 和 discord 两个展示型主题
- **[theme] QSS v5 动态生成器**：`build_global_qss_v5()` 使用 `%(var)s` 模板变量，`apply_theme()` 自动重刷全局样式。ThemeManager 新增 `get_theme()` 返回 `AppTheme`
- **[theme] 主题选择器升级**：色卡底部显示风格标签（如"圆润 · 舒适 · 霓虹"），选中态增加 accent 色 √ 标记。新增"恢复默认主题"按钮
- **[scripts] 新增 start_debug.bat**：保留原始 CMD 启动模式供开发者调试

### 🔧 修复
- **[ux] 设置页统一保存**：4 个独立"保存 XX 配置"按钮 → 1 个"保存所有设置"按钮 + 脏标记（●），防止用户丢失修改
- **[ux] API Key 显隐切换**：`FluentIcon.VIEW` ↔ `FluentIcon.HIDE` 状态反馈
- **[ux] 发送/停止按钮同位置变色**：蓝→红平滑切换（参考 ChatGPT），消除 setVisible() 抖动
- **[ux] 录音/实时语音按钮区分**：🎤"录音" vs 🎙"实时对话"，不同图标和标签
- **[ux] 清空按钮加间距+警告色**：12px 间距 + hover 变红防误触
- **[ux] TTS 卡片背景统一**：`sidebar_bg` → `card_bg`
- **[ux] Live2D 工具栏 3→1 行**：模型切换 + 导入按钮 + 宠物按钮合并到一行，省 ~60px
- **[ux] 宠物按钮归位**：从 TTS 工具栏移到 Live2D 工具栏
- **[ux] VRM 变体标签清晰化**："AU"→"默认" + emoji 配中文
- **[ux] 训练页改进**：日志字体 9→11px、工作流引导提示、录音时长 3~30s 可调、上传默认目录、状态轮询 2s→1s
- **[ux] 记忆页改进**：统计卡片缩小、语义默认展开、重整按钮 loading 动画、详情面板主题刷新、不可见时暂停刷新
- **[ux] 聊天卡片内边距 3→8px、输入框快捷键提示、最小窗口 1100→960**
- **[ux] 重置项目按钮警告色 + DELETE 图标**
- **[ux] QProgressBar `font-size:0px` hack → `color:transparent`**
- **[theme] memory_page refresh_theme() 致命 Bug：缺少 `c=get_colors()` 导致切主题崩溃**
- **[theme] model_download_page 未注册主题回调，硬件状态使用硬编码暗色值**
- **[theme] settings_page reset_theme_btn 未保存为属性，无法跟随主题刷新**
- **[bug] Live2D 导入栏 hex+alpha 语法错误**：`#7c3aed22` → `rgba(124,58,237,0.13)`（QSS 不支持 8 位 hex）
- **[bug] FluentIcon.HEADSET 不存在**：改用 emoji 🎙 图标

### 📝 文件变更
- **新建**: `native/gugu_native/themes/style_types.py` (6 dataclass)、`themes/presets/vscode_dark.py`、`themes/presets/discord.py`
- **新建**: `native/gugu_native/widgets/splash_debug_window.py`
- **新建**: `scripts/start_debug.bat`
- **修改**: `native/main.py`、`native/gugu_native/theme.py`、`themes/definitions.py`、`themes/manager.py`、`themes/presets/__init__.py`、8 个预设主题、`theme_selector.py`、`theme_card.py`、`tray_manager.py`、`chat_page.py`、`settings_page.py`、`train_page.py`、`memory_page.py`、`model_download_page.py`、`scripts/start.bat`
- **修改**: `app/version.py`、`docs/VERSION.md`、`README.md`


## 🟢 v1.11.15 (2026-05-27) ✅ STABLE

### 🔧 修复
- **[chat] TTS 音频播放打断**：句子间存在竞态条件，新句子可能在前一句未播完时开始播放。统一播放调度到 `_try_play_next()` 方法，消除 `_on_tts_audio_ready` 和 `_on_playback_state_changed` 中的重复释放逻辑
- **[settings] TTS 引擎重建冗余**：`_TTSRebuildWorker` 重建后又调用 `set_voice()/set_project()`，导致 GPT-SoVITS 的 pipeline 被重置。移除冗余调用，rebuild 时已从更新后的 config 创建正确配置的引擎
- **[bat] start.bat UTF-8 BOM 问题**：每次编辑后都会出现 BOM（`锘緻echo off`）。改用 Python 以 ASCII 编码写入，彻底消除 BOM
- **[bat] 启动输出美化**：模块化分步输出 [1/4]~[4/4]，用户可直观了解启动进度
- **[perf] 内存清理阈值调整**：GPT-SoVITS 本地推理模式下内存自然占用 ~4.2GB，原阈值 4000MB 频繁误触发清理。提高至 WARNING=3500MB / CRITICAL=5500MB

### 🔧 修复（v1.11.14 遗留）
- **[settings] LLM 模型持久化 Bug**：`on_backend_ready` 使用 `Config.get()` 扁平查找获取嵌套字典返回空值，导致后端就绪时覆盖用户保存的 LLM 配置。改用 `backend.config.config`（原始 dict）访问，并统一所有模块优先使用偏好文件
- **[settings] TTS 音色持久化**：`_save_tts_config` 只保存 MiMo 的 `provider_configs`，Edge TTS / GPT-SoVITS 的音色不保存。改为所有引擎都保存音色到 `provider_configs`，并合并保留其他引擎的配置
- **[settings] TTS 音色恢复**：GPT-SoVITS 音色列表异步加载完成前 `_load_tts_prefs` 无法设置音色。新增 `_pending_tts_voice` 机制和 `_restore_tts_voice_after_populate` 方法，在异步加载回调中恢复音色
- **[config] TTS 偏好恢复遗漏 voice 字段**：`Config._load()` 从 `tts_preferences.json` 恢复时只恢复了 `base_url` 和 `model`，遗漏了 `voice` 和 `project`。已补全

## 🟢 v1.11.13 (2026-05-27) ✅ STABLE
- **[scripts] 移除 start.bat 中的 MiMo 配置菜单**：配置应在 GUI 内完成，不需要 CMD 交互
- **[scripts] mimo_config.py 不再由 start.bat 调用**：保留文件供高级用户命令行使用

## 🟢 v1.11.12 (2026-05-27) ✅ STABLE

**新增 start.bat MiMo 配置菜单 + 偏好持久化**

### ✨ 新增
- **[scripts] 新增 MiMo Token Plan 配置菜单**：`start.bat` 启动时显示交互式菜单，可选择 MiMo 模块组合（LLM/TTS/ASR/Vision），无需手动修改 config.yaml
- **[scripts] 新增 `scripts/mimo_config.py`**：MiMo 配置写入器，根据用户选择写入偏好文件
- **[config] 新增 ASR/TTS/Vision 偏好持久化**：`Config._load()` 现在也读取 `asr_preferences.json`、`tts_preferences.json`、`vision_preferences.json`，与 LLM 偏好机制一致

### 🔧 修复
- **[config] MiMo API Key 分发**：`api_keys.json` 中的 `mimo` key 现在会自动分发到 `asr.mimo`、`tts.mimo`、`vision.mimo_vision`，不再需要单独配置
- **[config] config.yaml 恢复默认值**：MiMo 相关 base_url 恢复为 `api.xiaomimimo.com`，由偏好文件覆盖为 `token-plan-cn.xiaomimimo.com`

### 🐛 优化
- **[llm] OpenAILLM 初始化日志增强**：打印 base_url 以便调试认证头问题

## 🟢 v1.11.11 (2026-05-27) ✅ STABLE

**修复 MiMo LLM 401 Unauthorized 认证头错误**

### 🔧 修复
- **[llm] 修复 MiMo LLM 认证头错误**：`OpenAILLM.__init__` 中硬编码 `Authorization: Bearer` 头，导致 MiMo API 返回 401 Unauthorized。现根据 base_url 动态选择：包含 `xiaomimimo.com` 时使用 `api-key` 头，其他 OpenAI 兼容提供商使用 `Authorization: Bearer` 头。

## 🟢 v1.11.10 (2026-05-27) ✅ STABLE

**修复 settings_page.py 中的 FluentIcon.VIEW_OFF 错误**

### 🔧 修复
- **[settings] 修复 FluentIcon.VIEW_OFF 不存在错误**：`settings_page.py` 第388行使用不存在的 `FluentIcon.VIEW_OFF`，导致启动时 `AttributeError`。已替换为 `FluentIcon.VIEW`，图标状态切换逻辑保持不变。

## 🟢 v1.11.9 (2026-05-27) ✅ STABLE

**新增小米 MiMo 云端全链路接入（ASR + TTS + Vision）**

### ✨ 新功能
- **[tts] MiMo TTS 云端引擎**：新增 `MimoTTS` 引擎，通过 `/v1/chat/completions` + `audio` 参数调用
  - 支持三种模型：`mimo-v2.5-tts`（预置音色）/ `mimo-v2.5-tts-voicedesign`（音色设计）/ `mimo-v2.5-tts-voiceclone`（音色复刻）
  - 支持预置音色：冰糖、茉莉、苏打、白桦、Mia、Chloe、Milo、Dean
  - 支持风格指令（通过 user 角色消息控制语气/语速/情感）
- **[asr] MiMo ASR 云端引擎**：新增 `MimoASR` 引擎，通过 `input_audio` 内容块调用 MiMo 音频理解
  - 支持 WAV/MP3/FLAC/M4A/OGG 格式
  - 自动从 `llm.mimo.api_key` 读取密钥
- **[vision] MiMo Vision 云端引擎**：新增 `MimoVisionProvider`，通过 `image_url` 内容块调用 MiMo 视觉理解
  - 支持 `mimo-v2.5` 和 `mimo-v2.5-pro` 模型
  - 自动 JPEG 压缩 + Base64 编码

### 📝 文档
- **[config] 新增**：`asr.mimo`、`tts.mimo`、`vision.mimo_vision` 配置节
- **[version] v1.11.9**


## 🟢 v1.11.8 (2026-05-26) ✅ STABLE

**启动性能优化（冷启动时间 6-8s → 2-3s）**

### ⚡ 性能
- **[startup] PySide6 检测加速**：`start.bat` 用 `pip show` 替代 `import QWebEngineView`，检查耗时 3-5s → 50ms
- **[startup] 模块懒导入**：非首屏页面（Settings/Train/Memory/Model/VRM）改为函数内延迟导入，省 ~1.5s
- **[version] v1.11.8**


## 🟢 v1.11.7 (2026-05-26) ✅ STABLE

**代码质量优化第二波（纯重构 + 性能提升）**

### 🔄 重构
- **[main] 模块抽取**：游戏风格日志函数（LogStyle + 15 个 game_* 函数）移至新文件 `app/log_style.py`

### ⚡ 性能
- **[memory] 缓存扩容**：embedding 缓存从 200 扩到 1000 条，提高重复查询命中率

### 🔧 修复
- **[web] 深拷贝**：`_get_tts_for_client` 中 Config 浅拷贝改为 `copy.deepcopy`，防止子字典被意外修改
- **[tools] 温度参数**：`fc_executor` 的 temperature 改为可配置参数（默认 0.7），不再硬编码

### 📝 文档
- **[version] v1.11.7**


## 🟢 v1.11.6 (2026-05-26) ✅ STABLE

**代码质量优化（纯重构，零行为变更）**

### 🔄 重构
- **[llm] 去重**：合并 `_strip_thinking` + `_parse_action` 7 处重复调用为统一 `_clean_response` 函数
- **[config] 加速**：`Config.get()` 改为惰性预展开扁平字典，热路径 O(n)→O(1)
- **[web] 清理**：`TTSFactory` 导入移到模块顶部，消除 `_get_tts_for_client` 内 2 处重复 import

### 📝 文档
- **[version] v1.11.6**


## 🟢 v1.11.5 (2026-05-26) ✅ STABLE

**PyInstaller 打包修复**

### 🔧 修复
- **[build] jaraco 兼容**：适配 setuptools 81，修复 PyInstaller 打包依赖冲突
- **[version] v1.11.5**


## 🟢 v1.11.4 (2026-05-25) ✅ STABLE

**打包优化 + 启动性能**

### ⚡ 性能
- **[core] 启动加速**：优化懒加载初始化流程，缩短冷启动时间
- **[build] 打包成功**：PyInstaller 打包为 65MB 单 EXE 启动器
- **[version] v1.11.4**


## 🟢 v1.11.3 (2026-05-25) ✅ STABLE

**修复 TTS 播放不完整/交替/中断**

### 🔧 修复
- **[tts] 统一播放队列**：主动说话和流式 TTS 走同一队列，不再互相打断
- **[tts] 修复 seq=0 插队**：主动说话音频改为排队，不中断当前播放
- **[tts] 排序缓冲区释放**：播放结束后自动释放 _tts_pending 中的连续序号
- **[tts] 去重**：同一音频不会重复入队
- **[version] v1.11.3**

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

