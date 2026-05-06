"""
设置页面 — LLM/TTS/ASR/系统配置

设计参考: LM Studio / Jan.ai 设置页
- ScrollArea + HeaderCardWidget 分组卡片布局
- 每个配置区域独立卡片，可折叠
- API Key 显隐切换
- 主题切换（暗色/亮色）
"""

import os
import sys
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

# 项目根目录
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from gugu_native.theme import apply_theme, get_global_qss, is_dark

# ===== Provider 配置数据（与 Web UI 的 _providerConfig 同步）=====
PROVIDER_CONFIG = {
    "deepseek": {
        "label": "DeepSeek",
        "baseUrl": "https://api.deepseek.com",
        "models": ["deepseek-v4-pro", "deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner"],
        "defaultModel": "deepseek-chat",
        "keyPlaceholder": "在 platform.deepseek.com 获取",
    },
    "kimi": {
        "label": "Kimi",
        "baseUrl": "https://api.moonshot.cn/v1",
        "models": ["kimi-k2.6", "kimi-k2.5", "kimi-k2-thinking", "kimi-k2-thinking-turbo", "kimi-k2-0905-preview", "moonshot-v1-128k", "moonshot-v1-32k", "moonshot-v1-8k"],
        "defaultModel": "kimi-k2.6",
        "keyPlaceholder": "在 platform.kimi.com 获取",
    },
    "glm": {
        "label": "智谱 GLM",
        "baseUrl": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["GLM-5.1", "GLM-5", "GLM-5-Turbo", "GLM-4.7", "GLM-4.7-FlashX", "GLM-4.6", "GLM-4.5-Air", "GLM-4-Long", "GLM-4.7-Flash"],
        "defaultModel": "GLM-4.7-FlashX",
        "keyPlaceholder": "在 open.bigmodel.cn 获取",
    },
    "qwen": {
        "label": "通义千问",
        "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen3.6-max-preview", "qwen3.6-plus", "qwen3.6-flash", "qwen-max", "qwen-plus", "qwen-turbo"],
        "defaultModel": "qwen3.6-plus",
        "keyPlaceholder": "在 dashscope.console.aliyun.com 获取",
    },
    "minimax": {
        "label": "MiniMax",
        "baseUrl": "https://api.minimaxi.com/anthropic",
        "models": ["MiniMax-M2.7", "MiniMax-M2.7-highspeed", "MiniMax-M2.5", "MiniMax-M2.5-highspeed", "MiniMax-M2.1", "MiniMax-M2.1-highspeed", "MiniMax-M2"],
        "defaultModel": "MiniMax-M2.7",
        "keyPlaceholder": "在 minimaxi.com 获取",
    },
    "doubao": {
        "label": "豆包",
        "baseUrl": "https://ark.cn-beijing.volces.com/api/v3",
        "models": ["doubao-seed-1-8-250415", "doubao-seed-1-6-251015", "doubao-seed-1-6-flash-250415", "doubao-1.5-pro-32k", "doubao-1.5-pro-256k", "doubao-1.5-lite-32k"],
        "defaultModel": "doubao-1.5-pro-32k",
        "keyPlaceholder": "在 console.volcengine.com/ark 获取",
    },
    "mimo": {
        "label": "小米 MiMo",
        "baseUrl": "https://api.xiaomimimo.com/v1",
        "models": ["mimo-v2.5-pro", "mimo-v2.5", "mimo-v2.5-flash"],
        "defaultModel": "mimo-v2.5",
        "keyPlaceholder": "在 platform.xiaomimimo.com 获取",
    },
    "openai": {
        "label": "OpenAI",
        "baseUrl": "https://api.openai.com/v1",
        "models": ["gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini", "o3", "o4-mini"],
        "defaultModel": "gpt-4o-mini",
        "keyPlaceholder": "在 platform.openai.com 获取",
    },
    "anthropic": {
        "label": "Anthropic",
        "baseUrl": "https://api.anthropic.com",
        "models": ["claude-sonnet-4-6-20260219", "claude-sonnet-4-5-20250929", "claude-haiku-4-5-20251015", "claude-opus-4-20250514"],
        "defaultModel": "claude-sonnet-4-5-20250929",
        "keyPlaceholder": "在 console.anthropic.com 获取",
    },
    "ollama": {
        "label": "Ollama (本地)",
        "baseUrl": "http://localhost:11434/v1",
        "models": [],  # 运行时动态获取
        "defaultModel": "qwen3:8b",
        "keyPlaceholder": "ollama",
    },
}

# Provider 显示名 -> 内部 key 的映射
_LABEL_TO_KEY = {v["label"]: k for k, v in PROVIDER_CONFIG.items()}

