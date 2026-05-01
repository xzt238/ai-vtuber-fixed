#!/usr/bin/env python3
"""
=====================================
咕咕嘎嘎 AI-VTuber — 桌面启动器
=====================================

功能概述:
    游戏式桌面启动器。双击启动，先展示启动画面，后端自动在后台启动，
    就绪后窗口无缝跳转到主界面。全程原生窗口，有X按钮可关闭。

核心架构:
    用户双击 desktop.bat
         ↓
    ┌─────────────────────────────────────────────────┐
    │  pywebview 原生窗口                               │
    │                                                   │
    │  阶段1: splash.html (启动画面)                     │
    │    - 加载动画 + 进度条 + 实时状态                    │
    │    - 后端启动中... → 预热LLM → 预热TTS → 即将就绪    │
    │                                                   │
    │  阶段2: localhost:12393 (主界面)                    │
    │    - 自动跳转，零感知切换                            │
    │    - window.pywebview.api 可调用启动器功能           │
    │                                                   │
    │  系统托盘: 右键 → 显示窗口 / 退出                   │
    │  关闭窗口 → 退出后端 → 清理退出                      │
    └──────────────────────┬────────────────────────────┘
                           │ subprocess
                           ▼
    ┌─────────────────────────────────────────────────┐
    │  Python 后端 (app.main --desktop)                │
    │  HTTP :12393  │  WebSocket :12394                │
    │  ASR / LLM / TTS / Vision / Memory              │
    └─────────────────────────────────────────────────┘

作者: 咕咕嘎嘎
日期: 2026-04-25
"""

import os
import sys
import time
import signal
import threading
import subprocess
from pathlib import Path
from typing import Optional

# ============ 项目路径 ============
# 支持 PyInstaller 打包后的 EXE 运行
# 打包后 EXE 在项目根目录，项目结构: GuguGaga.exe + python/ + app/ + launcher/
# 开发时 launcher.py 在 launcher/ 子目录下
if getattr(sys, 'frozen', False):
    # PyInstaller 打包模式: EXE 所在目录就是项目根目录
    PROJECT_ROOT = Path(sys.executable).parent.resolve()
    LAUNCHER_DIR = PROJECT_ROOT / "launcher"
    SPLASH_PATH = LAUNCHER_DIR / "splash.html"
    # 如果 launcher/ 下没有 splash.html，尝试 PyInstaller 临时目录
    if not SPLASH_PATH.exists():
        SPLASH_PATH = Path(sys._MEIPASS) / "splash.html"
else:
    # 开发模式: launcher.py 在 launcher/ 子目录下
    LAUNCHER_DIR = Path(__file__).parent.resolve()          # launcher/
    PROJECT_ROOT = Path(__file__).parent.parent.resolve()    # ai-vtuber-fixed/
    SPLASH_PATH = LAUNCHER_DIR / "splash.html"               # 启动画面就在 launcher/ 里

# Logo 图片路径（用于嵌入到 splash.html）
LOGO_PATH = PROJECT_ROOT / "assets" / "gugugaga_logo.png"

APP_DIR = PROJECT_ROOT / "app"

# 确保模块搜索路径包含 app/
sys.path.insert(0, str(APP_DIR))


# ============ 配置 ============

BACKEND_PORT = 12393
BACKEND_WS_PORT = 12394
BACKEND_URL = f"http://localhost:{BACKEND_PORT}"
STARTUP_TIMEOUT = 300       # 5 分钟超时
HEALTH_INTERVAL = 0.3       # 300ms 检查一次（v1.9.27: 从 1s 优化，加速启动检测）

WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
WINDOW_MIN_W = 1024
WINDOW_MIN_H = 768
WINDOW_TITLE = "咕咕嘎嘎 AI-VTuber"


# ============ 后端进程管理 ============

