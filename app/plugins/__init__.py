"""
=====================================
插件系统
=====================================

提供插件 API 和加载机制，支持第三方扩展。

架构：
- Plugin (抽象基类) — 定义插件接口
- PluginManager — 管理插件生命周期
- 插件目录: app/plugins/ 或 ~/.gugugaga/plugins/

插件生命周期：
1. 发现 — 扫描插件目录
2. 加载 — 导入插件模块
3. 初始化 — 调用 plugin.on_load()
4. 运行 — 插件响应事件
5. 卸载 — 调用 plugin.on_unload()

作者: 咕咕嘎嘎
日期: 2026-06-02
"""

import os
import json
import importlib
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ==================== 插件元数据 ====================

@dataclass
class PluginInfo:
    """插件元数据"""
    name: str
    version: str
    description: str
    author: str
    entry_point: str  # 入口模块，如 "my_plugin.main"
    enabled: bool = True
    dependencies: List[str] = None  # 依赖的其他插件

    def __post_init__(self) -> None:
        """内部方法"""
        if self.dependencies is None:
            self.dependencies = []


# ==================== 插件基类 ====================

class Plugin(ABC):
    """插件抽象基类

    所有插件必须继承此类，并实现 on_load/on_unload 方法。
    """

    @property
    @abstractmethod
    def info(self) -> PluginInfo:
        """插件元数据"""
        pass

    @abstractmethod
    def on_load(self, context: Dict[str, Any]) -> None:
        """插件加载时调用

        Args:
            context: 应用上下文，包含：
                - app: 应用实例
                - config: 配置字典
                - logger: 日志实例
                - register_hook: 注册钩子的函数
        """
        pass

    @abstractmethod
    def on_unload(self) -> None:
        """插件卸载时调用"""
        pass

    def on_ready(self) -> None:
        """应用就绪后调用（可选）"""
        pass

    def on_config_change(self, config: Dict[str, Any]) -> None:
        """配置变更时调用（可选）"""
        pass


# ==================== 钩子系统 ====================