# 缓存文件路径
_CACHE_DIR = os.path.join(PROJECT_DIR, "app", "cache")
_LLM_PREFS_FILE = os.path.join(_CACHE_DIR, "llm_preferences.json")
_API_KEYS_FILE = os.path.join(_CACHE_DIR, "api_keys.json")
_TTS_PREFS_FILE = os.path.join(_CACHE_DIR, "tts_preferences.json")

# Edge TTS 音色列表（与 app/tts/__init__.py EdgeTTS.VOICES 同步）
EDGE_VOICES = [
    ("zh-CN-XiaoxiaoNeural", "中文女声 (标准)"),
    ("zh-CN-XiaoyiNeural", "中文女声 (年轻)"),
    ("zh-CN-YunxiNeural", "中文男声 (云希)"),
    ("zh-CN-YunyangNeural", "中文男声 (云扬)"),
    ("zh-HK-HiuGaaiNeural", "粤语女声"),
    ("zh-HK-HiuMaanNeural", "粤语女声2"),
    ("zh-TW-HsiaoChenNeural", "台湾女声"),
    ("zh-TW-HsiaoYuNeural", "台湾女声2"),
]


class SettingsPage(ScrollArea):
    """设置页面 — 卡片式分组布局"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsPage")
        self._backend = None
        self._api_key_visible = False  # API Key 显隐状态
        self._init_ui()
        self._load_saved_config()

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

        # 标题
        title = TitleLabel("设置")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        main_layout.addWidget(title)

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

        save_llm_btn = PushButton("保存 LLM 配置")
        save_llm_btn.setIcon(FluentIcon.SAVE)
        save_llm_btn.clicked.connect(self._save_llm_config)
        save_llm_btn.setStyleSheet("""
            PushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5c7cfa, stop:1 #4263eb);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 20px;
                font-weight: 500;
            }
            PushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4c6cf0, stop:1 #3b5bdb);
            }
            PushButton:pressed {
                background: #3549c6;
            }
        """)
        llm_layout.addRow("", save_llm_btn)

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
        self.tts_engine.addItems(["Edge TTS", "GPT-SoVITS"])
        self.tts_engine.currentIndexChanged.connect(self._on_tts_engine_changed)
        tts_layout.addRow("TTS 引擎:", self.tts_engine)

        self.tts_voice = ComboBox()
        self.tts_voice.setPlaceholderText("选择音色...")
        self._populate_edge_voices()
        tts_layout.addRow("音色:", self.tts_voice)

        save_tts_btn = PushButton("保存 TTS 配置")
        save_tts_btn.setIcon(FluentIcon.SAVE)
        save_tts_btn.clicked.connect(self._save_tts_config)
        save_tts_btn.setStyleSheet("""
            PushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5c7cfa, stop:1 #4263eb);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 20px;
                font-weight: 500;
            }
            PushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4c6cf0, stop:1 #3b5bdb);
            }
            PushButton:pressed {
                background: #3549c6;
            }
        """)
        tts_layout.addRow("", save_tts_btn)

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
        self.vision_provider.addItems(["RapidOCR (本地)", "MiniMax VL (云端)", "MiniCPM-V2 (本地GPU)"])
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

        # MiniCPM-V2 配置
        self.vision_model_path = LineEdit()
        self.vision_model_path.setPlaceholderText("本地模型路径（如 openbmb/MiniCPM-V-2_6）")
        vision_layout.addRow("MiniCPM 模型:", self.vision_model_path)

        self.vision_int4_switch = SwitchButton("INT4 量化")
        self.vision_int4_switch.setChecked(False)
        vision_layout.addRow("INT4 量化:", self.vision_int4_switch)

        # 保存视觉配置按钮
        save_vision_btn = PushButton("保存视觉配置")
        save_vision_btn.setIcon(FluentIcon.SAVE)
        save_vision_btn.clicked.connect(self._save_vision_config)
        save_vision_btn.setStyleSheet("""
            PushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5c7cfa, stop:1 #4263eb);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 20px;
                font-weight: 500;
            }
            PushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4c6cf0, stop:1 #3b5bdb);
            }
            PushButton:pressed {
                background: #3549c6;
            }
        """)
        vision_layout.addRow("", save_vision_btn)

        vision_card.viewLayout.addWidget(vision_content)
        main_layout.addWidget(vision_card)

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

        self.theme_combo = ComboBox()
        self.theme_combo.addItems(["深色", "浅色"])
        self.theme_combo.setCurrentIndex(0)  # 默认深色
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        appearance_layout.addRow("主题:", self.theme_combo)

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

        version_label = StrongBodyLabel("咕咕嘎嘎 AI-VTuber v1.9.82")
        about_layout.addWidget(version_label)

        desc_label = CaptionLabel("AI 实时对话伴侣 — 声音克隆训练 + 深度记忆 + Live2D 形象")
        about_layout.addWidget(desc_label)

        github_btn = HyperlinkButton(
            "https://github.com/xzt238/ai-vtuber-fixed",
            "GitHub 仓库",
            self,
        )
        about_layout.addWidget(github_btn)

        check_update_btn = PushButton("检查更新")
        check_update_btn.setIcon(FluentIcon.UPDATE)
        check_update_btn.clicked.connect(self._check_for_updates)
        check_update_btn.setStyleSheet("""
            PushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #37b24d, stop:1 #2f9e44);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 20px;
                font-weight: 500;
            }
            PushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2f9e44, stop:1 #2b8a3e);
            }
        """)
        about_layout.addWidget(check_update_btn)

        about_card.viewLayout.addWidget(about_content)
        main_layout.addWidget(about_card)

        # 底部弹性空间
        main_layout.addStretch(1)

    # ========== 主题切换 ==========

    def _on_theme_changed(self, index: int):
        """主题切换 — v1.9.80 增强版：通知全局刷新"""
        from qfluentwidgets import Theme
        theme = Theme.DARK if index == 0 else Theme.LIGHT
        apply_theme(theme)
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

    # ========== API Key 显隐 ==========

    def _toggle_api_key_visibility(self):
        """切换 API Key 显示/隐藏"""
        self._api_key_visible = not self._api_key_visible
        if self._api_key_visible:
            self.api_key_input.setEchoMode(LineEdit.EchoMode.Normal)
            self._toggle_key_btn.setIcon(FluentIcon.VIEW_OFF)
        else:
            self.api_key_input.setEchoMode(LineEdit.EchoMode.Password)
            self._toggle_key_btn.setIcon(FluentIcon.VIEW)

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
        """从 Ollama API 动态获取模型列表"""
        try:
            import requests
            resp = requests.get("http://localhost:11434/api/tags", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                if models:
                    self.model_combo.addItems(models)
                    return
        except Exception:
            pass
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
        """将 LLM 配置应用到后端"""
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

        # 重建 LLM 引擎
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
                old_llm = backend._lazy_modules.pop('llm', None)
                if old_llm and hasattr(old_llm, 'cleanup') and callable(old_llm.cleanup):
                    try:
                        old_llm.cleanup()
                    except Exception:
                        pass
                try:
                    _ = backend.llm
                except Exception as e:
                    print(f"[SettingsPage] LLM 引擎重建失败: {e}")

    # ========== TTS 配置逻辑 ==========

    def _populate_edge_voices(self):
        """填充 Edge TTS 音色列表"""
        self.tts_voice.clear()
        for voice_id, label in EDGE_VOICES:
            self.tts_voice.addItem(f"{label} ({voice_id})", userData=voice_id)

    def _populate_gptsovits_voices(self):
        """填充 GPT-SoVITS 音色列表（从后端获取项目列表）"""
        self.tts_voice.clear()
        backend = self.backend
        if not backend:
            self.tts_voice.addItem("默认音色", userData="default")
            return

        try:
            tts = backend.tts
            if tts and hasattr(tts, 'get_voices'):
                voices = tts.get_voices()
                if voices:
                    for v in voices:
                        if isinstance(v, dict):
                            value = str(v.get('value', v.get('name', '')))
                            label = str(v.get('label', value))
                            self.tts_voice.addItem(label, userData=value)
                        else:
                            self.tts_voice.addItem(str(v), userData=str(v))
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
                    self.tts_voice.addItem(name, userData=name)
                return
        except Exception:
            pass

        self.tts_voice.addItem("默认音色", userData="default")

    def _on_tts_engine_changed(self, index: int):
        """TTS 引擎切换 — 动态填充音色列表"""
        engine = self.tts_engine.currentText()
        if engine == "Edge TTS":
            self._populate_edge_voices()
        elif engine == "GPT-SoVITS":
            self._populate_gptsovits_voices()

    def _get_current_tts_provider(self) -> str:
        """获取当前 TTS 引擎内部标识"""
        engine = self.tts_engine.currentText()
        return {"Edge TTS": "edge", "GPT-SoVITS": "gptsovits"}.get(engine, "edge")

    def _get_current_voice_id(self) -> str:
        """获取当前选中的音色 ID（userData 优先，fallback 到文本）"""
        idx = self.tts_voice.currentIndex()
        if idx >= 0:
            user_data = self.tts_voice.itemData(idx)
            if user_data:
                return str(user_data)
        return self.tts_voice.currentText()

    def _save_tts_config(self):
        """保存 TTS 配置（持久化 + 后端同步）"""
        engine = self.tts_engine.currentText()
        voice_id = self._get_current_voice_id()
        provider = self._get_current_tts_provider()

        # 1. 持久化到 tts_preferences.json
        tts_prefs = {
            "engine": engine,
            "provider": provider,
            "voice": voice_id,
        }
        try:
            os.makedirs(_CACHE_DIR, exist_ok=True)
            with open(_TTS_PREFS_FILE, "w", encoding="utf-8") as f:
                json.dump(tts_prefs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[SettingsPage] 保存 TTS 偏好失败: {e}")

        # 2. 更新后端配置并重建 TTS 引擎
        backend = self.backend
        if backend:
            tts_section = backend.config.config.setdefault("tts", {})
            tts_section["provider"] = provider

            if voice_id:
                sub = tts_section.setdefault(provider, {})
                sub["voice"] = voice_id
                if provider == "gptsovits":
                    sub["project"] = voice_id  # GPT-SoVITS voice ID 就是 project name

            if hasattr(backend, '_lazy_modules') and 'tts' in backend._lazy_modules:
                old_tts = backend._lazy_modules.pop('tts', None)
                if old_tts and hasattr(old_tts, 'cleanup'):
                    try:
                        old_tts.cleanup()
                    except Exception:
                        pass
                try:
                    _ = backend.tts
                    # TTS 引擎重建后，设置音色
                    if hasattr(backend.tts, 'set_voice'):
                        backend.tts.set_voice(voice_id)
                    elif provider == "gptsovits" and hasattr(backend.tts, 'set_project'):
                        backend.tts.set_project(voice_id)
                except Exception as e:
                    print(f"[SettingsPage] TTS 引擎重建失败: {e}")

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
        """从 tts_preferences.json 加载 TTS 偏好"""
        try:
            if not os.path.exists(_TTS_PREFS_FILE):
                return

            with open(_TTS_PREFS_FILE, "r", encoding="utf-8") as f:
                prefs = json.load(f)

            engine = prefs.get("engine", "Edge TTS")
            voice_id = prefs.get("voice", "")

            # 设置引擎
            idx = self.tts_engine.findText(engine)
            if idx >= 0:
                self.tts_engine.setCurrentIndex(idx)
            # 引擎切换会自动填充音色列表

            # 设置音色
            if voice_id:
                # 先尝试按 userData 查找
                for i in range(self.tts_voice.count()):
                    if str(self.tts_voice.itemData(i) or "") == voice_id:
                        self.tts_voice.setCurrentIndex(i)
                        return
                # 再尝试按文本查找
                voice_idx = self.tts_voice.findText(voice_id)
                if voice_idx >= 0:
                    self.tts_voice.setCurrentIndex(voice_idx)

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

    def on_backend_ready(self):
        """后端就绪回调 - 从后端同步当前配置"""
        try:
            backend = self.backend
            if not backend:
                return
            if hasattr(backend, 'config'):
                config = backend.config
                # 同步 LLM 配置
                llm_cfg = config.get('llm', {})
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

                # 同步 TTS 配置（优先用持久化文件，回退到 config.yaml）
                tts_cfg = config.get('tts', {})
                if not os.path.exists(_TTS_PREFS_FILE):
                    tts_provider = tts_cfg.get("provider", "edge")
                    engine_map = {"edge": "Edge TTS", "gptsovits": "GPT-SoVITS"}
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
                else:
                    self._load_tts_prefs()

                # 同步视觉配置
                vision_cfg = config.get('vision', {})
                vision_provider = vision_cfg.get('default_provider', 'rapidocr')
                provider_idx = {"rapidocr": 0, "minimax_vl": 1, "minicpm": 2}.get(vision_provider, 0)
                self.vision_provider.setCurrentIndex(provider_idx)
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

                # 触发 provider 切换以更新 UI 状态
                self._on_vision_provider_changed(provider_idx)

                # v1.9.76: 同步主动说话配置
                self._load_proactive_config()
        except Exception:
            pass

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

    # ========== 视觉配置 ==========

    def _on_vision_provider_changed(self, index: int):
        """v1.9.76: 视觉引擎切换"""
        # 0=RapidOCR, 1=MiniMax VL, 2=MiniCPM-V2
        is_minimax = index == 1
        is_minicpm = index == 2
        self.vision_api_key.setEnabled(is_minimax)
        self.vision_api_host.setEnabled(is_minimax)
        self.vision_model_path.setEnabled(is_minicpm)
        self.vision_int4_switch.setEnabled(is_minicpm)

    def _save_vision_config(self):
        """v1.9.76: 保存视觉配置"""
        backend = self.backend
        if not backend:
            return

        provider_map = {0: "rapidocr", 1: "minimax_vl", 2: "minicpm"}
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
