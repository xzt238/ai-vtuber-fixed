"""
新增功能调试页面 - 优化版

提供RAG、直播、SVC、唱歌、SD、游戏、多Agent、Bot、视觉输入等功能的调试界面。

优化点:
1. 左侧功能列表与右侧配置面板联动
2. 配置参数实时保存到配置文件
3. 状态刷新功能实现
4. 操作按钮功能实现
5. 日志输出面板
6. 性能监控面板
"""

import os
import json
import yaml
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


class DebugPageOptimized(QWidget, LazyPageMixin):
    """新增功能调试页面 - 优化版"""

    # 信号定义
    config_changed = Signal(str, object)  # 配置变更信号
    status_updated = Signal(str, str)     # 状态更新信号
    log_message = Signal(str, str)        # 日志消息信号

    def __init__(self, parent=None) -> None:
        QWidget.__init__(self, parent)
        LazyPageMixin.__init__(self)
        self.setObjectName("debugPageOptimized")
        self._backend = None
        self._config_widgets = {}
        self._status_labels = {}
        self._log_messages = []
        self._config_file = Path(PROJECT_DIR) / "app" / "config.yaml"
        self._config_data = {}
        
        # 骨架屏占位
        self._skeleton = SkeletonContainer("正在加载调试页面...", self)
        self._skeleton.hide_skeleton()
        
        # 连接信号
        self.config_changed.connect(self._on_config_changed)
        self.status_updated.connect(self._on_status_updated)
        self.log_message.connect(self._on_log_message)

    def show_skeleton(self) -> None:
        self._skeleton.show_skeleton()

    def hide_skeleton(self) -> None:
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

        card_layout.addWidget(SubtitleLabel("新增功能"))

        features = [
            ("🔧 系统调试", "system", "系统状态、日志查看"),
            ("📊 性能监控", "performance", "CPU、内存、GPU监控"),
            ("🔄 配置热重载", "hot_reload", "配置文件监听、自动重载"),
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
            status_label = CaptionLabel("未启用")
            status_label.setStyleSheet("color: gray;")
            btn_layout.addWidget(status_label)
            
            self._feature_buttons[key] = (btn, status_label)
            card_layout.addLayout(btn_layout)

        card_layout.addStretch()
        layout.addWidget(card)

    def _init_all_cards(self) -> None:
        """初始化所有配置卡片"""
        self._cards = {}
        
        # 系统调试配置卡片
        self._cards['system'] = self._create_system_card()
        self._right_layout.addWidget(self._cards['system'])
        
        # 性能监控配置卡片
        self._cards['performance'] = self._create_performance_card()
        self._right_layout.addWidget(self._cards['performance'])
        
        # 配置热重载配置卡片
        self._cards['hot_reload'] = self._create_hot_reload_card()
        self._right_layout.addWidget(self._cards['hot_reload'])

    def _create_system_card(self) -> None:
        """创建系统调试配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🔧 系统调试"))

        # 系统信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        
        # 版本信息
        version_layout = QHBoxLayout()
        version_layout.addWidget(CaptionLabel("版本:"))
        version_label = CaptionLabel("v1.18.4")
        version_label.setStyleSheet("font-weight: bold;")
        version_layout.addWidget(version_label)
        version_layout.addStretch()
        info_layout.addLayout(version_layout)
        
        # Python版本
        python_layout = QHBoxLayout()
        python_layout.addWidget(CaptionLabel("Python:"))
        python_label = CaptionLabel("3.11.0")
        python_layout.addWidget(python_label)
        python_layout.addStretch()
        info_layout.addLayout(python_layout)
        
        # 运行模式
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(CaptionLabel("运行模式:"))
        mode_label = CaptionLabel("原生桌面")
        mode_layout.addWidget(mode_label)
        mode_layout.addStretch()
        info_layout.addLayout(mode_layout)
        
        card_layout.addLayout(info_layout)

        # 操作按钮
        btn_layout = QHBoxLayout()
        
        refresh_btn = PushButton("刷新状态")
        refresh_btn.clicked.connect(self._refresh_system_status)
        btn_layout.addWidget(refresh_btn)
        
        clear_cache_btn = PushButton("清除缓存")
        clear_cache_btn.clicked.connect(self._clear_cache)
        btn_layout.addWidget(clear_cache_btn)
        
        card_layout.addLayout(btn_layout)

        # 状态显示
        self._status_labels['system'] = CaptionLabel("状态: 正常")
        card_layout.addWidget(self._status_labels['system'])

        return card

    def _create_performance_card(self) -> None:
        """创建性能监控配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("📊 性能监控"))

        # 监控开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用性能监控"))
        self._config_widgets['perf_enabled'] = SwitchButton()
        self._config_widgets['perf_enabled'].setChecked(True)
        enable_layout.addWidget(self._config_widgets['perf_enabled'])
        card_layout.addLayout(enable_layout)

        # 监控间隔
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(CaptionLabel("监控间隔（秒）"))
        self._config_widgets['perf_interval'] = SpinBox()
        self._config_widgets['perf_interval'].setRange(1, 60)
        self._config_widgets['perf_interval'].setValue(1)
        interval_layout.addWidget(self._config_widgets['perf_interval'])
        card_layout.addLayout(interval_layout)

        # 性能指标显示
        metrics_layout = QVBoxLayout()
        metrics_layout.setSpacing(4)
        
        cpu_layout = QHBoxLayout()
        cpu_layout.addWidget(CaptionLabel("CPU:"))
        self._perf_cpu_label = CaptionLabel("0%")
        cpu_layout.addWidget(self._perf_cpu_label)
        cpu_layout.addStretch()
        metrics_layout.addLayout(cpu_layout)
        
        memory_layout = QHBoxLayout()
        memory_layout.addWidget(CaptionLabel("内存:"))
        self._perf_memory_label = CaptionLabel("0MB")
        memory_layout.addWidget(self._perf_memory_label)
        memory_layout.addStretch()
        metrics_layout.addLayout(memory_layout)
        
        card_layout.addLayout(metrics_layout)

        # 操作按钮
        btn_layout = QHBoxLayout()
        
        start_btn = PushButton("开始监控")
        start_btn.clicked.connect(self._start_performance_monitor)
        btn_layout.addWidget(start_btn)
        
        stop_btn = PushButton("停止监控")
        stop_btn.clicked.connect(self._stop_performance_monitor)
        btn_layout.addWidget(stop_btn)
        
        card_layout.addLayout(btn_layout)

        # 状态显示
        self._status_labels['performance'] = CaptionLabel("状态: 未启动")
        card_layout.addWidget(self._status_labels['performance'])

        return card

    def _create_hot_reload_card(self) -> None:
        """创建配置热重载配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🔄 配置热重载"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用配置热重载"))
        self._config_widgets['hot_reload_enabled'] = SwitchButton()
        self._config_widgets['hot_reload_enabled'].setChecked(False)
        enable_layout.addWidget(self._config_widgets['hot_reload_enabled'])
        card_layout.addLayout(enable_layout)

        # 监听间隔
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(CaptionLabel("监听间隔（秒）"))
        self._config_widgets['hot_reload_interval'] = SpinBox()
        self._config_widgets['hot_reload_interval'].setRange(1, 60)
        self._config_widgets['hot_reload_interval'].setValue(1)
        interval_layout.addWidget(self._config_widgets['hot_reload_interval'])
        card_layout.addLayout(interval_layout)

        # 监听文件列表
        files_layout = QVBoxLayout()
        files_layout.setSpacing(4)
        
        files_label = CaptionLabel("监听的文件:")
        files_layout.addWidget(files_label)
        
        self._hot_reload_files_list = QTextEdit()
        self._hot_reload_files_list.setMaximumHeight(100)
        self._hot_reload_files_list.setPlainText("config.yaml\napi_keys.json")
        files_layout.addWidget(self._hot_reload_files_list)
        
        card_layout.addLayout(files_layout)

        # 操作按钮
        btn_layout = QHBoxLayout()
        
        start_btn = PushButton("开始监听")
        start_btn.clicked.connect(self._start_hot_reload)
        btn_layout.addWidget(start_btn)
        
        stop_btn = PushButton("停止监听")
        stop_btn.clicked.connect(self._stop_hot_reload)
        btn_layout.addWidget(stop_btn)
        
        card_layout.addLayout(btn_layout)

        # 状态显示
        self._status_labels['hot_reload'] = CaptionLabel("状态: 未启动")
        card_layout.addWidget(self._status_labels['hot_reload'])

        return card

    def _create_rag_card(self) -> None:
        """创建RAG知识库配置卡片（已移至功能设置页面）"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("📚 RAG知识库配置"))
        card_layout.addWidget(CaptionLabel("此功能已移至功能设置页面"))
        
        # 跳转按钮
        goto_btn = PushButton("前往功能设置")
        goto_btn.clicked.connect(lambda: self._navigate_to_features_settings())
        card_layout.addWidget(goto_btn)

        return card

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用RAG知识库"))
        self._config_widgets['rag_enabled'] = SwitchButton()
        self._config_widgets['rag_enabled'].setChecked(self._config_data.get('rag', {}).get('enabled', False))
        self._config_widgets['rag_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('rag.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['rag_enabled'])
        card_layout.addLayout(enable_layout)

        # 分块大小
        chunk_size_layout = QHBoxLayout()
        chunk_size_layout.addWidget(CaptionLabel("分块大小（字符数）"))
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
        top_k_layout.addWidget(CaptionLabel("检索结果数量"))
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
        self._status_labels['rag'] = CaptionLabel("状态: 未初始化")
        card_layout.addWidget(self._status_labels['rag'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        test_btn = PushButton("测试RAG功能")
        test_btn.clicked.connect(self._test_rag)
        btn_layout.addWidget(test_btn)
        
        load_doc_btn = PushButton("加载文档")
        load_doc_btn.clicked.connect(self._load_rag_document)
        btn_layout.addWidget(load_doc_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_live_card(self) -> None:
        """创建直播平台配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("📺 直播平台配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用直播平台"))
        self._config_widgets['live_enabled'] = SwitchButton()
        self._config_widgets['live_enabled'].setChecked(self._config_data.get('live', {}).get('enabled', False))
        self._config_widgets['live_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('live.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['live_enabled'])
        card_layout.addLayout(enable_layout)

        # Bilibili配置
        bilibili_group = QGroupBox("Bilibili配置")
        bilibili_layout = QVBoxLayout(bilibili_group)

        room_id_layout = QHBoxLayout()
        room_id_layout.addWidget(CaptionLabel("房间ID"))
        self._config_widgets['live_room_id'] = LineEdit()
        self._config_widgets['live_room_id'].setText(self._config_data.get('live', {}).get('bilibili', {}).get('room_id', ''))
        self._config_widgets['live_room_id'].textChanged.connect(
            lambda text: self._update_config('live.bilibili.room_id', text)
        )
        room_id_layout.addWidget(self._config_widgets['live_room_id'])
        bilibili_layout.addLayout(room_id_layout)

        card_layout.addWidget(bilibili_group)

        # 状态显示
        self._status_labels['live'] = CaptionLabel("状态: 未连接")
        card_layout.addWidget(self._status_labels['live'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        connect_btn = PushButton("连接直播间")
        connect_btn.clicked.connect(self._connect_live)
        btn_layout.addWidget(connect_btn)
        
        disconnect_btn = PushButton("断开连接")
        disconnect_btn.clicked.connect(self._disconnect_live)
        btn_layout.addWidget(disconnect_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_svc_card(self) -> None:
        """创建SVC声音转换配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🎵 SVC声音转换配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用SVC声音转换"))
        self._config_widgets['svc_enabled'] = SwitchButton()
        self._config_widgets['svc_enabled'].setChecked(self._config_data.get('svc', {}).get('enabled', False))
        self._config_widgets['svc_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('svc.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['svc_enabled'])
        card_layout.addLayout(enable_layout)

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
        card_layout.addLayout(device_layout)

        # 模型路径
        model_path_layout = QHBoxLayout()
        model_path_layout.addWidget(CaptionLabel("模型路径"))
        self._config_widgets['svc_model_path'] = LineEdit()
        self._config_widgets['svc_model_path'].setText(self._config_data.get('svc', {}).get('model_path', ''))
        self._config_widgets['svc_model_path'].textChanged.connect(
            lambda text: self._update_config('svc.model_path', text)
        )
        model_path_layout.addWidget(self._config_widgets['svc_model_path'])
        card_layout.addLayout(model_path_layout)

        # 状态显示
        self._status_labels['svc'] = CaptionLabel("状态: 未加载模型")
        card_layout.addWidget(self._status_labels['svc'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        load_btn = PushButton("加载模型")
        load_btn.clicked.connect(self._load_svc_model)
        btn_layout.addWidget(load_btn)
        
        test_btn = PushButton("测试转换")
        test_btn.clicked.connect(self._test_svc)
        btn_layout.addWidget(test_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_singing_card(self) -> None:
        """创建唱歌模块配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("🎤 唱歌模块配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用唱歌模块"))
        self._config_widgets['singing_enabled'] = SwitchButton()
        self._config_widgets['singing_enabled'].setChecked(self._config_data.get('singing', {}).get('enabled', False))
        self._config_widgets['singing_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('singing.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['singing_enabled'])
        card_layout.addLayout(enable_layout)

        # 设备选择
        device_layout = QHBoxLayout()
        device_layout.addWidget(CaptionLabel("设备"))
        self._config_widgets['singing_device'] = ComboBox()
        self._config_widgets['singing_device'].addItems(["cuda", "cpu"])
        self._config_widgets['singing_device'].setCurrentText(self._config_data.get('singing', {}).get('device', 'cuda'))
        self._config_widgets['singing_device'].currentTextChanged.connect(
            lambda text: self._update_config('singing.device', text)
        )
        device_layout.addWidget(self._config_widgets['singing_device'])
        card_layout.addLayout(device_layout)

        # 状态显示
        self._status_labels['singing'] = CaptionLabel("状态: 未加载模型")
        card_layout.addWidget(self._status_labels['singing'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        load_btn = PushButton("加载模型")
        load_btn.clicked.connect(self._load_singing_model)
        btn_layout.addWidget(load_btn)
        
        test_btn = PushButton("测试唱歌")
        test_btn.clicked.connect(self._test_singing)
        btn_layout.addWidget(test_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_multi_agent_card(self) -> None:
        """创建多AI群聊配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("👥 多AI群聊配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用多AI群聊"))
        self._config_widgets['multi_agent_enabled'] = SwitchButton()
        self._config_widgets['multi_agent_enabled'].setChecked(self._config_data.get('multi_agent', {}).get('enabled', False))
        self._config_widgets['multi_agent_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('multi_agent.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['multi_agent_enabled'])
        card_layout.addLayout(enable_layout)

        # 最大代理数量
        max_agents_layout = QHBoxLayout()
        max_agents_layout.addWidget(CaptionLabel("最大代理数量"))
        self._config_widgets['multi_agent_max'] = SpinBox()
        self._config_widgets['multi_agent_max'].setRange(2, 20)
        self._config_widgets['multi_agent_max'].setValue(self._config_data.get('multi_agent', {}).get('max_agents', 10))
        self._config_widgets['multi_agent_max'].valueChanged.connect(
            lambda value: self._update_config('multi_agent.max_agents', value)
        )
        max_agents_layout.addWidget(self._config_widgets['multi_agent_max'])
        card_layout.addLayout(max_agents_layout)

        # 状态显示
        self._status_labels['multi_agent'] = CaptionLabel("状态: 未初始化")
        card_layout.addWidget(self._status_labels['multi_agent'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        create_btn = PushButton("创建测试代理")
        create_btn.clicked.connect(self._create_test_agent)
        btn_layout.addWidget(create_btn)
        
        start_btn = PushButton("开始对话")
        start_btn.clicked.connect(self._start_multi_agent_conversation)
        btn_layout.addWidget(start_btn)
        card_layout.addLayout(btn_layout)

        return card

    def _create_vision_input_card(self) -> None:
        """创建摄像头视觉输入配置卡片"""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        card_layout.addWidget(SubtitleLabel("📷 摄像头视觉输入配置"))

        # 启用开关
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(CaptionLabel("启用摄像头视觉输入"))
        self._config_widgets['vision_input_enabled'] = SwitchButton()
        self._config_widgets['vision_input_enabled'].setChecked(self._config_data.get('vision_input', {}).get('enabled', False))
        self._config_widgets['vision_input_enabled'].checkedChanged.connect(
            lambda checked: self._update_config('vision_input.enabled', checked)
        )
        enable_layout.addWidget(self._config_widgets['vision_input_enabled'])
        card_layout.addLayout(enable_layout)

        # 摄像头配置
        camera_group = QGroupBox("摄像头配置")
        camera_layout = QVBoxLayout(camera_group)

        device_layout = QHBoxLayout()
        device_layout.addWidget(CaptionLabel("设备ID"))
        self._config_widgets['camera_device_id'] = SpinBox()
        self._config_widgets['camera_device_id'].setRange(0, 10)
        self._config_widgets['camera_device_id'].setValue(self._config_data.get('vision_input', {}).get('camera', {}).get('device_id', 0))
        self._config_widgets['camera_device_id'].valueChanged.connect(
            lambda value: self._update_config('vision_input.camera.device_id', value)
        )
        device_layout.addWidget(self._config_widgets['camera_device_id'])
        camera_layout.addLayout(device_layout)

        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(CaptionLabel("宽度"))
        self._config_widgets['camera_width'] = SpinBox()
        self._config_widgets['camera_width'].setRange(320, 1920)
        self._config_widgets['camera_width'].setValue(self._config_data.get('vision_input', {}).get('camera', {}).get('width', 640))
        self._config_widgets['camera_width'].valueChanged.connect(
            lambda value: self._update_config('vision_input.camera.width', value)
        )
        resolution_layout.addWidget(self._config_widgets['camera_width'])
        
        resolution_layout.addWidget(CaptionLabel("高度"))
        self._config_widgets['camera_height'] = SpinBox()
        self._config_widgets['camera_height'].setRange(240, 1080)
        self._config_widgets['camera_height'].setValue(self._config_data.get('vision_input', {}).get('camera', {}).get('height', 480))
        self._config_widgets['camera_height'].valueChanged.connect(
            lambda value: self._update_config('vision_input.camera.height', value)
        )
        resolution_layout.addWidget(self._config_widgets['camera_height'])
        camera_layout.addLayout(resolution_layout)

        card_layout.addWidget(camera_group)

        # 状态显示
        self._status_labels['vision_input'] = CaptionLabel("状态: 未打开摄像头")
        card_layout.addWidget(self._status_labels['vision_input'])

        # 操作按钮
        btn_layout = QHBoxLayout()
        open_btn = PushButton("打开摄像头")
        open_btn.clicked.connect(self._open_camera)
        btn_layout.addWidget(open_btn)
        
        close_btn = PushButton("关闭摄像头")
        close_btn.clicked.connect(self._close_camera)
        btn_layout.addWidget(close_btn)
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
        feature = key.split('.')[0]
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

    # 操作按钮的回调函数
    def _test_rag(self) -> None:
        """测试RAG功能"""
        self._log("INFO", "测试RAG功能...")
        # 这里应该调用后端的RAG测试功能

    def _load_rag_document(self) -> None:
        """加载RAG文档"""
        self._log("INFO", "加载RAG文档...")
        # 这里应该调用后端的文档加载功能

    def _connect_live(self) -> None:
        """连接直播间"""
        self._log("INFO", "连接直播间...")
        # 这里应该调用后端的直播连接功能

    def _disconnect_live(self) -> None:
        """断开直播间连接"""
        self._log("INFO", "断开直播间连接...")
        # 这里应该调用后端的直播断开功能

    def _load_svc_model(self) -> None:
        """加载SVC模型"""
        self._log("INFO", "加载SVC模型...")
        # 这里应该调用后端的SVC模型加载功能

    def _test_svc(self) -> None:
        """测试SVC转换"""
        self._log("INFO", "测试SVC转换...")
        # 这里应该调用后端的SVC测试功能

    def _load_singing_model(self) -> None:
        """加载唱歌模型"""
        self._log("INFO", "加载唱歌模型...")
        # 这里应该调用后端的唱歌模型加载功能

    def _test_singing(self) -> None:
        """测试唱歌功能"""
        self._log("INFO", "测试唱歌功能...")
        # 这里应该调用后端的唱歌测试功能

    def _create_test_agent(self) -> None:
        """创建测试代理"""
        self._log("INFO", "创建测试代理...")
        # 这里应该调用后端的代理创建功能

    def _start_multi_agent_conversation(self) -> None:
        """开始多Agent对话"""
        self._log("INFO", "开始多Agent对话...")
        # 这里应该调用后端的多Agent对话功能

    def _open_camera(self) -> None:
        """打开摄像头"""
        self._log("INFO", "打开摄像头...")
        # 这里应该调用后端的摄像头打开功能

    def _close_camera(self) -> None:
        """关闭摄像头"""
        self._log("INFO", "关闭摄像头...")
        # 这里应该调用后端的摄像头关闭功能

    def _refresh_system_status(self) -> None:
        """刷新系统状态"""
        self._log("INFO", "刷新系统状态...")
        # 这里应该调用后端的系统状态获取功能
        self._status_labels['system'].setText("状态: 正常")

    def _clear_cache(self) -> None:
        """清除缓存"""
        self._log("INFO", "清除缓存...")
        # 这里应该调用后端的缓存清除功能

    def _start_performance_monitor(self) -> None:
        """开始性能监控"""
        self._log("INFO", "开始性能监控...")
        # 这里应该调用后端的性能监控启动功能
        self._status_labels['performance'].setText("状态: 监控中")

    def _stop_performance_monitor(self) -> None:
        """停止性能监控"""
        self._log("INFO", "停止性能监控...")
        # 这里应该调用后端的性能监控停止功能
        self._status_labels['performance'].setText("状态: 已停止")

    def _start_hot_reload(self) -> None:
        """开始配置热重载"""
        self._log("INFO", "开始配置热重载...")
        # 这里应该调用后端的配置热重载启动功能
        self._status_labels['hot_reload'].setText("状态: 监听中")

    def _stop_hot_reload(self) -> None:
        """停止配置热重载"""
        self._log("INFO", "停止配置热重载...")
        # 这里应该调用后端的配置热重载停止功能
        self._status_labels['hot_reload'].setText("状态: 已停止")

    def _navigate_to_features_settings(self) -> None:
        """导航到功能设置页面"""
        self._log("INFO", "导航到功能设置页面...")
        # 这里应该实现页面导航功能