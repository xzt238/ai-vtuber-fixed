"""
系统日志页面 — 实时日志 + LLM智能分析

功能：
1. 实时系统日志流显示（类似声音训练页面风格）
2. 系统状态信息展示（CPU/内存/GPU等）
3. LLM智能分析（自动/手动）
4. 分析报告管理（左侧文件夹式列表）
   - 自动报告：同一天更新同一份
   - 手动报告：单独存储
5. 报告自动清理（保留最近30天）
"""

import os
import re
import json
import logging
import threading
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from collections import Counter

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QLabel, QSpinBox, QFileDialog, QTreeWidget,
    QTreeWidgetItem, QHeaderView, QSplitter, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor, QFont, QColor

from qfluentwidgets import (
    PushButton, FluentIcon, CaptionLabel, InfoBar,
    ComboBox, CheckBox, SearchLineEdit, StrongBodyLabel
)

from gugu_native.theme import get_colors, register_theme_callback

logger = logging.getLogger('LogPage')

# 配置常量
REPORTS_DIR = Path(__file__).parent.parent.parent / "app" / "cache" / "log_reports"
MAX_LOG_BUFFER = 10000
MAX_REPORT_DAYS = 30  # 报告保留天数
SYS_INFO_UPDATE_INTERVAL = 3000  # 系统信息更新间隔(ms)
LOG_FLUSH_INTERVAL = 100  # 日志刷新间隔(ms)

# 日志级别颜色
LOG_COLORS = {
    "CRITICAL": "#ff4757",
    "ERROR": "#ff6b6b",
    "WARNING": "#ffa502",
    "INFO": "#d4d4d4",
    "DEBUG": "#70a1ff",
}

# 正则表达式：匹配日志格式 [timestamp] [level] message
LOG_PATTERN = re.compile(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\] \[(\w+)\] (.+)')


