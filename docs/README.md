# 📚 咕咕嘎嘎 AI-VTuber 文档中心

> **最后更新**: 2026-05-07 | **当前版本**: v1.9.90 | **文档总数**: 17

欢迎来到项目文档中心！所有文档按功能分类，快速找到你需要的内容。

---

## 🧭 快速查找

| 我想… | 去看 |
|--------|------|
| 了解项目架构和模块 | [guides/DEVGUIDE.md](guides/DEVGUIDE.md) |
| 修改代码前检查影响范围 | [CHANGE_IMPACT_MAP.md](CHANGE_IMPACT_MAP.md) |
| 知道怎么改（分步指南） | [MODIFICATION_GUIDE.md](MODIFICATION_GUIDE.md) |
| 查看已知 Bug 和技术债务 | [KNOWN_ISSUES.md](KNOWN_ISSUES.md) |
| 开始贡献代码 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 了解文档系统如何维护 | [DOCS_SYSTEM.md](DOCS_SYSTEM.md) |
| 查看版本变更记录 | [VERSION.md](VERSION.md) |
| 构建和打包项目 | [guides/BUILD.md](guides/BUILD.md) |
| 了解原生桌面架构 | [guides/NATIVE_DESKTOP.md](guides/NATIVE_DESKTOP.md) |
| 查看竞品差距 | [reference/COMPETITIVE_GAP_ANALYSIS.md](reference/COMPETITIVE_GAP_ANALYSIS.md) |

---

## 📂 文档目录

### 顶层文档

| 文档 | 说明 | 更新频率 |
|------|------|----------|
| [CHANGE_IMPACT_MAP.md](CHANGE_IMPACT_MAP.md) | 修改影响地图 — 改一处需同步 N 处的完整依赖关系 | 新增跨文件依赖时 |
| [KNOWN_ISSUES.md](KNOWN_ISSUES.md) | 已知问题 & 技术债务 — 含 ID/严重度/状态/变通方案 | 发现/修复问题时 |
| [MODIFICATION_GUIDE.md](MODIFICATION_GUIDE.md) | 常见修改操作手册 — 版本升级、新增模块、端口修改等分步指南 | 新增操作类型时 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献者指南 — 代码风格、提交前检查清单、PR 流程 | 流程变更时 |
| [DOCS_SYSTEM.md](DOCS_SYSTEM.md) | 文档系统元文档 — 目录结构、更新触发条件、文档生命周期 | 目录结构变更时 |
| [VERSION.md](VERSION.md) | 版本变更记录（v1.9.81+） | 每次发版 |

### guides/ — 操作指南

| 文档 | 说明 | 更新频率 |
|------|------|----------|
| [guides/DEVGUIDE.md](guides/DEVGUIDE.md) | 开发者指南 — 架构、模块详解、开发规范、调试技巧 | 架构变更时 |
| [guides/BUILD.md](guides/BUILD.md) | 构建打包指南 — WebUI / 桌面 / 原生 / 安装器 | 构建流程变更时 |
| [guides/NATIVE_DESKTOP.md](guides/NATIVE_DESKTOP.md) | 原生桌面架构 — 页面、组件、后端交互、主题系统 | 原生桌面变更时 |

### reference/ — 参考分析

| 文档 | 说明 | 更新频率 |
|------|------|----------|
| [reference/COMPETITIVE_GAP_ANALYSIS.md](reference/COMPETITIVE_GAP_ANALYSIS.md) | 竞品差距分析 — 7 个竞品的功能矩阵对比 | 季度 |
| [reference/GAP_DETAILED_ANALYSIS.md](reference/GAP_DETAILED_ANALYSIS.md) | 详细优先级分析 — AI 陪伴定位的差距和路线图 | 路线图调整时 |
| [reference/CHAT_UX_COMPETITIVE_ANALYSIS.md](reference/CHAT_UX_COMPETITIVE_ANALYSIS.md) | 聊天 UX 竞品分析 — 优化后的 UX 评分和实现细节 | UX 大改版时 |

### archive/ — 历史归档

| 文档 | 说明 | 归档原因 |
|------|------|----------|
| [archive/VERSION_ARCHIVE.md](archive/VERSION_ARCHIVE.md) | v1.9.81 之前的版本记录 | 拆分到归档以减小主文件体积 |
| [archive/feasibility_native_desktop.md](archive/feasibility_native_desktop.md) | 原生桌面可行性研究 | 所有 5 个阶段已执行完毕 |
| [archive/feasibility_tool_system_upgrade.md](archive/feasibility_tool_system_upgrade.md) | 工具系统升级可行性 | Phase 1 已完成 |
| [archive/CHAT_UX_COMPETITIVE_ANALYSIS_V1.md](archive/CHAT_UX_COMPETITIVE_ANALYSIS_V1.md) | 聊天 UX 分析 V1 | 已被 V2 取代 |

---

## ⚠️ 重要提醒

### 修改代码前必读
1. **查阅修改影响地图**: [CHANGE_IMPACT_MAP.md](CHANGE_IMPACT_MAP.md) — 确认修改不涉及跨文件依赖
2. **遵循操作手册**: [MODIFICATION_GUIDE.md](MODIFICATION_GUIDE.md) — 常见修改的分步指南
3. **JS-Python 同步**: 修改 `app/shared_config.py` 后必须手动同步 `app/web/static/index.html`

### 版本发布前必做
1. 执行 [MODIFICATION_GUIDE.md → M-001](MODIFICATION_GUIDE.md) 版本号升级
2. 执行 [CHANGE_IMPACT_MAP.md](CHANGE_IMPACT_MAP.md) 发布检查清单
3. 在 [VERSION.md](VERSION.md) 添加版本记录

---

## 📊 文档统计

| 类别 | 数量 |
|------|------|
| 顶层文档 | 6 |
| 操作指南 | 3 |
| 参考分析 | 3 |
| 历史归档 | 4 |
| **总计** | **16** |

---

## 🔧 文档维护

如需新增、更新或归档文档，请遵循 [DOCS_SYSTEM.md](DOCS_SYSTEM.md) 中定义的文档生命周期。
