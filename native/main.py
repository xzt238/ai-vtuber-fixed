"""
咕咕嘎嘎 AI-VTuber — 原生桌面应用

主入口文件

架构:
- FluentWindow 主窗口 + 导航侧栏
- Live2DWidget 中央渲染组件
- 直接 Python 调用 AIVTuber 后端（无需 HTTP/WS）
- 分页面管理：对话/训练/记忆/设置
- 系统托盘管理（TrayManager）
- 实时语音管理（RealtimeVoiceManager）
- 全局快捷键（HotkeyManager）
- 桌面宠物（DesktopPetWindow）
- 开机自启（AutoStartManager）
- 自动更新（UpdateManager）
- 性能管理（PerformanceManager）
- 启动画面（SplashScreen）

v1.11.23 变更:
- 修复 P0 BUG: PageInitWorker 非主线程 UI 崩溃 → 改为 QTimer.singleShot 错峰调度
- 页面 on_backend_ready() 全部在主线程执行（间隔 50ms 错峰）
- StatsResultWorker setAutoDelete(False) 防止 Bridge 被 QThreadPool 提前回收
- 删除 PageInitWorker 和 _SignalBridge 类

关键依赖:
- PySide6 6.x (Qt6)
- PySide6-Fluent-Widgets (Windows 11 Fluent Design)
- live2d-py 0.6.x (Live2D Cubism 原生渲染)

包名策略:
- 原生桌面应用的包名为 gugu_native（避免与项目 app/ 冲突）
- 后端通过 PROJECT_DIR.sys.path 访问 app.main.AIVTuber
"""

import sys
import os
import time
import time as _time
import threading
import logging

# ===== Win32 FFmpeg 扫描加速（必须在前 3 行，Qt 初始化前执行）=====
# pydub（torchaudio 传递依赖）导入时用 subprocess 扫描 PATH 找 ffmpeg
# Windows 每个子进程 2-5s，累计 10-20s。拦截并毫秒跳过
if os.name == 'nt':
    import subprocess as _sp_main
    _SP_MAIN_ORIG = _sp_main.check_output
    def _sp_main_patched(cmd, **kw) -> None:
        """内部方法"""
        try:
            prog = (cmd[0] if isinstance(cmd, (list, tuple)) else str(cmd).split()[0]).lower()
        except Exception as e:
            return _SP_MAIN_ORIG(cmd, **kw)
        if prog in ('ffmpeg', 'ffmpeg.exe', 'avconv', 'avconv.exe', 'ffprobe', 'ffprobe.exe'):
            raise FileNotFoundError("patched")
        return _SP_MAIN_ORIG(cmd, **kw)
    _sp_main.check_output = _sp_main_patched
    # 同时抑制 pydub RuntimeWarning
    import warnings as _w
    _w.filterwarnings("ignore", message=".*Couldn.t find ffmpeg.*")
    _w.filterwarnings("ignore", message=".*ffmpeg is not installed.*")

# native 目录本身（包含 gugu_native 包）
NATIVE_DIR = os.path.dirname(os.path.abspath(__file__))
if NATIVE_DIR not in sys.path:
    sys.path.insert(0, NATIVE_DIR)

# 项目根目录（用于访问 app.main.AIVTuber 后端）
# KI-005: 先本地计算用于 sys.path，再从 shared_config 统一引用
_LOCAL_PROJECT_DIR = os.path.dirname(NATIVE_DIR)
if _LOCAL_PROJECT_DIR not in sys.path:
    sys.path.append(_LOCAL_PROJECT_DIR)  # append 而非 insert，避免 app/ 覆盖 gugu_native

from app.shared_config import PROJECT_DIR  # KI-005: 统一引用

# v2.0: Live2D 渲染已切换到 QWebEngineView + pixi.js 方案
# live2d-py 不再是必需依赖（保留为可选，兼容旧配置）
LIVE2D_AVAILABLE = False
live2d = None
try:
    import live2d.v3 as _live2d
    live2d = _live2d
    LIVE2D_AVAILABLE = True
    # 注意：live2d.init() 不再必须在 QApplication 之前调用
    # 只有在仍使用旧版 QOpenGLWidget 渲染时才需要
    # 新版 Web 渲染方案不依赖 live2d-py
except ImportError:
    pass  # live2d-py 可选，不影响 Web 渲染方案

from PySide6.QtCore import Qt, QTimer, QThread, Slot
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QIcon

from qfluentwidgets import FluentWindow, NavigationItemPosition, setTheme, Theme, FluentIcon

from gugu_native.theme import apply_theme, get_global_qss, get_colors, apply_theme_by_id, _ensure_manager

# 延迟导入 — 所有重量级模块在 _create_pages() 内按需加载，节省 ~5s 冷启动时间
# ChatPage / TrainPage / MemoryPage / SettingsPage / ModelDownloadPage
# TrayManager / VoiceManager / HotkeyManager / DesktopPet / AutoStart / Update / Perf / DualMode

# 统一版本号（从 app/version.py 读取）
def _get_version() -> None:
    """内部方法"""
    try:
        from app.version import VERSION
        return VERSION
    except ImportError:
        return "1.12.0"  # fallback

# 配置日志 — 强制 UTF-8 编码避免 Windows 中文乱码
# 注意: sys.stderr 本身已是文本流，不能用 io.TextIOWrapper 二次包装（会导致 flush 写 bytes 崩溃）
# 正确做法: reconfigure 直接修改 stderr 的编码，或在 Python 启动参数加 -X utf8
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
_stream_handler = logging.StreamHandler(sys.stderr)
_file_handler = logging.FileHandler(os.path.join(NATIVE_DIR, 'gugu_native.log'), encoding='utf-8')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[_stream_handler, _file_handler],
)
logger = logging.getLogger('GuguGagaApp')


