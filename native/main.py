"""
咕咕嘎嘎 AI-VTuber — 原生桌面应用 v1.9.82

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
import logging

# native 目录本身（包含 gugu_native 包）
NATIVE_DIR = os.path.dirname(os.path.abspath(__file__))
if NATIVE_DIR not in sys.path:
    sys.path.insert(0, NATIVE_DIR)

# 项目根目录（用于访问 app.main.AIVTuber 后端）
PROJECT_DIR = os.path.dirname(NATIVE_DIR)
if PROJECT_DIR not in sys.path:
    sys.path.append(PROJECT_DIR)  # append 而非 insert，避免 app/ 覆盖 gugu_native

# live2d.init() 必须在 QApplication 和 QWidget 之前调用
# live2d-py 是可选依赖，未安装时跳过 Live2D 功能
LIVE2D_AVAILABLE = False
live2d = None
try:
    import live2d.v3 as _live2d
    _live2d.init()
    live2d = _live2d
    LIVE2D_AVAILABLE = True
except ImportError:
    print("[WARN] live2d-py not installed, Live2D features will be disabled.")
    print("       Install it later: pip install live2d-py")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QIcon, QPixmap

from qfluentwidgets import FluentWindow, NavigationItemPosition, setTheme, Theme, FluentIcon

from gugu_native.theme import apply_theme, get_global_qss, get_colors

from gugu_native.pages.chat_page import ChatPage
from gugu_native.pages.train_page import TrainPage
from gugu_native.pages.memory_page import MemoryPage
from gugu_native.pages.model_download_page import ModelDownloadPage
from gugu_native.pages.settings_page import SettingsPage
from gugu_native.widgets.tray_manager import TrayManager
from gugu_native.widgets.voice_manager import RealtimeVoiceManager
from gugu_native.widgets.hotkey_manager import HotkeyManager
from gugu_native.widgets.desktop_pet import DesktopPetWindow
from gugu_native.widgets.autostart_manager import AutoStartManager
from gugu_native.widgets.update_manager import UpdateManager
from gugu_native.widgets.perf_manager import PerformanceManager
from gugu_native.widgets.dual_mode_compat import DualModeCompat

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

    def __init__(self):
        super().__init__()
        self.setWindowTitle("咕咕嘎嘎 AI-VTuber v1.9.82")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)
        self.setObjectName("guguGagaApp")

        # 标题栏样式 — 深色沉浸式
        from gugu_native.theme import get_colors
        c = get_colors()
        self.setStyleSheet(f"""
            FluentWindow {{
                background-color: {c.window_bg};
            }}
            QWidget#guguGagaApp {{
                background-color: {c.window_bg};
            }}
        """)

        # 后端引用（延迟初始化）
        self._backend = None
        self._backend_ready = False

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

        # 检查 WebUI 是否在运行
        if self.dual_mode.check_webui_running():
            from qfluentwidgets import InfoBar, InfoBarPosition
            InfoBar.warning(
                title="WebUI 模式检测",
                content="检测到 WebUI 模式正在运行，两者可以共存但共享同一后端配置。",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
            )

        # === 性能管理器 ===
        self.perf_manager = PerformanceManager(self)

        # === 开机自启管理器（需在 _create_pages 前初始化）===
        self.autostart_manager = AutoStartManager(self)

        # 创建各页面
        self._create_pages()

        # 设置主题
        apply_theme(Theme.DARK)

        # 应用全局样式表
        self.setStyleSheet(get_global_qss())

        # === 系统托盘管理器 ===
        self.tray_manager = TrayManager(self)
        self.tray_manager.setup()
        self.tray_manager.quit_requested.connect(self._on_quit_requested)

        # === 实时语音管理器 ===
        self.voice_manager = RealtimeVoiceManager(parent=self)
        # v1.9.76: speech_recognized 信号由 chat_page 在实时语音模式中按需连接
        # 不在全局连接，避免与 chat_page._on_realtime_speech 重复触发 _send_message()
        self.voice_manager.vad_state_changed.connect(self._on_vad_state_changed)
        self.voice_manager.error_occurred.connect(self._on_voice_error)

        # === 全局快捷键管理器 ===
        self.hotkey_manager = HotkeyManager(self)
        self.hotkey_manager.hotkey_triggered.connect(self._on_hotkey_triggered)
        self.hotkey_manager.start()

        # === 桌面宠物 ===
        self._pet_window = None

        # === 自动更新管理器 ===
        self.update_manager = UpdateManager("xzt238/ai-vtuber-fixed", "1.9.82", parent=self)
        self.update_manager.check_done.connect(self._on_update_check)
        self.update_manager.download_done.connect(self._on_update_downloaded)

        # === 延迟初始化后端（2秒后，让 UI 先渲染完）===
        self.perf_manager.schedule_backend_init(
            callback=self._on_backend_ready,
            delay_ms=2000
        )

        # 延迟检查更新（10秒后，不抢后端初始化的资源）
        QTimer.singleShot(10000, self.update_manager.check_for_updates)

        # 注册性能监控目标
        self.perf_manager.register_cleanup_target("voice_manager", self.voice_manager)
        self.perf_manager.register_cleanup_target("hotkey_manager", self.hotkey_manager)

        logger.info("GuguGagaApp initialized")

    def _create_pages(self):
        """创建导航页面"""

        # 对话页面（含 Live2D）
        self.chat_page = ChatPage(self)
        self.addSubInterface(
            self.chat_page,
            FluentIcon.CHAT,
            "对话"
        )

        # 训练页面
        self.train_page = TrainPage(self)
        self.addSubInterface(
            self.train_page,
            FluentIcon.MICROPHONE,
            "音色训练"
        )

        # 记忆页面
        self.memory_page = MemoryPage(self)
        self.addSubInterface(
            self.memory_page,
            FluentIcon.BOOK_SHELF,
            "记忆"
        )

        # 模型下载页面（v1.9.80: 从设置页拆出，提升到主导航栏）
        self.model_download_page = ModelDownloadPage(self)
        self.addSubInterface(
            self.model_download_page,
            FluentIcon.DOWNLOAD,
            "模型下载"
        )

        # 设置页面（放在底部）
        self.settings_page = SettingsPage(self)
        # 绑定开机自启开关到 AutoStartManager
        self.settings_page.autostart_switch.setChecked(self.autostart_manager.is_enabled())
        self.settings_page.autostart_switch.checkedChanged.connect(
            lambda checked: self.autostart_manager.enable() if checked else self.autostart_manager.disable()
        )
        self.addSubInterface(
            self.settings_page,
            FluentIcon.SETTING,
            "设置",
            position=NavigationItemPosition.BOTTOM
        )

        # 导航栏样式优化
        try:
            from qfluentwidgets import NavigationAvatarWidget
            nav = self.navigationInterface
            nav.setExpandWidth(200)
            nav.setCollapsible(True)
        except Exception:
            pass

    @property
    def backend(self):
        """延迟初始化后端"""
        if self._backend is None:
            self.tray_manager.update_progress("正在初始化后端...")
            try:
                # 确保 CWD 在项目根目录，使 AIVTuber 的相对路径("./memory"等)正确解析
                # native.bat 从 native/ 目录启动，CWD 不在项目根会导致记忆/缓存路径错误
                os.chdir(PROJECT_DIR)

                from app.main import AIVTuber
                self._backend = AIVTuber()
                # 连接语音管理器到后端
                self.voice_manager.backend = self._backend
                self._backend_ready = True
                self.tray_manager.notify_backend_ready()
                logger.info("Backend initialized")
            except Exception as e:
                self.tray_manager.notify_backend_error(str(e))
                logger.error(f"Backend init failed: {e}")
                raise
        return self._backend

    def _on_backend_ready(self):
        """后端初始化完成回调"""
        logger.info("Backend ready, updating pages")
        # 通知各页面后端已就绪
        for page in [self.chat_page, self.train_page, self.memory_page, self.model_download_page, self.settings_page]:
            if hasattr(page, 'on_backend_ready'):
                try:
                    page.on_backend_ready()
                except Exception as e:
                    logger.warning(f"Failed to notify {page.__class__.__name__}: {e}")

        # v1.9.80: 注册主动说话原生回调
        try:
            if hasattr(self.backend, 'proactive') and self.backend.proactive:
                self.backend.proactive._native_callback = self.chat_page._on_proactive_speech
                logger.info("Proactive speech native callback registered")
        except Exception as e:
            logger.warning(f"Failed to register proactive callback: {e}")

        # TTS 预热: 加载上次使用的音色项目,避免 ref_audio_path 为空
        # 参考 WebUI 模式的 _prewarm_tts() 逻辑
        self._prewarm_tts()

        # ASR 预加载: 在后台线程触发懒加载,避免首次语音识别时等待
        import threading
        def _preload_asr():
            try:
                _ = self.backend.asr
                logger.info("ASR preload completed")
            except Exception as e:
                logger.warning(f"ASR preload failed: {e}")
        threading.Thread(target=_preload_asr, daemon=True).start()

    def _prewarm_tts(self):
        """TTS 引擎预热 — 串行加载上次使用的音色项目,避免 ref_audio_path 为空报错"""
        import threading

        def prewarm_single_voice(voice_name, tts):
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

        def do_prewarm():
            """后台预热主逻辑(串行,避免并发推理冲突)"""
            try:
                if not self.backend or not self.backend.tts:
                    return
                tts = self.backend.tts

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

    def _on_speech_recognized(self, text: str):
        """语音识别完成 → 发送到对话"""
        if text:
            self.chat_page.input_field.setText(text)
            self.chat_page._send_message()

    def _on_vad_state_changed(self, is_speaking: bool):
        """语音活动状态变化"""
        # 更新录音按钮状态
        if hasattr(self.chat_page, 'record_btn'):
            if is_speaking:
                self.chat_page.record_btn.setText("识别中...")

    def _on_voice_error(self, error_msg: str):
        """语音错误"""
        self.chat_page.chat_display.append_system_msg(f"语音错误: {error_msg}")

    # ========== 全局快捷键 ==========

    def _on_hotkey_triggered(self, action: str):
        """快捷键触发"""
        if action == "toggle_record":
            # 切换录音
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
            if self.voice_manager.is_listening:
                self.voice_manager.stop_listening()

    # ========== 桌面宠物 ==========

    def _toggle_desktop_pet(self):
        """切换桌面宠物模式"""
        if self._pet_window and self._pet_window.isVisible():
            self._pet_window.hide()
            self.show()
        else:
            if self._pet_window is None:
                self._pet_window = DesktopPetWindow(self)
                self._pet_window.switch_to_main.connect(self._on_pet_switch_to_main)
                self._pet_window.pet_closed.connect(self._on_pet_closed)
            self._pet_window.show()
            self.hide()

    def _on_pet_switch_to_main(self):
        """宠物切回主窗口"""
        if self._pet_window:
            self._pet_window.hide()
        self.show()
        self.activateWindow()

    def _on_pet_closed(self):
        """宠物窗口关闭"""
        self.show()

    # ========== 自动更新 ==========

    def _on_update_check(self, result: dict):
        """更新检查完成"""
        if result.get("has_update"):
            from qfluentwidgets import MessageBox
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

    def _on_update_downloaded(self, file_path: str):
        """更新下载完成"""
        from qfluentwidgets import InfoBar, InfoBarPosition
        InfoBar.success(
            title="下载完成",
            content=f"更新包已下载到: {file_path}",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=5000,
        )

    # ========== 窗口事件 ==========

    def keyPressEvent(self, event):
        """全局键盘事件 — Ctrl+F 搜索"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_F:
                # 搜索消息
                if hasattr(self.chat_page, 'search_bar'):
                    self.chat_page.search_bar.show_search()
                return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        """关闭事件 — 最小化到托盘或退出"""
        # 先尝试最小化到托盘
        if not getattr(self, '_force_quit', False) and self.tray_manager.handle_close_event(event):
            return  # 事件已处理（最小化到托盘）

        # 正常退出
        self._cleanup_and_exit(event)

    def _on_quit_requested(self):
        """托盘菜单触发退出"""
        self._force_quit = True
        self.close()

    def _cleanup_and_exit(self, event):
        """清理资源并退出"""
        logger.info("Cleaning up and exiting...")

        # 停止语音管理器
        if self.voice_manager.is_listening:
            self.voice_manager.stop_listening()

        # 停止全局快捷键
        self.hotkey_manager.stop()

        # 关闭桌面宠物
        if self._pet_window:
            self._pet_window.close()

        # 性能管理器清理
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

        self.tray_manager.cleanup()
        event.accept()
        logger.info("Cleanup completed")


def main():
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

    app = QApplication(sys.argv)

    # 全局默认字体
    from PySide6.QtGui import QFont
    app.setFont(QFont("Microsoft YaHei UI", 10))

    # 设置应用图标
    icon_path = os.path.join(NATIVE_DIR, "gugu_native", "resources", "app.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 启动画面
    splash_path = os.path.join(NATIVE_DIR, "gugu_native", "resources", "splash.png")
    splash = None
    if os.path.exists(splash_path):
        splash_pix = QPixmap(splash_path)
        splash = QSplashScreen(splash_pix)
        splash.show()
        splash.showMessage("正在启动...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
                          Qt.GlobalColor.white)
        app.processEvents()  # 确保 splash 立即渲染

    window = GuguGagaApp()
    window.show()

    # 关闭启动画面
    if splash:
        splash.finish(window)

    exit_code = app.exec()

    # 清理 Live2D 资源
    if LIVE2D_AVAILABLE and live2d:
        try:
            live2d.dispose()
        except Exception:
            pass

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
