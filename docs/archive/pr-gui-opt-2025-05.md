# PRD：GuguGaga AI-VTuber GUI 主线程卡顿优化

| 字段 | 值 |
|------|-----|
| 项目名称 | ai-vtuber-gui-opt |
| 编程语言 | Python 3.11+ / PySide6 |
| 文档版本 | v1.0 |
| 创建日期 | 2025-05-31 |
| 负责人 | 许清楚（产品经理） |

---

## 一、原始需求复述

用户反馈：拖动窗口或切换界面时频繁出现"未响应"，每次拖动都有卡顿感。经诊断，GUI 主线程存在 5 个阻塞源，分别涉及后端初始化、页面同步加载、全量 GC、同步数据读取及 GIL 争抢。需要系统性优化，消除窗口拖动/切换时的"未响应"状态。

---

## 二、产品定义

### 2.1 产品目标

| # | 目标 | 可量化指标 |
|---|------|-----------|
| G1 | 消除主线程阻塞导致的"未响应" | 窗口拖动时 0 次"未响应"，拖动帧率 ≥ 30fps |
| G2 | 启动阶段 GUI 保持可交互 | 后端初始化期间 GUI 可正常拖动/最小化，主线程单次阻塞 < 50ms |
| G3 | 运行时无感知卡顿 | 常规操作（切换页面、刷新数据）主线程阻塞 < 16ms/次（60fps 标准） |

### 2.2 用户故事

1. **As a** 直播中的 VTuber 用户，**I want** 在 AI 后端启动时仍能拖动和调整窗口位置，**so that** 我不会因为等待初始化而无法操作界面，影响直播体验。

2. **As a** 日常使用 AI-VTuber 的用户，**I want** 切换不同页面（Live2D、记忆、设置）时界面流畅无卡顿，**so that** 我的工作流不被打断，体验流畅如原生应用。

3. **As a** 长时间运行 AI-VTuber 的用户，**I want** 应用在运行数小时后仍保持响应，**so that** GC 和后台任务不会导致间歇性卡顿和"未响应"弹窗。

4. **As a** 低配设备用户，**I want** 即使在 CPU 负载较高时也能基本操作界面，**so that** GIL 争抢不会完全冻结 GUI。

5. **As a** 开发者，**I want** 所有耗时操作都有明确的异步模式规范可遵循，**so that** 未来新增功能不会再次引入主线程阻塞问题。

---

## 三、已诊断阻塞源分析

| # | 问题 | 位置 | 影响 | 阻塞时长 | 根因分类 |
|---|------|------|------|----------|----------|
| 1 | 后端初始化在主线程 | `perf_manager.py` L73 `_do_init()` | 启动后100ms触发 AIVTuber() 构造，GUI冻住 | 5-15秒 | 同步初始化 |
| 2 | `_on_backend_ready` 同步调用所有页面 | `main.py` L370-375 | 串行调用5个页面的 on_backend_ready()，Live2D初始化、记忆刷新全堵住 | 3-8秒 | 串行加载 |
| 3 | gc.collect() 在主线程 | `perf_manager.py` L153 | 每60秒全量GC，PySide6+torch对象多时卡顿 | 100-500ms | GC暂停 |
| 4 | MemoryPage _refresh_stats 在主线程 | `memory_page.py` | 每10秒同步读记忆数据，访问 vector_store.get_stats() | 50-200ms | 同步IO |
| 5 | GIL 争抢 | 全局 | TTS预热/ASR预加载等CPU密集线程持有GIL时，Qt事件循环无法处理 | 间歇性 | GIL争抢 |

---

## 四、优化方法论调研

### 4.1 Qt/PySide6 桌面应用主线程最佳实践

#### 4.1.1 Qt 官方多线程技术选型指南

根据 Qt 6.11 官方文档，Qt 提供四种多线程技术，选型依据为线程目的和生命周期：

