"""
Phase 0.3 + 0.4 综合验证:
- Python 直接调用 AIVTuber 后端（不需要 HTTP/WS）
- QMediaPlayer / QSoundEffect 播放 TTS 音频
- QSystemTrayIcon 系统托盘

关键要点:
1. AIVTuber 实例可直接创建，无需启动 HTTP/WS 服务
2. process_message(text) → Dict[str, Any] 直接获取对话结果
3. stream_chat(msg, history, callback) → 流式对话+回调
4. QMediaPlayer 可播放本地音频文件（TTS 输出）
5. QSystemTrayIcon 实现系统托盘
"""

import sys
import os
import signal

# 确保项目路径在 sys.path 中
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton,
    QHBoxLayout, QTextEdit, QLineEdit, QSystemTrayIcon, QMenu
)
from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QIcon, QAction, QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtOpenGLWidgets import QOpenGLWidget

import live2d.v3 as live2d
live2d.init()


class Live2DWidget(QOpenGLWidget):
    """Live2D 模型渲染组件（简化版）"""

    def __init__(self, model_path, parent=None):
        super().__init__(parent)
        self.model = None
        self.model_path = model_path
        self._mouse_x = 0.0
        self._mouse_y = 0.0
        self.setMinimumSize(300, 400)
        self.setMouseTracking(True)

    def initializeGL(self):
        try:
            live2d.glInit()
            self.model = live2d.LAppModel()
            self.model.LoadModelJson(self.model_path)
            self.model.SetAutoBlinkEnable(True)
            self.model.SetAutoBreathEnable(True)
            self.model.StartRandomMotion("Idle", live2d.MotionPriority.IDLE)
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick)
            self._timer.start(16)
            print("[Live2D] 模型加载成功")
        except Exception as e:
            print(f"[Live2D] 模型加载失败: {e}")

    def paintGL(self):
        live2d.clearBuffer(0.1, 0.1, 0.15, 1.0)
        if self.model:
            self.model.Update()
            self.model.Draw()

    def resizeGL(self, w, h):
        if self.model:
            self.model.Resize(w, h)

    def _tick(self):
        if self.model:
            self.model.Drag(self._mouse_x, self._mouse_y)
        self.update()

    def mouseMoveEvent(self, event):
        if self.model:
            x = (event.position().x() / self.width()) * 2 - 1
            y = 1 - (event.position().y() / self.height()) * 2
            self._mouse_x = x
            self._mouse_y = y
        super().mouseMoveEvent(event)

    def set_mouth_open(self, value):
        """TTS 口型同步"""
        if self.model and hasattr(live2d, 'StandardParams'):
            try:
                self.model.SetParameterValueById(
                    live2d.StandardParams.ParamMouthOpenY, value
                )
            except Exception:
                pass


