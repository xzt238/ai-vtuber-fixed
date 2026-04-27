# 🖥️ GuguGaga AI VTuber — 桌面应用打包技术规划

> **版本**: v1.0  
> **日期**: 2026-04-21  
> **状态**: 规划中  
> **目标**: 将 Web 应用打包为原生桌面客户端（.exe 安装器），所有模型内嵌，开箱即用

---

## 1. 项目背景与目标

### 1.1 现状

GuguGaga AI VTuber 目前是一个基于 Python 的 AI 虚拟主播应用，前端通过浏览器访问 `http://localhost:12393`。用户使用流程：

```
安装 Python 3.11 → clone 仓库 → 运行 install_deps.bat → 双击 go.bat → 打开浏览器访问
```

**痛点**：
- 部署流程复杂，非技术用户难以上手
- 需要手动安装 Python、配置环境
- 模型需要单独下载（10-20GB），网络/适配问题多
- 通过浏览器访问，没有"软件"的感觉

### 1.2 目标

将整个应用打包为一个**原生桌面应用程序**：

- **双击 .exe 即可启动**，无需安装 Python、无需下载模型
- **内置桌面窗口**（Electron），不再需要打开浏览器
- **NSIS 安装向导**，像安装正常软件一样（选择目录、创建快捷方式、开始菜单）
- **所有模型内嵌**，包括 MiniCPM-V2 视觉模型，完整功能

### 1.3 用户使用流程（目标）

```
下载 GuguGaga-Setup-v1.8.2.exe (~10-15GB)
    ↓
双击运行安装向导（选择安装目录、创建桌面快捷方式）
    ↓
安装完成，双击桌面快捷方式 "GuguGaga AI VTuber"
    ↓
应用启动 → 显示启动画面 → 后端加载完成 → 进入主界面
    ↓
在桌面窗口内操作（与 Web UI 完全一致）
    ↓
关闭窗口 → 自动清理 → 退出
```

---

## 2. 技术架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    GuguGaga.exe (Electron)                │
│                                                          │
│  ┌──────────────┐    ┌───────────────────────────────┐   │
│  │  主进程       │    │  渲染进程 (BrowserWindow)      │   │
│  │  main.js     │    │                               │   │
│  │              │    │  ┌─────────────────────────┐  │   │
│  │  • 启动 Python│───→│  │  http://localhost:12393 │  │   │
│  │  • 健康检查   │    │  │  (现有 Web UI 零修改)    │  │   │
│  │  • 进程管理   │    │  │                         │  │   │
│  │  • 系统托盘   │    │  │  ws://localhost:12394   │  │   │
│  │  • 自动更新   │    │  │  (WebSocket 实时通信)   │  │   │
│  └──────┬───────┘    │  └─────────────────────────┘  │   │
│         │            └───────────────────────────────┘   │
└─────────│────────────────────────────────────────────────┘
          │ spawn
          ▼
