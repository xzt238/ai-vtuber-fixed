# 🏗️ 构建与打包指南

> **最后更新**: 2026-05-07 | **适用版本**: v1.9.90+

## 前置要求
- Python 3.11（嵌入式 Python 在 python/ 目录）
- PyInstaller（自动安装）
- NSIS 或 Inno Setup（可选，用于安装器）

## 1. WebUI 模式构建
运行 `scripts/go.bat` 或手动:
```
python app/main.py
```

## 2. pywebview 桌面模式构建
### 开发运行
```
python launcher/launcher.py
```

### 打包为 EXE
```
cd launcher
py -3.11 -m PyInstaller launcher.spec --clean --noconfirm
```
输出: `dist/GuguGaga.exe`

## 3. PySide6 原生桌面模式构建
### 开发运行
```
python native/main.py
```

### 打包为 EXE
```
cd native
build.bat
```
前置: Python 3.11 + PySide6 + live2d-py + qfluentwidgets
输出: `dist/GuguGagaNative/`

### Windows 版本信息
- 版本信息文件: `native/gugu_native/resources/version_info.txt`
- 图标生成: `native/gugu_native/resources/generate_icons.py`
- 安装器: `native/gugu_setup.iss`（Inno Setup）

## 4. 安装器构建
```
cd scripts
makensis installer.nsi
```
或使用 Inno Setup 编译 `native/gugu_setup.iss`

## 5. 常见构建问题
- **PySide6 import 失败**: 确认 Python 3.11 环境中已安装
- **live2d-py 加载失败**: 确认 DLL 已解锁（`scripts/setup.bat` 会自动处理）
- **CUDA 不可用**: GPT-SoVITS 将自动降级到 CPU 模式
- **端口占用**: 默认 HTTP 12393 / WS 12394，检查端口占用

## 6. 版本号同步
构建前确认版本号已更新，参见 MODIFICATION_GUIDE.md → M-001
