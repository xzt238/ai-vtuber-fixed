# 🔧 常见修改操作手册 (MODIFICATION_GUIDE)

> **最后更新**: 2026-05-07 | **当前版本**: v1.9.90

本文档提供常见多文件修改的分步操作指南。每个操作对应一个唯一编号，与 `CHANGE_IMPACT_MAP.md`（列出*哪些文件需要改*）互补——本手册告诉你*具体怎么改*。

---

## M-001: 版本号升级

每次发版时执行。

| 步骤 | 操作 | 文件 |
|------|------|------|
| 1 | 修改 `VERSION` 字符串 | `app/version.py` |
| 2 | 在顶部添加新版本条目 | `docs/VERSION.md` |
| 3 | 更新版本徽章中的版本号 | 根目录 `README.md` |
| 4 | 更新构建脚本中的版本号 | `native/build.bat` |
| 5 | 更新 Windows 版本信息 | `native/gugu_native/resources/version_info.txt` |
| 6 | 更新启动画面版本号 | `native/gugu_native/resources/generate_icons.py` |
| 7 | 更新 fallback 版本号 | `native/main.py` L85 |
| 8 | 更新 fallback 版本号 | `native/gugu_native/widgets/update_manager.py` L180 |

**验证**:
```bash
grep -rn "旧版本号" --include="*.py" --include="*.html" --include="*.bat" --include="*.txt" app/ native/ launcher/
```
应只剩注释/文档字符串中的旧版本号引用。

---

## M-002: 新增 LLM 提供商

| 步骤 | 操作 | 文件 |
|------|------|------|
| 1 | 添加 `PROVIDER_CONFIG` 条目 | `app/shared_config.py` |
| 2 | 如果 API 格式不同于 OpenAI，创建新的 Provider 类 | `app/llm/__init__.py` |
| 3 | 同步 JS 提供商配置对象 | `app/web/static/index.html` → `_providerConfig` |
| 4 | 验证 settings_page 自动加载 | `native/gugu_native/pages/settings_page.py`（自动从 shared_config 导入） |
| 5 | 更新开发者指南 | `docs/guides/DEVGUIDE.md` → LLM 模块章节 |

**注意**: 步骤 3 必须手动完成！JS 无法 import Python，详见 `CHANGE_IMPACT_MAP.md` 第 2 节。

---

## M-003: 新增 TTS 引擎

| 步骤 | 操作 | 文件 |
|------|------|------|
| 1 | 创建引擎类，继承 `TTSBase` | `app/tts/new_engine.py` |
| 2 | 在工厂中注册 | `app/tts/__init__.py` → `TTS_FACTORY` |
| 3 | 添加语音选项 UI | `app/web/static/index.html` → `voiceOptions` |
| 4 | 添加 TTS 下拉选项 | `native/gugu_native/pages/settings_page.py` |
| 5 | 如果有语音列表，添加到共享配置 | `app/shared_config.py` |
| 6 | 更新开发者指南 | `docs/guides/DEVGUIDE.md` → TTS 模块章节 |

**TTSBase 子类必须实现的接口**:
- `speak(text, ...)` — 同步合成语音
- `stop()` — 停止当前播放
- `_is_playing` — 通过 property 使用 `_cls_is_playing` 类变量

---

## M-004: 新增原生桌面页面

| 步骤 | 操作 | 文件 |
|------|------|------|
| 1 | 创建页面类，继承 `QFrame` 或 `FluentWindow` 页面基类 | `native/gugu_native/pages/new_page.py` |
| 2 | 在主窗口注册页面 | `native/main.py` → `_create_pages()` |
| 3 | 添加页面样式（如需要） | `native/gugu_native/theme.py` |
| 4 | 更新架构文档 | `docs/guides/NATIVE_DESKTOP.md` → 页面章节 |

**页面注册模板**:
```python
# native/main.py → _create_pages()
from gugu_native.pages.new_page import NewPage
self.new_page = NewPage(self)
self.addSubInterface(self.new_page, FluentIcon.NEW, "新页面")
```

---

## M-005: 新增原生桌面组件

| 步骤 | 操作 | 文件 |
|------|------|------|
| 1 | 创建组件类 | `native/gugu_native/widgets/new_widget.py` |
| 2 | 在相关页面中 import 并使用 | 对应的 page 文件 |
| 3 | 更新架构文档 | `docs/guides/NATIVE_DESKTOP.md` → 组件章节 |

---

## M-006: 修改端口号

| 步骤 | 操作 | 文件 |
|------|------|------|
| 1 | 修改 HTTP/WS 端口 | `app/config.yaml` → `web.port` / `web.ws_port` |
| 2 | 修改启动器端口 | `launcher/launcher.py` → `BACKEND_PORT` / `BACKEND_WS_PORT` |
| 3 | 修改双模兼容端口 | `native/gugu_native/widgets/dual_mode_compat.py` → `WEBUI_HTTP_PORT` / `WEBUI_WS_PORT` |
| 4 | 修改 CLI 默认端口 | `app/main.py` → 默认参数 |
| 5 | 修改 WebSocket 服务端口 | `app/web/__init__.py` → 端口定义 |

**参见**: `CHANGE_IMPACT_MAP.md` 第 6 节

---

## M-007: 修改共享配置 (shared_config.py)

| 步骤 | 操作 | 文件 |
|------|------|------|
| 1 | 修改配置内容 | `app/shared_config.py` |
| 2 | 检查是否需要同步到 JS | `app/web/static/index.html` → 对应的 JS 变量 |
| 3 | 如果修改了 Mutex 名称，检查双模兼容 | `native/gugu_native/widgets/dual_mode_compat.py` |

**需要手动同步到 JS 的数据集**:
- `PROVIDER_CONFIG` → `_providerConfig`
- `EDGE_VOICES` → `voiceOptions.edge`
- `EXPRESSION_KEYWORDS` → `expressionKeywords`
- `EXPRESSION_MAP` → `expressionMap`

---

## M-008: 构建与发布

| 步骤 | 操作 |
|------|------|
| 1 | 执行版本号升级（M-001） |
| 2 | 执行 `CHANGE_IMPACT_MAP.md` 发布检查清单所有项目 |
| 3 | 构建 WebUI 启动器: `cd launcher && py -3.11 -m PyInstaller launcher.spec --clean --noconfirm` |
| 4 | 构建原生桌面: `cd native && build.bat` |
| 5 | 测试三种模式是否正常运行 |
| 6 | Git: `git add . && git commit -m "vX.Y.Z: 描述" && git tag vX.Y.Z && git push && git push --tags` |

---

## M-009: 添加新工具 (Function Calling)

| 步骤 | 操作 | 文件 |
|------|------|------|
| 1 | 创建工具类，继承 `BaseTool` | `app/tools/` 下新建文件 |
| 2 | 在工具工厂注册 | `app/tools/__init__.py` → `ToolFactory` |
| 3 | 在 FC 提示词中描述工具用途 | `app/llm/prompts.py` 或对应的 system prompt |
| 4 | 更新开发者指南 | `docs/guides/DEVGUIDE.md` → 工具章节 |

---

## M-010: 文档系统变更

| 步骤 | 操作 | 文件 |
|------|------|------|
| 1 | 创建/修改/归档文档 | `docs/` 对应子目录 |
| 2 | 更新导航中心 | `docs/README.md` |
| 3 | 如果改变了目录结构，更新元文档 | `docs/DOCS_SYSTEM.md` |
| 4 | 确认代码引用的文档路径仍然有效 | `app/version.py`, `app/shared_config.py`, `launcher/launcher.py` |
