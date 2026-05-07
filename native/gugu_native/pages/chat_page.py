"""
对话页面 — Chat + Live2D + TTS/STT 控制

布局:
┌──────────────────────────────────────────────────────────┐
│ ┌──────────┐  ┌──────────┐  ┌────────────────────────┐  │
│ │ Live2D   │  │ 会话列表 │  │  消息搜索栏            │  │
│ │ 模型     │  │          │  ├────────────────────────┤  │
│ │          │  │          │  │  对话显示区             │  │
│ │          │  │          │  │  (QWebEngineView)      │  │
│ │          │  │          │  │                        │  │
│ │          │  │          │  ├────────────────────────┤  │
│ │          │  │          │  │ 多行输入框 + 发送/停止  │  │
│ │          │  │          │  ├────────────────────────┤  │
│ │          │  │          │  │ TTS引擎|音色|录音|实时  │  │
│ └──────────┘  └──────────┘  └────────────────────────┘  │
└──────────────────────────────────────────────────────────┘

v1.9.86: 完全重构
- QWebEngineView Markdown 渲染
- 多行输入框 (Shift+Enter 换行)
- 消息操作菜单 (复制/重试/引用/编辑)
- 多会话管理
- 消息搜索
- 拖拽发送文件
- 引用回复
"""

import os
import sys
import json
import time
import tempfile
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QComboBox,
    QGroupBox, QApplication, QFrame, QSplitter
)
from PySide6.QtCore import Qt, Signal, Slot, QThread, QMutex, Q_ARG, QTimer
from PySide6.QtGui import QTextCursor, QFont, QDragEnterEvent, QDropEvent
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl

from qfluentwidgets import (
    PushButton, ToolButton, FluentIcon, CaptionLabel,
    TogglePushButton, Slider
)
from PySide6.QtWidgets import QFileDialog

# 项目根目录
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# TTS 偏好文件路径
_TTS_PREFS_FILE = os.path.join(PROJECT_DIR, "app", "cache", "tts_preferences.json")

from gugu_native.widgets.live2d_widget import Live2DWidget
from gugu_native.widgets.chat_web_display import ChatWebDisplay
from gugu_native.widgets.multi_line_input import MultiLineInputV2
from gugu_native.widgets.session_manager import SessionManager, ChatSession
from gugu_native.widgets.message_search import MessageSearchBar
from gugu_native.widgets.animation_controller import AnimationController


class StreamChatWorker(QThread):
    """流式对话线程 — 调用 backend.llm.stream_chat() 并逐 chunk 更新 UI

    支持两种 TTS 模式：
    - streaming_tts=True: 流式分句，检测到句子结束立即发出 sentence_ready 信号
    - streaming_tts=False: 整段合成，等待完整回复后一次性合成 TTS
    """
    chunk_received = Signal(str)      # 每个文本片段
    sentence_ready = Signal(str)      # 流式模式：检测到完整句子
    finished_stream = Signal(dict)    # 完整结果
    error = Signal(str)               # 错误
    tool_call_status = Signal(str)    # FC 工具调用状态提示（如"🌤 正在查询天气…"）

    # 句子结束标点
    _SENTENCE_ENDS = set('。！？.!?')

    def __init__(self, backend, text, history, streaming_tts=False):
        super().__init__()
        self.backend = backend
        self.text = text
        self.history = history
        self.streaming_tts = streaming_tts
        self._stop_requested = False
        self._mutex = QMutex()
        self._sentence_buffer = ""  # 流式模式：句子缓冲区

    def stop_stream(self):
        """请求停止流式对话"""
        self._mutex.lock()
        self._stop_requested = True
        self._mutex.unlock()

    def is_stop_requested(self):
        self._mutex.lock()
        val = self._stop_requested
        self._mutex.unlock()
        return val

    def _extract_sentences(self, chunk_text: str):
        """流式模式：从 chunk 中提取完整句子"""
        self._sentence_buffer += chunk_text
        sentences = []
        i = 0
        while i < len(self._sentence_buffer):
            if self._sentence_buffer[i] in self._SENTENCE_ENDS:
                # 找到句子结束点
                end = i + 1
                # 包含连续的结束标点（如 ！！！）
                while end < len(self._sentence_buffer) and self._sentence_buffer[end] in self._SENTENCE_ENDS:
                    end += 1
                sentence = self._sentence_buffer[:end].strip()
                if sentence:
                    sentences.append(sentence)
                self._sentence_buffer = self._sentence_buffer[end:]
                i = 0  # 重置索引（buffer 已截断）
            else:
                i += 1
        return sentences

    def run(self):
        try:
            # 获取记忆上下文
            relevant_memories = self.backend.memory.search(self.text, top_k=3)
            context = ""
            if relevant_memories:
                context = "\n\n相关记忆:\n" + "\n".join(
                    [m.get("content") or m.get("text", "") for m in relevant_memories]
                )

            full_prompt = self.text
            if context:
                full_prompt = f"用户问题: {self.text}{context}"

            # 流式回调 — 在工作线程中触发信号
            def on_chunk(chunk_text: str):
                if self.is_stop_requested():
                    return
                self.chunk_received.emit(chunk_text)
                # 流式分句 TTS：检测句子结束
                if self.streaming_tts and chunk_text:
                    sentences = self._extract_sentences(chunk_text)
                    for s in sentences:
                        self.sentence_ready.emit(s)

            # FC 工具调用状态回调 — 通知 UI 显示工具调用提示
            def on_tool_call(tool_name: str, display_text: str, tool_args: dict):
                self.tool_call_status.emit(display_text)

            # 调用 LLM 的 stream_chat
            result = self.backend.llm.stream_chat(
                full_prompt,
                list(self.history),
                callback=on_chunk,
                on_tool_call=on_tool_call
            )

            # 处理结果
            reply = result.get("text", "")
            action = result.get("action")
            stream_error = result.get("_stream_error")

            # LLM 返回空文本 + 有流式错误 → 给用户明确提示
            if not reply and stream_error:
                reply = f"LLM 请求失败: {stream_error}"
            elif not reply:
                reply = "（LLM 未返回内容）"

            if action and isinstance(action, dict) and action.get("type") == "execute":
                cmd = action.get("command", "")
                exec_result = self.backend.executor.execute(cmd)
                if exec_result["success"]:
                    output = exec_result.get("stdout", "") or exec_result.get("stderr", "")
                    reply = f"命令执行完成！\n{output}"
                else:
                    reply = f"命令执行失败: {exec_result.get('error', '未知错误')}"

            if "BASH:" in reply or "READ:" in reply or "WRITE:" in reply or "EDIT:" in reply:
                tool_result = self.backend._handle_local_tool(reply)
                if tool_result:
                    reply = f"{reply}\n\n本地工具结果:\n{tool_result}"

            # 记录交互
            self.backend.record_interaction(self.text, reply)

            # 流式模式：处理缓冲区中剩余的未完结文本
            if self.streaming_tts and self._sentence_buffer.strip():
                remaining = self._sentence_buffer.strip()
                if remaining:
                    self.sentence_ready.emit(remaining)
                self._sentence_buffer = ""

            # TTS 合成（整段模式在此时合成；流式模式已在 sentence_ready 中逐句合成）
            audio_path = None
            if not self.streaming_tts:
                try:
                    audio_path = self.backend.speak(reply)
                except Exception as e:
                    print(f"[ChatPage] TTS 合成失败: {e}")

            self.finished_stream.emit({
                "text": reply,
                "audio_path": audio_path
            })

        except Exception as e:
            if not self.is_stop_requested():
                self.error.emit(str(e))


