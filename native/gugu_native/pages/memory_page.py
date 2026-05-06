"""
记忆页面 — 四层记忆系统可视化

对接 app/memory/ MemorySystem，提供：
- 工作记忆（短期对话窗口）
- 情景记忆（摘要压缩后的对话）
- 语义记忆（向量库检索）
- 事实记忆（用户偏好/个人信息）
- 记忆搜索/删除/编辑/标记重要
- 记忆重整/导出
- 实时统计面板
"""

import os
import time
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QComboBox, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QHeaderView,
    QInputDialog, QMessageBox, QSplitter, QMenu,
    QProgressBar, QGroupBox
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread
from PySide6.QtGui import QFont, QColor, QAction, QTextCursor

from qfluentwidgets import (
    PushButton, LineEdit, ComboBox, TitleLabel, SubtitleLabel,
    CaptionLabel, CardWidget, FluentIcon, ToolButton,
    TogglePushButton, InfoBar, InfoBarPosition, ProgressRing,
    TextEdit, SearchLineEdit
)

# 项目根目录
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class MemorySearchWorker(QThread):
    """记忆搜索线程"""
    results_ready = Signal(list)
    error = Signal(str)

    def __init__(self, memory_system, query, top_k=10):
        super().__init__()
        self.memory_system = memory_system
        self.query = query
        self.top_k = top_k

    def run(self):
        try:
            results = self.memory_system.search(self.query, top_k=self.top_k)
            self.results_ready.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class ConsolidateWorker(QThread):
    """记忆重整线程"""
    done = Signal(dict)
    error = Signal(str)

    def __init__(self, memory_system):
        super().__init__()
        self.memory_system = memory_system

    def run(self):
        try:
            result = self.memory_system.consolidate()
            self.done.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class MemoryItemWidget(QTreeWidgetItem):
    """记忆条目 TreeWidget Item"""

    def __init__(self, parent, data: dict, layer: str, index: int):
        # 列: [重要性, 角色, 内容, 标签, 时间]
        importance = data.get("importance", 0)
        role = data.get("role", "")
        content = data.get("text", data.get("content", ""))
        tags = data.get("tags", [])
        timestamp = data.get("timestamp", 0)

        # 格式化时间
        if timestamp:
            try:
                dt = datetime.fromtimestamp(timestamp)
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                time_str = str(timestamp)[:16]
        else:
            time_str = ""

        # 重要性星标
        stars = "★" * importance + "☆" * (5 - importance) if importance > 0 else "—"

        # 标签
        tag_str = ", ".join(tags[:3]) if tags else ""

        # 截断内容
        display_content = content[:100] + "..." if len(content) > 100 else content

        super().__init__(parent, [stars, role, display_content, tag_str, time_str])

        self.layer = layer
        self.index = index
        self.full_content = content
        self.importance = importance

        # 根据重要性设置颜色
        if importance >= 4:
            self.setForeground(0, QColor("#ff6b6b"))  # 关键记忆 - 红
            self.setForeground(2, QColor("#ffaaaa"))
        elif importance >= 3:
            self.setForeground(0, QColor("#ffd93d"))  # 重要记忆 - 黄
            self.setForeground(2, QColor("#ffe0a0"))
        elif importance >= 1:
            self.setForeground(0, QColor("#6bcb77"))  # 一般 - 绿
            self.setForeground(2, QColor("#b0b0b0"))
        else:
            self.setForeground(2, QColor("#808080"))  # 闲聊 - 灰

        # 摘要标记
        if data.get("is_summary"):
            self.setForeground(2, QColor("#a0c4ff"))
            self.setText(1, f"[摘要] {role}")


