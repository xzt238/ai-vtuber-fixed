# 复盘报告：桌面模式启动闪退事故

**日期**: 2026-06-08  
**严重级别**: P0 — 应用完全无法启动  
**影响时间**: 05:17 ~ 21:40（约 16 小时）  
**修复轮次**: 5 轮  
**相关提交**: 36 次（其中 18 次为修复提交）

---

## 一、事故时间线

| 时间 | 事件 | 触发提交 |
|------|------|---------|
| 05:17 | `__slots__` 添加到 QObject 子类 → 段错误 | `949bbde` |
| 06:53 | `logger` 定义被放入 docstring 内部 → NameError | `694d4ce` |
| 08:20 | "重复导入清理" 删除了实际使用的导入 → NameError 雪崩 | `db13937` |
| 08:25~09:05 | 第一轮修复：补导入 + 移除 QObject 的 `__slots__` | 4 次提交 |
| 10:37~12:04 | 类型注解/文档/常量重构，引入循环导入 | 多次提交 |
| 16:02 | 循环导入修复 | `289eeba` |
| 19:35 | 用户报告仍然闪退（无 Python traceback） | — |
| 19:52~20:38 | 第二轮修复：诊断 + processEvents 根因 | 6 次提交 |
| 20:47~21:01 | 第三轮修复：批量补缺失导入 | 3 次提交 |
| 21:14~21:29 | 第四轮修复：logger 位置错误 | 3 次提交 |
| 21:32~21:40 | 第五轮修复：contextmanager + threading | 2 次提交 |
| 21:36 | **应用完全正常启动** ✅ | — |

---

## 二、根因分析

### 根因 1：`__slots__` 加到 QObject 子类（05:17）

**提交**: `949bbde` — `perf: add __slots__ to key classes for memory optimization`

**问题**: 为 `AnimationController`、`ChatSession` 等类添加了 `__slots__`。其中部分是 QObject/QWidget 子类。PySide6 的元类系统与 `__slots__` 不兼容，会导致 C++ 级别的段错误（无 Python traceback）。

**额外问题**: `ChatSession.__slots__` 定义了 `("id", "name", "created_at", "messages", "metadata")`，但实际属性是 `session_id, title, messages, created_at, updated_at`。`AnimationController.__slots__` 只列了 6 个属性，但 `__init__` 里赋值了 14+ 个。

**教训**:
- ❌ QObject/QWidget 子类**绝对不能**使用 `__slots__`
- ❌ 添加 `__slots__` 前必须逐一核对 `__init__` 中所有赋值的属性
- ✅ 纯 Python 数据类可以用 `__slots__`，但必须精确匹配

---

### 根因 2：`logger` 定义被放入 docstring（06:53）

**提交**: `694d4ce` — `refactor: improve exception handling and logging`

**问题**: 批量替换 `print()` → `logger.info()` 时，脚本在文件顶部添加了 `import logging`，但把 `logger = logging.getLogger(__name__)` 插入到了模块 docstring **内部**：

```python
import logging
"""
咕咕嘎嘎 AI-VTuber — QWebEngineView 聊天显示组件

logger = logging.getLogger(__name__)   # ← 在 docstring 里面！

完整 Markdown 渲染...
"""
```

Python 不会执行 docstring 中的代码，所以 `logger` 变量从未定义。

**影响**: 9 个文件（`chat_web_display.py`、`debug_page.py`、`settings_page.py`、`animation_controller.py`、`autostart_manager.py`、`desktop_pet.py`、`hotkey_manager.py`、`session_manager.py`、`voice_manager.py`）

**教训**:
- ❌ 批量代码修改脚本不能盲目插入代码行，必须理解 AST 结构
- ✅ 插入代码后应立即运行 `ast.parse()` 验证语法
- ✅ 插入代码后应立即运行应用验证功能

---

### 根因 3："重复导入清理" 删除了实际使用的导入（08:20）

**提交**: `db13937` — `perf: remove duplicate imports and optimize code`

**问题**: 脚本将"同一模块出现多次的导入"视为重复并删除。但很多是**函数内部的局部导入**（用于延迟加载优化），与模块顶部的导入不是同一作用域：

```python
# 模块顶部
from PySide6.QtWidgets import QWidget

class MultiLineInput(QWidget):
    def _init_ui(self):
        from gugu_native.theme import get_colors  # ← 局部导入，用于延迟加载
        c = get_colors()
    
    def refresh_theme(self):
        from gugu_native.theme import get_colors  # ← 被脚本视为"重复"并删除
        c = get_colors()  # ← NameError!
```

**影响**: 22 个文件，58 个"重复导入"被删除，其中大量是实际需要的。

**教训**:
- ❌ "重复导入" ≠ "冗余导入"。同名导入在不同作用域有不同含义
- ❌ 不能用简单的文本匹配判断导入是否重复，必须用 AST 分析作用域
- ✅ 删除导入后必须运行完整应用验证