┌─────────────────────────────────────────────────────────┐
│               Python 后端 (app.main)                      │
│                                                          │
│  HTTP Server  :0.12393    WebSocket   :0.12394           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │   ASR   │ │   LLM   │ │   TTS   │ │  Vision │       │
│  │ Whisper │ │ OpenAI  │ │GPT-SoVITS│ │MiniCPM-V│       │
│  │ FunASR  │ │ Anthro  │ │ EdgeTTS │ │         │       │
│  └─────────┘ │ MiniMax │ └─────────┘ └─────────┘       │
│              └─────────┘                                 │
└─────────────────────────────────────────────────────────┘
```

### 2.2 技术选型

| 组件 | 技术 | 理由 |
|------|------|------|
| **桌面壳** | Electron | 生态成熟、跨平台、内嵌 Chromium 不依赖系统组件 |
| **打包** | electron-builder | Electron 标准打包工具，支持 NSIS 安装器 |
| **安装器** | NSIS (Nullsoft Scriptable Install System) | 通过 electron-builder 自动生成，专业安装向导体验 |
| **Python 管理** | 系统 Python 3.11 + 检测脚本 | 不内嵌 Python（节省 100MB+），首次启动检测并引导安装 |
| **模型存储** | 安装器内嵌 | 所有模型打进安装包，用户无需单独下载 |

### 2.3 为什么选择 Electron

| 对比项 | Electron | Tauri | PyWebView | PyQt 重写 |
|--------|----------|-------|-----------|-----------|
| 前端改动量 | **零** | **零** | **零** | **全部重写** |
| 打包体积 | ~200MB 壳 | ~10MB 壳 | ~5MB 壳 | N/A |
| 系统依赖 | 无（自带 Chromium） | 需要 WebView2 | 需要系统浏览器 | 无 |
| 进程管理能力 | **强**（Node.js） | 中（Rust） | 弱 | 强 |
| 生态/文档 | **最成熟** | 成长中 | 有限 | 成熟 |
| 本地化 CDN | 简单 | 简单 | 复杂 | N/A |

**结论**：Electron 壳虽然大 200MB，但对于 15-25GB 的总体积来说可以忽略不计。它的进程管理能力（Node.js spawn 子进程、健康检查轮询、信号处理）对管理 Python 后端至关重要。

---

## 3. 现有项目分析

### 3.1 前端架构

- **技术栈**：纯 Vanilla JS 单体 SPA（无框架、无 npm 依赖、无构建步骤）
- **入口文件**：`app/web/static/index.html`（7286 行，包含所有 HTML/CSS/JS）
- **通信方式**：
  - HTTP API：`http://localhost:12393/api/...`
  - WebSocket：`ws://localhost:12394`
- **CDN 依赖**（需要本地化）：
  - PixiJS v7（Live2D 渲染）
  - oh-my-live2d（Live2D 控制）
  - Google Fonts（Noto Sans SC）

### 3.2 后端架构

- **HTTP 服务器**：Python 标准库 `http.server`（`app/web/__init__.py`）
- **WebSocket**：`websocket-server` 库
- **端口**：HTTP 12393 / WebSocket 12394
- **启动入口**：`py -3.11 -m app.main`（通过 `go.bat`）

### 3.3 硬编码路径问题（必须修复）

打包前必须将所有硬编码路径改为相对路径，否则换目录就跑不了：

| 优先级 | 文件 | 位置 | 当前值 | 修复方式 |
|--------|------|------|--------|---------|
| **P0** | `app/trainer/manager.py` | L66 | `PYTHON = r"C:\Users\x\..."` | `sys.executable` |
| **P0** | `GPT-SoVITS/.../tts_infer.yaml` | custom 区块 | 4 处绝对路径 | 相对路径（基于安装目录） |
| **P1** | `GPT-SoVITS/extract_hubert.py` | 多处 | 6 处绝对路径 | 相对路径 |
| **P1** | `GPT-SoVITS/.../s2_web_hongkong.json` | 多处 | 2 处绝对路径 | 相对路径 |
| **P2** | `GPT-SoVITS/data/web_projects/.../config.json` | 1 处 | 1 处绝对路径 | 相对路径 |

---

## 4. 详细实施计划

### 阶段 1：路径可移植化（预计 30 分钟）

**目标**：确保项目可以在任意目录下运行。

**任务清单**：
- [ ] 1.1 `app/trainer/manager.py` — 将 `PYTHON` 改为 `sys.executable`
- [ ] 1.2 `GPT-SoVITS/GPT_SoVITS/configs/tts_infer.yaml` — custom 区块路径改相对路径
- [ ] 1.3 `GPT-SoVITS/extract_hubert.py` — 路径改相对路径
- [ ] 1.4 `GPT-SoVITS/GPT_SoVITS/configs/s2_web_hongkong.json` — 路径改相对路径
- [ ] 1.5 `GPT-SoVITS/data/web_projects/hongkong/config.json` — 路径改相对路径
- [ ] 1.6 全局搜索确认无遗漏的硬编码路径