class LogPage(QWidget):
    """系统日志页面"""

    def __init__(self, parent=None) -> None:
        """初始化系统日志页面"""
        super().__init__(parent)
        self.setObjectName("logPage")
        
        # 日志缓冲区
        self._log_buffer: List[str] = []
        self._auto_scroll = True
        self._current_filter = "ALL"
        self._search_keyword = ""
        
        # 分析报告相关
        self._analysis_reports: Dict[str, Dict[str, Any]] = {}
        self._current_report: Optional[Dict[str, Any]] = None
        self._analysis_interval = 10  # 默认10分钟
        self._is_analyzing = False
        self._auto_analysis_enabled = True
        
        # 系统信息缓存
        self._sys_info_cache: Dict[str, Any] = {}
        self._sys_info_cache_time: float = 0
        
        # 内存泄漏监控
        self._memory_history: List[Tuple[float, float]] = []  # [(timestamp, memory_mb), ...]
        self._memory_leak_warning_shown = False
        self._max_memory_history = 60  # 保留最近60个采样点（约5分钟）
        
        # 确保报告目录存在
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        
        # 初始化 UI
        self._init_ui()
        
        # 注册主题回调
        register_theme_callback(self._apply_theme)
        
        # 启动定时器
        self._start_timers()
        
        # 注册日志处理器
        self._setup_log_handler()
        
        # 加载历史报告并清理旧报告
        self._load_history_reports()
        self._cleanup_old_reports()
        
        logger.info("LogPage initialized")

    def _init_ui(self) -> None:
        """初始化 UI 布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # 主内容区: 左右分割
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：报告列表
        left_panel = self._create_report_panel()
        main_splitter.addWidget(left_panel)
        
        # 右侧：日志和分析
        right_panel = self._create_right_panel()
        main_splitter.addWidget(right_panel)
        
        # 设置分割比例（左侧20%，右侧80%）
        main_splitter.setSizes([200, 800])
        
        layout.addWidget(main_splitter)

    def _create_report_panel(self) -> QWidget:
        """创建报告列表面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 标题
        title = QLabel("📁 分析报告")
        title.setStyleSheet("font-weight: bold; font-size: 11px; padding: 2px;")
        layout.addWidget(title)
        
        # 报告树
        self.report_tree = QTreeWidget()
        self.report_tree.setHeaderLabels(["报告", "时间", "类型"])
        self.report_tree.setColumnCount(3)
        
        # 设置列宽
        header = self.report_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.report_tree.setColumnWidth(1, 70)
        self.report_tree.setColumnWidth(2, 45)
        
        self.report_tree.currentItemChanged.connect(self._on_report_selected)
        self.report_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                font-size: 11px;
            }
            QTreeWidget::item {
                padding: 2px;
            }
            QTreeWidget::item:selected {
                background-color: #404040;
            }
        """)
        layout.addWidget(self.report_tree)
        
        # 按钮栏
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        
        refresh_btn = PushButton("刷新")
        refresh_btn.setIcon(FluentIcon.SYNC)
        refresh_btn.clicked.connect(self._load_history_reports)
        btn_layout.addWidget(refresh_btn)
        
        export_btn = PushButton("导出")
        export_btn.setIcon(FluentIcon.SAVE)
        export_btn.clicked.connect(self._export_report)
        btn_layout.addWidget(export_btn)
        
        delete_btn = PushButton("删除")
        delete_btn.setIcon(FluentIcon.DELETE)
        delete_btn.clicked.connect(self._delete_report)
        btn_layout.addWidget(delete_btn)
        
        layout.addLayout(btn_layout)
        
        return panel

    def _create_right_panel(self) -> QWidget:
        """创建右侧面板（日志+分析）"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 上下分割
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 上半部分：实时日志
        log_widget = self._create_log_widget()
        splitter.addWidget(log_widget)
        
        # 下半部分：LLM分析
        analysis_widget = self._create_analysis_widget()
        splitter.addWidget(analysis_widget)
        
        # 设置分割比例（日志65%，分析35%）
        splitter.setSizes([650, 350])
        
        layout.addWidget(splitter)
        
        return panel

    def _create_log_widget(self) -> QWidget:
        """创建日志显示组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 系统信息栏（单行紧凑）
        sys_info = self._create_sys_info_bar()
        layout.addWidget(sys_info)
        
        # 工具栏
        toolbar = self._create_log_toolbar()
        layout.addLayout(toolbar)
        
        # 日志显示区域
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Consolas", 10))
        self.log_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.log_display)
        
        return widget

    def _create_sys_info_bar(self) -> QWidget:
        """创建系统信息栏"""
        widget = QWidget()
        widget.setStyleSheet("background: #252525; border-radius: 4px; padding: 2px;")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)
        
        # 信息标签样式
        label_style = "font-size: 11px; color: #aaa;"
        
        self.cpu_label = CaptionLabel("CPU: --%")
        self.cpu_label.setStyleSheet(label_style)
        layout.addWidget(self.cpu_label)
        
        self.memory_label = CaptionLabel("RAM: --%")
        self.memory_label.setStyleSheet(label_style)
        layout.addWidget(self.memory_label)
        
        self.gpu_label = CaptionLabel("GPU: --")
        self.gpu_label.setStyleSheet(label_style)
        layout.addWidget(self.gpu_label)
        
        # 内存泄漏状态
        self.memory_leak_label = CaptionLabel("内存: 正常")
        self.memory_leak_label.setStyleSheet(label_style + "color: #2ed573;")
        layout.addWidget(self.memory_leak_label)
        
        # 分隔符
        sep = QLabel("│")
        sep.setStyleSheet("color: #555;")
        layout.addWidget(sep)
        
        self.log_count_label = CaptionLabel("日志: 0")
        self.log_count_label.setStyleSheet(label_style)
        layout.addWidget(self.log_count_label)
        
        self.error_count_label = CaptionLabel("错误: 0")
        self.error_count_label.setStyleSheet(label_style + "color: #ff6b6b;")
        layout.addWidget(self.error_count_label)
        
        self.warning_count_label = CaptionLabel("警告: 0")
        self.warning_count_label.setStyleSheet(label_style + "color: #ffa502;")
        layout.addWidget(self.warning_count_label)
        
        layout.addStretch()
        
        return widget

    def _create_log_toolbar(self) -> QHBoxLayout:
        """创建日志工具栏"""
        layout = QHBoxLayout()
        layout.setSpacing(8)
        
        # 自动滚动
        self.auto_scroll_cb = CheckBox("自动滚动")
        self.auto_scroll_cb.setChecked(True)
        self.auto_scroll_cb.toggled.connect(self._toggle_auto_scroll)
        layout.addWidget(self.auto_scroll_cb)
        
        # 级别过滤
        layout.addWidget(QLabel("级别:"))
        self.level_combo = ComboBox()
        self.level_combo.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.setCurrentText("ALL")
        self.level_combo.currentTextChanged.connect(self._filter_changed)
        layout.addWidget(self.level_combo)
        
        # 搜索
        layout.addWidget(QLabel("搜索:"))
        self.search_input = SearchLineEdit()
        self.search_input.setPlaceholderText("输入关键词...")
        self.search_input.textChanged.connect(self._search_changed)
        layout.addWidget(self.search_input)
        
        layout.addStretch()
        
        # 操作按钮
        clear_btn = PushButton("清空")
        clear_btn.setIcon(FluentIcon.DELETE)
        clear_btn.clicked.connect(self._clear_logs)
        layout.addWidget(clear_btn)
        
        export_btn = PushButton("导出日志")
        export_btn.setIcon(FluentIcon.SAVE)
        export_btn.clicked.connect(self._export_logs)
        layout.addWidget(export_btn)
        
        return layout

    def _create_analysis_widget(self) -> QWidget:
        """创建分析组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 工具栏
        toolbar = self._create_analysis_toolbar()
        layout.addLayout(toolbar)
        
        # 分析结果显示
        self.analysis_display = QTextEdit()
        self.analysis_display.setReadOnly(True)
        self.analysis_display.setFont(QFont("Microsoft YaHei", 10))
        self.analysis_display.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a2e;
                color: #e0e0e0;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        self.analysis_display.setPlaceholderText(
            "📊 LLM智能分析报告\n\n"
            "点击「手动分析」或等待自动分析...\n\n"
            "报告内容：\n"
            "• 系统健康状态评估\n"
            "• 日志统计与错误分析\n"
            "• 异常模式识别\n"
            "• 性能瓶颈分析\n"
            "• 优化建议与行动计划"
        )
        layout.addWidget(self.analysis_display)
        
        return widget

    def _create_analysis_toolbar(self) -> QHBoxLayout:
        """创建分析工具栏"""
        layout = QHBoxLayout()
        layout.setSpacing(8)
        
        # 标题
        title = QLabel("🤖 LLM智能分析")
        title.setStyleSheet("font-weight: bold; font-size: 11px;")
        layout.addWidget(title)
        
        layout.addSpacing(16)
        
        # 自动分析
        self.auto_analysis_cb = CheckBox("自动分析")
        self.auto_analysis_cb.setChecked(self._auto_analysis_enabled)
        self.auto_analysis_cb.toggled.connect(self._toggle_auto_analysis)
        layout.addWidget(self.auto_analysis_cb)
        
        # 间隔设置
        layout.addWidget(QLabel("间隔:"))
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(1, 60)
        self.interval_spinbox.setValue(self._analysis_interval)
        self.interval_spinbox.setSuffix(" 分钟")
        self.interval_spinbox.setFixedWidth(80)
        self.interval_spinbox.valueChanged.connect(self._update_analysis_interval)
        layout.addWidget(self.interval_spinbox)
        
        layout.addStretch()
        
        # 手动分析按钮
        analyze_btn = PushButton("🔍 手动分析")
        analyze_btn.setIcon(FluentIcon.SEARCH)
        analyze_btn.clicked.connect(self._run_manual_analysis)
        layout.addWidget(analyze_btn)
        
        return layout

    def _start_timers(self) -> None:
        """启动定时器"""
        # 日志刷新定时器
        self._log_timer = QTimer(self)
        self._log_timer.timeout.connect(self._flush_log_buffer)
        self._log_timer.start(LOG_FLUSH_INTERVAL)
        
        # 系统信息更新定时器
        self._sys_info_timer = QTimer(self)
        self._sys_info_timer.timeout.connect(self._update_system_info)
        self._sys_info_timer.start(SYS_INFO_UPDATE_INTERVAL)
        
        # 自动分析定时器
        self._analysis_timer = QTimer(self)
        self._analysis_timer.timeout.connect(self._run_auto_analysis)
        self._analysis_timer.start(self._analysis_interval * 60 * 1000)

    def _setup_log_handler(self) -> None:
        """设置日志处理器"""
        self._log_handler = LogHandler(self)
        self._log_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s')
        )
        logging.getLogger().addHandler(self._log_handler)

    # ==================== 日志操作 ====================

    def _toggle_auto_scroll(self, checked: bool) -> None:
        """切换自动滚动"""
        self._auto_scroll = checked

    def _filter_changed(self, level: str) -> None:
        """日志级别过滤变更"""
        self._current_filter = level
        self._refresh_display()

    def _search_changed(self, keyword: str) -> None:
        """搜索关键词变更"""
        self._search_keyword = keyword
        self._refresh_display()

    def _clear_logs(self) -> None:
        """清空日志"""
        self._log_buffer.clear()
        self.log_display.clear()
        self._update_log_counts()
        logger.info("Logs cleared")

    def _export_logs(self) -> None:
        """导出日志"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出日志",
                f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "文本文件 (*.txt);;所有文件 (*)"
            )
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_display.toPlainText())
                InfoBar.success("导出成功", f"日志已导出到: {filename}", parent=self)
        except Exception as e:
            InfoBar.error("导出失败", f"错误: {e}", parent=self)

    def _refresh_display(self) -> None:
        """刷新日志显示"""
        self.log_display.clear()
        for log_line in self._log_buffer:
            if self._should_show_log(log_line):
                self._append_log_to_display(log_line)
        
        if self._auto_scroll:
            self._scroll_to_bottom()

    def _should_show_log(self, log_line: str) -> bool:
        """判断是否应该显示该日志"""
        # 级别过滤
        if self._current_filter != "ALL":
            if f"[{self._current_filter}]" not in log_line:
                return False
        
        # 关键词搜索
        if self._search_keyword:
            if self._search_keyword.lower() not in log_line.lower():
                return False
        
        return True

    def _append_log_to_display(self, log_line: str) -> None:
        """添加日志到显示区域（带颜色）"""
        # 根据日志级别设置颜色
        color = LOG_COLORS.get("INFO", "#d4d4d4")
        for level, level_color in LOG_COLORS.items():
            if f"[{level}]" in log_line:
                color = level_color
                break
        
        self.log_display.setTextColor(QColor(color))
        self.log_display.append(log_line)

    def _scroll_to_bottom(self) -> None:
        """滚动到底部"""
        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_display.setTextCursor(cursor)

    def _flush_log_buffer(self) -> None:
        """刷新日志缓冲区（定时器调用）"""
        pass

    def add_log(self, message: str, level: str = "INFO") -> None:
        """添加日志条目"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_line = f"[{timestamp}] [{level}] {message}"
        
        self._log_buffer.append(log_line)
        
        # 限制缓冲区大小
        if len(self._log_buffer) > MAX_LOG_BUFFER:
            self._log_buffer = self._log_buffer[-MAX_LOG_BUFFER:]
        
        # 如果符合过滤条件，添加到显示
        if self._should_show_log(log_line):
            self._append_log_to_display(log_line)
            
            if self._auto_scroll:
                self._scroll_to_bottom()

    def _update_log_counts(self) -> None:
        """更新日志计数"""
        total = len(self._log_buffer)
        errors = sum(1 for log in self._log_buffer if "[ERROR]" in log or "[CRITICAL]" in log)
        warnings = sum(1 for log in self._log_buffer if "[WARNING]" in log)
        
        self.log_count_label.setText(f"日志: {total}")
        self.error_count_label.setText(f"错误: {errors}")
        self.warning_count_label.setText(f"警告: {warnings}")

    # ==================== 系统信息 ====================

    def _update_system_info(self) -> None:
        """更新系统信息（带内存泄漏检测）"""
        try:
            import psutil
            import time
            
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0)
            self.cpu_label.setText(f"CPU: {cpu_percent:.0f}%")
            
            # 内存
            mem = psutil.virtual_memory()
            memory_mb = mem.used / (1024 * 1024)
            self.memory_label.setText(f"RAM: {mem.percent:.0f}%")
            
            # 记录内存历史
            current_time = time.time()
            self._memory_history.append((current_time, memory_mb))
            
            # 限制历史记录数量
            if len(self._memory_history) > self._max_memory_history:
                self._memory_history = self._memory_history[-self._max_memory_history:]
            
            # 检测内存泄漏
            self._check_memory_leak()
            
            # GPU
            gpu_info = self._get_gpu_info()
            self.gpu_label.setText(f"GPU: {gpu_info}")
            
            # 更新日志计数
            self._update_log_counts()
                
        except Exception as e:
            logger.debug(f"更新系统信息失败: {e}")

    def _check_memory_leak(self) -> None:
        """检测内存泄漏"""
        try:
            # 至少需要10个采样点
            if len(self._memory_history) < 10:
                return
            
            # 获取最近的内存使用数据
            recent_data = self._memory_history[-10:]
            times = [t for t, _ in recent_data]
            memories = [m for _, m in recent_data]
            
            # 计算内存增长率（MB/分钟）
            time_span = (times[-1] - times[0]) / 60  # 转换为分钟
            if time_span < 0.5:  # 至少30秒的数据
                return
            
            memory_growth = memories[-1] - memories[0]
            growth_rate = memory_growth / time_span  # MB/分钟
            
            # 计算线性回归斜率（更准确）
            n = len(memories)
            sum_x = sum(range(n))
            sum_y = sum(memories)
            sum_xy = sum(i * m for i, m in enumerate(memories))
            sum_x2 = sum(i * i for i in range(n))
            
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
            
            # 判断是否可能存在内存泄漏
            # 斜率 > 5MB/分钟 且 持续增长
            if slope > 5 and growth_rate > 3:
                if not self._memory_leak_warning_shown:
                    self._memory_leak_warning_shown = True
                    warning_msg = f"⚠️ 检测到内存持续增长: {growth_rate:.1f}MB/分钟, 当前: {memories[-1]:.0f}MB"
                    logger.warning(warning_msg)
                    
                    # 在日志中显示警告
                    QTimer.singleShot(0, lambda: InfoBar.warning(
                        "内存泄漏警告",
                        f"内存持续增长 {growth_rate:.1f}MB/分钟",
                        duration=5000,
                        parent=self
                    ))
                
                # 更新状态标签
                QTimer.singleShot(0, lambda: self._update_memory_leak_status(
                    f"⚠️ +{growth_rate:.1f}MB/分", "#ffa502"
                ))
            else:
                # 内存稳定或下降，重置警告标志
                if slope < 1:
                    self._memory_leak_warning_shown = False
                    QTimer.singleShot(0, lambda: self._update_memory_leak_status(
                        "内存: 正常", "#2ed573"
                    ))
                    
        except Exception as e:
            logger.debug(f"内存泄漏检测失败: {e}")

    def _update_memory_leak_status(self, text: str, color: str) -> None:
        """更新内存泄漏状态标签"""
        try:
            self.memory_leak_label.setText(text)
            self.memory_leak_label.setStyleSheet(f"font-size: 11px; color: {color};")
        except Exception:
            pass

    def get_memory_stats(self) -> Dict[str, Any]:
        """获取内存统计信息"""
        if len(self._memory_history) < 2:
            return {"status": "数据不足"}
        
        try:
            memories = [m for _, m in self._memory_history]
            
            return {
                "current_mb": memories[-1],
                "min_mb": min(memories),
                "max_mb": max(memories),
                "avg_mb": sum(memories) / len(memories),
                "samples": len(memories),
                "trend": "上升" if memories[-1] > memories[0] else "下降" if memories[-1] < memories[0] else "稳定"
            }
        except Exception:
            return {"status": "计算失败"}

    def _get_gpu_info(self) -> str:
        """获取GPU信息"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=2,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if result.returncode == 0:
                return f"{result.stdout.strip()}%"
        except:
            pass
        return "N/A"

    def _get_system_info_for_prompt(self) -> str:
        """获取系统信息用于LLM提示词"""
        try:
            import psutil
            
            cpu = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            
            # 运行时间
            uptime = datetime.now() - boot_time
            days = uptime.days
            hours = uptime.seconds // 3600
            
            # GPU信息
            gpu_info = self._get_gpu_info()
            
            return f"""系统状态：
