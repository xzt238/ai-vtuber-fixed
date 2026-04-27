# 📚 AI VTuber 技术文档中心

欢迎来到咕咕嘎嘎 AI VTuber 的技术文档中心喵~ 🐱

---

## 📖 文档索引

### 🚀 快速开始
- **[BUILD.md](BUILD.md)** - 快速构建和打包指南
  - 一键打包脚本
  - 手动打包步骤
  - 运行和配置说明

### 🏗️ 架构与开发
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - 技术架构文档 ⭐ 新增
  - 项目架构概览
  - 目录结构规范
  - 启动流程规范
  - 依赖管理规范
  - 配置文件规范
  - 版本管理规范
  - 开发规范
  - 安全规范
  - 性能优化规范
  - 调试指南

- **[DEV_GUIDE.md](DEV_GUIDE.md)** - 开发规范文档 ⭐ 新增
  - 开发流程规范
  - 代码规范 (PEP 8)
  - 测试规范 (单元测试/集成测试/性能测试)
  - 版本发布规范
  - 维护规范
  - 问题排查指南

- **[CODE_REVIEW_REPORT.md](CODE_REVIEW_REPORT.md)** - 代码架构深度分析报告
  - 项目概览和技术栈
  - 分层架构设计
  - 核心模块详解 (TTS/LLM/Memory/SubAgent/Live2D)
  - 数据流程分析
  - 性能优化分析
  - 安全性分析
  - 代码质量评估

### 🔧 集成与优化
- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** - 集成指南
  - 模块集成说明
  - API 接口文档
  - 配置参数说明

- **[OPTIMIZATION_PLAN.md](OPTIMIZATION_PLAN.md)** - 优化计划
  - 短期优化目标
  - 中期优化目标
  - 长期优化目标

- **[OPTIMIZATION_SUMMARY.md](OPTIMIZATION_SUMMARY.md)** - 优化总结
  - 已完成的优化
  - 性能提升数据
  - 优化效果分析

- **[OPTIMIZATION_COMPLETE.md](OPTIMIZATION_COMPLETE.md)** - 优化完成报告
  - 优化成果汇总
  - 性能对比数据
  - 后续建议

### 📝 版本历史
- **[VERSION.md](VERSION.md)** - 版本更新日志 ⭐ 重要
  - 各版本功能更新
  - Bug 修复记录
  - 已知问题列表

---

## 🎯 文档分类

### 按用途分类

| 类型 | 文档 | 适用人群 |
|------|------|----------|
| **入门** | BUILD.md | 新用户、部署人员 |
| **架构** | ARCHITECTURE.md ⭐ | 开发者、架构师、AI 助手 |
| **开发** | DEV_GUIDE.md ⭐, CODE_REVIEW_REPORT.md | 开发者、维护者 |
| **集成** | INTEGRATION_GUIDE.md | 集成工程师 |
| **优化** | OPTIMIZATION_*.md | 性能优化工程师 |
| **维护** | VERSION.md ⭐ | 运维人员、项目管理者 |

### 按模块分类

| 模块 | 相关文档 | 说明 |
|------|----------|------|
| **整体架构** | ARCHITECTURE.md | 完整技术架构和规范 |
| **TTS** | CODE_REVIEW_REPORT.md (第1节) | ChatTTS + EdgeTTS + OpenAudio 三引擎 |
| **LLM** | CODE_REVIEW_REPORT.md (第2节) | MiniMax 集成 |
| **Memory** | CODE_REVIEW_REPORT.md (第3节) | 分层记忆系统 |
| **SubAgent** | CODE_REVIEW_REPORT.md (第4节) | 工具执行系统 |
| **Live2D** | CODE_REVIEW_REPORT.md (第5节) | 虚拟形象渲染 |

---

## 🔍 快速查找

### 常见问题

**Q: 如何快速部署？**  
A: 查看 [BUILD.md](BUILD.md) 的"一键打包"章节

**Q: 如何理解代码架构？**  
A: 查看 [ARCHITECTURE.md](ARCHITECTURE.md) 的"项目架构概览"章节

**Q: 如何开始开发？**  
A: 查看 [DEV_GUIDE.md](DEV_GUIDE.md) 的"开发流程规范"章节

**Q: 如何更新版本？**  
A: 查看 [DEV_GUIDE.md](DEV_GUIDE.md) 的"版本发布规范"章节，**每次更新必须更新 VERSION.md**

**Q: 如何优化性能？**  
A: 查看 [OPTIMIZATION_PLAN.md](OPTIMIZATION_PLAN.md) 和 [OPTIMIZATION_SUMMARY.md](OPTIMIZATION_SUMMARY.md)

**Q: 如何集成新模块？**  
A: 查看 [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)

**Q: 有哪些版本更新？**  
A: 查看 [VERSION.md](VERSION.md)

---

## ⭐ 重要提醒

### 每次代码更新后必须执行：

1. **更新 VERSION.md** ⭐⭐⭐
   - 记录版本号 (v主版本.次版本.修订号)
   - 记录更新类型 (✨新增/🔧修复/📝文档等)
   - 记录详细说明

2. **更新相关文档** (如有必要)
   - ARCHITECTURE.md (架构变更)
   - README.md (功能变更)
   - DEV_GUIDE.md (规范变更)

3. **Git 提交和打标签**
   ```bash
   git add .
   git commit -m "v1.x.x: 更新说明"
   git tag v1.x.x
   git push origin main --tags
   ```

详细流程请查看 [DEV_GUIDE.md](DEV_GUIDE.md) 的"版本发布规范"章节。

---

## 📈 文档统计

- **总文档数**: 9 个 (新增 2 个)
- **总字数**: ~80,000 字
- **最后更新**: 2026-04-06
- **维护者**: 咕咕嘎嘎 🐱

---

## 🤝 贡献指南

如果你想为文档做出贡献：

1. 保持文档结构清晰
2. 使用 Markdown 格式
3. 添加代码示例和图表
4. 及时更新版本信息 ⭐
5. 保持语言风格一致（可爱、专业、易懂）

---

## 📞 联系方式

- **项目主页**: `/volume1/docker/cat/ai-vtuber-fixed`
- **维护者**: 咕咕嘎嘎 (可爱的猫娘 AI 助手)
- **最后更新**: 2026-04-06

---

**喵~ 希望这些文档能帮到你！如有问题随时问咕咕嘎嘎喵~ 🐱✨**
