"""懒加载页面混入基类

所有需要延迟构造的页面继承此类。
启动时仅显示骨架屏，首次切换到该页时才执行实际构造。

v1.11.24 优化:
- 新增 LazyPageMixin，支持骨架屏 + 延迟初始化
- ensure_initialized 增加异常安全（try/finally）

v1.12.0 优化:
- ensure_initialized 添加 processEvents() 防止 UI 冻结
- 在 lazy_init() 前后各处理一次事件队列，保持界面响应
"""
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget, QApplication


class LazyPageMixin:
    """懒加载混入：页面首次可见时才执行完整初始化

    使用方式：
        class MyPage(QWidget, LazyPageMixin):
            def __init__(self, parent=None):
                QWidget.__init__(self, parent)
                LazyPageMixin.__init__(self)
                ...
    """

    def __init__(self):
        self._is_initialized = False
        self._is_loading = False

    def ensure_initialized(self):
        """由 GuguGagaApp.switchTo() 调用，确保页面已初始化

        v1.12.0: 在初始化前后处理事件队列，防止 UI 冻结
        """
        if self._is_initialized or self._is_loading:
            return
        self._is_loading = True
        try:
            self.show_skeleton()
            # v1.12.0: 让骨架屏先渲染出来
            QApplication.processEvents()
            self.lazy_init()
            self._is_initialized = True
        finally:
            self._is_loading = False
            self.hide_skeleton()
            # v1.12.0: 初始化完成后处理积压事件
            QApplication.processEvents()

    def lazy_init(self):
        """子类重写：完成实际的 UI 构造和控件填充"""
        raise NotImplementedError("子类必须重写 lazy_init()")

    def show_skeleton(self):
        """显示骨架屏/加载占位"""
        pass

    def hide_skeleton(self):
        """隐藏骨架屏"""
        pass

    @property
    def is_initialized(self) -> bool:
        return self._is_initialized

    @property
    def is_loading(self) -> bool:
        return self._is_loading