**验证**：将项目复制到不同目录，运行 `go.bat` 确认正常启动。

---

### 阶段 2：CDN 资源本地化（预计 15 分钟）

**目标**：去除对外部 CDN 的依赖，确保离线可用。

**任务清单**：
- [ ] 2.1 下载 PixiJS v7 到 `app/web/static/libs/pixi.min.js`
- [ ] 2.2 下载 oh-my-live2d 到 `app/web/static/libs/oh-my-live2d/`
- [ ] 2.3 下载 Google Fonts (Noto Sans SC) 到 `app/web/static/libs/fonts/`
- [ ] 2.4 修改 `index.html` 中的 CDN 引用为本地路径
- [ ] 2.5 离线测试：断网后刷新页面确认资源加载正常

---

### 阶段 3：Electron 壳（预计 2-3 小时）

**目标**：创建 Electron 桌面应用，包装现有 Web UI。

#### 3.1 目录结构

```
electron/
├── package.json          ← Electron 项目配置
├── main.js               ← Electron 主进程
├── preload.js            ← 预加载脚本（安全桥接）
├── splash.html           ← 启动画面
├── assets/
│   ├── icon.ico          ← 应用图标（256x256）
│   ├── icon.png          ← 应用图标（512x512）
│   ├── splash-bg.png     ← 启动画面背景
│   └── tray-icon.png     ← 系统托盘图标
└── build/                ← electron-builder 配置
    └── nsis.nsh          ← NSIS 自定义安装脚本
```

#### 3.2 `package.json` 配置

```jsonc
{
  "name": "gugugaga-ai-vtuber",
  "version": "1.8.2",
  "description": "GuguGaga AI VTuber 桌面客户端",
  "main": "main.js",
  "scripts": {
    "start": "electron .",
    "build": "electron-builder --win",
    "build:dir": "electron-builder --win --dir"
  },
  "build": {
    "appId": "com.gugugaga.ai-vtuber",
    "productName": "GuguGaga AI VTuber",
    "win": {
      "target": ["nsis"],
      "icon": "assets/icon.ico"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true,
      "createDesktopShortcut": true,
      "createStartMenuShortcut": true,
      "shortcutName": "GuguGaga AI VTuber",
      "installerIcon": "assets/icon.ico",
      "uninstallerIcon": "assets/icon.ico",
      "installerHeaderIcon": "assets/icon.ico",
      "license": "../LICENSE"
    },
    "files": [
      "main.js",
      "preload.js",
      "splash.html",
      "assets/**/*",
      "../app/**/*",
      "../GPT-SoVITS/**/*",
      "../go.bat",
      "../install_deps.bat"
    ],
    "extraResources": [
      {
        "from": "../models",
        "to": "models",
        "filter": ["**/*"]
      }
    ]
  },
  "devDependencies": {
    "electron": "^28.0.0",
    "electron-builder": "^24.0.0"
  }
}
```

#### 3.3 `main.js` 核心逻辑

