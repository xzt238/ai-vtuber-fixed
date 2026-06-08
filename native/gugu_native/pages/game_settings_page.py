"""
游戏设置页面

提供多游戏配置界面，支持Minecraft、Factorio、Terraria、Stardew Valley等游戏的配置和管理。

设计参考: 直播设置页面的卡片式布局
- 左侧游戏列表
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


class GameSettingsPage(QWidget, LazyPageMixin):
    """游戏设置页面 - 支持懒加载"""

    # 信号定义
    config_changed = Signal(str, object)  # 配置变更信号
    status_updated = Signal(str, str)     # 状态更新信号
    log_message = Signal(str, str)        # 日志消息信号

    def __init__(self, parent=None) -> None:
        """内部方法"""
        QWidget.__init__(self, parent)
        LazyPageMixin.__init__(self)
        self.setObjectName("gameSettingsPage")
        self._backend = None
        self._config_widgets = {}
        self._status_labels = {}
        self._log_messages = []
        self._config_file = Path(PROJECT_DIR) / "app" / "config.yaml"
        self._config_data = {}
        
        # 骨架屏占位
        self._skeleton = SkeletonContainer("正在加载游戏设置...", self)
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
        
        # 上部：游戏配置区域
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # 左侧游戏列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self._init_game_list(left_layout)
        top_layout.addWidget(left_widget)
        
        # 右侧配置面板
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        right_panel = QWidget()
        self._right_layout = QVBoxLayout(right_panel)
        self._right_layout.setSpacing(10)
        
        # 创建各个游戏的配置卡片
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

    def _init_game_list(self, layout) -> None:
        """初始化左侧游戏列表"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)
        card_layout.setContentsMargins(12, 12, 12, 12)

        card_layout.addWidget(SubtitleLabel("游戏集成"))

        games = [
            ("⛏️ Minecraft", "minecraft", "Minecraft游戏集成"),
            ("🏭 Factorio", "factorio", "Factorio游戏集成"),
            ("🌳 Terraria", "terraria", "Terraria游戏集成"),
            ("🌾 Stardew Valley", "stardew_valley", "Stardew Valley游戏集成"),
            ("🎮 通用屏幕识别", "generic", "通用屏幕识别方案"),
        ]

        self._game_buttons = {}
        for name, key, desc in games:
            btn_layout = QVBoxLayout()
            btn_layout.setSpacing(2)
            
            btn = PushButton(name)
            btn.setToolTip(desc)
            btn.clicked.connect(lambda checked, k=key: self._show_game_config(k))
            btn_layout.addWidget(btn)
            
            # 状态标签
            status_label = CaptionLabel("未配置")
            status_label.setStyleSheet("color: gray;")
            btn_layout.addWidget(status_label)
            
            self._game_buttons[key] = (btn, status_label)
            card_layout.addLayout(btn_layout)

        card_layout.addStretch()
        layout.addWidget(card)

    def _init_all_cards(self) -> None:
        """初始化所有配置卡片"""
        self._cards = {}
        
        # Minecraft配置卡片
        self._cards['minecraft'] = self._create_minecraft_card()
        self._right_layout.addWidget(self._cards['minecraft'])
        
        # Factorio配置卡片
        self._cards['factorio'] = self._create_factorio_card()
        self._right_layout.addWidget(self._cards['factorio'])
        
        # Terraria配置卡片
        self._cards['terraria'] = self._create_terraria_card()
        self._right_layout.addWidget(self._cards['terraria'])
        
        # Stardew Valley配置卡片
        self._cards['stardew_valley'] = self._create_stardew_valley_card()
        self._right_layout.addWidget(self._cards['stardew_valley'])
        
        # 通用屏幕识别配置卡片
        self._cards['generic'] = self._create_generic_card()
        self._right_layout.addWidget(self._cards['generic'])

    def _create_minecraft_card(self) -> None:
        """创建Minecraft配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("⛏️ Minecraft配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用Minecraft"))
        self._config_widgets['minecraft_enabled'] = SwitchButton()
        self._config_widgets['minecraft_enabled'].setChecked(self._config_data.get('game', {}).get('minecraft', {}).get('enabled', False))
        self._config_widgets['minecraft_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('game.minecraft.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['minecraft_enabled'])
        card_layout.addLayout(enable_layout)

        # 服务器地址
        host_layout = QHBoxLayout()
        host_layout.addWidget(CaptionLabel("服务器地址"))
        self._config_widgets['minecraft_host'] = LineEdit()
        self._config_widgets['minecraft_host'].setText(self._config_data.get('game', {}).get('minecraft', {}).get('host', 'localhost'))
        self._config_widgets['minecraft_host'].setPlaceholderText("输入服务器地址")
        self._config_widgets['minecraft_host'].textChanged.connect(
            lambda text: self._update_config('game.minecraft.host', text)
        )
        host_layout.addWidget(self._config_widgets['minecraft_host'])
        card_layout.addLayout(host_layout)

        # 服务器端口
        port_layout = QHBoxLayout()
        port_layout.addWidget(CaptionLabel("服务器端口"))
        self._config_widgets['minecraft_port'] = SpinBox()
        self._config_widgets['minecraft_port'].setRange(1, 65535)
        self._config_widgets['minecraft_port'].setValue(self._config_data.get('game', {}).get('minecraft', {}).get('port', 25565))
        self._config_widgets['minecraft_port'].valueChanged.connect(
            lambda value: self._update_config('game.minecraft.port', value)
        )
        port_layout.addWidget(self._config_widgets['minecraft_port'])
        card_layout.addLayout(port_layout)

        # 用户名
        username_layout = QHBoxLayout()
        username_layout.addWidget(CaptionLabel("用户名"))
        self._config_widgets['minecraft_username'] = LineEdit()
        self._config_widgets['minecraft_username'].setText(self._config_data.get('game', {}).get('minecraft', {}).get('username', 'AI_VTuber'))
        self._config_widgets['minecraft_username'].setPlaceholderText("输入用户名")
        self._config_widgets['minecraft_username'].textChanged.connect(
            lambda text: self._update_config('game.minecraft.username', text)
        )
        username_layout.addWidget(self._config_widgets['minecraft_username'])
        card_layout.addLayout(username_layout)

        # 密码
        password_layout = QHBoxLayout()
        password_layout.addWidget(CaptionLabel("密码"))
        self._config_widgets['minecraft_password'] = LineEdit()
        self._config_widgets['minecraft_password'].setText(self._config_data.get('game', {}).get('minecraft', {}).get('password', ''))
        self._config_widgets['minecraft_password'].setPlaceholderText("输入密码（可选）")
        self._config_widgets['minecraft_password'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['minecraft_password'].textChanged.connect(
            lambda text: self._update_config('game.minecraft.password', text)
        )
        password_layout.addWidget(self._config_widgets['minecraft_password'])
        card_layout.addLayout(password_layout)

        # 游戏版本
        version_layout = QHBoxLayout()
        version_layout.addWidget(CaptionLabel("游戏版本"))
        self._config_widgets['minecraft_version'] = ComboBox()
        self._config_widgets['minecraft_version'].addItems(["1.20.1", "1.20.2", "1.20.3", "1.20.4", "1.21", "1.21.1"])
        self._config_widgets['minecraft_version'].setCurrentText(self._config_data.get('game', {}).get('minecraft', {}).get('version', '1.20.1'))
        self._config_widgets['minecraft_version'].currentTextChanged.connect(
            lambda text: self._update_config('game.minecraft.version', text)
        )
        version_layout.addWidget(self._config_widgets['minecraft_version'])
        card_layout.addLayout(version_layout)

        # 状态显示
        self._status_labels['minecraft'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['minecraft'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接服务器")
        connect_btn.clicked.connect(lambda: self._connect_game('minecraft'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_game('minecraft'))
        btn_layout.addWidget(disconnect_btn)
        
        test_btn = PushButton("测试连接")
        test_btn.clicked.connect(lambda: self._test_game('minecraft'))
        btn_layout.addWidget(test_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_factorio_card(self) -> None:
        """创建Factorio配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🏭 Factorio配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用Factorio"))
        self._config_widgets['factorio_enabled'] = SwitchButton()
        self._config_widgets['factorio_enabled'].setChecked(self._config_data.get('game', {}).get('factorio', {}).get('enabled', False))
        self._config_widgets['factorio_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('game.factorio.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['factorio_enabled'])
        card_layout.addLayout(enable_layout)

        # RCON服务器地址
        host_layout = QHBoxLayout()
        host_layout.addWidget(CaptionLabel("RCON服务器地址"))
        self._config_widgets['factorio_host'] = LineEdit()
        self._config_widgets['factorio_host'].setText(self._config_data.get('game', {}).get('factorio', {}).get('host', 'localhost'))
        self._config_widgets['factorio_host'].setPlaceholderText("输入RCON服务器地址")
        self._config_widgets['factorio_host'].textChanged.connect(
            lambda text: self._update_config('game.factorio.host', text)
        )
        host_layout.addWidget(self._config_widgets['factorio_host'])
        card_layout.addLayout(host_layout)

        # RCON端口
        port_layout = QHBoxLayout()
        port_layout.addWidget(CaptionLabel("RCON端口"))
        self._config_widgets['factorio_port'] = SpinBox()
        self._config_widgets['factorio_port'].setRange(1, 65535)
        self._config_widgets['factorio_port'].setValue(self._config_data.get('game', {}).get('factorio', {}).get('port', 27015))
        self._config_widgets['factorio_port'].valueChanged.connect(
            lambda value: self._update_config('game.factorio.port', value)
        )
        port_layout.addWidget(self._config_widgets['factorio_port'])
        card_layout.addLayout(port_layout)

        # RCON密码
        password_layout = QHBoxLayout()
        password_layout.addWidget(CaptionLabel("RCON密码"))
        self._config_widgets['factorio_password'] = LineEdit()
        self._config_widgets['factorio_password'].setText(self._config_data.get('game', {}).get('factorio', {}).get('password', ''))
        self._config_widgets['factorio_password'].setPlaceholderText("输入RCON密码")
        self._config_widgets['factorio_password'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['factorio_password'].textChanged.connect(
            lambda text: self._update_config('game.factorio.password', text)
        )
        password_layout.addWidget(self._config_widgets['factorio_password'])
        card_layout.addLayout(password_layout)

        # 状态显示
        self._status_labels['factorio'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['factorio'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接RCON")
        connect_btn.clicked.connect(lambda: self._connect_game('factorio'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_game('factorio'))
        btn_layout.addWidget(disconnect_btn)
        
        test_btn = PushButton("测试连接")
        test_btn.clicked.connect(lambda: self._test_game('factorio'))
        btn_layout.addWidget(test_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_terraria_card(self) -> None:
        """创建Terraria配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🌳 Terraria配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用Terraria"))
        self._config_widgets['terraria_enabled'] = SwitchButton()
        self._config_widgets['terraria_enabled'].setChecked(self._config_data.get('game', {}).get('terraria', {}).get('enabled', False))
        self._config_widgets['terraria_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('game.terraria.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['terraria_enabled'])
        card_layout.addLayout(enable_layout)

        # 服务器地址
        host_layout = QHBoxLayout()
        host_layout.addWidget(CaptionLabel("服务器地址"))
        self._config_widgets['terraria_host'] = LineEdit()
        self._config_widgets['terraria_host'].setText(self._config_data.get('game', {}).get('terraria', {}).get('host', 'localhost'))
        self._config_widgets['terraria_host'].setPlaceholderText("输入服务器地址")
        self._config_widgets['terraria_host'].textChanged.connect(
            lambda text: self._update_config('game.terraria.host', text)
        )
        host_layout.addWidget(self._config_widgets['terraria_host'])
        card_layout.addLayout(host_layout)

        # 服务器端口
        port_layout = QHBoxLayout()
        port_layout.addWidget(CaptionLabel("服务器端口"))
        self._config_widgets['terraria_port'] = SpinBox()
        self._config_widgets['terraria_port'].setRange(1, 65535)
        self._config_widgets['terraria_port'].setValue(self._config_data.get('game', {}).get('terraria', {}).get('port', 7777))
        self._config_widgets['terraria_port'].valueChanged.connect(
            lambda value: self._update_config('game.terraria.port', value)
        )
        port_layout.addWidget(self._config_widgets['terraria_port'])
        card_layout.addLayout(port_layout)

        # 密码
        password_layout = QHBoxLayout()
        password_layout.addWidget(CaptionLabel("密码"))
        self._config_widgets['terraria_password'] = LineEdit()
        self._config_widgets['terraria_password'].setText(self._config_data.get('game', {}).get('terraria', {}).get('password', ''))
        self._config_widgets['terraria_password'].setPlaceholderText("输入密码（可选）")
        self._config_widgets['terraria_password'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['terraria_password'].textChanged.connect(
            lambda text: self._update_config('game.terraria.password', text)
        )
        password_layout.addWidget(self._config_widgets['terraria_password'])
        card_layout.addLayout(password_layout)

        # 状态显示
        self._status_labels['terraria'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['terraria'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接服务器")
        connect_btn.clicked.connect(lambda: self._connect_game('terraria'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_game('terraria'))
        btn_layout.addWidget(disconnect_btn)
        
        test_btn = PushButton("测试连接")
        test_btn.clicked.connect(lambda: self._test_game('terraria'))
        btn_layout.addWidget(test_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_stardew_valley_card(self) -> None:
        """创建Stardew Valley配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🌾 Stardew Valley配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用Stardew Valley"))
        self._config_widgets['stardew_valley_enabled'] = SwitchButton()
        self._config_widgets['stardew_valley_enabled'].setChecked(self._config_data.get('game', {}).get('stardew_valley', {}).get('enabled', False))
        self._config_widgets['stardew_valley_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('game.stardew_valley.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['stardew_valley_enabled'])
        card_layout.addLayout(enable_layout)

        # SMAPI服务器地址
        host_layout = QHBoxLayout()
        host_layout.addWidget(CaptionLabel("SMAPI服务器地址"))
        self._config_widgets['stardew_valley_host'] = LineEdit()
        self._config_widgets['stardew_valley_host'].setText(self._config_data.get('game', {}).get('stardew_valley', {}).get('host', 'localhost'))
        self._config_widgets['stardew_valley_host'].setPlaceholderText("输入SMAPI服务器地址")
        self._config_widgets['stardew_valley_host'].textChanged.connect(
            lambda text: self._update_config('game.stardew_valley.host', text)
        )
        host_layout.addWidget(self._config_widgets['stardew_valley_host'])
        card_layout.addLayout(host_layout)

        # SMAPI端口
        port_layout = QHBoxLayout()
        port_layout.addWidget(CaptionLabel("SMAPI端口"))
        self._config_widgets['stardew_valley_port'] = SpinBox()
        self._config_widgets['stardew_valley_port'].setRange(1, 65535)
        self._config_widgets['stardew_valley_port'].setValue(self._config_data.get('game', {}).get('stardew_valley', {}).get('port', 24642))
        self._config_widgets['stardew_valley_port'].valueChanged.connect(
            lambda value: self._update_config('game.stardew_valley.port', value)
        )
        port_layout.addWidget(self._config_widgets['stardew_valley_port'])
        card_layout.addLayout(port_layout)

        # API Key
        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(CaptionLabel("API Key"))
        self._config_widgets['stardew_valley_api_key'] = LineEdit()
        self._config_widgets['stardew_valley_api_key'].setText(self._config_data.get('game', {}).get('stardew_valley', {}).get('api_key', ''))
        self._config_widgets['stardew_valley_api_key'].setPlaceholderText("输入API Key（可选）")
        self._config_widgets['stardew_valley_api_key'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['stardew_valley_api_key'].textChanged.connect(
            lambda text: self._update_config('game.stardew_valley.api_key', text)
        )
        api_key_layout.addWidget(self._config_widgets['stardew_valley_api_key'])
        card_layout.addLayout(api_key_layout)

        # 状态显示
        self._status_labels['stardew_valley'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['stardew_valley'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接SMAPI")
        connect_btn.clicked.connect(lambda: self._connect_game('stardew_valley'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_game('stardew_valley'))
        btn_layout.addWidget(disconnect_btn)
        
        test_btn = PushButton("测试连接")
        test_btn.clicked.connect(lambda: self._test_game('stardew_valley'))
        btn_layout.addWidget(test_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_generic_card(self) -> None:
        """创建通用屏幕识别配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🎮 通用屏幕识别配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用屏幕识别"))
        self._config_widgets['generic_enabled'] = SwitchButton()
        self._config_widgets['generic_enabled'].setChecked(self._config_data.get('game', {}).get('generic', {}).get('enabled', False))
        self._config_widgets['generic_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('game.generic.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['generic_enabled'])
        card_layout.addLayout(enable_layout)

        # 截图间隔
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(CaptionLabel("截图间隔（毫秒）"))
        self._config_widgets['generic_interval'] = SpinBox()
        self._config_widgets['generic_interval'].setRange(100, 5000)
        self._config_widgets['generic_interval'].setValue(self._config_data.get('game', {}).get('generic', {}).get('interval', 500))
        self._config_widgets['generic_interval'].valueChanged.connect(
            lambda value: self._update_config('game.generic.interval', value)
        )
        interval_layout.addWidget(self._config_widgets['generic_interval'])
        card_layout.addLayout(interval_layout)

        # OCR引擎
        ocr_layout = QHBoxLayout()
        ocr_layout.addWidget(CaptionLabel("OCR引擎"))
        self._config_widgets['generic_ocr'] = ComboBox()
        self._config_widgets['generic_ocr'].addItems(["PaddleOCR", "EasyOCR", "RapidOCR"])
        self._config_widgets['generic_ocr'].setCurrentText(self._config_data.get('game', {}).get('generic', {}).get('ocr_engine', 'PaddleOCR'))
        self._config_widgets['generic_ocr'].currentTextChanged.connect(
            lambda text: self._update_config('game.generic.ocr_engine', text)
        )
        ocr_layout.addWidget(self._config_widgets['generic_ocr'])
        card_layout.addLayout(ocr_layout)

        # 状态显示
        self._status_labels['generic'] = CaptionLabel("状态: 未启用")
        card_layout.addWidget(self._status_labels['generic'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        start_btn = PushButton("启动识别")
        start_btn.clicked.connect(lambda: self._start_generic())
        btn_layout.addWidget(start_btn)
        
        stop_btn = PushButton("停止识别")
        stop_btn.clicked.connect(lambda: self._stop_generic())
        btn_layout.addWidget(stop_btn)
        
        test_btn = PushButton("测试截图")
        test_btn.clicked.connect(lambda: self._test_generic())
        btn_layout.addWidget(test_btn)
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
        self._status_table.setColumnCount(4)
        self._status_table.setHorizontalHeaderLabels(["游戏", "状态", "服务器", "最后更新"])
        self._status_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        status_layout.addWidget(self._status_table)
        tab_widget.addTab(status_widget, "状态")
        
        # 游戏状态标签页
        game_state_widget = QWidget()
        game_state_layout = QVBoxLayout(game_state_widget)
        self._game_state_text = QTextEdit()
        self._game_state_text.setReadOnly(True)
        self._game_state_text.setFont(QFont("Consolas", 9))
        game_state_layout.addWidget(self._game_state_text)
        tab_widget.addTab(game_state_widget, "游戏状态")
        
        layout.addWidget(tab_widget)

    def _show_game_config(self, game_key) -> None:
        """显示游戏配置"""
        # 隐藏所有卡片
        for key, card in self._cards.items():
            card.setVisible(key == game_key)
        
        # 更新按钮状态
        for key, (btn, status_label) in self._game_buttons.items():
            btn.setChecked(key == game_key)
        
        self._log("DEBUG", f"切换到游戏配置: {game_key}")

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
        game = key.split('.')[1] if len(key.split('.')) > 1 else key
        if game in self._status_labels:
            self._status_labels[game].setText(f"配置已更新: {key}")

    def _on_status_updated(self, game, status) -> None:
        """状态更新处理"""
        if game in self._status_labels:
            self._status_labels[game].setText(f"状态: {status}")
        
        # 更新游戏列表中的状态标签
        if game in self._game_buttons:
            btn, status_label = self._game_buttons[game]
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
        for i, (game, label) in enumerate(self._status_labels.items()):
            self._status_table.setItem(i, 0, QTableWidgetItem(game))
            self._status_table.setItem(i, 1, QTableWidgetItem(label.text()))
            self._status_table.setItem(i, 2, QTableWidgetItem(self._config_data.get('game', {}).get(game, {}).get('host', '')))
            self._status_table.setItem(i, 3, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))

    def _connect_game(self, game) -> None:
        """连接游戏"""
        self._log("INFO", f"正在连接{game}...")
        # 这里应该调用后端的连接功能

    def _disconnect_game(self, game) -> None:
        """断开游戏连接"""
        self._log("INFO", f"正在断开{game}连接...")
        # 这里应该调用后端的断开功能

    def _test_game(self, game) -> None:
        """测试游戏连接"""
        self._log("INFO", f"正在测试{game}连接...")
        # 这里应该调用后端的测试功能

    def _start_generic(self) -> None:
        """启动通用屏幕识别"""
        self._log("INFO", "正在启动通用屏幕识别...")
        # 这里应该调用后端的启动功能

    def _stop_generic(self) -> None:
        """停止通用屏幕识别"""
        self._log("INFO", "正在停止通用屏幕识别...")
        # 这里应该调用后端的停止功能

    def _test_generic(self) -> None:
        """测试通用屏幕识别"""
        self._log("INFO", "正在测试通用屏幕识别...")
        # 这里应该调用后端的测试功能