class MemoryPage(QWidget):
    """记忆页面 — 四层记忆系统可视化"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("memoryPage")
        self._backend = None
        self._search_worker = None
        self._consolidate_worker = None
        self._init_ui()

        # 定时刷新统计
        self._stats_timer = QTimer(self)
        self._stats_timer.setInterval(10000)  # 10秒刷新
        self._stats_timer.timeout.connect(self._refresh_stats)
        self._stats_timer.start()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(8)

        # === 顶部: 标题 + 搜索 + 操作 ===
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)

        title = TitleLabel("记忆系统")
        top_layout.addWidget(title)

        # 搜索框
        self.search_field = SearchLineEdit()
        self.search_field.setPlaceholderText("搜索记忆...")
        self.search_field.setFixedWidth(300)
        self.search_field.searchSignal.connect(self._do_search)
        top_layout.addWidget(self.search_field)

        top_layout.addStretch()

        # 操作按钮
        self.refresh_btn = PushButton("刷新")
        self.refresh_btn.setIcon(FluentIcon.SYNC)
        self.refresh_btn.clicked.connect(self._refresh_all)
        top_layout.addWidget(self.refresh_btn)

        self.consolidate_btn = PushButton("重整记忆")
        self.consolidate_btn.setIcon(FluentIcon.UPDATE)
        self.consolidate_btn.clicked.connect(self._consolidate)
        top_layout.addWidget(self.consolidate_btn)

        self.export_btn = PushButton("导出")
        self.export_btn.setIcon(FluentIcon.SAVE)
        self.export_btn.clicked.connect(self._export_memory)
        top_layout.addWidget(self.export_btn)

        main_layout.addLayout(top_layout)

        # === 统计面板 ===
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(8)

        self.stat_working, self._stat_working_val = self._create_stat_card("工作记忆", "0", "#4dabf7")
        stats_layout.addWidget(self.stat_working)

        self.stat_episodic, self._stat_episodic_val = self._create_stat_card("情景记忆", "0", "#69db7c")
        stats_layout.addWidget(self.stat_episodic)

        self.stat_semantic, self._stat_semantic_val = self._create_stat_card("语义记忆", "0", "#da77f2")
        stats_layout.addWidget(self.stat_semantic)

        self.stat_facts, self._stat_facts_val = self._create_stat_card("事实记忆", "0", "#ffd43b")
        stats_layout.addWidget(self.stat_facts)

        self.stat_forgotten, self._stat_forgotten_val = self._create_stat_card("已遗忘", "0", "#868e96")
        stats_layout.addWidget(self.stat_forgotten)

        main_layout.addLayout(stats_layout)

        # === 主内容区: 分割面板 ===
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧: 记忆树
        self._init_memory_tree(splitter)

        # 右侧: 详情 + 搜索结果
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Tab: 详情 / 搜索结果
        self.detail_tabs = QTabWidget()

        # 详情 Tab
        self.detail_text = TextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setFont(QFont("Microsoft YaHei UI", 10))
        self.detail_text.setPlaceholderText("选择左侧记忆条目查看详情...")
        self.detail_tabs.addTab(self.detail_text, "详情")

        # 搜索结果 Tab
        self.search_results_tree = QTreeWidget()
        self.search_results_tree.setHeaderLabels(["重要性", "层级", "内容", "分数"])
        self.search_results_tree.header().setStretchLastSection(True)
        self.search_results_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.search_results_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.search_results_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.search_results_tree.setColumnWidth(0, 80)
        self.search_results_tree.setColumnWidth(1, 60)
        self.search_results_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.search_results_tree.customContextMenuRequested.connect(self._show_search_context_menu)
        self.search_results_tree.itemClicked.connect(self._on_search_item_clicked)
        self.detail_tabs.addTab(self.search_results_tree, "搜索结果")

        right_layout.addWidget(self.detail_tabs, stretch=1)

        # 详情操作按钮
        detail_btn_layout = QHBoxLayout()

        self.edit_btn = PushButton("编辑")
        self.edit_btn.setIcon(FluentIcon.EDIT)
        self.edit_btn.clicked.connect(self._edit_memory)
        self.edit_btn.setEnabled(False)
        detail_btn_layout.addWidget(self.edit_btn)

        self.delete_btn = PushButton("删除")
        self.delete_btn.setIcon(FluentIcon.DELETE)
        self.delete_btn.clicked.connect(self._delete_memory)
        self.delete_btn.setEnabled(False)
        detail_btn_layout.addWidget(self.delete_btn)

        self.important_btn = PushButton("标记重要")
        self.important_btn.setIcon(FluentIcon.PIN)
        self.important_btn.clicked.connect(self._mark_important)
        self.important_btn.setEnabled(False)
        detail_btn_layout.addWidget(self.important_btn)

        detail_btn_layout.addStretch()
        right_layout.addLayout(detail_btn_layout)

        splitter.addWidget(right_panel)
        splitter.setSizes([400, 500])

        main_layout.addWidget(splitter, stretch=1)

        # 延迟加载数据
        QTimer.singleShot(800, self._refresh_all)

    def _create_stat_card(self, label: str, value: str, color: str) -> CardWidget:
        """创建统计卡片 — 返回 (card, value_label) 元组"""
        from gugu_native.theme import get_colors
        c = get_colors()
        card = CardWidget()
        card.setFixedHeight(72)
        card.setMinimumWidth(140)
        card.setStyleSheet(f"""
            CardWidget {{
                background-color: {c.card_bg};
                border: 1px solid {c.card_border};
                border-radius: 12px;
                border-top: 3px solid {color};
            }}
            CardWidget:hover {{
                background-color: {c.card_bg_hover};
                border: 1px solid {c.card_border_hover};
                border-top: 3px solid {color};
            }}
        """)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(10)

        # 左侧: 图标圆点
        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
        layout.addWidget(dot)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = CaptionLabel(label)
        name_label.setStyleSheet(f"color: {c.text_muted}; font-size: 12px;")
        info_layout.addWidget(name_label)

        val_label = QLabel(value)
        val_label.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")
        info_layout.addWidget(val_label)

        layout.addLayout(info_layout)

        return card, val_label

    def _init_memory_tree(self, parent):
        """初始化记忆树"""
        self.memory_tree = QTreeWidget()
        self.memory_tree.setHeaderLabels(["重要性", "角色", "内容", "标签", "时间"])
        self.memory_tree.header().setStretchLastSection(True)
        self.memory_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.memory_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.memory_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.memory_tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.memory_tree.setColumnWidth(0, 80)
        self.memory_tree.setColumnWidth(1, 60)
        self.memory_tree.setColumnWidth(3, 100)

        # 四层记忆分类节点
        self.working_root = QTreeWidgetItem(self.memory_tree, ["工作记忆", "", "", "", ""])
        self.working_root.setExpanded(True)
        self.working_root.setForeground(0, QColor("#4dabf7"))

        self.episodic_root = QTreeWidgetItem(self.memory_tree, ["情景记忆", "", "", "", ""])
        self.episodic_root.setExpanded(True)
        self.episodic_root.setForeground(0, QColor("#69db7c"))

        self.semantic_root = QTreeWidgetItem(self.memory_tree, ["语义记忆", "", "", "", ""])
        self.semantic_root.setExpanded(False)
        self.semantic_root.setForeground(0, QColor("#da77f2"))

        self.facts_root = QTreeWidgetItem(self.memory_tree, ["事实记忆", "", "", "", ""])
        self.facts_root.setExpanded(True)
        self.facts_root.setForeground(0, QColor("#ffd43b"))

        # 右键菜单
        self.memory_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.memory_tree.customContextMenuRequested.connect(self._show_context_menu)

        # 点击事件
        self.memory_tree.itemClicked.connect(self._on_item_clicked)

        parent.addWidget(self.memory_tree)

    @property
    def backend(self):
        """获取后端实例（延迟初始化）"""
        if self._backend is None:
            main_window = self.window()
            if hasattr(main_window, 'backend'):
                self._backend = main_window.backend
        return self._backend

    @property
    def memory_system(self):
        """获取记忆系统实例"""
        if self.backend and hasattr(self.backend, 'memory'):
            return self.backend.memory
        return None

    def on_backend_ready(self):
        """后端就绪回调 — 刷新记忆数据"""
        self._refresh_all()

    # ========== 数据加载 ==========

    def _refresh_all(self):
        """刷新全部记忆数据"""
        mem = self.memory_system
        if not mem:
            return

        self._refresh_stats()
        self._refresh_working()
        self._refresh_episodic()
        self._refresh_semantic()
        self._refresh_facts()

    def _refresh_stats(self):
        """刷新统计面板"""
        mem = self.memory_system
        if not mem:
            return

        try:
            working_count = len(mem.working_memory)
            episodic_count = len(mem.episodic_memory)
            semantic_stats = mem.vector_store.get_stats()
            semantic_count = semantic_stats.get("total_docs", 0)
            facts_count = len(mem.facts)
            forgotten = mem.forgotten_count

            # 更新统计卡片（直接引用，不再用 findChild）
            self._stat_working_val.setText(str(working_count))
            self._stat_episodic_val.setText(str(episodic_count))
            self._stat_semantic_val.setText(str(semantic_count))
            self._stat_facts_val.setText(str(facts_count))
            self._stat_forgotten_val.setText(str(forgotten))
        except Exception as e:
            print(f"[MemoryPage] 刷新统计失败: {e}")

    def _refresh_working(self):
        """刷新工作记忆"""
        self.working_root.takeChildren()
        mem = self.memory_system
        if not mem:
            return

        for i, item in enumerate(mem.working_memory):
            data = {
                "importance": item.importance,
                "role": item.role,
                "text": item.content,
                "tags": item.tags or [],
                "timestamp": item.timestamp,
                "is_summary": item.is_summary,
            }
            widget_item = MemoryItemWidget(self.working_root, data, "working", i)
            # 显示访问计数
            if item.access_count > 1:
                widget_item.setText(3, f"访问:{item.access_count}")

        self.working_root.setText(0, f"⚡ 工作记忆 ({len(mem.working_memory)})")

    def _refresh_episodic(self):
        """刷新情景记忆"""
        self.episodic_root.takeChildren()
        mem = self.memory_system
        if not mem:
            return

        for i, item in enumerate(mem.episodic_memory):
            if item.is_forgotten:
                continue
            data = {
                "importance": item.importance,
                "role": item.role,
                "text": item.content,
                "tags": item.tags or [],
                "timestamp": item.timestamp,
                "is_summary": item.is_summary,
            }
            widget_item = MemoryItemWidget(self.episodic_root, data, "episodic", i)
            # 显示保留分数
            retention = item.get_retention_score()
            retention_text = f"保留:{retention:.2f}"
            if item.tags:
                retention_text = f"{', '.join(item.tags[:2])} | {retention_text}"
            widget_item.setText(3, retention_text)

        active_count = sum(1 for m in mem.episodic_memory if not m.is_forgotten)
        self.episodic_root.setText(0, f"📖 情景记忆 ({active_count})")

    def _refresh_semantic(self):
        """刷新语义记忆（向量库）"""
        self.semantic_root.takeChildren()
        mem = self.memory_system
        if not mem:
            return

        vs = mem.vector_store
        count = 0
        for doc_id, text in vs.texts.items():
            metadata = vs.metadatas.get(doc_id, {})
            data = {
                "importance": metadata.get("importance", 0),
                "role": metadata.get("role", ""),
                "text": text,
                "tags": metadata.get("tags", []),
                "timestamp": metadata.get("timestamp", 0),
                "is_summary": metadata.get("is_summary", False),
            }
            item = MemoryItemWidget(self.semantic_root, data, "semantic", count)
            item.index = doc_id  # 向量库用 doc_id 作索引
            count += 1

        self.semantic_root.setText(0, f"🧠 语义记忆 ({count})")

    def _refresh_facts(self):
        """刷新事实记忆"""
        self.facts_root.takeChildren()
        mem = self.memory_system
        if not mem:
            return

        for i, fact in enumerate(mem.facts):
            source_map = {
                "user_preference": "偏好",
                "user_info": "信息",
                "key_fact": "事实",
            }
            source_text = source_map.get(fact.source, fact.source)
            data = {
                "importance": 4,  # 事实默认高分
                "role": source_text,
                "text": fact.content,
                "tags": fact.tags or [],
                "timestamp": fact.timestamp,
            }
            item = MemoryItemWidget(self.facts_root, data, "fact", i)
            # 显示置信度
            item.setText(3, f"置信:{fact.confidence:.0%}")

        self.facts_root.setText(0, f"📌 事实记忆 ({len(mem.facts)})")

    # ========== 交互 ==========

    def _on_item_clicked(self, item, column):
        """点击记忆条目"""
        if not isinstance(item, MemoryItemWidget):
            return

        # 显示详情
        from gugu_native.theme import get_colors
        c = get_colors()
        self.detail_text.clear()
        details = []
        details.append(f"<h3 style='color: {c.text_primary};'>记忆详情</h3>")
        details.append(f"<p style='color: {c.text_secondary};'><b>层级:</b> {item.layer}</p>")
        details.append(f"<p style='color: {c.text_secondary};'><b>重要性:</b> {'★' * item.importance}{'☆' * (5 - item.importance)} ({item.importance}/5)</p>")
        details.append(f"<p style='color: {c.text_secondary};'><b>内容:</b></p>")
        details.append(f"<div style='background-color: {c.input_bg}; border: 1px solid {c.card_border}; "
                       f"padding: 14px; border-radius: 10px; color: {c.text_primary}; "
                       f"line-height: 1.6;'>{item.full_content}</div>")

        self.detail_text.setHtml("\n".join(details))

        # 启用操作按钮
        self.edit_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.important_btn.setEnabled(item.layer in ("working", "episodic"))

        # 保存当前选中
        self._selected_item = item

    def _show_context_menu(self, pos):
        """右键菜单"""
        item = self.memory_tree.itemAt(pos)
        if not isinstance(item, MemoryItemWidget):
            return

        menu = QMenu(self)

        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(self._edit_memory)
        menu.addAction(edit_action)

        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self._delete_memory)
        menu.addAction(delete_action)

        if item.layer in ("working", "episodic"):
            menu.addSeparator()
            for imp in range(6):
                imp_action = QAction(f"标记重要性: {'★' * imp}", self)
                imp_action.triggered.connect(lambda checked, i=imp: self._set_importance(i))
                menu.addAction(imp_action)

        self._selected_item = item
        menu.exec(self.memory_tree.viewport().mapToGlobal(pos))

    def _show_search_context_menu(self, pos):
        """搜索结果右键菜单"""
        item = self.search_results_tree.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)

        view_action = QAction("查看详情", self)
        view_action.triggered.connect(lambda: self._on_search_item_clicked(item, 0))
        menu.addAction(view_action)

        menu.exec(self.search_results_tree.viewport().mapToGlobal(pos))

    def _on_search_item_clicked(self, item, column):
        """搜索结果点击"""
        from gugu_native.theme import get_colors
        c = get_colors()
        text = item.text(2)
        self.detail_text.clear()
        self.detail_text.setHtml(
            f"<h3>搜索结果</h3>"
            f"<p><b>层级:</b> {item.text(1)}</p>"
            f"<p><b>重要性:</b> {item.text(0)}</p>"
            f"<p><b>内容:</b></p>"
            f"<p style='background-color: {c.input_bg}; border: 1px solid {c.card_border}; padding: 12px; border-radius: 8px;'>{text}</p>"
        )
        self.detail_tabs.setCurrentIndex(1)

    # ========== 操作 ==========

    def _do_search(self, query: str):
        """执行记忆搜索"""
        if not query.strip():
            return
        mem = self.memory_system
        if not mem:
            self._show_info("后端未初始化", "请先在设置页面配置后端")
            return

        self._search_worker = MemorySearchWorker(mem, query, top_k=15)
        self._search_worker.results_ready.connect(self._on_search_results)
        self._search_worker.error.connect(lambda e: self._show_info("搜索失败", e))
        self._search_worker.start()

    @Slot(list)
    def _on_search_results(self, results: list):
        """搜索结果返回"""
        self.search_results_tree.clear()
        for r in results:
            layer = r.get("layer", "")
            layer_map = {"working": "工作", "episodic": "情景", "semantic": "语义", "fact": "事实"}
            imp = r.get("importance", 0)
            stars = "★" * imp + "☆" * (5 - imp) if imp > 0 else "—"
            text = r.get("text", "")[:120]
            score = r.get("score", 0)

            item = QTreeWidgetItem(self.search_results_tree,
                                   [stars, layer_map.get(layer, layer), text, f"{score:.2f}"])
            if score > 0.8:
                item.setForeground(2, QColor("#ffaaaa"))
            elif score > 0.5:
                item.setForeground(2, QColor("#ffe0a0"))
            else:
                item.setForeground(2, QColor("#b0b0b0"))

        self.detail_tabs.setCurrentIndex(1)

    def _edit_memory(self):
        """编辑记忆"""
        item = getattr(self, '_selected_item', None)
        if not item or not isinstance(item, MemoryItemWidget):
            return

        new_text, ok = QInputDialog.getText(
            self, "编辑记忆", "修改内容:",
            text=item.full_content
        )
        if ok and new_text:
            mem = self.memory_system
            if not mem:
                return
            success = mem.edit_memory(item.index, new_text, layer=item.layer)
            if success:
                self._show_info("成功", "记忆已更新")
                self._refresh_all()
            else:
                self._show_info("失败", "更新记忆失败")

    def _delete_memory(self):
        """删除记忆"""
        item = getattr(self, '_selected_item', None)
        if not item or not isinstance(item, MemoryItemWidget):
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除这条记忆吗？\n\n{item.full_content[:100]}...",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            mem = self.memory_system
            if not mem:
                return
            success = mem.delete_memory(item.index, layer=item.layer)
            if success:
                self._show_info("成功", "记忆已删除")
                self._refresh_all()
            else:
                self._show_info("失败", "删除记忆失败")

    def _mark_important(self):
        """标记重要"""
        item = getattr(self, '_selected_item', None)
        if not item or not isinstance(item, MemoryItemWidget):
            return

        importance, ok = QInputDialog.getInt(
            self, "标记重要性", "设置重要性 (0-5):", value=item.importance, min=0, max=5
        )
        if ok:
            self._set_importance(importance)

    def _set_importance(self, importance: int):
        """设置重要性"""
        item = getattr(self, '_selected_item', None)
        if not item or not isinstance(item, MemoryItemWidget):
            return

        mem = self.memory_system
        if not mem:
            return

        success = mem.set_importance(item.index, importance, layer=item.layer)
        if success:
            self._show_info("成功", f"已标记为重要性 {importance}")
            self._refresh_all()

    def _consolidate(self):
        """记忆重整"""
        mem = self.memory_system
        if not mem:
            self._show_info("后端未初始化", "请先配置后端")
            return

        self.consolidate_btn.setEnabled(False)
        self.consolidate_btn.setText("重整中...")

        self._consolidate_worker = ConsolidateWorker(mem)
        self._consolidate_worker.done.connect(self._on_consolidate_done)
        self._consolidate_worker.error.connect(lambda e: self._on_consolidate_done({"error": e}))
        self._consolidate_worker.start()

    @Slot(dict)
    def _on_consolidate_done(self, result: dict):
        """重整完成"""
        self.consolidate_btn.setEnabled(True)
        self.consolidate_btn.setText("重整记忆")

        if "error" in result:
            self._show_info("重整失败", result["error"])
        else:
            msg = (
                f"合并: {result.get('merged', 0)} 条\n"
                f"提升: {result.get('promoted', 0)} 条\n"
                f"清理: {result.get('cleaned', 0)} 条"
            )
            self._show_info("重整完成", msg)
            self._refresh_all()

    def _export_memory(self):
        """导出记忆"""
        mem = self.memory_system
        if not mem:
            return

        try:
            content = mem.file_storage.export_all()

            # 选择保存路径
            from PySide6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出记忆", "memory_export.md", "Markdown (*.md);;All Files (*)"
            )
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self._show_info("导出成功", f"记忆已导出到: {file_path}")
        except Exception as e:
            self._show_info("导出失败", str(e))

    def _show_info(self, title: str, content: str):
        """显示信息栏"""
        InfoBar.info(
            title=title,
            content=content,
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000,
        )

    # ========== 主题刷新（v1.9.80）==========

    def refresh_theme(self):
        """主题切换时刷新统计卡片等硬编码样式"""
        # 重建统计卡片样式
        stat_colors = {
            "stat_working": ("工作记忆", "#4dabf7"),
            "stat_episodic": ("情景记忆", "#69db7c"),
            "stat_semantic": ("语义记忆", "#da77f2"),
            "stat_facts": ("事实记忆", "#ffd43b"),
            "stat_forgotten": ("已遗忘", "#868e96"),
        }
        from gugu_native.theme import get_colors
        c = get_colors()

        for attr, (label, color) in stat_colors.items():
            card_widget = getattr(self, attr, None)
            if card_widget:
                card_widget.setStyleSheet(f"""
                    CardWidget {{
                        background-color: {c.card_bg};
                        border: 1px solid {c.card_border};
                        border-radius: 12px;
                        border-top: 3px solid {color};
                    }}
                    CardWidget:hover {{
                        background-color: {c.card_bg_hover};
                        border: 1px solid {c.card_border_hover};
                        border-top: 3px solid {color};
                    }}
                """)

        # 刷新记忆树根节点颜色
        self.working_root.setForeground(0, QColor("#4dabf7"))
        self.episodic_root.setForeground(0, QColor("#69db7c"))
        self.semantic_root.setForeground(0, QColor("#da77f2"))
        self.facts_root.setForeground(0, QColor("#ffd43b"))