```javascript
const { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

let mainWindow = null;
let splashWindow = null;
let pythonProcess = null;
let tray = null;

// ==================== Python 后端管理 ====================

const PYTHON_CMD = 'py';
const PYTHON_ARGS = ['-3.11', '-m', 'app.main'];
const BACKEND_URL = 'http://localhost:12393';
const BACKEND_WS = 'ws://localhost:12394';
const HEALTH_CHECK_INTERVAL = 1000;  // 1 秒
const HEALTH_CHECK_TIMEOUT = 300000; // 5 分钟超时

/**
 * 启动 Python 后端进程
 */
function startPythonBackend() {
  const projectRoot = path.resolve(__dirname, '..');
  
  pythonProcess = spawn(PYTHON_CMD, PYTHON_ARGS, {
    cwd: projectRoot,
    env: { ...process.env },
    stdio: ['pipe', 'pipe', 'pipe'],
    shell: true
  });

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Python] ${data}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[Python:ERR] ${data}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`Python 后端退出，代码: ${code}`);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.close();
    }
  });

  pythonProcess.on('error', (err) => {
    console.error('无法启动 Python 后端:', err);
    // 显示错误对话框
    dialog.showErrorBox(
      '启动失败',
      `无法启动 Python 后端。\n\n` +
      `请确保已安装 Python 3.11。\n` +
      `错误信息: ${err.message}`
    );
    app.quit();
  });
}

/**
 * 健康检查 — 轮询后端直到就绪
 */
function waitForBackend() {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();

    const check = () => {
      if (Date.now() - startTime > HEALTH_CHECK_TIMEOUT) {
        reject(new Error('后端启动超时'));
        return;
      }

      http.get(`${BACKEND_URL}/api/status`, (res) => {
        if (res.statusCode === 200) {
          resolve();
        } else {
          setTimeout(check, HEALTH_CHECK_INTERVAL);
        }
      }).on('error', () => {
        setTimeout(check, HEALTH_CHECK_INTERVAL);
      });
    };

    setTimeout(check, 2000); // 等 2 秒再开始检查
  });
}

/**
 * 停止 Python 后端
 */
function stopPythonBackend() {
  if (pythonProcess) {
    pythonProcess.kill('SIGTERM');
    // 3 秒后强制终止
    setTimeout(() => {
      if (pythonProcess && !pythonProcess.killed) {
        pythonProcess.kill('SIGKILL');
      }
    }, 3000);
  }
}

// ==================== 窗口管理 ====================

/**
 * 创建启动画面
 */
function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 500,
    height: 350,
    transparent: true,
    frame: false,
    resizable: false,
    center: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  splashWindow.loadFile('splash.html');
}

/**
 * 创建主窗口
 */
function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 768,
    title: 'GuguGaga AI VTuber',
    icon: path.join(__dirname, 'assets', 'icon.ico'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  mainWindow.loadURL(BACKEND_URL);

  mainWindow.on('close', (e) => {
    // 最小化到托盘而不是关闭
    if (process.platform === 'win32') {
      e.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

/**
 * 创建系统托盘
 */
function createTray() {
  const icon = nativeImage.createFromPath(
    path.join(__dirname, 'assets', 'tray-icon.png')
  );
  
  tray = new Tray(icon);
  tray.setToolTip('GuguGaga AI VTuber');

  const contextMenu = Menu.buildFromTemplate([
    { label: '显示主窗口', click: () => mainWindow?.show() },
    { type: 'separator' },
    { label: '退出', click: () => {
      stopPythonBackend();
      app.quit();
    }}
  ]);

  tray.setContextMenu(contextMenu);
  tray.on('double-click', () => mainWindow?.show());
}

// ==================== 应用生命周期 ====================

app.whenReady().then(async () => {
  createSplashWindow();
  createTray();

  try {
    startPythonBackend();
    await waitForBackend();
    
    // 后端就绪，关闭启动画面，打开主窗口
    splashWindow?.close();
    createMainWindow();
  } catch (err) {
    splashWindow?.close();
    dialog.showErrorBox('启动失败', `后端启动失败: ${err.message}`);
    app.quit();
  }
});

app.on('window-all-closed', () => {
  stopPythonBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  stopPythonBackend();
});

// ==================== IPC 通信 ====================

// 预加载脚本通过 contextBridge 暴露的 API
// 这里不需要额外的 IPC，因为前端直接通过 HTTP/WS 与 Python 后端通信
```

#### 3.4 `preload.js`