class HookManager:
    """钩子管理器

    允许插件注册钩子，在特定事件发生时被调用。
    """

    def __init__(self) -> None:
        """内部方法"""
        self._hooks: Dict[str, List[Callable]] = {}

    def register(self, event: str, callback: Callable) -> None:
        """注册钩子

        Args:
            event: 事件名称
            callback: 回调函数
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)
        logger.debug(f"钩子已注册: {event}")

    def unregister(self, event: str, callback: Callable) -> None:
        """取消注册钩子"""
        if event in self._hooks:
            self._hooks[event] = [h for h in self._hooks[event] if h != callback]

    def trigger(self, event: str, **kwargs) -> None:
        """触发钩子

        Args:
            event: 事件名称
            **kwargs: 传递给回调的参数
        """
        if event in self._hooks:
            for callback in self._hooks[event]:
                try:
                    callback(**kwargs)
                except Exception as e:
                    logger.error(f"钩子执行失败 ({event}): {e}")

    def get_events(self) -> List[str]:
        """获取所有已注册的事件"""
        return list(self._hooks.keys())


# ==================== 插件管理器 ====================

class PluginManager:
    """插件管理器

    管理插件的发现、加载、卸载和生命周期。
    """

    # 支持的钩子事件
    SUPPORTED_EVENTS = [
        "on_message",           # 收到消息
        "on_danmaku",           # 收到弹幕
        "on_tts_start",         # TTS 开始
        "on_tts_end",           # TTS 结束
        "on_asr_result",        # ASR 识别结果
        "on_model_loaded",      # 模型加载完成
        "on_theme_change",      # 主题变更
        "on_startup",           # 应用启动
        "on_shutdown",          # 应用关闭
    ]

    def __init__(self, plugin_dirs: List[str] = None) -> None:
        """
        Args:
            plugin_dirs: 插件目录列表
        """
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_infos: Dict[str, PluginInfo] = {}
        self._hook_manager = HookManager()
        self._context: Dict[str, Any] = {}

        # 默认插件目录
        if plugin_dirs is None:
            plugin_dirs = [
                str(Path(__file__).parent),  # app/plugins/
                str(Path.home() / ".gugugaga" / "plugins"),  # 用户插件
            ]
        self._plugin_dirs = [Path(d) for d in plugin_dirs]

    @property
    def hooks(self) -> HookManager:
        """钩子管理器"""
        return self._hook_manager

    def set_context(self, context: Dict[str, Any]) -> None:
        """设置应用上下文"""
        self._context = context

    def discover_plugins(self) -> List[PluginInfo]:
        """发现所有可用插件

        Returns:
            插件信息列表
        """
        discovered = []

        for plugin_dir in self._plugin_dirs:
            if not plugin_dir.exists():
                continue

            # 扫描插件目录
            for item in plugin_dir.iterdir():
                if item.is_dir():
                    # 检查是否有 plugin.json
                    manifest = item / "plugin.json"
                    if manifest.exists():
                        try:
                            with open(manifest, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            info = PluginInfo(**data)
                            discovered.append(info)
                        except Exception as e:
                            logger.warning(f"插件清单解析失败 ({item}): {e}")

                elif item.suffix == ".py" and item.stem != "__init__":
                    # 单文件插件
                    try:
                        info = PluginInfo(
                            name=item.stem,
                            version="1.0.0",
                            description=f"Plugin: {item.stem}",
                            author="Unknown",
                            entry_point=item.stem
                        )
                        discovered.append(info)
                    except Exception as e:
                        logger.warning(f"插件解析失败 ({item}): {e}")

        return discovered

    def load_plugin(self, plugin_info: PluginInfo) -> bool:
        """加载插件

        Args:
            plugin_info: 插件信息

        Returns:
            是否加载成功
        """
        try:
            # 导入插件模块
            module = importlib.import_module(plugin_info.entry_point)

            # 查找 Plugin 子类
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, Plugin) and
                    attr is not Plugin):
                    plugin_class = attr
                    break

            if plugin_class is None:
                logger.warning(f"插件未找到 Plugin 子类: {plugin_info.name}")
                return False

            # 实例化插件
            plugin = plugin_class()

            # 调用 on_load
            context = {
                **self._context,
                "hooks": self._hook_manager,
                "register_hook": self._hook_manager.register,
            }
            plugin.on_load(context)

            # 注册插件
            self._plugins[plugin_info.name] = plugin
            self._plugin_infos[plugin_info.name] = plugin_info

            logger.info(f"插件已加载: {plugin_info.name} v{plugin_info.version}")
            return True

        except Exception as e:
            logger.error(f"插件加载失败 ({plugin_info.name}): {e}")
            return False

    def unload_plugin(self, name: str) -> bool:
        """卸载插件

        Args:
            name: 插件名称

        Returns:
            是否卸载成功
        """
        if name not in self._plugins:
            return False

        try:
            plugin = self._plugins[name]
            plugin.on_unload()

            del self._plugins[name]
            del self._plugin_infos[name]

            logger.info(f"插件已卸载: {name}")
            return True

        except Exception as e:
            logger.error(f"插件卸载失败 ({name}): {e}")
            return False

    def load_all(self) -> None:
        """加载所有发现的插件"""
        discovered = self.discover_plugins()
        for info in discovered:
            if info.enabled:
                self.load_plugin(info)

    def unload_all(self) -> None:
        """卸载所有插件"""
        for name in list(self._plugins.keys()):
            self.unload_plugin(name)

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """获取插件实例"""
        return self._plugins.get(name)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """列出所有已加载的插件"""
        return [
            {
                "name": info.name,
                "version": info.version,
                "description": info.description,
                "enabled": info.enabled,
                "loaded": name in self._plugins,
            }
            for name, info in self._plugin_infos.items()
        ]

    def trigger_event(self, event: str, **kwargs) -> None:
        """触发事件"""
        self._hook_manager.trigger(event, **kwargs)

    def on_ready(self) -> None:
        """通知所有插件应用就绪"""
        for plugin in self._plugins.values():
            try:
                plugin.on_ready()
            except Exception as e:
                logger.error(f"插件 on_ready 失败: {e}")


# ==================== 全局实例 ====================

_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


def init_plugins(context: Dict[str, Any] = None) -> None:
    """初始化插件系统

    Args:
        context: 应用上下文
    """
    manager = get_plugin_manager()
    if context:
        manager.set_context(context)
    manager.load_all()
