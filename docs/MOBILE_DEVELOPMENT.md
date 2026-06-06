# 移动端开发指南

本文档详细说明 GuguGaga AI VTuber 移动端的开发流程、架构设计和最佳实践。

---

## 📱 项目概述

GuguGaga AI VTuber 移动端是基于 React Native + Expo 构建的跨平台移动应用，支持 Android 和 iOS。

### 技术栈

| 技术 | 用途 | 版本 |
|------|------|------|
| React Native | 跨平台框架 | 0.74 |
| Expo | 开发工具链 | 51 |
| TypeScript | 类型安全 | 5.3 |
| Zustand | 状态管理 | 4.5 |
| MMKV | 本地存储 | 2.12 |
| expo-router | 页面路由 | 3.5 |
| react-native-webview | WebView | 13.10 |
| react-native-reanimated | 动画 | 3.10 |

### 项目结构

```
mobile/
│
├── app/                    # 页面路由 (expo-router)
│   ├── (tabs)/            # Tab 页面
│   │   ├── _layout.tsx    # Tab 布局
│   │   ├── index.tsx      # 对话 Tab
│   │   ├── characters.tsx # 角色 Tab
│   │   ├── live.tsx       # 直播 Tab
│   │   ├── memory.tsx     # 记忆 Tab
│   │   └── settings.tsx   # 设置 Tab
│   ├── _layout.tsx        # 根布局
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
│   ├── components/        # UI 组件
│   │   ├── live2d/        # Live2D 组件
│   │   │   ├── Live2DView.tsx
│   │   │   └── index.ts
│   │   ├── vrm/           # VRM 3D 组件
│   │   │   ├── VRMView.tsx
│   │   │   └── index.ts
│   │   ├── AnimatedBubble.tsx
│   │   ├── AnimatedButton.tsx
│   │   ├── AnimatedCard.tsx
│   │   ├── ChatBubble.tsx
│   │   ├── CharacterCard.tsx
│   │   ├── EmotionBadge.tsx
│   │   ├── EmptyState.tsx
│   │   ├── FadeInView.tsx
│   │   ├── Header.tsx
│   │   ├── LoadingOverlay.tsx
│   │   ├── SearchBar.tsx
│   │   ├── ThemeProvider.tsx
│   │   ├── TypingIndicator.tsx
│   │   └── index.ts
│   │
│   ├── services/          # 业务服务
│   │   ├── localAI.ts     # 本地 AI 引擎
│   │   ├── api.ts         # 云端 API 服务
│   │   ├── tts/           # 语音合成
│   │   │   └── index.ts
│   │   ├── asr/           # 语音识别
│   │   │   ├── index.ts
│   │   │   └── v2.ts
│   │   ├── rag/           # RAG 知识库
│   │   │   ├── index.ts
│   │   │   └── v2.ts
│   │   ├── vad/           # 语音活动检测
│   │   │   └── index.ts
│   │   ├── interrupt/     # 语音打断
│   │   │   └── index.ts
│   │   ├── emotion/       # 情感分析
│   │   │   └── index.ts
│   │   ├── game/          # 游戏助手
│   │   │   └── index.ts
│   │   ├── vision/        # 视觉分析
│   │   │   └── index.ts
│   │   ├── i18n/          # 国际化
│   │   │   └── index.ts
│   │   ├── voiceChanger/  # 变声器
│   │   │   └── index.ts
│   │   ├── singing/       # AI 唱歌
│   │   │   └── index.ts
│   │   ├── voiceClone/    # 语音克隆
│   │   │   └── index.ts
│   │   ├── performanceMonitor/ # 性能监控
│   │   │   └── index.ts
│   │   ├── multiAgent/    # 多 Agent
│   │   │   └── index.ts
│   │   ├── live/          # 直播弹幕
│   │   │   └── DanmakuService.ts
│   │   ├── imageGen/      # 文生图
│   │   │   └── index.ts
│   │   ├── modelManager.ts # 模型管理
│   │   ├── characterMarket.ts # 角色市场
│   │   ├── characterShare.ts # 角色分享
│   │   ├── groupChat.ts   # 群聊服务
│   │   ├── messageSearch.ts # 消息搜索
│   │   ├── dataBackup.ts  # 数据备份
│   │   ├── voiceCall.ts   # 语音通话
│   │   ├── audioAnalyzer.ts # 音频分析
│   │   ├── cacheManager.ts # 缓存管理
│   │   ├── startupOptimizer.ts # 启动优化
│   │   ├── themeManager.ts # 主题管理
│   │   └── index.ts
│   │
│   ├── stores/            # 状态管理 (Zustand)
│   │   └── index.ts
│   │
│   ├── hooks/             # React Hooks
│   │   ├── useI18n.ts     # 国际化 Hook
│   │   └── useTheme.ts    # 主题 Hook
│   │
│   ├── utils/             # 工具函数
│   │   ├── animations.ts  # 动画工具
│   │   ├── constants.ts   # 常量定义
│   │   ├── helpers.ts     # 辅助函数
│   │   ├── performance.ts # 性能工具
│   │   └── theme.ts       # 主题工具
│   │
│   └── types/             # 类型定义
│       └── index.ts
│
├── assets/                # 资源文件
│   ├── web/               # WebView 资源
│   │   ├── live2d.html    # Live2D V1
│   │   ├── live2d-v2.html # Live2D V2
│   │   ├── live2d-v3.html # Live2D V3
│   │   └── vrm-viewer.html # VRM 查看器
│   ├── images/            # 图片资源
│   └── fonts/             # 字体资源
│
├── app.json               # Expo 配置
├── package.json           # 依赖配置
├── tsconfig.json          # TypeScript 配置
├── babel.config.js        # Babel 配置
├── eas.json               # EAS 构建配置
├── index.js               # 入口文件
├── build.bat              # APK 构建脚本
├── build.sh               # Mac/Linux 构建脚本
├── update.bat             # OTA 热更新脚本
├── update.sh              # Mac/Linux 更新脚本
└── rebuild.bat            # 重新构建脚本
```