| 技术 | 适用场景 | 线程复用 | 事件循环 | 信号槽通信 | 推荐度 |
|------|----------|----------|----------|-----------|--------|
| **QThread + Worker QObject（MoveToThread）** | 长驻后台服务，需接收命令/数据 | 否 | 是 | 是 | ★★★★★ |
| **QThreadPool + QRunnable** | 一次性短任务，需线程复用 | 是 | 否 | 需自定义信号 | ★★★★☆ |
| **QtConcurrent::run() + QFutureWatcher** | 一次性调用，需返回值 | 是 | 否 | 通过QFuture信号 | ★★★★☆ |
| **子类化 QThread（无事件循环）** | 永久循环任务，不需接收信号 | 否 | 否 | 仅发射信号 | ★★★☆☆ |

**核心原则**：
- 任何耗时操作都不应在 GUI 线程执行
- 短期一次性任务优先使用 `QtConcurrent::run()` 或 `QThreadPool`
- 需要事件循环的长驻任务使用 Worker QObject + QThread 模式
- 线程间通信统一使用信号槽机制（Qt 队列连接天然保证线程安全）

#### 4.1.2 信号槽跨线程通信的正确模式

```
┌──────────────┐     Signal.emit()     ┌──────────────┐
│  Worker 线程  │ ──────────────────→  │  GUI 主线程   │
│              │   (队列连接,自动序列化)  │              │
│  执行耗时任务  │                       │  更新 UI 组件  │
└──────────────┘                       └──────────────┘

⚠️ 绝对禁止在后台线程中直接操作 GUI 组件
⚠️ 使用 Signal 定义类变量，而非实例变量
⚠️ @Slot() 装饰器标注槽函数，提升性能
```

**PySide6 正确实现模板**：

```python
from PySide6.QtCore import QThread, Signal, Slot, QObject

class Worker(QObject):
    finished = Signal(object)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self):
        super().__init__()

    @Slot()
    def do_work(self):
        try:
            result = self._heavy_computation()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def start_background_task(self):
        self.thread = QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.do_work)
        self.worker.finished.connect(self.on_task_finished)
        self.worker.error.connect(self.on_task_error)
        self.thread.start()

    @Slot(object)
    def on_task_finished(self, result):
        # 安全地更新 UI
        self.label.setText(f"Result: {result}")
        self.thread.quit()
        self.thread.wait()
```

#### 4.1.3 QThreadPool 通用 Worker 模式

适用于"投递即忘"的一次性任务，无需长驻线程：

```python
from PySide6.QtCore import QRunnable, QThreadPool, Signal, Slot

class GenericWorker(QRunnable):
    """通用后台任务包装器"""
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        self.fn(*self.args, **self.kwargs)

# 使用方式
threadpool = QThreadPool.globalInstance()
worker = GenericWorker(self.load_data_async)
threadpool.start(worker)
```

---

### 4.2 知名开源项目优化方法分析

#### 4.2.1 Calibre（电子书管理器，PyQt）

**规模**：百万级用户，最大的 Python/Qt 桌面应用之一

| 优化策略 | 具体实现 | 适用度 |
|----------|----------|--------|
| **Job 管理系统** | 耗时操作抽象为后台 Job，JobManager 统一追踪状态，JobsButton 显示进度 | ★★★★★ 本项目可直接借鉴 |
| **三阶段初始化** | `do_genesis()` → `gui_layout_complete()` → `initialization_complete()`，延迟加载非核心功能 | ★★★★★ 完美匹配阻塞源#1,#2 |
| **信号驱动事件模型** | 所有组件通过 Qt 信号异步通信，避免同步等待 | ★★★★★ |
| **两阶段窗口构造** | `__init__` 仅创建轻量结构，`initialize()` 在适当时机执行重量级操作 | ★★★★☆ |
| **数据库事件监听** | 通过 broker 异步同步 GUI 与后端数据变更 | ★★★★☆ 适用于记忆页刷新 |

**可借鉴要点**：
- 三阶段初始化模式完美解决本项目"后端初始化阻塞"和"串行页面加载"问题
- Job 管理系统可作为统一的异步任务管理基础设施
- 信号驱动的数据同步模式替代轮询式同步读取

#### 4.2.2 OBS Studio（直播软件，Qt/C++）

**规模**：直播领域标准软件，同时处理音视频采集、渲染、编码