```javascript
const { contextBridge, ipcRenderer } = require('electron');

// 向渲染进程暴露 Electron API
// 前端可以通过 window.electronAPI 访问
contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  isElectron: true,
  
  // 最小化窗口
  minimize: () => ipcRenderer.invoke('window-minimize'),
  
  // 最大化/还原窗口
  maximize: () => ipcRenderer.invoke('window-maximize'),
  
  // 关闭窗口（最小化到托盘）
  close: () => ipcRenderer.invoke('window-close'),
  
  // 获取应用版本
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  
  // 获取安装目录
  getAppPath: () => ipcRenderer.invoke('get-app-path')
});
```

#### 3.5 `splash.html`（启动画面）

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      width: 500px; height: 350px;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      font-family: 'Segoe UI', sans-serif; color: white;
      overflow: hidden;
    }
    .logo { width: 120px; height: 120px; margin-bottom: 24px; }
    .title { font-size: 28px; font-weight: 700; margin-bottom: 12px; }
    .subtitle { font-size: 14px; opacity: 0.8; margin-bottom: 40px; }
    .progress-container {
      width: 300px; height: 4px;
      background: rgba(255,255,255,0.2);
      border-radius: 2px; overflow: hidden;
    }
    .progress-bar {
      width: 0%; height: 100%;
      background: white;
      border-radius: 2px;
      animation: loading 3s ease-in-out infinite;
    }
    .status {
      margin-top: 16px; font-size: 13px;
      opacity: 0.7;
    }
    @keyframes loading {
      0% { width: 0%; margin-left: 0; }
      50% { width: 60%; margin-left: 20%; }
      100% { width: 0%; margin-left: 100%; }
    }
  </style>
</head>
<body>
  <img class="logo" src="assets/icon.png" alt="Logo">
  <div class="title">GuguGaga AI VTuber</div>
  <div class="subtitle">正在启动后端服务...</div>
  <div class="progress-container">
    <div class="progress-bar"></div>
  </div>
  <div class="status">加载模型和初始化引擎中，请稍候...</div>
</body>
</html>
```

#### 3.6 任务清单

- [ ] 3.1 创建 `electron/` 目录结构
- [ ] 3.2 编写 `package.json`
- [ ] 3.3 编写 `main.js`（主进程）
- [ ] 3.4 编写 `preload.js`（预加载脚本）
- [ ] 3.5 编写 `splash.html`（启动画面）
- [ ] 3.6 设计/导出应用图标（.ico + .png）
- [ ] 3.7 实现系统托盘功能
- [ ] 3.8 实现窗口控制（最小化、最大化、关闭到托盘）
- [ ] 3.9 测试 Electron 启动 + 加载 Web UI

---

### 阶段 4：NSIS 安装器配置（预计 2-3 小时）

**目标**：使用 electron-builder + NSIS 生成专业安装向导。

#### 4.1 electron-builder 完整配置

在 `electron/package.json` 的 `build` 字段中详细配置：

```jsonc
{
  "build": {
    "appId": "com.gugugaga.ai-vtuber",
    "productName": "GuguGaga AI VTuber",
    "copyright": "Copyright © 2026 GuguGaga",
    
    "directories": {
      "output": "../dist",
      "buildResources": "assets"
    },
    
    "win": {
      "target": [
        {
          "target": "nsis",
          "arch": ["x64"]
        }
      ],
      "icon": "assets/icon.ico",
      "requestedExecutionLevel": "requireAdministrator",
      "signAndEditExecutable": false
    },
    
    "nsis": {
      "oneClick": false,
      "perMachine": true,
      "allowToChangeInstallationDirectory": true,
      "allowElevation": true,
      "installerIcon": "assets/icon.ico",
      "uninstallerIcon": "assets/icon.ico",
      "installerHeaderIcon": "assets/icon.ico",
      "createDesktopShortcut": true,
      "createStartMenuShortcut": true,
      "shortcutName": "GuguGaga AI VTuber",
      "deleteAppDataOnUninstall": false,
      "displayLanguageSelector": false,
      "language": 2052,  // 简体中文
      
      // 自定义 NSIS 脚本
      "include": "build/nsis.nsh"
    },
    
    "files": [
      "main.js",
      "preload.js",
      "splash.html",
      "assets/**/*",
      // Python 应用代码
      "../app/**/*",
      "!../app/__pycache__/**/*",
      "!../app/**/__pycache__/**/*",
      // GPT-SoVITS TTS 引擎
      "../GPT-SoVITS/**/*",
      "!../GPT-SoVITS/TEMP/**/*",
      "!../GPT-SoVITS/logs/**/*",
      "!../GPT-SoVITS/runtime/**/*",
      "!../GPT-SoVITS/**/__pycache__/**/*",
      // 启动脚本
      "../go.bat",
      "../install_deps.bat",
      // 版本信息
      "../docs/VERSION.md"
    ],
    
    "extraResources": [
      {
        "from": "../models",
        "to": "models",
        "filter": ["**/*"]
      }
    ],
    
    "compression": "maximum"
  }
}
```

#### 4.2 自定义 NSIS 安装脚本 (`build/nsis.nsh`)

```nsi
; ==========================================
; GuguGaga AI VTuber - NSIS 自定义安装脚本
; ==========================================