---

## 🚀 开发环境搭建

### 环境要求

| 项目 | 要求 |
|------|------|
| Node.js | 18+ |
| npm | 9+ |
| Expo CLI | 最新版 |
| Android Studio | Android 开发（可选） |
| Xcode | iOS 开发（仅 macOS） |

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/xzt238/ai-vtuber-fixed.git
cd ai-vtuber-fixed/mobile

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npx expo start

# 4. 在手机上运行
# Android: 安装 Expo Go 应用，扫描二维码
# iOS: 安装 Expo Go 应用，扫描二维码
```

---

## 📦 构建和发布

### 构建 APK

```bash
# 方式一：使用构建脚本
build.bat android

# 方式二：使用 EAS CLI
EAS_NO_VCS=1 npx eas-cli build --platform android --profile preview
```

### 构建 iOS

```bash
# 需要 Apple 开发者账号 ($99/年)
build.bat ios

# 或
EAS_NO_VCS=1 npx eas-cli build --platform ios --profile preview
```

### OTA 热更新

```bash
# 推送 JS 代码更新（用户打开 App 自动下载）
update.bat

# 或
EAS_NO_VCS=1 npx eas-cli update --branch preview --message "Update message"
```

### 版本更新策略

| 更新类型 | 方式 | 说明 |
|----------|------|------|
| **JS/UI 更新** | OTA 热更新 | 用户无需重新安装 |
| **原生代码更新** | 重新构建 APK | 需要用户重新安装 |
| **依赖更新** | 重新构建 APK | 需要用户重新安装 |
| **配置更新** | 重新构建 APK | 需要用户重新安装 |

---

## 🏗️ 架构设计

### 页面路由

使用 expo-router 进行页面路由管理：

```typescript
// app/_layout.tsx - 根布局
export default function RootLayout() {
  return (
    <Stack>
      <Stack.Screen name="(tabs)" />
      <Stack.Screen name="chat" />
      <Stack.Screen name="voice-call" />
      // ...
    </Stack>
  );
}

// app/(tabs)/_layout.tsx - Tab 布局
export default function TabLayout() {
  return (
    <Tabs>
      <Tabs.Screen name="index" />
      <Tabs.Screen name="characters" />
      <Tabs.Screen name="live" />
      <Tabs.Screen name="memory" />
      <Tabs.Screen name="settings" />
    </Tabs>
  );
}
```

### 状态管理

使用 Zustand 进行状态管理：

```typescript
// src/stores/index.ts
import { create } from 'zustand';
import { MMKV } from 'react-native-mmkv';

const storage = new MMKV();

export const useCharacterStore = create((set, get) => ({
  characters: [],
  addCharacter: (character) => set((state) => ({
    characters: [...state.characters, character],
  })),
  // ...
}));
```

### 服务层

每个功能模块都有独立的服务：

```typescript
// src/services/tts/index.ts
class TTSService {
  async speak(text: string, config?: TTSConfig): Promise<void> {
    // 实现 TTS 逻辑
  }
}

export const ttsService = new TTSService();
```

### Live2D 渲染

使用 WebView 渲染 Live2D 模型：

```typescript
// src/components/live2d/Live2DView.tsx
import { WebView } from 'react-native-webview';

export default function Live2DView({ emotion, isSpeaking }: Props) {
  return (
    <WebView
      source={require('../../../assets/web/live2d-v3.html')}
      onMessage={handleMessage}
    />
  );
}
```

---

## 🧪 测试

### TypeScript 检查

```bash
npx tsc --noEmit
```

### 运行测试

```bash
npm test
```

---

## 📝 编码规范

### 命名规范

- **文件名**: PascalCase (组件) | camelCase (服务/工具)
- **组件名**: PascalCase
- **函数名**: camelCase
- **常量**: UPPER_SNAKE_CASE
- **类型/接口**: PascalCase

### 代码风格

- 使用 TypeScript 严格模式
- 使用 ESLint 进行代码检查
- 使用 Prettier 进行代码格式化

### 组件规范

```typescript
// 1. 使用 React.memo 优化性能
const MyComponent = React.memo(({ prop }: Props) => {
  // 2. 使用 useMemo 缓存计算结果
  const computed = useMemo(() => expensiveCalculation(prop), [prop]);
  
  // 3. 使用 useCallback 缓存回调
  const handlePress = useCallback(() => {
    // ...
  }, []);
  
  return <View>...</View>;
});
```

---

## 🔧 调试技巧

### 开发者菜单

- Android: `Ctrl + M` 或摇晃手机
- iOS: `Cmd + D` 或摇晃手机

### React Native Debugger

```bash
# 安装
npm install -g react-native-debugger

# 启动
rndebugger-open
```

### 性能监控

使用内置的性能监控页面：
- 设置 → 通用 → 性能监控

---

## 📚 参考资料

- [Expo 文档](https://docs.expo.dev/)
- [React Native 文档](https://reactnative.dev/)
- [expo-router 文档](https://docs.expo.dev/router/)
- [Zustand 文档](https://zustand-demo.pmnd.rs/)
- [Live2D Web SDK](https://www.live2d.com/en/)

---

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -m 'Add feature xxx'`)
4. 推送到分支 (`git push origin feature/xxx`)
5. 创建 Pull Request

---

<div align="center">

**让 AI 陪伴你的每一天** ❤️

</div>