| 优化策略 | 具体实现 | 适用度 |
|----------|----------|--------|
| **渲染线程完全独立** | `obs_graphics_thread` 在独立线程运行所有 GPU 操作，Qt UI 线程不参与 | ★★★★★ 核心架构参考 |
| **状态更新的线程安全设计** | UI 修改 source 只更新临时值，渲染线程在 tick_sources() 中完成实际更新 | ★★★★☆ |
| **信号量通信** | 线程间通过信号量而非互斥锁通信，video_thread 无数据时阻塞不消耗 CPU | ★★★★☆ |
| **回调机制解耦** | UI 通过 `obs_display_add_draw_callback` 注册回调，渲染线程负责调用 | ★★★★☆ 适用于Live2D渲染 |
| **双缓冲/多纹理** | 当前帧渲染与上一帧数据下载并行，避免 GPU 等待 | ★★★☆☆ |

**可借鉴要点**：
- OBS 证明"渲染/计算线程完全独立于 UI 线程"是实时应用的正确架构
- Live2D 渲染、TTS/ASR 预处理应与 Qt UI 线程完全解耦
- 回调注册模式比直接调用更安全

#### 4.2.3 Spyder IDE（科学计算 IDE，PyQt）

| 优化策略 | 具体实现 | 适用度 |
|----------|----------|--------|
| **Kernel 通信异步化** | IPython Kernel 通信通过 ZMQ 异步执行，UI 不阻塞 | ★★★★☆ |
| **后台代码执行** | 代码运行在独立进程（Kernel），IDE 本身保持响应 | ★★★★☆ |
| **延迟加载插件** | 插件按需初始化，不在启动时全部加载 | ★★★★★ |
| **进度指示** | 长时操作显示进度条，避免用户以为卡死 | ★★★★☆ |

**可借鉴要点**：
- 后端 AI 引擎类似 Spyder 的 Kernel，应作为独立服务运行
- 插件/页面延迟加载模式可直接应用

#### 4.2.4 Anki（记忆卡片软件，PyQt）

| 优化策略 | 具体实现 | 适用度 |
|----------|----------|--------|
| **混合架构** | Qt + Web(HTML/CSS/JS)，将渲染密集部分用 Web 技术处理 | ★★★☆☆ |
| **后台同步** | 卡片同步在后台执行，通过信号通知 UI 更新 | ★★★★★ |
| **显示驱动可选** | 提供软件渲染/硬件渲染切换选项，兼容不同设备 | ★★★☆☆ |

#### 4.2.5 AI 桌面应用对比

| 应用 | 技术栈 | GUI 优化策略 | 适用度 |
|------|--------|-------------|--------|
| **LM Studio** | Electron/React | Web 技术天然异步；IPC 与模型进程分离；下载/加载异步化 | ★★★☆☆ 架构不同但异步思路可借鉴 |
| **Ollama** | Go 后端 + 简单 CLI/Web | 模型推理在独立进程，GUI 不直接接触计算 | ★★★★☆ 进程隔离思路 |
| **Jan.ai** | Electron + 本地模型 | 模型在独立线程/进程推理，UI 通过 IPC 获取结果 | ★★★★☆ |

**关键发现**：所有成熟的 AI 桌面应用都将模型推理放在独立进程/线程，GUI 仅通过 IPC 获取结果。本项目也应将 AI 后端视为"外部服务"而非主线程的一部分。

---

### 4.3 Python GIL 优化策略

#### 4.3.1 三种并发模型在 Qt 应用中的适用性

| 模型 | 适用场景 | GIL 影响 | Qt 兼容性 | 推荐度 |
|------|----------|----------|-----------|--------|
| **多线程 (QThread/QThreadPool)** | IO 密集型任务（网络请求、文件读取、数据库查询） | IO 操作期间释放 GIL，GUI 线程可获得执行机会 | ★★★★★ 原生集成 | ★★★★★ |
| **多进程 (multiprocessing)** | CPU 密集型任务（模型推理、音频处理、大量计算） | 完全绕过 GIL，真正并行 | ★★★☆☆ 需自行管理 IPC | ★★★★☆ |
| **asyncio** | 高并发 IO（大量网络请求、WebSocket） | 单线程协作式并发，不涉及 GIL | ★★☆☆☆ 需与 Qt 事件循环集成 | ★★☆☆☆ |

