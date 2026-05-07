# 🤝 贡献者指南 (CONTRIBUTING)

> **最后更新**: 2026-05-07 | **当前版本**: v1.9.90

欢迎为「咕咕嘎嘎 AI-VTuber」做贡献！本文档帮助你快速上手。

---

## 1. 快速开始

1. **克隆仓库**，运行 `scripts/setup.bat` 安装依赖
2. **阅读架构概览**: `docs/guides/DEVGUIDE.md`
3. **阅读修改影响地图**: `docs/CHANGE_IMPACT_MAP.md` — 修改代码前必读
4. **了解已知问题**: `docs/KNOWN_ISSUES.md` — 避免重复报告

---

## 2. 代码风格

### Python
- 遵循 PEP 8
- 鼓励使用类型提示（type hints）
- 函数/类必须有 docstring
- 使用 f-string 而非 `%` 或 `.format()`

### 原生桌面 (native/)
- 不硬编码颜色，使用 `theme.py` 中的 `get_colors()` 获取主题色
- 不硬编码版本号，使用 `from app.version import VERSION`
- 共享配置从 `app/shared_config.py` 导入，不在本地重复定义
- Qt 信号连接前先 disconnect 旧连接，避免信号泄漏

### Web UI (app/web/)
- JS 变量与 Python `shared_config.py` 保持同步
- 修改 `shared_config.py` 后检查 `index.html` 中对应的 JS 变量

### 通用规则
- 版本号只从 `app/version.py` 读取
- 端口号当前硬编码在 5 处（待统一），修改时按 `MODIFICATION_GUIDE.md` M-006 操作
- 跨文件共享数据统一放在 `app/shared_config.py`

---

## 3. 提交前检查清单

每次提交代码前，确认以下事项：

- [ ] `docs/VERSION.md` 已添加变更描述
- [ ] 已查阅 `CHANGE_IMPACT_MAP.md`，确认修改不涉及跨文件依赖
- [ ] 如果涉及跨文件依赖，已同步更新所有相关文件
- [ ] 如果发现了新 Bug，已添加到 `KNOWN_ISSUES.md`
- [ ] 如果新增了跨文件依赖，已更新 `CHANGE_IMPACT_MAP.md`
- [ ] 三种模式（WebUI / pywebview 桌面 / PySide6 原生）均能正常运行
- [ ] 如果修改了共享配置，已同步 `index.html` 中的 JS 变量

---

## 4. PR 流程

1. **Fork** 仓库
2. 创建特性分支: `git checkout -b feature/描述`
3. 提交修改，一个逻辑变更一个 commit
4. PR 描述中包含:
   - 变更目的
   - 影响范围（参考 `CHANGE_IMPACT_MAP.md`）
   - `VERSION.md` 条目
5. 等待审核

---

## 5. 文档更新义务

每个代码变更都应有对应的文档更新：

| 变更类型 | 需要更新的文档 |
|----------|---------------|
| 新增功能 | `VERSION.md` + `DEVGUIDE.md`（如涉及架构） |
| 修复 Bug | `VERSION.md` + `KNOWN_ISSUES.md`（标记已解决） |
| 新增跨文件依赖 | `CHANGE_IMPACT_MAP.md` + `MODIFICATION_GUIDE.md` |
| 重构 | `VERSION.md` + 受影响的架构文档 |

文档维护详细规则见 `docs/DOCS_SYSTEM.md`。

---

## 6. 常见操作快速参考

| 我想… | 参见 |
|--------|------|
| 升级版本号 | `MODIFICATION_GUIDE.md` → M-001 |
| 添加 LLM 提供商 | `MODIFICATION_GUIDE.md` → M-002 |
| 添加 TTS 引擎 | `MODIFICATION_GUIDE.md` → M-003 |
| 添加原生页面 | `MODIFICATION_GUIDE.md` → M-004 |
| 修改端口 | `MODIFICATION_GUIDE.md` → M-006 |
| 构建发布 | `MODIFICATION_GUIDE.md` → M-008 |
| 了解修改影响 | `CHANGE_IMPACT_MAP.md` |
| 查看已知问题 | `KNOWN_ISSUES.md` |