; 自定义安装页面 — Python 环境检测
!macro CustomPageAfterInstall
  ; 安装完成后检查 Python 3.11
  nsExec::ExecToLog 'py -3.11 --version'
  Pop $0
  ${If} $0 != "0"
    MessageBox MB_YESNO|MB_ICONQUESTION \
      "未检测到 Python 3.11，是否打开 Python 下载页面？$\n$\n\
       应用需要 Python 3.11 才能运行。" \
      IDYES DownloadPython IDNO SkipPython
    
    DownloadPython:
      ExecShell::open "https://www.python.org/downloads/"
    
    SkipPython:
  ${EndIf}
!macroend

; 自定义卸载页面 — 清理确认
!macro CustomUnInstall
  MessageBox MB_YESNO|MB_ICONQUESTION \
    "是否删除所有用户数据（配置、模型缓存等）？$\n$\n\
     选择【否】将保留配置文件。" \
    IDYES DeleteAllData IDNO KeepData
  
  DeleteAllData:
    RMDir /r "$APPDATA\GuguGaga"
  
  KeepData:
!macroend

; 安装完成后显示 README
!macro FinishPageShowReadme
  !insertmacro MUI_FINISHPAGE_SHOW "$INSTDIR\docs\README.md"
!macroend
```

#### 4.3 任务清单

- [ ] 4.1 完善 `electron-builder` 配置
- [ ] 4.2 编写 NSIS 自定义安装脚本
- [ ] 4.3 配置安装向导页面（欢迎页、目录选择、安装进度、完成页）
- [ ] 4.4 配置卸载清理逻辑
- [ ] 4.5 配置文件排除列表（`__pycache__`、`TEMP`、`logs` 等）
- [ ] 4.6 配置压缩选项（maximum 压缩，减小安装包体积）

---

### 阶段 5：Python 环境检测与引导（预计 1 小时）

**目标**：首次启动时检测 Python 3.11，不存在则引导安装。

#### 5.1 检测流程

```
Electron 启动
    ↓
检测 py -3.11 --version
    ↓
┌── 有 Python 3.11 ──→ 启动 Python 后端 → 正常流程
│
└── 没有 Python 3.11
    ↓
    显示对话框："需要安装 Python 3.11"
    ├── [下载 Python] → 打开 python.org 下载页
    ├── [我已经安装了] → 让用户指定 Python 路径
    └── [取消] → 退出应用
```

#### 5.2 在 `main.js` 中实现

```javascript
const { execSync } = require('child_process');

/**
 * 检测 Python 3.11 是否可用
 * @returns {{ available: boolean, version: string|null, path: string|null }}
 */
