"""
桌面宠物模式 — 无边框透明窗口 + Live2D

功能:
- 无边框透明窗口（FramelessWindowHint + WA_TranslucentBackground）
- 可拖拽移动
- 右键菜单（切回主窗口/关闭宠物/说话）
- Live2D 渲染到透明背景上
- 桌面宠物模式和主窗口模式可切换

使用方式:
    pet = DesktopPetWindow(main_window)
    pet.show()  # 显示桌面宠物
    pet.hide()  # 切回主窗口
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QMenu
)
from PySide6.QtCore import Qt, Signal, QPoint, QTimer
from PySide6.QtGui import QAction

# live2d-py 是可选依赖
try:
    import live2d.v3 as live2d
    LIVE2D_AVAILABLE = True
except ImportError:
    live2d = None
    LIVE2D_AVAILABLE = False

from gugu_native.widgets.live2d_widget import Live2DWidget

# 项目根目录
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class DesktopPetWindow(QWidget):
    """
    桌面宠物窗口 — 无边框透明窗口 + Live2D 渲染

    信号:
        switch_to_main: 请求切回主窗口
        pet_speak: 请求宠物说话
        pet_closed: 宠物窗口关闭
    """

    switch_to_main = Signal()
    pet_speak = Signal()
    pet_closed = Signal()

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main_window = main_window
        self._drag_pos = QPoint()
        self._drag_start_pos = QPoint()  # 记录按下位置，用于区分点击和拖拽
        self._model_loaded = False
        self._init_ui()
        self._init_menu()

    def _init_ui(self):
        """初始化 UI"""
        # 无边框 + 置顶 + 透明背景
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # 不在任务栏显示
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # 固定宠物大小
        self.setFixedSize(320, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Live2D 渲染（透明背景）
        self.live2d_widget = Live2DWidget()
        self.live2d_widget.setMinimumSize(320, 420)
        layout.addWidget(self.live2d_widget)

        # 延迟加载模型
        QTimer.singleShot(300, self._load_model)

    def _init_menu(self):
        """初始化右键菜单"""
        self._menu = QMenu(self)
        self._menu.setStyleSheet("""
            QMenu {
                background-color: #2a2a3e;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item:selected {
                background-color: #3d3d5c;
                border-radius: 4px;
            }
        """)

        # 切回主窗口
        switch_action = QAction("返回主窗口", self)
        switch_action.triggered.connect(self._on_switch_to_main)
        self._menu.addAction(switch_action)

        # 说话
        speak_action = QAction("说话", self)
        speak_action.triggered.connect(self.pet_speak.emit)
        self._menu.addAction(speak_action)

        self._menu.addSeparator()

        # 随机动作
        motion_action = QAction("随机动作", self)
        motion_action.triggered.connect(self._on_random_motion)
        self._menu.addAction(motion_action)

        self._menu.addSeparator()

        # 关闭宠物
        close_action = QAction("关闭宠物", self)
        close_action.triggered.connect(self._on_close_pet)
        self._menu.addAction(close_action)

    def _load_model(self):
        """加载 Live2D 模型"""
        # 尝试从主窗口的 ChatPage 获取当前模型路径
        model_path = None
        chat_page = getattr(self._main_window, 'chat_page', None)
        if chat_page:
            live2d_w = getattr(chat_page, 'live2d_widget', None)
            if live2d_w and live2d_w.model_path:
                model_path = live2d_w.model_path

        # 回退到默认模型
        if not model_path:
            model_path = os.path.join(
                PROJECT_DIR, "app", "web", "static", "assets", "model",
                "hiyori", "Hiyori.model3.json"
            )

        if os.path.exists(model_path):
            self._model_loaded = self.live2d_widget.load_model(model_path)
        else:
            print(f"[DesktopPet] 模型不存在: {model_path}")

    def _on_switch_to_main(self):
        """切回主窗口"""
        self.hide()
        self.switch_to_main.emit()

    def _on_close_pet(self):
        """关闭宠物"""
        self.hide()
        self.pet_closed.emit()

    def _on_random_motion(self):
        """随机动作"""
        if self.live2d_widget.model:
            self.live2d_widget.start_random_motion("TapBody")

    # ========== 拖拽移动 ==========

    def mousePressEvent(self, event):
        """鼠标按下 — 记录拖拽起始位置"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._drag_start_pos = event.globalPosition().toPoint()  # 记录按下位置
        elif event.button() == Qt.MouseButton.RightButton:
            # 右键菜单
            self._menu.exec(event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动 — 拖拽窗口"""
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放 — 仅在未拖拽时触发动作（移动距离 < 5px 视为点击）"""
        if event.button() == Qt.MouseButton.LeftButton and self.live2d_widget.model:
            release_pos = event.globalPosition().toPoint()
            distance = (release_pos - self._drag_start_pos).manhattanLength()
            if distance < 5:
                # 点击宠物 → 挥手动作
                try:
                    self.live2d_widget.start_random_motion("TapBody")
                except Exception:
                    pass
        super().mouseReleaseEvent(event)

    def closeEvent(self, event):
        """关闭事件"""
        self.pet_closed.emit()
        super().closeEvent(event)
