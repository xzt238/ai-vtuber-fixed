"""
功能设置页面

提供声音处理、知识库、角色扮演、情感系统、插件系统等功能的配置界面。

设计参考: 直播设置页面的卡片式布局
- 左侧功能列表
- 右侧配置面板
- 实时状态显示

作者: 咕咕嘎嘎
日期: 2026-06-04
"""



from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QScrollArea, QDoubleSpinBox, QSpinBox, QCheckBox,
    QComboBox, QLineEdit, QTextEdit, QGroupBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont

from qfluentwidgets import (
    Slider, PushButton, CaptionLabel, InfoBar, InfoBarPosition,
    TitleLabel, SubtitleLabel, CardWidget, FluentIcon,
    SwitchButton, LineEdit, ComboBox, SpinBox, DoubleSpinBox,
    TextEdit, ProgressBar, TabBar, ScrollArea
)

from app.shared_config import PROJECT_DIR
from gugu_native.widgets.lazy_page_mixin import LazyPageMixin
from gugu_native.widgets.skeleton_container import SkeletonContainer


class FeaturesSettingsPage(QWidget, LazyPageMixin):
    """功能设置页面 - 支持懒加载"""

    # 信号定义
    config_changed = Signal(str, object)  # 配置变更信号
    status_updated = Signal(str, str)     # 状态更新信号
    log_message = Signal(str, str)        # 日志消息信号

    def __init__(self, parent=None) -> None:
        """内部方法"""
        QWidget.__init__(self, parent)
        LazyPageMixin.__init__(self)
        self.setObjectName("featuresSettingsPage")
        self._backend = None
        self._config_widgets = {}
        self._status_labels = {}
        self._log_messages = []
        self._config_file = Path(PROJECT_DIR) / "app" / "config.yaml"
        self._config_data = {}
        
        # 骨架屏占位
        self._skeleton = SkeletonContainer("正在加载功能设置...", self)
        self._skeleton.hide_skeleton()
        
        # 连接信号
        self.config_changed.connect(self._on_config_changed)
        self.status_updated.connect(self._on_status_updated)
        self.log_message.connect(self._on_log_message)

    def show_skeleton(self) -> None:
        """Show skeleton"""
        self._skeleton.show_skeleton()

    def hide_skeleton(self) -> None:
        """Hide skeleton"""
        self._skeleton.hide_skeleton()

    def lazy_init(self) -> None:
        """首次切换到该页时调用 — 构建完整 UI"""
        if self._is_initialized:
            return
        self._skeleton.hide_skeleton()
        self._skeleton.setParent(None)
        self._skeleton.deleteLater()
        
        # 加载配置
        self._load_config()
        
        # 初始化UI
        self._init_ui()
        
        # 启动状态刷新定时器
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_status)
        self._refresh_timer.start(2000)

    def set_backend(self, backend) -> None:
        """设置后端引用"""
        self._backend = backend

    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            import yaml
            if self._config_file.exists():
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    self._config_data = yaml.safe_load(f) or {}
                self._log("INFO", f"配置文件加载成功: {self._config_file}")
            else:
                self._log("WARN", f"配置文件不存在: {self._config_file}")
                self._config_data = {}
        except Exception as e:
            self._log("ERROR", f"配置文件加载失败: {e}")
            self._config_data = {}

    def _save_config(self) -> None:
        """保存配置文件"""
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self._config_data, f, allow_unicode=True, default_flow_style=False)
            self._log("INFO", "配置文件保存成功")
        except Exception as e:
            self._log("ERROR", f"配置文件保存失败: {e}")

    def _init_ui(self) -> None:
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # 创建主分割器
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 上部：功能配置区域
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # 左侧功能列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self._init_feature_list(left_layout)
        top_layout.addWidget(left_widget)
        
        # 右侧配置面板
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        right_panel = QWidget()
        self._right_layout = QVBoxLayout(right_panel)
        self._right_layout.setSpacing(10)
        
        # 创建各个功能的配置卡片
        self._init_all_cards()
        
        self._right_layout.addStretch()
        right_scroll.setWidget(right_panel)
        top_layout.addWidget(right_scroll)
        
        # 设置分割比例
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.addWidget(left_widget)
        top_splitter.addWidget(right_scroll)
        top_splitter.setStretchFactor(0, 1)
        top_splitter.setStretchFactor(1, 3)
        
        main_splitter.addWidget(top_splitter)
        
        # 下部：日志和状态面板
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        self._init_bottom_panel(bottom_layout)
        main_splitter.addWidget(bottom_widget)
        
        # 设置分割比例
        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(main_splitter)

    def _init_feature_list(self, layout) -> None:
        """初始化左侧功能列表"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)
        card_layout.setContentsMargins(12, 12, 12, 12)

        card_layout.addWidget(SubtitleLabel("功能模块"))

        features = [
            ("🎵 声音处理", "audio", "SVC声音转换、唱歌"),
            ("📚 知识库", "rag", "RAG文档检索增强"),
            ("🎭 角色扮演", "roleplay", "角色创建、剧情系统"),
            ("💝 情感系统", "emotion", "情感识别、表达、记忆"),
            ("👥 多AI群聊", "multi_agent", "多角色对话场景"),
            ("📷 摄像头视觉", "vision_input", "摄像头视觉输入"),
            ("🔌 插件系统", "plugin", "插件管理、扩展功能"),
        ]

        self._feature_buttons = {}
        for name, key, desc in features:
            btn_layout = QVBoxLayout()
            btn_layout.setSpacing(2)
            
            btn = PushButton(name)
            btn.setToolTip(desc)
            btn.clicked.connect(lambda checked, k=key: self._show_feature_config(k))
            btn_layout.addWidget(btn)
            
            # 状态标签
            status_label = CaptionLabel("未配置")
            status_label.setStyleSheet("color: gray;")
            btn_layout.addWidget(status_label)
            
            self._feature_buttons[key] = (btn, status_label)
            card_layout.addLayout(btn_layout)

        card_layout.addStretch()
        layout.addWidget(card)

    def _init_all_cards(self) -> None:
        """初始化所有配置卡片"""
        self._cards = {}
        
        # 声音处理配置卡片
        self._cards['audio'] = self._create_audio_card()
        self._right_layout.addWidget(self._cards['audio'])
        
        # 知识库配置卡片
        self._cards['rag'] = self._create_rag_card()
        self._right_layout.addWidget(self._cards['rag'])
        
        # 角色扮演配置卡片
        self._cards['roleplay'] = self._create_roleplay_card()
        self._right_layout.addWidget(self._cards['roleplay'])
        
        # 情感系统配置卡片
        self._cards['emotion'] = self._create_emotion_card()
        self._right_layout.addWidget(self._cards['emotion'])
        
        # 插件系统配置卡片
        self._cards['plugin'] = self._create_plugin_card()
        self._right_layout.addWidget(self._cards['plugin'])

    def _create_audio_card(self) -> None:
        """创建声音处理配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🎵 声音处理配置"))

        # SVC声音转换
        svc_group = QGroupBox("SVC声音转换")
        svc_layout = QVBoxLayout(svc_group)

        # 启用开关
        svc_enable_layout = QHBoxLayout()
        svc_enable_layout.addWidget(CaptionLabel("启用SVC"))
        self._config_widgets['svc_enabled'] = SwitchButton()
        self._config_widgets['svc_enabled'].setChecked(self._config_data.get('svc', {}).get('enabled', False))
        self._config_widgets['svc_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('svc.enabled', checked)
        )
        svc_enable_layout.addWidget(self._config_widgets['svc_enabled'])
        svc_layout.addLayout(svc_enable_layout)

        # 设备选择
        device_layout = QHBoxLayout()
        device_layout.addWidget(CaptionLabel("设备"))
        self._config_widgets['svc_device'] = ComboBox()
        self._config_widgets['svc_device'].addItems(["cuda", "cpu"])
        self._config_widgets['svc_device'].setCurrentText(self._config_data.get('svc', {}).get('device', 'cuda'))
        self._config_widgets['svc_device'].currentTextChanged.connect(
            lambda text: self._update_config('svc.device', text)
        )
        device_layout.addWidget(self._config_widgets['svc_device'])
        svc_layout.addLayout(device_layout)

        # 模型路径
        model_layout = QHBoxLayout()
        model_layout.addWidget(CaptionLabel("模型路径"))
        self._config_widgets['svc_model_path'] = LineEdit()
        self._config_widgets['svc_model_path'].setText(self._config_data.get('svc', {}).get('model_path', ''))
        self._config_widgets['svc_model_path'].setPlaceholderText("选择SVC模型文件")
        self._config_widgets['svc_model_path'].textChanged.connect(
            lambda text: self._update_config('svc.model_path', text)
        )
        model_layout.addWidget(self._config_widgets['svc_model_path'])
        svc_layout.addLayout(model_layout)

        card_layout.addWidget(svc_group)

        # 唱歌模块
        singing_group = QGroupBox("唱歌模块")
        singing_layout = QVBoxLayout(singing_group)

        # 启用开关
        singing_enable_layout = QHBoxLayout()
        singing_enable_layout.addWidget(CaptionLabel("启用唱歌"))
        self._config_widgets['singing_enabled'] = SwitchButton()
        self._config_widgets['singing_enabled'].setChecked(self._config_data.get('singing', {}).get('enabled', False))
        self._config_widgets['singing_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('singing.enabled', checked)
        )
        singing_enable_layout.addWidget(self._config_widgets['singing_enabled'])
        singing_layout.addLayout(singing_enable_layout)

        # 设备选择
        singing_device_layout = QHBoxLayout()
        singing_device_layout.addWidget(CaptionLabel("设备"))
        self._config_widgets['singing_device'] = ComboBox()
        self._config_widgets['singing_device'].addItems(["cuda", "cpu"])
        self._config_widgets['singing_device'].setCurrentText(self._config_data.get('singing', {}).get('device', 'cuda'))
        self._config_widgets['singing_device'].currentTextChanged.connect(
            lambda text: self._update_config('singing.device', text)
        )
        singing_device_layout.addWidget(self._config_widgets['singing_device'])
        singing_layout.addLayout(singing_device_layout)

        # 模型路径
        singing_model_layout = QHBoxLayout()
        singing_model_layout.addWidget(CaptionLabel("模型路径"))
        self._config_widgets['singing_model_path'] = LineEdit()
        self._config_widgets['singing_model_path'].setText(self._config_data.get('singing', {}).get('model_path', ''))
        self._config_widgets['singing_model_path'].setPlaceholderText("选择唱歌模型文件")
        self._config_widgets['singing_model_path'].textChanged.connect(
            lambda text: self._update_config('singing.model_path', text)
        )
        singing_model_layout.addWidget(self._config_widgets['singing_model_path'])
        singing_layout.addLayout(singing_model_layout)

        card_layout.addWidget(singing_group)

        # 状态显示
        self._status_labels['audio'] = CaptionLabel("状态: 未配置")
        card_layout.addWidget(self._status_labels['audio'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        save_btn = PushButton("保存配置")
        save_btn.clicked.connect(self._save_audio_config)
        btn_layout.addWidget(save_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_rag_card(self) -> None:
        """创建知识库配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("📚 知识库配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用知识库"))
        self._config_widgets['rag_enabled'] = SwitchButton()
        self._config_widgets['rag_enabled'].setChecked(self._config_data.get('rag', {}).get('enabled', False))
        self._config_widgets['rag_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('rag.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['rag_enabled'])
        card_layout.addLayout(enable_layout)

        # 分块大小
        chunk_size_layout = QHBoxLayout()
        chunk_size_layout.addWidget(CaptionLabel("分块大小"))
        self._config_widgets['rag_chunk_size'] = SpinBox()
        self._config_widgets['rag_chunk_size'].setRange(100, 2000)
        self._config_widgets['rag_chunk_size'].setValue(self._config_data.get('rag', {}).get('chunk_size', 500))
        self._config_widgets['rag_chunk_size'].valueChanged.connect(
            lambda value: self._update_config('rag.chunk_size', value)
        )
        chunk_size_layout.addWidget(self._config_widgets['rag_chunk_size'])
        card_layout.addLayout(chunk_size_layout)

        # 检索数量
        top_k_layout = QHBoxLayout()
        top_k_layout.addWidget(CaptionLabel("检索数量"))
        self._config_widgets['rag_top_k'] = SpinBox()
        self._config_widgets['rag_top_k'].setRange(1, 20)
        self._config_widgets['rag_top_k'].setValue(self._config_data.get('rag', {}).get('top_k', 5))
        self._config_widgets['rag_top_k'].valueChanged.connect(
            lambda value: self._update_config('rag.top_k', value)
        )
        top_k_layout.addWidget(self._config_widgets['rag_top_k'])
        card_layout.addLayout(top_k_layout)

        # 存储目录
        storage_layout = QHBoxLayout()
        storage_layout.addWidget(CaptionLabel("存储目录"))
        self._config_widgets['rag_storage_dir'] = LineEdit()
        self._config_widgets['rag_storage_dir'].setText(self._config_data.get('rag', {}).get('storage_dir', './memory/knowledge_base'))
        self._config_widgets['rag_storage_dir'].textChanged.connect(
            lambda text: self._update_config('rag.storage_dir', text)
        )
        storage_layout.addWidget(self._config_widgets['rag_storage_dir'])
        card_layout.addLayout(storage_layout)

        # 状态显示
        self._status_labels['rag'] = CaptionLabel("状态: 未配置")
        card_layout.addWidget(self._status_labels['rag'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        save_btn = PushButton("保存配置")
        save_btn.clicked.connect(self._save_rag_config)
        btn_layout.addWidget(save_btn)
        
        import_btn = PushButton("导入文档")
        import_btn.clicked.connect(self._import_rag_document)
        btn_layout.addWidget(import_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_roleplay_card(self) -> None:
        """创建角色扮演配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🎭 角色扮演配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用角色扮演"))
        self._config_widgets['roleplay_enabled'] = SwitchButton()
        self._config_widgets['roleplay_enabled'].setChecked(self._config_data.get('roleplay', {}).get('enabled', True))
        self._config_widgets['roleplay_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('roleplay.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['roleplay_enabled'])
        card_layout.addLayout(enable_layout)

        # 最大角色数
        max_chars_layout = QHBoxLayout()
        max_chars_layout.addWidget(CaptionLabel("最大角色数"))
        self._config_widgets['roleplay_max_characters'] = SpinBox()
        self._config_widgets['roleplay_max_characters'].setRange(1, 100)
        self._config_widgets['roleplay_max_characters'].setValue(self._config_data.get('roleplay', {}).get('characters', {}).get('max_characters', 50))
        self._config_widgets['roleplay_max_characters'].valueChanged.connect(
            lambda value: self._update_config('roleplay.characters.max_characters', value)
        )
        max_chars_layout.addWidget(self._config_widgets['roleplay_max_characters'])
        card_layout.addLayout(max_chars_layout)

        # 存储目录
        storage_layout = QHBoxLayout()
        storage_layout.addWidget(CaptionLabel("存储目录"))
        self._config_widgets['roleplay_storage_dir'] = LineEdit()
        self._config_widgets['roleplay_storage_dir'].setText(self._config_data.get('roleplay', {}).get('storage_dir', './memory/roleplay'))
        self._config_widgets['roleplay_storage_dir'].textChanged.connect(
            lambda text: self._update_config('roleplay.storage_dir', text)
        )
        storage_layout.addWidget(self._config_widgets['roleplay_storage_dir'])
        card_layout.addLayout(storage_layout)

        # 状态显示
        self._status_labels['roleplay'] = CaptionLabel("状态: 未配置")
        card_layout.addWidget(self._status_labels['roleplay'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        save_btn = PushButton("保存配置")
        save_btn.clicked.connect(self._save_roleplay_config)
        btn_layout.addWidget(save_btn)
        
        create_btn = PushButton("创建角色")
        create_btn.clicked.connect(self._create_roleplay_character)
        btn_layout.addWidget(create_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_emotion_card(self) -> None:
        """创建情感系统配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("💝 情感系统配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用情感系统"))
        self._config_widgets['emotion_enabled'] = SwitchButton()
        self._config_widgets['emotion_enabled'].setChecked(self._config_data.get('emotion', {}).get('enabled', True))
        self._config_widgets['emotion_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('emotion.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['emotion_enabled'])
        card_layout.addLayout(enable_layout)

        # 文本情感分析
        text_layout = QHBoxLayout()
        text_layout.addWidget(CaptionLabel("文本情感分析"))
        self._config_widgets['emotion_text_enabled'] = SwitchButton()
        self._config_widgets['emotion_text_enabled'].setChecked(self._config_data.get('emotion', {}).get('analysis', {}).get('text_enabled', True))
        self._config_widgets['emotion_text_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('emotion.analysis.text_enabled', checked)
        )
        text_layout.addWidget(self._config_widgets['emotion_text_enabled'])
        card_layout.addLayout(text_layout)

        # 语音情感分析
        voice_layout = QHBoxLayout()
        voice_layout.addWidget(CaptionLabel("语音情感分析"))
        self._config_widgets['emotion_voice_enabled'] = SwitchButton()
        self._config_widgets['emotion_voice_enabled'].setChecked(self._config_data.get('emotion', {}).get('analysis', {}).get('voice_enabled', True))
        self._config_widgets['emotion_voice_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('emotion.analysis.voice_enabled', checked)
        )
        voice_layout.addWidget(self._config_widgets['emotion_voice_enabled'])
        card_layout.addLayout(voice_layout)

        # 表情回复
        emoji_layout = QHBoxLayout()
        emoji_layout.addWidget(CaptionLabel("表情回复"))
        self._config_widgets['emotion_emoji_enabled'] = SwitchButton()
        self._config_widgets['emotion_emoji_enabled'].setChecked(self._config_data.get('emotion', {}).get('expression', {}).get('emoji_enabled', True))
        self._config_widgets['emotion_emoji_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('emotion.expression.emoji_enabled', checked)
        )
        emoji_layout.addWidget(self._config_widgets['emotion_emoji_enabled'])
        card_layout.addLayout(emoji_layout)

        # 存储目录
        storage_layout = QHBoxLayout()
        storage_layout.addWidget(CaptionLabel("存储目录"))
        self._config_widgets['emotion_storage_dir'] = LineEdit()
        self._config_widgets['emotion_storage_dir'].setText(self._config_data.get('emotion', {}).get('storage_dir', './memory/emotion'))
        self._config_widgets['emotion_storage_dir'].textChanged.connect(
            lambda text: self._update_config('emotion.storage_dir', text)
        )
        storage_layout.addWidget(self._config_widgets['emotion_storage_dir'])
        card_layout.addLayout(storage_layout)

        # 状态显示
        self._status_labels['emotion'] = CaptionLabel("状态: 未配置")
        card_layout.addWidget(self._status_labels['emotion'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        save_btn = PushButton("保存配置")
        save_btn.clicked.connect(self._save_emotion_config)
        btn_layout.addWidget(save_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_plugin_card(self) -> None:
        """创建插件系统配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🔌 插件系统配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用插件系统"))
        self._config_widgets['plugin_enabled'] = SwitchButton()
        self._config_widgets['plugin_enabled'].setChecked(self._config_data.get('plugin', {}).get('enabled', True))
        self._config_widgets['plugin_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('plugin.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['plugin_enabled'])
        card_layout.addLayout(enable_layout)

        # 自动加载
        auto_load_layout = QHBoxLayout()
        auto_load_layout.addWidget(CaptionLabel("自动加载插件"))
        self._config_widgets['plugin_auto_load'] = SwitchButton()
        self._config_widgets['plugin_auto_load'].setChecked(self._config_data.get('plugin', {}).get('auto_load', True))
        self._config_widgets['plugin_auto_load'].checkedChanged.connect(
            lambda checked: self._update_config('plugin.auto_load', checked)
        )
        auto_load_layout.addWidget(self._config_widgets['plugin_auto_load'])
        card_layout.addLayout(auto_load_layout)

        # 最大插件数
        max_plugins_layout = QHBoxLayout()
        max_plugins_layout.addWidget(CaptionLabel("最大插件数"))
        self._config_widgets['plugin_max_plugins'] = SpinBox()
        self._config_widgets['plugin_max_plugins'].setRange(1, 100)
        self._config_widgets['plugin_max_plugins'].setValue(self._config_data.get('plugin', {}).get('max_plugins', 50))
        self._config_widgets['plugin_max_plugins'].valueChanged.connect(
            lambda value: self._update_config('plugin.max_plugins', value)
        )
        max_plugins_layout.addWidget(self._config_widgets['plugin_max_plugins'])
        card_layout.addLayout(max_plugins_layout)

        # 插件目录
        plugins_dir_layout = QHBoxLayout()
        plugins_dir_layout.addWidget(CaptionLabel("插件目录"))
        self._config_widgets['plugin_plugins_dir'] = LineEdit()
        self._config_widgets['plugin_plugins_dir'].setText(self._config_data.get('plugin', {}).get('plugins_dir', './plugins'))
        self._config_widgets['plugin_plugins_dir'].textChanged.connect(
            lambda text: self._update_config('plugin.plugins_dir', text)
        )
        plugins_dir_layout.addWidget(self._config_widgets['plugin_plugins_dir'])
        card_layout.addLayout(plugins_dir_layout)

        # 状态显示
        self._status_labels['plugin'] = CaptionLabel("状态: 未配置")
        card_layout.addWidget(self._status_labels['plugin'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        save_btn = PushButton("保存配置")
        save_btn.clicked.connect(self._save_plugin_config)
        btn_layout.addWidget(save_btn)
        
        scan_btn = PushButton("扫描插件")
        scan_btn.clicked.connect(self._scan_plugins)
        btn_layout.addWidget(scan_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _init_bottom_panel(self, layout) -> None:
        """初始化底部面板"""
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 日志标签页
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self._log_text)
        tab_widget.addTab(log_widget, "日志")
        
        # 状态标签页
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        self._status_table = QTableWidget()
        self._status_table.setColumnCount(3)
        self._status_table.setHorizontalHeaderLabels(["功能", "状态", "最后更新"])
        self._status_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        status_layout.addWidget(self._status_table)
        tab_widget.addTab(status_widget, "状态")
        
        layout.addWidget(tab_widget)

    def _show_feature_config(self, feature_key) -> None:
        """显示功能配置"""
        # 隐藏所有卡片
        for key, card in self._cards.items():
            card.setVisible(key == feature_key)
        
        # 更新按钮状态
        for key, (btn, status_label) in self._feature_buttons.items():
            btn.setChecked(key == feature_key)
        
        self._log("DEBUG", f"切换到功能配置: {feature_key}")

    def _update_config(self, key, value) -> None:
        """更新配置"""
        # 更新内存中的配置
        keys = key.split('.')
        config = self._config_data
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        
        # 保存配置文件
        self._save_config()
        
        # 发送配置变更信号
        self.config_changed.emit(key, value)
        
        self._log("INFO", f"配置更新: {key} = {value}")

    def _on_config_changed(self, key, value) -> None:
        """配置变更处理"""
        # 更新状态标签
        feature = key.split('.')[0] if len(key.split('.')) > 1 else key
        if feature in self._status_labels:
            self._status_labels[feature].setText(f"配置已更新: {key}")

    def _on_status_updated(self, feature, status) -> None:
        """状态更新处理"""
        if feature in self._status_labels:
            self._status_labels[feature].setText(f"状态: {status}")
        
        # 更新功能列表中的状态标签
        if feature in self._feature_buttons:
            btn, status_label = self._feature_buttons[feature]
            status_label.setText(status)

    def _on_log_message(self, level, message) -> None:
        """日志消息处理"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self._log_messages.append(log_entry)
        
        # 保持最近1000条日志
        if len(self._log_messages) > 1000:
            self._log_messages = self._log_messages[-1000:]
        
        # 更新日志显示（如果_log_text已创建）
        if hasattr(self, '_log_text') and self._log_text is not None:
            self._log_text.append(log_entry)
            
            # 自动滚动到底部
            scrollbar = self._log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def _log(self, level, message) -> None:
        """记录日志"""
        self.log_message.emit(level, message)

    def _refresh_status(self) -> None:
        """刷新状态"""
        # 这里应该从后端获取实际状态
        # 简化实现，只更新状态表格
        self._status_table.setRowCount(len(self._status_labels))
        for i, (feature, label) in enumerate(self._status_labels.items()):
            self._status_table.setItem(i, 0, QTableWidgetItem(feature))
            self._status_table.setItem(i, 1, QTableWidgetItem(label.text()))
            self._status_table.setItem(i, 2, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))

    def _save_audio_config(self) -> None:
        """保存声音处理配置"""
        self._log("INFO", "保存声音处理配置...")
        self._save_config()

    def _save_rag_config(self) -> None:
        """保存知识库配置"""
        self._log("INFO", "保存知识库配置...")
        self._save_config()

    def _save_roleplay_config(self) -> None:
        """保存角色扮演配置"""
        self._log("INFO", "保存角色扮演配置...")
        self._save_config()

    def _save_emotion_config(self) -> None:
        """保存情感系统配置"""
        self._log("INFO", "保存情感系统配置...")
        self._save_config()

    def _save_plugin_config(self) -> None:
        """保存插件系统配置"""
        self._log("INFO", "保存插件系统配置...")
        self._save_config()

    def _import_rag_document(self) -> None:
        """导入知识库文档"""
        self._log("INFO", "导入知识库文档...")

    def _create_roleplay_character(self) -> None:
        """创建角色扮演角色"""
        self._log("INFO", "创建角色扮演角色...")

    def _scan_plugins(self) -> None:
        """扫描插件"""
        self._log("INFO", "扫描插件...")