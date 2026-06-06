# 跨平台适配修改计划

## 📋 需要修改的文件

### 1. native/main.py

#### 1.1 依赖检查函数 (_check_dependencies)
**问题**: 使用Windows特定的`ctypes.windll.user32.MessageBoxW`
**修改方案**: 使用平台抽象层的`show_message`函数

```python
# 修改前
def _check_dependencies():
    """检查关键依赖（PySide6），失败时弹出 Windows 消息框"""
    try:
        import PySide6
    except ImportError:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            "PySide6 未安装!\n请先运行 scripts\\install_deps.bat 安装依赖。",
            "咕咕嘎嘎 - 启动失败",
            0x10
        )
        sys.exit(1)

# 修改后
def _check_dependencies():
    """检查关键依赖（PySide6），失败时弹出跨平台消息框"""
    try:
        import PySide6
    except ImportError:
        from app.platform_abstraction import show_message
        show_message(
            "咕咕嘎嘎 - 启动失败",
            "PySide6 未安装!\n请先运行安装脚本安装依赖。",
            level="error"
        )
        sys.exit(1)
```

#### 1.2 字体设置
**问题**: 使用Windows特定的"Microsoft YaHei UI"字体
**修改方案**: 检测操作系统，使用系统默认字体

```python
# 修改前
app.setFont(QFont("Microsoft YaHei UI", 10))

# 修改后
import platform
if platform.system() == "Windows":
    font_family = "Microsoft YaHei UI"
elif platform.system() == "Darwin":
    font_family = "PingFang SC"
else:
    font_family = "Noto Sans CJK SC"
app.setFont(QFont(font_family, 10))
```

#### 1.3 图标文件
**问题**: 使用`.ico`图标文件
**修改方案**: 检测操作系统，使用对应的图标格式

```python
# 修改前
icon_path = os.path.join(NATIVE_DIR, "gugu_native", "resources", "app.ico")
if os.path.exists(icon_path):
    app.setWindowIcon(QIcon(icon_path))

# 修改后
import platform
if platform.system() == "Windows":
    icon_name = "app.ico"
elif platform.system() == "Darwin":
    icon_name = "app.icns"
else:
    icon_name = "app.png"
icon_path = os.path.join(NATIVE_DIR, "gugu_native", "resources", icon_name)
if os.path.exists(icon_path):
    app.setWindowIcon(QIcon(icon_path))
```

#### 1.4 FFmpeg扫描加速
**问题**: 仅在Windows上需要
**修改方案**: 已经是跨平台的（使用`os.name == 'nt'`检测）

### 2. app/main.py

#### 2.1 Windows GBK编码安全网
**问题**: 仅在Windows上需要
**修改方案**: 已经是跨平台的（使用`sys.platform == "win32"`检测）

#### 2.2 Windows subprocess安全辅助函数
**问题**: 仅在Windows上需要
**修改方案**: 已经是跨平台的（使用`sys.platform != "win32"`检测）

### 3. app/platform_abstraction.py

**现状**: 已经是跨平台的，不需要修改

### 4. 启动脚本

#### 4.1 scripts/start.bat
**问题**: Windows批处理脚本
**修改方案**: 创建跨平台启动脚本

```bash
# 创建 scripts/start.sh (macOS/Linux)
#!/bin/bash
cd "$(dirname "$0")/.."
python native/main.py "$@"
```

#### 4.2 scripts/go.bat
**问题**: Windows批处理脚本
**修改方案**: 创建跨平台启动脚本

```bash
# 创建 scripts/go.sh (macOS/Linux)
#!/bin/bash
cd "$(dirname "$0")/.."
python -m app.main "$@"
```

---

## 📊 修改优先级

### 高优先级（必须修改）
1. **依赖检查函数** - 使用跨平台消息框
2. **字体设置** - 使用系统默认字体
3. **图标文件** - 使用对应格式

### 中优先级（建议修改）
4. **启动脚本** - 创建跨平台版本
5. **文档更新** - 更新安装说明

### 低优先级（可选修改）
6. **FFmpeg扫描加速** - 已经是跨平台的
7. **编码安全网** - 已经是跨平台的

---

## 🎯 预期成果

### 修改完成后
- **macOS支持**: 完整功能支持
- **Linux支持**: 完整功能支持
- **跨平台部署**: 统一的部署流程
- **用户体验**: 一致的用户体验

### 测试验证
- **macOS测试**: 在macOS上测试所有功能
- **Linux测试**: 在Linux上测试所有功能
- **兼容性测试**: 确保Windows功能不受影响

---

**计划制定时间**: 2026-06-03 08:26:00  
**计划制定人**: 齐活林（Qi）· 交付总监