class GuguGagaApp(FluentWindow):
    """咕咕嘎嘎 AI-VTuber 主窗口"""

    def __init__(self, start_time=None, splash=None) -> None:
        """内部方法"""
        logger.info("[DIAG] __init__ step 0: before super().__init__()")
        super().__init__()
        logger.info("[DIAG] __init__ step 1: after super().__init__()")
        import time as _time
        self._init_start_time = start_time or _time.time()
        # T10: 性能埋点 — __init__ 入口
        self._perf_t1 = _time.perf_counter()
        self._splash = splash  # 保存启动画面引用，用于后续重开调试窗口
        self.setWindowTitle(f"咕咕嘎嘎 AI-VTuber v{_get_version()}")
        self.setMinimumSize(960, 600)
        self.resize(1280, 800)
        self.setObjectName("guguGagaApp")
        logger.info("[DIAG] __init__ step 2: window properties set")

        # 标题栏样式 — 深色沉浸式
        from gugu_native.theme import get_colors
        logger.info("[DIAG] __init__ step 3: get_colors imported")
        c = get_colors()
        logger.info("[DIAG] __init__ step 4: get_colors() returned")
        self.setStyleSheet(f"""
            FluentWindow {{
                background-color: {c.window_bg};
            }}
            QWidget#guguGagaApp {{
                background-color: {c.window_bg};
            }}
        """)
        logger.info("[DIAG] __init__ step 5: stylesheet set")

        # 后端引用（延迟初始化 — 异步模式由 PerformanceManager 管理）
        self._backend = None
        self._backend_ready = False

        # === 延迟导入（按需加载，节省 ~5s 冷启动）===
        logger.info("[DIAG] __init__ step 6: importing widgets...")
        from gugu_native.widgets.dual_mode_compat import DualModeCompat
        from gugu_native.widgets.autostart_manager import AutoStartManager
        from gugu_native.widgets.perf_manager import PerformanceManager
        from gugu_native.widgets.tray_manager import TrayManager
        from gugu_native.widgets.update_manager import UpdateManager
        logger.info("[DIAG] __init__ step 7: widgets imported")

        # === 双模式兼容 ===
        self.dual_mode = DualModeCompat(PROJECT_DIR)
        self.dual_mode.ensure_dirs()

        # 检查互斥锁
        if not self.dual_mode.acquire_native_mutex():
            from qfluentwidgets import MessageBox
            msg = MessageBox(
                "重复启动",
                "咕咕嘎嘎原生桌面版已在运行中！\n不能同时启动多个实例。",
                self
            )
            msg.exec()
            # 退出
            QTimer.singleShot(0, self.close)
            return

        # === 开机自启管理器（需在 _create_pages 前初始化）===
        self.autostart_manager = AutoStartManager(self)

        # === 创建各页面 ===
        if self._splash: self._splash.set_progress("正在加载界面...")
        logger.info("[DIAG] __init__ step 8: before _create_pages()")
        self._perf_t2 = time.perf_counter()  # T10: 开始创建页面
        self._create_pages()
        logger.info("[DIAG] __init__ step 9: after _create_pages()")
        self._perf_t3 = time.perf_counter()  # T10: 页面创建完成

        # 缩短/禁用页面切换动画，减少切换时的主线程卡顿
        logger.info("[DIAG] __init__ step 9a: before stackedWidget")
        try:
            if hasattr(self, 'stackedWidget') and hasattr(self.stackedWidget, 'view'):
                self.stackedWidget.view.setAnimationEnabled(False)
        except Exception as e:
            pass
        logger.info("[DIAG] __init__ step 9b: after stackedWidget")

        # === 设置主题（从持久化偏好恢复）===
        if self._splash: self._splash.set_progress("正在应用主题...")
        logger.info("[DIAG] __init__ step 10: before _ensure_manager()")
        manager = _ensure_manager()
        logger.info("[DIAG] __init__ step 11: after _ensure_manager()")
        theme_id = manager.load_preferences()
        logger.info(f"[DIAG] __init__ step 12: theme_id={theme_id}")
        logger.info("[DIAG] __init__ step 12a: before apply_theme_by_id")
        apply_theme_by_id(theme_id)
        logger.info("[DIAG] __init__ step 13: apply_theme_by_id done")
        logger.info("[DIAG] __init__ step 13a: before get_global_qss")
        self.setStyleSheet(get_global_qss())
        logger.info("[DIAG] __init__ step 14: global QSS applied")

        # === 性能管理器 ===
        self.perf_manager = PerformanceManager(self)
        self.perf_manager.tune_gc_thresholds()  # 调优 GC 阈值，减少启动阶段 GC 暂停

        # === 窗口拖动防抖定时器 ===
        # v1.11.24: 避免 resize/move 快速连续触发时堆积多个 singleShot
        self._drag_timer = QTimer(self)
        self._drag_timer.setSingleShot(True)
        self._drag_timer.timeout.connect(
            lambda: self.perf_manager.set_window_drag_state(False)
            if hasattr(self, 'perf_manager') else None
        )

        # === 系统托盘管理器 ===
        self.tray_manager = TrayManager(self)
        self.tray_manager.setup()
        self.tray_manager.quit_requested.connect(self._on_quit_requested)

        # === 实时语音管理器（延迟初始化，窗口渲染完成后创建）===
        self.voice_manager = None
        # === 全局快捷键管理器（延迟初始化，窗口渲染完成后创建）===
        self.hotkey_manager = None
        self._managers_initialized = False

        # === 桌面宠物 ===
        self._pet_window = None

        # === 自动更新管理器 ===
        self.update_manager = UpdateManager("xzt238/ai-vtuber-fixed", _get_version(), parent=self)
        self.update_manager.check_done.connect(self._on_update_check)
        self.update_manager.download_done.connect(self._on_update_downloaded)

        # WebUI 检测 — 异步通知式，不阻塞页面创建
        self._start_webui_check()

        # === 后端管理器延迟初始化（窗口渲染完成后）===
        QTimer.singleShot(500, self._init_backend_managers)

        # === 延迟异步初始化后端（100ms 后，让 UI 先渲染完）===
        # v1.11.22: 使用异步初始化，后端在 QThread 中构造，不阻塞主线程
        self.perf_manager.schedule_backend_init_async(
            callback=self._on_backend_ready_async,
            delay_ms=100
        )

        # 延迟检查更新（10秒后，不抢后端初始化的资源）
        QTimer.singleShot(10000, self.update_manager.check_for_updates)

        logger.info("GuguGagaApp initialized")

    def _start_webui_check(self) -> None:
        """异步检测 WebUI 是否运行 — 纯通知式，不阻塞页面创建"""
        from gugu_native.widgets.dual_mode_compat import WebUICheckWorker
        self._webui_checker = WebUICheckWorker(self.dual_mode.WEBUI_HTTP_PORT)
        self._webui_check_thread = QThread()
        self._webui_checker.moveToThread(self._webui_check_thread)
        self._webui_checker.result_ready.connect(self._on_webui_check_result)
        self._webui_check_thread.started.connect(self._webui_checker.check)
        self._webui_check_thread.start()

    def _init_backend_managers(self) -> None:
        """延迟创建后端管理器（窗口渲染完成后）"""
        if self._managers_initialized:
            return

        # T10: 性能埋点
        self._perf_t5 = time.perf_counter()

        from gugu_native.widgets.voice_manager import RealtimeVoiceManager
        from gugu_native.widgets.hotkey_manager import HotkeyManager

        self.voice_manager = RealtimeVoiceManager(parent=self)
        self.voice_manager.vad_state_changed.connect(self._on_vad_state_changed)
        self.voice_manager.error_occurred.connect(self._on_voice_error)

        self.hotkey_manager = HotkeyManager(self)
        self.hotkey_manager.hotkey_triggered.connect(self._on_hotkey_triggered)
        self.hotkey_manager.start()

        self.perf_manager.register_cleanup_target("voice_manager", self.voice_manager)
        self.perf_manager.register_cleanup_target("hotkey_manager", self.hotkey_manager)

        self._managers_initialized = True
        logger.info("Backend managers initialized (delayed)")

    def _on_webui_check_result(self, is_running: bool) -> None:
        """WebUI 检测回调 — 仅显示提示，不创建页面"""
        if is_running:
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.warning(
                title="WebUI 模式检测",
                content="检测到 WebUI 模式正在运行，两者可以共存但共享同一后端配置。",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
            )
        # 清理线程
        if hasattr(self, '_webui_check_thread') and self._webui_check_thread.isRunning():
            self._webui_check_thread.quit()
            self._webui_check_thread.wait(2000)

    def _create_pages(self) -> None:
        """创建导航页面 — 首屏立即创建，其余页面延迟创建以加速冷启动"""
        logger.info("[DIAG] _create_pages step A: importing ChatPage")

        # 对话页面（首屏，立即创建）
        from gugu_native.pages.chat_page import ChatPage
        logger.info("[DIAG] _create_pages step B: ChatPage imported, creating instance")
        self.chat_page = ChatPage(self)
        self.addSubInterface(
            self.chat_page,
            FluentIcon.CHAT,
            "对话"
        )

        # 非首屏页面延迟创建，让首屏先渲染、用户先可交互
        # 注意：不能用 delay=0，否则 set_progress() 中的 processEvents() 会提前触发
        QTimer.singleShot(200, self._create_non_primary_pages)

        # 导航栏样式优化
        try:
            from qfluentwidgets import NavigationAvatarWidget
            nav = self.navigationInterface
            nav.setExpandWidth(200)
            nav.setCollapsible(True)
        except Exception as e:
            pass

    def _create_non_primary_pages(self) -> None:
        """延迟创建非首屏页面 — 分批创建，减少单帧压力

        第一批：使用 LazyPageMixin 的页面（__init__ 极轻量，骨架屏占位）
        第二批：设置相关页面（延迟 200ms，让先创建的页面先注册到导航栏）
        """
        # 第一批：轻量页面（LazyPageMixin，__init__ 只初始化属性+骨架屏）
        try:
            logger.info("[DIAG] _create_non_primary_pages: creating TrainPage")
            from gugu_native.pages.train_page import TrainPage
            self.train_page = TrainPage(self)
            self.addSubInterface(
                self.train_page,
                FluentIcon.MICROPHONE,
                "音色训练"
            )
            logger.info("[DIAG] _create_non_primary_pages: TrainPage done")
        except Exception as e:
            logger.error(f"[DIAG] TrainPage failed: {e}")

        try:
            logger.info("[DIAG] _create_non_primary_pages: creating MemoryPage")
            from gugu_native.pages.memory_page import MemoryPage
            self.memory_page = MemoryPage(self)
            self.addSubInterface(
                self.memory_page,
                FluentIcon.BOOK_SHELF,
                "记忆"
            )
            logger.info("[DIAG] _create_non_primary_pages: MemoryPage done")
        except Exception as e:
            logger.error(f"[DIAG] MemoryPage failed: {e}")

        try:
            logger.info("[DIAG] _create_non_primary_pages: creating ModelDownloadPage")
            from gugu_native.pages.model_download_page import ModelDownloadPage
            self.model_download_page = ModelDownloadPage(self)
            self.addSubInterface(
                self.model_download_page,
                FluentIcon.DOWNLOAD,
                "模型下载"
            )
            logger.info("[DIAG] _create_non_primary_pages: ModelDownloadPage done")
        except Exception as e:
            logger.error(f"[DIAG] ModelDownloadPage failed: {e}")

        # 第二批：设置页面（延迟 200ms，让先创建的页面先渲染）
        QTimer.singleShot(200, self._create_settings_pages)

    def _create_settings_pages(self) -> None:
        """延迟创建设置相关页面"""
        try:
            from gugu_native.pages.vrm_settings_page import VRMSettingsPage
            self.vrm_settings_page = VRMSettingsPage(self)
            self.addSubInterface(
                self.vrm_settings_page,
                FluentIcon.VIEW,
                "VRM 设置"
            )
        except ImportError:
            pass

        # 新增功能调试页面（优化版）
        try:
            from gugu_native.pages.debug_page_optimized import DebugPageOptimized
            self.debug_page = DebugPageOptimized(self)
            self.addSubInterface(
                self.debug_page,
                FluentIcon.DEVELOPER_TOOLS,
                "功能调试"
            )
        except ImportError:
            pass

        # 直播平台设置页面
        try:
            from gugu_native.pages.live_settings_page import LiveSettingsPage
            self.live_settings_page = LiveSettingsPage(self)
            self.addSubInterface(
                self.live_settings_page,
                FluentIcon.VIDEO,
                "直播设置"
            )
        except ImportError:
            pass

        # 游戏设置页面
        try:
            from gugu_native.pages.game_settings_page import GameSettingsPage
            self.game_settings_page = GameSettingsPage(self)
            self.addSubInterface(
                self.game_settings_page,
                FluentIcon.GAME,
                "游戏设置"
            )
        except ImportError:
            pass

        # 社交Bot设置页面
        try:
            from gugu_native.pages.bot_settings_page import BotSettingsPage
            self.bot_settings_page = BotSettingsPage(self)
            self.addSubInterface(
                self.bot_settings_page,
                FluentIcon.PEOPLE,
                "Bot设置"
            )
        except ImportError:
            pass

        # 功能设置页面
        try:
            from gugu_native.pages.features_settings_page import FeaturesSettingsPage
            self.features_settings_page = FeaturesSettingsPage(self)
            self.addSubInterface(
                self.features_settings_page,
                FluentIcon.SHOPPING_CART,
                "功能设置"
            )
        except ImportError:
            pass

        # 日志查看页面
        try:
            from gugu_native.pages.log_page import LogPage
            self.log_page = LogPage(self)
            self.addSubInterface(
                self.log_page,
                FluentIcon.DOCUMENT,
                "日志"
            )
        except ImportError:
            pass

        from gugu_native.pages.settings_page import SettingsPage
        self.settings_page = SettingsPage(self)
        # autostart_switch 绑定已移至 SettingsPage.lazy_init() 中
        # （因为 _init_ui 延迟到首次导航时才执行，此处 autostart_switch 尚不存在）
        self.addSubInterface(
            self.settings_page,
            FluentIcon.SETTING,
            "设置",
            position=NavigationItemPosition.BOTTOM
        )

    @property
    def backend(self) -> None:
        """延迟初始化后端

        v1.11.22: 异步初始化后，_backend 由 PerformanceManager._on_backend_init_done() 赋值。
        此 property 仅作为 fallback（兼容直接访问 backend 的代码）。
        """
        if self._backend is None and not self._backend_ready:
            # 后端尚未就绪（异步初始化中或同步 fallback）
            logger.debug("Backend not yet initialized (async init in progress)")
        return self._backend

    # ========== 异步后端就绪回调 ==========

    def _on_backend_ready_async(self) -> None:
        """后端就绪 — 错峰初始化各页面

        v1.11.23: 替代原来的 _on_backend_ready() 同步串行初始化。
        - ChatPage 仍在主线程调用（Live2D/QWebEngineView 必须主线程操作）
        - 其余页面通过 QTimer.singleShot 错峰调度到主线程，避免 UI 操作崩溃
        - 主动说话回调、TTS 预热、ASR 预加载保持原有逻辑
        """
        elapsed = _time.time() - self._init_start_time if hasattr(self, '_init_start_time') else 0
        logger.info(f"Backend ready — total startup: {elapsed:.1f}s")

        # 关闭启动画面（隐藏但不销毁，日志内容保留供后续查看）
        if self._splash:
            logger.info(f"✓ 后端全部就绪 (耗时 {elapsed:.1f}s)")
            self._splash.set_progress("启动完成!")
            self._splash.fade_out_and_close()

        # ChatPage 特殊处理 — 仍在主线程，因为 Live2D/QWebEngineView 必须主线程操作
        if self.chat_page and hasattr(self.chat_page, 'on_backend_ready'):
            try:
                self.chat_page.on_backend_ready()
            except Exception as e:
                logger.warning(f"Failed to notify ChatPage: {e}")

        # 其余页面错峰初始化 — QTimer.singleShot 调度到主线程，避免 UI 操作崩溃
        # 每个页面间隔 50ms，让事件循环有机会处理 GUI 事件（拖动/重绘）
        if self._splash:
            self._splash.set_progress("加载页面组件...")

        _page_init_schedule = [
            ("train", getattr(self, 'train_page', None), 50),
            ("memory", getattr(self, 'memory_page', None), 100),
            ("model_download", getattr(self, 'model_download_page', None), 150),
            ("settings", getattr(self, 'settings_page', None), 200),
        ]
        for page_name, page, delay_ms in _page_init_schedule:
            if page and hasattr(page, 'on_backend_ready'):
                QTimer.singleShot(delay_ms, page.on_backend_ready)

        # v1.9.80: 注册主动说话原生回调
        try:
            if self.backend and hasattr(self.backend, 'proactive') and self.backend.proactive:
                self.backend.proactive._native_callback = self.chat_page._on_proactive_speech
                logger.info("Proactive speech native callback registered")
        except Exception as e:
            logger.warning(f"Failed to register proactive callback: {e}")

        # v1.11.25: S-001 模型预加载并行化 — 替代原来串行的 ASR/TTS 单独加载
        # ASR + TTS + Memory 三个模型并行加载，总耗时从 sum → max
        if self._splash: self._splash.set_progress("正在并行预加载模型...")
        try:
            if self.backend and hasattr(self.backend, 'preload_models_parallel'):
                self.backend.preload_models_parallel()
            else:
                # Fallback: 后端无 preload 方法时走旧逻辑
                logger.warning("Backend has no preload_models_parallel(), falling back to serial")
                import threading
                def _preload_asr() -> None:
                    """内部方法"""
                    try:
                        import time as _t
                        _t.sleep(0.01)
                        _ = self.backend.asr
                        logger.info("ASR preload completed")
                    except Exception as e:
                        logger.warning(f"ASR preload failed: {e}")
                threading.Thread(target=_preload_asr, daemon=True).start()
        except Exception as e:
            logger.warning(f"Parallel preload failed: {e}")

        # v1.11.30: TTS 模型后台预加载 — 不阻塞 UI，但提前加载 GPT-SoVITS 模型
        # 原来延迟到首次对话，导致首次发消息要等 5-10s。现在后台加载，首次对话无延迟。
        self._tts_prewarmed = False

        # v1.20.16: 预导入 TTS 重量级依赖（torchaudio/librosa/ffmpeg）
        # TTS_infer_pack.TTS 在顶层 import 这些库，首次导入耗时 ~30s
        # 提前在后台线程预导入，后续 TTS 加载时 Python 直接从 sys.modules 缓存取，0s
        def _preload_tts_deps() -> None:
            """内部方法"""
            try:
                import importlib
                for mod in ('torchaudio', 'librosa', 'ffmpeg'):
                    try:
                        importlib.import_module(mod)
                    except ImportError:
                        pass
                logger.info("TTS deps preload: torchaudio/librosa/ffmpeg cached")
            except Exception as e:
                logger.debug(f"TTS deps preload skipped: {e}")
        threading.Thread(target=_preload_tts_deps, daemon=True, name="tts-deps-preload").start()

        self._prewarm_tts_background()

    def _prewarm_tts_background(self) -> None:
        """后台预热 TTS 模型 — 不阻塞 UI，首次对话前完成加载"""

        def _do_prewarm() -> None:
            """内部方法"""
            try:
                if not self.backend or not self.backend.tts:
                    return
                tts = self.backend.tts
                # 触发 _lazy_init() 加载 GPT-SoVITS 模型
                if hasattr(tts, '_lazy_init'):
                    tts._lazy_init()
                    logger.info("TTS background prewarm: GPT-SoVITS model loaded")
                # 预热音色
                if hasattr(tts, '_project_config'):
                    ref_audio = tts._project_config.get('ref_audio', '')
                    if ref_audio:
                        warm_text = "你好."
                        path = tts.speak(warm_text)
                        if path and os.path.exists(path):
                            try:
                                os.unlink(path)
                            except OSError:
                                pass
                        logger.info("TTS background prewarm: voice warmed up")
            except Exception as e:
                logger.warning(f"TTS background prewarm failed (不影响使用): {e}")

        threading.Thread(target=_do_prewarm, daemon=True, name="tts-prewarm").start()
        logger.info("TTS background prewarm started")

    def _prewarm_tts(self) -> None:
        """TTS 引擎预热 — 串行加载上次使用的音色项目,避免 ref_audio_path 为空报错"""

        def prewarm_single_voice(voice_name, tts) -> None:
            """预热单个音色"""
            try:
                if hasattr(tts, '_project_config'):
                    ref_audio = tts._project_config.get('ref_audio', '')
                    if not ref_audio:
                        logger.info(f"TTS Prewarm: {voice_name} 无参考音频,跳过预热")
                        return
                warm_text = "你好."
                path = tts.speak(warm_text)
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except OSError:
                        pass
                    logger.info(f"TTS Prewarm: {voice_name} 预热完成")
                else:
                    logger.info(f"TTS Prewarm: {voice_name} 预热返回空(不影响使用)")
            except Exception as e:
                logger.warning(f"TTS Prewarm: {voice_name} 预热失败: {e}")

        def do_prewarm() -> None:
            """后台预热主逻辑(串行,避免并发推理冲突)"""
            try:
                if not self.backend or not self.backend.tts:
                    return
                tts = self.backend.tts

                # 短暂让出 GIL，减少对主线程的争抢
                _t.sleep(0.01)

                # 1. 预热默认音色
                logger.info("TTS Prewarm: 预热默认音色...")
                prewarm_single_voice("default", tts)

                # 2. 预热上次使用的音色
                last_project = None
                if hasattr(tts, '_load_last_project'):
                    last_project = tts._load_last_project()

                if last_project and hasattr(tts, 'set_project'):
                    logger.info(f"TTS Prewarm: 预热上次使用的音色: {last_project}")
                    tts.set_project(last_project)
                    prewarm_single_voice(last_project, tts)
                elif hasattr(tts, 'get_available_projects'):
                    # 没有记录上次音色 → 预热第一个已训练音色
                    try:
                        projects = tts.get_available_projects()
                        trained = [p['name'] for p in projects if p.get('has_trained')]
                        if trained:
                            first = trained[0]
                            logger.info(f"TTS Prewarm: 无上次记录,预热首个已训练音色: {first}")
                            tts.set_project(first)
                            prewarm_single_voice(first, tts)
                    except Exception as proj_err:
                        logger.warning(f"TTS Prewarm: 获取音色列表失败: {proj_err}")

            except Exception as e:
                logger.warning(f"TTS Prewarm: 预热失败(不影响使用): {e}")

        threading.Thread(target=do_prewarm, daemon=True).start()

    # ========== 实时语音 ==========

    def _on_speech_recognized(self, text: str) -> None:
        """语音识别完成 → 发送到对话"""
        if text:
            self.chat_page.input_field.setText(text)
            self.chat_page._send_message()

    def _on_vad_state_changed(self, is_speaking: bool) -> None:
        """语音活动状态变化"""
        # 更新录音按钮状态
        if hasattr(self.chat_page, 'record_btn'):
            if is_speaking:
                self.chat_page.record_btn.setText("识别中...")

    def _on_voice_error(self, error_msg: str) -> None:
        """语音错误"""
        self.chat_page.chat_display.append_system_msg(f"语音错误: {error_msg}")

    # ========== 全局快捷键 ==========

    def _on_hotkey_triggered(self, action: str) -> None:
        """快捷键触发"""
        if action == "toggle_record":
            # 切换录音
            if self.voice_manager is None:
                return
            if self.voice_manager.is_listening:
                self.voice_manager.stop_listening()
                self.chat_page.chat_display.append_system_msg("实时语音已停止")
            else:
                self.voice_manager.start_listening()
                self.chat_page.chat_display.append_system_msg("实时语音已启动")

        elif action == "show_window":
            # 显示/隐藏主窗口
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()

        elif action == "toggle_pet":
            # 切换桌面宠物
            self._toggle_desktop_pet()

        elif action == "stop_action":
            # 停止当前操作
            if hasattr(self.chat_page, '_is_streaming') and self.chat_page._is_streaming:
                self.chat_page._stop_streaming()
            if self.voice_manager is not None and self.voice_manager.is_listening:
                self.voice_manager.stop_listening()

    # ========== 桌面宠物 ==========

    def _toggle_desktop_pet(self) -> None:
        """切换桌面宠物模式"""
        if self._pet_window and self._pet_window.isVisible():
            self._pet_window.hide()
            self.show()
            # 恢复主窗口 Live2D 渲染
            self._resume_main_live2d()
        else:
            if self._pet_window is None:
                from gugu_native.widgets.desktop_pet import DesktopPetWindow
                self._pet_window = DesktopPetWindow(self)
                self._pet_window.switch_to_main.connect(self._on_pet_switch_to_main)
                self._pet_window.pet_closed.connect(self._on_pet_closed)
            # 暂停主窗口 Live2D 渲染（宠物窗口有自己的 Live2D 实例）
            self._pause_main_live2d()
            self._pet_window.show()
            self.hide()

    def _pause_main_live2d(self) -> None:
        """暂停主窗口的 Live2D 渲染以节省 GPU 资源"""
        try:
            # v2.0: Web 渲染模式下无需手动管理定时器，只停止动画控制器
            if hasattr(self.chat_page, '_animation_controller') and self.chat_page._animation_controller:
                self.chat_page._animation_controller.stop()
        except Exception as e:
            logger.debug(f"Pause main Live2D failed: {e}")

    # ========== 运行调试窗口 ==========

    def show_debug_window(self) -> None:
        """显示运行调试窗口（启动后已隐藏，可重新打开查看历史日志）"""
        if self._splash:
            self._splash.show()
            self._splash.raise_()
            self._splash.activateWindow()

    def _resume_main_live2d(self) -> None:
        """恢复主窗口的 Live2D 渲染"""
        try:
            # v2.0: Web 渲染模式下无需手动管理定时器，只恢复动画控制器
            if hasattr(self.chat_page, '_animation_controller') and self.chat_page._animation_controller:
                self.chat_page._animation_controller.start()
        except Exception as e:
            logger.debug(f"Resume main Live2D failed: {e}")

    def _on_pet_switch_to_main(self) -> None:
        """宠物切回主窗口"""
        if self._pet_window:
            self._pet_window.hide()
        self.show()
        self.activateWindow()
        # 恢复主窗口 Live2D 渲染
        self._resume_main_live2d()

    def _on_pet_closed(self) -> None:
        """宠物窗口关闭"""
        self.show()
        # 恢复主窗口 Live2D 渲染
        self._resume_main_live2d()

    # ========== 自动更新 ==========

    def _on_update_check(self, result: dict) -> None:
        """更新检查完成"""
        if result.get("has_update"):
            version = result.get("latest_version", "")
            notes = result.get("release_notes", "")[:500]
            url = result.get("release_url", "")

            msg = MessageBox(
                "发现新版本",
                f"新版本 v{version} 可用！\n\n{notes}\n\n"
                f"是否前往下载？",
                self
            )
            msg.yesButton.setText("前往下载")
            msg.cancelButton.setText("跳过此版本")

            if msg.exec():
                self.update_manager.open_release_page(url)
            else:
                self.update_manager.skip_version(version)

    def _on_update_downloaded(self, file_path: str) -> None:
        """更新下载完成"""
        InfoBar.success(
            title="下载完成",
            content=f"更新包已下载到: {file_path}",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=5000,
        )

    # ========== 页面切换与窗口状态 ==========

    def changeEvent(self, event) -> None:
        """监听窗口状态变化 — 最小化时暂停 idle 动画"""
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange:
            chat_page = getattr(self, 'chat_page', None)
            controller = getattr(chat_page, '_animation_controller', None) if chat_page else None
            if self.windowState() & Qt.WindowState.WindowMinimized:
                if controller:
                    controller.pause_idle()
            else:
                if controller:
                    controller.resume_idle()

    def switchTo(self, widget) -> None:
        """重写页面切换 — 支持懒加载页面的 ensure_initialized()"""
        if widget and hasattr(widget, 'ensure_initialized'):
            widget.ensure_initialized()
        super().switchTo(widget)

    def resizeEvent(self, event) -> None:
        """窗口 resize 期间广播拖动状态，暂停 Live2D 渲染"""
        super().resizeEvent(event)
        if hasattr(self, 'perf_manager'):
            self.perf_manager.set_window_drag_state(True)
            if hasattr(self, '_drag_timer'):
                self._drag_timer.stop()
                self._drag_timer.start(100)

    def moveEvent(self, event) -> None:
        """窗口移动期间广播拖动状态，暂停 Live2D 渲染"""
        super().moveEvent(event)
        if hasattr(self, 'perf_manager'):
            self.perf_manager.set_window_drag_state(True)
            if hasattr(self, '_drag_timer'):
                self._drag_timer.stop()
                self._drag_timer.start(100)

    # ========== 窗口事件 ==========

    def keyPressEvent(self, event) -> None:
        """全局键盘事件 — Ctrl+F 搜索"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_F:
                # 搜索消息
                if hasattr(self.chat_page, 'search_bar'):
                    self.chat_page.search_bar.show_search()
                return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        """关闭事件 — 最小化到托盘或退出"""
        # 先尝试最小化到托盘
        if not getattr(self, '_force_quit', False) and hasattr(self, 'tray_manager') and self.tray_manager.handle_close_event(event):
            return  # 事件已处理（最小化到托盘）

        # 正常退出
        self._cleanup_and_exit(event)

    def _on_quit_requested(self) -> None:
        """托盘菜单触发退出"""
        self._force_quit = True
        self.close()

    def _cleanup_and_exit(self, event) -> None:
        """清理资源并退出

        v1.11.22: 增量 GC 定时器停止 + gc.enable() 恢复 + 页面 Worker 清理
        """
        logger.info("Cleaning up and exiting...")

        # 优化 #2: 强制保存所有脏会话
        if hasattr(self, 'chat_page') and hasattr(self.chat_page, 'session_manager'):
            try:
                self.chat_page.session_manager.flush_dirty()
            except Exception as e:
                logger.warning(f"Failed to flush dirty sessions: {e}")

        # 停止语音管理器
        if hasattr(self, 'voice_manager') and self.voice_manager is not None and self.voice_manager.is_listening:
            self.voice_manager.stop_listening()

        # 停止全局快捷键
        if hasattr(self, 'hotkey_manager') and self.hotkey_manager is not None:
            self.hotkey_manager.stop()

        # 关闭桌面宠物
        if self._pet_window:
            self._pet_window.close()

        # 性能管理器清理（停止增量 GC 定时器 + 恢复 gc.enable() + gc.collect(2)）
        if hasattr(self, 'perf_manager'):
            self.perf_manager.cleanup()

        # 释放互斥锁
        self.dual_mode.release_mutex()

        # 保存后端状态
        if self._backend:
            if hasattr(self._backend, '_save_history'):
                try:
                    self._backend._save_history()
                except Exception as e:
                    logger.warning(f"Failed to save history: {e}")
            if hasattr(self._backend, 'memory') and hasattr(self._backend.memory, 'flush'):
                try:
                    self._backend.memory.flush()
                except Exception as e:
                    logger.warning(f"Failed to flush memory: {e}")
            if hasattr(self._backend, 'stop'):
                try:
                    self._backend.stop()
                except Exception as e:
                    logger.warning(f"Failed to stop backend: {e}")

        if hasattr(self, 'tray_manager'):
            self.tray_manager.cleanup()
        event.accept()
        logger.info("Cleanup completed")


def _check_dependencies() -> None:
    """检查关键依赖（PySide6），失败时弹出跨平台消息框"""
    try:
        import PySide6  # noqa: F401
    except ImportError:
        from app.platform_abstraction import show_message
        show_message(
            "咕咕嘎嘎 - 启动失败",
            "PySide6 未安装!\n请先运行安装脚本安装依赖。",
            level="error"
        )
        sys.exit(1)


def main() -> None:
    """Main"""
    # ★ 依赖检查（在 QApplication 之前，避免创建窗口后才发现依赖缺失）
    _check_dependencies()

    # v9: 全局启动计时 — 从 main() 入口开始，而非 __init__()
    # 之前放在 __init__ 里测量的是"构造函数→后端就绪"的耗时，
    # 但用户感知的"启动慢"是从双击 start.bat 到 UI 可用的总时间。
    _PROCESS_START = _time.time()
    _last_checkpoint = _time.time()

    def _checkpoint(name) -> None:
        """内部方法"""
        nonlocal _last_checkpoint
        now = _time.time()
        elapsed_total = now - _PROCESS_START
        elapsed_step = now - _last_checkpoint
        logger.info(f"[Perf] {name}: +{elapsed_step:.2f}s (total {elapsed_total:.2f}s)")
        _last_checkpoint = now

    # v1.12.0 STEP-2: 禁用 PySide6 shiboken 签名检测
    # shibokensupport/feature.py 调用 inspect.getsource 392 次（0.227s）
    # 禁用后 PySide6 不再检查每个模块的签名，启动快 0.2s
    os.environ.setdefault('SHIBOKEN_DISABLE_FEATURE_DETECTION', '1')

    # 注意: CUDA_MODULE_LOADING=LAZY 已移除 — 会导致 torch.cuda.is_available() 返回 False
    # 使得 GPT-SoVITS 回退到 CPU 推理，严重影响 TTS 性能

    # ★ Chromium GPU 加速开关 — 必须在 QApplication 创建之前设置！
    # QWebEngineView 默认可能使用软件渲染（SwiftShader），导致 WebGL 性能极差
    # 或 Live2D 模型无法正确渲染。
    # 这些环境变量会被 Chromium 的 base::CommandLine 读取。
    # 必须在 QApplication 之前设置，因为 Chromium 在 QApplication 构造时初始化。
    # v1.11.28 P0-2: 添加启动加速参数
    os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS',
        '--enable-gpu-rasterization '
        '--enable-native-gpu-memory-buffers '
        '--enable-webgl2-compute-context '
        '--ignore-gpu-blocklist '
        '--disable-software-rasterizer '
        # v1.11.28: 启动加速参数
        '--disable-features=TranslateUI '  # 禁用翻译功能
        '--disable-extensions '  # 禁用扩展
        '--disable-background-networking '  # 禁用后台网络
        '--disable-sync '  # 禁用同步
        '--disable-translate '  # 禁用翻译
        '--metrics-recording-only '  # 仅记录指标，不上传
        '--no-first-run '  # 跳过首次运行向导
        '--no-default-browser-check '  # 跳过默认浏览器检查
        '--disable-component-update '  # 禁用组件更新
        '--disable-background-timer-throttling '  # 禁用后台定时器节流
        '--disable-renderer-backgrounding '  # 禁用渲染器后台化
        '--disable-backgrounding-occluded-windows '  # 禁用被遮挡窗口的后台化
        '--disable-ipc-flooding-protection '  # 禁用 IPC 洪水保护（减少延迟）
        '--disable-hang-monitor '  # 禁用挂起监视器
        '--disable-prompt-on-repost '  # 禁用重新发布提示
        '--disable-domain-reliability '  # 禁用域可靠性
        '--disable-client-side-phishing-detection '  # 禁用客户端钓鱼检测
        '--disable-default-apps '  # 禁用默认应用
        '--disable-popup-blocking '  # 禁用弹出窗口阻止
        '--disable-save-password-bubble '  # 禁用保存密码气泡
        '--disable-session-crashed-bubble '  # 禁用会话崩溃气泡
        '--disable-infobars '  # 禁用信息栏
        '--disable-gesture-typing '  # 禁用手势输入
        '--disable-modal-animations '  # 禁用模态动画
        '--disable-smooth-scrolling '  # 禁用平滑滚动（减少 GPU 负载）
    )

    # 高 DPI 支持 — 必须在 QApplication 创建之前设置
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # OpenGL 上下文共享 — Live2D (QOpenGLWidget) 和 QWebEngineView 共存时必须设置
    # 否则 QWebEngineView 无法正确渲染（黑屏）或 QQuickWidget 报 QRhi 错误
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

    # 强制 Qt Scene Graph 使用 OpenGL RHI 后端
    # Windows 上 Qt6 默认使用 Direct3D11，但 QOpenGLWidget 需要 OpenGL，
    # 两者冲突会导致 QQuickWidget: Failed to get a QRhi 错误
    # 必须在 QApplication 创建之前调用
    try:
        from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
        QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)
    except ImportError:
        pass  # QtQuick 不可用时忽略（不影响 QOpenGLWidget 本身）

    _checkpoint("环境变量设置完成")

    app = QApplication(sys.argv)
    _checkpoint("QApplication 创建完成")

    # 全局默认字体 - 跨平台支持
    from PySide6.QtGui import QFont
    import platform
    if platform.system() == "Windows":
        font_family = "Microsoft YaHei UI"
    elif platform.system() == "Darwin":
        font_family = "PingFang SC"
    else:
        font_family = "Noto Sans CJK SC"
    app.setFont(QFont(font_family, 10))

    # 设置应用图标 - 跨平台支持
    if platform.system() == "Windows":
        icon_name = "app.ico"
    elif platform.system() == "Darwin":
        icon_name = "app.icns"
    else:
        icon_name = "app.png"
    icon_path = os.path.join(NATIVE_DIR, "gugu_native", "resources", icon_name)
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 启动画面 — 自定义 SplashDebugWindow（含运行调试窗口）
    splash_path = os.path.join(NATIVE_DIR, "gugu_native", "resources", "splash.png")
    from gugu_native.widgets.splash_debug_window import SplashDebugWindow, StdoutRedirector
    _checkpoint("Splash 模块导入完成")

    splash = SplashDebugWindow(logo_path=splash_path if os.path.exists(splash_path) else None)
    splash.set_progress("正在初始化界面...")
    splash.show()
    app.processEvents()  # 确保 splash 立即渲染

    # 重定向 stdout 到启动画面的调试窗口（stderr 不重定向，避免破坏 logging handler）
    _stdout_redirector = StdoutRedirector()
    _stdout_redirector.text_written.connect(splash.append_log)
    sys.stdout = _stdout_redirector

    splash.append_log("✓ Python 环境就绪")
    splash.set_progress("正在初始化界面组件...")

    try:
        logger.info("[DIAG] main: about to create GuguGagaApp...")
        window = GuguGagaApp(start_time=_PROCESS_START, splash=splash)
        _checkpoint("GuguGagaApp 初始化完成")
        window.show()
        _checkpoint("window.show() 完成")
    except Exception as e:
        splash.append_log(f"[ERROR] 界面初始化失败: {e}")
        splash.set_progress("初始化失败 - 按 Esc 关闭")
        import traceback
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                splash.append_log(line)
        # 保持 splash 显示，不退出——让用户看到错误日志
        exit_code = app.exec()
        sys.exit(1)

    # v1.11.22: 连接 BackendInitWorker 的 init_progress Signal 到 splash
    # 后端初始化进度实时更新到启动画面
    if window.perf_manager._init_worker:
        window.perf_manager._init_worker.init_progress.connect(
            lambda msg: splash.set_progress(msg) if splash and splash.isVisible() else None
        )

    # 启动画面由 _on_backend_ready_async 中关闭（不再使用 splash.finish）

    # v9: 记录 UI 显示耗时（从 main() 入口到 window.show()）
    import time as _time2
    ui_elapsed = _time2.time() - _PROCESS_START
    logger.info(f"UI visible in {ui_elapsed:.1f}s")

    exit_code = app.exec()

    # v2.0: live2d-py 清理（可选，Web 渲染模式不需要）
    if LIVE2D_AVAILABLE and live2d:
        try:
            if hasattr(live2d, 'dispose'):
                live2d.dispose()
        except Exception as e:
            pass

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
