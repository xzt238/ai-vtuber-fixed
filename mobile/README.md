# GuguGaga AI VTuber - 移动端

<div align="center">

🎭 **你的专属 AI 虚拟主播伙伴 - 移动版**

[![Version](https://img.shields.io/badge/version-2.6.0-blue)]()
[![Platform](https://img.shields.io/badge/platform-Android%20%7C%20iOS-lightgrey)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

**基于 React Native + Expo 构建的全功能 AI VTuber 移动应用**

</div>

---

## 📖 项目简介

GuguGaga AI VTuber 移动端是一个功能完整的 AI 虚拟主播应用，支持 Android 和 iOS 平台。

### ✨ 核心亮点

- 🤖 **12 种 AI 模型** - OpenAI, Claude, 通义千问, DeepSeek 等
- 🎭 **Live2D/3D 模型** - V3 引擎，粒子+物理+情感
- 🎤 **语音交互** - TTS 15 种语音 + ASR 7 种引擎
- 📺 **9 大直播平台** - B站, 抖音, 快手, YouTube 等
- 👥 **多角色群聊** - 多个 AI 同时对话
- 📞 **语音通话** - 实时语音对话
- 🎮 **游戏助手** - 6 款游戏支持
- 🎵 **AI 唱歌** - 11 种唱法
- 🎙️ **变声器** - 15 种音效
- 🔊 **语音克隆** - 7 种克隆引擎
- 📊 **性能监控** - 实时指标+评分

---

## 🚀 快速开始

### 环境要求

| 项目 | 要求 |
|------|------|
| **Node.js** | 18+ |
| **npm** | 9+ |
| **Expo CLI** | 最新版 |

### 安装依赖

```bash
cd mobile
npm install
```

### 启动开发服务器

```bash
npx expo start
```

### 构建 APK

```bash
# 方式一：使用构建脚本
build.bat android

# 方式二：使用 EAS CLI
EAS_NO_VCS=1 npx eas-cli build --platform android --profile preview
```

### 推送 OTA 热更新

```bash
# 方式一：使用更新脚本
update.bat

# 方式二：使用 EAS CLI
EAS_NO_VCS=1 npx eas-cli update --branch preview --message "Update message"
```

---

## 📁 项目结构

```
mobile/
│
├── app/                    # 17 个页面
│   ├── (tabs)/            # 5 个 Tab 页面
│   │   ├── index.tsx      # 对话 Tab
│   │   ├── characters.tsx # 角色 Tab
│   │   ├── live.tsx       # 直播 Tab
│   │   ├── memory.tsx     # 记忆 Tab
│   │   └── settings.tsx   # 设置 Tab
│   ├── chat.tsx           # 聊天页面
│   ├── voice-call.tsx     # 语音通话
│   ├── group-chat.tsx     # 多角色群聊
│   ├── character-editor.tsx # 角色编辑器
│   ├── character-market.tsx # 角色市场
│   ├── model-select.tsx   # 模型选择
│   ├── game-assistant.tsx # 游戏助手
│   ├── vision-analyzer.tsx # 视觉分析
│   ├── voice-changer.tsx  # 变声器
│   ├── singing.tsx        # AI 唱歌
│   ├── voice-clone.tsx    # 语音克隆
│   ├── performance.tsx    # 性能监控
│   ├── search.tsx         # 消息搜索
│   └── about.tsx          # 关于页面
│
├── src/
│   ├── components/        # 15 个 UI 组件
│   │   ├── live2d/        # Live2D 组件
│   │   ├── vrm/           # VRM 3D 组件
│   │   ├── AnimatedBubble.tsx
│   │   ├── AnimatedButton.tsx
│   │   ├── ChatBubble.tsx
│   │   └── ...
│   │
│   ├── services/          # 18 个服务模块
│   │   ├── localAI.ts     # 本地 AI 引擎
│   │   ├── tts/           # 语音合成
│   │   ├── asr/           # 语音识别
│   │   ├── rag/           # RAG 知识库
│   │   ├── vad/           # 语音活动检测
│   │   ├── interrupt/     # 语音打断
│   │   ├── emotion/       # 情感分析
│   │   ├── game/          # 游戏助手
│   │   ├── vision/        # 视觉分析
│   │   ├── i18n/          # 国际化
│   │   ├── voiceChanger/  # 变声器
│   │   ├── singing/       # AI 唱歌
│   │   ├── voiceClone/    # 语音克隆
│   │   ├── performanceMonitor/ # 性能监控
│   │   ├── multiAgent/    # 多 Agent
│   │   ├── live/          # 直播弹幕
│   │   ├── imageGen/      # 文生图
│   │   └── ...
│   │
│   ├── stores/            # 状态管理 (Zustand)
│   ├── hooks/             # React Hooks
│   ├── utils/             # 工具函数
│   └── types/             # 类型定义
│
├── assets/                # 资源文件
│   ├── web/               # WebView 资源
│   ├── images/            # 图片资源
│   └── fonts/             # 字体资源
│
├── app.json               # Expo 配置
├── package.json           # 依赖配置
├── tsconfig.json          # TypeScript 配置
├── babel.config.js        # Babel 配置
├── eas.json               # EAS 构建配置
├── build.bat              # APK 构建脚本
├── update.bat             # OTA 热更新脚本
└── rebuild.bat            # 重新构建脚本
```

---

## ✨ 功能清单

### 🎭 虚拟形象

| 功能 | 说明 |
|------|------|
| Live2D V3 | 粒子系统、物理引擎、8 种情感 |
| VRM 3D | Three.js 渲染 |
| 口型同步 | 音频驱动口型 |
| 触摸交互 | 点击头部/脸颊反应 |

### 🤖 AI 对话

| 功能 | 说明 |
|------|------|
| LLM 支持 | 12 种 AI 模型 |
| 本地 AI | 离线可用 |
| RAG 知识库 | 向量检索增强 |
| 情感分析 | 7 种情感识别 |
| 多 Agent | 5 种协作模式 |

### 🎤 语音交互

| 功能 | 说明 |
|------|------|
| TTS 语音 | 15 种语音+情感语调 |
| ASR 识别 | 7 种引擎 |
| VAD 打断 | 语音活动检测 |
| 变声器 | 15 种音效 |
| AI 唱歌 | 11 种唱法 |
| 语音克隆 | 7 种引擎 |

### 📺 直播集成

| 功能 | 说明 |
|------|------|
| 直播平台 | 9 个（B站/抖音/快手/YouTube 等） |
| 弹幕互动 | 智能回复 |
| 礼物感谢 | 自动感谢 |

### 🎮 游戏助手

| 功能 | 说明 |
|------|------|
| 游戏支持 | 6 款（Minecraft/Factorio/原神等） |
| 攻略查询 | AI 生成攻略 |
| 物品识别 | 截图+OCR |

### 👥 社交功能

| 功能 | 说明 |
|------|------|
| 多角色群聊 | 4 种预设场景+自定义 |
| 角色市场 | 预设+自定义角色 |
| 角色编辑 | 自定义创建 |
| 角色分享 | 导出/导入 |
| 语音通话 | 实时语音对话 |

### 💾 数据管理

| 功能 | 说明 |
|------|------|
| 消息搜索 | 全局搜索 |
| 数据备份 | 备份/恢复 |
| 热更新 | OTA 更新 |
| 性能监控 | 实时指标 |

### 🌍 其他功能

| 功能 | 说明 |
|------|------|
| 多语言 | 12 种语言 |
| 深色模式 | 主题切换 |
| 文生图 | 5 种 API |
| 视觉分析 | 6 种分析类型 |

---

## 📊 版本历史

| 版本 | 日期 | 主要功能 |
|------|------|----------|
| v2.6.0 | 2026-06-07 | 性能监控面板 |
| v2.5.0 | 2026-06-07 | 语音克隆（7 种引擎） |
| v2.4.0 | 2026-06-06 | 变声器 + AI 唱歌 |
| v2.3.0 | 2026-06-06 | 游戏助手 + 视觉分析 + 多语言 |
| v2.2.0 | 2026-06-06 | 多 Agent + ASR V2 |
| v2.1.0 | 2026-06-06 | VAD + 打断 + RAG V2 + 弹幕 |
| v2.0.0 | 2026-06-05 | Live2D V3 + 页面转场动画 |
| v1.9.0 | 2026-06-05 | 主题系统 + 动画库 |
| v1.8.0 | 2026-06-05 | 设置优化 + 自定义群聊 |
| v1.7.0 | 2026-06-05 | 消息搜索 + 数据备份 |
| v1.6.0 | 2026-06-05 | 语音通话 + 角色分享 |
| v1.5.0 | 2026-06-05 | 性能优化 + 角色编辑器 |
| v1.4.0 | 2026-06-05 | 多角色群聊 |
| v1.3.0 | 2026-06-05 | 模型管理器 + 角色市场 |
| v1.2.0 | 2026-06-05 | Live2D V2 + VRM 3D |

---

## 🛠️ 技术栈

| 技术 | 用途 |
|------|------|
| React Native | 跨平台框架 |
| Expo | 开发工具链 |
| TypeScript | 类型安全 |
| Zustand | 状态管理 |
| MMKV | 本地存储 |
| React Native Animated | 动画 |
| Three.js + WebView | 3D 渲染 |
| expo-router | 页面路由 |

---

## 📱 安装指南

### Android APK

1. 下载最新 APK
2. 传输到手机
3. 安装（需要开启"允许安装未知来源应用"）
4. 打开 GuguGaga 应用

### iOS (Expo Go)

1. 在 App Store 下载 Expo Go
2. 打开 Expo Go 应用
3. 输入开发服务器地址或扫描二维码

---

## 🔧 开发指南

### 类型检查

```bash
npx tsc --noEmit
```

### 构建 APK

```bash
EAS_NO_VCS=1 npx eas-cli build --platform android --profile preview
```

### 推送 OTA 更新

```bash
EAS_NO_VCS=1 npx eas-cli update --branch preview --message "Update message"
```

---

## 📄 许可证

MIT License

---

<div align="center">

**让 AI 陪伴你的每一天** ❤️

Made with ❤️ by GuguGaga Team

</div>
