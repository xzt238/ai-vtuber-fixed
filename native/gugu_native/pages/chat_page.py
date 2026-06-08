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
import shutil
import json
import time
import logging
import random  # 优化 #5: 移到顶层，避免 _lipsync_tick 每 50ms 重复导入
import tempfile
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QComboBox,
    QGroupBox, QApplication, QFrame, QSplitter
)
from PySide6.QtCore import Qt, Signal, Slot, QThread, Q_ARG, QTimer
from PySide6.QtGui import QTextCursor, QFont, QDragEnterEvent, QDropEvent
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl

from qfluentwidgets import (
    PushButton, ToolButton, FluentIcon, CaptionLabel,
    TogglePushButton, Slider, InfoBar
)
from PySide6.QtWidgets import QFileDialog

from app.shared_config import PROJECT_DIR

logger = logging.getLogger('ChatPage')

# TTS 偏好文件路径
_TTS_PREFS_FILE = os.path.join(PROJECT_DIR, "app", "cache", "tts_preferences.json")

# hex 颜色 → rgba() 转换工具（QSS 不支持 8位 hex 如 #rrggbbaa）
def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """将 hex 颜色转为 rgba() 格式，如 #7c3aed + 0.13 → rgba(124,58,237,0.13)"""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.2f})"


from gugu_native.widgets.live2d_widget import Live2DWidget
from gugu_native.widgets.chat_web_display import ChatWebDisplay
from gugu_native.widgets.multi_line_input import MultiLineInputV2
from gugu_native.widgets.session_manager import SessionManager, ChatSession
from gugu_native.widgets.message_search import MessageSearchBar
from gugu_native.widgets.animation_controller import AnimationController

# 主题回调注册
from gugu_native.theme import register_theme_callback

# VRM 3D 模型支持（可选依赖，优雅降级）
try:
    from gugu_native.widgets.vrm_widget import VRMWidget
except ImportError:
    VRMWidget = None


from gugu_native.workers.chat_workers import StreamChatWorker, TTSWorker, ASRWorker
from gugu_native.workers.vision_workers import OCRWorker, VisionWorker

# 导入 Mixin 类
from gugu_native.pages.chat_page_mixins.live2d_mixin import ChatPageLive2DMixin
from gugu_native.pages.chat_page_mixins.audio_mixin import ChatPageAudioMixin
from gugu_native.pages.chat_page_mixins.message_mixin import ChatPageMessageMixin
from gugu_native.pages.chat_page_mixins.vision_mixin import ChatPageVisionMixin
from gugu_native.pages.chat_page_mixins.tts_config_mixin import ChatPageTTSConfigMixin


# ============================================================================
# ChatPage — 对话页面主控件
# ============================================================================