class TestWindow(QMainWindow):
    """Phase 0.3+0.4 综合测试窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("咕咕嘎嘎 AI-VTuber — Phase 0.3+0.4 验证")
        self.setMinimumSize(900, 650)
        self.backend = None

        # === 主布局 ===
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        # === 左侧: Live2D ===
        model_path = os.path.join(
            PROJECT_DIR, "app", "web", "static", "assets", "model",
            "hiyori", "Hiyori.model3.json"
        )
        self.live2d_widget = Live2DWidget(model_path)
        layout.addWidget(self.live2d_widget, stretch=2)

        # === 右侧: 对话 + 控制 ===
        right_panel = QVBoxLayout()
        layout.addLayout(right_panel, stretch=3)

        # 对话显示区
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlaceholderText("对话将显示在这里...")
        right_panel.addWidget(self.chat_display, stretch=1)

        # 输入行
        input_row = QHBoxLayout()
        right_panel.addLayout(input_row)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入消息...")
        self.input_field.returnPressed.connect(self.send_message)
        input_row.addWidget(self.input_field, stretch=1)

        send_btn = QPushButton("发送")
        send_btn.clicked.connect(self.send_message)
        input_row.addWidget(send_btn)

        # 控制按钮行
        ctrl_row = QHBoxLayout()
        right_panel.addLayout(ctrl_row)

        # 初始化后端按钮
        self.init_btn = QPushButton("初始化后端")
        self.init_btn.clicked.connect(self.init_backend)
        ctrl_row.addWidget(self.init_btn)

        # 播放音频测试
        test_audio_btn = QPushButton("测试音频")
        test_audio_btn.clicked.connect(self.test_audio)
        ctrl_row.addWidget(test_audio_btn)

        # === 音频播放器 ===
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.8)

        # === 系统托盘 ===
        self._setup_tray()

        # 状态栏
        self.statusBar().showMessage("点击「初始化后端」开始...")

    def _setup_tray(self):
        """设置系统托盘"""
        # 使用应用图标（如果有的话）
        icon_path = os.path.join(PROJECT_DIR, "assets", "icon.ico")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
            # 使用系统默认应用图标
            icon = QIcon.fromTheme("computer")
            if icon.isNull():
                # 创建一个简单的彩色图标
                pixmap = QPixmap(32, 32)
                pixmap.fill(Qt.GlobalColor.cyan)
                icon = QIcon(pixmap)

        self.tray_icon = QSystemTrayIcon(icon, self)

        tray_menu = QMenu()

        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_activated)
        self.tray_icon.show()

        self.tray_icon.showMessage(
            "咕咕嘎嘎 AI-VTuber",
            "程序已最小化到系统托盘",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
        print("[Tray] 系统托盘创建成功")

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()

    def init_backend(self):
        """初始化 AIVTuber 后端（直调模式，不启动 HTTP/WS）"""
        self.init_btn.setEnabled(False)
        self.init_btn.setText("初始化中...")
        self.statusBar().showMessage("正在初始化 AIVTuber 后端...")

        try:
            from app.main import AIVTuber
            self.backend = AIVTuber()
            self.init_btn.setText("后端已就绪 ✅")
            self.statusBar().showMessage("后端初始化成功 — 可以开始对话")
            self.chat_display.append(
                "<span style='color: #4CAF50;'>✅ 后端初始化成功！直接调用 process_message() 即可对话。</span>"
            )
            print("[Backend] AIVTuber 初始化成功")
        except Exception as e:
            self.init_btn.setText("初始化失败 ❌")
            self.statusBar().showMessage(f"后端初始化失败: {e}")
            self.chat_display.append(
                f"<span style='color: #f44336;'>❌ 后端初始化失败: {e}</span>"
            )
            print(f"[Backend] 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            self.init_btn.setEnabled(True)
            self.init_btn.setText("重试初始化")

    def send_message(self):
        """发送消息（后端直调模式）"""
        text = self.input_field.text().strip()
        if not text:
            return
        if not self.backend:
            self.chat_display.append(
                "<span style='color: #FF9800;'>⚠️ 请先初始化后端</span>"
            )
            return

        self.input_field.clear()
        self.chat_display.append(f"<b>你:</b> {text}")
        self.statusBar().showMessage("正在思考...")

        try:
            # 核心：直接 Python 调用，无需 HTTP/WS！
            result = self.backend.process_message(text)
            reply = result.get("text", "")
            action = result.get("action")

            self.chat_display.append(f"<b>AI:</b> {reply}")

            # 播放 TTS 音频（如果后端生成了）
            audio_path = result.get("audio_path")
            if audio_path and os.path.exists(audio_path):
                self._play_audio(audio_path)

            if action:
                self.chat_display.append(
                    f"<span style='color: #9C27B0;'><i>动作: {action}</i></span>"
                )

            self.statusBar().showMessage("就绪")
        except Exception as e:
            self.chat_display.append(
                f"<span style='color: #f44336;'>❌ 错误: {e}</span>"
            )
            self.statusBar().showMessage(f"错误: {e}")

    def _play_audio(self, file_path):
        """播放音频文件"""
        try:
            self.media_player.setSource(QUrl.fromLocalFile(file_path))
            self.media_player.play()
            print(f"[Audio] 播放: {file_path}")
        except Exception as e:
            print(f"[Audio] 播放失败: {e}")

    def test_audio(self):
        """测试 QMediaPlayer 音频播放"""
        # 生成一个简单的测试 WAV
        import struct
        import tempfile

        sample_rate = 44100
        duration = 0.5  # 秒
        freq = 440  # A4 音高
        n_samples = int(sample_rate * duration)

        wav_path = os.path.join(tempfile.gettempdir(), "test_tone.wav")

        with open(wav_path, 'wb') as f:
            # WAV header
            f.write(b'RIFF')
            f.write(struct.pack('<I', 36 + n_samples * 2))
            f.write(b'WAVE')
            f.write(b'fmt ')
            f.write(struct.pack('<IHHIIHH', 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
            f.write(b'data')
            f.write(struct.pack('<I', n_samples * 2))
            for i in range(n_samples):
                sample = int(32767 * 0.3 * (1 if (i // (sample_rate // freq)) % 2 == 0 else -1))
                f.write(struct.pack('<h', sample))

        self._play_audio(wav_path)
        self.chat_display.append(
            "<span style='color: #2196F3;'>🔊 音频测试: 播放 440Hz 方波</span>"
        )

    def closeEvent(self, event):
        """关闭窗口时最小化到托盘"""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "咕咕嘎嘎 AI-VTuber",
            "程序已最小化到系统托盘，双击图标恢复",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )


def main():
    app = QApplication(sys.argv)
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出，托盘保留

    window = TestWindow()
    window.show()

    exit_code = app.exec()
    live2d.dispose()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