---

### 根因 4：`processEvents()` 导致提前初始化（预存隐患）

**文件**: `native/gugu_native/widgets/splash_debug_window.py`

**问题**: `set_progress()` 方法调用了 `QApplication.processEvents()` 来强制刷新 UI。这会处理所有挂起的 Qt 事件，包括 `QTimer.singleShot(0, _create_non_primary_pages)` 定时器。

当 `__init__` 还没完成时，`processEvents()` 触发了非首屏页面的创建，导致在未初始化完的状态下访问 widget → C++ 段错误。

**这不是今天引入的 bug**，而是预存隐患。之前的启动可能因为时序不同偶尔成功，但今天的一系列修改改变了导入时间，使得触发概率变为 100%。

**教训**:
- ❌ `processEvents()` 是危险调用，尤其在初始化阶段。它会打破代码执行顺序的假设
- ✅ 启动画面不需要实时刷新，移除 `processEvents()` 即可
- ✅ `QTimer.singleShot(0, ...)` 应改为非零延迟，避免在当前事件循环中立即执行

---

### 根因 5：循环导入（12:04）

**提交**: `70f3c84` 之前的状态

**问题**: `themes/manager.py` 顶部 `from gugu_native.theme import AppColors`，与 `theme.py` → `themes/__init__.py` → `themes/manager.py` 形成循环。

**修复**: 改为方法内部局部导入。

**教训**:
- ❌ 包的 `__init__.py` 中不要从"父级引用"的模块导入
- ✅ 循环依赖用局部导入（函数内部 import）解决

---

## 三、事故链路图

```
根因1: __slots__ on QObject ──→ C++ 段错误（无 traceback）
    ↓ 修复
根因2: logger in docstring ──→ NameError: 'logger' is not defined
    ↓ 修复
根因3: 删除局部导入 ──→ NameError 雪崩（get_colors/logging/Optional/...）
    ↓ 修复
根因4: processEvents() ──→ 提前触发页面创建 → C++ 段错误
    ↓ 修复
根因5: 循环导入 ──→ C++ 段错误
    ↓ 修复
遗留: 缺失 threading/contextmanager/RotatingFileHandler 导入
    ↓ 修复
✅ 应用正常启动
```

---

## 四、数据统计

| 指标 | 数值 |
|------|------|
| 总提交数（今日） | 36 |
| 其中修复提交 | 18 (50%) |
| 受影响文件数 | ~40 |
| 修复的 NameError | 15+ |
| 修复的 IndentationError | 8 |
| 修复的循环导入 | 1 |
| 修复的段错误 | 3 |
| 用户等待时间 | ~2 小时（19:35~21:40） |

---

## 五、改进建议

### 5.1 批量重构必须有回归测试

所有"全局替换"类操作（print→logger、导入清理、`__slots__` 添加）**必须**在完成后立即运行应用验证。建议：

```bash
# 每次批量修改后执行
python -c "import ast; [ast.parse(open(f).read()) for f in glob('**/*.py', recursive=True)]"
python native/main.py --smoke-test  # 快速启动测试
```

### 5.2 导入清理不能用文本匹配

当前的"重复导入检测"用的是简单文本匹配，无法区分：
- 模块级导入 vs 函数内局部导入
- 同名但不同模块的导入（如 `from a import X` vs `from b import X`）

**应该用 AST 分析**，只删除同一作用域内完全相同的导入。

### 5.3 `__slots__` 添加规则

- **禁止**: QObject、QWidget、QThread 等 Qt 子类
- **必须**: 逐一核对 `__init__` 中所有 `self.xxx = ...` 赋值
- **建议**: 只在纯数据类（dataclass、namedtuple 替代品）上使用

### 5.4 `processEvents()` 使用规范

- **禁止**: 在 `__init__`、`show()`、构造函数链中使用
- **禁止**: 在有 `QTimer.singleShot(0, ...)` 的上下文中使用
- **替代**: 用 `QTimer.singleShot(0, ...)` 延迟执行，或用信号槽

### 5.5 版本策略

今日版本号从 1.20.2 升到 1.20.15（13 个小版本），全部是修复。建议：
- 重大重构前先创建分支
- 每个功能点独立提交，不要混合"重构"和"修复"
- 修复提交用 `fix:` 前缀，便于 `git bisect`

---

## 六、正面经验

1. **诊断日志有效**: `[DIAG] step 0~14` 的逐步日志精确定位了段错误位置（step 9b 之后、step 10 之前）
2. **分段排查策略正确**: 先确认 Python 层没有 traceback → 判断为 C++ 段错误 → 逐步缩小范围
3. **AST 批量修复脚本有效**: 用 Python AST 扫描缺失导入并自动修复，比手动查找高效得多
4. **用户耐心配合**: 多次提供启动日志，加速了定位过程
