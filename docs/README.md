# 📚 咕咕嘎嘎 AI-VTuber 技术文档中心

欢迎来到咕咕嘎嘎 AI VTuber 的技术文档中心

---

## 📖 文档索引

### 🚀 快速开始
- **[BUILD.md](BUILD.md)** - 快速构建和打包指南
  - 一键打包脚本
  - 手动打包步骤
  - 运行和配置说明

### 🛠️ 开发指南
- **[DEVGUIDE.md](DEVGUIDE.md)** - 开发者指南 ⭐ 核心文档
  - 项目概览与技术栈
  - 项目结构详解
  - 三种启动模式对比
  - 核心架构（AIVTuber 懒加载、Config、工厂模式）
  - 模块详解（ASR/TTS/LLM/记忆/视觉/工具/MCP/Web）
  - 开发环境搭建
  - 代码规范与约定
  - 调试指南
  - 常见开发任务
  - 版本管理与发布流程

### 🖥️ 原生桌面
- **[NATIVE_DESKTOP.md](NATIVE_DESKTOP.md)** - 原生桌面应用架构 ⭐ 重点
  - 架构概览与模式对比
  - 入口与启动流程
  - 主窗口结构（FluentWindow 布局）
  - 5 个页面详解（对话/训练/记忆/模型下载/设置）
  - 10 个组件详解（Live2D/语音/托盘/快捷键/宠物等）
  - 后端交互方式（Python 直调 vs HTTP/WS）
  - 主题系统
  - 构建与打包
  - 当前状态与待改进项（P0-P3 优先级）
  - 开发指南

### 📝 版本与规划
- **[VERSION.md](VERSION.md)** - 版本更新日志 ⭐ 必读
  - 各版本功能更新
  - Bug 修复记录
  - 版本号管理规范

- **[feasibility_native_desktop.md](feasibility_native_desktop.md)** - 原生桌面可行性报告
  - 技术方案对比（PySide6 vs Tauri vs Electron vs Flutter）
  - 分阶段实施计划
  - 关键技术细节（Live2D/后端直调/实时语音）
  - 风险评估

- **[feasibility_tool_system_upgrade.md](feasibility_tool_system_upgrade.md)** - 工具系统升级可行性报告
  - 现状诊断（5 个致命缺陷）
  - 行业标杆调研
  - 四阶段升级方案（Function Calling → 前端展示 → MCP 预配置 → 可视化）
  - 本地 MCP 服务器清单

---

## 🎯 快速查找

| 你想做什么 | 看哪个文档 |
|-----------|-----------|
| 首次搭建开发环境 | [DEVGUIDE.md §7](DEVGUIDE.md) |
| 理解项目架构 | [DEVGUIDE.md §5](DEVGUIDE.md) |
| 修改原生桌面 UI | [NATIVE_DESKTOP.md](NATIVE_DESKTOP.md) |
| 添加新的 LLM Provider | [DEVGUIDE.md §10.1](DEVGUIDE.md) |
| 打包发布 | [DEVGUIDE.md §11](DEVGUIDE.md) |
| 查看版本历史 | [VERSION.md](VERSION.md) |
| 了解原生桌面待改进项 | [NATIVE_DESKTOP.md §9](NATIVE_DESKTOP.md) |
| 了解工具系统升级计划 | [feasibility_tool_system_upgrade.md](feasibility_tool_system_upgrade.md) |

---

## ⭐ 重要提醒

### 每次代码更新后必须执行：

1. **更新 VERSION.md** ⭐⭐⭐
   - 记录版本号 (v主版本.次版本.修订号)
   - 记录更新类型 (✨新增/🔧修复/📝文档等)
   - 记录详细说明

2. **更新散布的版本号** ⭐⭐
   - `README.md` 中的版本 badge
   - `native/main.py` 中的 `setWindowTitle` 和 `UpdateManager`
   - `scripts/start.bat` 中的 `version:` 行

3. **Git 提交和打标签**
   ```bash
   git add .
   git commit -m "v1.x.x: 更新说明"
   git tag v1.x.x
   git push origin main --tags
   ```

详细流程请查看 [DEVGUIDE.md §11](DEVGUIDE.md)。

---

## 📊 文档统计

- **总文档数**: 7 个
- **最后更新**: 2026-05-05
- **核心文档**: DEVGUIDE.md, NATIVE_DESKTOP.md, VERSION.md

---

## 🤝 贡献指南

1. 保持文档结构清晰
2. 使用 Markdown 格式
3. 添加代码示例和架构图
4. 及时更新版本信息 ⭐
5. 颜色值不要硬编码，引用 `theme.py` 的 `get_colors()`
6. 新增页面必须在 `native/main.py` 的 `_create_pages()` 中注册

---

*文档中心最后更新: 2026-05-05*
