"""
设置页面 — LLM/TTS/ASR/系统配置

设计参考: LM Studio / Jan.ai 设置页
- ScrollArea + HeaderCardWidget 分组卡片布局
- 每个配置区域独立卡片，可折叠
- API Key 显隐切换
- 主题切换（暗色/亮色）
"""

import os
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFormLayout, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from qfluentwidgets import (
    TitleLabel, SubtitleLabel, ComboBox, LineEdit,
    PushButton, FluentIcon, InfoBar, InfoBarPosition,
    SwitchButton, SpinBox, HeaderCardWidget, ScrollArea,
    ToolButton, BodyLabel, CaptionLabel, HyperlinkButton,
    StrongBodyLabel
)

from app.shared_config import PROJECT_DIR

from gugu_native.theme import apply_theme, get_global_qss, is_dark, apply_theme_by_id, get_current_theme_id, get_colors, register_theme_callback
from gugu_native.widgets.theme_selector import ThemeSelector

# ===== Provider 配置数据（统一从 shared_config 引入，不再本地维护副本）=====
from app.shared_config import PROVIDER_CONFIG, EDGE_VOICES

# Provider 显示名 -> 内部 key 的映射
_LABEL_TO_KEY = {v["label"]: k for k, v in PROVIDER_CONFIG.items()}

# 缓存文件路径
_CACHE_DIR = os.path.join(PROJECT_DIR, "app", "cache")
_LLM_PREFS_FILE = os.path.join(_CACHE_DIR, "llm_preferences.json")
_API_KEYS_FILE = os.path.join(_CACHE_DIR, "api_keys.json")
_TTS_PREFS_FILE = os.path.join(_CACHE_DIR, "tts_preferences.json")

# Edge TTS 音色列表已从 app/shared_config.py 引入（不再本地维护副本）