#### 4.3.2 减少 GIL 争抢的具体策略

| 策略 | 实现方式 | 适用度 |
|------|----------|--------|
| **C 扩展释放 GIL** | 在 C 扩展代码中使用 `Py_BEGIN_ALLOW_THREADS` / `Py_END_ALLOW_THREADS` | ★★★☆☆ 需修改底层库 |
| **multiprocessing 隔离 CPU 密集任务** | 将 TTS 预热、ASR 预加载放入独立进程，通过 Queue/Pipe 通信 | ★★★★★ |
| **subprocess 调用外部命令** | 对可独立运行的模块（如模型推理），使用 subprocess 启动 | ★★★★☆ |
| **减少主线程 Python 字节码执行量** | 耗时操作尽量在 C 层完成，减少 Python 层循环 | ★★★☆☆ |
| **QThread 优先级调整** | 降低后台线程优先级，给 GUI 线程更多 GIL 获取机会 | ★★★★☆ |

#### 4.3.3 Python 3.13+ Free-Threaded 模式

| 项目 | 详情 |
|------|------|
| **可用版本** | Python 3.13+ 可选安装 free-threaded 构建 |
| **启用方式** | 官方安装器勾选 / 源码 `--disable-gil` 编译 / 运行时 `PYTHON_GIL=0` 或 `-X gil=0` |
| **PySide6 兼容性** | ⚠️ **当前不可用**：PySide6 尚未标记支持 free-threading，导入将自动重新启用 GIL |
| **单线程性能开销** | macOS aarch64 ~1%，x86-64 Linux ~8% |
| **内存增长** | 对象头更大，QSBR 延迟释放，内存使用增加 |
| **跟踪状态** | https://py-free-threading.github.io/tracking/ |

**建议**：当前版本不采用 free-threaded 模式。持续跟踪 PySide6 适配进度，待其正式支持后再评估迁移。

---

### 4.4 特殊优化技巧

#### 4.4.1 QCoreApplication.processEvents() 分段处理

**原理**：在耗时循环中周期性调用 `processEvents()`，让 Qt 有机会处理积压的 UI 事件。

```python
# 适用场景：无法移至后台线程的遗留代码的临时过渡方案
from PySide6.QtWidgets import QApplication

def heavy_loop_with_responsive_ui():
    for i in range(large_number):
        do_heavy_step(i)
        if i % 100 == 0:  # 每 100 步让出一次
            QApplication.processEvents()
```

**⚠️ 严重警告**：
- `processEvents()` 可能导致递归重入问题（处理事件时触发的信号再次进入当前函数）
- 仅作为**过渡方案**，不应作为最终解决方案
- 本项目应优先使用真正的多线程方案，processEvents 仅用于无法重构的紧急热修复

#### 4.4.2 延迟加载 / 懒加载模式

**Calibre 的三阶段初始化模式**（强烈推荐）：

```
阶段1: do_genesis()         → 基本配置，不涉及IO
阶段2: gui_layout_complete() → UI结构已确定，可进行布局相关初始化
阶段3: initialization_complete() → 所有依赖就绪，执行完整功能
```

**本项目应用**：
- 页面（Page）对象仅在首次显示时初始化（懒加载）
- Live2D 模型加载延迟到页面实际可见时
- 记忆数据首次请求时才建立连接

#### 4.4.3 渲染优化

| 方案 | 描述 | 适用度 |
|------|------|--------|
| **Live2D 渲染独立线程** | 将 Live2D 更新循环放入 QThread，通过信号通知 UI 刷新 | ★★★★★ |
| **QQuickWidget + Scene Graph** | 使用 Qt Quick 的 GPU 加速渲染管线替代纯 QWidget | ★★☆☆☆ 改动过大 |
| **QOpenGLWidget** | 对需要硬件加速的自定义渲染使用 OpenGL 窗口 | ★★★☆☆ |
| **减少重绘区域** | 使用 `QWidget.update()` 而非 `repaint()`，利用 Qt 脏区域合并 | ★★★★☆ |