class BackendManager:
    """
    后端进程管理器 — 启动/监控/停止 Python 后端

    流程:
        1. subprocess 启动 app.main --desktop
        2. 后台线程轮询 http://localhost:12393/ 健康检查
        3. 就绪 → 回调 on_ready
        4. 崩溃/超时 → 回调 on_failed
    """

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self._running = False
        self._log_thread = None
        # 外部回调
        self.on_status = None    # (str) 状态文字更新
        self.on_ready = None     # () 后端就绪
        self.on_failed = None    # (str) 错误信息

    def start(self) -> bool:
        """启动后端子进程（非阻塞）"""
        cmd = self._get_python_cmd()
        print(f"[启动器] 启动后端: {' '.join(cmd)}")
        print(f"[启动器] 工作目录: {PROJECT_ROOT}")

        env = os.environ.copy()
        env["HF_HOME"] = str(PROJECT_ROOT / ".cache" / "huggingface")
        env["HF_ENDPOINT"] = "https://hf-mirror.com"
        env["PYTHONIOENCODING"] = "utf-8"
        env["GUGUGAGA_DESKTOP"] = "1"
        # 关键: 禁用 Python stdout 缓冲，否则 piped stdout 默认 block-buffered
        # 导致 launcher.log 几乎捕获不到后端输出
        env["PYTHONUNBUFFERED"] = "1"

        # 将 PyTorch CUDA DLL 和嵌入式 Python DLL 加入 PATH
        # 双击 EXE 时系统 PATH 可能不含 CUDA，导致 ctranslate2/sounddevice 等 DLL 加载失败
        extra_paths = []
        python_dir = PROJECT_ROOT / "python"
        if python_dir.exists():
            # 嵌入式 Python 自身 DLL
            extra_paths.append(str(python_dir))
            # PyTorch CUDA 运行时 DLL (cublas64_12.dll, cufft64_11.dll 等)
            torch_lib = python_dir / "Lib" / "site-packages" / "torch" / "lib"
            if torch_lib.exists():
                extra_paths.append(str(torch_lib))
            # NVIDIA CUDA Toolkit DLL (cublasLt, cuDNN 等 — torch/lib 可能不全)
            nvidia_bin = python_dir / "Lib" / "site-packages" / "nvidia" / "cublas" / "bin"
            if nvidia_bin.exists():
                extra_paths.append(str(nvidia_bin))
            nvidia_cudnn = python_dir / "Lib" / "site-packages" / "nvidia" / "cudnn" / "bin"
            if nvidia_cudnn.exists():
                extra_paths.append(str(nvidia_cudnn))
        if extra_paths:
            env["PATH"] = ";".join(extra_paths) + ";" + env.get("PATH", "")

        # 记录完整环境信息到日志（修复后检测 torch/lib PATH 是否生效）
        try:
            diag_path = PROJECT_ROOT / "logs" / "launcher.log"
            with open(diag_path, "a", encoding="utf-8") as f:
                import datetime
                f.write(f"\n[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] 后端环境配置\n")
                f.write(f"  命令: {' '.join(cmd)}\n")
                f.write(f"  工作目录: {PROJECT_ROOT}\n")
                f.write(f"  frozen: {getattr(sys, 'frozen', False)}\n")
                f.write(f"  sys.executable: {sys.executable}\n")
                f.write(f"  PYTHONUNBUFFERED: {env.get('PYTHONUNBUFFERED')}\n")
                f.write(f"  extra_paths: {extra_paths}\n")
                f.write(f"  PATH (前300字符): {env.get('PATH', '')[:300]}\n")
        except Exception:
            pass

        try:
            si = None
            if sys.platform == "win32":
                si = subprocess.STARTUPINFO()
                # 桌面模式下隐藏后端控制台窗口
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE

            self.process = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                encoding='utf-8',
                errors='replace',
                startupinfo=si,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            )

            self._running = True
            print(f"[启动器] 后端进程 PID: {self.process.pid}")

            # 日志转发线程
            self._log_thread = threading.Thread(
                target=self._forward_logs, daemon=True, name="backend-log"
            )
            self._log_thread.start()

            # 健康检查线程
            threading.Thread(
                target=self._health_check, daemon=True, name="backend-health"
            ).start()

            return True

        except FileNotFoundError:
            self._emit_failed("找不到 Python 3.11，请确保已安装")
            return False
        except Exception as e:
            self._emit_failed(f"启动失败: {e}")
            return False

    def stop(self):
        """优雅停止后端"""
        print("[启动器] 正在停止后端...")
        self._running = False

        if self.process and self.process.poll() is None:
            try:
                if sys.platform == "win32":
                    os.kill(self.process.pid, signal.CTRL_BREAK_EVENT)
                else:
                    self.process.terminate()

                self.process.wait(timeout=5)
                print("[启动器] 后端已正常退出")
            except subprocess.TimeoutExpired:
                print("[启动器] 后端未响应，强制终止")
                self.process.kill()
                self.process.wait(timeout=3)
            except ProcessLookupError:
                pass
            except Exception as e:
                print(f"[启动器] 停止异常: {e}")

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def _get_python_cmd(self) -> list:
        """获取 Python 启动命令"""
        embedded = PROJECT_ROOT / "python" / "python.exe"
        if embedded.exists():
            # -u: 禁用 stdout 缓冲（双保险，配合 PYTHONUNBUFFERED=1）
            return [str(embedded), "-u", "-m", "app.main", "--desktop"]
        return ["py", "-3.11", "-u", "-m", "app.main", "--desktop"]

    def _forward_logs(self):
        """转发后端 stdout → 日志文件 + 启动画面状态提取
        
        v1.9.24 修复: 
        1. 不在循环中调用 print()（PyInstaller 无控制台时可能阻塞）
        2. on_status 回调改为非阻塞（防 evaluate_js 死锁）
        3. 优先写日志文件（管道满时后端 print() 会阻塞）
        """
        log_file = None
        try:
            log_path = PROJECT_ROOT / "logs" / "launcher.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_file = open(log_path, "a", encoding="utf-8")
            import datetime
            log_file.write(f"\n{'='*60}\n[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] 后端启动\n{'='*60}\n")
            log_file.flush()
        except Exception:
            log_file = None

        try:
            for line in self.process.stdout:
                if not self._running:
                    break
                line = line.rstrip()
                if not line:
                    continue

                # v1.9.24: 先写日志文件（最可靠），再尝试控制台输出
                if log_file:
                    try:
                        log_file.write(f"{line}\n")
                        log_file.flush()
                    except Exception:
                        pass
                
                # 控制台输出（PyInstaller 无控制台时可能静默失败，不影响主流程）
                try:
                    print(f"[后端] {line}")
                except Exception:
                    pass

                status = self._extract_status(line)
                if status and self.on_status:
                    self.on_status(status)
        except Exception as e:
            if self._running:
                print(f"[启动器] 日志转发异常: {e}")
        finally:
            if log_file:
                try:
                    log_file.close()
                except Exception:
                    pass

    def _extract_status(self, line: str) -> Optional[str]:
        """从后端日志中提取可读的状态文字"""
        line_lower = line.lower()

        if "懒加载" in line or "初始化" in line:
            if "LLM" in line or "llm" in line_lower:
                return "正在初始化语言模型..."
            if "TTS" in line or "tts" in line_lower:
                return "正在初始化语音合成..."
            if "ASR" in line or "asr" in line_lower:
                return "正在初始化语音识别..."
            if "Live2D" in line:
                return "正在加载 Live2D..."
            if "Vision" in line or "vision" in line_lower:
                return "正在初始化视觉模块..."
            return "正在初始化模块..."

        if "服务已启动" in line or "桌面模式服务已启动" in line:
            return "后端服务已启动"
        if "启动Web服务" in line:
            return "正在启动 Web 服务..."

        return None

    def _health_check(self):
        """轮询后端健康状态"""
        import urllib.request
        import urllib.error

        self._emit_status("正在启动后端服务...")
        time.sleep(0.5)  # v1.9.27: 从 2s 优化到 0.5s（后端进程启动通常 >0.5s）

        start_time = time.time()
        last_status_time = start_time

        while self._running:
            elapsed = time.time() - start_time

            if self.process.poll() is not None:
                code = self.process.returncode
                self._emit_failed(f"后端进程退出（退出码: {code}）")
                return

            if elapsed > STARTUP_TIMEOUT:
                self._emit_failed(f"后端启动超时（{STARTUP_TIMEOUT}秒）")
                return

            try:
                url = f"http://localhost:{BACKEND_PORT}/"
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=2) as resp:
                    if resp.status == 200:
                        print(f"[启动器] 后端就绪！耗时 {elapsed:.1f}秒")
                        self._emit_status("后端就绪，正在加载主界面...")
                        # v1.9.27: 移除 time.sleep(0.5)，健康检查通过即可跳转
                        if self.on_ready:
                            self.on_ready()
                        return
            except (urllib.error.URLError, ConnectionRefusedError, OSError):
                pass

            now = time.time()
            if now - last_status_time > 8:
                self._emit_status(f"等待后端就绪... ({elapsed:.0f}s)")
                last_status_time = now

            time.sleep(HEALTH_INTERVAL)

    def _emit_status(self, msg: str):
        if self.on_status:
            self.on_status(msg)

    def _emit_failed(self, msg: str):
        self._running = False
        print(f"[启动器] {msg}")
        if self.on_failed:
            self.on_failed(msg)


