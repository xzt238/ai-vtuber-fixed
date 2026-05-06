"""
音色训练页面 — GPT-SoVITS 训练管理

对接 app/trainer/manager.py TrainingManager，提供：
- 项目列表管理（创建/删除/切换）
- 音频文件上传/管理
- 参考音频和文本配置
- S1/S2 训练参数配置
- 训练进度实时监控
- 训练模型管理（切换/删除）
"""

import os
import json
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QComboBox, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QHeaderView,
    QInputDialog, QMessageBox, QSplitter, QMenu,
    QProgressBar, QGroupBox, QFormLayout, QSpinBox,
    QFileDialog, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread
from PySide6.QtGui import QFont, QColor, QAction

from qfluentwidgets import (
    PushButton, LineEdit, ComboBox, TitleLabel, SubtitleLabel,
    CaptionLabel, CardWidget, FluentIcon, ToolButton,
    TogglePushButton, InfoBar, InfoBarPosition, ProgressRing,
    TextEdit, SearchLineEdit, SpinBox, DoubleSpinBox,
    StrongBodyLabel, BodyLabel, HyperlinkButton
)

# 项目根目录
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from gugu_native.theme import get_colors


class ProjectListWorker(QThread):
    """项目列表加载线程"""
    done = Signal(list)
    error = Signal(str)

    def __init__(self, trainer):
        super().__init__()
        self.trainer = trainer

    def run(self):
        try:
            projects = self.trainer.list_projects()
            self.done.emit(projects)
        except Exception as e:
            self.error.emit(str(e))