#### 4.4.4 内存管理优化

**Python GC 优化（关键发现：qtpygc 库）**：

Kovid Goyal（Calibre 作者）在 PyQt 邮件列表提出的方案：**禁用自动 GC，在主线程中定期手动运行 GC**。已封装为 `qtpygc` 库。

| 措施 | 实现方式 | 解决的阻塞源 |
|------|----------|-------------|
| **禁用自动 GC** | `gc.disable()` | 防止后台线程中意外触发 GC 导致 Qt 对象不安全销毁 |
| **定时器驱动手动 GC** | QTimer 周期性调用 `gc.collect()` | GC 仅在主线程中执行，不阻塞 UI 事件处理 |
| **分代 GC 调优** | `gc.set_threshold(700, 10, 10)` 调整阈值，减少全量 GC 频率 | 降低单次 GC 耗时 |
| **增量 GC** | 每次 timer 只回收年轻代(gen0)，全量 GC 间隔拉长 | 将 500ms 暂停拆分为多次 <16ms 暂停 |
| **deleteLater() 延迟析构** | 使用 Qt 的 `deleteLater()` 替代直接删除对象 | 确保对象在正确线程析构 |
| **弱引用 (weakref)** | 对缓存数据使用弱引用，允许 GC 在内存紧张时自动回收 | 减少内存压力，间接减少 GC 工作量 |

**qtpygc 使用方式**：

```python
from qtpygc import GarbageCollector

gaco = GarbageCollector()

with gaco.qt_loop():
    app.exec_()
```

**PEP 556（线程化 GC）参考**：
- 当前状态：Deferred（延期）
- 提案核心：将隐式 GC 移至专用线程执行
- 虽未正式采纳，但其设计思路（GC 不在调用线程中同步执行）与本项目优化方向一致

---

## 五、需求池

### P0 — 必须实现（Must Have）

| ID | 需求 | 关联阻塞源 | 优化方法 | 验收标准 |
|----|------|-----------|----------|----------|
| P0-1 | 后端初始化异步化 | #1 | Worker QThread + 进度信号 | `_do_init()` 在后台线程执行，主线程单次阻塞 < 50ms |
| P0-2 | 页面 on_backend_ready 并行化 | #2 | QThreadPool 并行调用 + 各页面独立 Worker | 5 个页面初始化从串行 3-8s 降至并行 < 2s |
| P0-3 | GC 优化：禁用自动 GC + 定时手动 GC | #3 | qtpygc 模式 / 自实现增量 GC 定时器 | GC 暂停 < 16ms/次，无 100ms+ 卡顿 |
| P0-4 | MemoryPage 异步刷新 | #4 | QRunnable + Signal 异步读取 | `_refresh_stats` 不阻塞主线程，数据到达后 Signal 通知更新 |
| P0-5 | 拖动窗口帧率保障 | 全局 | 综合以上优化 | 拖动时帧率 ≥ 30fps，0 次"未响应" |

### P1 — 应该实现（Should Have）

| ID | 需求 | 关联阻塞源 | 优化方法 | 验收标准 |
|----|------|-----------|----------|----------|
| P1-1 | GIL 争抢缓解 | #5 | 后台 CPU 密集线程降低优先级；TTS/ASR 预加载改为异步触发 | 间歇性卡顿频率降低 80% |
| P1-2 | 统一异步任务框架 | 全局 | 借鉴 Calibre JobManager，建立 AsyncJobManager | 所有耗时操作有统一异步入口，新增功能不会引入主线程阻塞 |
| P1-3 | 页面懒加载 | #2 | 页面首次显示时才初始化，借鉴 Calibre 三阶段模式 | 启动时仅加载可见页面，其他页面按需加载 |
| P1-4 | 启动进度展示 | #1,#2 | 后端初始化 + 页面加载期间展示进度条/骨架屏 | 用户可感知启动进度，GUI 始终可交互 |
| P1-5 | Live2D 渲染独立线程 | #5 | Live2D update loop 放入 QThread，Signal 通知 UI 刷新 | Live2D 更新不阻塞 Qt 事件循环 |

