"""
咕咕嘎嘎 AI-VTuber — 多会话管理器

功能:
- 多会话（多标签）支持
- 会话创建、切换、删除、重命名
- 会话列表侧边栏
- 会话数据持久化（JSON 文件）
- 自动标题生成（首条消息摘要）

存储格式:
- 每个会话一个 JSON 文件
- 存储在 app/state/sessions/ 目录下
"""

import os
import json
import time
from datetime import datetime
from typing import Optional, List, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QFrame, QMenu, QInputDialog
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QIcon, QAction

from qfluentwidgets import (
    PushButton, ToolButton, FluentIcon, LineEdit,
    CaptionLabel, MessageBox
)

# 项目根目录
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class ChatSession:
    """单个聊天会话数据"""

    def __init__(self, session_id: str = "", title: str = "新对话",
                 messages: list = None, created_at: str = "", updated_at: str = ""):
        self.session_id = session_id or f"session_{int(time.time() * 1000)}"
        self.title = title
        self.messages = messages or []
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "messages": self.messages,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ChatSession':
        return cls(
            session_id=data.get("session_id", ""),
            title=data.get("title", "新对话"),
            messages=data.get("messages", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    def update_timestamp(self):
        self.updated_at = datetime.now().isoformat()

    def auto_title(self):
        """根据第一条用户消息自动生成标题"""
        for msg in self.messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                self.title = content[:30] + ("..." if len(content) > 30 else "")
                return
        self.title = "新对话"


class SessionManager(QWidget):
    """会话管理器 — 侧边栏

    信号:
    - sessionSwitched(session_id) — 切换会话
    - sessionCreated(session_id) — 创建新会话
    - sessionDeleted(session_id) — 删除会话
    """

    sessionSwitched = Signal(str)
    sessionCreated = Signal(str)
    sessionDeleted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sessionManager")
        self._sessions: Dict[str, ChatSession] = {}
        self._current_session_id: Optional[str] = None
        self._state_dir = os.path.join(PROJECT_DIR, "app", "state", "sessions")

        self.setMinimumWidth(160)
        self.setMaximumWidth(220)
        self._init_ui()
        self._load_sessions()

    def _init_ui(self):
        """初始化 UI"""
        from gugu_native.theme import get_colors
        c = get_colors()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(6)

        # 标题栏
        header_layout = QHBoxLayout()
        header_layout.setSpacing(4)

        title_label = CaptionLabel("对话列表")
        title_label.setStyleSheet(f"color: {c.text_secondary}; font-weight: 600;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # 新建对话按钮
        new_btn = ToolButton(FluentIcon.ADD)
        new_btn.setFixedSize(28, 28)
        new_btn.setToolTip("新建对话")
        new_btn.clicked.connect(self._on_new_session)
        header_layout.addWidget(new_btn)

        layout.addLayout(header_layout)

        # 搜索框
        self._search_field = LineEdit()
        self._search_field.setPlaceholderText("搜索对话...")
        self._search_field.setClearButtonEnabled(True)
        self._search_field.textChanged.connect(self._on_search)
        self._search_field.setStyleSheet(f"""
            LineEdit {{
                background-color: {c.input_bg};
                border: 1px solid {c.input_border};
                border-radius: 8px;
                padding: 5px 10px;
                color: {c.text_primary};
                font-size: 12px;
            }}
        """)
        layout.addWidget(self._search_field)

        # 会话列表
        self._session_list = QListWidget()
        self._session_list.setObjectName("sessionList")
        self._session_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._session_list.customContextMenuRequested.connect(self._on_context_menu)
        self._session_list.itemClicked.connect(self._on_item_clicked)
        self._session_list.setStyleSheet(f"""
            QListWidget#sessionList {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QListWidget#sessionList::item {{
                border-radius: 8px;
                padding: 8px 10px;
                margin: 2px 0;
                color: {c.text_primary};
            }}
            QListWidget#sessionList::item:selected {{
                background-color: {c.accent};
                color: white;
            }}
            QListWidget#sessionList::item:hover:!selected {{
                background-color: {c.card_bg_hover};
            }}
        """)
        layout.addWidget(self._session_list, stretch=1)

        # 整体样式
        self.setStyleSheet(f"""
            QWidget#sessionManager {{
                background-color: {c.sidebar_bg};
                border-right: 1px solid {c.card_border};
            }}
        """)

    # ===== 会话操作 =====

    def _on_new_session(self):
        """新建对话"""
        session = ChatSession()
        self._sessions[session.session_id] = session
        self._add_session_item(session)
        self._save_session(session)
        self._current_session_id = session.session_id
        self._select_session(session.session_id)
        self.sessionCreated.emit(session.session_id)
        self.sessionSwitched.emit(session.session_id)

    def _on_item_clicked(self, item: QListWidgetItem):
        """点击会话项"""
        session_id = item.data(Qt.ItemDataRole.UserRole)
        if session_id != self._current_session_id:
            self._current_session_id = session_id
            self.sessionSwitched.emit(session_id)

    def _on_context_menu(self, pos):
        """右键菜单"""
        item = self._session_list.itemAt(pos)
        if not item:
            return

        session_id = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)

        rename_action = menu.addAction("重命名")
        delete_action = menu.addAction("删除")

        from gugu_native.theme import get_colors
        c = get_colors()
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {c.card_bg};
                color: {c.text_primary};
                border: 1px solid {c.card_border};
                border-radius: 10px;
                padding: 6px;
            }}
            QMenu::item {{
                border-radius: 6px;
                padding: 6px 24px;
                margin: 1px 4px;
            }}
            QMenu::item:selected {{
                background-color: {c.accent};
                color: white;
            }}
        """)

        action = menu.exec(self._session_list.mapToGlobal(pos))

        if action == rename_action:
            self._rename_session(session_id)
        elif action == delete_action:
            self._delete_session(session_id)

    def _rename_session(self, session_id: str):
        """重命名会话"""
        session = self._sessions.get(session_id)
        if not session:
            return

        new_title, ok = QInputDialog.getText(
            self, "重命名对话", "请输入新名称:", text=session.title
        )
        if ok and new_title.strip():
            session.title = new_title.strip()
            session.update_timestamp()
            self._update_session_item(session_id)
            self._save_session(session)

    def _delete_session(self, session_id: str):
        """删除会话"""
        session = self._sessions.get(session_id)
        if not session:
            return

        msg = MessageBox(
            "删除对话",
            f"确定要删除「{session.title}」吗？此操作不可撤销。",
            self
        )
        if msg.exec():
            # 从列表移除
            for i in range(self._session_list.count()):
                item = self._session_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == session_id:
                    self._session_list.takeItem(i)
                    break

            # 删除数据
            del self._sessions[session_id]
            self._delete_session_file(session_id)
            self.sessionDeleted.emit(session_id)

            # 如果删除的是当前会话，切换到其他会话
            if session_id == self._current_session_id:
                self._current_session_id = None
                if self._session_list.count() > 0:
                    first_item = self._session_list.item(0)
                    first_id = first_item.data(Qt.ItemDataRole.UserRole)
                    self._select_session(first_id)
                    self.sessionSwitched.emit(first_id)
                else:
                    # 没有会话了，自动创建新的
                    self._on_new_session()

    def _on_search(self, text: str):
        """搜索会话"""
        text_lower = text.lower()
        for i in range(self._session_list.count()):
            item = self._session_list.item(i)
            session_id = item.data(Qt.ItemDataRole.UserRole)
            session = self._sessions.get(session_id)
            if session:
                match = text_lower in session.title.lower()
                item.setHidden(not match)

    # ===== 会话列表管理 =====

    def _add_session_item(self, session: ChatSession):
        """添加会话列表项"""
        item = QListWidgetItem(session.title)
        item.setData(Qt.ItemDataRole.UserRole, session.session_id)
        # 格式化时间显示
        created_display = self._format_time(session.created_at)
        updated_display = self._format_time(session.updated_at)
        item.setToolTip(f"创建: {created_display}\n更新: {updated_display}\n消息: {len(session.messages)} 条")
        self._session_list.insertItem(0, item)  # 新会话在顶部

    def _update_session_item(self, session_id: str):
        """更新会话列表项"""
        session = self._sessions.get(session_id)
        if not session:
            return
        for i in range(self._session_list.count()):
            item = self._session_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == session_id:
                item.setText(session.title)
                created_display = self._format_time(session.created_at)
                updated_display = self._format_time(session.updated_at)
                item.setToolTip(f"创建: {created_display}\n更新: {updated_display}\n消息: {len(session.messages)} 条")
                break

    @staticmethod
    def _format_time(iso_str: str) -> str:
        """将 ISO 时间字符串格式化为友好显示"""
        if not iso_str:
            return "未知"
        try:
            dt = datetime.fromisoformat(iso_str)
            now = datetime.now()
            # 今天的消息只显示时间
            if dt.date() == now.date():
                return dt.strftime("今天 %H:%M")
            # 昨天
            yesterday = (now - __import__('datetime').timedelta(days=1)).date()
            if dt.date() == yesterday:
                return dt.strftime("昨天 %H:%M")
            # 今年
            if dt.year == now.year:
                return dt.strftime("%m-%d %H:%M")
            # 更早
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            return iso_str[:16] if len(iso_str) > 16 else iso_str

    def _select_session(self, session_id: str):
        """选中会话"""
        for i in range(self._session_list.count()):
            item = self._session_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == session_id:
                self._session_list.setCurrentItem(item)
                break

    # ===== 持久化 =====

    def _load_sessions(self):
        """加载所有会话"""
        os.makedirs(self._state_dir, exist_ok=True)

        try:
            for filename in os.listdir(self._state_dir):
                if not filename.endswith(".json"):
                    continue
                filepath = os.path.join(self._state_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    session = ChatSession.from_dict(data)
                    self._sessions[session.session_id] = session
                except Exception:
                    continue
        except Exception:
            pass

        # 如果没有会话，创建默认会话
        if not self._sessions:
            default = ChatSession(session_id="default", title="默认对话")
            self._sessions[default.session_id] = default

        # 按更新时间排序，添加到列表
        sorted_sessions = sorted(
            self._sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True
        )
        for session in sorted_sessions:
            self._add_session_item(session)

        # 选中第一个
        if sorted_sessions:
            self._current_session_id = sorted_sessions[0].session_id
            self._select_session(self._current_session_id)

    def _save_session(self, session: ChatSession):
        """保存单个会话"""
        os.makedirs(self._state_dir, exist_ok=True)
        filepath = os.path.join(self._state_dir, f"{session.session_id}.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _delete_session_file(self, session_id: str):
        """删除会话文件"""
        filepath = os.path.join(self._state_dir, f"{session_id}.json")
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass

    # ===== 公共接口 =====

    def current_session_id(self) -> Optional[str]:
        """获取当前会话 ID"""
        return self._current_session_id

    def current_session(self) -> Optional[ChatSession]:
        """获取当前会话"""
        if self._current_session_id:
            return self._sessions.get(self._current_session_id)
        return None

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取指定会话"""
        return self._sessions.get(session_id)

    def update_session_messages(self, session_id: str, messages: list):
        """更新会话消息"""
        session = self._sessions.get(session_id)
        if session:
            session.messages = messages[-100:]  # 只保留最近 100 条
            session.update_timestamp()
            # 如果标题还是默认的，自动更新
            if session.title == "新对话":
                session.auto_title()
                self._update_session_item(session_id)
            self._save_session(session)

    def refresh_theme(self):
        """刷新主题"""
        from gugu_native.theme import get_colors
        c = get_colors()

        self.setStyleSheet(f"""
            QWidget#sessionManager {{
                background-color: {c.sidebar_bg};
                border-right: 1px solid {c.card_border};
            }}
        """)

        self._session_list.setStyleSheet(f"""
            QListWidget#sessionList {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QListWidget#sessionList::item {{
                border-radius: 8px;
                padding: 8px 10px;
                margin: 2px 0;
                color: {c.text_primary};
            }}
            QListWidget#sessionList::item:selected {{
                background-color: {c.accent};
                color: white;
            }}
            QListWidget#sessionList::item:hover:!selected {{
                background-color: {c.card_bg_hover};
            }}
        """)