# ============ 桌面窗口（pywebview） ============

class DesktopApp:
    """
    桌面应用主控 — 管理窗口生命周期

    流程:
        1. 创建 pywebview 窗口，加载 splash.html（启动画面）
        2. 启动后端子进程
        3. 后端日志 → 实时推送到启动画面
        4. 后端就绪 → 窗口跳转到 localhost:12393（主界面）
        5. 窗口关闭 → 停止后端 → 退出
    """

    def __init__(self):
        self.backend = BackendManager()
        self.window = None
        self._tray = None
        self._should_quit = False
        self._splash_done = False  # splash 关闭后不再调用 evaluate_js（防止死锁）

    def _load_splash_html(self) -> str:
        """加载 splash.html 并嵌入 Logo Base64，返回修改后的 HTML 内容"""
        import base64

        # 读取 splash.html 内容
        splash_content = SPLASH_PATH.read_text(encoding="utf-8")

        # 读取 Logo 图片并转为 Base64
        if LOGO_PATH.exists():
            with open(LOGO_PATH, "rb") as f:
                logo_base64 = base64.b64encode(f.read()).decode("utf-8")
            logo_data_url = f"data:image/png;base64,{logo_base64}"
            # 替换 HTML 中的图片 URL
            splash_content = splash_content.replace(
                'src="../assets/gugugaga_logo.png"',
                f'src="{logo_data_url}"'
            )
            print(f"[启动器] Logo 已嵌入 (Base64, {len(logo_base64)} bytes)")

        return splash_content

    def run(self):
        """主入口 — 启动应用"""
        try:
            import webview
        except ImportError:
            print("[启动器] pywebview 未安装，尝试安装...")
            self._install_pywebview()
            import webview

        # 绑定后端回调
        self.backend.on_status = self._on_backend_status
        self.backend.on_ready = self._on_backend_ready
        self.backend.on_failed = self._on_backend_failed

        # 启动后端
        if not self.backend.start():
            self._show_error_and_exit("无法启动后端")

        # 创建 pywebview 窗口 — 先显示启动画面（嵌入 Logo）
        api = LauncherAPI(self)

        # 获取嵌入 Logo 的 HTML 内容
        splash_html = self._load_splash_html()

        # pywebview 需要文件路径，使用临时文件
        import tempfile
        import os
        temp_html = os.path.join(tempfile.gettempdir(), "gugugaga_splash.html")
        with open(temp_html, "w", encoding="utf-8") as f:
            f.write(splash_html)

        self.window = webview.create_window(
            title=WINDOW_TITLE,
            url=temp_html,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            min_size=(WINDOW_MIN_W, WINDOW_MIN_H),
            js_api=api,
            text_select=True,
            confirm_close=False,
            frameless=False,
        )

        # 绑定窗口关闭事件
        self.window.events.closing += self._on_window_closing

        # 启动系统托盘
        self._start_tray()

        # 启动 pywebview 事件循环（阻塞，直到窗口关闭）
        debug = "--debug" in sys.argv or os.getenv("GUGUGAGA_DEBUG") == "1"
        webview.start(debug=debug, http_server=False)

        # 窗口关闭后 → 停止后端
        self.backend.stop()

    def _on_backend_status(self, msg: str):
        """后端状态 → 推送到启动画面
        
        v1.9.24 修复: splash 关闭后不再调用 evaluate_js
        根因: window.load_url() 导航期间 evaluate_js 会死锁
        → _forward_logs 线程卡死 → stdout 管道满 → 后端 print() 阻塞 → 服务器冻死
        """
        if self._splash_done:
            return
        if self.window:
            safe_msg = msg.replace("'", "\\'").replace("\n", " ")
            # 非阻塞: 在独立线程中调用 evaluate_js，设超时防卡死
            def _update():
                try:
                    self.window.evaluate_js(f"updateStatus('{safe_msg}')")
                except Exception:
                    pass
            t = threading.Thread(target=_update, daemon=True)
            t.start()
            t.join(timeout=3)  # 最多等3秒，超时则放弃（不阻塞 _forward_logs）

    def _on_backend_ready(self):
        """后端就绪 → 平滑过渡到主界面
        
        v1.9.24 修复: 跳转前先设 _splash_done=True
        防止 _forward_logs 在导航期间继续调用 evaluate_js 导致死锁
        """
        self._splash_done = True  # ← 关键: 阻止后续 evaluate_js 调用
        if not self.window:
            print("[启动器] ⚠️ 窗口对象为空，无法跳转")
            return
        try:
            # 触发 splash 淡出动画
            print("[启动器] 触发淡出动画...")
            self.window.evaluate_js("onBackendReady()")
            # 等待动画完成（CSS 0.8s 淡出，0.5s 即可——WebView2 导航需一点时间但不需要等完全淡出）
            time.sleep(0.5)
            # 跳转到主界面
            print(f"[启动器] 正在跳转到 {BACKEND_URL} ...")
            self.window.load_url(BACKEND_URL)
            print("[启动器] 已跳转到主界面")
        except Exception as e:
            print(f"[启动器] 跳转失败: {e}，尝试直接加载")
            try:
                self.window.load_url(BACKEND_URL)
            except Exception as e2:
                print(f"[启动器] 直接加载也失败: {e2}")

    def _on_backend_failed(self, msg: str):
        """后端失败 → 启动画面显示错误"""
        if self._splash_done:
            return
        if self.window:
            safe_msg = msg.replace("'", "\\'").replace("\n", " ")
            def _show():
                try:
                    self.window.evaluate_js(f"showError('{safe_msg}')")
                except Exception:
                    pass
            t = threading.Thread(target=_show, daemon=True)
            t.start()
            t.join(timeout=3)

    def _on_window_closing(self):
        """窗口关闭"""
        if not self._should_quit:
            self._should_quit = True

    def _start_tray(self):
        """系统托盘（可选）"""
        try:
            import pystray
            from PIL import Image, ImageDraw
        except ImportError:
            print("[启动器] pystray/Pillow 未安装，跳过系统托盘")
            return

        def create_icon():
            img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            dc = ImageDraw.Draw(img)
            dc.ellipse([8, 8, 56, 56], fill=(102, 126, 234, 255))
            dc.text((18, 16), "GG", fill=(255, 255, 255, 255))
            return img

        def on_show(icon, item):
            if self.window:
                self.window.restore()
                self.window.show()

        def on_quit(icon, item):
            self._should_quit = True
            icon.stop()
            if self.window:
                self.window.destroy()
            self.backend.stop()

        menu = pystray.Menu(
            pystray.MenuItem("显示窗口", on_show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", on_quit),
        )

        self._tray = pystray.Icon("GuguGaga", icon=create_icon(), title="咕咕嘎嘎", menu=menu)
        threading.Thread(target=self._tray.run, daemon=True, name="system-tray").start()

    def _install_pywebview(self):
        """安装 pywebview"""
        import subprocess as sp
        print("[启动器] 安装 pywebview...")
        try:
            sp.check_call(
                [sys.executable, "-m", "pip", "install", "pywebview"],
                stdout=sp.DEVNULL, stderr=sp.DEVNULL,
            )
            print("[启动器] pywebview 安装成功")
        except sp.CalledProcessError:
            print("[启动器] pywebview 安装失败，将降级到浏览器模式")
            self._fallback_to_browser()

    def _fallback_to_browser(self):
        """降级到浏览器模式"""
        import webbrowser
        print("[启动器] 使用浏览器模式")

        def on_ready():
            webbrowser.open(BACKEND_URL)
            print("[启动器] 浏览器已打开，此窗口请保持运行")

        self.backend.on_ready = on_ready
        self.backend.on_failed = lambda msg: print(f"[启动器] 失败: {msg}")

        if not self.backend.start():
            input("按回车退出...")
            sys.exit(1)

        print("[启动器] 按 Ctrl+C 退出")
        try:
            while self.backend.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.backend.stop()

    def _show_error_and_exit(self, msg: str):
        print(f"[启动器] {msg}")
        input("按回车退出...")
        sys.exit(1)


# ============ 前端 API 桥接 ============

class LauncherAPI:
    """
    暴露给前端 JavaScript 的 API

    使用方式（在主界面的 JS 中）:
        const isDesktop = await window.pywebview.api.isDesktop();  // true
        const version  = await window.pywebview.api.getVersion();
        window.pywebview.api.quit();       // 退出应用
        window.pywebview.api.minimize();   // 最小化
    """

    def __init__(self, app: DesktopApp):
        self._app = app

    def getVersion(self) -> str:
        vf = PROJECT_ROOT / "docs" / "VERSION.md"
        if vf.exists():
            for line in vf.read_text(encoding="utf-8").splitlines():
                if "STABLE" in line or line.startswith("## v"):
                    for part in line.split():
                        if part.startswith("v") and any(c.isdigit() for c in part):
                            return part
        return "1.9.54"

    def isDesktop(self) -> bool:
        return True

    def quit(self):
        self._app._should_quit = True
        self._app.backend.stop()
        if self._app.window:
            self._app.window.destroy()

    def minimize(self):
        if self._app.window:
            self._app.window.minimize()

    def getAppPath(self) -> str:
        return str(PROJECT_ROOT)

    def getBackendUrl(self) -> str:
        return BACKEND_URL

    def openExternal(self, url: str):
        import webbrowser
        webbrowser.open(url)


# ============ 入口 ============

def main():
    # v1.9.29: 解除 pip 下载 DLL 的网络锁定标记
    # Windows 会对从网络下载的 DLL 添加 Zone.Identifier，.NET 拒绝加载导致 pywebview 崩溃
    _unblock_dlls()

    app = DesktopApp()
    try:
        app.run()
    except KeyboardInterrupt:
        app.backend.stop()
    except Exception as e:
        print(f"[启动器] 异常退出: {e}")
        app.backend.stop()
    finally:
        print("[启动器] 再见~")


def _unblock_dlls():
    """解除 python/Lib/site-packages 下 DLL/PYD 的网络锁定标记"""
    sp_dir = PROJECT_ROOT / "python" / "Lib" / "site-packages"
    if not sp_dir.exists():
        return
    try:
        import subprocess
        subprocess.run(
            ["powershell", "-Command",
             f"Get-ChildItem '{sp_dir}' -Recurse -Include *.dll,*.pyd | Unblock-File -ErrorAction SilentlyContinue"],
            capture_output=True, timeout=10
        )
    except Exception:
        pass  # 解锁失败不影响启动


if __name__ == "__main__":
    main()
