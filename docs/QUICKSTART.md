# 🚀 咕咕嘎嘎 AI VTuber - 快速启动指南

## 📋 前置要求

### ⚠️ 必须安装 Python 3.11
```bash
# 下载地址
https://www.python.org/downloads/release/python-3110/

# 验证安装
py -3.11 --version
# 应该显示: Python 3.11.x
```

**重要**：必须是 Python 3.11，其他版本可能导致依赖冲突！

---

## 🔧 第一步：安装依赖

### 运行 `install_deps.bat`

```cmd
install_deps.bat
```

**这个脚本会自动完成：**

1. ✅ **检查 Python 3.11** - 确保使用正确版本
2. ✅ **升级 pip** - 使用清华源加速
3. ✅ **安装核心依赖** - pyyaml, requests, websockets 等
4. ✅ **安装 ASR** - Faster-Whisper 语音识别
5. ✅ **安装 TTS** - Edge TTS 语音合成
6. ✅ **安装 ChatTTS** - 本地 TTS 引擎（可选，需要 GPU）
7. ✅ **安装 OpenAudio S1-mini** - fish-speech TTS（可选）
8. ✅ **安装记忆系统** - sentence-transformers, chromadb
9. ✅ **安装视觉模块** - opencv-python
10. ✅ **安装构建工具** - pyinstaller, pywin32

### 安装过程说明

```
[1/8] Checking Python 3.11...        # 检查 Python 版本
[2/8] Upgrading pip...                # 升级 pip
[3/8] Installing core dependencies... # 核心依赖
[4/8] Installing ASR...               # 语音识别
[5/8] Installing TTS...               # 语音合成
[6/8] ChatTTS (Optional)...           # ChatTTS（可选）
[6.5/8] OpenAudio S1-mini...          # OpenAudio（可选）
[7/8] Installing Memory System...     # 记忆系统
[8/8] Installing Vision...            # 视觉模块
[Build] Installing build tools...     # 构建工具
```

### 特殊依赖处理

#### OpenAudio S1-mini 依赖
```bash
# 自动安装以下依赖（解决版本冲突）
torch==2.5.1
torchaudio==2.5.1
vector-quantize-pytorch==1.14.0
einx==0.2.2
protobuf==3.19.6
fish-speech (从本地 fish-speech-src 安装)
```

#### 使用清华源加速
脚本自动使用清华源：
```
https://pypi.tuna.tsinghua.edu.cn/simple
```
如果失败会自动切换到官方源。

---

## 🎮 第二步：启动程序

### 运行 `go.bat`

```cmd
go.bat
```

**这个脚本会自动完成：**

1. ✅ **检查 Python 3.11** - 确保使用正确版本
2. ✅ **切换到 app 目录** - 进入主程序目录
3. ✅ **启动 TTS API**（可选）- 如果存在 tts_api.py
4. ✅ **检查 OpenAudio API** - 如果未运行则自动启动
5. ✅ **启动主程序** - 运行 main.py

### 启动流程

```
========================================
   GuguGaga AI Virtual Character
========================================

[INFO] Current directory: C:\...\app
[INFO] Starting TTS API on port 12396...
[INFO] Checking OpenAudio API...
[INFO] OpenAudio API not running, starting...
[INFO] Starting AI VTuber...

🐱 初始化咕咕嘎嘎 AI虚拟形象
========================================
```

### 自动启动的服务

| 服务 | 端口 | 说明 |
|------|------|------|
| **主程序 Web** | 12393 | 主界面 |
| **WebSocket** | 12394 | 实时通信 |
| **TTS API** | 12396 | TTS 测试接口（可选）|
| **OpenAudio API** | 8080 | fish-speech TTS |

---

## 🌐 访问界面

启动成功后，打开浏览器访问：

```
http://localhost:12393
```

---

## 🔍 故障排查

### 问题 1：Python 3.11 未找到

**错误信息：**
```
[ERROR] Python 3.11 not found. Please install Python 3.11
```

**解决方案：**
1. 下载并安装 Python 3.11：https://www.python.org/downloads/
2. 安装时勾选 "Add Python to PATH"
3. 重新运行 `install_deps.bat`