class ChatPage(
    ChatPageLive2DMixin,
    ChatPageAudioMixin,
    ChatPageMessageMixin,
    ChatPageVisionMixin,
    ChatPageTTSConfigMixin,
    QWidget
):
    """对话页面 v2.0 — 完全重构版（使用 Mixin 模式拆分功能）"""

    # 优化 #13: 线程安全的 TTS 音频就绪信号
    # v14 FIX: Signal 携带序号 (audio_path, seq)，用于流式 TTS 句子排序
    _tts_audio_signal = Signal(str, int)

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
        # 优化 #13: TTS 并发限制，防止线程爆炸
        # v15 FIX: 恢复 max_workers=3 并行处理（效率高），
        # 按序播放由 _tts_pending + _tts_next_play_seq 机制保证
        from concurrent.futures import ThreadPoolExecutor
        self._tts_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="tts")
        self._tts_audio_signal.connect(self._on_tts_audio_ready)
        # v14 FIX: 流式 TTS 句子排序 — 序号计数器和播放指针
        self._tts_seq_counter = 0
        self._tts_next_play_seq = 1   # 下一个预期播放的序号（序号从 1 开始）
        self._tts_pending = {}        # 暂存乱序到达的音频: {seq: audio_path}

        # 注册清理回调
        if parent and hasattr(parent, 'perf_manager'):
            parent.perf_manager.register_cleanup_target("chat_page", self)

        # === 分帧初始化：先创建 shell 框架，再延迟创建内容 ===
        self._chat_display_ready = False
        self._pending_chat_messages = []

        self._init_ui_shell()
        QTimer.singleShot(0, self._init_ui_content)

        self.setAcceptDrops(True)  # 启用拖拽
        # 注册主题变更回调
        register_theme_callback(self.refresh_theme)

    def cleanup(self):
        """退出时清理：关闭线程池 + 停止定时器 + 清空 Worker 列表"""
        if hasattr(self, '_tts_executor') and self._tts_executor:
            self._tts_executor.shutdown(wait=False)
        if hasattr(self, '_lipsync_timer') and self._lipsync_timer:
            self._lipsync_timer.stop()
        if hasattr(self, '_tts_workers'):
            self._tts_workers.clear()

    def _init_ui_shell(self):
        """创建主布局框架 + 占位符（极轻量，让窗口尽快显示）"""
        from gugu_native.theme import get_colors
        c = get_colors()

        # 设置页面最小尺寸，防止缩放时重叠
        self.setMinimumSize(800, 500)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # === 左侧: Live2D 区域 ===
        self._live2d_layout = QVBoxLayout()
        self._live2d_layout.setSpacing(4)
        main_layout.addLayout(self._live2d_layout, stretch=2)

        # ★ v11: Live2D 延迟创建 — 先用占位符，窗口显示后再创建 QWebEngineView
        self.live2d_widget = None  # 将在 _lazy_init_live2d() 中创建
        self._vrm_widget = None    # VRM 3D 模型 widget（延迟创建）
        self._current_model_type = "live2d"  # "live2d" | "vrm"
        self._live2d_placeholder = QLabel("⏳ 正在加载 Live2D...")
        self._live2d_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._live2d_placeholder.setStyleSheet(f"""
            QLabel {{
                color: {c.text_muted};
                font-size: 14px;
                background: transparent;
                padding: 20px;
            }}
        """)
        self._live2d_placeholder.setMinimumSize(380, 480)
        self._model_toggle_bar = None  # 将在 _init_ui_content 中创建
        self._vrm_variant_bar = None   # 将在 _init_ui_content 中创建
        self._live2d_layout.addWidget(self._live2d_placeholder, stretch=1)

        # 主动画控制器 — 将在 _lazy_init_live2d() 中创建
        self._animation_controller = None

        # === 中部: 会话列表侧边栏（占位，延迟创建） ===
        self.session_manager = None  # 将在 _init_ui_content 中创建

        # === 右侧: 对话区域 — 占位符 ===
        self._right_panel = QVBoxLayout()
        self._right_panel.setSpacing(6)
        self._right_panel.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(self._right_panel, stretch=3)

        # 对话区占位符 — 替代 ChatWebDisplay
        self._chat_placeholder = QLabel("⏳ 正在加载对话...")
        self._chat_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._chat_placeholder.setStyleSheet(f"""
            QLabel {{
                color: {c.text_muted};
                font-size: 14px;
                background: transparent;
                padding: 20px;
            }}
        """)
        self._right_panel.addWidget(self._chat_placeholder, stretch=1)

        # 以下控件将在 _init_ui_content 中创建
        self.search_bar = None
        self._chat_card = None
        self.chat_display = None
        self._input_card = None
        self.input_field = None
        self.send_btn = None
        self.clear_btn = None
        self._tts_card = None
        self.tts_combo = None
        self.voice_combo = None
        self.record_btn = None
        self.realtime_btn = None
        self.tts_mode_btn = None
        self.speed_slider = None
        self.volume_slider = None
        self._media_player = None
        self._audio_output = None
        self._send_style = ""
        self._stop_style = ""

    def _init_ui_content(self):
        """延迟创建具体控件（通过 QTimer.singleShot(0) 调度，让窗口先显示）"""
        # T10: 性能埋点
        if hasattr(self, '_perf_t4_start'):
            pass  # 由 T10 外层设置
        self._perf_t4_start = time.perf_counter()

        c = get_colors()

        # === 移除对话区占位符 ===
        if self._chat_placeholder:
            self._right_panel.removeWidget(self._chat_placeholder)
            self._chat_placeholder.hide()
            self._chat_placeholder.deleteLater()
            self._chat_placeholder = None

        # ★ 模型类型切换栏（Live2D / VRM 3D）— 插入到 Live2D 占位符之前
        self._model_toggle_bar = QWidget()
        toggle_layout = QHBoxLayout(self._model_toggle_bar)
        toggle_layout.setContentsMargins(4, 2, 4, 2)
        toggle_layout.setSpacing(4)

        self._btn_live2d = QPushButton("🐱 Live2D")
        self._btn_live2d.setCheckable(True)
        self._btn_live2d.setChecked(True)
        self._btn_live2d.setStyleSheet(f"""
            QPushButton {{ background: {c.accent}; color: {c.text_on_accent}; border: none;
                border-radius: 4px; padding: 4px 12px; font-size: 12px; font-weight: bold; }}
            QPushButton:checked {{ background: {c.accent}; color: {c.text_on_accent}; }}
            QPushButton:!checked {{ background: {c.card_bg}; color: {c.text_muted}; }}
            QPushButton:hover {{ background: {c.accent_hover}; }}
        """)
        self._btn_live2d.clicked.connect(lambda: self.switch_model_type("live2d"))

        self._btn_vrm = QPushButton("🧊 VRM 3D")
        self._btn_vrm.setCheckable(True)
        self._btn_vrm.setStyleSheet(f"""
            QPushButton {{ background: {c.card_bg}; color: {c.text_muted}; border: none;
                border-radius: 4px; padding: 4px 12px; font-size: 12px; }}
            QPushButton:checked {{ background: {c.ai_bubble_accent}; color: {c.text_on_accent}; font-weight: bold; }}
            QPushButton:!checked {{ background: {c.card_bg}; color: {c.text_muted}; }}
            QPushButton:hover {{ background: {c.card_bg_hover}; }}
        """)
        self._btn_vrm.clicked.connect(lambda: self.switch_model_type("vrm"))

        toggle_layout.addWidget(self._btn_live2d)
        toggle_layout.addWidget(self._btn_vrm)

        # 竖分隔线
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background-color: {c.card_border};")
        toggle_layout.addWidget(sep)

        # ★ 模型导入按钮（合并到同一行）
        btn_vrm = QPushButton("📁 加载VRM")
        _vrm_bg = _hex_to_rgba(c.ai_bubble_accent, 0.13)
        _vrm_border = _hex_to_rgba(c.ai_bubble_accent, 0.27)
        btn_vrm.setStyleSheet(f"""
            QPushButton {{ background: {_vrm_bg}; color: {c.text_secondary};
                border: 1px solid {_vrm_border}; border-radius: 3px;
                padding: 2px 8px; font-size: 11px; }}
            QPushButton:hover {{ background: {_vrm_border}; }}
        """)
        btn_vrm.clicked.connect(self._import_vrm_model)
        toggle_layout.addWidget(btn_vrm)

        btn_l2d = QPushButton("📁 加载Live2D")
        _l2d_bg = _hex_to_rgba(c.accent, 0.13)
        _l2d_border = _hex_to_rgba(c.accent, 0.27)
        btn_l2d.setStyleSheet(f"""
            QPushButton {{ background: {_l2d_bg}; color: {c.text_secondary};
                border: 1px solid {_l2d_border}; border-radius: 3px;
                padding: 2px 8px; font-size: 11px; }}
            QPushButton:hover {{ background: {_l2d_border}; }}
        """)
        btn_l2d.clicked.connect(self._import_live2d_model)
        toggle_layout.addWidget(btn_l2d)

        toggle_layout.addStretch()

        # 桌面宠物按钮
        self.pet_btn = ToolButton(FluentIcon.HEART)
        self.pet_btn.setFixedSize(26, 26)
        self.pet_btn.setToolTip("桌面宠物")
        self.pet_btn.clicked.connect(self._toggle_pet)
        toggle_layout.addWidget(self.pet_btn)

        self._model_toggle_bar.setFixedHeight(34)
        # 默认可见（导入按钮+宠物按钮始终可用），VRM 切换按钮按需显示
        self._btn_vrm.hide()
        # 插入到 Live2D 占位符之前（index 0 = toggle bar, index 1 = VRM variant bar, index 2 = placeholder/widget）
        self._live2d_layout.insertWidget(0, self._model_toggle_bar)

        # ★ VRM 变体切换栏（AU / cow / jacket / swim）
        self._vrm_variant_bar = QWidget()
        variant_layout = QHBoxLayout(self._vrm_variant_bar)
        variant_layout.setContentsMargins(4, 1, 4, 1)
        variant_layout.setSpacing(3)
        self._btn_vrm_variants = {}
        for name, label in [("default", "默认"), ("cow", "🐄 奶牛"), ("jacket", "🧥 外套"), ("swim", "🏊 泳装")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(f"""
                QPushButton {{ background: {c.card_bg}; color: {c.text_muted};
                    border: 1px solid {c.card_border}; border-radius: 3px;
                    padding: 2px 8px; font-size: 11px; }}
                QPushButton:checked {{ background: {c.ai_bubble_accent}; color: {c.text_on_accent}; border-color: {c.ai_bubble_accent}; font-weight: bold; }}
                QPushButton:hover {{ background: {c.card_bg_hover}; }}
            """)
            btn.clicked.connect(lambda checked, n=name: self._switch_vrm_variant(n))
            variant_layout.addWidget(btn)
            self._btn_vrm_variants[name] = btn
        variant_layout.addStretch()
        # 默认选中 AU
        if "default" in self._btn_vrm_variants:
            self._btn_vrm_variants["default"].setChecked(True)
        self._vrm_variant_bar.setFixedHeight(26)
        self._vrm_variant_bar.hide()
        self._live2d_layout.insertWidget(1, self._vrm_variant_bar)

        # === 中部: 会话列表侧边栏 ===
        self.session_manager = SessionManager(self)
        self.session_manager.sessionSwitched.connect(self._on_session_switched)
        self.session_manager.sessionCreated.connect(self._on_session_created)
        # 插入到主布局中 Live2D 和右侧之间（index 1）
        self.layout().insertWidget(1, self.session_manager, stretch=0)

        # ──────── 消息搜索栏（默认隐藏） ────────
        self.search_bar = MessageSearchBar(self)
        self.search_bar.searchRequested.connect(self._on_search)
        self.search_bar.searchNavigate.connect(self._on_search_navigate)
        self._right_panel.addWidget(self.search_bar)

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
        chat_card_layout.setContentsMargins(8, 8, 8, 8)
        chat_card_layout.setSpacing(0)

        # QWebEngineView 聊天显示（带 QTextEdit 降级）
        self.chat_display = ChatWebDisplay(self)
        self.chat_display.action_copy.connect(self._on_action_copy)
        self.chat_display.action_retry.connect(self._on_action_retry)
        self.chat_display.action_quote.connect(self._on_action_quote)
        self.chat_display.action_edit.connect(self._on_action_edit)
        chat_card_layout.addWidget(self.chat_display)
        self._right_panel.addWidget(self._chat_card, stretch=1)

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

        # 发送/停止按钮 — 同位置切换（参考 ChatGPT/微信设计）
        self.send_btn = PushButton(" 发送")
        self.send_btn.setIcon(FluentIcon.SEND)
        self.send_btn.clicked.connect(self._on_send_or_stop)
        self._send_style = f"""
            PushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c.accent_gradient_start}, stop:1 {c.accent_gradient_end});
                color: {c.text_on_accent};
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
        """
        self._stop_style = f"""
            PushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c.error}, stop:1 {c.error_hover});
                color: {c.text_on_accent};
                border: none;
                border-radius: 10px;
                padding: 7px 18px;
                font-weight: 600;
                font-size: 13px;
            }}
            PushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c.error_hover}, stop:1 {c.error_pressed});
            }}
        """
        self.send_btn.setStyleSheet(self._send_style)
        toolbar_layout.addWidget(self.send_btn)

        toolbar_layout.addSpacing(12)

        # 清空按钮 — 间距加大 + 警告色防误触
        self.clear_btn = ToolButton(FluentIcon.DELETE)
        self.clear_btn.setFixedSize(32, 32)
        self.clear_btn.setToolTip("清空对话 (需确认)")
        self.clear_btn.clicked.connect(self._on_clear_chat)
        self.clear_btn.setStyleSheet(f"""
            ToolButton {{
                color: {c.text_muted};
                border-radius: 6px;
            }}
            ToolButton:hover {{
                color: {c.error};
                background-color: {c.error_bg};
            }}
        """)
        toolbar_layout.addWidget(self.clear_btn)

        input_card_layout.addLayout(toolbar_layout)

        # 多行输入框
        self.input_field = MultiLineInputV2(self)
        self.input_field.sendRequested.connect(self._send_message)
        input_card_layout.addWidget(self.input_field)

        self._right_panel.addWidget(self._input_card)

        # ──────── 卡片3: TTS 工具栏（两行布局，防缩放重叠） ────────
        self._tts_card = QFrame()
        self._tts_card.setObjectName("ttsCard")
        self._tts_card.setStyleSheet(f"""
            QFrame#ttsCard {{
                background-color: {c.card_bg};
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
        self.tts_combo.addItems(["Edge TTS", "GPT-SoVITS"])
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

        # 实时语音按钮 — 耳麦图标区分于录音的麦克风
        self.realtime_btn = TogglePushButton("🎙 实时对话")
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

        self._right_panel.addWidget(self._tts_card)

        # === 音频播放器 ===
        self._media_player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._media_player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(0.8)

        # === ChatWebDisplay 已就绪 — 标记 + 重放缓冲消息 ===
        self._chat_display_ready = True
        self._replay_pending_chat_messages()

        # === 加载对话历史（从 __init__ 移至此处，确保 chat_display 已创建）===
        self._load_chat_history()

        # T10: 性能埋点
        self._perf_t4_end = time.perf_counter()
        logger.info(f"[PERF] ChatPage _init_ui_content: {self._perf_t4_end - self._perf_t4_start:.3f}s")

    def append_message_safe(self, role: str, text: str, timestamp: str = None):
        """安全追加消息 — 如果 ChatWebDisplay 未就绪，缓冲到队列"""
        if self._chat_display_ready and self.chat_display:
            if role == "user":
                self.chat_display.append_user_msg(text, timestamp=timestamp)
            elif role == "assistant":
                self.chat_display.append_ai_msg(text, timestamp=timestamp)
            else:
                self.chat_display.append_system_msg(text)
        else:
            self._pending_chat_messages.append((role, text, timestamp))

    def _replay_pending_chat_messages(self):
        """重放缓冲消息 — 在 ChatWebDisplay 创建后调用"""
        if not self._pending_chat_messages:
            return
        for role, text, timestamp in self._pending_chat_messages:
            if role == "user":
                self.chat_display.append_user_msg(text, timestamp=timestamp)
            elif role == "assistant":
                self.chat_display.append_ai_msg(text, timestamp=timestamp)
            else:
                self.chat_display.append_system_msg(text)
        self._pending_chat_messages.clear()

    # T10: showEvent 埋点
    def showEvent(self, event):
        """首次显示时输出性能汇总"""
        super().showEvent(event)
        if not hasattr(self, '_perf_first_show'):
            self._perf_first_show = True
            self._perf_t6 = time.perf_counter()
            # 从主窗口获取性能时间戳（_perf_t1/t2/t3 在 GuguGagaApp 上）
            main_win = self.window()
            t1 = getattr(main_win, '_perf_t1', 0)
            t2 = getattr(main_win, '_perf_t2', 0)
            t3 = getattr(main_win, '_perf_t3', 0)
            t6 = self._perf_t6
            if t1 > 0:
                logger.info(f"[PERF] T1→T2: init前置 {t2-t1:.3f}s | T2→T3: 页面创建 {t3-t2:.3f}s | T1→T6: 总计 {t6-t1:.3f}s")

    def _lazy_init_live2d(self):
        """v1.10.2: 延迟创建 Live2DWidget — 让窗口先显示再加载 Chromium

        QWebEngineView 的创建需要启动 Chromium 渲染进程，这是整个启动链路中
        最耗时的操作（5-10 秒）。通过延迟创建，窗口可以先显示出来，
        用户看到的是"应用已启动"，而不是"等了 20 秒什么都没出来"。

        v1.10.2 修复:
        - 直接在 self._live2d_layout 上做 indexOf（placeholder 最初添加到的布局）
        - 替换后 invalidate + activate 确保 QWebEngineView 几何正确传播
        - 三段式 repaint：立即 + 500ms + 3000ms 安全网
        """
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        if self.live2d_widget is not None:
            return  # 已经创建过了

        # 创建 Live2D 组件
        self.live2d_widget = Live2DWidget()

        # v1.11.24 性能优化：连接窗口拖动状态信号，拖动/resize 时暂停 Live2D 渲染
        main_window = self.window()
        if main_window and hasattr(main_window, 'perf_manager') and main_window.perf_manager:
            main_window.perf_manager.window_drag_state_changed.connect(
                self.live2d_widget.set_window_drag_state
            )

        # 替换占位符 — 只在 _live2d_layout 上操作
        # placeholder 在 __init__ 中通过 self._live2d_layout.addWidget() 添加，
        # 必须在同一个 layout 实例上做 indexOf / removeWidget / insertWidget
        if self._live2d_placeholder:
            idx = self._live2d_layout.indexOf(self._live2d_placeholder)
            if idx >= 0:
                self._live2d_layout.removeWidget(self._live2d_placeholder)
                self._live2d_placeholder.hide()
                self._live2d_placeholder.deleteLater()
                self._live2d_placeholder = None

                # 在同一位置插入 Live2D widget
                self._live2d_layout.insertWidget(idx, self.live2d_widget, stretch=1)
                self.live2d_widget.show()
                self.live2d_widget.updateGeometry()

                # 强制布局刷新：invalidate + activate 确保 QWebEngineView
                # 的几何信息在父布局链中正确传播
                self._live2d_layout.invalidate()
                self._live2d_layout.activate()
                self.update()

                # ★ 三段式 repaint：确保 QWebEngineView 合成到屏幕
                # (1) 立即：通过 processEvents 让 pending 的布局事件先处理
                # (2) 500ms：Chromium 轻量初始化可能已完成
                # (3) 3000ms：安全网，覆盖 Chromium 完全冷启动
                # 优化：使用 QTimer.singleShot 替代直接调用 processEvents，避免阻塞UI
                QTimer.singleShot(0, self._force_live2d_repaint)
                QTimer.singleShot(500, self._force_live2d_repaint)
                QTimer.singleShot(3000, self._force_live2d_repaint)
                logger.info("[ChatPage] Live2D placeholder replaced with widget")
            else:
                # fallback: indexOf 没找到 — 追加到布局末尾
                self._live2d_layout.addWidget(self.live2d_widget, stretch=1)
                self.live2d_widget.show()
                self.live2d_widget.updateGeometry()
                self._live2d_placeholder.hide()
                self._live2d_placeholder.deleteLater()
                self._live2d_placeholder = None

                # 优化：使用 QTimer.singleShot 替代直接调用 processEvents，避免阻塞UI
                QTimer.singleShot(0, self._force_live2d_repaint)
                QTimer.singleShot(500, self._force_live2d_repaint)
                QTimer.singleShot(3000, self._force_live2d_repaint)
                logger.info("[ChatPage] Live2D placeholder replaced (fallback append)")

        # 创建动画控制器
        self._animation_controller = AnimationController(self.live2d_widget)

        # 加载默认模型
        self._load_default_model()

        # ★ VRM 3D 模型支持 — 延迟创建（与 Live2D 共用布局位置）
        if VRMWidget is not None:
            self._vrm_widget = VRMWidget()
            self._vrm_widget.model_loaded.connect(lambda _: self._apply_vrm_display_config())
            # 添加到布局末尾（与 Live2D widget 同一层级），默认隐藏
            self._live2d_layout.addWidget(self._vrm_widget, stretch=1)
            self._vrm_widget.hide()
            self._load_default_vrm_model()
            # 显示 VRM 切换按钮
            self._btn_vrm.show()
            logger.info("[ChatPage] VRM widget 已创建（隐藏）")
        else:
            logger.info("[ChatPage] VRMWidget 不可用，跳过 VRM 支持")

    def _force_live2d_repaint(self):
        """微调窗口尺寸强制 QWebEngineView 合成到屏幕"""
        if not self.live2d_widget:
            return
        w = self.window()
        if w:
            g = w.geometry()
            w.resize(g.width() + 1, g.height())
            w.resize(g.width(), g.height())

    def _load_default_model(self):
        """加载默认 Live2D 模型"""
        if self.live2d_widget is None:
            return  # Live2D 还没创建

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
            if self._chat_display_ready and self.chat_display:
                self.chat_display.append_system_msg(f"默认模型不存在: {model_path}")

    def _load_default_vrm_model(self):
        """加载默认 VRM 3D 模型"""
        if self._vrm_widget is None:
            return

        vrm_path = os.path.join(
            PROJECT_DIR, "app", "web", "static", "assets", "model",
            "default.vrm"
        )
        if os.path.exists(vrm_path):
            self._vrm_widget.load_model(vrm_path)
            logger.info(f"[ChatPage] VRM 默认模型已加载: {vrm_path}")
        else:
            logger.info(f"[ChatPage] VRM 默认模型不存在: {vrm_path}")

    def switch_model_type(self, model_type: str):
        """切换 Live2D / VRM 模型显示"""
        if model_type == self._current_model_type:
            return

        if model_type == "vrm" and self._vrm_widget is None:
            logger.info("[ChatPage] VRM widget 不可用，无法切换")
            return

        if model_type == "vrm":
            if self.live2d_widget:
                self.live2d_widget.hide()
            if self._vrm_widget:
                self._vrm_widget.show()
                if self._animation_controller:
                    self._animation_controller._widget = self._vrm_widget
            self._current_model_type = "vrm"
            self._btn_live2d.setChecked(False)
            self._btn_vrm.setChecked(True)
            self._vrm_variant_bar.show()
            logger.info("[ChatPage] 已切换到 VRM 模型")
        else:
            if self._vrm_widget:
                self._vrm_widget.hide()
            if self.live2d_widget:
                self.live2d_widget.show()
                if self._animation_controller:
                    self._animation_controller._widget = self.live2d_widget
            self._current_model_type = "live2d"
            self._btn_live2d.setChecked(True)
            self._btn_vrm.setChecked(False)
            self._vrm_variant_bar.hide()
            logger.info("[ChatPage] 已切换到 Live2D 模型")

    def _switch_vrm_variant(self, variant: str):
        """切换 VRM 变体"""
        if not self._vrm_widget:
            return
        variant_files = {
            "default": "default.vrm",
            "cow": "Asmodeus_cow.vrm",
            "jacket": "Asmodeus_jacket.vrm",
            "swim": "Asmodeus_swim.vrm",
        }
        filename = variant_files.get(variant)
        if not filename:
            return
        vrm_path = os.path.join(PROJECT_DIR, "app", "web", "static", "assets", "model", filename)
        if os.path.exists(vrm_path):
            self._vrm_widget.load_model(vrm_path)
            # 更新按钮选中状态
            for name, btn in self._btn_vrm_variants.items():
                btn.setChecked(name == variant)
            logger.info(f"[ChatPage] 切换 VRM 变体: {variant} → {filename}")

    def _import_vrm_model(self):
        """导入新的 VRM 模型文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 VRM 模型文件",
            os.path.expanduser("~"), "VRM 模型 (*.vrm)"
        )
        if not path:
            return
        model_name = os.path.splitext(os.path.basename(path))[0]
        dest_dir = os.path.join(PROJECT_DIR, "app", "web", "static", "assets", "model")
        dest = os.path.join(dest_dir, f"user_{model_name}.vrm")
        shutil.copy2(path, dest)
        # 如果当前是 VRM 模式，直接加载
        if self._vrm_widget and self._current_model_type == "vrm":
            self._vrm_widget.load_model(dest)
        InfoBar.success("导入成功", f"VRM 模型已导入: {model_name}", parent=self)
        logger.info(f"[ChatPage] 导入 VRM: {path} → {dest}")

    def _import_live2d_model(self):
        """导入新的 Live2D 模型文件夹"""
        path = QFileDialog.getExistingDirectory(
            self, "选择 Live2D 模型文件夹"
        )
        if not path:
            return
        model_name = os.path.basename(path)
        dest_dir = os.path.join(PROJECT_DIR, "app", "web", "static", "assets", "model", f"l2d_{model_name}")
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)
        shutil.copytree(path, dest_dir)
        # 找到 .model3.json 文件并加载
        for f in os.listdir(dest_dir):
            if f.endswith(".model3.json"):
                model_json = os.path.join(dest_dir, f)
                if self.live2d_widget:
                    self.live2d_widget.load_model(model_json)
                break
        InfoBar.success("导入成功", f"Live2D 模型已导入: {model_name}", parent=self)
        logger.info(f"[ChatPage] 导入 Live2D: {path} → {dest_dir}")

    def _apply_vrm_display_config(self):
        """读取保存的 VRM 显示配置并应用到当前模型"""
        if not self._vrm_widget:
            return
        cache_path = os.path.join(PROJECT_DIR, "app", "cache", "vrm_display.json")
        config = {}
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception as e:
                pass
        if config:
            self._vrm_widget.apply_display_config(config)

    @property
    def backend(self):
        """获取后端实例（延迟初始化）"""
        if self._backend is None:
            main_window = self.window()
            if hasattr(main_window, 'backend'):
                self._backend = main_window.backend
        return self._backend

    def on_backend_ready(self):
        """后端就绪回调 — 启动 Live2D、加载 TTS 配置和对话历史"""
        if not self.backend:
            return

        # v13: 在后端就绪后启动 Live2D（而非 ChatPage 构造时）
        # 确保窗口已经显示，Live2D 的 Chromium 初始化不会阻塞 UI
        QTimer.singleShot(100, self._lazy_init_live2d)

        # 加载 TTS 配置（需要 chat_display_ready，因为 _populate_*_voices 依赖 combo 控件）
        if self._chat_display_ready:
            self._load_tts_config_on_backend_ready()
        else:
            # 延迟加载：等 _init_ui_content 完成后
            QTimer.singleShot(200, self._load_tts_config_on_backend_ready)

        # 加载对话历史（仅从 backend.history 加载，_load_chat_history 在 _init_ui_content 中已调用）
        if self._chat_display_ready:
            self._load_backend_history()
        else:
            QTimer.singleShot(300, self._load_backend_history)

    def _load_tts_config_on_backend_ready(self):
        """后端就绪后加载 TTS 配置"""
        if not self._chat_display_ready:
            return
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
            logger.info(f"[ChatPage] 加载 TTS 配置失败: {e}")
            self.tts_combo.blockSignals(False)
            self.voice_combo.blockSignals(False)

    def _load_backend_history(self):
        """从 backend.history 加载对话历史"""
        if not self._chat_display_ready or not self.chat_display:
            return
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
        except Exception as e:
            logger.info(f"[ChatPage] 从后端加载历史失败: {e}")

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
            self.append_message_safe("system", "后端未初始化，请先在设置页面配置 API Key")
            return

        # v1.11.25: S-002 TTS 预热懒加载 — 首次对话时触发预热
        if not getattr(self, '_tts_prewarmed', True):
            self._tts_prewarmed = True
            main_window = self.window()
            if main_window and hasattr(main_window, '_prewarm_tts'):
                import threading
                threading.Thread(target=main_window._prewarm_tts, daemon=True).start()
                logger.info("TTS prewarm triggered by first conversation")

        # 获取引用文本
        quote = self.input_field.quote_text
        if quote:
            if self._chat_display_ready and self.chat_display:
                self.chat_display.append_user_msg(text, quote=quote)
            else:
                self._pending_chat_messages.append(("user", text, None))
            # 在发送给 LLM 的文本中加入引用
            if quote:
                text = f"[引用: {quote}]\n{text}"
            self.input_field.clear_quote()
        else:
            self.append_message_safe("user", text)
        # v1.9.89: 记录用户消息到历史
        self._record_message("user", text)

        self.input_field.clear()
        self._set_streaming_state(True)
        self._current_ai_text = ""

        # v14 FIX: 重置流式 TTS 排序状态
        self._tts_seq_counter = 0
        self._tts_next_play_seq = 1  # 序号从 1 开始
        self._tts_pending.clear()

        # 添加正在思考占位
        if self._chat_display_ready and self.chat_display:
            self.chat_display.start_streaming()

        # 获取对话历史
        history = list(self.backend.history) if hasattr(self.backend, 'history') else []

        # 启动流式对话线程
        streaming_tts = self.tts_mode_btn.isChecked()
        worker = StreamChatWorker(self.backend, text, history, streaming_tts=streaming_tts)
        self._worker = worker
        self._active_worker_id = id(worker)  # 追踪当前 worker 身份
        worker.chunk_received.connect(self._on_chunk)
        worker.sentence_ready.connect(self._on_sentence_ready)
        worker.finished_stream.connect(self._on_stream_finished)
        worker.error.connect(self._on_error)
        worker.tool_call_status.connect(self._on_tool_call_status)
        worker.start()

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
            # v14 FIX: 清空排序缓冲区
            self._tts_pending.clear()
            self._tts_next_play_seq = 1
            self._tts_seq_counter = 0
            for w in self._tts_workers:
                if w.isRunning():
                    w.quit()
                    w.wait(500)
            self._tts_workers.clear()

    def _on_send_or_stop(self):
        """发送/停止按钮点击——根据当前状态路由"""
        if self._is_streaming:
            self._stop_streaming()
        else:
            self._send_message()

    def _set_streaming_state(self, streaming: bool):
        """流式状态切换——同按钮变色不消失（参考 ChatGPT 设计）"""
        self._is_streaming = streaming
        if streaming:
            self.send_btn.setText(" 停止")
            self.send_btn.setIcon(FluentIcon.CANCEL)
            self.send_btn.setStyleSheet(self._stop_style)
        else:
            self.send_btn.setText(" 发送")
            self.send_btn.setIcon(FluentIcon.SEND)
            self.send_btn.setStyleSheet(self._send_style)
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
        """流式 TTS：检测到完整句子，在后台线程合成音频

        v14 FIX: 给每个句子分配递增序号，传递给 TTS 任务，
        确保句子按 LLM 输出顺序播放（即使合成完成时间不同）
        """
        if not sentence or not self.backend:
            return
        # v14 FIX: 递增序号并捕获当前值
        self._tts_seq_counter += 1
        seq = self._tts_seq_counter
        def _tts_task(text, seq_num):
            try:
                audio_path = self.backend.speak(text)
                if audio_path and os.path.exists(audio_path):
                    # 通过信号传回主线程（线程安全），携带序号
                    self._tts_audio_signal.emit(audio_path, seq_num)
            except Exception as e:
                logger.info(f"[ChatPage] 流式 TTS 句子合成失败: {e}")
        self._tts_executor.submit(_tts_task, sentence, seq)

    @Slot(dict)
    def _on_stream_finished(self, result: dict):
        """流式对话完成"""
        # 守卫1: 流已停止
        if not self._is_streaming:
            return
        # 守卫2: 忽略旧 worker 的信号（防止实时语音中断时的竞态崩溃）
        sender = self.sender()
        if sender is not None and sender is not self._worker:
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
                logger.info(f"[ChatPage] FC 表情指令: {emotion}")

        # 自动表情检测 → 统一通过 AnimationController（优化 #6: 去重）
        if reply_text and not any(a.get("type") == "change_expression" for a in ui_actions):
            if self._animation_controller:
                self._animation_controller.trigger_emotion_from_text(reply_text)

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
    # 优化 #6: 已移除 _EXPRESSION_KEYWORDS / _EXPRESSION_MAP / _auto_detect_expression()
    # 所有情绪检测统一通过 AnimationController.trigger_emotion_from_text()
    _auto_expression_enabled = True

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
                    except Exception as e:
                        continue
        except Exception as e:
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

    def _on_tts_audio_ready(self, audio_path: str, seq: int = 0):
        """TTS 合成完成回调 — 统一排队，不中断当前播放

        排序缓冲区机制（seq > 0 时生效）：
        - TTS 句子可能乱序完成（并行合成），用 seq 序号保证播放顺序
        - 新音频先入 _tts_pending 缓冲区，按序释放到 _audio_queue
        - 播放决策统一由 _try_play_next() 处理，避免竞态条件

        v1.11.15 FIX: 解决句子打断问题 —
        1) 不在 _on_tts_audio_ready 中直接 _play_audio，统一走 _try_play_next
        2) 释放排序缓冲区只在一个地方（_try_play_next），不重复释放
        3) _is_playing 标志位替代 QMediaPlayer 实时状态检查，避免信号延迟导致的竞态
        """
        if not audio_path or not os.path.exists(audio_path):
            return

        # 流式 TTS：先入排序缓冲区
        if seq > 0:
            self._tts_pending[seq] = audio_path
        else:
            # 非流式（主动说话等）：直接排队
            if audio_path not in self._audio_queue:
                self._audio_queue.append(audio_path)

        # 尝试释放连续的排序序号并播放
        self._try_play_next()

    def _try_play_next(self):
        """统一的播放调度 — 释放排序缓冲区 + 播放下一首

        所有播放决策集中在此方法，避免多处重复释放导致竞态条件。
        """
        # 1. 释放所有连续的排序序号到播放队列
        while self._tts_next_play_seq in self._tts_pending:
            na = self._tts_pending.pop(self._tts_next_play_seq)
            self._tts_next_play_seq += 1
            if na not in self._audio_queue:
                self._audio_queue.append(na)

        # 2. 检查是否正在播放（用标志位而非 QMediaPlayer 实时状态）
        if self._is_audio_playing():
            return  # 正在播放，等 _on_playback_state_changed 回调时再调度

        # 3. 空闲状态：播放队列头
        if self._audio_queue:
            next_audio = self._audio_queue.pop(0)
            if os.path.exists(next_audio):
                self._play_audio(next_audio)

    def _is_audio_playing(self) -> bool:
        """检查音频是否正在播放（比直接检查 QMediaPlayer 更可靠）

        优先使用 QMediaPlayer 的状态，但增加保护：
        - StoppedState + 队列非空 = 不算播放中（可能刚播完）
        - 检查 source 是否有效，避免误判
        """
        if not self._media_player:
            return False
        state = self._media_player.playbackState()
        return state == QMediaPlayer.PlaybackState.PlayingState

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
            logger.info(f"[ChatPage] 音频播放失败: {e}")

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
        self._lipsync_timer.start(100)  # 每 100ms 更新一次（10 fps，原 50ms）

        # 监听播放结束 — 先断开旧连接再重新连接，防止 N 次播放触发 N 次回调
        try:
            self._media_player.playbackStateChanged.disconnect(self._on_playback_state_changed)
        except (RuntimeError, TypeError):
            pass  # 未连接时 disconnect 会抛异常，忽略即可
        self._media_player.playbackStateChanged.connect(self._on_playback_state_changed)

    def _lipsync_tick(self):
        """口型同步定时更新 — 模拟嘴巴开合"""
        if not self.isVisible():
            return
        if not self._animation_controller:
            return
        if not self._media_player or self._media_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            return
        # 简易口型同步：用随机值模拟嘴巴开合
        # TODO: 后续可用音频振幅分析驱动更精确的口型
        mouth_open = random.uniform(0.3, 1.0)
        self._animation_controller.set_mouth_open(mouth_open)

    def _on_playback_state_changed(self, state):
        """播放结束 → 播队首（排序缓冲区释放统一由 _try_play_next 处理）

        v1.11.15 FIX: 不再在此处释放排序缓冲区，避免与 _on_tts_audio_ready 的重复释放。
        只需调用 _try_play_next()，它会统一处理缓冲区释放 + 播放下一首。
        """
        if state != QMediaPlayer.PlaybackState.PlayingState:
            if self._animation_controller:
                self._animation_controller.set_mouth_open(0.0)
            if hasattr(self, '_lipsync_timer') and self._lipsync_timer:
                self._lipsync_timer.stop()
                self._lipsync_timer = None
            # 统一走 _try_play_next（包含释放排序缓冲区 + 播放下一首）
            self._try_play_next()

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
            except Exception as e:
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
            except Exception as e:
                pass
            self._recording_file = None
        self.chat_display.append_system_msg(f"语音识别失败: {error_msg}")

    # ========== 实时语音 ==========

    def _toggle_realtime_voice(self, checked: bool):
        """切换实时语音模式

        v14 FIX: 改进错误处理和信号连接/断开逻辑
        """
        main_window = self.window()
        if not hasattr(main_window, 'voice_manager') or main_window.voice_manager is None:
            self.chat_display.append_system_msg("语音管理器未初始化")
            self.realtime_btn.setChecked(False)
            return

        voice_mgr = main_window.voice_manager

        if checked and (not hasattr(main_window, 'backend') or main_window.backend is None):
            self.chat_display.append_system_msg("AI 后端尚未就绪，请稍后再试")
            self.realtime_btn.setChecked(False)
            return

        if checked:
            # v14 FIX: 先断开旧连接再重新连接，防止重复连接导致信号被多次触发
            try:
                voice_mgr.speech_recognized.disconnect(self._on_realtime_speech)
            except (RuntimeError, TypeError):
                pass  # 未连接，忽略
            voice_mgr.speech_recognized.connect(self._on_realtime_speech)
            voice_mgr.start_listening()
            if not voice_mgr.is_listening:
                self.realtime_btn.setChecked(False)
                try:
                    voice_mgr.speech_recognized.disconnect(self._on_realtime_speech)
                except (RuntimeError, TypeError):
                    pass
                return
            self.realtime_btn.setText("监听中")
        else:
            voice_mgr.stop_listening()
            self.realtime_btn.setText("实时语音")
            try:
                voice_mgr.speech_recognized.disconnect(self._on_realtime_speech)
            except (RuntimeError, TypeError):
                pass

    def _on_realtime_speech(self, text: str):
        """实时语音识别完成

        v14 FIX: 完善停止逻辑，清空所有旧的 TTS 状态，
        防止旧流式回复的音频/信号干扰新的语音输入
        """
        if text:
            # 如果正在流式回复，先停止并终结当前消息
            if self._is_streaming:
                self._stop_streaming()

            # 停止当前 TTS 播放
            if self._media_player and self._media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self._media_player.stop()

            # v14 FIX: 清空旧的音频队列和排序缓冲区
            self._audio_queue.clear()
            self._tts_pending.clear()
            self._tts_next_play_seq = 1
            self._tts_seq_counter = 0

            # 断开旧的播放状态监听，防止播放旧队列音频
            try:
                self._media_player.playbackStateChanged.disconnect(self._on_playback_state_changed)
            except (RuntimeError, TypeError):
                pass

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
                        except Exception as e:
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
        """截图OCR — 区域选择截图后识别文字"""
        if not self.backend:
            self.chat_display.append_system_msg("后端未初始化，无法使用OCR")
            return
        try:
            from gugu_native.widgets.screenshot_selector import ScreenshotSelector
            self._screenshot_selector = ScreenshotSelector()
            self._screenshot_selector.region_selected.connect(self._on_screenshot_ready)
            self._screenshot_selector.start()
        except Exception as e:
            self.chat_display.append_system_msg(f"截图OCR失败: {e}")

    def _on_screenshot_ready(self, tmp_path: str):
        """截图区域保存完成，开始 OCR"""
        self.chat_display.append_system_msg("正在识别屏幕文字...")
        self._ocr_worker = OCRWorker(self.backend, tmp_path)
        self._ocr_worker.finished.connect(self._on_ocr_result)
        self._ocr_worker.error.connect(self._on_ocr_error)
        self._ocr_worker.start()

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
        """处理待发送的图片 — KI-014 FIX: 异步处理，不阻塞主线程"""
        if not self._pending_image:
            return user_text

        image_path = self._pending_image
        self._pending_image = None

        if not self.backend:
            return user_text

        # KI-014 FIX: 使用 QThread 异步处理视觉请求，避免 UI 冻结
        self.input_field.setPlaceholderText("正在分析图片...")
        self.input_field.setEnabled(False)

        self._vision_worker = VisionWorker(self.backend, image_path, user_text)
        self._vision_worker.result_ready.connect(self._on_vision_result)
        self._vision_worker.error_occurred.connect(self._on_vision_error)
        self._vision_worker.finished.connect(lambda: self.input_field.setEnabled(True))
        self._vision_worker.start()
        return None  # 异步返回，结果通过信号传递

    @Slot(str)
    def _on_vision_result(self, enriched_text: str):
        """视觉理解完成，发送消息"""
        self.input_field.setPlaceholderText("输入消息，Enter 发送 · Ctrl+F 搜索")
        if enriched_text:
            self._send_message(enriched_text)

    @Slot(str)
    def _on_vision_error(self, error_msg: str):
        """视觉理解失败"""
        self.chat_display.append_system_msg(f"视觉理解失败: {error_msg}")
        self.input_field.setPlaceholderText("输入消息，Enter 发送 · Ctrl+F 搜索")

    # ========== 多会话管理 ==========

    def _on_session_switched(self, session_id: str):
        """切换会话"""
        # 保存当前会话
        self._save_current_session()

        # 加载新会话
        if not self.session_manager or not self.chat_display:
            return
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
        if self.chat_display:
            self.chat_display.clear()
        self._chat_messages = []

    def _save_current_session(self):
        """保存当前会话"""
        if not self.session_manager:
            return
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
        from app.shared_config import EDGE_VOICES
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
            logger.info(f"[ChatPage] 获取 GPT-SoVITS 音色失败: {e}")
        self.voice_combo.addItem("默认音色", userData="default")

    def _on_tts_engine_changed_chat(self, index: int):
        """Chat 页 TTS 引擎切换"""
        engine = self.tts_combo.currentText()
        if engine == "Edge TTS":
            self._populate_edge_voices_chat()
        elif engine == "GPT-SoVITS":
            self._populate_gptsovits_voices_chat()
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
        """将当前 TTS 选择应用到后端 — 使用线程安全的 rebuild_tts()"""
        if not self.backend:
            return
        engine = self.tts_combo.currentText()
        voice_id = self._get_voice_id_chat()
        provider_map = {"Edge TTS": "edge", "GPT-SoVITS": "gptsovits"}
        provider = provider_map.get(engine, "edge")

        tts_section = self.backend.config.config.setdefault("tts", {})
        tts_section["provider"] = provider
        if voice_id:
            sub = tts_section.setdefault(provider, {})
            sub["voice"] = voice_id
            if provider == "gptsovits":
                sub["project"] = voice_id

        # 使用线程安全的重建方法（替代直接 pop _lazy_modules）
        self.backend.rebuild_tts()

        # GPT-SoVITS 项目设置
        if provider == "gptsovits" and hasattr(self.backend.tts, 'set_project'):
            self.backend.tts.set_project(voice_id)

        # 持久化
        try:
            tts_prefs = {"engine": engine, "provider": provider, "voice": voice_id}
            cache_dir = os.path.join(PROJECT_DIR, "app", "cache")
            os.makedirs(cache_dir, exist_ok=True)
            with open(_TTS_PREFS_FILE, "w", encoding="utf-8") as f:
                json.dump(tts_prefs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.info(f"[ChatPage] TTS 偏好保存失败: {e}")

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
        except Exception as e:
            pass

    def _load_chat_history(self):
        """加载对话历史（优化 #9: 仅渲染最近20条，完整历史保存在 _chat_messages 中供 LLM 上下文使用）"""
        if not self.chat_display:
            return  # ChatWebDisplay 未创建，跳过（将在 _init_ui_content 中调用）
        try:
            path = self._get_history_path()
            if not os.path.exists(path):
                return
            with open(path, "r", encoding="utf-8") as f:
                messages = json.load(f)
            # 完整历史保存供 LLM 上下文使用
            self._chat_messages = messages[-100:]
            # 仅渲染最近20条到 UI
            display_messages = self._chat_messages[-20:]
            for msg in display_messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                time_str = msg.get("time", "")
                if role == "user":
                    self.chat_display.append_user_msg(content, timestamp=time_str)
                elif role == "assistant":
                    self.chat_display.append_ai_msg(content, timestamp=time_str)
        except Exception as e:
            pass

    def clear_chat(self):
        """清空对话"""
        if self.chat_display:
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

        if self._chat_display_ready and self.chat_display:
            self.chat_display.append_system_msg("AI 主动说话")
            self.chat_display.append_ai_msg(text)
        else:
            self._pending_chat_messages.append(("system", "AI 主动说话", None))
            self._pending_chat_messages.append(("assistant", text, None))
        self._record_message("assistant", text)

        # 优化 #6: 统一通过 AnimationController 检测情绪
        if self._animation_controller:
            self._animation_controller.trigger_emotion_from_text(text)

        if self.backend:
            worker = TTSWorker(self.backend, text, parent=self)
            worker.audio_ready.connect(self._on_tts_audio_ready)
            worker.error.connect(lambda e: logger.info(f"[ChatPage] 主动说话 TTS 失败: {e}"))
            worker.finished.connect(lambda: self._cleanup_tts_worker(worker))
            self._tts_workers.append(worker)
            worker.start()

        self._save_chat_history()

    # ========== 主题刷新 ==========

    def refresh_theme(self):
        """主题切换时刷新所有硬编码样式"""
        c = get_colors()

        # 如果 _init_ui_content 尚未执行，只刷新 shell 阶段的控件
        if not self._chat_display_ready:
            # 刷新 Live2D 占位符
            if self._live2d_placeholder:
                self._live2d_placeholder.setStyleSheet(f"""
                    QLabel {{
                        color: {c.text_muted};
                        font-size: 14px;
                        background: transparent;
                        padding: 20px;
                    }}
                """)
            # 刷新对话区占位符
            if self._chat_placeholder:
                self._chat_placeholder.setStyleSheet(f"""
                    QLabel {{
                        color: {c.text_muted};
                        font-size: 14px;
                        background: transparent;
                        padding: 20px;
                    }}
                """)
            return

        # 刷新聊天区卡片
        if self._chat_card:
            self._chat_card.setStyleSheet(f"""
                QFrame#chatCard {{
                    background-color: {c.card_bg};
                    border: 1px solid {c.card_border};
                    border-radius: 16px;
                }}
            """)

        # 刷新 Web 显示主题
        if self.chat_display:
            self.chat_display.refresh_theme()

        # 刷新输入栏卡片
        if self._input_card:
            self._input_card.setStyleSheet(f"""
                QFrame#inputCard {{
                    background-color: {c.card_bg};
                    border: 1px solid {c.card_border};
                    border-radius: 14px;
                }}
            """)

        # 刷新多行输入框
        if self.input_field:
            self.input_field.refresh_theme()

        # 刷新发送按钮
        if self.send_btn:
            self.send_btn.setStyleSheet(f"""
                PushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {c.accent_gradient_start}, stop:1 {c.accent_gradient_end});
                    color: {c.text_on_accent};
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

        # 停止按钮样式已在 _set_streaming_state 中通过 send_btn 切换

        # 刷新TTS工具栏卡片
        if self._tts_card:
            self._tts_card.setStyleSheet(f"""
                QFrame#ttsCard {{
                    background-color: {c.card_bg};
                    border: 1px solid {c.card_border};
                    border-radius: 12px;
                }}
            """)

        # 刷新 QComboBox 样式
        if self.tts_combo:
            self._style_qcombobox(self.tts_combo, c)
        if self.voice_combo:
            self._style_qcombobox(self.voice_combo, c)

        # 刷新录音/实时语音按钮
        if self.record_btn:
            self.record_btn.setStyleSheet(f"""
                TogglePushButton {{
                    border-radius: 12px;
                    padding: 3px 10px;
                    border: 1px solid {c.card_border};
                    font-size: 12px;
                }}
                TogglePushButton:checked {{
                    background-color: {c.error};
                    color: {c.text_on_accent};
                    border: none;
                }}
            """)
        if self.realtime_btn:
            self.realtime_btn.setStyleSheet(f"""
                TogglePushButton {{
                    border-radius: 12px;
                    padding: 3px 10px;
                    border: 1px solid {c.card_border};
                    font-size: 12px;
                }}
                TogglePushButton:checked {{
                    background-color: {c.success};
                    color: {c.text_on_accent};
                    border: none;
                }}
            """)

        # 刷新搜索栏
        if self.search_bar:
            self.search_bar.refresh_theme()

        # 刷新会话管理器
        if self.session_manager:
            self.session_manager.refresh_theme()

        # 刷新 Live2D/VRM 切换按钮
        if hasattr(self, '_btn_live2d') and self._btn_live2d:
            self._btn_live2d.setStyleSheet(f"""
                QPushButton {{ background: {c.accent}; color: {c.text_on_accent}; border: none;
                    border-radius: 4px; padding: 4px 12px; font-size: 12px; font-weight: bold; }}
                QPushButton:checked {{ background: {c.accent}; color: {c.text_on_accent}; }}
                QPushButton:!checked {{ background: {c.card_bg}; color: {c.text_muted}; }}
                QPushButton:hover {{ background: {c.accent_hover}; }}
            """)
        if hasattr(self, '_btn_vrm') and self._btn_vrm:
            self._btn_vrm.setStyleSheet(f"""
                QPushButton {{ background: {c.card_bg}; color: {c.text_muted}; border: none;
                    border-radius: 4px; padding: 4px 12px; font-size: 12px; }}
                QPushButton:checked {{ background: {c.ai_bubble_accent}; color: {c.text_on_accent}; font-weight: bold; }}
                QPushButton:!checked {{ background: {c.card_bg}; color: {c.text_muted}; }}
                QPushButton:hover {{ background: {c.card_bg_hover}; }}
            """)

        # 刷新 VRM 变体按钮
        if hasattr(self, '_btn_vrm_variants') and self._btn_vrm_variants:
            for name, btn in self._btn_vrm_variants.items():
                btn.setStyleSheet(f"""
                    QPushButton {{ background: {c.card_bg}; color: {c.text_muted};
                        border: 1px solid {c.card_border}; border-radius: 3px;
                        padding: 2px 8px; font-size: 11px; }}
                    QPushButton:checked {{ background: {c.ai_bubble_accent}; color: {c.text_on_accent}; border-color: {c.ai_bubble_accent}; font-weight: bold; }}
                    QPushButton:hover {{ background: {c.card_bg_hover}; }}
                """)

        # 刷新 Live2D 占位符
        if self._live2d_placeholder:
            self._live2d_placeholder.setStyleSheet(f"""
                QLabel {{
                    color: {c.text_muted};
                    font-size: 16px;
                    background: transparent;
                }}
            """)

        # 刷新 TTS 模式按钮
        if self.tts_mode_btn:
            self.tts_mode_btn.setStyleSheet(f"""
                TogglePushButton {{
                    border-radius: 12px;
                    padding: 3px 10px;
                    border: 1px solid {c.card_border};
                    font-size: 12px;
                }}
                TogglePushButton:checked {{
                background-color: {c.accent};
                color: {c.text_on_accent};
                border: none;
            }}
        """)

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
                selection-color: {c.text_on_accent};
                padding: 4px;
                outline: none;
            }}
        """)
