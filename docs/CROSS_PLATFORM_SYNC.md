# 全平台同步开发指南

本文档说明如何在桌面端和移动端之间进行同步开发，确保两个平台的功能保持一致。

---

## 📋 概述

GuguGaga AI VTuber 支持两个平台：

| 平台 | 技术栈 | 位置 | 版本 |
|------|--------|------|------|
| **Windows 桌面端** | Python + PySide6 | 根目录 | v1.19.1 |
| **Android/iOS 移动端** | React Native + Expo | `mobile/` | v2.6.0 |

### 同步开发原则

1. **功能对齐** - 新功能同时在两个平台实现
2. **接口一致** - 核心接口保持一致
3. **配置共享** - 使用统一的配置格式
4. **版本同步** - 两端版本号保持一致

---

## 🔄 开发流程

### 新功能开发流程

```
1. 设计功能接口
   ↓
2. 桌面端实现 (Python)
   ↓
3. 移动端实现 (TypeScript)
   ↓
4. 同步测试
   ↓
5. 发布更新
```

### 详细步骤

#### 步骤 1：设计功能接口

在 `shared/` 目录定义共享接口：

```yaml
# shared/config.yaml
new_feature:
  enabled: true
  option1: value1
  option2: value2
```

#### 步骤 2：桌面端实现

```python
# app/new_feature/__init__.py
class NewFeature:
    def __init__(self, config):
        self.config = config
    
    def process(self, input):
        # 实现逻辑
        return result
```

#### 步骤 3：移动端实现

```typescript
// src/services/newFeature/index.ts
class NewFeatureService {
  private config: NewFeatureConfig;
  
  constructor(config: NewFeatureConfig) {
    this.config = config;
  }
  
  process(input: string): Result {
    // 实现逻辑
    return result;
  }
}

export const newFeatureService = new NewFeatureService();
```

#### 步骤 4：同步测试

- 桌面端：运行测试套件
- 移动端：TypeScript 检查 + 设备测试

#### 步骤 5：发布更新

- 桌面端：打包发布
- 移动端：OTA 热更新或重新构建

---

## 📁 目录结构对比

| 功能 | 桌面端 | 移动端 |
|------|--------|--------|
| **主入口** | `app/main.py` | `app/_layout.tsx` |
| **配置** | `app/config.yaml` | `app.json` |
| **LLM** | `app/llm/` | `src/services/api.ts` |
| **TTS** | `app/tts/` | `src/services/tts/` |
| **ASR** | `app/asr/` | `src/services/asr/` |
| **Live2D** | `app/live2d/` | `src/components/live2d/` |
| **VRM** | `native/gugu_native/widgets/vrm_widget.py` | `src/components/vrm/` |
| **记忆** | `app/memory/` | `src/stores/index.ts` |
| **RAG** | `app/rag/` | `src/services/rag/` |
| **游戏** | `app/game/` | `src/services/game/` |
| **直播** | `app/live/` | `src/services/live/` |
| **Bot** | `app/bot/` | ❌ 未实现 |
| **变声** | `app/svc/` | `src/services/voiceChanger/` |
| **唱歌** | `app/singing/` | `src/services/singing/` |
| **克隆** | `GPT-SoVITS/` | `src/services/voiceClone/` |
| **视觉** | `app/vision_input/` | `src/services/vision/` |
| **多语言** | `app/i18n/` | `src/services/i18n/` |

---

## 🔌 接口设计规范

### LLM 接口

**桌面端 (Python)**:
```python
class LLMEngine:
    def chat(self, messages: List[Dict], config: Dict) -> str:
        pass
```

**移动端 (TypeScript)**:
```typescript
interface LLMEngine {
  chat(messages: Message[], config: AIConfig): Promise<string>;
}
```

### TTS 接口

**桌面端 (Python)**:
```python
class TTSEngine:
    def speak(self, text: str, config: Dict) -> str:
        pass
```

**移动端 (TypeScript)**:
```typescript
interface TTSEngine {
  speak(text: string, config?: TTSConfig): Promise<void>;
}
```

### ASR 接口

**桌面端 (Python)**:
```python
class ASREngine:
    def recognize(self, audio_path: str) -> str:
        pass
```

**移动端 (TypeScript)**:
```typescript
interface ASREngine {
  recognize(audioUri: string): Promise<string>;
}
```

---

## 🧩 功能模块对照表

### 已实现功能