### 问题 2：依赖安装失败

**错误信息：**
```
ERROR: Could not find a version that satisfies the requirement...
```

**解决方案：**
```cmd
# 手动安装失败的包
py -3.11 -m pip install <package_name> -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或使用官方源
py -3.11 -m pip install <package_name>
```

### 问题 3：OpenAudio API 启动失败

**错误信息：**
```
[INFO] OpenAudio API not running, starting...
```

**解决方案：**
1. 检查模型文件是否完整：
   ```
   app/OpenAudio S1-Mini/
   ├── model.pth (1.7GB)
   ├── codec.pth (1.8GB)
   ├── config.json
   ├── tokenizer.tiktoken
   └── special_tokens.json
   ```

2. 手动启动 fish-speech API：
   ```cmd
   cd fish-speech-src
   python -m tools.api_server --llama-checkpoint-path checkpoints\openaudio-s1-mini --decoder-checkpoint-path checkpoints\openaudio-s1-mini\codec.pth --decoder-config-name modded_dac_vq --device cuda --listen 0.0.0.0:8080 --api-key openaudio123 --workers 1
   ```

3. 测试 API：
   ```cmd
   curl http://127.0.0.1:8080/health
   ```

### 问题 4：CUDA 不可用

**错误信息：**
```
CUDA not available, using CPU
```

**解决方案：**
1. 确认显卡驱动已安装
2. 安装 CUDA 版本的 PyTorch：
   ```cmd
   py -3.11 -m pip install torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu118
   ```

### 问题 5：端口被占用

**错误信息：**
```
OSError: [WinError 10048] 通常每个套接字地址只允许使用一次
```

**解决方案：**
```cmd
# 查看端口占用
netstat -ano | findstr :12393
netstat -ano | findstr :8080

# 结束占用进程
taskkill /PID <进程ID> /F
```

---

## 📚 其他脚本

### `go_debug.bat` - 调试模式
```cmd
go_debug.bat
```
显示详细的环境信息和错误日志。

### `start_fish_api.bat` - 单独启动 OpenAudio API
```cmd
start_fish_api.bat
```
仅启动 fish-speech API 服务器。

### `test_openaudio.py` - 测试 OpenAudio 配置
```cmd
py -3.11 test_openaudio.py
```
诊断 OpenAudio TTS 配置问题。

---

## 🎯 完整启动流程

### 首次使用

```cmd
# 1. 安装依赖（只需运行一次）
install_deps.bat

# 2. 启动程序
go.bat

# 3. 打开浏览器
http://localhost:12393
```

### 日常使用

```cmd
# 直接启动
go.bat
```

---

## 📝 配置文件

主配置文件：`app/config.yaml`

```yaml
# TTS 引擎选择
tts:
  provider: "chattts"  # 可选: edge, chattts, openaudio
  
# LLM 配置
llm:
  provider: "minimax"
  minimax:
    api_key: "your-api-key"
    base_url: "http://120.24.86.32:3000/v1"
    model: "MiniMax-M2.7"

# Live2D 配置
live2d:
  enabled: true
  model_path: "./app/web/assets/model/shizuku"
```

---

## 🆘 获取帮助

### 查看日志
```
logs/
├── main.log       # 主程序日志
├── security.log   # 安全日志
└── tts.log        # TTS 日志
```

### 查看文档
```
docs/
├── README.md                  # 文档索引
├── BUILD.md                   # 构建指南
├── CODE_REVIEW_REPORT.md     # 代码审计
├── INTEGRATION_GUIDE.md      # 集成指南
└── VERSION.md                 # 版本历史
```

---

## ✨ 功能特性

- 🎤 **语音识别**：FasterWhisper 本地 ASR
- 🧠 **智能对话**：MiniMax LLM (Claude Opus 4.6)
- 🔊 **语音合成**：ChatTTS + EdgeTTS + OpenAudio 三引擎
- 🎭 **虚拟形象**：Live2D 模型展示
- 💾 **智能记忆**：分层记忆系统（短期/中期/长期）
- 🛠️ **工具系统**：SubAgent 工具执行
- 🌐 **Web 界面**：实时交互界面

---

**祝你使用愉快！🎉**
