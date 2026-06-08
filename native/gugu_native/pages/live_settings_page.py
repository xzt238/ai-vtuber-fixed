"""
直播平台设置页面

提供多平台直播配置界面，支持Bilibili、抖音、快手等平台的配置和管理。

设计参考: VRM设置页面的卡片式布局
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


class LiveSettingsPage(QWidget, LazyPageMixin):
    """直播平台设置页面 - 支持懒加载"""

    # 信号定义
    config_changed = Signal(str, object)  # 配置变更信号
    status_updated = Signal(str, str)     # 状态更新信号
    log_message = Signal(str, str)        # 日志消息信号

    def __init__(self, parent=None) -> None:
        """内部方法"""
        QWidget.__init__(self, parent)
        LazyPageMixin.__init__(self)
        self.setObjectName("liveSettingsPage")
        self._backend = None
        self._config_widgets = {}
        self._status_labels = {}
        self._log_messages = []
        self._config_file = Path(PROJECT_DIR) / "app" / "config.yaml"
        self._config_data = {}
        
        # 骨架屏占位
        self._skeleton = SkeletonContainer("正在加载直播设置...", self)
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
        
        # 上部：平台配置区域
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

    def _init_platform_list(self, layout) -> None:
        """初始化左侧平台列表"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)
        card_layout.setContentsMargins(12, 12, 12, 12)

        card_layout.addWidget(SubtitleLabel("直播平台"))

        platforms = [
            ("📺 Bilibili", "bilibili", "Bilibili直播弹幕互动"),
            ("🎵 抖音", "douyin", "抖音直播弹幕互动"),
            ("🎬 快手", "kuaishou", "快手直播弹幕互动"),
            ("🐟 斗鱼", "douyu", "斗鱼直播弹幕互动"),
            ("🐯 虎牙", "huya", "虎牙直播弹幕互动"),
            ("📹 YouTube", "youtube", "YouTube直播弹幕互动"),
            ("💜 Twitch", "twitch", "Twitch直播弹幕互动"),
            ("🎬 TikTok", "tiktok", "TikTok直播弹幕互动"),
            ("📱 微信视频号", "weixin_video", "微信视频号直播弹幕互动"),
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

    def _init_all_cards(self) -> None:
        """初始化所有配置卡片"""
        self._cards = {}
        
        # Bilibili配置卡片
        self._cards['bilibili'] = self._create_bilibili_card()
        self._right_layout.addWidget(self._cards['bilibili'])
        
        # 抖音配置卡片
        self._cards['douyin'] = self._create_douyin_card()
        self._right_layout.addWidget(self._cards['douyin'])
        
        # 快手配置卡片
        self._cards['kuaishou'] = self._create_kuaishou_card()
        self._right_layout.addWidget(self._cards['kuaishou'])
        
        # 斗鱼配置卡片
        self._cards['douyu'] = self._create_douyu_card()
        self._right_layout.addWidget(self._cards['douyu'])
        
        # 虎牙配置卡片
        self._cards['huya'] = self._create_huya_card()
        self._right_layout.addWidget(self._cards['huya'])
        
        # YouTube配置卡片
        self._cards['youtube'] = self._create_youtube_card()
        self._right_layout.addWidget(self._cards['youtube'])
        
        # Twitch配置卡片
        self._cards['twitch'] = self._create_twitch_card()
        self._right_layout.addWidget(self._cards['twitch'])
        
        # TikTok配置卡片
        self._cards['tiktok'] = self._create_tiktok_card()
        self._right_layout.addWidget(self._cards['tiktok'])
        
        # 微信视频号配置卡片
        self._cards['weixin_video'] = self._create_weixin_video_card()
        self._right_layout.addWidget(self._cards['weixin_video'])

    def _create_bilibili_card(self) -> None:
        """创建Bilibili配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("📺 Bilibili直播配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用Bilibili直播"))
        self._config_widgets['bilibili_enabled'] = SwitchButton()
        self._config_widgets['bilibili_enabled'].setChecked(self._config_data.get('live', {}).get('bilibili', {}).get('enabled', False))
        self._config_widgets['bilibili_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('live.bilibili.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['bilibili_enabled'])
        card_layout.addLayout(enable_layout)

        # 直播间ID
        room_id_layout = QHBoxLayout()
        room_id_layout.addWidget(CaptionLabel("直播间ID"))
        self._config_widgets['bilibili_room_id'] = LineEdit()
        self._config_widgets['bilibili_room_id'].setText(self._config_data.get('live', {}).get('bilibili', {}).get('room_id', ''))
        self._config_widgets['bilibili_room_id'].setPlaceholderText("输入Bilibili直播间ID")
        self._config_widgets['bilibili_room_id'].textChanged.connect(
            lambda text: self._update_config('live.bilibili.room_id', text)
        )
        room_id_layout.addWidget(self._config_widgets['bilibili_room_id'])
        card_layout.addLayout(room_id_layout)

        # 用户UID
        uid_layout = QHBoxLayout()
        uid_layout.addWidget(CaptionLabel("用户UID"))
        self._config_widgets['bilibili_uid'] = LineEdit()
        self._config_widgets['bilibili_uid'].setText(str(self._config_data.get('live', {}).get('bilibili', {}).get('uid', '')))
        self._config_widgets['bilibili_uid'].setPlaceholderText("输入用户UID")
        self._config_widgets['bilibili_uid'].textChanged.connect(
            lambda text: self._update_config('live.bilibili.uid', text)
        )
        uid_layout.addWidget(self._config_widgets['bilibili_uid'])
        card_layout.addLayout(uid_layout)

        # 认证Token
        token_layout = QHBoxLayout()
        token_layout.addWidget(CaptionLabel("认证Token"))
        self._config_widgets['bilibili_token'] = LineEdit()
        self._config_widgets['bilibili_token'].setText(self._config_data.get('live', {}).get('bilibili', {}).get('token', ''))
        self._config_widgets['bilibili_token'].setPlaceholderText("输入认证Token")
        self._config_widgets['bilibili_token'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['bilibili_token'].textChanged.connect(
            lambda text: self._update_config('live.bilibili.token', text)
        )
        token_layout.addWidget(self._config_widgets['bilibili_token'])
        card_layout.addLayout(token_layout)

        # 状态显示
        self._status_labels['bilibili'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['bilibili'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接直播间")
        connect_btn.clicked.connect(lambda: self._connect_platform('bilibili'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_platform('bilibili'))
        btn_layout.addWidget(disconnect_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_douyin_card(self) -> None:
        """创建抖音配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🎵 抖音直播配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用抖音直播"))
        self._config_widgets['douyin_enabled'] = SwitchButton()
        self._config_widgets['douyin_enabled'].setChecked(self._config_data.get('live', {}).get('douyin', {}).get('enabled', False))
        self._config_widgets['douyin_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('live.douyin.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['douyin_enabled'])
        card_layout.addLayout(enable_layout)

        # 直播间ID
        room_id_layout = QHBoxLayout()
        room_id_layout.addWidget(CaptionLabel("直播间ID"))
        self._config_widgets['douyin_room_id'] = LineEdit()
        self._config_widgets['douyin_room_id'].setText(self._config_data.get('live', {}).get('douyin', {}).get('room_id', ''))
        self._config_widgets['douyin_room_id'].setPlaceholderText("输入抖音直播间ID")
        self._config_widgets['douyin_room_id'].textChanged.connect(
            lambda text: self._update_config('live.douyin.room_id', text)
        )
        room_id_layout.addWidget(self._config_widgets['douyin_room_id'])
        card_layout.addLayout(room_id_layout)

        # Cookie
        cookie_layout = QHBoxLayout()
        cookie_layout.addWidget(CaptionLabel("Cookie"))
        self._config_widgets['douyin_cookie'] = LineEdit()
        self._config_widgets['douyin_cookie'].setText(self._config_data.get('live', {}).get('douyin', {}).get('cookie', ''))
        self._config_widgets['douyin_cookie'].setPlaceholderText("输入抖音Cookie")
        self._config_widgets['douyin_cookie'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['douyin_cookie'].textChanged.connect(
            lambda text: self._update_config('live.douyin.cookie', text)
        )
        cookie_layout.addWidget(self._config_widgets['douyin_cookie'])
        card_layout.addLayout(cookie_layout)

        # 状态显示
        self._status_labels['douyin'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['douyin'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接直播间")
        connect_btn.clicked.connect(lambda: self._connect_platform('douyin'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_platform('douyin'))
        btn_layout.addWidget(disconnect_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_kuaishou_card(self) -> None:
        """创建快手配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🎬 快手直播配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用快手直播"))
        self._config_widgets['kuaishou_enabled'] = SwitchButton()
        self._config_widgets['kuaishou_enabled'].setChecked(self._config_data.get('live', {}).get('kuaishou', {}).get('enabled', False))
        self._config_widgets['kuaishou_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('live.kuaishou.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['kuaishou_enabled'])
        card_layout.addLayout(enable_layout)

        # 直播间ID
        room_id_layout = QHBoxLayout()
        room_id_layout.addWidget(CaptionLabel("直播间ID"))
        self._config_widgets['kuaishou_room_id'] = LineEdit()
        self._config_widgets['kuaishou_room_id'].setText(self._config_data.get('live', {}).get('kuaishou', {}).get('room_id', ''))
        self._config_widgets['kuaishou_room_id'].setPlaceholderText("输入快手直播间ID")
        self._config_widgets['kuaishou_room_id'].textChanged.connect(
            lambda text: self._update_config('live.kuaishou.room_id', text)
        )
        room_id_layout.addWidget(self._config_widgets['kuaishou_room_id'])
        card_layout.addLayout(room_id_layout)

        # Cookie
        cookie_layout = QHBoxLayout()
        cookie_layout.addWidget(CaptionLabel("Cookie"))
        self._config_widgets['kuaishou_cookie'] = LineEdit()
        self._config_widgets['kuaishou_cookie'].setText(self._config_data.get('live', {}).get('kuaishou', {}).get('cookie', ''))
        self._config_widgets['kuaishou_cookie'].setPlaceholderText("输入快手Cookie")
        self._config_widgets['kuaishou_cookie'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['kuaishou_cookie'].textChanged.connect(
            lambda text: self._update_config('live.kuaishou.cookie', text)
        )
        cookie_layout.addWidget(self._config_widgets['kuaishou_cookie'])
        card_layout.addLayout(cookie_layout)

        # 状态显示
        self._status_labels['kuaishou'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['kuaishou'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接直播间")
        connect_btn.clicked.connect(lambda: self._connect_platform('kuaishou'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_platform('kuaishou'))
        btn_layout.addWidget(disconnect_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_douyu_card(self) -> None:
        """创建斗鱼配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🐟 斗鱼直播配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用斗鱼直播"))
        self._config_widgets['douyu_enabled'] = SwitchButton()
        self._config_widgets['douyu_enabled'].setChecked(self._config_data.get('live', {}).get('douyu', {}).get('enabled', False))
        self._config_widgets['douyu_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('live.douyu.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['douyu_enabled'])
        card_layout.addLayout(enable_layout)

        # 直播间ID
        room_id_layout = QHBoxLayout()
        room_id_layout.addWidget(CaptionLabel("直播间ID"))
        self._config_widgets['douyu_room_id'] = LineEdit()
        self._config_widgets['douyu_room_id'].setText(self._config_data.get('live', {}).get('douyu', {}).get('room_id', ''))
        self._config_widgets['douyu_room_id'].setPlaceholderText("输入斗鱼直播间ID")
        self._config_widgets['douyu_room_id'].textChanged.connect(
            lambda text: self._update_config('live.douyu.room_id', text)
        )
        room_id_layout.addWidget(self._config_widgets['douyu_room_id'])
        card_layout.addLayout(room_id_layout)

        # 状态显示
        self._status_labels['douyu'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['douyu'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接直播间")
        connect_btn.clicked.connect(lambda: self._connect_platform('douyu'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_platform('douyu'))
        btn_layout.addWidget(disconnect_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_huya_card(self) -> None:
        """创建虎牙配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🐯 虎牙直播配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用虎牙直播"))
        self._config_widgets['huya_enabled'] = SwitchButton()
        self._config_widgets['huya_enabled'].setChecked(self._config_data.get('live', {}).get('huya', {}).get('enabled', False))
        self._config_widgets['huya_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('live.huya.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['huya_enabled'])
        card_layout.addLayout(enable_layout)

        # 直播间ID
        room_id_layout = QHBoxLayout()
        room_id_layout.addWidget(CaptionLabel("直播间ID"))
        self._config_widgets['huya_room_id'] = LineEdit()
        self._config_widgets['huya_room_id'].setText(self._config_data.get('live', {}).get('huya', {}).get('room_id', ''))
        self._config_widgets['huya_room_id'].setPlaceholderText("输入虎牙直播间ID")
        self._config_widgets['huya_room_id'].textChanged.connect(
            lambda text: self._update_config('live.huya.room_id', text)
        )
        room_id_layout.addWidget(self._config_widgets['huya_room_id'])
        card_layout.addLayout(room_id_layout)

        # 状态显示
        self._status_labels['huya'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['huya'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接直播间")
        connect_btn.clicked.connect(lambda: self._connect_platform('huya'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_platform('huya'))
        btn_layout.addWidget(disconnect_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_youtube_card(self) -> None:
        """创建YouTube配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("📹 YouTube直播配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用YouTube直播"))
        self._config_widgets['youtube_enabled'] = SwitchButton()
        self._config_widgets['youtube_enabled'].setChecked(self._config_data.get('live', {}).get('youtube', {}).get('enabled', False))
        self._config_widgets['youtube_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('live.youtube.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['youtube_enabled'])
        card_layout.addLayout(enable_layout)

        # 频道ID
        channel_id_layout = QHBoxLayout()
        channel_id_layout.addWidget(CaptionLabel("频道ID"))
        self._config_widgets['youtube_channel_id'] = LineEdit()
        self._config_widgets['youtube_channel_id'].setText(self._config_data.get('live', {}).get('youtube', {}).get('channel_id', ''))
        self._config_widgets['youtube_channel_id'].setPlaceholderText("输入YouTube频道ID")
        self._config_widgets['youtube_channel_id'].textChanged.connect(
            lambda text: self._update_config('live.youtube.channel_id', text)
        )
        channel_id_layout.addWidget(self._config_widgets['youtube_channel_id'])
        card_layout.addLayout(channel_id_layout)

        # API Key
        api_key_layout = QHBoxLayout()
        api_key_layout.addWidget(CaptionLabel("API Key"))
        self._config_widgets['youtube_api_key'] = LineEdit()
        self._config_widgets['youtube_api_key'].setText(self._config_data.get('live', {}).get('youtube', {}).get('api_key', ''))
        self._config_widgets['youtube_api_key'].setPlaceholderText("输入YouTube API Key")
        self._config_widgets['youtube_api_key'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['youtube_api_key'].textChanged.connect(
            lambda text: self._update_config('live.youtube.api_key', text)
        )
        api_key_layout.addWidget(self._config_widgets['youtube_api_key'])
        card_layout.addLayout(api_key_layout)

        # 状态显示
        self._status_labels['youtube'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['youtube'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接直播间")
        connect_btn.clicked.connect(lambda: self._connect_platform('youtube'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_platform('youtube'))
        btn_layout.addWidget(disconnect_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_twitch_card(self) -> None:
        """创建Twitch配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("💜 Twitch直播配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用Twitch直播"))
        self._config_widgets['twitch_enabled'] = SwitchButton()
        self._config_widgets['twitch_enabled'].setChecked(self._config_data.get('live', {}).get('twitch', {}).get('enabled', False))
        self._config_widgets['twitch_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('live.twitch.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['twitch_enabled'])
        card_layout.addLayout(enable_layout)

        # 频道名
        channel_layout = QHBoxLayout()
        channel_layout.addWidget(CaptionLabel("频道名"))
        self._config_widgets['twitch_channel'] = LineEdit()
        self._config_widgets['twitch_channel'].setText(self._config_data.get('live', {}).get('twitch', {}).get('channel', ''))
        self._config_widgets['twitch_channel'].setPlaceholderText("输入Twitch频道名")
        self._config_widgets['twitch_channel'].textChanged.connect(
            lambda text: self._update_config('live.twitch.channel', text)
        )
        channel_layout.addWidget(self._config_widgets['twitch_channel'])
        card_layout.addLayout(channel_layout)

        # OAuth Token
        oauth_layout = QHBoxLayout()
        oauth_layout.addWidget(CaptionLabel("OAuth Token"))
        self._config_widgets['twitch_oauth_token'] = LineEdit()
        self._config_widgets['twitch_oauth_token'].setText(self._config_data.get('live', {}).get('twitch', {}).get('oauth_token', ''))
        self._config_widgets['twitch_oauth_token'].setPlaceholderText("输入Twitch OAuth Token")
        self._config_widgets['twitch_oauth_token'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['twitch_oauth_token'].textChanged.connect(
            lambda text: self._update_config('live.twitch.oauth_token', text)
        )
        oauth_layout.addWidget(self._config_widgets['twitch_oauth_token'])
        card_layout.addLayout(oauth_layout)

        # 状态显示
        self._status_labels['twitch'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['twitch'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接直播间")
        connect_btn.clicked.connect(lambda: self._connect_platform('twitch'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_platform('twitch'))
        btn_layout.addWidget(disconnect_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_tiktok_card(self) -> None:
        """创建TikTok配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🎬 TikTok直播配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用TikTok直播"))
        self._config_widgets['tiktok_enabled'] = SwitchButton()
        self._config_widgets['tiktok_enabled'].setChecked(self._config_data.get('live', {}).get('tiktok', {}).get('enabled', False))
        self._config_widgets['tiktok_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('live.tiktok.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['tiktok_enabled'])
        card_layout.addLayout(enable_layout)

        # 直播间ID
        room_id_layout = QHBoxLayout()
        room_id_layout.addWidget(CaptionLabel("直播间ID"))
        self._config_widgets['tiktok_room_id'] = LineEdit()
        self._config_widgets['tiktok_room_id'].setText(self._config_data.get('live', {}).get('tiktok', {}).get('room_id', ''))
        self._config_widgets['tiktok_room_id'].setPlaceholderText("输入TikTok直播间ID")
        self._config_widgets['tiktok_room_id'].textChanged.connect(
            lambda text: self._update_config('live.tiktok.room_id', text)
        )
        room_id_layout.addWidget(self._config_widgets['tiktok_room_id'])
        card_layout.addLayout(room_id_layout)

        # Cookie
        cookie_layout = QHBoxLayout()
        cookie_layout.addWidget(CaptionLabel("Cookie"))
        self._config_widgets['tiktok_cookie'] = LineEdit()
        self._config_widgets['tiktok_cookie'].setText(self._config_data.get('live', {}).get('tiktok', {}).get('cookie', ''))
        self._config_widgets['tiktok_cookie'].setPlaceholderText("输入TikTok Cookie")
        self._config_widgets['tiktok_cookie'].setEchoMode(QLineEdit.EchoMode.Password)
        self._config_widgets['tiktok_cookie'].textChanged.connect(
            lambda text: self._update_config('live.tiktok.cookie', text)
        )
        cookie_layout.addWidget(self._config_widgets['tiktok_cookie'])
        card_layout.addLayout(cookie_layout)

        # 状态显示
        self._status_labels['tiktok'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['tiktok'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接直播间")
        connect_btn.clicked.connect(lambda: self._connect_platform('tiktok'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_platform('tiktok'))
        btn_layout.addWidget(disconnect_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_weixin_video_card(self) -> None:
        """创建微信视频号配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("📱 微信视频号直播配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用微信视频号直播"))
        self._config_widgets['weixin_video_enabled'] = SwitchButton()
        self._config_widgets['weixin_video_enabled'].setChecked(self._config_data.get('live', {}).get('weixin_video', {}).get('enabled', False))
        self._config_widgets['weixin_video_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('live.weixin_video.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['weixin_video_enabled'])
        card_layout.addLayout(enable_layout)

        # 直播间ID
        room_id_layout = QHBoxLayout()
        room_id_layout.addWidget(CaptionLabel("直播间ID"))
        self._config_widgets['weixin_video_room_id'] = LineEdit()
        self._config_widgets['weixin_video_room_id'].setText(self._config_data.get('live', {}).get('weixin_video', {}).get('room_id', ''))
        self._config_widgets['weixin_video_room_id'].setPlaceholderText("输入微信视频号直播间ID")
        self._config_widgets['weixin_video_room_id'].textChanged.connect(
            lambda text: self._update_config('live.weixin_video.room_id', text)
        )
        room_id_layout.addWidget(self._config_widgets['weixin_video_room_id'])
        card_layout.addLayout(room_id_layout)

        # 状态显示
        self._status_labels['weixin_video'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['weixin_video'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接直播间")
        connect_btn.clicked.connect(lambda: self._connect_platform('weixin_video'))
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(lambda: self._disconnect_platform('weixin_video'))
        btn_layout.addWidget(disconnect_btn)
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
        self._status_table.setHorizontalHeaderLabels(["平台", "状态", "直播间ID", "最后更新"])
        self._status_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        status_layout.addWidget(self._status_table)
        tab_widget.addTab(status_widget, "状态")
        
        layout.addWidget(tab_widget)

    def _show_platform_config(self, platform_key) -> None:
        """显示平台配置"""
        # 隐藏所有卡片
        for key, card in self._cards.items():
            card.setVisible(key == platform_key)
        
        # 更新按钮状态
        for key, (btn, status_label) in self._platform_buttons.items():
            btn.setChecked(key == platform_key)
        
        self._log("DEBUG", f"切换到平台配置: {platform_key}")

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
        platform = key.split('.')[1] if len(key.split('.')) > 1 else key
        if platform in self._status_labels:
            self._status_labels[platform].setText(f"配置已更新: {key}")

    def _on_status_updated(self, platform, status) -> None:
        """状态更新处理"""
        if platform in self._status_labels:
            self._status_labels[platform].setText(f"状态: {status}")
        
        # 更新平台列表中的状态标签
        if platform in self._platform_buttons:
            btn, status_label = self._platform_buttons[platform]
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
        for i, (platform, label) in enumerate(self._status_labels.items()):
            self._status_table.setItem(i, 0, QTableWidgetItem(platform))
            self._status_table.setItem(i, 1, QTableWidgetItem(label.text()))
            self._status_table.setItem(i, 2, QTableWidgetItem(self._config_data.get('live', {}).get(platform, {}).get('room_id', '')))
            self._status_table.setItem(i, 3, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))

    def _connect_platform(self, platform) -> None:
        """连接平台"""
        self._log("INFO", f"正在连接{platform}直播间...")
        # 这里应该调用后端的连接功能

    def _disconnect_platform(self, platform) -> None:
        """断开平台连接"""
        self._log("INFO", f"正在断开{platform}连接...")
        # 这里应该调用后端的断开功能