| 功能 | 桌面端 | 移动端 | 说明 |
|------|--------|--------|------|
| Live2D 渲染 | ✅ | ✅ | 桌面端用 OpenGL，移动端用 WebView |
| VRM 3D | ✅ | ✅ | 桌面端用 QWebEngineView，移动端用 Three.js |
| LLM 对话 | ✅ | ✅ | 12 种 LLM 支持 |
| TTS 语音 | ✅ | ✅ | 桌面端 6 种，移动端 15 种 |
| ASR 识别 | ✅ | ✅ | 桌面端 3 种，移动端 7 种 |
| RAG 知识库 | ✅ | ✅ | 向量检索 |
| 情感分析 | ✅ | ✅ | 7 种情感 |
| 直播弹幕 | ✅ | ✅ | 9 大平台 |
| 游戏助手 | ✅ | ✅ | 桌面端 5 款，移动端 6 款 |
| 多 Agent | ✅ | ✅ | 5 种协作模式 |
| 视觉分析 | ✅ | ✅ | 桌面端 4 种，移动端 6 种 |
| 变声器 | ✅ | ✅ | 15 种音效 |
| AI 唱歌 | ✅ | ✅ | 11 种唱法 |
| 语音克隆 | ✅ | ✅ | 桌面端 GPT-SoVITS，移动端 7 种引擎 |
| VAD 打断 | ✅ | ✅ | Silero VAD |
| 多语言 | ✅ | ✅ | 12 种语言 |
| 数据备份 | ✅ | ✅ | 备份/恢复 |
| 消息搜索 | ✅ | ✅ | 全局搜索 |
| 性能监控 | ✅ | ✅ | 实时指标 |

### 桌面端独有功能

| 功能 | 说明 |
|------|------|
| 桌面宠物 | 桌面悬浮虚拟形象 |
| 模型训练 | GPT-SoVITS 训练面板 |
| OCR 识别 | 屏幕文字识别 |
| MCP 协议 | 模型上下文协议 |
| 系统托盘 | 后台运行 |
| 全局快捷键 | 快速操作 |

### 移动端独有功能

| 功能 | 说明 |
|------|------|
| OTA 热更新 | 无需重新安装 |
| 触觉反馈 | 震动反馈 |
| 推送通知 | 消息通知 |
| 性能监控面板 | 实时性能数据 |
| 角色市场 | 在线角色分享 |

---

## 🔧 同步开发工具

### 代码同步

```bash
# 桌面端代码目录
E:\ai-vtuber-fixed\app\

# 移动端代码目录
E:\ai-vtuber-fixed\mobile\src\
```

### 配置同步

```bash
# 共享配置
E:\ai-vtuber-fixed\shared\config.yaml

# 桌面端配置
E:\ai-vtuber-fixed\app\config.yaml

# 移动端配置
E:\ai-vtuber-fixed\mobile\app.json
```

### 测试同步

```bash
# 桌面端测试
cd E:\ai-vtuber-fixed
python -m pytest tests/

# 移动端测试
cd E:\ai-vtuber-fixed\mobile
npx tsc --noEmit
```

---

## 📝 开发检查清单

### 新功能开发检查

- [ ] 设计功能接口
- [ ] 桌面端实现
- [ ] 移动端实现
- [ ] 桌面端测试
- [ ] 移动端测试
- [ ] 更新文档
- [ ] 提交代码

### 发布检查

- [ ] 桌面端打包
- [ ] 移动端构建 APK
- [ ] 移动端推送 OTA
- [ ] 更新版本号
- [ ] 更新 CHANGELOG
- [ ] 创建 GitHub Release

---

## 🐛 常见问题

### Q: 桌面端和移动端的功能不一致怎么办？

A: 检查两个平台的实现，确保接口一致。如果某个平台缺少功能，需要补充实现。

### Q: 如何同步配置？

A: 使用 `shared/config.yaml` 作为配置源，桌面端和移动端分别读取并转换为各自的格式。

### Q: 移动端的 OTA 更新会影响桌面端吗？

A: 不会。OTA 更新只更新移动端的 JS 代码，不影响桌面端。

### Q: 如何处理平台差异？

A: 使用平台特定的代码：
```typescript
import { Platform } from 'react-native';

if (Platform.OS === 'android') {
  // Android 特定代码
} else if (Platform.OS === 'ios') {
  // iOS 特定代码
}
```

---

## 📚 参考资料

- [React Native 跨平台开发](https://reactnative.dev/docs/platform-specific-code)
- [Expo 文档](https://docs.expo.dev/)
- [PySide6 文档](https://doc.qt.io/qtforpython-6/)

---

<div align="center">

**全平台同步开发，让 AI 无处不在** ❤️

</div>
