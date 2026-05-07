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