### P2 — 锦上添花（Nice to Have）

| ID | 需求 | 关联阻塞源 | 优化方法 | 验收标准 |
|----|------|-----------|----------|----------|
| P2-1 | CPU 密集任务进程隔离 | #5 | TTS 预热、ASR 预加载放入 multiprocessing.Process | GIL 争抢完全消除 |
| P2-2 | 缓存与弱引用优化 | #3 | 对频繁创建/销毁的对象使用对象池/弱引用 | 内存使用更平滑，GC 压力降低 |
| P2-3 | Free-Threaded Python 适配评估 | #5 | 跟踪 PySide6 对 free-threaded Python 的支持 | 文档记录适配路径，待 PySide6 支持后评估 |
| P2-4 | processEvents() 紧急热修复能力 | 全局 | 为无法立即重构的代码提供安全的使用模式 | 紧急情况下可在 10 分钟内热修复卡顿 |

---

## 六、UI 设计草案

### 6.1 启动流程改造

```
当前流程（阻塞式）：
┌───────────────────────────────────────────────────────────────┐
│ MainWindow.__init__()                                          │
│   ├─ 创建 UI                                                   │
│   ├─ _do_init() ──── 阻塞 5-15s ────►                        │
│   └─ _on_backend_ready() ──── 阻塞 3-8s ────►                │
│                                                                 │
│  ❌ GUI 完全冻结，无法拖动                                      │
└───────────────────────────────────────────────────────────────┘

优化后流程（异步式）：
┌───────────────────────────────────────────────────────────────┐
│ MainWindow.__init__()                                          │
│   ├─ 创建 UI + 骨架屏/加载指示器                              │
│   ├─ QTimer.singleShot(100, self._start_async_init)           │
│   │                                                             │
│   ✅ GUI 立即可交互                                            │
│                                                                 │
│ ┌─ Worker Thread ─────────────────────────────┐               │
│ │  _do_init()  →  发射 backend_ready 信号      │               │
│ └─────────────────────────────────────────────┘               │
│       ↓ Signal                                                  │
│ _on_backend_ready()                                            │
│   ├─ QThreadPool.start(Page1InitWorker)                         │
│   ├─ QThreadPool.start(Page2InitWorker)  ← 并行初始化         │
│   ├─ QThreadPool.start(Page3InitWorker)                         │
│   └─ ...                                                       │
└───────────────────────────────────────────────────────────────┘
```

### 6.2 GC 优化设计

```
当前模式（主线程全量 GC）：
┌──────────────────────────────────────────┐
│ QTimer(60s) → gc.collect() → 阻塞 100-500ms │
└──────────────────────────────────────────┘

优化后模式（增量 GC + 定时器驱动）：
┌──────────────────────────────────────────┐
│ gc.disable()  // 禁用自动 GC               │
│                                            │
│ QTimer(5s) → gc.collect(0)   // 仅 gen0, <5ms │
│ QTimer(30s) → gc.collect(1)  // gen0+1, <16ms │
│ QTimer(120s) → gc.collect(2) // 全量, <50ms   │
│                                            │
│ ✅ 单次暂停 < 16ms，用户无感知              │
└──────────────────────────────────────────┘
```

### 6.3 异步任务框架设计

