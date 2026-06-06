"""
社交Bot设置页面

提供多平台社交Bot配置界面，支持Discord、Telegram、QQ、微信、飞书、钉钉、Slack、LINE等平台的配置和管理。

设计参考: 直播设置页面的卡片式布局
- 左侧平台列表
- 右侧配置面板
- 实时状态显示

作者: 咕咕嘎嘎
日期: 2026-06-03
"""

import os
import json
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QScrollArea, QDoubleSpinBox, QSpinBox, QCheckBox,
    QComboBox, QLineEdit, QTextEdit, QGroupBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont, QColor

from qfluentwidgets import (
    Slider, PushButton, CaptionLabel, InfoBar, InfoBarPosition,
    TitleLabel, SubtitleLabel, CardWidget, FluentIcon,
    SwitchButton, LineEdit, ComboBox, SpinBox, DoubleSpinBox,
    TextEdit, ProgressBar, TabBar, ScrollArea
)

from app.shared_config import PROJECT_DIR
from gugu_native.widgets.lazy_page_mixin import LazyPageMixin
from gugu_native.widgets.skeleton_container import SkeletonContainer


class BotSettingsPage(QWidget, LazyPageMixin):
    """社交Bot设置页面 - 支持懒加载"""

    # 信号定义
    config_changed = Signal(str, object)  # 配置变更信号
    status_updated = Signal(str, str)     # 状态更新信号
    log_message = Signal(str, str)        # 日志消息信号

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        LazyPageMixin.__init__(self)
        self.setObjectName("botSettingsPage")
        self._backend = None
        self._config_widgets = {}
        self._status_labels = {}
        self._log_messages = []
        self._config_file = Path(PROJECT_DIR) / "app" / "config.yaml"
        self._config_data = {}
        
        # 骨架屏占位
        self._skeleton = SkeletonContainer("正在加载Bot设置...", self)
        self._skeleton.hide_skeleton()
        
        # 连接信号
        self.config_changed.connect(self._on_config_changed)
        self.status_updated.connect(self._on_status_updated)
        self.log_message.connect(self._on_log_message)

    def show_skeleton(self):
        self._skeleton.show_skeleton()

    def hide_skeleton(self):
        self._skeleton.hide_skeleton()

    def lazy_init(self):
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

    def set_backend(self, backend):
        """设置后端引用"""
        self._backend = backend

    def _load_config(self):
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

    def _save_config(self):
        """保存配置文件"""
        try:
            import yaml
            with open(self._config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self._config_data, f, allow_unicode=True, default_flow_style=False)
            self._log("INFO", "配置文件保存成功")
        except Exception as e:
            self._log("ERROR", f"配置文件保存失败: {e}")

    def _init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # 创建主分割器
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 上部：Bot配置区域
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # 左侧平台列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self._init_platform_list(left_layout)
        top_layout.addWidget(left_widget)
        
        # 右侧配置面板
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        right_panel = QWidget()
        self._right_layout = QVBoxLayout(right_panel)
        self._right_layout.setSpacing(10)
        
        # 创建各个平台的配置卡片
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

    def _init_platform_list(self, layout):
        """初始化左侧平台列表"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)
        card_layout.setContentsMargins(12, 12, 12, 12)

        card_layout.addWidget(SubtitleLabel("社交Bot"))

        platforms = [
            ("💜 Discord", "discord", "Discord服务器Bot"),
            ("✈️ Telegram", "telegram", "Telegram聊天Bot"),
            ("🐧 QQ", "qq", "QQ机器人"),
            ("💬 微信", "wechat", "微信公众号/企业微信"),
            ("🐦 飞书", "feishu", "飞书机器人"),
            ("📌 钉钉", "dingtalk", "钉钉机器人"),
            ("💼 Slack", "slack", "Slack工作区Bot"),
            ("🟢 LINE", "line", "LINE聊天Bot"),
        ]

        self._platform_buttons = {}
        for name, key, desc in platforms:
            btn_layout = QVBoxLayout()
            btn_layout.setSpacing(2)
            
            btn = PushButton(name)
            btn.setToolTip(desc)
            btn.clicked.connect(lambda checked, k=key: self._show_platform_config(k))
            btn_layout.addWidget(btn)
            
            # 状态标签
            status_label = CaptionLabel("未配置")
            status_label.setStyleSheet("color: gray;")
            btn_layout.addWidget(status_label)
            
            self._platform_buttons[key] = (btn, status_label)
            card_layout.addLayout(btn_layout)

        card_layout.addStretch()
        layout.addWidget(card)

    def _init_all_cards(self):
        """初始化所有配置卡片"""
        self._cards = {}
        
        # Discord配置卡片
        self._cards['discord'] = self._create_discord_card()
        self._right_layout.addWidget(self._cards['discord'])
        
        # Telegram配置卡片
        self._cards['telegram'] = self._create_telegram_card()
        self._right_layout.addWidget(self._cards['telegram'])
        
        # QQ配置卡片
        self._cards['qq'] = self._create_qq_card()
        self._right_layout.addWidget(self._cards['qq'])
        
        # 微信配置卡片
        self._cards['wechat'] = self._create_wechat_card()
        self._right_layout.addWidget(self._cards['wechat'])
        
        # 飞书配置卡片
        self._cards['feishu'] = self._create_feishu_card()
        self._right_layout.addWidget(self._cards['feishu'])
        
        # 钉钉配置卡片
        self._cards['dingtalk'] = self._create_dingtalk_card()
        self._right_layout.addWidget(self._cards['dingtalk'])
        
        # Slack配置卡片
        self._cards['slack'] = self._create_slack_card()
        self._right_layout.addWidget(self._cards['slack'])
        
        # LINE配置卡片
        self._cards['line'] = self._create_line_card()
        self._right_layout.addWidget(self._cards['line'])

    def _create_discord_card(self):
        """创建Discord配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("💜 Discord配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用Discord Bot"))
        self._config_widgets['discord_enabled'] = SwitchButton()
        self._config_widgets['discord_enabled'].setChecked(self._config_data.get('bot', {}).get('discord', {}).get('enabled', False))
        self._config_widgets['discord_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('bot.discord.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['discord_enabled'])
        card_layout.addLayout(enable_layout)

        # Bot Token
        token_layout = QHBoxLayout()
        token_layout.addWidget(CaptionLabel("Bot Token"))
        self._config_widgets['discord_token'] = LineEdit()
        self._config_widgets['discord_token'].setText(self._config_data.get('bot', {}).get('discord', {}).get('token', ''))
        self._config_widgets['discord_token'].setPlaceholderText("输入Discord Bot Token")
        self._config_widgets['discord_token'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['discord_token'].textChanged.connect(
            lambda text: self._update_config('bot.discord.token', text)
        )
        token_layout.addWidget(self._config_widgets['discord_token'])
        card_layout.addLayout(token_layout)

        # 服务器ID
        guild_layout = QHBoxLayout()
        guild_layout.addWidget(CaptionLabel("服务器ID"))
        self._config_widgets['discord_guild_id'] = LineEdit()
        self._config_widgets['discord_guild_id'].setText(self._config_data.get('bot', {}).get('discord', {}).get('guild_id', ''))
        self._config_widgets['discord_guild_id'].setPlaceholderText("输入服务器ID")
        self._config_widgets['discord_guild_id'].textChanged.connect(
            lambda text: self._update_config('bot.discord.guild_id', text)
        )
        guild_layout.addWidget(self._config_widgets['discord_guild_id'])
        card_layout.addLayout(guild_layout)

        # 命令前缀
        prefix_layout = QHBoxLayout()
        prefix_layout.addWidget(CaptionLabel("命令前缀"))
        self._config_widgets['discord_command_prefix'] = LineEdit()
        self._config_widgets['discord_command_prefix'].setText(self._config_data.get('bot', {}).get('discord', {}).get('command_prefix', '!'))
        self._config_widgets['discord_command_prefix'].setPlaceholderText("输入命令前缀")
        self._config_widgets['discord_command_prefix'].textChanged.connect(
            lambda text: self._update_config('bot.discord.command_prefix', text)
        )
        prefix_layout.addWidget(self._config_widgets['discord_command_prefix'])
        card_layout.addLayout(prefix_layout)

        # 状态显示
        self._status_labels['discord'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['discord'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接Bot")
        connect_btn.clicked.connect(lambda: self._connect_bot('discord'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_bot('discord'))
        btn_layout.addWidget(disconnect_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_telegram_card(self):
        """创建Telegram配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("✈️ Telegram配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用Telegram Bot"))
        self._config_widgets['telegram_enabled'] = SwitchButton()
        self._config_widgets['telegram_enabled'].setChecked(self._config_data.get('bot', {}).get('telegram', {}).get('enabled', False))
        self._config_widgets['telegram_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('bot.telegram.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['telegram_enabled'])
        card_layout.addLayout(enable_layout)

        # Bot Token
        token_layout = QHBoxLayout()
        token_layout.addWidget(CaptionLabel("Bot Token"))
        self._config_widgets['telegram_token'] = LineEdit()
        self._config_widgets['telegram_token'].setText(self._config_data.get('bot', {}).get('telegram', {}).get('token', ''))
        self._config_widgets['telegram_token'].setPlaceholderText("输入Telegram Bot Token")
        self._config_widgets['telegram_token'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['telegram_token'].textChanged.connect(
            lambda text: self._update_config('bot.telegram.token', text)
        )
        token_layout.addWidget(self._config_widgets['telegram_token'])
        card_layout.addLayout(token_layout)

        # Chat ID
        chat_layout = QHBoxLayout()
        chat_layout.addWidget(CaptionLabel("Chat ID"))
        self._config_widgets['telegram_chat_id'] = LineEdit()
        self._config_widgets['telegram_chat_id'].setText(self._config_data.get('bot', {}).get('telegram', {}).get('chat_id', ''))
        self._config_widgets['telegram_chat_id'].setPlaceholderText("输入Chat ID")
        self._config_widgets['telegram_chat_id'].textChanged.connect(
            lambda text: self._update_config('bot.telegram.chat_id', text)
        )
        chat_layout.addWidget(self._config_widgets['telegram_chat_id'])
        card_layout.addLayout(chat_layout)

        # 状态显示
        self._status_labels['telegram'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['telegram'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接Bot")
        connect_btn.clicked.connect(lambda: self._connect_bot('telegram'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_bot('telegram'))
        btn_layout.addWidget(disconnect_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_qq_card(self):
        """创建QQ配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🐧 QQ配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用QQ Bot"))
        self._config_widgets['qq_enabled'] = SwitchButton()
        self._config_widgets['qq_enabled'].setChecked(self._config_data.get('bot', {}).get('qq', {}).get('enabled', False))
        self._config_widgets['qq_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('bot.qq.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['qq_enabled'])
        card_layout.addLayout(enable_layout)

        # App ID
        app_id_layout = QHBoxLayout()
        app_id_layout.addWidget(CaptionLabel("App ID"))
        self._config_widgets['qq_app_id'] = LineEdit()
        self._config_widgets['qq_app_id'].setText(self._config_data.get('bot', {}).get('qq', {}).get('app_id', ''))
        self._config_widgets['qq_app_id'].setPlaceholderText("输入QQ App ID")
        self._config_widgets['qq_app_id'].textChanged.connect(
            lambda text: self._update_config('bot.qq.app_id', text)
        )
        app_id_layout.addWidget(self._config_widgets['qq_app_id'])
        card_layout.addLayout(app_id_layout)

        # Token
        token_layout = QHBoxLayout()
        token_layout.addWidget(CaptionLabel("Token"))
        self._config_widgets['qq_token'] = LineEdit()
        self._config_widgets['qq_token'].setText(self._config_data.get('bot', {}).get('qq', {}).get('token', ''))
        self._config_widgets['qq_token'].setPlaceholderText("输入QQ Token")
        self._config_widgets['qq_token'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['qq_token'].textChanged.connect(
            lambda text: self._update_config('bot.qq.token', text)
        )
        token_layout.addWidget(self._config_widgets['qq_token'])
        card_layout.addLayout(token_layout)

        # Secret
        secret_layout = QHBoxLayout()
        secret_layout.addWidget(CaptionLabel("Secret"))
        self._config_widgets['qq_secret'] = LineEdit()
        self._config_widgets['qq_secret'].setText(self._config_data.get('bot', {}).get('qq', {}).get('secret', ''))
        self._config_widgets['qq_secret'].setPlaceholderText("输入QQ Secret")
        self._config_widgets['qq_secret'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['qq_secret'].textChanged.connect(
            lambda text: self._update_config('bot.qq.secret', text)
        )
        secret_layout.addWidget(self._config_widgets['qq_secret'])
        card_layout.addLayout(secret_layout)

        # 状态显示
        self._status_labels['qq'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['qq'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接Bot")
        connect_btn.clicked.connect(lambda: self._connect_bot('qq'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_bot('qq'))
        btn_layout.addWidget(disconnect_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_wechat_card(self):
        """创建微信配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("💬 微信配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用微信 Bot"))
        self._config_widgets['wechat_enabled'] = SwitchButton()
        self._config_widgets['wechat_enabled'].setChecked(self._config_data.get('bot', {}).get('wechat', {}).get('enabled', False))
        self._config_widgets['wechat_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('bot.wechat.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['wechat_enabled'])
        card_layout.addLayout(enable_layout)

        # App ID
        app_id_layout = QHBoxLayout()
        app_id_layout.addWidget(CaptionLabel("App ID"))
        self._config_widgets['wechat_app_id'] = LineEdit()
        self._config_widgets['wechat_app_id'].setText(self._config_data.get('bot', {}).get('wechat', {}).get('app_id', ''))
        self._config_widgets['wechat_app_id'].setPlaceholderText("输入微信 App ID")
        self._config_widgets['wechat_app_id'].textChanged.connect(
            lambda text: self._update_config('bot.wechat.app_id', text)
        )
        app_id_layout.addWidget(self._config_widgets['wechat_app_id'])
        card_layout.addLayout(app_id_layout)

        # App Secret
        secret_layout = QHBoxLayout()
        secret_layout.addWidget(CaptionLabel("App Secret"))
        self._config_widgets['wechat_app_secret'] = LineEdit()
        self._config_widgets['wechat_app_secret'].setText(self._config_data.get('bot', {}).get('wechat', {}).get('app_secret', ''))
        self._config_widgets['wechat_app_secret'].setPlaceholderText("输入微信 App Secret")
        self._config_widgets['wechat_app_secret'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['wechat_app_secret'].textChanged.connect(
            lambda text: self._update_config('bot.wechat.app_secret', text)
        )
        secret_layout.addWidget(self._config_widgets['wechat_app_secret'])
        card_layout.addLayout(secret_layout)

        # Token
        token_layout = QHBoxLayout()
        token_layout.addWidget(CaptionLabel("Token"))
        self._config_widgets['wechat_token'] = LineEdit()
        self._config_widgets['wechat_token'].setText(self._config_data.get('bot', {}).get('wechat', {}).get('token', ''))
        self._config_widgets['wechat_token'].setPlaceholderText("输入微信 Token")
        self._config_widgets['wechat_token'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['wechat_token'].textChanged.connect(
            lambda text: self._update_config('bot.wechat.token', text)
        )
        token_layout.addWidget(self._config_widgets['wechat_token'])
        card_layout.addLayout(token_layout)

        # 状态显示
        self._status_labels['wechat'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['wechat'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接Bot")
        connect_btn.clicked.connect(lambda: self._connect_bot('wechat'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_bot('wechat'))
        btn_layout.addWidget(disconnect_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_feishu_card(self):
        """创建飞书配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🐦 飞书配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用飞书 Bot"))
        self._config_widgets['feishu_enabled'] = SwitchButton()
        self._config_widgets['feishu_enabled'].setChecked(self._config_data.get('bot', {}).get('feishu', {}).get('enabled', False))
        self._config_widgets['feishu_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('bot.feishu.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['feishu_enabled'])
        card_layout.addLayout(enable_layout)

        # App ID
        app_id_layout = QHBoxLayout()
        app_id_layout.addWidget(CaptionLabel("App ID"))
        self._config_widgets['feishu_app_id'] = LineEdit()
        self._config_widgets['feishu_app_id'].setText(self._config_data.get('bot', {}).get('feishu', {}).get('app_id', ''))
        self._config_widgets['feishu_app_id'].setPlaceholderText("输入飞书 App ID")
        self._config_widgets['feishu_app_id'].textChanged.connect(
            lambda text: self._update_config('bot.feishu.app_id', text)
        )
        app_id_layout.addWidget(self._config_widgets['feishu_app_id'])
        card_layout.addLayout(app_id_layout)

        # App Secret
        secret_layout = QHBoxLayout()
        secret_layout.addWidget(CaptionLabel("App Secret"))
        self._config_widgets['feishu_app_secret'] = LineEdit()
        self._config_widgets['feishu_app_secret'].setText(self._config_data.get('bot', {}).get('feishu', {}).get('app_secret', ''))
        self._config_widgets['feishu_app_secret'].setPlaceholderText("输入飞书 App Secret")
        self._config_widgets['feishu_app_secret'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['feishu_app_secret'].textChanged.connect(
            lambda text: self._update_config('bot.feishu.app_secret', text)
        )
        secret_layout.addWidget(self._config_widgets['feishu_app_secret'])
        card_layout.addLayout(secret_layout)

        # 状态显示
        self._status_labels['feishu'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['feishu'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接Bot")
        connect_btn.clicked.connect(lambda: self._connect_bot('feishu'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_bot('feishu'))
        btn_layout.addWidget(disconnect_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_dingtalk_card(self):
        """创建钉钉配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("📌 钉钉配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用钉钉 Bot"))
        self._config_widgets['dingtalk_enabled'] = SwitchButton()
        self._config_widgets['dingtalk_enabled'].setChecked(self._config_data.get('bot', {}).get('dingtalk', {}).get('enabled', False))
        self._config_widgets['dingtalk_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('bot.dingtalk.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['dingtalk_enabled'])
        card_layout.addLayout(enable_layout)

        # App Key
        app_key_layout = QHBoxLayout()
        app_key_layout.addWidget(CaptionLabel("App Key"))
        self._config_widgets['dingtalk_app_key'] = LineEdit()
        self._config_widgets['dingtalk_app_key'].setText(self._config_data.get('bot', {}).get('dingtalk', {}).get('app_key', ''))
        self._config_widgets['dingtalk_app_key'].setPlaceholderText("输入钉钉 App Key")
        self._config_widgets['dingtalk_app_key'].textChanged.connect(
            lambda text: self._update_config('bot.dingtalk.app_key', text)
        )
        app_key_layout.addWidget(self._config_widgets['dingtalk_app_key'])
        card_layout.addLayout(app_key_layout)

        # App Secret
        secret_layout = QHBoxLayout()
        secret_layout.addWidget(CaptionLabel("App Secret"))
        self._config_widgets['dingtalk_app_secret'] = LineEdit()
        self._config_widgets['dingtalk_app_secret'].setText(self._config_data.get('bot', {}).get('dingtalk', {}).get('app_secret', ''))
        self._config_widgets['dingtalk_app_secret'].setPlaceholderText("输入钉钉 App Secret")
        self._config_widgets['dingtalk_app_secret'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['dingtalk_app_secret'].textChanged.connect(
            lambda text: self._update_config('bot.dingtalk.app_secret', text)
        )
        secret_layout.addWidget(self._config_widgets['dingtalk_app_secret'])
        card_layout.addLayout(secret_layout)

        # 状态显示
        self._status_labels['dingtalk'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['dingtalk'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接Bot")
        connect_btn.clicked.connect(lambda: self._connect_bot('dingtalk'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_bot('dingtalk'))
        btn_layout.addWidget(disconnect_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_slack_card(self):
        """创建Slack配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("💼 Slack配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用Slack Bot"))
        self._config_widgets['slack_enabled'] = SwitchButton()
        self._config_widgets['slack_enabled'].setChecked(self._config_data.get('bot', {}).get('slack', {}).get('enabled', False))
        self._config_widgets['slack_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('bot.slack.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['slack_enabled'])
        card_layout.addLayout(enable_layout)

        # Bot Token
        token_layout = QHBoxLayout()
        token_layout.addWidget(CaptionLabel("Bot Token"))
        self._config_widgets['slack_token'] = LineEdit()
        self._config_widgets['slack_token'].setText(self._config_data.get('bot', {}).get('slack', {}).get('token', ''))
        self._config_widgets['slack_token'].setPlaceholderText("输入Slack Bot Token")
        self._config_widgets['slack_token'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['slack_token'].textChanged.connect(
            lambda text: self._update_config('bot.slack.token', text)
        )
        token_layout.addWidget(self._config_widgets['slack_token'])
        card_layout.addLayout(token_layout)

        # App Token
        app_token_layout = QHBoxLayout()
        app_token_layout.addWidget(CaptionLabel("App Token"))
        self._config_widgets['slack_app_token'] = LineEdit()
        self._config_widgets['slack_app_token'].setText(self._config_data.get('bot', {}).get('slack', {}).get('app_token', ''))
        self._config_widgets['slack_app_token'].setPlaceholderText("输入Slack App Token")
        self._config_widgets['slack_app_token'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['slack_app_token'].textChanged.connect(
            lambda text: self._update_config('bot.slack.app_token', text)
        )
        app_token_layout.addWidget(self._config_widgets['slack_app_token'])
        card_layout.addLayout(app_token_layout)

        # 状态显示
        self._status_labels['slack'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['slack'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接Bot")
        connect_btn.clicked.connect(lambda: self._connect_bot('slack'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_bot('slack'))
        btn_layout.addWidget(disconnect_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_line_card(self):
        """创建LINE配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🟢 LINE配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用LINE Bot"))
        self._config_widgets['line_enabled'] = SwitchButton()
        self._config_widgets['line_enabled'].setChecked(self._config_data.get('bot', {}).get('line', {}).get('enabled', False))
        self._config_widgets['line_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('bot.line.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['line_enabled'])
        card_layout.addLayout(enable_layout)

        # Channel Access Token
        token_layout = QHBoxLayout()
        token_layout.addWidget(CaptionLabel("Channel Access Token"))
        self._config_widgets['line_channel_access_token'] = LineEdit()
        self._config_widgets['line_channel_access_token'].setText(self._config_data.get('bot', {}).get('line', {}).get('channel_access_token', ''))
        self._config_widgets['line_channel_access_token'].setPlaceholderText("输入LINE Channel Access Token")
        self._config_widgets['line_channel_access_token'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['line_channel_access_token'].textChanged.connect(
            lambda text: self._update_config('bot.line.channel_access_token', text)
        )
        token_layout.addWidget(self._config_widgets['line_channel_access_token'])
        card_layout.addLayout(token_layout)

        # Channel Secret
        secret_layout = QHBoxLayout()
        secret_layout.addWidget(CaptionLabel("Channel Secret"))
        self._config_widgets['line_channel_secret'] = LineEdit()
        self._config_widgets['line_channel_secret'].setText(self._config_data.get('bot', {}).get('line', {}).get('channel_secret', ''))
        self._config_widgets['line_channel_secret'].setPlaceholderText("输入LINE Channel Secret")
        self._config_widgets['line_channel_secret'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['line_channel_secret'].textChanged.connect(
            lambda text: self._update_config('bot.line.channel_secret', text)
        )
        secret_layout.addWidget(self._config_widgets['line_channel_secret'])
        card_layout.addLayout(secret_layout)

        # 状态显示
        self._status_labels['line'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['line'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接Bot")
        connect_btn.clicked.connect(lambda: self._connect_bot('line'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_bot('line'))
        btn_layout.addWidget(disconnect_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _init_bottom_panel(self, layout):
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
        self._status_table.setColumnCount(4)
        self._status_table.setHorizontalHeaderLabels(["平台", "状态", "配置", "最后更新"])
        self._status_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        status_layout.addWidget(self._status_table)
        tab_widget.addTab(status_widget, "状态")
        
        layout.addWidget(tab_widget)

    def _show_platform_config(self, platform_key):
        """显示平台配置"""
        # 隐藏所有卡片
        for key, card in self._cards.items():
            card.setVisible(key == platform_key)
        
        # 更新按钮状态
        for key, (btn, status_label) in self._platform_buttons.items():
            btn.setChecked(key == platform_key)
        
        self._log("DEBUG", f"切换到平台配置: {platform_key}")

    def _update_config(self, key, value):
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

    def _on_config_changed(self, key, value):
        """配置变更处理"""
        # 更新状态标签
        platform = key.split('.')[1] if len(key.split('.')) > 1 else key
        if platform in self._status_labels:
            self._status_labels[platform].setText(f"配置已更新: {key}")

    def _on_status_updated(self, platform, status):
        """状态更新处理"""
        if platform in self._status_labels:
            self._status_labels[platform].setText(f"状态: {status}")
        
        # 更新平台列表中的状态标签
        if platform in self._platform_buttons:
            btn, status_label = self._platform_buttons[platform]
            status_label.setText(status)

    def _on_log_message(self, level, message):
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

    def _log(self, level, message):
        """记录日志"""
        self.log_message.emit(level, message)

    def _refresh_status(self):
        """刷新状态"""
        # 这里应该从后端获取实际状态
        # 简化实现，只更新状态表格
        self._status_table.setRowCount(len(self._status_labels))
        for i, (platform, label) in enumerate(self._status_labels.items()):
            self._status_table.setItem(i, 0, QTableWidgetItem(platform))
            self._status_table.setItem(i, 1, QTableWidgetItem(label.text()))
            self._status_table.setItem(i, 2, QTableWidgetItem(self._config_data.get('bot', {}).get(platform, {}).get('token', '')[:10] + '...' if self._config_data.get('bot', {}).get(platform, {}).get('token', '') else ''))
            self._status_table.setItem(i, 3, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))

    def _connect_bot(self, platform):
        """连接Bot"""
        self._log("INFO", f"正在连接{platform} Bot...")
        # 这里应该调用后端的连接功能

    def _disconnect_bot(self, platform):
        """断开Bot连接"""
        self._log("INFO", f"正在断开{platform} Bot连接...")
        # 这里应该调用后端的断开功能