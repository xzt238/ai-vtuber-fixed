# VRM 3D 模型支持可行性分析

> **日期**: 2026-05-22 | **目标**: 评估在咕咕嘎嘎中集成 VRM 3D 模型的可行性

---

## 一、什么是 VRM

VRM (Virtual Reality Model) 是一种基于 **glTF 2.0** 的 3D 虚拟化身文件格式，由日本 VRM Consortium 制定。可以理解为 **Live2D 的 3D 版**。

| 对比 | Live2D | VRM 3D |
|------|:------:|:------:|
| 维度 | 2D 骨骼动画 | 3D 模型（mesh + bones） |
| 文件 | `.model3.json` + `.moc3` | `.vrm`（单个文件） |
| 视角 | 固定视角（正交） | 自由旋转/缩放 |
| 表情 | 参数驱动（ParamEyeOpen 等） | BlendShape（52 种预设） |
| 物理 | 骨骼物理模拟 | 头发/裙摆物理 |
| 模型来源 | Live2D Cubism Editor | VRoid Studio / Blender |
| 生态 | VTuber 直播主流 | VRChat / VR 社交主流 |

**核心价值**: VRM 让用户可以用免费工具（VRoid Studio）自己建模，且模型可以带表情、物理效果、SpringBone 骨骼链。

---

## 二、竞品支持现状

| 产品 | VRM 支持 | 实现方式 |
|------|:---:|------|
| Project AIRI (22K⭐) | ✅ | three-vrm + Three.js (WebGL) |
| Soul of Waifu (3K⭐) | ✅ | three-vrm + Electron |
| HoloWaifu (闭源) | ✅ | UniVRM + Unity |
| Neuro-sama | ❌ | 专属 Live2D 模型 |
| **咕咕嘎嘎** | ❌ | — |

---

## 三、集成方案对比

### 方案 A：QWebEngineView + three-vrm（推荐）

```
                          ┌──────────────────────┐
                          │   QWebEngineView     │
                          │  ┌─────────────────┐ │
                          │  │  three.js        │ │
                          │  │  └─ three-vrm    │ │
                          │  │     └─ .vrm 文件  │ │
                          │  └─────────────────┘ │
                          │  WebGL → GPU         │
                          └──────────────────────┘
```

| 优点 | 缺点 |
|------|------|
| three-vrm 是 pixiv 官方维护，Star 4K+ | 需要 QWebEngineView（我们刚替换掉） |
| 完整的 VRM 规范支持（BlendShape/SpringBone 等） | 需要 HTTP 本地服务器提供文件 |
| JS 生态成熟，示例丰富 | 与 Live2D 共存需要两个 WebView |
| 参考 AIRI 项目实现 | 加载大模型可能较慢 |

**工作量**: 中等（~300 行 Python + ~200 行 HTML/JS）  
**可行性**: ⭐⭐⭐⭐⭐

### 方案 B：原生 Python + QOpenGLWidget（自研）

```
                          ┌──────────────────────┐
                          │   QOpenGLWidget      │
                          │  ┌─────────────────┐ │
                          │  │  自研 glTF Renderer│ │
                          │  │  └─ VRM Extension │ │
                          │  │     └─ .vrm 文件   │ │
                          │  └─────────────────┘  │
                          │  OpenGL → GPU         │
                          └──────────────────────┘
```

| 优点 | 缺点 |
|------|------|
| 与 Live2D 技术栈一致 | **需要从零实现 VRM 渲染器** |
| 无 Chromium 开销 | VRM 规范复杂（BlendShape/MToon/SpringBone） |
| 启动快 | 无成熟 Python glTF 渲染库 |
| | **预估工作量 >2000 行** |

**可行性**: ⭐⭐☆☆☆（不推荐）

### 方案 C：外部程序 + 窗口嵌入

使用 VRM 查看器（VRM Posing Desktop / VSeeFace）独立运行，通过 OBS Spout 或窗口嵌入到 Qt 中。

| 优点 | 缺点 |
|------|------|
| 零开发成本 | 体验割裂、无法交互 |
| 效果最好 | 无法与 AI 系统联动 |

**可行性**: ⭐⭐⭐☆☆（体验差）

---

## 四、推荐方案：QWebEngineView + three-vrm

### 架构

```
咕咕嘎嘎
├── 左侧面板
│   ├── Live2D (QOpenGLWidget + live2d-py)  ← 当前
│   └── VRM 3D (QWebEngineView + three-vrm)  ← 新增（切换显示）
├── 右侧面板 (QWebEngineView + chat)
└── backend (API)
```

### 关键技术点

```javascript
// three-vrm 加载 VRM 模型
import { VRMLoaderPlugin } from 'three-vrm';

const loader = new GLTFLoader();
loader.register(parser => new VRMLoaderPlugin(parser));

loader.load('model.vrm', (gltf) => {
    const vrm = gltf.userData.vrm;
    scene.add(vrm.scene);
    
    // 表情控制
    vrm.expressionManager.setValue('happy', 1.0);
    
    // 口型同步
    vrm.expressionManager.setValue('aa', value);
    
    // 表情参数（52种预设）
    vrm.expressionManager.getExpressionNames();
});
```

### 与 Live2D 共存

- VRM 和 Live2D **不同时显示**（左侧面板切换）
- 共用 AnimationController 的信号接口
- 口型同步通过 `set_mouth_open` 统一接口
- 表情切换通过 `set_expression` 统一接口

### 对现有代码的影响

| 文件 | 变更 |
|------|------|
| `live2d_widget.py` | 不变 |
| `chat_page.py` | 新增 VRM Widget 创建 + 切换逻辑 |
| 新增 `vrm_widget.py` | QWebEngineView 封装 |
| 新增 `vrm_template.html` | three-vrm HTML 页面 |
| `config.yaml` | 新增 `vrm:` 配置段 |

---

## 五、总结

| 维度 | 评估 |
|------|------|
| 技术可行性 | ⭐⭐⭐⭐⭐ — three-vrm 成熟可靠 |
| 开发工作量 | 中等（~2-3 天） |
| 用户价值 | ⭐⭐⭐⭐ — 社区大量 VRM 模型可用（VRoid Hub 百万+） |
| 风险 | QWebEngineView 仅用于 VRM，不影响 Live2D 主线 |
| **推荐** | ✅ **方案 A：QWebEngineView + three-vrm** |