class TTSWorker(QThread):
    """TTS 合成线程 — 在后台线程调用 backend.speak()，避免阻塞 UI

    流式 TTS 和主动说话都通过此 Worker 合成音频，
    合成完成后通过 audio_ready 信号将音频路径传回主线程播放。
    """
    audio_ready = Signal(str)   # 合成完成的音频文件路径
    error = Signal(str)         # 合成失败信息

    def __init__(self, backend, text, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.text = text

    def run(self):
        try:
            audio_path = self.backend.speak(self.text)
            if audio_path and os.path.exists(audio_path):
                self.audio_ready.emit(audio_path)
        except Exception as e:
            self.error.emit(str(e))


class ASRWorker(QThread):
    """ASR 识别线程 — 录音结束后调用 backend.asr 识别"""
    finished = Signal(str)  # 识别文本
    error = Signal(str)

    def __init__(self, backend, audio_path):
        super().__init__()
        self.backend = backend
        self.audio_path = audio_path

    def run(self):
        try:
            text = self.backend.asr.recognize(self.audio_path)
            self.finished.emit(text or "")
        except Exception as e:
            self.error.emit(str(e))


class _OCRWorker(QThread):
    """OCR 识别线程 — 截图后调用 backend.vision 识别文字"""
    finished = Signal(str)  # OCR 文本
    error = Signal(str)

    def __init__(self, backend, image_path):
        super().__init__()
        self.backend = backend
        self.image_path = image_path

    def run(self):
        try:
            if hasattr(self.backend, 'vision'):
                vision = self.backend.vision
                text = vision.recognize_text(self.image_path)
                self.finished.emit(text or "")
            else:
                self.error.emit("视觉模块未初始化")
        except Exception as e:
            self.error.emit(str(e))


class ChatPage(QWidget):
    """对话页面 v2.0 — 完全重构版"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chatPage")
        self._backend = None
        self._worker = None
        self._asr_worker = None
        self._media_player = None
        self._is_streaming = False
        self._current_ai_text = ""  # 当前流式回复累积文本
        self._recording_file = None  # 录音临时文件
        self._pending_image = None  # 待发送的图片路径
        self._chat_messages = []  # 当前会话对话历史列表
        self._pending_quote = ""  # 待引用的文本
        self._animation_controller = None  # 主动画控制器
        self._audio_queue = []  # 音频播放队列（流式 TTS 逐句排队）
        self._tts_workers = []  # 活跃的 TTSWorker 列表（用于清理）
        self._init_ui()
        self._load_chat_history()
        self.setAcceptDrops(True)  # 启用拖拽

    def _init_ui(self):
        """初始化 UI — v2.0 完全重构"""
        from gugu_native.theme import get_colors
        c = get_colors()

        # 设置页面最小尺寸，防止缩放时重叠
        self.setMinimumSize(800, 500)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # === 左侧: Live2D 区域 ===
        left_panel = QVBoxLayout()
        left_panel.setSpacing(4)
        main_layout.addLayout(left_panel, stretch=2)

        # Live2D 渲染（占满整个左侧）
        self.live2d_widget = Live2DWidget()
        left_panel.addWidget(self.live2d_widget, stretch=1)

        # 主动画控制器 — 让 Live2D 角色有生命感
        self._animation_controller = AnimationController(self.live2d_widget)

        # === 中部: 会话列表侧边栏 ===
        self.session_manager = SessionManager(self)
        self.session_manager.sessionSwitched.connect(self._on_session_switched)
        self.session_manager.sessionCreated.connect(self._on_session_created)
        main_layout.addWidget(self.session_manager, stretch=0)

        # === 右侧: 对话区域 — 四层布局 ===
        right_panel = QVBoxLayout()
        right_panel.setSpacing(6)
        right_panel.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(right_panel, stretch=3)

        # ──────── 消息搜索栏（默认隐藏） ────────
        self.search_bar = MessageSearchBar(self)
        self.search_bar.searchRequested.connect(self._on_search)
        self.search_bar.searchNavigate.connect(self._on_search_navigate)
        right_panel.addWidget(self.search_bar)

        # ──────── 卡片1: 聊天显示区 (QWebEngineView) ────────
        self._chat_card = QFrame()
        self._chat_card.setObjectName("chatCard")
        self._chat_card.setMinimumHeight(200)  # 防止缩放时聊天区被压缩为0
        self._chat_card.setStyleSheet(f"""
            QFrame#chatCard {{
                background-color: {c.card_bg};
                border: 1px solid {c.card_border};
                border-radius: 16px;
            }}
        """)
        chat_card_layout = QVBoxLayout(self._chat_card)
        chat_card_layout.setContentsMargins(3, 3, 3, 3)
        chat_card_layout.setSpacing(0)

        # QWebEngineView 聊天显示（带 QTextEdit 降级）
        self.chat_display = ChatWebDisplay(self)
        self.chat_display.action_copy.connect(self._on_action_copy)
        self.chat_display.action_retry.connect(self._on_action_retry)
        self.chat_display.action_quote.connect(self._on_action_quote)
        self.chat_display.action_edit.connect(self._on_action_edit)
        chat_card_layout.addWidget(self.chat_display)
        right_panel.addWidget(self._chat_card, stretch=1)

        # ──────── 卡片2: 输入栏（多行输入框） ────────
        self._input_card = QFrame()
        self._input_card.setObjectName("inputCard")
        self._input_card.setStyleSheet(f"""
            QFrame#inputCard {{
                background-color: {c.card_bg};
                border: 1px solid {c.card_border};
                border-radius: 14px;
            }}
        """)
        input_card_layout = QVBoxLayout(self._input_card)
        input_card_layout.setContentsMargins(10, 6, 10, 6)
        input_card_layout.setSpacing(4)

        # 工具栏 — 附件按钮 + 搜索
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(4)

        self.image_btn = ToolButton(FluentIcon.PHOTO)
        self.image_btn.setFixedSize(28, 28)
        self.image_btn.setToolTip("上传图片")
        self.image_btn.clicked.connect(self._upload_image)
        toolbar_layout.addWidget(self.image_btn)

        self.ocr_btn = ToolButton(FluentIcon.CLIPPING_TOOL)
        self.ocr_btn.setFixedSize(28, 28)
        self.ocr_btn.setToolTip("截图OCR")
        self.ocr_btn.clicked.connect(self._screenshot_ocr)
        toolbar_layout.addWidget(self.ocr_btn)

        # 分隔线
        sep1 = QFrame()
        sep1.setFixedWidth(1)
        sep1.setStyleSheet(f"background-color: {c.card_border};")
        toolbar_layout.addWidget(sep1)

        self.search_btn = ToolButton(FluentIcon.SEARCH)
        self.search_btn.setFixedSize(28, 28)
        self.search_btn.setToolTip("搜索消息 (Ctrl+F)")
        self.search_btn.clicked.connect(self._toggle_search)
        toolbar_layout.addWidget(self.search_btn)

        toolbar_layout.addStretch()

        # 发送按钮 — 渐变 + 圆润
        self.send_btn = PushButton(" 发送")
        self.send_btn.setIcon(FluentIcon.SEND)
        self.send_btn.clicked.connect(self._send_message)
        self.send_btn.setStyleSheet(f"""
            PushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c.accent_gradient_start}, stop:1 {c.accent_gradient_end});
                color: white;
                border: none;
                border-radius: 10px;
                padding: 7px 18px;
                font-weight: 600;
                font-size: 13px;
            }}
            PushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c.accent}, stop:1 {c.accent_hover});
            }}
            PushButton:pressed {{
                background: {c.accent_pressed};
            }}
            PushButton:disabled {{
                background: {c.card_border};
                color: {c.text_muted};
            }}
        """)
        toolbar_layout.addWidget(self.send_btn)

        # 停止按钮 — 红色渐变
        self.stop_btn = PushButton(" 停止")
        self.stop_btn.setIcon(FluentIcon.CANCEL)
        self.stop_btn.clicked.connect(self._stop_streaming)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setVisible(False)
        self.stop_btn.setStyleSheet(f"""
            PushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c.error}, stop:1 #e03131);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 7px 18px;
                font-weight: 600;
                font-size: 13px;
            }}
            PushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e03131, stop:1 #c92a2a);
            }}
            PushButton:pressed {{
                background: #c92a2a;
            }}
        """)
        toolbar_layout.addWidget(self.stop_btn)

        # 清空按钮
        self.clear_btn = ToolButton(FluentIcon.DELETE)
        self.clear_btn.setFixedSize(28, 28)
        self.clear_btn.setToolTip("清空对话")
        self.clear_btn.clicked.connect(self._on_clear_chat)
        toolbar_layout.addWidget(self.clear_btn)

        input_card_layout.addLayout(toolbar_layout)

        # 多行输入框
        self.input_field = MultiLineInputV2(self)
        self.input_field.sendRequested.connect(self._send_message)
        input_card_layout.addWidget(self.input_field)

        right_panel.addWidget(self._input_card)

        # ──────── 卡片3: TTS 工具栏（两行布局，防缩放重叠） ────────
        self._tts_card = QFrame()
        self._tts_card.setObjectName("ttsCard")
        self._tts_card.setStyleSheet(f"""
            QFrame#ttsCard {{
                background-color: {c.sidebar_bg};
                border: 1px solid {c.card_border};
                border-radius: 12px;
            }}
        """)
        tts_card_outer = QVBoxLayout(self._tts_card)
        tts_card_outer.setContentsMargins(8, 4, 8, 4)
        tts_card_outer.setSpacing(3)

        # ── 第一行：核心控件 ──
        tts_row1 = QHBoxLayout()
        tts_row1.setSpacing(5)

        # TTS 引擎选择 — 使用原生 QComboBox（支持 itemData/setSizeAdjustPolicy）
        self.tts_combo = QComboBox()
        self.tts_combo.addItems(["Edge TTS", "GPT-SoVITS", "ChatTTS", "CosyVoice"])
        self.tts_combo.setCurrentIndex(0)
        self.tts_combo.setMinimumWidth(100)
        self.tts_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.tts_combo.currentIndexChanged.connect(self._on_tts_engine_changed_chat)
        self._style_qcombobox(self.tts_combo, c)
        tts_row1.addWidget(self.tts_combo)

        # 音色选择 — 使用原生 QComboBox（支持 itemData）
        self.voice_combo = QComboBox()
        self.voice_combo.setMinimumWidth(80)
        self.voice_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.voice_combo.currentIndexChanged.connect(self._on_voice_changed_chat)
        self._style_qcombobox(self.voice_combo, c)
        tts_row1.addWidget(self.voice_combo, stretch=1)

        # 竖分隔线
        tts_sep1 = QFrame()
        tts_sep1.setFixedWidth(1)
        tts_sep1.setStyleSheet(f"background-color: {c.card_border};")
        tts_row1.addWidget(tts_sep1)

        # 录音按钮
        self.record_btn = TogglePushButton("录音")
        self.record_btn.setIcon(FluentIcon.MICROPHONE)
        self.record_btn.toggled.connect(self._toggle_recording)
        self.record_btn.setStyleSheet(f"""
            TogglePushButton {{
                border-radius: 12px;
                padding: 3px 10px;
                border: 1px solid {c.card_border};
                font-size: 12px;
            }}
            TogglePushButton:checked {{
                background-color: {c.error};
                color: white;
                border: none;
            }}
        """)
        tts_row1.addWidget(self.record_btn)

        # 实时语音按钮
        self.realtime_btn = TogglePushButton("实时语音")
        self.realtime_btn.setIcon(FluentIcon.MICROPHONE)
        self.realtime_btn.toggled.connect(self._toggle_realtime_voice)
        self.realtime_btn.setStyleSheet(f"""
            TogglePushButton {{
                border-radius: 12px;
                padding: 3px 10px;
                border: 1px solid {c.card_border};
                font-size: 12px;
            }}
            TogglePushButton:checked {{
                background-color: {c.success};
                color: white;
                border: none;
            }}
        """)
        tts_row1.addWidget(self.realtime_btn)

        # TTS 流式/整段切换按钮
        self.tts_mode_btn = TogglePushButton("流式")
        self.tts_mode_btn.setToolTip("流式分句合成 / 整段合成切换")
        self.tts_mode_btn.setChecked(True)  # 默认流式
        self.tts_mode_btn.setStyleSheet(f"""
            TogglePushButton {{
                border-radius: 12px;
                padding: 3px 10px;
                border: 1px solid {c.card_border};
                font-size: 12px;
            }}
            TogglePushButton:checked {{
                background-color: {c.accent};
                color: white;
                border: none;
            }}
        """)
        self.tts_mode_btn.toggled.connect(self._on_tts_mode_toggled)
        tts_row1.addWidget(self.tts_mode_btn)

        # 桌面宠物按钮
        self.pet_btn = ToolButton(FluentIcon.HEART)
        self.pet_btn.setFixedSize(28, 28)
        self.pet_btn.setToolTip("桌面宠物")
        self.pet_btn.clicked.connect(self._toggle_pet)
        tts_row1.addWidget(self.pet_btn)

        tts_row1.addStretch()
        tts_card_outer.addLayout(tts_row1)

        # ── 第二行：辅助控件（速度/音量） ──
        tts_row2 = QHBoxLayout()
        tts_row2.setSpacing(5)

        # 速度滑块
        speed_icon = CaptionLabel("速度")
        speed_icon.setFixedWidth(28)
        tts_row2.addWidget(speed_icon)

        self.speed_slider = Slider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        self.speed_slider.setMinimumWidth(50)
        self.speed_slider.setToolTip("语速 50-200%")
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        tts_row2.addWidget(self.speed_slider, stretch=1)

        # 音量滑块
        vol_icon = CaptionLabel("音量")
        vol_icon.setFixedWidth(28)
        tts_row2.addWidget(vol_icon)

        self.volume_slider = Slider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 150)
        self.volume_slider.setValue(80)
        self.volume_slider.setMinimumWidth(50)
        self.volume_slider.setToolTip("音量 0-150%")
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        tts_row2.addWidget(self.volume_slider, stretch=1)

        right_panel.addWidget(self._tts_card)

        # === 音频播放器 ===
        self._media_player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._media_player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(0.8)

        # === 延迟加载模型 ===
        QTimer.singleShot(500, self._load_default_model)

    def _load_default_model(self):
        """加载默认 Live2D 模型"""
        model_path = os.path.join(
            PROJECT_DIR, "app", "web", "static", "assets", "model",
            "hiyori", "Hiyori.model3.json"
        )
        if os.path.exists(model_path):
            self.live2d_widget.load_model(model_path)
            # 模型加载后启动主动画控制器（idle 动画 + 问候动画）
            if self._animation_controller:
                self._animation_controller.start()
        else:
            self.chat_display.append_system_msg(f"默认模型不存在: {model_path}")

    @property
    def backend(self):
        """获取后端实例（延迟初始化）"""
        if self._backend is None:
            main_window = self.window()
            if hasattr(main_window, 'backend'):
                self._backend = main_window.backend
        return self._backend

    def on_backend_ready(self):
        """后端就绪回调 — 加载 TTS 配置和对话历史"""
        if not self.backend:
            return

        # 加载 TTS 配置
        try:
            if os.path.exists(_TTS_PREFS_FILE):
                with open(_TTS_PREFS_FILE, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
                engine = prefs.get("engine", "Edge TTS")
                voice_id = prefs.get("voice", "")
            else:
                tts_config = self.backend.config.config.get("tts", {})
                provider = tts_config.get("provider", "edge")
                engine_map = {"edge": "Edge TTS", "gptsovits": "GPT-SoVITS"}
                engine = engine_map.get(provider, "Edge TTS")
                voice_id = tts_config.get(provider, {}).get("voice", "")

            self.tts_combo.blockSignals(True)
            self.voice_combo.blockSignals(True)

            idx = self.tts_combo.findText(engine)
            if idx >= 0:
                self.tts_combo.setCurrentIndex(idx)

            if engine == "GPT-SoVITS":
                self._populate_gptsovits_voices_chat()
            else:
                self._populate_edge_voices_chat()

            if voice_id:
                for i in range(self.voice_combo.count()):
                    if str(self.voice_combo.itemData(i) or "") == voice_id:
                        self.voice_combo.setCurrentIndex(i)
                        break

            self.tts_combo.blockSignals(False)
            self.voice_combo.blockSignals(False)
        except Exception as e:
            print(f"[ChatPage] 加载 TTS 配置失败: {e}")
            self.tts_combo.blockSignals(False)
            self.voice_combo.blockSignals(False)

        # 加载对话历史
        # v1.9.89: 避免与 _load_chat_history() 重复加载
        # 如果 _load_chat_history 已经加载了历史，不再重复加载
        # backend.history 用于 LLM 上下文，不用于 UI 显示
        # （native_chat_history.json 是 UI 显示的数据源）
        try:
            if not self._chat_messages and hasattr(self.backend, 'history') and len(self.backend.history) > 0:
                # 仅在 _load_chat_history 没有数据时，才从 backend.history 加载
                for msg in self.backend.history[-20:]:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    time_str = msg.get('time', '')
                    if role == 'user':
                        self.chat_display.append_user_msg(content, timestamp=time_str)
                    elif role == 'assistant':
                        self.chat_display.append_ai_msg(content, timestamp=time_str)
                    self._chat_messages.append({
                        "role": role,
                        "content": content,
                        "time": time_str
                    })
                self._save_chat_history()
        except Exception:
            pass

    # ========== 发送/流式对话 ==========

    def _send_message(self, text: str = ""):
        """发送消息"""
        if self._is_streaming:
            return

        if isinstance(text, bool):
            # 防止信号传递 bool 参数
            text = ""

        text = text or self.input_field.text()

        # 处理待发送的图片（OCR/视觉理解）
        if self._pending_image:
            text = self._process_pending_image(text)
            if not text:
                return

        if not text:
            return
        if not self.backend:
            self.chat_display.append_system_msg("后端未初始化，请先在设置页面配置 API Key")
            return

        # 获取引用文本
        quote = self.input_field.quote_text
        if quote:
            self.chat_display.append_user_msg(text, quote=quote)
            # 在发送给 LLM 的文本中加入引用
            if quote:
                text = f"[引用: {quote}]\n{text}"
            self.input_field.clear_quote()
        else:
            self.chat_display.append_user_msg(text)
        # v1.9.89: 记录用户消息到历史
        self._record_message("user", text)

        self.input_field.clear()
        self._set_streaming_state(True)
        self._current_ai_text = ""

        # 添加正在思考占位
        self.chat_display.start_streaming()

        # 获取对话历史
        history = list(self.backend.history) if hasattr(self.backend, 'history') else []

        # 启动流式对话线程
        streaming_tts = self.tts_mode_btn.isChecked()
        self._worker = StreamChatWorker(self.backend, text, history, streaming_tts=streaming_tts)
        self._worker.chunk_received.connect(self._on_chunk)
        self._worker.sentence_ready.connect(self._on_sentence_ready)
        self._worker.finished_stream.connect(self._on_stream_finished)
        self._worker.error.connect(self._on_error)
        self._worker.tool_call_status.connect(self._on_tool_call_status)
        self._worker.start()

    def _stop_streaming(self):
        """停止流式对话"""
        if self._worker and self._is_streaming:
            self._worker.stop_stream()
            # 终结当前流式消息占位 — 避免遗留未关闭的流式气泡
            if self._current_ai_text:
                self.chat_display.finish_streaming(self._current_ai_text)
                self._record_message("assistant", self._current_ai_text)
            else:
                self.chat_display.finish_streaming("(已停止)")
            self.chat_display.append_system_msg("已停止生成")
            self._current_ai_text = ""
            self._set_streaming_state(False)
            # 清空音频队列和等待中的 TTS Worker
            self._audio_queue.clear()
            for w in self._tts_workers:
                if w.isRunning():
                    w.quit()
                    w.wait(500)
            self._tts_workers.clear()

    def _set_streaming_state(self, streaming: bool):
        """切换发送/停止按钮状态"""
        self._is_streaming = streaming
        self.send_btn.setEnabled(not streaming)
        self.send_btn.setVisible(not streaming)
        self.stop_btn.setEnabled(streaming)
        self.stop_btn.setVisible(streaming)
        self.input_field.setEnabled(not streaming)

    @Slot(str)
    def _on_tool_call_status(self, display_text: str):
        """FC 工具调用状态提示 — 在聊天界面显示系统消息"""
        self.chat_display.append_system_msg(display_text)

    @Slot(str)
    def _on_chunk(self, chunk_text: str):
        """收到流式文本片段"""
        self._current_ai_text += chunk_text
        self.chat_display.update_streaming(self._current_ai_text)

    @Slot(str)
    def _on_sentence_ready(self, sentence: str):
        """流式 TTS：检测到完整句子，在后台线程合成音频"""
        if not sentence or not self.backend:
            return
        worker = TTSWorker(self.backend, sentence, parent=self)
        worker.audio_ready.connect(self._on_tts_audio_ready)
        worker.error.connect(lambda e: print(f"[ChatPage] 流式 TTS 句子合成失败: {e}"))
        worker.finished.connect(lambda: self._cleanup_tts_worker(worker))
        self._tts_workers.append(worker)
        worker.start()

    @Slot(dict)
    def _on_stream_finished(self, result: dict):
        """流式对话完成"""
        # 如果已经被 _stop_streaming 提前终结，跳过重复处理
        if not self._is_streaming:
            return

        reply_text = result.get("text", "")

        if reply_text and reply_text != self._current_ai_text:
            self._current_ai_text = reply_text

        # 完成流式
        self.chat_display.finish_streaming(self._current_ai_text or "(无回复)")

        # FC UI 指令处理（如 change_expression → 驱动 Live2D 表情）
        ui_actions = result.get("_ui_actions", [])
        for action in ui_actions:
            if action.get("type") == "change_expression" and self._animation_controller:
                emotion = action.get("emotion", "neutral")
                self._animation_controller.trigger_emotion(emotion, lock_duration=5.0)
                print(f"[ChatPage] FC 表情指令: {emotion}")

        # 自动表情检测 → 主动画控制器驱动（仅在无 FC 表情指令时触发，避免覆盖）
        if reply_text and not any(a.get("type") == "change_expression" for a in ui_actions):
            if self._animation_controller:
                self._animation_controller.trigger_emotion_from_text(reply_text)
            else:
                self._auto_detect_expression(reply_text)

        # 播放 TTS 音频（整段模式才在这里播放；流式模式已逐句播放）
        audio_path = result.get("audio_path")
        is_streaming_tts = self._worker and getattr(self._worker, 'streaming_tts', False)
        if audio_path and os.path.exists(audio_path) and not is_streaming_tts:
            self._play_audio(audio_path)

        # 记录消息
        self._record_message("assistant", self._current_ai_text or reply_text)

        self._current_ai_text = ""
        self._set_streaming_state(False)
        self._save_chat_history()

    # ========== 自动表情检测 ==========

    _EXPRESSION_KEYWORDS = {
        "happy": ['开心', '高兴', '快乐', '好开心', '哈哈', '笑', '太棒', '太好了', '嘻', '棒', '赞', '爱你', '喜欢', '么么哒', '可爱', '萌'],
        "smile": ['微笑', '嗯', '好的', '可以', '行', '没问题', '了解', '知道', '明白', '懂', '是', '对'],
        "shine": ['哇', '啊', '惊讶', '惊喜', '厉害', '太厉害', '真的吗', '真的假的', '天哪', '我的天', '哇塞', '哇哦', '好厉害', '惊了'],
        "sad": ['难过', '伤心', '哭', '悲伤', '遗憾', '可惜', '唉', '郁闷', '烦', '讨厌'],
        "angry": ['生气', '愤怒', '哼', '气死', '可恶', '滚', '烦死了'],
        "surprised": ['震惊', '什么', '怎么', '为什么', '啥', '啥情况'],
    }

    _EXPRESSION_MAP = {
        "happy": "f02",
        "smile": "f03",
        "shine": "f04",
        "neutral": "f01",
        "sad": "f03",
        "angry": "f03",
        "surprised": "f04",
    }

    _auto_expression_enabled = True

    def _auto_detect_expression(self, text: str):
        """根据文本关键词自动触发表情"""
        if not self._auto_expression_enabled or not text:
            return

        text_lower = text.lower()
        max_score = 0
        detected_type = None

        for exp_type, keywords in self._EXPRESSION_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > max_score:
                max_score = score
                detected_type = exp_type

        if max_score >= 1 and detected_type:
            exp_name = self._EXPRESSION_MAP.get(detected_type, "f01")
            if hasattr(self, 'live2d_widget') and self.live2d_widget:
                self.live2d_widget.set_expression(exp_name)

    @Slot(str)
    def _on_error(self, error_msg: str):
        """处理错误"""
        self.chat_display.append_system_msg(f"错误: {error_msg}")
        self._current_ai_text = ""
        self._set_streaming_state(False)

    # ========== 消息操作回调 ==========

    def _on_action_copy(self, text: str):
        """复制消息"""
        QApplication.clipboard().setText(text)

    def _on_action_retry(self, msg_id: str):
        """重试（重新生成最后一条 AI 回复）"""
        if self._is_streaming:
            return
        # 找到最后一条用户消息
        last_user_msg = None
        for msg in reversed(self._chat_messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break
        if last_user_msg and self.backend:
            # 删除最后一条 AI 消息
            self.chat_display.append_system_msg("重新生成...")
            self.input_field.setText(last_user_msg)
            self._send_message()

    def _on_action_quote(self, text: str):
        """引用消息"""
        self._pending_quote = text
        self.input_field.set_quote(text)
        self.input_field.setFocus()

    def _on_action_edit(self, msg_id: str, text: str):
        """编辑重发"""
        self.input_field.setText(text)
        self.input_field.setFocus()

    # ========== 搜索 ==========

    def _toggle_search(self):
        """切换搜索栏"""
        self.search_bar.show_search()

    def _on_search(self, query: str):
        """搜索消息 — 当前会话高亮 + 跨会话计数"""
        count = self.chat_display.search(query)

        # 跨会话搜索：统计其他会话中的匹配数
        cross_count = 0
        try:
            sessions_dir = os.path.join(PROJECT_DIR, "app", "state", "sessions")
            if os.path.isdir(sessions_dir):
                current_id = self.session_manager.current_session_id()
                for fname in os.listdir(sessions_dir):
                    if not fname.endswith(".json"):
                        continue
                    sid = fname[:-5]  # 去掉 .json
                    if sid == current_id:
                        continue
                    try:
                        with open(os.path.join(sessions_dir, fname), "r", encoding="utf-8") as f:
                            data = json.load(f)
                        for msg in data.get("messages", []):
                            if query.lower() in msg.get("content", "").lower():
                                cross_count += 1
                    except Exception:
                        continue
        except Exception:
            pass

        if cross_count > 0:
            self.search_bar.set_result_count(count, cross_session=cross_count)
        else:
            self.search_bar.set_result_count(count)

    def _on_search_navigate(self, direction: int):
        """导航搜索结果"""
        # 简单实现：重新搜索并高亮
        pass

    # ========== TTS/录音 ==========

    def _on_tts_audio_ready(self, audio_path: str):
        """TTS 合成完成回调 — 入队或立即播放"""
        if not audio_path or not os.path.exists(audio_path):
            return
        # 如果播放器空闲，立即播放；否则入队等待
        if self._media_player and self._media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._audio_queue.append(audio_path)
        else:
            self._play_audio(audio_path)

    def _cleanup_tts_worker(self, worker):
        """清理已完成的 TTSWorker"""
        try:
            self._tts_workers.remove(worker)
        except ValueError:
            pass

    def _play_audio(self, file_path: str):
        """播放音频（含 Live2D 口型同步）"""
        try:
            self._media_player.setSource(QUrl.fromLocalFile(file_path))
            self._media_player.play()
            # 启动口型同步动画
            self._start_lipsync()
        except Exception as e:
            print(f"[ChatPage] 音频播放失败: {e}")

    def _start_lipsync(self):
        """TTS 播放时驱动 Live2D 口型动画"""
        if not self._animation_controller:
            return

        # 先停止旧的口型同步定时器（防止快速连续播放时旧 timer 泄漏）
        if hasattr(self, '_lipsync_timer') and self._lipsync_timer:
            self._lipsync_timer.stop()
            self._lipsync_timer = None

        # 使用 QMediaPlayer 的播放状态来控制口型同步
        # 播放期间持续设置嘴巴开合度
        self._lipsync_timer = QTimer(self)
        self._lipsync_timer.timeout.connect(self._lipsync_tick)
        self._lipsync_timer.start(50)  # 每 50ms 更新一次

        # 监听播放结束 — 先断开旧连接再重新连接，防止 N 次播放触发 N 次回调
        try:
            self._media_player.playbackStateChanged.disconnect(self._on_playback_state_changed)
        except (RuntimeError, TypeError):
            pass  # 未连接时 disconnect 会抛异常，忽略即可
        self._media_player.playbackStateChanged.connect(self._on_playback_state_changed)

    def _lipsync_tick(self):
        """口型同步定时更新 — 模拟嘴巴开合"""
        if not self._animation_controller:
            return
        if not self._media_player or self._media_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            return
        # 简易口型同步：用随机值模拟嘴巴开合
        # TODO: 后续可用音频振幅分析驱动更精确的口型
        import random
        mouth_open = random.uniform(0.3, 1.0)
        self._animation_controller.set_mouth_open(mouth_open)

    def _on_playback_state_changed(self, state):
        """音频播放状态变化 — 结束时停止口型同步并播放队列中的下一首"""
        if state != QMediaPlayer.PlaybackState.PlayingState:
            # 播放结束，关闭嘴巴
            if self._animation_controller:
                self._animation_controller.set_mouth_open(0.0)
            # 停止口型同步定时器
            if hasattr(self, '_lipsync_timer') and self._lipsync_timer:
                self._lipsync_timer.stop()
                self._lipsync_timer = None
            # 从队列中取下一首播放
            if self._audio_queue:
                next_audio = self._audio_queue.pop(0)
                if os.path.exists(next_audio):
                    self._play_audio(next_audio)

    def _toggle_recording(self, checked: bool):
        """切换录音状态"""
        if checked:
            self.record_btn.setText("停止")
            self.chat_display.append_system_msg("开始录音...")
            try:
                import sounddevice as sd
                import numpy as np

                self._sd = sd
                self._np = np
                self._recording_data = []
                self._sample_rate = 16000

                def audio_callback(indata, frames, time_info, status):
                    self._recording_data.append(indata.copy())

                self._recording_stream = sd.InputStream(
                    samplerate=self._sample_rate,
                    channels=1,
                    dtype='float32',
                    callback=audio_callback
                )
                self._recording_stream.start()
            except ImportError:
                self.chat_display.append_system_msg("录音需要 sounddevice 库，请安装: pip install sounddevice")
                self.record_btn.setChecked(False)
                self.record_btn.setText("录音")
            except Exception as e:
                self.chat_display.append_system_msg(f"录音启动失败: {e}")
                self.record_btn.setChecked(False)
                self.record_btn.setText("录音")
        else:
            self.record_btn.setText("录音")
            try:
                if hasattr(self, '_recording_stream') and self._recording_stream:
                    self._recording_stream.stop()
                    self._recording_stream.close()
                    self._recording_stream = None

                    if self._recording_data:
                        audio = self._np.concatenate(self._recording_data, axis=0)
                        tmp = tempfile.NamedTemporaryFile(
                            suffix=".wav", delete=False, dir=PROJECT_DIR
                        )
                        tmp_path = tmp.name
                        tmp.close()

                        import wave
                        with wave.open(tmp_path, 'wb') as wf:
                            wf.setnchannels(1)
                            wf.setsampwidth(2)
                            wf.setframerate(self._sample_rate)
                            audio_int16 = (audio * 32767).astype(self._np.int16)
                            wf.writeframes(audio_int16.tobytes())

                        self._recording_file = tmp_path
                        self.chat_display.append_system_msg("录音结束，正在识别...")

                        if self.backend:
                            self._asr_worker = ASRWorker(self.backend, tmp_path)
                            self._asr_worker.finished.connect(self._on_asr_result)
                            self._asr_worker.error.connect(self._on_asr_error)
                            self._asr_worker.start()
                        else:
                            self.chat_display.append_system_msg("后端未初始化，无法识别语音")

                    self._recording_data = []
            except Exception as e:
                self.chat_display.append_system_msg(f"录音停止失败: {e}")

    @Slot(str)
    def _on_asr_result(self, text: str):
        """ASR 识别完成"""
        if self._recording_file:
            try:
                os.unlink(self._recording_file)
            except Exception:
                pass
            self._recording_file = None

        if text:
            self.input_field.setText(text)
            self._send_message()
        else:
            self.chat_display.append_system_msg("未能识别语音内容")

    @Slot(str)
    def _on_asr_error(self, error_msg: str):
        """ASR 识别失败"""
        if self._recording_file:
            try:
                os.unlink(self._recording_file)
            except Exception:
                pass
            self._recording_file = None
        self.chat_display.append_system_msg(f"语音识别失败: {error_msg}")

    # ========== 实时语音 ==========

    def _toggle_realtime_voice(self, checked: bool):
        """切换实时语音模式"""
        main_window = self.window()
        if not hasattr(main_window, 'voice_manager'):
            self.chat_display.append_system_msg("语音管理器未初始化")
            self.realtime_btn.setChecked(False)
            return

        voice_mgr = main_window.voice_manager

        if checked and (not hasattr(main_window, 'backend') or main_window.backend is None):
            self.chat_display.append_system_msg("AI 后端尚未就绪，请稍后再试")
            self.realtime_btn.setChecked(False)
            return

        if checked:
            voice_mgr.speech_recognized.connect(self._on_realtime_speech)
            voice_mgr.start_listening()
            if not voice_mgr.is_listening:
                self.realtime_btn.setChecked(False)
                voice_mgr.speech_recognized.disconnect(self._on_realtime_speech)
                return
            self.realtime_btn.setText("监听中")
        else:
            voice_mgr.stop_listening()
            self.realtime_btn.setText("实时语音")
            try:
                voice_mgr.speech_recognized.disconnect(self._on_realtime_speech)
            except Exception:
                pass

    def _on_realtime_speech(self, text: str):
        """实时语音识别完成"""
        if text:
            # 如果正在流式回复，先停止并终结当前消息
            if self._is_streaming:
                self._stop_streaming()
            # 停止当前 TTS 播放
            if self._media_player and self._media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self._media_player.stop()

            self.input_field.setText(text)
            # 延迟 50ms 发送，确保 _stop_streaming 的状态清理完全生效
            QTimer.singleShot(50, self._send_message)

    # ========== 桌面宠物 ==========

    def _toggle_pet(self):
        """切换桌面宠物模式"""
        main_window = self.window()
        if hasattr(main_window, '_toggle_desktop_pet'):
            main_window._toggle_desktop_pet()

    def _on_clear_chat(self):
        """清空对话（带确认）"""
        from qfluentwidgets import MessageBox
        msg = MessageBox("清空对话", "确定要清空所有对话记录吗？此操作不可撤销。", self)
        if msg.exec():
            self.clear_chat()

    # ========== 拖拽发送 ==========

    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入"""
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """拖拽释放 — 发送文件"""
        mime = event.mimeData()
        if mime.hasUrls():
            for url in mime.urls():
                file_path = url.toLocalFile()
                if file_path:
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in ('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif'):
                        self._pending_image = file_path
                        self.chat_display.append_image(file_path)
                        self.input_field.setFocus()
                        self.input_field.setPlaceholderText("输入关于图片的问题，或直接按回车进行OCR识别...")
                    elif ext in ('.txt', '.md', '.py', '.js', '.json', '.csv'):
                        # 文本文件：读取内容发送
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read(2000)  # 限制 2000 字符
                            self.input_field.setText(f"[文件: {os.path.basename(file_path)}]\n{content}")
                            self.input_field.setFocus()
                        except Exception:
                            self.chat_display.append_system_msg(f"无法读取文件: {file_path}")
                    else:
                        self.chat_display.append_system_msg(f"不支持的文件类型: {ext}")

    # ========== 图片/视觉/OCR ==========

    def _upload_image(self):
        """上传图片进行视觉理解"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.webp *.gif);;所有文件 (*)"
        )
        if not file_path:
            return
        self._pending_image = file_path
        self.chat_display.append_image(file_path)
        self.input_field.setFocus()
        self.input_field.setPlaceholderText("输入关于图片的问题，或直接按回车进行OCR识别...")

    def _screenshot_ocr(self):
        """截图OCR"""
        if not self.backend:
            self.chat_display.append_system_msg("后端未初始化，无法使用OCR")
            return
        try:
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if not screen:
                self.chat_display.append_system_msg("无法获取屏幕")
                return
            screenshot = screen.grabWindow(0)
            tmp_path = os.path.join(tempfile.gettempdir(), f"gugu_screenshot_{int(time.time())}.png")
            screenshot.save(tmp_path, "PNG")
            self.chat_display.append_system_msg("正在识别屏幕文字...")
            self._ocr_worker = _OCRWorker(self.backend, tmp_path)
            self._ocr_worker.finished.connect(self._on_ocr_result)
            self._ocr_worker.error.connect(self._on_ocr_error)
            self._ocr_worker.start()
        except Exception as e:
            self.chat_display.append_system_msg(f"截图OCR失败: {e}")

    @Slot(str)
    def _on_ocr_result(self, text: str):
        """OCR 识别完成"""
        if text:
            self.chat_display.append_system_msg(f"OCR 识别结果:\n{text}")
            self.input_field.setText(text)
        else:
            self.chat_display.append_system_msg("OCR 未识别到文字")

    @Slot(str)
    def _on_ocr_error(self, error: str):
        """OCR 识别失败"""
        self.chat_display.append_system_msg(f"OCR 识别失败: {error}")

    def _process_pending_image(self, user_text: str) -> str:
        """处理待发送的图片"""
        if not self._pending_image:
            return user_text

        image_path = self._pending_image
        self._pending_image = None
        self.input_field.setPlaceholderText("输入消息，按 Enter 发送...")

        if not self.backend:
            return user_text

        try:
            if not user_text.strip():
                if hasattr(self.backend, 'vision'):
                    vision = self.backend.vision
                    ocr_result = vision.recognize_text(image_path)
                    if ocr_result:
                        self.chat_display.append_system_msg(f"OCR 识别结果:\n{ocr_result}")
                        return f"请根据以下OCR识别结果回答：\n{ocr_result}"
                return user_text

            if hasattr(self.backend, 'vision'):
                vision = self.backend.vision
                description = vision.understand(image_path, user_text)
                if description:
                    return f"[用户上传了一张图片，AI描述: {description}]\n用户问题: {user_text}"
        except Exception as e:
            self.chat_display.append_system_msg(f"视觉理解失败: {e}")

        return user_text

    # ========== 多会话管理 ==========

    def _on_session_switched(self, session_id: str):
        """切换会话"""
        # 保存当前会话
        self._save_current_session()

        # 加载新会话
        session = self.session_manager.get_session(session_id)
        if session:
            self.chat_display.clear()
            self._chat_messages = list(session.messages)
            # 重新渲染历史消息（使用保存的时间戳）
            for msg in session.messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                time_str = msg.get("time", "")
                if role == "user":
                    self.chat_display.append_user_msg(content, timestamp=time_str)
                elif role == "assistant":
                    self.chat_display.append_ai_msg(content, timestamp=time_str)

    def _on_session_created(self, session_id: str):
        """创建新会话"""
        self.chat_display.clear()
        self._chat_messages = []

    def _save_current_session(self):
        """保存当前会话"""
        session_id = self.session_manager.current_session_id()
        if session_id:
            self.session_manager.update_session_messages(session_id, self._chat_messages)

    # ========== 消息记录 ==========

    def _record_message(self, role: str, content: str):
        """记录一条消息到历史列表"""
        if not hasattr(self, '_chat_messages'):
            self._chat_messages = []
        self._chat_messages.append({
            "role": role,
            "content": content,
            "time": datetime.now().isoformat()
        })
        # 更新会话管理器
        self._save_current_session()

    # ========== TTS 控制 ==========

    def _populate_edge_voices_chat(self):
        """填充 Edge TTS 音色列表"""
        from gugu_native.pages.settings_page import EDGE_VOICES
        self.voice_combo.clear()
        for voice_id, label in EDGE_VOICES:
            self.voice_combo.addItem(f"{label}", userData=voice_id)

    def _populate_gptsovits_voices_chat(self):
        """填充 GPT-SoVITS 音色列表"""
        self.voice_combo.clear()
        if not self.backend:
            self.voice_combo.addItem("默认音色", userData="default")
            return
        try:
            tts = self.backend.tts
            if tts and hasattr(tts, 'get_voices'):
                voices = tts.get_voices()
                if voices:
                    for v in voices:
                        if isinstance(v, dict):
                            value = str(v.get('value', v.get('name', '')))
                            label = str(v.get('label', value))
                            self.voice_combo.addItem(label, userData=value)
                        else:
                            self.voice_combo.addItem(str(v), userData=str(v))
                    return
        except Exception as e:
            print(f"[ChatPage] 获取 GPT-SoVITS 音色失败: {e}")
        self.voice_combo.addItem("默认音色", userData="default")

    def _populate_chattts_voices_chat(self):
        """填充 ChatTTS 音色列表"""
        self.voice_combo.clear()
        try:
            from app.tts.chattts import ChatTTSEngine
            engine = ChatTTSEngine({})
            voices = engine.get_voices()
            for v in voices:
                if isinstance(v, dict):
                    self.voice_combo.addItem(v.get("name", ""), userData=v.get("id", ""))
                else:
                    self.voice_combo.addItem(str(v), userData=str(v))
        except Exception:
            self.voice_combo.addItem("随机音色", userData="random")

    def _populate_cosyvoice_voices_chat(self):
        """填充 CosyVoice 音色列表"""
        self.voice_combo.clear()
        try:
            from app.tts.cosyvoice import CosyVoiceEngine
            config = self.backend.config.config.get("tts", {}).get("cosyvoice", {})
            engine = CosyVoiceEngine(config)
            voices = engine.get_voices()
            for v in voices:
                if isinstance(v, dict):
                    self.voice_combo.addItem(v.get("name", ""), userData=v.get("id", ""))
                else:
                    self.voice_combo.addItem(str(v), userData=str(v))
        except Exception:
            self.voice_combo.addItem("中文女 (默认)", userData="中文女")

    def _on_tts_engine_changed_chat(self, index: int):
        """Chat 页 TTS 引擎切换"""
        engine = self.tts_combo.currentText()
        if engine == "Edge TTS":
            self._populate_edge_voices_chat()
        elif engine == "GPT-SoVITS":
            self._populate_gptsovits_voices_chat()
        elif engine == "ChatTTS":
            self._populate_chattts_voices_chat()
        elif engine == "CosyVoice":
            self._populate_cosyvoice_voices_chat()
        self._apply_tts_to_backend()

    def _on_voice_changed_chat(self, index: int):
        """Chat 页音色切换"""
        self._apply_tts_to_backend()

    def _on_speed_changed(self, value: int):
        """TTS 速度滑块变更"""
        speed = value / 100.0
        if self.backend:
            tts_section = self.backend.config.config.setdefault("tts", {})
            provider = tts_section.get("provider", "edge")
            sub = tts_section.setdefault(provider, {})
            sub["speed"] = speed
            if hasattr(self.backend, 'tts') and self.backend.tts:
                if hasattr(self.backend.tts, 'set_speed'):
                    self.backend.tts.set_speed(speed)

    def _on_volume_changed(self, value: int):
        """TTS 音量滑块变更"""
        volume = value / 100.0
        self._audio_output.setVolume(min(volume, 1.0))

    def _on_tts_mode_toggled(self, checked: bool):
        """TTS 流式/整段模式切换"""
        if checked:
            self.tts_mode_btn.setText("流式")
        else:
            self.tts_mode_btn.setText("整段")

    def _get_voice_id_chat(self) -> str:
        """获取当前选中音色 ID"""
        idx = self.voice_combo.currentIndex()
        if idx >= 0:
            user_data = self.voice_combo.itemData(idx)
            if user_data:
                return str(user_data)
        return self.voice_combo.currentText()

    def _apply_tts_to_backend(self):
        """将当前 TTS 选择应用到后端"""
        if not self.backend:
            return
        engine = self.tts_combo.currentText()
        voice_id = self._get_voice_id_chat()
        provider_map = {"Edge TTS": "edge", "GPT-SoVITS": "gptsovits", "ChatTTS": "chattts", "CosyVoice": "cosyvoice"}
        provider = provider_map.get(engine, "edge")

        tts_section = self.backend.config.config.setdefault("tts", {})
        tts_section["provider"] = provider
        if voice_id:
            sub = tts_section.setdefault(provider, {})
            sub["voice"] = voice_id
            if provider == "gptsovits":
                sub["project"] = voice_id

        # 重建 TTS 引擎
        if hasattr(self.backend, '_lazy_modules') and 'tts' in self.backend._lazy_modules:
            old_tts = self.backend._lazy_modules.pop('tts', None)
            if old_tts and hasattr(old_tts, 'cleanup'):
                try:
                    old_tts.cleanup()
                except Exception:
                    pass
            try:
                _ = self.backend.tts
                if provider == "gptsovits" and hasattr(self.backend.tts, 'set_project'):
                    self.backend.tts.set_project(voice_id)
            except Exception as e:
                print(f"[ChatPage] TTS 引擎重建失败: {e}")

        # 持久化
        try:
            tts_prefs = {"engine": engine, "provider": provider, "voice": voice_id}
            cache_dir = os.path.join(PROJECT_DIR, "app", "cache")
            os.makedirs(cache_dir, exist_ok=True)
            with open(_TTS_PREFS_FILE, "w", encoding="utf-8") as f:
                json.dump(tts_prefs, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def sync_tts_from_settings(self, engine: str, voice_id: str):
        """从设置页同步 TTS 配置到 Chat 页"""
        self.tts_combo.blockSignals(True)
        self.voice_combo.blockSignals(True)

        idx = self.tts_combo.findText(engine)
        if idx >= 0:
            self.tts_combo.setCurrentIndex(idx)

        if engine == "Edge TTS":
            self._populate_edge_voices_chat()
        elif engine == "GPT-SoVITS":
            self._populate_gptsovits_voices_chat()

        for i in range(self.voice_combo.count()):
            if str(self.voice_combo.itemData(i) or "") == voice_id:
                self.voice_combo.setCurrentIndex(i)
                break

        self.tts_combo.blockSignals(False)
        self.voice_combo.blockSignals(False)

    # ========== 对话历史持久化 ==========

    def _get_history_path(self):
        """获取对话历史文件路径"""
        state_dir = os.path.join(PROJECT_DIR, "app", "state")
        os.makedirs(state_dir, exist_ok=True)
        return os.path.join(state_dir, "native_chat_history.json")

    def _save_chat_history(self):
        """保存对话历史到 JSON"""
        try:
            messages = getattr(self, '_chat_messages', [])
            if not messages:
                return
            messages = messages[-200:]
            # v1.9.89: 为缺少 time 的旧消息补充时间戳
            for m in messages:
                if not m.get('time'):
                    from datetime import datetime as _dt
                    m['time'] = _dt.now().isoformat()
            with open(self._get_history_path(), "w", encoding="utf-8") as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_chat_history(self):
        """加载对话历史"""
        try:
            path = self._get_history_path()
            if not os.path.exists(path):
                return
            with open(path, "r", encoding="utf-8") as f:
                messages = json.load(f)
            for msg in messages[-100:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                time_str = msg.get("time", "")
                if role == "user":
                    self.chat_display.append_user_msg(content, timestamp=time_str)
                elif role == "assistant":
                    self.chat_display.append_ai_msg(content, timestamp=time_str)
                self._chat_messages.append(msg)
        except Exception:
            pass

    def clear_chat(self):
        """清空对话"""
        self.chat_display.clear()
        self._chat_messages = []
        self._save_chat_history()

    # ========== 主动说话回调 ==========

    def _on_proactive_speech(self, text: str):
        """处理 AI 主动说话回调"""
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(
            self,
            "_handle_proactive_speech",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, text)
        )

    @Slot(str)
    def _handle_proactive_speech(self, text: str):
        """在 UI 线程中处理主动说话（TTS 合成在后台线程）"""
        if not text:
            return

        self.chat_display.append_system_msg("AI 主动说话")
        self.chat_display.append_ai_msg(text)
        self._record_message("assistant", text)

        self._auto_detect_expression(text)

        if self.backend:
            worker = TTSWorker(self.backend, text, parent=self)
            worker.audio_ready.connect(self._on_tts_audio_ready)
            worker.error.connect(lambda e: print(f"[ChatPage] 主动说话 TTS 失败: {e}"))
            worker.finished.connect(lambda: self._cleanup_tts_worker(worker))
            self._tts_workers.append(worker)
            worker.start()

        self._save_chat_history()

    # ========== 主题刷新 ==========

    def refresh_theme(self):
        """主题切换时刷新所有硬编码样式"""
        from gugu_native.theme import get_colors
        c = get_colors()

        # 刷新聊天区卡片
        self._chat_card.setStyleSheet(f"""
            QFrame#chatCard {{
                background-color: {c.card_bg};
                border: 1px solid {c.card_border};
                border-radius: 16px;
            }}
        """)

        # 刷新 Web 显示主题
        self.chat_display.refresh_theme()

        # 刷新输入栏卡片
        self._input_card.setStyleSheet(f"""
            QFrame#inputCard {{
                background-color: {c.card_bg};
                border: 1px solid {c.card_border};
                border-radius: 14px;
            }}
        """)

        # 刷新多行输入框
        self.input_field.refresh_theme()

        # 刷新发送按钮
        self.send_btn.setStyleSheet(f"""
            PushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c.accent_gradient_start}, stop:1 {c.accent_gradient_end});
                color: white;
                border: none;
                border-radius: 10px;
                padding: 7px 18px;
                font-weight: 600;
                font-size: 13px;
            }}
            PushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c.accent}, stop:1 {c.accent_hover});
            }}
            PushButton:pressed {{
                background: {c.accent_pressed};
            }}
            PushButton:disabled {{
                background: {c.card_border};
                color: {c.text_muted};
            }}
        """)

        # 刷新停止按钮
        self.stop_btn.setStyleSheet(f"""
            PushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c.error}, stop:1 #e03131);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 7px 18px;
                font-weight: 600;
                font-size: 13px;
            }}
            PushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e03131, stop:1 #c92a2a);
            }}
            PushButton:pressed {{
                background: #c92a2a;
            }}
        """)

        # 刷新TTS工具栏卡片
        self._tts_card.setStyleSheet(f"""
            QFrame#ttsCard {{
                background-color: {c.sidebar_bg};
                border: 1px solid {c.card_border};
                border-radius: 12px;
            }}
        """)

        # 刷新 QComboBox 样式
        self._style_qcombobox(self.tts_combo, c)
        self._style_qcombobox(self.voice_combo, c)

        # 刷新录音/实时语音按钮
        self.record_btn.setStyleSheet(f"""
            TogglePushButton {{
                border-radius: 12px;
                padding: 3px 10px;
                border: 1px solid {c.card_border};
                font-size: 12px;
            }}
            TogglePushButton:checked {{
                background-color: {c.error};
                color: white;
                border: none;
            }}
        """)
        self.realtime_btn.setStyleSheet(f"""
            TogglePushButton {{
                border-radius: 12px;
                padding: 3px 10px;
                border: 1px solid {c.card_border};
                font-size: 12px;
            }}
            TogglePushButton:checked {{
                background-color: {c.success};
                color: white;
                border: none;
            }}
        """)

        # 刷新搜索栏
        self.search_bar.refresh_theme()

        # 刷新会话管理器
        self.session_manager.refresh_theme()

    @staticmethod
    def _style_qcombobox(combo: QComboBox, c):
        """为原生 QComboBox 应用与 qfluentwidgets 风格一致的样式"""
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {c.input_bg};
                color: {c.text_primary};
                border: 1px solid {c.card_border};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                min-height: 24px;
            }}
            QComboBox:hover {{
                border-color: {c.accent};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {c.text_muted};
                margin-right: 6px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {c.card_bg};
                color: {c.text_primary};
                border: 1px solid {c.card_border};
                border-radius: 6px;
                selection-background-color: {c.accent};
                selection-color: white;
                padding: 4px;
                outline: none;
            }}
        """)