```
┌─────────────────────────────────────────────────────────┐
│                    AsyncJobManager                        │
│  (借鉴 Calibre JobManager)                               │
│                                                          │
│  ┌─────────────┐   ┌──────────────┐                    │
│  │ QThreadPool  │   │ 长驻 Worker   │                    │
│  │ (短任务复用) │   │ QThread       │                    │
│  └──────┬──────┘   └──────┬───────┘                    │
│         │                 │                              │
│  ┌──────▼─────────────────▼───────┐                    │
│  │        Signal Hub              │                    │
│  │  job_started / job_progress   │                    │
│  │  job_finished / job_error      │                    │
│  └──────────────┬────────────────┘                    │
│                 │                                        │
│  ┌──────────────▼────────────────┐                    │
│  │   GUI 主线程（Slot 处理）      │                    │
│  │   - 更新进度条                  │                    │
│  │   - 更新状态栏                  │                    │
│  │   - 显示错误提示                │                    │
│  └───────────────────────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

---

## 七、待确认问题

| # | 问题 | 影响 | 建议确认人 |
|---|------|------|-----------|
| Q1 | AIVTuber() 构造函数是否可安全地在非主线程调用？是否有隐式依赖 Qt 对象？ | P0-1 实现方式 | 架构师 |
| Q2 | 5 个页面的 on_backend_ready() 之间是否存在数据依赖，能否真正并行？ | P0-2 并行化可行性 | 架构师 |
| Q3 | vector_store.get_stats() 是否涉及线程不安全的操作（如共享模型文件的内存映射）？ | P0-4 异步读取安全性 | 架构师 |
| Q4 | Live2D SDK 的渲染调用是否要求在特定线程（如 OpenGL 上下文线程）？ | P1-5 实现方式 | 架构师 |
| Q5 | qtpygc 库是否与项目现有的 GC 管理逻辑（perf_manager.py L153）兼容？是否需要自行实现增量 GC？ | P0-3 方案选择 | 架构师 |
| Q6 | 项目是否有计划升级 Python 版本？3.13+ free-threaded 模式是否纳入长期路线图？ | P2-3 优先级 | 项目负责人 |
| Q7 | TTS 预热和 ASR 预加载是否可以延迟到用户首次触发时执行，而非启动时？ | P1-1 缓解策略 | 产品/架构 |
| Q8 | 是否存在其他未被诊断出的主线程阻塞源（如定时器回调、信号槽中的同步操作）？ | 完整性 | QA |

---

## 八、优化方法论调研总结

### 8.1 核心方法论矩阵

| 方法论 | 解决的阻塞源 | 实现复杂度 | 效果 | 优先采用 |
|--------|-------------|-----------|------|---------|
| **Worker QThread（MoveToThread）** | #1,#4 | 低 | 高 | ✅ |
| **QThreadPool + QRunnable** | #2,#4 | 低 | 高 | ✅ |
| **增量 GC / qtpygc** | #3 | 低 | 高 | ✅ |
| **Calibre 三阶段初始化** | #1,#2 | 中 | 高 | ✅ |
| **Calibre JobManager 模式** | 全局 | 中 | 高 | ✅ |
| **OBS 渲染线程独立** | #5(Live2D) | 高 | 高 | △ P1 |
| **multiprocessing 隔离** | #5 | 高 | 最高 | △ P2 |
| **processEvents()** | 全局 | 极低 | 低 | ⚠️ 仅紧急 |
| **Free-Threaded Python** | #5 | 极高 | 高 | ❌ 待评估 |

### 8.2 关键调研结论

1. **Qt 社区共识**：所有耗时操作必须离开主线程，使用信号槽回传结果。这是 Qt 桌面应用的基本架构纪律。

2. **Calibre 是最佳参考**：同为 Python+Qt 大型应用，其三阶段初始化、Job 管理系统、qtpygc GC 方案可直接借鉴。

3. **OBS 架构验证了渲染独立线程的必要性**：对实时渲染类应用（如 Live2D 驱动的 VTuber），渲染线程独立于 UI 线程是行业共识。

4. **AI 桌面应用的共同模式**：模型推理/后端服务在独立进程/线程运行，GUI 仅通过 IPC 获取结果——本项目应遵循此模式。

5. **GC 是隐蔽但关键的阻塞源**：Python GC 可在任意线程触发，对 Qt 应用是定时炸弹。qtpygc 的"禁用自动 GC + 定时器驱动手动 GC"模式应成为标准实践。

6. **GIL 是系统性问题**：多线程无法根本解决 CPU 密集型任务的 GIL 争抢，最终需要 multiprocessing 隔离。但短期内通过线程优先级调整和延迟加载可有效缓解。

7. **Python free-threaded 模式尚未就绪**：PySide6 尚未适配，导入即重新启用 GIL。当前版本不应依赖此特性。