- CPU: {cpu_count}核, 使用率 {cpu}%
- 内存: {mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB ({mem.percent}%)
- 磁盘: {disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB ({disk.percent}%)
- GPU: {gpu_info}
- 运行时间: {days}天{hours}小时
- 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        except Exception as e:
            return f"系统信息获取失败: {e}"

    # ==================== 主题 ====================

    def _apply_theme(self) -> None:
        """应用主题样式"""
        colors = get_colors()
        
        log_style = f"""
            QTextEdit {{
                background-color: {colors.card_bg};
                color: {colors.text_primary};
                border: 1px solid {colors.card_border};
                border-radius: 6px;
                padding: 8px;
            }}
        """
        
        analysis_style = f"""
            QTextEdit {{
                background-color: {colors.card_bg};
                color: {colors.text_primary};
                border: 1px solid {colors.card_border};
                border-radius: 6px;
                padding: 10px;
            }}
        """
        
        self.log_display.setStyleSheet(log_style)
        self.analysis_display.setStyleSheet(analysis_style)

    # ==================== 分析功能 ====================

    def _toggle_auto_analysis(self, checked: bool) -> None:
        """切换自动分析"""
        self._auto_analysis_enabled = checked
        if checked:
            self._analysis_timer.start(self._analysis_interval * 60 * 1000)
            logger.info(f"自动分析已启用，间隔 {self._analysis_interval} 分钟")
        else:
            self._analysis_timer.stop()
            logger.info("自动分析已禁用")

    def _update_analysis_interval(self, value: int) -> None:
        """更新分析间隔"""
        self._analysis_interval = value
        if self._auto_analysis_enabled:
            self._analysis_timer.start(value * 60 * 1000)
        logger.info(f"分析间隔已更新为 {value} 分钟")

    def _run_auto_analysis(self) -> None:
        """运行自动分析"""
        if not self._auto_analysis_enabled:
            return
        
        logger.info("开始自动分析日志...")
        self._run_analysis(is_auto=True)

    def _run_manual_analysis(self) -> None:
        """运行手动分析"""
        if not self._log_buffer:
            InfoBar.warning("无日志", "没有可分析的日志", parent=self)
            return
        
        logger.info("开始手动分析日志...")
        self._run_analysis(is_auto=False)

    def _run_analysis(self, is_auto: bool = True) -> None:
        """运行分析"""
        if self._is_analyzing:
            InfoBar.warning("分析中", "正在进行分析，请稍后...", parent=self)
            return
        
        self._is_analyzing = True
        
        # 在后台线程运行分析
        thread = threading.Thread(
            target=self._analyze_logs_thread,
            args=(is_auto,),
            daemon=True
        )
        thread.start()

    def _analyze_logs_thread(self, is_auto: bool) -> None:
        """分析日志线程"""
        try:
            logs_text = "\n".join(self._log_buffer[-500:])
            
            if not logs_text:
                self._update_analysis_result("没有日志可分析", is_auto)
                return
            
            # 尝试使用LLM分析
            report = self._call_llm_analysis(logs_text)
            
            if report:
                self._update_analysis_result(report, is_auto)
            else:
                # 使用基础分析
                report = self._basic_analysis(logs_text, is_auto)
                self._update_analysis_result(report, is_auto)
                
        except Exception as e:
            logger.error(f"分析失败: {e}")
            self._update_analysis_result(f"分析失败: {e}", is_auto)
        finally:
            self._is_analyzing = False

    def _call_llm_analysis(self, logs_text: str) -> Optional[str]:
        """调用LLM进行分析"""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app"))
            from llm import get_llm
            
            # 获取系统信息
            sys_info = self._get_system_info_for_prompt()
            
            # 统计日志信息
            stats = self._compute_log_stats()
            
            prompt = f"""请作为资深系统运维专家，分析以下咕咕嘎嘎AI VTuber系统的日志和状态，生成一份全面专业的分析报告。

{sys_info}

日志统计：
- 总日志数：{stats['total']}
- DEBUG: {stats['DEBUG']}
- INFO: {stats['INFO']}
- WARNING: {stats['WARNING']}
- ERROR: {stats['ERROR']}
- CRITICAL: {stats['CRITICAL']}

最近日志：
{logs_text[:5000]}

请生成包含以下内容的详细报告（使用Markdown格式）：

## 📊 系统健康状态评估
- 整体健康评分（0-100）及状态等级
- 各组件状态表格（CPU/内存/磁盘/GPU）

## 📈 日志统计分析
- 日志级别分布表格
- 错误率及趋势分析

## 🔍 异常模式识别
- 重复出现的错误模式
- 时间分布异常
- 关联性分析

## ⚡ 性能瓶颈分析
- 资源使用瓶颈
- 耗时操作识别

## 🐛 潜在问题诊断
- 已识别问题及严重程度
- 潜在风险预警

## 💡 优化建议
- 🔴 立即处理（紧急）
- 🟡 短期优化（1-7天）
- 🟢 长期改进（1-4周）

## 📋 总结与行动计划
- 关键发现
- 优先行动清单
- 下次检查建议

请用中文回复，格式清晰专业。"""

            llm = get_llm()
            if llm and hasattr(llm, 'chat'):
                response = llm.chat(prompt)
                return response
            
            return None
            
        except Exception as e:
            logger.debug(f"LLM分析不可用: {e}")
            return None

    def _compute_log_stats(self) -> Dict[str, int]:
        """计算日志统计"""
        stats = {"DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0, "total": len(self._log_buffer)}
        
        for log in self._log_buffer:
            for level in stats:
                if level != "total" and f"[{level}]" in log:
                    stats[level] += 1
                    break
        
        return stats

    def _basic_analysis(self, logs_text: str, is_auto: bool = True) -> str:
        """基础分析（不使用LLM）"""
        lines = logs_text.split("\n")
        
        # 统计各级别日志
        stats = {"DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0}
        errors = []
        warnings = []
        
        for line in lines:
            for level in stats:
                if f"[{level}]" in line:
                    stats[level] += 1
                    if level == "ERROR":
                        errors.append(line[:120])
                    elif level == "WARNING":
                        warnings.append(line[:120])
                    break
        
        total = len(lines) if lines else 1
        error_count = stats['ERROR'] + stats['CRITICAL']
        error_rate = error_count / total * 100
        health_score = max(0, 100 - error_rate * 10 - stats['WARNING'] * 2)
        
        # 分析类型
        analysis_type = "自动分析" if is_auto else "手动分析"
        
        # 生成报告
        report = f"""📊 系统日志分析报告
{'='*50}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
分析方式: {analysis_type}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 系统健康状态评估
{'-'*50}
• 健康评分: {health_score:.0f}/100 {'🟢 优秀' if health_score >= 80 else '🟡 良好' if health_score >= 60 else '🟠 一般' if health_score >= 40 else '🔴 较差'}
• 总日志数: {total}
• 错误数: {error_count} ({error_rate:.2f}%)
• 警告数: {stats['WARNING']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 日志级别分布
{'-'*50}
• DEBUG:   {stats['DEBUG']:>6} ({stats['DEBUG']/total*100:.1f}%)
• INFO:    {stats['INFO']:>6} ({stats['INFO']/total*100:.1f}%)
• WARNING: {stats['WARNING']:>6} ({stats['WARNING']/total*100:.1f}%)
• ERROR:   {stats['ERROR']:>6} ({stats['ERROR']/total*100:.1f}%)
• CRITICAL:{stats['CRITICAL']:>6} ({stats['CRITICAL']/total*100:.1f}%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 异常模式识别
{'-'*50}
"""
        
        # 错误分析
        if errors:
            report += f"❌ 发现 {len(errors)} 条错误日志:\n"
            for i, err in enumerate(errors[:5], 1):
                report += f"  {i}. {err}\n"
            if len(errors) > 5:
                report += f"  ... 还有 {len(errors)-5} 条错误\n"
        else:
            report += "✅ 未发现错误日志\n"
        
        # 警告分析
        report += f"\n⚠️ 警告分析:\n"
        if warnings:
            report += f"发现 {len(warnings)} 条警告日志:\n"
            for i, warn in enumerate(warnings[:3], 1):
                report += f"  {i}. {warn}\n"
            if len(warnings) > 3:
                report += f"  ... 还有 {len(warnings)-3} 条警告\n"
        else:
            report += "✅ 未发现警告日志\n"
        
        # 优化建议
        report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 优化建议
{'-'*50}
"""
        
        suggestions = []
        if stats['CRITICAL'] > 0:
            suggestions.append("🔴 [紧急] 存在CRITICAL日志，系统可能存在严重问题，需要立即处理")
        if stats['ERROR'] > 0:
            suggestions.append("🔴 [紧急] 存在ERROR日志，建议立即检查并修复")
        if stats['WARNING'] > 10:
            suggestions.append("🟡 [短期] WARNING日志较多，建议排查潜在问题")
        if error_rate > 5:
            suggestions.append("🟡 [短期] 错误率较高，建议深入分析根本原因")
        if stats['WARNING'] > 0 and stats['WARNING'] <= 10:
            suggestions.append("🟢 [监控] 存在少量WARNING，建议持续关注")
        
        if not suggestions:
            suggestions.append("🟢 系统运行正常，无需特别处理")
        
        report += "\n".join(f"  {s}" for s in suggestions)
        
        return report

    def _update_analysis_result(self, report: str, is_auto: bool) -> None:
        """更新分析结果"""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        
        report_data = {
            "timestamp": now.isoformat(),
            "date": today,
            "time": now.strftime("%H:%M:%S"),
            "type": "auto" if is_auto else "manual",
            "content": report
        }
        
        # 保存报告
        if is_auto:
            key = f"auto_{today}"
        else:
            key = f"manual_{now.strftime('%Y%m%d_%H%M%S')}"
        
        self._analysis_reports[key] = report_data
        self._current_report = report_data
        
        # 保存到文件
        self._save_report_to_file(report_data, key)
        
        # 更新UI
        QTimer.singleShot(0, lambda: self._display_report(report))
        QTimer.singleShot(0, self._update_report_tree)

    def _display_report(self, report: str) -> None:
        """显示报告"""
        self.analysis_display.setPlainText(report)
        InfoBar.success("分析完成", "日志分析报告已生成", parent=self)

    def _save_report_to_file(self, report_data: Dict[str, Any], key: str) -> None:
        """保存报告到文件"""
        try:
            # 保存JSON
            json_file = REPORTS_DIR / f"{key}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            # 保存文本
            txt_file = REPORTS_DIR / f"{key}.txt"
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(report_data['content'])
            
            logger.info(f"报告已保存: {json_file}")
        except Exception as e:
            logger.error(f"保存报告失败: {e}")

    def _load_history_reports(self) -> None:
        """加载历史报告"""
        try:
            if not REPORTS_DIR.exists():
                return
            
            self._analysis_reports.clear()
            
            # 获取所有JSON报告文件
            report_files = sorted(REPORTS_DIR.glob("*.json"), reverse=True)
            
            for report_file in report_files[:50]:  # 最多加载50个
                try:
                    with open(report_file, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)
                    
                    key = report_file.stem
                    self._analysis_reports[key] = report_data
                    
                except Exception:
                    continue
            
            self._update_report_tree()
            logger.info(f"加载了 {len(self._analysis_reports)} 个历史报告")
            
        except Exception as e:
            logger.error(f"加载历史报告失败: {e}")

    def _cleanup_old_reports(self) -> None:
        """清理旧报告（保留最近30天）"""
        try:
            if not REPORTS_DIR.exists():
                return
            
            cutoff_date = datetime.now() - timedelta(days=MAX_REPORT_DAYS)
            cutoff_str = cutoff_date.strftime("%Y-%m-%d")
            
            deleted_count = 0
            for report_file in REPORTS_DIR.glob("*.json"):
                try:
                    # 从文件名提取日期
                    stem = report_file.stem
                    if stem.startswith("auto_"):
                        date_str = stem.replace("auto_", "")
                    elif stem.startswith("manual_"):
                        # manual_20260609_090000
                        date_str = stem[7:15]  # 提取 YYYYMMDD
                        date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    else:
                        continue
                    
                    if date_str < cutoff_str:
                        # 删除旧报告
                        report_file.unlink(missing_ok=True)
                        txt_file = report_file.with_suffix('.txt')
                        txt_file.unlink(missing_ok=True)
                        deleted_count += 1
                        
                except Exception:
                    continue
            
            if deleted_count > 0:
                logger.info(f"清理了 {deleted_count} 个旧报告")
                
        except Exception as e:
            logger.error(f"清理旧报告失败: {e}")

    def _update_report_tree(self) -> None:
        """更新报告树形列表"""
        self.report_tree.clear()
        
        # 按日期分组
        date_groups: Dict[str, List[Dict]] = {}
        
        for key, report in self._analysis_reports.items():
            date_str = report.get('date', 'unknown')
            if date_str not in date_groups:
                date_groups[date_str] = []
            date_groups[date_str].append({**report, 'key': key})
        
        # 按日期倒序排列
        for date_str in sorted(date_groups.keys(), reverse=True):
            date_item = QTreeWidgetItem(self.report_tree)
            date_item.setText(0, f"📅 {date_str}")
            date_item.setExpanded(True)
            
            # 按时间倒序排列
            reports = sorted(date_groups[date_str], key=lambda x: x.get('time', ''), reverse=True)
            
            for report in reports:
                report_item = QTreeWidgetItem(date_item)
                report_type = report.get('type', 'unknown')
                time_str = report.get('time', '')
                
                if report_type == 'auto':
                    icon = "🔄"
                    type_text = "自动"
                else:
                    icon = "📝"
                    type_text = "手动"
                
                report_item.setText(0, f"{icon} {type_text}报告")
                report_item.setText(1, time_str)
                report_item.setText(2, type_text)
                report_item.setData(0, Qt.ItemDataRole.UserRole, report.get('key'))

    def _on_report_selected(self, current, previous) -> None:
        """报告选中事件"""
        if not current:
            return
        
        key = current.data(0, Qt.ItemDataRole.UserRole)
        if key and key in self._analysis_reports:
            report = self._analysis_reports[key]
            self.analysis_display.setPlainText(report.get('content', ''))
            self._current_report = report

    def _export_report(self) -> None:
        """导出当前报告"""
        if not self._current_report:
            InfoBar.warning("无报告", "没有可导出的报告", parent=self)
            return
        
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出报告",
                f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "文本文件 (*.txt);;所有文件 (*)"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self._current_report.get('content', ''))
                InfoBar.success("导出成功", f"报告已导出到: {filename}", parent=self)
        except Exception as e:
            InfoBar.error("导出失败", f"错误: {e}", parent=self)

    def _delete_report(self) -> None:
        """删除选中的报告"""
        current = self.report_tree.currentItem()
        if not current:
            InfoBar.warning("未选择", "请先选择要删除的报告", parent=self)
            return
        
        key = current.data(0, Qt.ItemDataRole.UserRole)
        if not key:
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除这个报告吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # 从内存中删除
            if key in self._analysis_reports:
                del self._analysis_reports[key]
            
            # 从文件中删除
            json_file = REPORTS_DIR / f"{key}.json"
            txt_file = REPORTS_DIR / f"{key}.txt"
            
            json_file.unlink(missing_ok=True)
            txt_file.unlink(missing_ok=True)
            
            # 更新UI
            self._update_report_tree()
            self.analysis_display.clear()
            self._current_report = None
            
            InfoBar.success("删除成功", "报告已删除", parent=self)
        except Exception as e:
            InfoBar.error("删除失败", f"错误: {e}", parent=self)


class LogHandler(logging.Handler):
    """自定义日志处理器，将日志发送到 LogPage"""
    
    def __init__(self, log_page: LogPage) -> None:
        """初始化日志处理器"""
        super().__init__()
        self.log_page = log_page
    
    def emit(self, record) -> None:
        """发送日志记录"""
        try:
            msg = self.format(record)
            self.log_page.add_log(msg, record.levelname)
        except Exception:
            self.handleError(record)