function checkPython() {
  try {
    const version = execSync('py -3.11 --version', {
      encoding: 'utf-8',
      timeout: 5000
    }).trim();
    
    const path = execSync('py -3.11 -c "import sys; print(sys.executable)"', {
      encoding: 'utf-8',
      timeout: 5000
    }).trim();
    
    return { available: true, version, path };
  } catch {
    return { available: false, version: null, path: null };
  }
}
```

#### 5.3 任务清单

- [ ] 5.1 实现 Python 3.11 检测函数
- [ ] 5.2 实现"未找到 Python"对话框
- [ ] 5.3 实现"指定 Python 路径"功能
- [ ] 5.4 实现 Python 路径配置持久化（写入用户配置文件）

---

### 阶段 6：集成测试（预计 1-2 小时）

**目标**：全流程测试，确保打包后的应用可以正常安装和运行。

#### 6.1 测试用例

| # | 测试场景 | 预期结果 | 优先级 |
|---|---------|---------|--------|
| T1 | 全新 Windows 10 电脑安装 | 安装向导正常，文件完整 | P0 |
| T2 | 安装后首次启动 | 启动画面显示 → 后端加载 → 主窗口打开 | P0 |
| T3 | Web UI 所有功能正常 | 配置、对话、Live2D、TTS 等功能正常 | P0 |
| T4 | 关闭窗口 → 最小化到托盘 | 窗口隐藏，托盘图标存在 | P1 |
| T5 | 系统托盘菜单 | 显示窗口、退出功能正常 | P1 |
| T6 | 桌面快捷方式 | 双击可以启动应用 | P0 |
| T7 | 开始菜单快捷方式 | 从开始菜单可以启动 | P2 |
| T8 | 卸载 | 卸载向导正常，可选清理用户数据 | P1 |
| T9 | 安装到非默认目录 | 自定义路径安装后正常运行 | P1 |
| T10 | 路径含空格 | 安装到 `C:\Program Files\` 正常运行 | P0 |
| T11 | 无 Python 环境 | 显示引导安装对话框 | P1 |
| T12 | 离线运行 | 断网后所有功能正常（CDN 已本地化） | P1 |
| T13 | 长时间运行 | 8 小时连续运行无内存泄漏 | P2 |

#### 6.2 任务清单

- [ ] 6.1 本机打包测试（开发者电脑）
- [ ] 6.2 全新 Windows 10 虚拟机测试
- [ ] 6.3 全新 Windows 11 虚拟机测试
- [ ] 6.4 功能回归测试（所有 Web UI 功能）
- [ ] 6.5 卸载/重装测试
- [ ] 6.6 性能测试（内存占用、启动时间）

---

## 5. 文件体积与性能预估

### 5.1 安装包体积

| 组件 | 原始大小 | 压缩后（预估） |
|------|---------|--------------|
| Python 应用代码 (`app/`) | ~50 MB | ~15 MB |
| GPT-SoVITS 引擎 | ~2 GB | ~800 MB |
| HuggingFace 模型缓存 | ~8 GB | ~5 GB |
| MiniCPM-V2 视觉模型 | ~6 GB | ~4 GB |
| GPT-SoVITS 预训练模型 | ~3 GB | ~2 GB |
| Faster-Whisper 模型 | ~1.5 GB | ~1 GB |
| FunASR 模型 | ~1 GB | ~700 MB |
| Electron 运行时 | ~200 MB | ~100 MB |
| 前端资源 + CDN 本地化 | ~50 MB | ~30 MB |
| **总计** | **~22 GB** | **~14 GB** |

> 💡 如果觉得 14GB 太大，可以考虑：
> - 去掉 MiniCPM-V2（-4GB 压缩后）
> - Faster-Whisper 用 `tiny` 或 `base` 模型（-800MB）
> - 首次启动时按需下载非核心模型

### 5.2 启动时间预估

| 阶段 | 预计耗时 |
|------|---------|
| Electron 启动 | 1-2 秒 |
| Python 进程启动 | 2-3 秒 |
| 模型加载（GPT-SoVITS） | 5-10 秒 |
| 模型加载（Whisper） | 3-5 秒 |
| HTTP 服务器就绪 | 1 秒 |
| 前端加载 | 1-2 秒 |
| **总计（首次）** | **13-23 秒** |
| **总计（热启动）** | **5-10 秒** |

---

## 6. 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| NSIS 打包超大文件失败 | 安装器生成失败 | 中 | 分卷压缩或使用 7z SFX 替代 |
| Python 路径问题导致导入失败 | 应用启动后崩溃 | 中 | 阶段 1 的路径修复 + 充分测试 |
| Electron + Python 进程同步问题 | 主窗口打开时后端未就绪 | 低 | 健康检查轮询 + 超时处理 |
| Windows Defender 误报 | 用户无法安装 | 中 | 代码签名（需购买证书） |
| GPU 驱动不兼容 | 模型推理失败 | 低 | 启动时检测 CUDA/ROCm 可用性 |
| 内存不足（< 8GB） | 模型加载 OOM | 中 | 启动前检测可用内存并提示 |

---

## 7. 后续优化方向（V2）

这些不在当前版本范围内，作为未来优化方向记录：

- [ ] **自动更新**：检查新版本并提示用户更新（electron-updater）
- [ ] **安装时下载模型**：安装器只含代码（~500MB），首次启动下载模型（节省带宽）
- [ ] **内嵌 Python**：打包 Python 3.11 运行时，无需用户安装
- [ ] **代码签名**：购买 EV 代码签名证书，消除 Windows Defender 警告
- [ ] **增量更新**：只下载变更的文件，而不是整个安装包
- [ ] **多语言安装向导**：支持中文、英文、日文
- [ ] **macOS / Linux 支持**：Tauri 替代方案或 Electron 跨平台打包

---

## 8. 关键命令参考

```bash
# ==================== 开发阶段 ====================

