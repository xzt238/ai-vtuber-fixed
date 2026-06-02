"""懒加载页面混入基类

所有需要延迟构造的页面继承此类。
启动时仅显示骨架屏，首次切换到该页时才执行实际构造。

v1.11.24 优化:
- 新增 LazyPageMixin，支持骨架屏 + 延迟初始化
- ensure_initialized 增加异常安全（try/finally）
"""
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget


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
        """由 GuguGagaApp.switchTo() 调用，确保页面已初始化"""
        if self._is_initialized or self._is_loading:
            return
        self._is_loading = True
        try:
            self.show_skeleton()
            self.lazy_init()
            self._is_initialized = True
        finally:
            self._is_loading = False
            self.hide_skeleton()

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