class _RecordWorker(QThread):
    """录音线程 — 避免 sd.rec() 阻塞主线程"""
    finished = Signal(object)  # numpy array 或 None
    error = Signal(str)

    def __init__(self, duration=5, sample_rate=16000, parent=None):
        super().__init__(parent)
        self.duration = duration
        self.sample_rate = sample_rate

    def run(self):
        try:
            import sounddevice as sd
            import numpy as np
            recording = sd.rec(
                int(self.duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1, dtype='float32'
            )
            sd.wait()
            self.finished.emit(recording)
        except Exception as e:
            self.error.emit(str(e))


class TrainWorker(QThread):
    """训练启动线程"""
    done = Signal(dict)
    error = Signal(str)

    def __init__(self, trainer, project_name, config, stage="s1"):
        super().__init__()
        self.trainer = trainer
        self.project_name = project_name
        self.config = config
        self.stage = stage

    def run(self):
        try:
            if self.stage == "s1":
                result = self.trainer.start_training(self.project_name, self.config)
            else:
                result = self.trainer.start_s2_training(self.project_name, self.config)
            self.done.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class TrainPage(QWidget):
    """音色训练页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("trainPage")
        self._backend = None
        self._trainer = None
        self._current_project = None
        self._train_worker = None
        self._init_ui()

        # 训练进度轮询
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(2000)  # 2秒轮询
        self._progress_timer.timeout.connect(self._poll_training_status)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(8)

        # === 顶部: 标题 + 项目选择 ===
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)

        title = TitleLabel("GPT-SoVITS 音色训练")
        top_layout.addWidget(title)

        top_layout.addStretch()

        # 项目选择
        project_label = BodyLabel("当前项目:")
        top_layout.addWidget(project_label)

        self.project_combo = ComboBox()
        self.project_combo.setFixedWidth(200)
        self.project_combo.setPlaceholderText("选择项目...")
        self.project_combo.currentTextChanged.connect(self._on_project_changed)
        top_layout.addWidget(self.project_combo)

        self.create_project_btn = PushButton("新建项目")
        self.create_project_btn.setIcon(FluentIcon.ADD)
        self.create_project_btn.clicked.connect(self._create_project)
        top_layout.addWidget(self.create_project_btn)

        self.refresh_btn = PushButton("刷新")
        self.refresh_btn.setIcon(FluentIcon.SYNC)
        self.refresh_btn.clicked.connect(self._refresh_projects)
        top_layout.addWidget(self.refresh_btn)

        main_layout.addLayout(top_layout)

        # === 主内容区: 分割面板 ===
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧: 项目信息 + 音频列表
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # 项目信息卡片
        self.project_info_group = QGroupBox("项目信息")
        info_layout = QFormLayout(self.project_info_group)
        info_layout.setSpacing(6)

        self.info_name = CaptionLabel("—")
        c = get_colors()
        self.info_name.setStyleSheet(f"color: {c.stat_working};")
        info_layout.addRow("项目名:", self.info_name)

        self.info_audio_count = CaptionLabel("0")
        info_layout.addRow("音频数:", self.info_audio_count)

        self.info_has_checkpoint = CaptionLabel("否")
        info_layout.addRow("有检查点:", self.info_has_checkpoint)

        self.info_trained = CaptionLabel("否")
        self.info_trained.setStyleSheet("color: #868e96;")
        info_layout.addRow("已训练:", self.info_trained)

        left_layout.addWidget(self.project_info_group)

        # 音频文件列表
        audio_group = QGroupBox("音频文件")
        audio_layout = QVBoxLayout(audio_group)

        self.audio_list = QListWidget()
        self.audio_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.audio_list.customContextMenuRequested.connect(self._show_audio_context_menu)
        audio_layout.addWidget(self.audio_list)

        # 音频操作按钮行
        audio_btn_layout = QHBoxLayout()

        self.upload_audio_btn = PushButton("上传音频")
        self.upload_audio_btn.setIcon(FluentIcon.FOLDER_ADD)
        self.upload_audio_btn.clicked.connect(self._upload_audio)
        audio_btn_layout.addWidget(self.upload_audio_btn)

        self.record_audio_btn = PushButton("录制")
        self.record_audio_btn.setIcon(FluentIcon.MICROPHONE)
        self.record_audio_btn.clicked.connect(self._record_audio)
        audio_btn_layout.addWidget(self.record_audio_btn)

        self.delete_audio_btn = PushButton("删除")
        self.delete_audio_btn.setIcon(FluentIcon.DELETE)
        self.delete_audio_btn.clicked.connect(self._delete_audio)
        audio_btn_layout.addWidget(self.delete_audio_btn)

        audio_layout.addLayout(audio_btn_layout)
        left_layout.addWidget(audio_group, stretch=1)

        splitter.addWidget(left_panel)

        # 右侧: Tab (参考配置 / 训练配置 / 训练进度)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.right_tabs = QTabWidget()

        # === Tab 1: 参考音频配置 ===
        ref_tab = QWidget()
        ref_layout = QVBoxLayout(ref_tab)

        # 参考音频选择
        ref_audio_layout = QHBoxLayout()
        ref_audio_label = BodyLabel("参考音频:")
        ref_audio_layout.addWidget(ref_audio_label)
        self.ref_audio_combo = ComboBox()
        self.ref_audio_combo.setFixedWidth(250)
        self.ref_audio_combo.setPlaceholderText("选择参考音频...")
        self.ref_audio_combo.currentTextChanged.connect(self._on_ref_audio_changed)
        ref_audio_layout.addWidget(self.ref_audio_combo)
        ref_audio_layout.addStretch()
        ref_layout.addLayout(ref_audio_layout)

        # 参考文本
        ref_text_label = BodyLabel("参考文本:")
        ref_layout.addWidget(ref_text_label)
        self.ref_text_edit = TextEdit()
        self.ref_text_edit.setPlaceholderText("输入参考音频对应的文本内容...")
        self.ref_text_edit.setMaximumHeight(120)
        ref_layout.addWidget(self.ref_text_edit)

        # ASR 自动识别按钮
        self.asr_btn = PushButton("ASR 自动识别")
        self.asr_btn.setIcon(FluentIcon.ROBOT)
        self.asr_btn.clicked.connect(self._auto_asr)
        ref_layout.addWidget(self.asr_btn)

        # 保存参考配置
        self.save_ref_btn = PushButton("保存参考配置")
        self.save_ref_btn.setIcon(FluentIcon.SAVE)
        self.save_ref_btn.clicked.connect(self._save_ref_config)
        ref_layout.addWidget(self.save_ref_btn)

        ref_layout.addStretch()
        self.right_tabs.addTab(ref_tab, "参考配置")

        # === Tab 2: 训练配置 ===
        train_config_tab = QWidget()
        tc_layout = QVBoxLayout(train_config_tab)

        # S1 配置
        s1_group = QGroupBox("S1 (语义模型) 训练参数")
        s1_form = QFormLayout(s1_group)

        self.s1_epochs = SpinBox()
        self.s1_epochs.setRange(1, 100)
        self.s1_epochs.setValue(10)
        s1_form.addRow("训练轮数:", self.s1_epochs)

        self.s1_batch_size = SpinBox()
        self.s1_batch_size.setRange(1, 32)
        self.s1_batch_size.setValue(4)
        s1_form.addRow("批次大小:", self.s1_batch_size)

        self.s1_lr = DoubleSpinBox()
        self.s1_lr.setRange(0.00001, 0.1)
        self.s1_lr.setValue(0.0001)
        self.s1_lr.setDecimals(5)
        self.s1_lr.setSingleStep(0.00001)
        s1_form.addRow("学习率:", self.s1_lr)

        tc_layout.addWidget(s1_group)

        # S2 配置
        s2_group = QGroupBox("S2 (声学模型) 训练参数")
        s2_form = QFormLayout(s2_group)

        self.s2_epochs = SpinBox()
        self.s2_epochs.setRange(1, 100)
        self.s2_epochs.setValue(10)
        s2_form.addRow("训练轮数:", self.s2_epochs)

        self.s2_batch_size = SpinBox()
        self.s2_batch_size.setRange(1, 32)
        self.s2_batch_size.setValue(4)
        s2_form.addRow("批次大小:", self.s2_batch_size)

        self.s2_lr = DoubleSpinBox()
        self.s2_lr.setRange(0.00001, 0.1)
        self.s2_lr.setValue(0.0001)
        self.s2_lr.setDecimals(5)
        self.s2_lr.setSingleStep(0.00001)
        s2_form.addRow("学习率:", self.s2_lr)

        tc_layout.addWidget(s2_group)

        # 保存训练参数
        self.save_train_config_btn = PushButton("保存训练参数")
        self.save_train_config_btn.setIcon(FluentIcon.SAVE)
        self.save_train_config_btn.clicked.connect(self._save_train_config)
        tc_layout.addWidget(self.save_train_config_btn)

        tc_layout.addStretch()
        self.right_tabs.addTab(train_config_tab, "训练配置")

        # === Tab 3: 训练进度 ===
        progress_tab = QWidget()
        prog_layout = QVBoxLayout(progress_tab)

        # 训练控制按钮
        train_ctrl_layout = QHBoxLayout()

        self.start_s1_btn = PushButton("开始 S1 训练")
        self.start_s1_btn.setIcon(FluentIcon.PLAY)
        self.start_s1_btn.setStyleSheet("""
            PushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #40c057, stop:1 #2f9e44);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 18px;
                font-weight: 500;
            }
            PushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2f9e44, stop:1 #2b8a3e);
            }
            PushButton:disabled {
                background: #3d3d5c;
                color: #666;
            }
        """)
        self.start_s1_btn.clicked.connect(lambda: self._start_training("s1"))
        train_ctrl_layout.addWidget(self.start_s1_btn)

        self.start_s2_btn = PushButton("开始 S2 训练")
        self.start_s2_btn.setIcon(FluentIcon.PLAY)
        self.start_s2_btn.setStyleSheet("""
            PushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7950f2, stop:1 #6741d9);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 18px;
                font-weight: 500;
            }
            PushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6741d9, stop:1 #5f3dc4);
            }
            PushButton:disabled {
                background: #3d3d5c;
                color: #666;
            }
        """)
        self.start_s2_btn.clicked.connect(lambda: self._start_training("s2"))
        train_ctrl_layout.addWidget(self.start_s2_btn)

        self.stop_train_btn = PushButton("停止训练")
        self.stop_train_btn.setIcon(FluentIcon.CANCEL)
        self.stop_train_btn.setStyleSheet("""
            PushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f03e3e, stop:1 #e03131);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 18px;
                font-weight: 500;
            }
            PushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e03131, stop:1 #c92a2a);
            }
            PushButton:disabled {
                background: #3d3d5c;
                color: #666;
            }
        """)
        self.stop_train_btn.clicked.connect(self._stop_training)
        self.stop_train_btn.setEnabled(False)
        train_ctrl_layout.addWidget(self.stop_train_btn)

        train_ctrl_layout.addStretch()
        prog_layout.addLayout(train_ctrl_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        prog_layout.addWidget(self.progress_bar)

        # 状态标签
        self.train_status_label = SubtitleLabel("就绪")
        self.train_status_label.setStyleSheet(f"color: {c.success};")
        prog_layout.addWidget(self.train_status_label)

        # 训练日志
        log_label = BodyLabel("训练日志:")
        prog_layout.addWidget(log_label)

        self.train_log = QTextEdit()
        self.train_log.setReadOnly(True)
        self.train_log.setFont(QFont("Cascadia Code", 9))
        self.train_log.setPlaceholderText("训练日志将显示在这里...")
        self.train_log.setStyleSheet("""
            QTextEdit {
                background-color: #0d0e1a;
                color: #c9d1d9;
                border: 1px solid #1e1f34;
                border-radius: 8px;
                padding: 8px;
                font-family: "Cascadia Code", "Consolas", monospace;
            }
        """)
        prog_layout.addWidget(self.train_log, stretch=1)

        # 操作按钮
        action_layout = QHBoxLayout()

        self.reset_btn = PushButton("重置项目")
        self.reset_btn.setIcon(FluentIcon.ROTATE)
        self.reset_btn.clicked.connect(self._reset_project)
        action_layout.addWidget(self.reset_btn)

        action_layout.addStretch()
        prog_layout.addLayout(action_layout)

        self.right_tabs.addTab(progress_tab, "训练进度")

        right_layout.addWidget(self.right_tabs, stretch=1)
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 550])

        main_layout.addWidget(splitter, stretch=1)

        # 延迟加载项目列表
        QTimer.singleShot(800, self._refresh_projects)

    # ========== 后端访问 ==========

    @property
    def backend(self):
        if self._backend is None:
            main_window = self.window()
            if hasattr(main_window, 'backend'):
                self._backend = main_window.backend
        return self._backend

    @property
    def trainer(self):
        if self._trainer is None:
            if self.backend and hasattr(self.backend, 'trainer'):
                self._trainer = self.backend.trainer
        return self._trainer

    def on_backend_ready(self):
        """后端就绪回调 — 刷新项目列表"""
        self._refresh_projects()

    # ========== 项目管理 ==========

    def _refresh_projects(self):
        """刷新项目列表"""
        if not self.trainer:
            return

        try:
            projects = self.trainer.list_projects()
            self.project_combo.clear()
            for p in projects:
                self.project_combo.addItem(p["name"])
                # 设置 tooltip 显示详情 — qfluentwidgets ComboBox 不支持 setItemData 的 role 参数
                # 需要访问内部 QComboBox 来设置 ToolTipRole
                idx = self.project_combo.count() - 1
                try:
                    # 尝试访问内部 QComboBox（qfluentwidgets ComboBox 的内部组合）
                    inner_cb = getattr(self.project_combo, 'comboBox', None) or getattr(self.project_combo, '_combo', None)
                    if inner_cb:
                        inner_cb.setItemData(idx, f"音频: {p.get('audio_count', 0)} | "
                                                   f"已训练: {'是' if p.get('has_trained') else '否'}",
                                             Qt.ItemDataRole.ToolTipRole)
                except Exception:
                    pass  # 内部 QComboBox 不可访问则忽略 tooltip
        except Exception as e:
            self._show_info("加载失败", str(e))

    def _on_project_changed(self, project_name: str):
        """项目切换"""
        if not project_name:
            self._current_project = None
            return

        self._current_project = project_name

        if not self.trainer:
            return

        try:
            info = self.trainer.get_project_info(project_name)

            # 更新项目信息（key 映射对齐 get_project_info() 返回格式）
            self.info_name.setText(project_name)
            audio_files = info.get("audio_files", [])
            self.info_audio_count.setText(str(len(audio_files)))
            checkpoints = info.get("checkpoints", [])
            self.info_has_checkpoint.setText("是" if checkpoints else "否")
            trained_count = info.get("trained_count", 0)
            has_trained = trained_count > 0 or info.get("has_s2_trained", False)
            self.info_trained.setText("是" if has_trained else "否")
            c = get_colors()
            self.info_trained.setStyleSheet(f"color: {c.success};" if has_trained else f"color: {c.text_muted};")

            # 更新音频列表
            self.audio_list.clear()
            # 从项目配置获取参考音频路径
            config = self.trainer.get_project_config(project_name)
            ref_audio = config.get("ref_audio", "")

            self.ref_audio_combo.clear()
            for audio in audio_files:
                name = audio.get("filename", audio.get("name", ""))
                is_trained = audio.get("is_trained", False)
                item = QListWidgetItem(f"{'🎤 ' if is_trained else '🎵 '}{name}")
                item.setData(Qt.ItemDataRole.UserRole, audio)
                self.audio_list.addItem(item)
                self.ref_audio_combo.addItem(name)

            # 设置当前参考音频
            if ref_audio:
                ref_name = os.path.basename(ref_audio)
                idx = self.ref_audio_combo.findText(ref_name)
                if idx >= 0:
                    self.ref_audio_combo.setCurrentIndex(idx)

            # 更新参考文本
            ref_text = config.get("ref_text", "")
            self.ref_text_edit.setPlainText(ref_text)

            # 更新训练参数
            defaults = self.trainer.get_train_defaults(project_name)
            s1 = defaults.get("s1_defaults", {})
            s2 = defaults.get("s2_defaults", {})
            if s1:
                if "epochs" in s1: self.s1_epochs.setValue(s1["epochs"])
                if "batch_size" in s1: self.s1_batch_size.setValue(s1["batch_size"])
                if "learning_rate" in s1: self.s1_lr.setValue(s1["learning_rate"])
            if s2:
                if "epochs" in s2: self.s2_epochs.setValue(s2["epochs"])
                if "batch_size" in s2: self.s2_batch_size.setValue(s2["batch_size"])
                if "learning_rate" in s2: self.s2_lr.setValue(s2["learning_rate"])

        except Exception as e:
            self._show_info("加载项目失败", str(e))

    def _create_project(self):
        """创建新项目"""
        name, ok = QInputDialog.getText(self, "新建项目", "项目名称:")
        if ok and name:
            if not self.trainer:
                return
            result = self.trainer.create_project(name)
            if result.get("success"):
                self._show_info("成功", f"项目 '{name}' 已创建")
                self._refresh_projects()
                self.project_combo.setCurrentText(name)
            else:
                self._show_info("失败", "创建项目失败")

    # ========== 音频管理 ==========

    def _upload_audio(self):
        """上传音频文件"""
        if not self._current_project or not self.trainer:
            self._show_info("提示", "请先选择项目")
            return

        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择音频文件", "",
            "音频文件 (*.wav *.mp3 *.flac *.m4a *.ogg);;所有文件 (*)"
        )

        for path in file_paths:
            try:
                filename = os.path.basename(path)
                with open(path, 'rb') as f:
                    audio_data = f.read()
                result = self.trainer.save_audio(self._current_project, filename, audio_data)
                if result.get("success"):
                    self._append_log(f"上传成功: {filename} ({len(audio_data)//1024}KB)")
                else:
                    self._append_log(f"上传失败: {filename}")
            except Exception as e:
                self._append_log(f"上传错误: {e}")

        self._on_project_changed(self._current_project)

    def _record_audio(self):
        """录制音频（异步线程，避免阻塞 UI）"""
        if not self._current_project:
            self._show_info("提示", "请先选择项目")
            return

        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            self._show_info("缺少依赖", "录音需要 sounddevice: pip install sounddevice")
            return

        # 禁用录音按钮，防止重复点击
        self.record_audio_btn.setEnabled(False)
        self.record_audio_btn.setText("录音中...")

        self._record_worker = _RecordWorker(duration=5, sample_rate=16000)
        self._record_worker.finished.connect(self._on_record_done)
        self._record_worker.error.connect(self._on_record_error)
        self._record_worker.start()

    @Slot(object)
    def _on_record_done(self, recording):
        """录音完成回调"""
        self.record_audio_btn.setEnabled(True)
        self.record_audio_btn.setText("录制音频")

        if recording is None:
            return

        try:
            import numpy as np
            import wave

            # 保存到项目 raw 目录
            if self.trainer:
                raw_dir = os.path.join(
                    str(self.trainer.projects_dir), self._current_project, "raw"
                )
                os.makedirs(raw_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"record_{timestamp}.wav"
                filepath = os.path.join(raw_dir, filename)

                audio_int16 = (recording * 32767).astype(np.int16)
                with wave.open(filepath, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(audio_int16.tobytes())

                self._append_log(f"录音保存: {filename}")

                # 更新项目配置
                config = self.trainer.get_project_config(self._current_project)
                if not config.get("ref_audio"):
                    self.trainer.update_project_config(self._current_project, "ref_audio", filepath)

                self._on_project_changed(self._current_project)

        except Exception as e:
            self._append_log(f"录音保存失败: {e}")

    @Slot(str)
    def _on_record_error(self, error_msg: str):
        """录音失败回调"""
        self.record_audio_btn.setEnabled(True)
        self.record_audio_btn.setText("录制音频")
        self._show_info("录音失败", error_msg)

    def _delete_audio(self):
        """删除选中的音频"""
        if not self._current_project or not self.trainer:
            return

        current = self.audio_list.currentItem()
        if not current:
            return

        audio_data = current.data(Qt.ItemDataRole.UserRole)
        filename = audio_data.get("filename", audio_data.get("name", "")) if audio_data else current.text().split(" ", 1)[-1]

        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除音频 '{filename}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            result = self.trainer.delete_audio(self._current_project, filename)
            if result.get("success"):
                self._show_info("成功", "音频已删除")
                self._on_project_changed(self._current_project)

    def _show_audio_context_menu(self, pos):
        """音频列表右键菜单"""
        item = self.audio_list.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)

        set_ref_action = QAction("设为参考音频", self)
        set_ref_action.triggered.connect(self._set_as_ref_audio)
        menu.addAction(set_ref_action)

        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self._delete_audio)
        menu.addAction(delete_action)

        menu.exec(self.audio_list.viewport().mapToGlobal(pos))

    def _set_as_ref_audio(self):
        """设为参考音频"""
        if not self._current_project or not self.trainer:
            return

        current = self.audio_list.currentItem()
        if not current:
            return

        audio_data = current.data(Qt.ItemDataRole.UserRole)
        filename = audio_data.get("filename", audio_data.get("name", "")) if audio_data else ""

        if filename:
            raw_dir = os.path.join(str(self.trainer.projects_dir), self._current_project, "raw")
            ref_path = os.path.join(raw_dir, filename)
            self.trainer.update_project_config(self._current_project, "ref_audio", ref_path)
            self._show_info("成功", f"已设为参考音频: {filename}")
            self._on_project_changed(self._current_project)

    # ========== 参考配置 ==========

    def _on_ref_audio_changed(self, filename: str):
        """参考音频切换"""
        if not self._current_project or not self.trainer:
            return

        # 尝试加载已保存的文本
        try:
            texts_file = os.path.join(
                str(self.trainer.projects_dir), self._current_project, "texts.json"
            )
            if os.path.exists(texts_file):
                with open(texts_file, 'r', encoding='utf-8') as f:
                    texts = json.load(f)
                base_name = filename.rsplit(".", 1)[0] if "." in filename else filename
                if base_name in texts:
                    self.ref_text_edit.setPlainText(texts[base_name])
                    return
            self.ref_text_edit.clear()
        except Exception:
            self.ref_text_edit.clear()

    def _save_ref_config(self):
        """保存参考配置"""
        if not self._current_project or not self.trainer:
            return

        ref_audio_name = self.ref_audio_combo.currentText()
        ref_text = self.ref_text_edit.toPlainText().strip()

        if ref_audio_name:
            raw_dir = os.path.join(str(self.trainer.projects_dir), self._current_project, "raw")
            ref_path = os.path.join(raw_dir, ref_audio_name)
            self.trainer.update_project_config(self._current_project, "ref_audio", ref_path)

            # 保存文本
            if ref_text:
                self.trainer.save_text(self._current_project, ref_audio_name, ref_text)

        self._show_info("成功", "参考配置已保存")

    def _auto_asr(self):
        """ASR 自动识别参考音频文本"""
        if not self._current_project or not self.trainer:
            return

        ref_name = self.ref_audio_combo.currentText()
        if not ref_name:
            self._show_info("提示", "请先选择参考音频")
            return

        self.asr_btn.setEnabled(False)
        self.asr_btn.setText("识别中...")

        try:
            result = self.trainer.recognize_audio_text(self._current_project, ref_name)
            if result.get("success"):
                text = result.get("text", "")
                self.ref_text_edit.setPlainText(text)
                self._show_info("识别成功", f"文本长度: {len(text)}")
            else:
                self._show_info("识别失败", result.get("error", "未知错误"))
        except Exception as e:
            self._show_info("识别失败", str(e))
        finally:
            self.asr_btn.setEnabled(True)
            self.asr_btn.setText("ASR 自动识别")

    # ========== 训练配置 ==========

    def _save_train_config(self):
        """保存训练参数"""
        if not self._current_project or not self.trainer:
            return

        s1_config = {
            "epochs": self.s1_epochs.value(),
            "batch_size": self.s1_batch_size.value(),
            "learning_rate": self.s1_lr.value(),
        }
        s2_config = {
            "epochs": self.s2_epochs.value(),
            "batch_size": self.s2_batch_size.value(),
            "learning_rate": self.s2_lr.value(),
        }

        result = self.trainer.save_train_defaults(self._current_project, s1_config, s2_config)
        if result.get("success"):
            self._show_info("成功", "训练参数已保存")

    # ========== 训练执行 ==========

    def _start_training(self, stage: str):
        """启动训练"""
        if not self._current_project or not self.trainer:
            self._show_info("提示", "请先选择项目")
            return

        # 检查参考配置
        config = self.trainer.get_project_config(self._current_project)
        if not config.get("ref_audio") or not config.get("ref_text"):
            self._show_info("提示", "请先配置参考音频和文本")
            self.right_tabs.setCurrentIndex(0)
            return

        # 构建训练配置
        train_config = {
            "epochs": self.s1_epochs.value() if stage == "s1" else self.s2_epochs.value(),
            "batch_size": self.s1_batch_size.value() if stage == "s1" else self.s2_batch_size.value(),
        }

        self._append_log(f"=== 开始 {stage.upper()} 训练 ===")
        self._set_training_state(True)
        self.train_status_label.setText(f"{stage.upper()} 训练中...")
        c = get_colors()
        self.train_status_label.setStyleSheet(f"color: {c.warning};")

        # 设置进度回调
        self.trainer.set_progress_callback(self._on_train_progress)

        self._train_worker = TrainWorker(self.trainer, self._current_project, train_config, stage)
        self._train_worker.done.connect(lambda r: self._on_train_done(stage, r))
        self._train_worker.error.connect(lambda e: self._on_train_error(stage, e))
        self._train_worker.start()

        # 启动进度轮询
        self._progress_timer.start()

    def _stop_training(self):
        """停止训练"""
        if not self.trainer:
            return

        result = self.trainer.stop_training()
        self._append_log("训练已停止")
        self._set_training_state(False)
        c = get_colors()
        self.train_status_label.setText("已停止")
        self.train_status_label.setStyleSheet(f"color: {c.error};")

    def _set_training_state(self, training: bool):
        """设置训练中 UI 状态"""
        self.start_s1_btn.setEnabled(not training)
        self.start_s2_btn.setEnabled(not training)
        self.stop_train_btn.setEnabled(training)
        self._progress_timer.start() if training else self._progress_timer.stop()

    def _on_train_progress(self, progress_data: dict):
        """训练进度回调"""
        step = progress_data.get("step", "")
        message = progress_data.get("message", "")
        progress = progress_data.get("progress", 0)
        action = progress_data.get("action", "")

        self.progress_bar.setValue(int(progress))
        self._append_log(f"[{step}] {message}")
        self.train_status_label.setText(message[:50])

    def _poll_training_status(self):
        """轮询训练状态"""
        if not self.trainer:
            return

        try:
            status = self.trainer.get_training_status()
            if status and not status.get("is_training", False):
                self._set_training_state(False)
                c = get_colors()
                self.train_status_label.setText("训练完成")
                self.train_status_label.setStyleSheet(f"color: {c.success};")
        except Exception:
            pass

    def _on_train_done(self, stage: str, result: dict):
        """训练完成"""
        self._set_training_state(False)

        if result.get("success"):
            c = get_colors()
            self.train_status_label.setText(f"{stage.upper()} 训练完成!")
            self.train_status_label.setStyleSheet(f"color: {c.success};")
            self.progress_bar.setValue(100)
            self._append_log(f"=== {stage.upper()} 训练完成! ===")
            self._show_info("训练完成", f"{stage.upper()} 训练已成功完成!")
            self._on_project_changed(self._current_project)
        else:
            error = result.get("error", "未知错误")
            c = get_colors()
            self.train_status_label.setText(f"训练失败: {error[:30]}")
            self.train_status_label.setStyleSheet(f"color: {c.error};")
            self._append_log(f"训练失败: {error}")
            self._show_info("训练失败", error)

    def _on_train_error(self, stage: str, error: str):
        """训练错误"""
        self._set_training_state(False)
        c = get_colors()
        self.train_status_label.setText("训练出错")
        self.train_status_label.setStyleSheet(f"color: {c.error};")
        self._append_log(f"训练错误: {error}")

    # ========== 项目操作 ==========

    def _reset_project(self):
        """重置项目"""
        if not self._current_project or not self.trainer:
            return

        reply = QMessageBox.warning(
            self, "确认重置",
            f"确定要重置项目 '{self._current_project}' 吗？\n这将清除训练数据但保留原始音频。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            result = self.trainer.reset_project(self._current_project, delete_all=False)
            if result.get("success"):
                self._show_info("成功", "项目已重置")
                self._on_project_changed(self._current_project)

    # ========== 工具 ==========

    def _append_log(self, text: str):
        """追加训练日志"""
        from gugu_native.theme import get_colors
        c = get_colors()
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.train_log.append(f'<span style="color: {c.log_timestamp};">[{timestamp}]</span> {text}')
        self.train_log.moveCursor(QTextCursor.MoveOperation.End)

    def _show_info(self, title: str, content: str):
        """显示信息栏"""
        InfoBar.info(
            title=title, content=content,
            parent=self, position=InfoBarPosition.TOP, duration=3000,
        )

    # ========== 主题刷新（v1.9.80）==========

    def refresh_theme(self):
        """主题切换时刷新硬编码样式"""
        from gugu_native.theme import get_colors
        c = get_colors()

        # 训练日志
        self.train_log.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c.log_bg};
                color: {c.log_text};
                border: 1px solid {c.card_border};
                border-radius: 8px;
                padding: 8px;
                font-family: "Cascadia Code", "Consolas", monospace;
            }}
        """)

        # 训练按钮样式
        btn_styles = {
            self.start_s1_btn: ("#40c057", "#2f9e44", "#2b8a3e"),
            self.start_s2_btn: ("#7950f2", "#6741d9", "#5f3dc4"),
            self.stop_train_btn: ("#f03e3e", "#e03131", "#c92a2a"),
        }
        for btn, (c1, c2, c3) in btn_styles.items():
            btn.setStyleSheet(f"""
                PushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {c1}, stop:1 {c2});
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 6px 18px;
                    font-weight: 500;
                }}
                PushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {c2}, stop:1 {c3});
                }}
                PushButton:disabled {{
                    background: {c.card_border};
                    color: {c.text_muted};
                }}
            """)

        # 状态标签
        self.train_status_label.setStyleSheet(f"color: {c.success};")

        # 项目信息
        self.info_name.setStyleSheet(f"color: {c.stat_working};")
        self.info_trained.setStyleSheet(f"color: {c.text_muted};")