# 进入 Electron 目录
cd C:\Users\x\Desktop\ai-vtuber-fixed\electron

# 安装 Electron 依赖
npm install

# 开发模式启动（热重载）
npm start

# 打包为 NSIS 安装器
npm run build

# 打包为目录模式（测试用，不生成安装器）
npm run build:dir

# ==================== 最终打包 ====================

# 完整打包（生成 .exe 安装器）
# 输出目录: dist/
npm run build

# 检查输出
dir dist\*.exe
```

---

## 附录 A：目录结构总览

```
ai-vtuber-fixed/                          # 项目根目录
├── electron/                             # 【新增】Electron 桌面壳
│   ├── package.json
│   ├── main.js
│   ├── preload.js
│   ├── splash.html
│   ├── assets/
│   │   ├── icon.ico
│   │   ├── icon.png
│   │   ├── splash-bg.png
│   │   └── tray-icon.png
│   └── build/
│       └── nsis.nsh
├── app/                                  # Python 应用（现有）
│   ├── main.py
│   ├── config.yaml
│   ├── web/
│   │   ├── __init__.py
│   │   └── static/
│   │       ├── index.html
│   │       └── libs/          # 【新增】CDN 本地化资源
│   │           ├── pixi.min.js
│   │           ├── oh-my-live2d/
│   │           └── fonts/
│   └── ...
├── GPT-SoVITS/                           # TTS 引擎（现有，路径需修复）
├── models/                               # HuggingFace 模型（现有）
├── go.bat                                # 命令行启动（保留）
├── install_deps.bat                      # 依赖安装（保留）
├── docs/
│   ├── VERSION.md
│   ├── README.md
│   └── DESKTOP_PACKAGING_PLAN.md         # 【本文件】
└── dist/                                 # 【新增】打包输出目录
    └── GuguGaga AI VTuber Setup 1.8.2.exe
```

---

> 📝 **维护说明**：本文档随实施进度更新。每个阶段完成后，在对应任务清单项打勾，并记录实际耗时和遇到的问题。
