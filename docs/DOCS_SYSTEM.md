# 📐 文档系统指南 (DOCS_SYSTEM)

> **最后更新**: 2026-05-07 | **当前版本**: v1.9.90

本文档是「咕咕嘎嘎 AI-VTuber」文档系统的**元文档**——它解释文档系统如何运作，以及如何维护文档自身。

---

## 1. 目录结构

```
docs/
├── README.md                    # 🧭 导航中心 — 所有文档的入口和索引
├── DOCS_SYSTEM.md               # 📐 本文档 — 文档系统的元文档
├── CHANGE_IMPACT_MAP.md         # 🗺️ 修改影响地图 — 改一处需同步 N 处的依赖关系
├── KNOWN_ISSUES.md              # 🐛 已知问题 & 技术债务
├── MODIFICATION_GUIDE.md        # 🔧 常见修改操作手册 — 分步指南
├── CONTRIBUTING.md              # 🤝 贡献者指南
├── VERSION.md                   # 📋 版本变更记录（v1.9.81+）
│
├── guides/                      # 📖 操作指南
│   ├── DEVGUIDE.md              # 开发者指南 — 架构、模块、开发规范
│   ├── BUILD.md                 # 构建打包指南
│   └── NATIVE_DESKTOP.md        # 原生桌面应用架构
│
├── reference/                   # 📊 参考分析
│   ├── COMPETITIVE_GAP_ANALYSIS.md  # 竞品差距分析
│   ├── GAP_DETAILED_ANALYSIS.md     # 详细优先级分析
│   └── CHAT_UX_COMPETITIVE_ANALYSIS.md  # 聊天 UX 竞品分析
│
└── archive/                     # 📦 历史归档
    ├── VERSION_ARCHIVE.md       # v1.9.81 之前的版本记录
    ├── feasibility_native_desktop.md  # 原生桌面可行性研究（已执行完毕）
    ├── feasibility_tool_system_upgrade.md  # 工具系统升级可行性（Phase 1 已完成）
    └── CHAT_UX_COMPETITIVE_ANALYSIS_V1.md  # UX 分析 V1（已被 V2 取代）
```

---

## 2. 何时更新哪些文档

| 触发事件 | 需要更新的文档 |
|----------|---------------|
| **新增功能** | `VERSION.md` 添加条目、`DEVGUIDE.md` 相关章节、如果涉及跨文件依赖则更新 `CHANGE_IMPACT_MAP.md` |
| **修复 Bug** | `VERSION.md` 添加条目、`KNOWN_ISSUES.md` 标记为已解决或删除 |
| **发现新问题** | `KNOWN_ISSUES.md` 添加新条目 |
| **新增跨文件依赖** | `CHANGE_IMPACT_MAP.md` 添加新类别、`MODIFICATION_GUIDE.md` 添加操作指南 |
| **版本发布** | `VERSION.md` 添加条目、根 `README.md` 版本徽章、超过 10 个版本时考虑将旧版本移入 `archive/VERSION_ARCHIVE.md` |
| **架构变更** | `DEVGUIDE.md` 更新架构章节、如涉及原生桌面则同步 `NATIVE_DESKTOP.md` |
| **新增构建/打包方式** | `BUILD.md` 更新 |
| **竞品分析更新** | `reference/` 下的分析文档 |
| **文档结构变更** | 本文档 (`DOCS_SYSTEM.md`) 和 `README.md` 导航 |

---

## 3. 文档生命周期

### 创建 (CREATE)
- 新文档放入对应的子目录：
  - 操作指南 → `guides/`
  - 参考分析 → `reference/`
- 在文档头部添加标题、版本号和最后更新日期
- 在 `README.md` 导航中心添加索引条目

### 更新 (UPDATE)
- 每次修改文档时，更新头部的「最后更新」日期
- 重大变更在 `VERSION.md` 中记录

### 归档 (ARCHIVE)
- 当文档被新文档完全取代时，移入 `archive/`
- 在归档文件头部添加归档说明和指向新文档的链接
- 在 `README.md` 导航中移除归档文档的条目

### 删除 (DELETE)
- 仅在文档确实无任何参考价值时删除（如过期的纯文本草稿）
- 删除前确认无其他文档或代码引用该文件

---

## 4. 命名规范

| 位置 | 命名风格 | 示例 |
|------|----------|------|
| 顶层 `docs/` | `UPPERCASE.md` | `VERSION.md`, `KNOWN_ISSUES.md` |
| `guides/` | `UPPERCASE.md` | `DEVGUIDE.md`, `BUILD.md` |
| `reference/` | `UPPERCASE.md` 或 `lowercase.md` | `COMPETITIVE_GAP_ANALYSIS.md`, `feasibility_*.md` |
| `archive/` | 与原始文件一致，必要时加后缀 | `CHAT_UX_COMPETITIVE_ANALYSIS_V1.md` |

**规则**：
- 活跃文档不使用版本后缀（V1/V2），被取代的版本归档时加后缀
- 文件名应能直接反映内容，避免模糊命名

---

## 5. 文档间关系图

```
README.md (入口)
  ├── DEVGUIDE.md (主参考)
  │     ├── 引用 CHANGE_IMPACT_MAP.md
  │     ├── 引用 KNOWN_ISSUES.md
  │     └── 引用 NATIVE_DESKTOP.md
  ├── CHANGE_IMPACT_MAP.md (修改依赖)
  │     └── 被 app/version.py, app/shared_config.py 代码注释引用
  ├── MODIFICATION_GUIDE.md (操作手册)
  │     └── 引用 CHANGE_IMPACT_MAP.md (互补)
  ├── KNOWN_ISSUES.md (问题清单)
  │     └── 引用 CHANGE_IMPACT_MAP.md
  ├── VERSION.md (变更记录)
  │     └── 被 launcher/launcher.py 运行时读取
  └── CONTRIBUTING.md (贡献指南)
        └── 引用以上所有文档
```

---

## 6. 自检机制

每次文档系统变更后，执行以下检查：

- [ ] `README.md` 导航表是否包含所有活跃文档？
- [ ] 新增文档是否已添加到对应的子目录？
- [ ] 归档文档是否已从导航中移除？
- [ ] 代码中引用的文档路径（`docs/CHANGE_IMPACT_MAP.md`、`docs/VERSION.md`）是否仍然有效？
- [ ] 各文档头部的「最后更新」日期是否已更新？
- [ ] 归档文件是否包含归档说明和指向新文档的链接？

---

## 7. 与代码的接口

以下代码文件引用了 `docs/` 中的文档路径，移动文件时**必须**保持这些路径有效：

| 代码文件 | 引用路径 | 用途 |
|----------|----------|------|
| `app/version.py` | `docs/CHANGE_IMPACT_MAP.md` | 注释中引用 |
| `app/shared_config.py` | `docs/CHANGE_IMPACT_MAP.md` | 注释中引用 |
| `launcher/launcher.py` L708 | `docs/VERSION.md` | **运行时读取**版本号 |

> ⚠️ `launcher/launcher.py` 会在运行时读取 `docs/VERSION.md` 获取最新版本号用于更新检查。该文件路径和当前版本条目**不能被移动或删除**。
