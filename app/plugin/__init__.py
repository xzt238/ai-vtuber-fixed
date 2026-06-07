"""
插件系统模块
支持插件加载、插件管理、插件执行
"""

import os
import json
import asyncio
import importlib
import importlib.util
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime

class PluginType(Enum):
    """插件类型"""
    TOOL = "tool"  # 工具插件
    TTS = "tts"  # TTS插件
    ASR = "asr"  # ASR插件
    LLM = "llm"  # LLM插件
    VISION = "vision"  # 视觉插件
    GAME = "game"  # 游戏插件
    CUSTOM = "custom"  # 自定义插件

class PluginStatus(Enum):
    """插件状态"""
    DISABLED = "disabled"  # 禁用
    ENABLED = "enabled"  # 启用
    LOADED = "loaded"  # 已加载
    ERROR = "error"  # 错误

@dataclass
class PluginInfo:
    """插件信息"""
    id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    plugin_type: PluginType = PluginType.CUSTOM
    entry_point: str = ""  # 入口点（模块路径:函数名）
    dependencies: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    status: PluginStatus = PluginStatus.DISABLED
    enabled: bool = False
    loaded_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PluginManifest:
    """插件清单"""
    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    type: str = "custom"
    entry_point: str = ""
    dependencies: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)

class PluginLoader:
    """插件加载器"""
    
    def __init__(self, plugins_dir: str = "./plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.loaded_modules: Dict[str, Any] = {}
    
    async def discover_plugins(self) -> List[PluginManifest]:
        """发现插件"""
        plugins = []
        
        if not self.plugins_dir.exists():
            return plugins
        
        for plugin_dir in self.plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue
            
            manifest_file = plugin_dir / "manifest.json"
            if manifest_file.exists():
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        manifest_data = json.load(f)
                    
                    manifest = PluginManifest(
                        id=manifest_data.get("id", plugin_dir.name),
                        name=manifest_data.get("name", plugin_dir.name),
                        version=manifest_data.get("version", "1.0.0"),
                        description=manifest_data.get("description", ""),
                        author=manifest_data.get("author", ""),
                        type=manifest_data.get("type", "custom"),
                        entry_point=manifest_data.get("entry_point", ""),
                        dependencies=manifest_data.get("dependencies", []),
                        config=manifest_data.get("config", {})
                    )
                    
                    plugins.append(manifest)
                    
                except Exception as e:
                    print(f"[Plugin] 读取插件清单失败: {plugin_dir.name}, {e}")
        
        return plugins
    
    async def load_plugin(self, plugin_id: str, entry_point: str) -> Optional[Any]:
        """加载插件"""
        try:
            # 解析入口点
            if ":" in entry_point:
                module_path, func_name = entry_point.rsplit(":", 1)
            else:
                module_path = entry_point
                func_name = None
            
            # 构建完整路径
            full_path = self.plugins_dir / plugin_id / module_path.replace(".", "/")
            if not full_path.exists():
                full_path = full_path.with_suffix(".py")
            
            if not full_path.exists():
                print(f"[Plugin] 插件文件不存在: {full_path}")
                return None
            
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(
                f"plugin_{plugin_id}",
                str(full_path)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 获取入口函数
            if func_name:
                entry_func = getattr(module, func_name, None)
                if entry_func is None:
                    print(f"[Plugin] 入口函数不存在: {func_name}")
                    return None
                return entry_func
            else:
                return module
            
        except Exception as e:
            print(f"[Plugin] 加载插件失败: {plugin_id}, {e}")
            return None
    
    async def unload_plugin(self, plugin_id: str):
        """卸载插件"""
        if plugin_id in self.loaded_modules:
            del self.loaded_modules[plugin_id]
            print(f"[Plugin] 插件已卸载: {plugin_id}")

class PluginManager:
    """插件管理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        plugins_dir = self.config.get("plugins_dir", "./plugins")
        self.auto_load = self.config.get("auto_load", True)
        self.max_plugins = self.config.get("max_plugins", 50)
        
        # 初始化组件
        self.loader = PluginLoader(plugins_dir)
        
        # 插件信息
        self.plugins: Dict[str, PluginInfo] = {}
        
        # 已加载的插件实例
        self.plugin_instances: Dict[str, Any] = {}
        
        # 插件目录
        self.plugins_dir = Path(plugins_dir)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[Plugin] 初始化完成: plugins_dir={plugins_dir}")
    
    async def initialize(self):
        """初始化插件系统"""
        # 发现插件
        manifests = await self.loader.discover_plugins()
        
        # 注册插件
        for manifest in manifests:
            plugin_info = PluginInfo(
                id=manifest.id,
                name=manifest.name,
                version=manifest.version,
                description=manifest.description,
                author=manifest.author,
                plugin_type=PluginType(manifest.type),
                entry_point=manifest.entry_point,
                dependencies=manifest.dependencies,
                config=manifest.config,
                status=PluginStatus.DISABLED,
                enabled=False
            )
            self.plugins[manifest.id] = plugin_info
        
        print(f"[Plugin] 发现了 {len(manifests)} 个插件")
        
        # 自动加载启用的插件
        if self.auto_load:
            await self._auto_load_plugins()
    
    async def _auto_load_plugins(self):
        """自动加载插件"""
        for plugin_id, plugin_info in self.plugins.items():
            if plugin_info.enabled:
                await self.load_plugin(plugin_id)
    
    async def load_plugin(self, plugin_id: str) -> bool:
        """加载插件"""
        if plugin_id not in self.plugins:
            print(f"[Plugin] 插件不存在: {plugin_id}")
            return False
        
        plugin_info = self.plugins[plugin_id]
        
        try:
            # 加载插件
            plugin_instance = await self.loader.load_plugin(
                plugin_id,
                plugin_info.entry_point
            )
            
            if plugin_instance is None:
                plugin_info.status = PluginStatus.ERROR
                return False
            
            # 保存实例
            self.plugin_instances[plugin_id] = plugin_instance
            
            # 更新状态
            plugin_info.status = PluginStatus.LOADED
            plugin_info.loaded_at = datetime.now()
            
            print(f"[Plugin] 插件加载成功: {plugin_id}")
            return True
            
        except Exception as e:
            print(f"[Plugin] 插件加载失败: {plugin_id}, {e}")
            plugin_info.status = PluginStatus.ERROR
            return False
    
    async def unload_plugin(self, plugin_id: str) -> bool:
        """卸载插件"""
        if plugin_id not in self.plugins:
            return False
        
        try:
            # 卸载插件
            await self.loader.unload_plugin(plugin_id)
            
            # 移除实例
            if plugin_id in self.plugin_instances:
                del self.plugin_instances[plugin_id]
            
            # 更新状态
            self.plugins[plugin_id].status = PluginStatus.DISABLED
            self.plugins[plugin_id].loaded_at = None
            
            print(f"[Plugin] 插件卸载成功: {plugin_id}")
            return True
            
        except Exception as e:
            print(f"[Plugin] 插件卸载失败: {plugin_id}, {e}")
            return False
    
    async def enable_plugin(self, plugin_id: str) -> bool:
        """启用插件"""
        if plugin_id not in self.plugins:
            return False
        
        plugin_info = self.plugins[plugin_id]
        plugin_info.enabled = True
        plugin_info.status = PluginStatus.ENABLED
        
        # 加载插件
        return await self.load_plugin(plugin_id)
    
    async def disable_plugin(self, plugin_id: str) -> bool:
        """禁用插件"""
        if plugin_id not in self.plugins:
            return False
        
        plugin_info = self.plugins[plugin_id]
        plugin_info.enabled = False
        
        # 卸载插件
        return await self.unload_plugin(plugin_id)
    
    async def execute_plugin(self, plugin_id: str, **kwargs) -> Any:
        """执行插件"""
        if plugin_id not in self.plugin_instances:
            print(f"[Plugin] 插件未加载: {plugin_id}")
            return None
        
        try:
            plugin_instance = self.plugin_instances[plugin_id]
            
            # 检查是否是可调用对象
            if callable(plugin_instance):
                # 如果是函数，直接调用
                if asyncio.iscoroutinefunction(plugin_instance):
                    result = await plugin_instance(**kwargs)
                else:
                    result = plugin_instance(**kwargs)
                return result
            elif hasattr(plugin_instance, "execute"):
                # 如果有execute方法，调用它
                if asyncio.iscoroutinefunction(plugin_instance.execute):
                    result = await plugin_instance.execute(**kwargs)
                else:
                    result = plugin_instance.execute(**kwargs)
                return result
            else:
                print(f"[Plugin] 插件不可执行: {plugin_id}")
                return None
            
        except Exception as e:
            print(f"[Plugin] 插件执行失败: {plugin_id}, {e}")
            return None
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self.plugins.get(plugin_id)
    
    def list_plugins(self, plugin_type: PluginType = None) -> List[PluginInfo]:
        """列出插件"""
        if plugin_type:
            return [p for p in self.plugins.values() if p.plugin_type == plugin_type]
        return list(self.plugins.values())
    
    def get_loaded_plugins(self) -> List[PluginInfo]:
        """获取已加载的插件"""
        return [p for p in self.plugins.values() if p.status == PluginStatus.LOADED]
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "total_plugins": len(self.plugins),
            "loaded_plugins": len(self.plugin_instances),
            "enabled_plugins": len([p for p in self.plugins.values() if p.enabled]),
            "plugins": {
                pid: {
                    "name": p.name,
                    "version": p.version,
                    "type": p.plugin_type.value,
                    "status": p.status.value,
                    "enabled": p.enabled
                }
                for pid, p in self.plugins.items()
            }
        }

# 全局插件管理器实例
_plugin_manager: Optional[PluginManager] = None

def get_plugin_manager(config: Dict[str, Any] = None) -> PluginManager:
    """获取插件管理器实例"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager(config)
    return _plugin_manager