class SettingsPage(ScrollArea):
    """设置页面 — 卡片式分组布局"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsPage")
        self._backend = None
        self._api_key_visible = False  # API Key 显隐状态
        self._pending_tts_voice = None  # 待恢复的 TTS 音色 ID（异步加载完成后恢复用）
        self._dirty = False  # 是否有未保存的修改
        self._init_ui()
        self._load_saved_config()
        # 注册主题变更回调
        register_theme_callback(self.refresh_theme)

    @property
    def backend(self):
        """获取后端实例 — 与 ChatPage 等页面保持一致的访问方式"""
        if self._backend is None:
            main_window = self.window()
            if main_window and hasattr(main_window, 'backend'):
                self._backend = main_window.backend
        return self._backend

    def _init_ui(self):
        """初始化 UI — 卡片式布局（v1.9.78: 模型相关配置置顶）"""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        self.setWidget(container)

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)

        # 标题 + 统一保存按钮
        c = get_colors()
        title_row = QHBoxLayout()
        title = TitleLabel("设置")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        title_row.addWidget(title)
        title_row.addStretch()

        self._save_all_btn = PushButton("💾 保存所有设置")
        self._save_all_btn.clicked.connect(self._save_all_settings)
        self._save_all_btn.setStyleSheet(f"""
            PushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c.accent_gradient_start}, stop:1 {c.accent_gradient_end});
                color: {c.text_on_accent};
                border: none;
                border-radius: 8px;
                padding: 8px 24px;
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
            PushButton[dirty="true"] {{
                border: 2px solid {c.warning};
            }}
        """)
        title_row.addWidget(self._save_all_btn)
        main_layout.addLayout(title_row)

        # 获取当前主题颜色
        c = get_colors()

        # ================================================================
        # 第一组：模型相关配置（最常用，置顶）
        # ================================================================

        # === 1. 模型配置卡片 ===
        llm_card = HeaderCardWidget(self)
        llm_card.setTitle("模型配置")
        llm_content = QWidget()
        llm_layout = QFormLayout(llm_content)
        llm_layout.setContentsMargins(16, 8, 16, 16)
        llm_layout.setSpacing(12)

        self.llm_provider = ComboBox()
        provider_order = ["deepseek", "kimi", "glm", "qwen", "minimax", "doubao", "mimo", "openai", "anthropic", "ollama"]
        for key in provider_order:
            cfg = PROVIDER_CONFIG.get(key, {})
            self.llm_provider.addItem(cfg.get("label", key))
        self.llm_provider.currentIndexChanged.connect(self._on_provider_changed)
        llm_layout.addRow("LLM 引擎:", self.llm_provider)

        # API Key 行（输入框 + 显隐切换按钮）
        api_key_row = QHBoxLayout()
        api_key_row.setSpacing(4)
        self.api_key_input = LineEdit()
        self.api_key_input.setPlaceholderText("输入 API Key...")
        self.api_key_input.setEchoMode(LineEdit.EchoMode.Password)
        api_key_row.addWidget(self.api_key_input, stretch=1)

        self._toggle_key_btn = ToolButton(FluentIcon.VIEW)
        self._toggle_key_btn.setFixedSize(32, 32)
        self._toggle_key_btn.setToolTip("显示/隐藏 API Key")
        self._toggle_key_btn.clicked.connect(self._toggle_api_key_visibility)
        api_key_row.addWidget(self._toggle_key_btn)
        llm_layout.addRow("API Key:", api_key_row)

        self.model_combo = ComboBox()
        self.model_combo.setPlaceholderText("选择模型...")
        llm_layout.addRow("模型:", self.model_combo)

        self.base_url_input = LineEdit()
        self.base_url_input.setPlaceholderText("自定义 Base URL（可选）")
        llm_layout.addRow("Base URL:", self.base_url_input)

        # 连接脏标记
        for w in [self.llm_provider, self.api_key_input, self.model_combo, self.base_url_input]:
            if hasattr(w, 'currentIndexChanged'):
                w.currentIndexChanged.connect(self._mark_dirty)
            elif hasattr(w, 'textChanged'):
                w.textChanged.connect(self._mark_dirty)

        llm_card.viewLayout.addWidget(llm_content)
        main_layout.addWidget(llm_card)

        # === 2. 语音配置卡片 ===
        tts_card = HeaderCardWidget(self)
        tts_card.setTitle("语音配置")
        tts_content = QWidget()
        tts_layout = QFormLayout(tts_content)
        tts_layout.setContentsMargins(16, 8, 16, 16)
        tts_layout.setSpacing(12)

        self.tts_engine = ComboBox()
        self.tts_engine.addItems(["Edge TTS", "GPT-SoVITS", "MiMo TTS"])
        self.tts_engine.currentIndexChanged.connect(self._on_tts_engine_changed)
        tts_layout.addRow("TTS 引擎:", self.tts_engine)

        self.tts_voice = ComboBox()
        self.tts_voice.setPlaceholderText("选择音色...")
        self._populate_edge_voices()
        tts_layout.addRow("音色:", self.tts_voice)

        # MiMo TTS 专用配置
        self.mimo_tts_base_url = LineEdit()
        self.mimo_tts_base_url.setPlaceholderText("https://api.xiaomimimo.com/v1")
        self.mimo_tts_base_url.setText("https://api.xiaomimimo.com/v1")
        tts_layout.addRow("MiMo Base URL:", self.mimo_tts_base_url)

        for w in [self.tts_engine, self.tts_voice, self.mimo_tts_base_url]:
            if hasattr(w, 'currentIndexChanged'):
                w.currentIndexChanged.connect(self._mark_dirty)
            elif hasattr(w, 'textChanged'):
                w.textChanged.connect(self._mark_dirty)

        tts_card.viewLayout.addWidget(tts_content)
        main_layout.addWidget(tts_card)

        # === 3. 视觉/OCR 配置卡片 ===
        vision_card = HeaderCardWidget(self)
        vision_card.setTitle("视觉/OCR")
        vision_content = QWidget()
        vision_layout = QFormLayout(vision_content)
        vision_layout.setContentsMargins(16, 8, 16, 16)
        vision_layout.setSpacing(12)

        self.vision_provider = ComboBox()
        self.vision_provider.addItems(["RapidOCR (本地)", "MiniMax VL (云端)", "MiniCPM-V2 (本地GPU)", "MiMo Vision (云端)"])
        self.vision_provider.setCurrentIndex(0)
        self.vision_provider.currentIndexChanged.connect(self._on_vision_provider_changed)
        vision_layout.addRow("视觉引擎:", self.vision_provider)

        # MiniMax VL 配置
        self.vision_api_key = LineEdit()
        self.vision_api_key.setPlaceholderText("使用 LLM MiniMax Key（自动同步）")
        self.vision_api_key.setEchoMode(LineEdit.EchoMode.Password)
        vision_layout.addRow("MiniMax VL Key:", self.vision_api_key)

        self.vision_api_host = LineEdit()
        self.vision_api_host.setPlaceholderText("https://api.minimaxi.com")
        self.vision_api_host.setText("https://api.minimaxi.com")
        vision_layout.addRow("MiniMax VL Host:", self.vision_api_host)

        # MiMo Vision 配置
        self.mimo_vision_base_url = LineEdit()
        self.mimo_vision_base_url.setPlaceholderText("https://api.xiaomimimo.com/v1")
        self.mimo_vision_base_url.setText("https://api.xiaomimimo.com/v1")
        vision_layout.addRow("MiMo Vision URL:", self.mimo_vision_base_url)

        # MiniCPM-V2 配置
        self.vision_model_path = LineEdit()
        self.vision_model_path.setPlaceholderText("本地模型路径（如 openbmb/MiniCPM-V-2_6）")
        vision_layout.addRow("MiniCPM 模型:", self.vision_model_path)

        self.vision_int4_switch = SwitchButton("INT4 量化")
        self.vision_int4_switch.setChecked(False)
        vision_layout.addRow("INT4 量化:", self.vision_int4_switch)

        for w in [self.vision_provider, self.vision_api_key, self.vision_api_host, self.vision_model_path]:
            if hasattr(w, 'currentIndexChanged'):
                w.currentIndexChanged.connect(self._mark_dirty)
            elif hasattr(w, 'textChanged'):
                w.textChanged.connect(self._mark_dirty)

        vision_card.viewLayout.addWidget(vision_content)
        main_layout.addWidget(vision_card)

        # === 4. ASR 配置卡片 ===
        asr_card = HeaderCardWidget(self)
        asr_card.setTitle("语音识别 (ASR)")
        asr_content = QWidget()
        asr_layout = QFormLayout(asr_content)
        asr_layout.setContentsMargins(16, 8, 16, 16)
        asr_layout.setSpacing(12)

        self.asr_provider = ComboBox()
        self.asr_provider.addItems(["FunASR (本地GPU)", "MiMo ASR (云端)"])
        self.asr_provider.currentIndexChanged.connect(self._on_asr_provider_changed)
        asr_layout.addRow("ASR 引擎:", self.asr_provider)

        # MiMo ASR 专用配置
        self.mimo_asr_base_url = LineEdit()
        self.mimo_asr_base_url.setPlaceholderText("https://api.xiaomimimo.com/v1")
        self.mimo_asr_base_url.setText("https://api.xiaomimimo.com/v1")
        asr_layout.addRow("MiMo Base URL:", self.mimo_asr_base_url)

        for w in [self.asr_provider, self.mimo_asr_base_url]:
            if hasattr(w, 'currentIndexChanged'):
                w.currentIndexChanged.connect(self._mark_dirty)
            elif hasattr(w, 'textChanged'):
                w.textChanged.connect(self._mark_dirty)

        asr_card.viewLayout.addWidget(asr_content)
        main_layout.addWidget(asr_card)

        # ================================================================
        # 第二组：系统/外观配置（使用频率较低，放下面）
        # ================================================================

        # === 5. 外观配置卡片 ===
        appearance_card = HeaderCardWidget(self)
        appearance_card.setTitle("外观配置")
        appearance_content = QWidget()
        appearance_layout = QFormLayout(appearance_content)
        appearance_layout.setContentsMargins(16, 8, 16, 16)
        appearance_layout.setSpacing(12)

        self.theme_selector = ThemeSelector()
        self.theme_selector.theme_selected.connect(self._on_theme_selected)
        appearance_layout.addRow("主题:", self.theme_selector)

        # 恢复默认主题按钮
        self._reset_theme_btn = PushButton("恢复默认主题")
        self._reset_theme_btn.clicked.connect(lambda: self._on_theme_selected("dark"))
        self._reset_theme_btn.setStyleSheet(f"""
            PushButton {{
                background: transparent;
                color: {c.text_muted};
                border: 1px solid {c.card_border};
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 12px;
            }}
            PushButton:hover {{
                color: {c.text_secondary};
                border-color: {c.card_border_hover};
            }}
        """)
        appearance_layout.addRow("", self._reset_theme_btn)

        appearance_card.viewLayout.addWidget(appearance_content)
        main_layout.addWidget(appearance_card)

        # === 6. 系统配置卡片 ===
        system_card = HeaderCardWidget(self)
        system_card.setTitle("系统配置")
        system_content = QWidget()
        system_layout = QFormLayout(system_content)
        system_layout.setContentsMargins(16, 8, 16, 16)
        system_layout.setSpacing(12)

        self.autostart_switch = SwitchButton("开机自启")
        system_layout.addRow("开机自启:", self.autostart_switch)

        self.tray_switch = SwitchButton("最小化到托盘")
        self.tray_switch.setChecked(True)
        system_layout.addRow("系统托盘:", self.tray_switch)

        self.proactive_switch = SwitchButton("AI 主动说话")
        self.proactive_switch.checkedChanged.connect(self._on_proactive_toggled)
        system_layout.addRow("主动说话:", self.proactive_switch)

        self.proactive_interval = SpinBox()
        self.proactive_interval.setRange(10, 600)
        self.proactive_interval.setValue(60)
        self.proactive_interval.setSuffix(" 秒")
        self.proactive_interval.valueChanged.connect(self._on_proactive_interval_changed)
        system_layout.addRow("主动说话间隔:", self.proactive_interval)

        system_card.viewLayout.addWidget(system_content)
        main_layout.addWidget(system_card)

        # === 7. 关于卡片 ===
        about_card = HeaderCardWidget(self)
        about_card.setTitle("关于")
        about_content = QWidget()
        about_layout = QVBoxLayout(about_content)
        about_layout.setContentsMargins(16, 8, 16, 16)
        about_layout.setSpacing(8)

        from app.version import VERSION
        version_label = StrongBodyLabel(f"咕咕嘎嘎 AI-VTuber v{VERSION}")
        about_layout.addWidget(version_label)

        desc_label = CaptionLabel("AI 实时对话伴侣 — 声音克隆训练 + 深度记忆 + Live2D 形象")
        about_layout.addWidget(desc_label)

        github_btn = HyperlinkButton(
            "https://github.com/xzt238/ai-vtuber-fixed",
            "GitHub 仓库",
            self,
        )
        about_layout.addWidget(github_btn)

        check_update_btn = PushButton("🔄 检查更新")
        check_update_btn.clicked.connect(self._check_for_updates)
        self._check_update_btn = check_update_btn
        check_update_btn.setStyleSheet(f"""
            PushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c.success}, stop:1 {c.success_hover});
                color: {c.text_on_accent};
                border: none;
                border-radius: 8px;
                padding: 6px 20px;
                font-weight: 500;
            }}
            PushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c.success_hover}, stop:1 {c.success_pressed});
            }}
        """)
        about_layout.addWidget(check_update_btn)

        about_card.viewLayout.addWidget(about_content)
        main_layout.addWidget(about_card)

        # 底部弹性空间
        main_layout.addStretch(1)

    # ========== 主题刷新 ==========

    def refresh_theme(self):
        """主题切换时刷新所有硬编码样式"""
        c = get_colors()

        # 统一保存按钮
        if hasattr(self, '_save_all_btn') and self._save_all_btn:
            self._save_all_btn.setStyleSheet(f"""
                PushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {c.accent_gradient_start}, stop:1 {c.accent_gradient_end});
                    color: {c.text_on_accent};
                    border: none;
                    border-radius: 8px;
                    padding: 8px 24px;
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
                PushButton[dirty="true"] {{
                    border: 2px solid {c.warning};
                }}
            """)

        # 检查更新按钮 — success 渐变
        if hasattr(self, '_check_update_btn') and self._check_update_btn:
            self._check_update_btn.setStyleSheet(f"""
                PushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {c.success}, stop:1 {c.success_hover});
                    color: {c.text_on_accent};
                    border: none;
                    border-radius: 8px;
                    padding: 6px 20px;
                    font-weight: 500;
                }}
                PushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {c.success_hover}, stop:1 {c.success_pressed});
                }}
            """)

        # 恢复默认主题按钮
        if hasattr(self, '_reset_theme_btn') and self._reset_theme_btn:
            self._reset_theme_btn.setStyleSheet(f"""
                PushButton {{
                    background: transparent;
                    color: {c.text_muted};
                    border: 1px solid {c.card_border};
                    border-radius: 6px;
                    padding: 4px 12px;
                    font-size: 12px;
                }}
                PushButton:hover {{
                    color: {c.text_secondary};
                    border-color: {c.card_border_hover};
                }}
            """)

    # ========== 主题切换 ==========

    def _on_theme_selected(self, theme_id: str):
        """主题选择回调 — 应用主题、持久化偏好、刷新全局样式

        Args:
            theme_id: 选中的主题 ID
        """
        from gugu_native.theme import _ensure_manager

        # 应用主题
        apply_theme_by_id(theme_id)

        # 保存偏好到 JSON
        manager = _ensure_manager()
        manager.save_preferences()

        # 刷新全局样式
        main_window = self.window()
        if main_window:
            main_window.setStyleSheet(get_global_qss())
            # 刷新各页面的硬编码样式
            for page_name in ['chat_page', 'train_page', 'memory_page', 'model_download_page']:
                page = getattr(main_window, page_name, None)
                if page and hasattr(page, 'refresh_theme'):
                    try:
                        page.refresh_theme()
                    except Exception:
                        pass

        # 刷新主题选择器自身
        self.theme_selector.set_current(theme_id)
        self.theme_selector.refresh_theme()

    # ========== API Key 显隐 ==========

    def _toggle_api_key_visibility(self):
        """切换 API Key 显示/隐藏"""
        self._api_key_visible = not self._api_key_visible
        if self._api_key_visible:
            self.api_key_input.setEchoMode(LineEdit.EchoMode.Normal)
            self._toggle_key_btn.setIcon(FluentIcon.HIDE)
            self._toggle_key_btn.setToolTip("隐藏 API Key")
        else:
            self.api_key_input.setEchoMode(LineEdit.EchoMode.Password)
            self._toggle_key_btn.setIcon(FluentIcon.VIEW)
            self._toggle_key_btn.setToolTip("显示 API Key")

    # ========== 统一保存 ==========

    def _mark_dirty(self, *args):
        """标记配置已修改 — 按钮边框变橙色提示"""
        self._dirty = True
        if hasattr(self, '_save_all_btn') and self._save_all_btn:
            self._save_all_btn.setProperty("dirty", True)
            self._save_all_btn.style().unpolish(self._save_all_btn)
            self._save_all_btn.style().polish(self._save_all_btn)

    def _save_all_settings(self):
        """统一保存所有配置"""
        errors = []
        # LLM
        try:
            self._save_llm_config()
        except Exception as e:
            errors.append(f"LLM: {e}")
        # TTS
        try:
            self._save_tts_config()
        except Exception as e:
            errors.append(f"TTS: {e}")
        # Vision
        try:
            self._save_vision_config()
        except Exception as e:
            errors.append(f"Vision: {e}")
        # ASR
        try:
            self._save_asr_config()
        except Exception as e:
            errors.append(f"ASR: {e}")

        self._dirty = False
        if hasattr(self, '_save_all_btn') and self._save_all_btn:
            self._save_all_btn.setProperty("dirty", False)
            self._save_all_btn.style().unpolish(self._save_all_btn)
            self._save_all_btn.style().polish(self._save_all_btn)

        if errors:
            InfoBar.error(
                title="部分保存失败",
                content="; ".join(errors),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=4000
            )
        else:
            InfoBar.success(
                title="保存成功",
                content="所有设置已保存",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )

    # ========== 检查更新 ==========

    def _check_for_updates(self):
        """触发更新检查"""
        main_window = self.window()
        if hasattr(main_window, 'update_manager'):
            main_window.update_manager.check_for_updates()
            InfoBar.info(
                title="检查中",
                content="正在检查更新...",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000,
            )

    # ========== LLM 配置逻辑 ==========

    def _get_current_provider_key(self) -> str:
        """获取当前选中的 provider 内部 key"""
        label = self.llm_provider.currentText()
        return _LABEL_TO_KEY.get(label, "minimax")

    def _on_provider_changed(self, index: int):
        """Provider 切换 - 加载对应的模型列表和默认值"""
        provider_key = self._get_current_provider_key()
        cfg = PROVIDER_CONFIG.get(provider_key, {})

        # 更新模型列表
        self.model_combo.clear()
        models = cfg.get("models", [])
        if models:
            self.model_combo.addItems(models)
        else:
            if provider_key == "ollama":
                self._load_ollama_models()
            self.model_combo.addItem(cfg.get("defaultModel", ""))

        # 更新 Base URL
        self.base_url_input.setText(cfg.get("baseUrl", ""))
        self.api_key_input.setPlaceholderText(cfg.get("keyPlaceholder", "输入 API Key..."))

        # 加载已保存的 API Key
        self._load_api_key_for_provider(provider_key)

    def _load_ollama_models(self):
        """从 Ollama API 动态获取模型列表（异步，不阻塞 UI）"""
        from PySide6.QtCore import QThread

        class _OllamaFetchWorker(QThread):
            finished = Signal(list)  # 模型名列表

            def run(self):
                try:
                    import requests
                    resp = requests.get("http://localhost:11434/api/tags", timeout=3)
                    if resp.status_code == 200:
                        data = resp.json()
                        models = [m.get("name", "") for m in data.get("models", [])]
                        self.finished.emit(models)
                        return
                except Exception:
                    pass
                self.finished.emit([])

        self._ollama_worker = _OllamaFetchWorker(self)
        self._ollama_worker.finished.connect(self._on_ollama_models_fetched)
        self._ollama_worker.start()

    def _on_ollama_models_fetched(self, models: list):
        """Ollama 模型列表获取完成"""
        if models:
            self.model_combo.addItems(models)
        else:
            self.model_combo.addItem("qwen3:8b")

    def _load_api_key_for_provider(self, provider_key: str):
        """加载指定 provider 的已保存 API Key"""
        try:
            if os.path.exists(_API_KEYS_FILE):
                with open(_API_KEYS_FILE, "r", encoding="utf-8") as f:
                    keys = json.load(f)
                saved_key = keys.get(provider_key, "")
                self.api_key_input.setText(saved_key)
            else:
                self.api_key_input.setText("")
        except Exception:
            self.api_key_input.setText("")

    def _save_llm_config(self):
        """保存 LLM 配置"""
        provider_key = self._get_current_provider_key()
        api_key = self.api_key_input.text().strip()
        model = self.model_combo.currentText()
        base_url = self.base_url_input.text().strip()
        cfg = PROVIDER_CONFIG.get(provider_key, {})

        if not base_url:
            base_url = cfg.get("baseUrl", "")

        # 1. 保存 API Key
        self._save_api_key(provider_key, api_key)

        # 2. 保存 LLM 偏好
        prefs = {}
        if os.path.exists(_LLM_PREFS_FILE):
            try:
                with open(_LLM_PREFS_FILE, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
            except Exception:
                prefs = {}

        prefs["provider"] = provider_key
        prefs["model"] = model
        if "provider_configs" not in prefs:
            prefs["provider_configs"] = {}
        prefs["provider_configs"][provider_key] = {
            "base_url": base_url,
            "model": model,
        }

        try:
            os.makedirs(_CACHE_DIR, exist_ok=True)
            with open(_LLM_PREFS_FILE, "w", encoding="utf-8") as f:
                json.dump(prefs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            InfoBar.error(
                title="保存失败",
                content=f"无法写入配置文件: {e}",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return

        # 3. 更新后端配置并重建引擎
        self._apply_llm_config_to_backend(provider_key, api_key, model, base_url)

        InfoBar.success(
            title="保存成功",
            content=f"LLM 配置已保存: {cfg.get('label', provider_key)} / {model}",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=2000
        )

    def _save_api_key(self, provider_key: str, api_key: str):
        """保存 API Key 到 api_keys.json"""
        keys = {}
        if os.path.exists(_API_KEYS_FILE):
            try:
                with open(_API_KEYS_FILE, "r", encoding="utf-8") as f:
                    keys = json.load(f)
            except Exception:
                keys = {}

        if api_key:
            keys[provider_key] = api_key
        elif provider_key in keys:
            del keys[provider_key]

        try:
            os.makedirs(_CACHE_DIR, exist_ok=True)
            with open(_API_KEYS_FILE, "w", encoding="utf-8") as f:
                json.dump(keys, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[SettingsPage] 保存 API Key 失败: {e}")

    def _apply_llm_config_to_backend(self, provider_key: str, api_key: str, model: str, base_url: str):
        """将 LLM 配置应用到后端（引擎重建在后台线程执行）"""
        backend = self.backend
        if not backend:
            return

        llm_section = backend.config.config.setdefault("llm", {})
        old_provider = llm_section.get("provider", "")
        llm_section["provider"] = provider_key

        provider_section = llm_section.setdefault(provider_key, {})
        if api_key:
            provider_section["api_key"] = api_key
        if model:
            provider_section["model"] = model
        if base_url:
            provider_section["base_url"] = base_url

        if model:
            llm_section["model"] = model

        if provider_key == "minimax" and api_key:
            vision_section = backend.config.config.setdefault("vision", {})
            minimax_vl = vision_section.setdefault("minimax_vl", {})
            minimax_vl["api_key"] = api_key

        # MiMo Key 分发: 一个 key 同时供 LLM/TTS/ASR/Vision 使用
        if provider_key == "mimo" and api_key:
            asr_section = backend.config.config.setdefault("asr", {})
            asr_mimo = asr_section.setdefault("mimo", {})
            asr_mimo["api_key"] = api_key
            tts_section = backend.config.config.setdefault("tts", {})
            tts_mimo = tts_section.setdefault("mimo", {})
            tts_mimo["api_key"] = api_key
            vision_section = backend.config.config.setdefault("vision", {})
            vision_mimo = vision_section.setdefault("mimo_vision", {})
            vision_mimo["api_key"] = api_key

        # 判断是否需要重建 LLM 引擎
        need_rebuild = False
        if hasattr(backend, '_lazy_modules'):
            llm = backend._lazy_modules.get('llm')

            if old_provider and old_provider != provider_key:
                need_rebuild = True
            elif llm is not None:
                llm_name = getattr(llm, 'name', '').lower()
                expected_names = {
                    'minimax': 'minimax', 'anthropic': 'anthropic',
                    'deepseek': 'openai', 'kimi': 'openai', 'glm': 'openai',
                    'qwen': 'openai', 'doubao': 'openai', 'mimo': 'openai',
                    'openai': 'openai', 'ollama': 'openai'
                }
                expected_name = expected_names.get(provider_key, '')
                if expected_name and llm_name != expected_name:
                    need_rebuild = True

            if need_rebuild:
                # KI-013 FIX: 使用线程安全的 rebuild_llm() 方法
                # 旧方式: 直接 pop _lazy_modules + 后台线程触发懒加载（有竞态风险）
                # 新方式: 调用后端提供的线程安全 rebuild 方法
                from PySide6.QtCore import QThread

                class _LLMRebuildWorker(QThread):
                    error = Signal(str)

                    def __init__(self, backend_ref):
                        super().__init__()
                        self._backend_ref = backend_ref

                    def run(self):
                        try:
                            result = self._backend_ref.rebuild_llm()
                            if not result:
                                self.error.emit("LLM 引擎重建失败")
                        except Exception as e:
                            self.error.emit(str(e))

                self._llm_rebuild_worker = _LLMRebuildWorker(backend)
                self._llm_rebuild_worker.error.connect(
                    lambda e: print(f"[SettingsPage] LLM 引擎重建失败: {e}")
                )
                self._llm_rebuild_worker.start()

    # ========== TTS 配置逻辑 ==========

    def _populate_edge_voices(self):
        """填充 Edge TTS 音色列表"""
        self.tts_voice.clear()
        for voice_id, label in EDGE_VOICES:
            self.tts_voice.addItem(f"{label} ({voice_id})", userData=voice_id)

    def _populate_gptsovits_voices(self):
        """填充 GPT-SoVITS 音色列表（后台加载，不阻塞 UI）"""
        self.tts_voice.clear()
        backend = self.backend
        if not backend:
            self.tts_voice.addItem("默认音色", userData="default")
            return

        # 先添加占位提示
        self.tts_voice.addItem("加载中...", userData="")

        from PySide6.QtCore import QThread

        class _VoiceFetchWorker(QThread):
            finished = Signal(list)  # [(label, value), ...]

            def __init__(self, backend_ref):
                super().__init__()
                self._backend_ref = backend_ref

            def run(self):
                voices = []
                try:
                    tts = self._backend_ref.tts
                    if tts and hasattr(tts, 'get_voices'):
                        raw_voices = tts.get_voices()
                        if raw_voices:
                            for v in raw_voices:
                                if isinstance(v, dict):
                                    value = str(v.get('value', v.get('name', '')))
                                    label = str(v.get('label', value))
                                    voices.append((label, value))
                                else:
                                    voices.append((str(v), str(v)))
                            self.finished.emit(voices)
                            return
                except Exception as e:
                    print(f"[SettingsPage] 获取 GPT-SoVITS 音色失败: {e}")

                # 回退: 尝试从 trainer 获取项目列表
                try:
                    from app.trainer.manager import TrainingManager
                    trainer = TrainingManager()
                    projects = trainer.list_projects()
                    if projects:
                        for p in projects:
                            name = p.get('name', '') if isinstance(p, dict) else str(p)
                            voices.append((name, name))
                except Exception:
                    pass

                self.finished.emit(voices)

        self._voice_fetch_worker = _VoiceFetchWorker(backend)
        self._voice_fetch_worker.finished.connect(self._on_gptsovits_voices_fetched)
        self._voice_fetch_worker.start()

    def _on_gptsovits_voices_fetched(self, voices: list):
        """GPT-SoVITS 音色列表获取完成 — 填充列表后恢复已保存的音色"""
        self.tts_voice.clear()
        if voices:
            for label, value in voices:
                self.tts_voice.addItem(label, userData=value)
        else:
            self.tts_voice.addItem("默认音色", userData="default")

        # 音色列表就绪后，尝试恢复之前保存的音色
        self._restore_tts_voice_after_populate()

    def _on_tts_engine_changed(self, index: int):
        """TTS 引擎切换 — 动态填充音色列表"""
        engine = self.tts_engine.currentText()
        if engine == "Edge TTS":
            self._populate_edge_voices()
            self.mimo_tts_base_url.setEnabled(False)
        elif engine == "GPT-SoVITS":
            self._populate_gptsovits_voices()
            self.mimo_tts_base_url.setEnabled(False)
        elif engine == "MiMo TTS":
            self._populate_mimo_tts_voices()
            self.mimo_tts_base_url.setEnabled(True)

        # 音色列表填充后，尝试恢复待恢复的音色（Edge/MiMo 是同步的，GPT-SoVITS 是异步的）
        self._restore_tts_voice_after_populate()

    def _restore_tts_voice_after_populate(self):
        """音色列表填充后，恢复待恢复的音色（处理异步加载的 GPT-SoVITS 等引擎）

        在以下时机调用：
        1. _on_tts_engine_changed — Edge TTS / MiMo TTS 音色列表同步填充后
        2. _on_gptsovits_voices_fetched — GPT-SoVITS 音色列表异步加载完成后
        """
        if not self._pending_tts_voice:
            return

        voice_id = self._pending_tts_voice

        # 先尝试按 userData 查找
        for i in range(self.tts_voice.count()):
            if str(self.tts_voice.itemData(i) or "") == voice_id:
                self.tts_voice.setCurrentIndex(i)
                self._pending_tts_voice = None  # 已恢复，清除
                return

        # 再尝试按文本查找
        voice_idx = self.tts_voice.findText(voice_id)
        if voice_idx >= 0:
            self.tts_voice.setCurrentIndex(voice_idx)
            self._pending_tts_voice = None  # 已恢复，清除

    def _populate_mimo_tts_voices(self):
        """填充 MiMo TTS 预置音色列表"""
        self.tts_voice.clear()
        mimo_voices = [
            ("mimo_default", "默认音色 (冰糖)"),
            ("冰糖", "中文女声 (冰糖)"),
            ("茉莉", "中文女声 (茉莉)"),
            ("苏打", "中文男声 (苏打)"),
            ("白桦", "中文男声 (白桦)"),
            ("Mia", "英文女声 (Mia)"),
            ("Chloe", "英文女声 (Chloe)"),
            ("Milo", "英文男声 (Milo)"),
            ("Dean", "英文男声 (Dean)"),
        ]
        for voice_id, label in mimo_voices:
            self.tts_voice.addItem(f"{label}", userData=voice_id)

    def _get_current_tts_provider(self) -> str:
        """获取当前 TTS 引擎内部标识"""
        engine = self.tts_engine.currentText()
        return {"Edge TTS": "edge", "GPT-SoVITS": "gptsovits", "MiMo TTS": "mimo"}.get(engine, "edge")

    def _get_current_voice_id(self) -> str:
        """获取当前选中的音色 ID（userData 优先，fallback 到文本）"""
        idx = self.tts_voice.currentIndex()
        if idx >= 0:
            user_data = self.tts_voice.itemData(idx)
            if user_data:
                return str(user_data)
        return self.tts_voice.currentText()

    def _save_tts_config(self):
        """保存 TTS 配置（持久化 + 后端同步）

        为所有引擎保存音色到 provider_configs，确保切换引擎后音色不丢失：
        - Edge TTS: 保存 voice ID（如 zh-CN-XiaoxiaoNeural）
        - GPT-SoVITS: 保存 voice/project ID
        - MiMo TTS: 保存 voice ID + base_url
        """
        engine = self.tts_engine.currentText()
        voice_id = self._get_current_voice_id()
        provider = self._get_current_tts_provider()

        # 1. 持久化到 tts_preferences.json（含所有引擎的 provider_configs）
        tts_prefs = {
            "engine": engine,
            "provider": provider,
            "voice": voice_id,
        }

        # 为当前引擎保存完整配置到 provider_configs
        provider_configs = {}
        if provider == "edge":
            provider_configs["edge"] = {
                "voice": voice_id,
            }
        elif provider == "gptsovits":
            provider_configs["gptsovits"] = {
                "voice": voice_id,
                "project": voice_id,  # GPT-SoVITS voice ID 就是 project name
            }
        elif provider == "mimo":
            mimo_url = self.mimo_tts_base_url.text().strip()
            provider_configs["mimo"] = {
                "base_url": mimo_url or "https://api.xiaomimimo.com/v1",
                "model": "mimo-v2.5-tts",
                "voice": voice_id,
            }

        # 合并到现有的 provider_configs 中（保留其他引擎的配置）
        existing_prefs = {}
        if os.path.exists(_TTS_PREFS_FILE):
            try:
                with open(_TTS_PREFS_FILE, "r", encoding="utf-8") as f:
                    existing_prefs = json.load(f)
            except Exception:
                pass
        existing_provider_configs = existing_prefs.get("provider_configs", {})
        # 用当前引擎的配置覆盖，其他引擎的配置保留
        existing_provider_configs.update(provider_configs)
        if existing_provider_configs:
            tts_prefs["provider_configs"] = existing_provider_configs

        try:
            os.makedirs(_CACHE_DIR, exist_ok=True)
            with open(_TTS_PREFS_FILE, "w", encoding="utf-8") as f:
                json.dump(tts_prefs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[SettingsPage] 保存 TTS 偏好失败: {e}")

        # 2. 更新后端配置并重建 TTS 引擎（后台线程执行）
        backend = self.backend
        if backend:
            tts_section = backend.config.config.setdefault("tts", {})
            tts_section["provider"] = provider

            if voice_id:
                sub = tts_section.setdefault(provider, {})
                sub["voice"] = voice_id
                if provider == "gptsovits":
                    sub["project"] = voice_id  # GPT-SoVITS voice ID 就是 project name

            # MiMo TTS: 同步 base_url 到后端配置
            if provider == "mimo":
                mimo_sub = tts_section.setdefault("mimo", {})
                mimo_url = self.mimo_tts_base_url.text().strip()
                if mimo_url:
                    mimo_sub["base_url"] = mimo_url
                mimo_sub["voice"] = voice_id

            if hasattr(backend, '_lazy_modules') and 'tts' in backend._lazy_modules:
                # KI-013 FIX: 使用线程安全的 rebuild_tts() 方法
                # v1.11.15 FIX: 不再 rebuild 后额外调用 set_voice/set_project
                # 因为 rebuild_tts() 会根据 config["tts"] 创建新引擎，
                # 而 config["tts"] 已在上方更新了 provider/voice/project，
                # 所以重建后的引擎已经包含了正确的音色配置。
                # 额外调用 set_project() 反而会重置 GPT-SoVITS 的 pipeline。
                from PySide6.QtCore import QThread

                class _TTSRebuildWorker(QThread):
                    error = Signal(str)

                    def __init__(self, backend_ref, voice_id_ref, provider_ref):
                        super().__init__()
                        self._backend_ref = backend_ref
                        self._voice_id = voice_id_ref
                        self._provider = provider_ref

                    def run(self):
                        try:
                            result = self._backend_ref.rebuild_tts()
                            if not result:
                                self.error.emit("TTS 引擎重建失败")
                                return
                            # 不再额外调用 set_voice/set_project
                            # rebuild_tts() 已根据更新后的 config 创建了正确配置的引擎
                        except Exception as e:
                            self.error.emit(str(e))

                self._tts_rebuild_worker = _TTSRebuildWorker(backend, voice_id, provider)
                self._tts_rebuild_worker.error.connect(
                    lambda e: print(f"[SettingsPage] TTS 引擎重建失败: {e}")
                )
                self._tts_rebuild_worker.start()

        # 3. 同步 ChatPage 的 TTS 控件
        main_window = self.window()
        if main_window and hasattr(main_window, 'chat_page'):
            chat = main_window.chat_page
            if hasattr(chat, 'sync_tts_from_settings'):
                chat.sync_tts_from_settings(engine, voice_id)

        InfoBar.success(
            title="保存成功",
            content=f"TTS 配置已保存: {engine} / {voice_id}",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=2000
        )

    def _load_tts_prefs(self):
        """从 tts_preferences.json 加载 TTS 偏好

        恢复引擎选择 → 触发音色列表填充 → 恢复音色选择 → 恢复各引擎子配置
        对于异步加载音色的引擎（GPT-SoVITS），音色恢复延迟到列表加载完成后执行。
        """
        try:
            if not os.path.exists(_TTS_PREFS_FILE):
                return

            with open(_TTS_PREFS_FILE, "r", encoding="utf-8") as f:
                prefs = json.load(f)

            engine = prefs.get("engine", "Edge TTS")
            voice_id = prefs.get("voice", "")

            # 设置引擎（会触发 _on_tts_engine_changed → 填充音色列表）
            idx = self.tts_engine.findText(engine)
            if idx >= 0:
                self.tts_engine.setCurrentIndex(idx)

            # 设置音色（引擎切换后音色列表已填充）
            if voice_id:
                # 保存待恢复的音色 ID（供异步加载完成后使用）
                self._pending_tts_voice = voice_id

                # 先尝试按 userData 查找（Edge TTS / MiMo TTS 的音色是同步填充的）
                for i in range(self.tts_voice.count()):
                    if str(self.tts_voice.itemData(i) or "") == voice_id:
                        self.tts_voice.setCurrentIndex(i)
                        self._pending_tts_voice = None  # 已恢复，清除
                        break
                else:
                    # 再尝试按文本查找
                    voice_idx = self.tts_voice.findText(voice_id)
                    if voice_idx >= 0:
                        self.tts_voice.setCurrentIndex(voice_idx)
                        self._pending_tts_voice = None  # 已恢复，清除
                    # GPT-SoVITS 的音色列表是异步加载的，此时可能还是空的
                    # _pending_tts_voice 保留，等 _on_gptsovits_voices_fetched 回调时恢复

            # 恢复各引擎的子配置（从 provider_configs 中读取）
            provider_configs = prefs.get("provider_configs", {})

            # MiMo base_url
            mimo_cfg = provider_configs.get("mimo", {})
            if mimo_cfg.get("base_url"):
                self.mimo_tts_base_url.setText(mimo_cfg["base_url"])

        except Exception as e:
            print(f"[SettingsPage] 加载 TTS 偏好失败: {e}")

    # ========== 加载已保存的配置 ==========

    def _load_saved_config(self):
        """从 llm_preferences.json 和 api_keys.json 加载已保存的配置"""
        try:
            prefs = {}
            if os.path.exists(_LLM_PREFS_FILE):
                with open(_LLM_PREFS_FILE, "r", encoding="utf-8") as f:
                    prefs = json.load(f)

            saved_provider = prefs.get("provider", "minimax")
            saved_model = prefs.get("model", "")

            provider_cfg = PROVIDER_CONFIG.get(saved_provider, {})
            label = provider_cfg.get("label", saved_provider)
            idx = self.llm_provider.findText(label)
            if idx >= 0:
                self.llm_provider.setCurrentIndex(idx)

            provider_configs = prefs.get("provider_configs", {})
            saved_config = provider_configs.get(saved_provider, {})
            base_url = saved_config.get("base_url", provider_cfg.get("baseUrl", ""))
            self.base_url_input.setText(base_url)

            if saved_model:
                model_idx = self.model_combo.findText(saved_model)
                if model_idx >= 0:
                    self.model_combo.setCurrentIndex(model_idx)
                else:
                    self.model_combo.addItem(saved_model)
                    self.model_combo.setCurrentText(saved_model)

            self._load_api_key_for_provider(saved_provider)

        except Exception as e:
            print(f"[SettingsPage] 加载已保存配置失败: {e}")

        # 加载 TTS 偏好
        self._load_tts_prefs()

        # 加载 ASR 偏好
        self._load_asr_prefs()

    def on_backend_ready(self):
        """后端就绪回调 - 从后端同步当前配置

        优先级: 偏好文件 (app/cache/*.json) > config.yaml
        所有模块（LLM/TTS/ASR/Vision）统一遵循此优先级，
        避免后端就绪时覆盖用户已保存的偏好。

        注意: backend.config 是 Config 对象，其 .get() 方法使用点号分隔的扁平查找，
        无法直接获取嵌套字典。需要通过 backend.config.config（原始 dict）访问。
        """
        try:
            backend = self.backend
            if not backend:
                return
            if hasattr(backend, 'config'):
                # 注意: backend.config 是 Config 对象，
                # config.get('llm') 用扁平查找会返回 {}（因为 'llm' 不是叶子节点）
                # 必须用 config.config.get('llm') 访问原始嵌套字典
                raw_config = backend.config.config if hasattr(backend.config, 'config') else {}

                # ===== 同步 LLM 配置（优先用偏好文件）=====
                if not os.path.exists(_LLM_PREFS_FILE):
                    # 偏好文件不存在 → 从 config.yaml 恢复
                    llm_cfg = raw_config.get('llm', {})
                    provider = llm_cfg.get('provider', 'minimax')
                    model = llm_cfg.get('model', '')
                    provider_cfg = PROVIDER_CONFIG.get(provider, {})
                    label = provider_cfg.get("label", provider)
                    idx = self.llm_provider.findText(label)
                    if idx >= 0:
                        self.llm_provider.setCurrentIndex(idx)
                    if model:
                        model_idx = self.model_combo.findText(model)
                        if model_idx >= 0:
                            self.model_combo.setCurrentIndex(model_idx)
                # 偏好文件存在 → _load_saved_config 已在 __init__ 中恢复，不覆盖

                # ===== 同步 TTS 配置（优先用偏好文件）=====
                if not os.path.exists(_TTS_PREFS_FILE):
                    tts_cfg = raw_config.get('tts', {})
                    tts_provider = tts_cfg.get("provider", "edge")
                    engine_map = {"edge": "Edge TTS", "gptsovits": "GPT-SoVITS", "mimo": "MiMo TTS"}
                    engine_label = engine_map.get(tts_provider, "Edge TTS")
                    idx = self.tts_engine.findText(engine_label)
                    if idx >= 0:
                        self.tts_engine.setCurrentIndex(idx)
                    voice = tts_cfg.get(tts_provider, {}).get("voice", "")
                    if voice:
                        for i in range(self.tts_voice.count()):
                            if str(self.tts_voice.itemData(i) or "") == voice:
                                self.tts_voice.setCurrentIndex(i)
                                break
                    # 恢复 MiMo base_url from config.yaml
                    if tts_provider == "mimo":
                        mimo_url = tts_cfg.get("mimo", {}).get("base_url", "")
                        if mimo_url:
                            self.mimo_tts_base_url.setText(mimo_url)
                else:
                    self._load_tts_prefs()

                # ===== 同步 ASR 配置（优先用偏好文件）=====
                asr_prefs_file = os.path.join(_CACHE_DIR, "asr_preferences.json")
                if not os.path.exists(asr_prefs_file):
                    asr_cfg = raw_config.get('asr', {})
                    asr_provider = asr_cfg.get("provider", "funasr")
                    provider_map = {"funasr": 0, "mimo": 1}
                    self.asr_provider.setCurrentIndex(provider_map.get(asr_provider, 0))
                    if asr_provider == "mimo":
                        mimo_url = asr_cfg.get("mimo", {}).get("base_url", "")
                        if mimo_url:
                            self.mimo_asr_base_url.setText(mimo_url)
                else:
                    self._load_asr_prefs()

                # ===== 同步视觉配置（优先用偏好文件）=====
                vision_cfg = raw_config.get('vision', {})
                vision_prefs_file = os.path.join(_CACHE_DIR, "vision_preferences.json")
                vision_provider_idx = 0  # 默认 RapidOCR
                if not os.path.exists(vision_prefs_file):
                    vision_provider = vision_cfg.get('default_provider', 'rapidocr')
                    vision_provider_idx = {"rapidocr": 0, "minimax_vl": 1, "minicpm": 2, "mimo_vision": 3}.get(vision_provider, 0)
                    self.vision_provider.setCurrentIndex(vision_provider_idx)
                    # MiniMax VL key 共享 LLM key
                    minimax_vl_cfg = vision_cfg.get('minimax_vl', {})
                    vl_key = minimax_vl_cfg.get('api_key', '')
                    if vl_key:
                        self.vision_api_key.setText(vl_key)
                    vl_host = minimax_vl_cfg.get('api_host', '')
                    if vl_host:
                        self.vision_api_host.setText(vl_host)

                    # v1.9.76: 同步 MiniCPM-V2 配置
                    minicpm_cfg = vision_cfg.get('minicpm', {})
                    model_path = minicpm_cfg.get('model_id_or_path', '')
                    if model_path:
                        self.vision_model_path.setText(model_path)
                    if minicpm_cfg.get('int4', False):
                        self.vision_int4_switch.setChecked(True)

                    # 同步 MiMo Vision base_url
                    if vision_provider == "mimo_vision":
                        mimo_url = vision_cfg.get("mimo_vision", {}).get("base_url", "")
                        if mimo_url:
                            self.mimo_vision_base_url.setText(mimo_url)
                else:
                    # 从偏好文件恢复
                    try:
                        with open(vision_prefs_file, "r", encoding="utf-8") as f:
                            vprefs = json.load(f)
                        vp = vprefs.get("default_provider", "rapidocr")
                        vision_provider_idx = {"rapidocr": 0, "minimax_vl": 1, "minicpm": 2, "mimo_vision": 3}.get(vp, 0)
                        self.vision_provider.setCurrentIndex(vision_provider_idx)
                        pcfg = vprefs.get("provider_configs", {}).get("mimo_vision", {})
                        if pcfg.get("base_url"):
                            self.mimo_vision_base_url.setText(pcfg["base_url"])
                    except Exception:
                        pass

                # 触发 provider 切换以更新 UI 状态
                self._on_vision_provider_changed(vision_provider_idx)

                # ASR provider 切换触发
                self._on_asr_provider_changed(self.asr_provider.currentIndex())

                # v1.9.76: 同步主动说话配置
                self._load_proactive_config()
        except Exception as e:
            import traceback
            print(f"[SettingsPage] on_backend_ready 失败: {e}")
            traceback.print_exc()

    def _on_proactive_toggled(self, checked: bool):
        """v1.9.76: 主动说话开关切换"""
        backend = self.backend
        if not backend:
            return

        try:
            if hasattr(backend, 'proactive') and backend.proactive:
                if checked:
                    interval = self.proactive_interval.value()
                    backend.proactive.enabled = True
                    backend.proactive.start(interval=interval)
                    print(f"[SettingsPage] 主动说话已启动，间隔 {interval}s")
                else:
                    backend.proactive.enabled = False
                    backend.proactive.stop()
                    print("[SettingsPage] 主动说话已停止")
            else:
                if checked:
                    self.proactive_switch.setChecked(False)
                    InfoBar.warning(
                        title="不可用",
                        content="主动说话模块未初始化",
                        parent=self,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                    )
        except Exception as e:
            print(f"[SettingsPage] 切换主动说话失败: {e}")
            if checked:
                self.proactive_switch.setChecked(False)

        # 持久化
        self._save_proactive_config()

    def _on_proactive_interval_changed(self, value: int):
        """v1.9.76: 主动说话间隔变更"""
        backend = self.backend
        if not backend:
            return

        try:
            if hasattr(backend, 'proactive') and backend.proactive and self.proactive_switch.isChecked():
                backend.proactive.stop()
                backend.proactive.start(interval=value)
        except Exception:
            pass

        self._save_proactive_config()

    def _save_proactive_config(self):
        """保存主动说话配置"""
        try:
            prefs_file = os.path.join(_CACHE_DIR, "proactive_prefs.json")
            prefs = {
                "enabled": self.proactive_switch.isChecked(),
                "interval": self.proactive_interval.value(),
            }
            os.makedirs(_CACHE_DIR, exist_ok=True)
            with open(prefs_file, "w", encoding="utf-8") as f:
                json.dump(prefs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[SettingsPage] 保存主动说话配置失败: {e}")

    def _load_proactive_config(self):
        """加载主动说话配置"""
        try:
            prefs_file = os.path.join(_CACHE_DIR, "proactive_prefs.json")
            if not os.path.exists(prefs_file):
                return

            with open(prefs_file, "r", encoding="utf-8") as f:
                prefs = json.load(f)

            if "interval" in prefs:
                self.proactive_interval.setValue(prefs["interval"])
            if prefs.get("enabled", False):
                self.proactive_switch.setChecked(True)
        except Exception:
            pass

    # ========== ASR 配置逻辑 ==========

    def _on_asr_provider_changed(self, index: int):
        """ASR 引擎切换"""
        # 0=FunASR, 1=MiMo ASR
        is_mimo = index == 1
        self.mimo_asr_base_url.setEnabled(is_mimo)

    def _save_asr_config(self):
        """保存 ASR 配置"""
        provider_map = {0: "funasr", 1: "mimo"}
        provider = provider_map.get(self.asr_provider.currentIndex(), "funasr")

        # 1. 持久化到 asr_preferences.json
        asr_prefs = {"provider": provider}
        provider_configs = {}
        if provider == "mimo":
            mimo_url = self.mimo_asr_base_url.text().strip()
            provider_configs["mimo"] = {
                "base_url": mimo_url or "https://api.xiaomimimo.com/v1",
                "model": "mimo-v2.5",
            }
        if provider_configs:
            asr_prefs["provider_configs"] = provider_configs

        asr_prefs_file = os.path.join(_CACHE_DIR, "asr_preferences.json")
        try:
            os.makedirs(_CACHE_DIR, exist_ok=True)
            with open(asr_prefs_file, "w", encoding="utf-8") as f:
                json.dump(asr_prefs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[SettingsPage] 保存 ASR 偏好失败: {e}")
            return

        # 2. 更新后端配置
        backend = self.backend
        if backend:
            asr_section = backend.config.config.setdefault("asr", {})
            asr_section["provider"] = provider

            if provider == "mimo":
                mimo_sub = asr_section.setdefault("mimo", {})
                mimo_url = self.mimo_asr_base_url.text().strip()
                if mimo_url:
                    mimo_sub["base_url"] = mimo_url

            # 重建 ASR 引擎
            if hasattr(backend, '_lazy_modules') and 'asr' in backend._lazy_modules:
                old_asr = backend._lazy_modules.pop('asr', None)
                if old_asr and hasattr(old_asr, 'cleanup'):
                    try:
                        old_asr.cleanup()
                    except Exception:
                        pass
                try:
                    _ = backend.asr
                except Exception as e:
                    print(f"[SettingsPage] ASR 引擎重建失败: {e}")

        InfoBar.success(
            title="保存成功",
            content=f"ASR 配置已保存: {self.asr_provider.currentText()}",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=2000
        )

    def _load_asr_prefs(self):
        """从 asr_preferences.json 加载 ASR 偏好"""
        try:
            asr_prefs_file = os.path.join(_CACHE_DIR, "asr_preferences.json")
            if not os.path.exists(asr_prefs_file):
                return

            with open(asr_prefs_file, "r", encoding="utf-8") as f:
                prefs = json.load(f)

            provider = prefs.get("provider", "funasr")
            provider_map = {"funasr": 0, "mimo": 1}
            idx = provider_map.get(provider, 0)
            self.asr_provider.setCurrentIndex(idx)

            # 恢复 MiMo base_url
            provider_configs = prefs.get("provider_configs", {})
            mimo_cfg = provider_configs.get("mimo", {})
            if mimo_cfg.get("base_url"):
                self.mimo_asr_base_url.setText(mimo_cfg["base_url"])

        except Exception as e:
            print(f"[SettingsPage] 加载 ASR 偏好失败: {e}")

    # ========== 视觉配置 ==========

    def _on_vision_provider_changed(self, index: int):
        """v1.9.76: 视觉引擎切换"""
        # 0=RapidOCR, 1=MiniMax VL, 2=MiniCPM-V2, 3=MiMo Vision
        is_minimax = index == 1
        is_minicpm = index == 2
        is_mimo = index == 3
        self.vision_api_key.setEnabled(is_minimax)
        self.vision_api_host.setEnabled(is_minimax)
        self.vision_model_path.setEnabled(is_minicpm)
        self.vision_int4_switch.setEnabled(is_minicpm)
        self.mimo_vision_base_url.setEnabled(is_mimo)

    def _save_vision_config(self):
        """v1.9.76: 保存视觉配置"""
        backend = self.backend
        if not backend:
            return

        provider_map = {0: "rapidocr", 1: "minimax_vl", 2: "minicpm", 3: "mimo_vision"}
        provider = provider_map.get(self.vision_provider.currentIndex(), "rapidocr")

        vision_section = backend.config.config.setdefault("vision", {})
        vision_section["default_provider"] = provider

        # MiniMax VL 配置
        if provider == "minimax_vl":
            minimax_vl = vision_section.setdefault("minimax_vl", {})
            key = self.vision_api_key.text().strip()
            if key:
                minimax_vl["api_key"] = key
            host = self.vision_api_host.text().strip()
            if host:
                minimax_vl["api_host"] = host

        # MiniCPM-V2 配置
        if provider == "minicpm":
            minicpm = vision_section.setdefault("minicpm", {})
            model_path = self.vision_model_path.text().strip()
            if model_path:
                minicpm["model_id_or_path"] = model_path
            minicpm["int4"] = self.vision_int4_switch.isChecked()

        # MiMo Vision 配置
        if provider == "mimo_vision":
            mimo_vision = vision_section.setdefault("mimo_vision", {})
            mimo_url = self.mimo_vision_base_url.text().strip()
            if mimo_url:
                mimo_vision["base_url"] = mimo_url

        # 持久化视觉偏好到 vision_preferences.json
        vision_prefs = {"default_provider": provider}
        provider_configs = {}
        if provider == "mimo_vision":
            mimo_url = self.mimo_vision_base_url.text().strip()
            provider_configs["mimo_vision"] = {
                "base_url": mimo_url or "https://api.xiaomimimo.com/v1",
                "model": "mimo-v2.5",
            }
        if provider_configs:
            vision_prefs["provider_configs"] = provider_configs
        try:
            vision_prefs_file = os.path.join(_CACHE_DIR, "vision_preferences.json")
            os.makedirs(_CACHE_DIR, exist_ok=True)
            with open(vision_prefs_file, "w", encoding="utf-8") as f:
                json.dump(vision_prefs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[SettingsPage] 保存视觉偏好失败: {e}")

        # 重建视觉引擎
        if hasattr(backend, '_lazy_modules') and 'vision' in backend._lazy_modules:
            old_vision = backend._lazy_modules.pop('vision', None)
            if old_vision and hasattr(old_vision, 'cleanup'):
                try:
                    old_vision.cleanup()
                except Exception:
                    pass
            try:
                _ = backend.vision
            except Exception as e:
                print(f"[SettingsPage] 视觉引擎重建失败: {e}")

        InfoBar.success(
            title="保存成功",
            content=f"视觉配置已保存: {self.vision_provider.currentText()}",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=2000
        )
