"""
配置管理器

提供配置缓存、热更新、配置变更通知等功能。
"""

import os
import json
import time
import threading
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum
import hashlib
import logging

logger = logging.getLogger(__name__)


class ConfigSource(Enum):
    """配置来源"""
    FILE = "file"
    ENVIRONMENT = "environment"
    DEFAULT = "default"


@dataclass
class ConfigItem:
    """配置项"""
    key: str
    value: Any
    source: ConfigSource
    last_modified: float
    checksum: str


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = None) -> None:
        self.config_dir = config_dir or os.path.join(os.path.dirname(__file__), 'cache')
        self.config_cache: Dict[str, ConfigItem] = {}
        self.watchers: Dict[str, List[Callable]] = {}
        self.lock = threading.RLock()
        self.hot_reload_enabled = True
        self.cache_ttl = 300  # 5分钟缓存过期
        
        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
    
    def get_config(self, key: str, default: Any = None, use_cache: bool = True) -> Any:
        """获取配置值"""
        with self.lock:
            # 检查缓存
            if use_cache and key in self.config_cache:
                config_item = self.config_cache[key]
                if time.time() - config_item.last_modified < self.cache_ttl:
                    return config_item.value
            
            # 从配置源获取值
            value = self._load_config_from_source(key, default)
            
            # 更新缓存
            if use_cache:
                self._update_cache(key, value, ConfigSource.FILE)
            
            return value
    
    def set_config(self, key: str, value: Any, source: ConfigSource = ConfigSource.FILE) -> bool:
        """设置配置值"""
        with self.lock:
            try:
                # 保存到配置源
                if source == ConfigSource.FILE:
                    self._save_config_to_file(key, value)
                
                # 更新缓存
                self._update_cache(key, value, source)
                
                # 通知观察者
                self._notify_watchers(key, value)
                
                return True
            except Exception as e:
                logger.info(f"[ConfigManager] 设置配置失败: {e}")
                return False
    
    def watch_config(self, key: str, callback: Callable) -> None:
        """监视配置变更"""
        with self.lock:
            if key not in self.watchers:
                self.watchers[key] = []
            self.watchers[key].append(callback)
    
    def unwatch_config(self, key: str, callback: Callable) -> None:
        """取消监视配置变更"""
        with self.lock:
            if key in self.watchers:
                self.watchers[key] = [cb for cb in self.watchers[key] if cb != callback]
    
    def clear_cache(self, key: str = None) -> None:
        """清除缓存"""
        with self.lock:
            if key:
                self.config_cache.pop(key, None)
            else:
                self.config_cache.clear()
    
    def reload_config(self, key: str = None) -> bool:
        """重新加载配置"""
        with self.lock:
            try:
                if key:
                    # 重新加载特定配置
                    self.clear_cache(key)
                    self.get_config(key, use_cache=True)
                else:
                    # 重新加载所有配置
                    self.clear_cache()
                    # 这里可以添加重新加载所有配置的逻辑
                
                return True
            except Exception as e:
                logger.info(f"[ConfigManager] 重新加载配置失败: {e}")
                return False
    
    def _load_config_from_source(self, key: str, default: Any = None) -> Any:
        """从配置源加载配置"""
        # 尝试从环境变量获取
        env_value = os.environ.get(key)
        if env_value is not None:
            return self._parse_env_value(env_value)
        
        # 尝试从配置文件获取
        config_file = self._get_config_file_path(key)
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('value', default)
            except Exception as e:
                logger.info(f"[ConfigManager] 读取配置文件失败: {e}")
        
        return default
    
    def _save_config_to_file(self, key: str, value: Any) -> None:
        """保存配置到文件"""
        config_file = self._get_config_file_path(key)
        config_data = {
            'key': key,
            'value': value,
            'updated_at': time.time(),
            'updated_at_iso': __import__('datetime').datetime.now().isoformat()
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
    
    def _get_config_file_path(self, key: str) -> str:
        """获取配置文件路径"""
        # 将key转换为安全的文件名
        safe_key = key.replace('.', '_').replace('/', '_').replace('\\', '_')
        return os.path.join(self.config_dir, f"{safe_key}.json")
    
    def _update_cache(self, key: str, value: Any, source: ConfigSource) -> None:
        """更新缓存"""
        # 计算值的校验和
        checksum = self._calculate_checksum(value)
        
        self.config_cache[key] = ConfigItem(
            key=key,
            value=value,
            source=source,
            last_modified=time.time(),
            checksum=checksum
        )
    
    def _calculate_checksum(self, value: Any) -> str:
        """计算值的校验和"""
        try:
            value_str = json.dumps(value, sort_keys=True, ensure_ascii=False)
            return hashlib.md5(value_str.encode('utf-8')).hexdigest()
        except (TypeError, ValueError, json.JSONDecodeError):
            return hashlib.md5(str(value).encode('utf-8')).hexdigest()
    
    def _notify_watchers(self, key: str, value: Any) -> None:
        """通知观察者"""
        if key in self.watchers:
            for callback in self.watchers[key]:
                try:
                    callback(key, value)
                except Exception as e:
                    logger.info(f"[ConfigManager] 通知观察者失败: {e}")
    
    def _parse_env_value(self, value: str) -> Any:
        """解析环境变量值"""
        # 尝试解析为JSON
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # 尝试解析为数字
            try:
                if '.' in value:
                    return float(value)
                else:
                    return int(value)
            except (ValueError, TypeError):
                # 返回字符串
                return value
    
    def get_config_info(self, key: str) -> Optional[Dict[str, Any]]:
        """获取配置信息"""
        with self.lock:
            if key in self.config_cache:
                config_item = self.config_cache[key]
                return {
                    'key': config_item.key,
                    'source': config_item.source.value,
                    'last_modified': config_item.last_modified,
                    'last_modified_iso': __import__('datetime').datetime.fromtimestamp(
                        config_item.last_modified
                    ).isoformat(),
                    'checksum': config_item.checksum,
                    'cached': True
                }
            return None
    
    def get_all_config_info(self) -> Dict[str, Dict[str, Any]]:
        """获取所有配置信息"""
        with self.lock:
            result = {}
            for key, config_item in self.config_cache.items():
                result[key] = {
                    'source': config_item.source.value,
                    'last_modified': config_item.last_modified,
                    'last_modified_iso': __import__('datetime').datetime.fromtimestamp(
                        config_item.last_modified
                    ).isoformat(),
                    'checksum': config_item.checksum,
                    'cached': True
                }
            return result
    
    def export_config(self, output_file: str) -> bool:
        """导出配置"""
        try:
            with self.lock:
                config_data = {}
                for key, config_item in self.config_cache.items():
                    config_data[key] = {
                        'value': config_item.value,
                        'source': config_item.source.value,
                        'last_modified': config_item.last_modified
                    }
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                
                return True
        except Exception as e:
            logger.info(f"[ConfigManager] 导出配置失败: {e}")
            return False
    
    def import_config(self, input_file: str) -> bool:
        """导入配置"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            with self.lock:
                for key, config_info in config_data.items():
                    value = config_info.get('value')
                    source = ConfigSource(config_info.get('source', 'file'))
                    self.set_config(key, value, source)
            
            return True
        except Exception as e:
            logger.info(f"[ConfigManager] 导入配置失败: {e}")
            return False


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config(key: str, default: Any = None, use_cache: bool = True) -> Any:
    """获取配置的便捷函数"""
    return config_manager.get_config(key, default, use_cache)


def set_config(key: str, value: Any, source: ConfigSource = ConfigSource.FILE) -> bool:
    """设置配置的便捷函数"""
    return config_manager.set_config(key, value, source)


def watch_config(key: str, callback: Callable) -> None:
    """监视配置的便捷函数"""
    config_manager.watch_config(key, callback)


def reload_config(key: str = None) -> bool:
    """重新加载配置的便捷函数"""
    return config_manager.reload_config(key)


if __name__ == "__main__":
    # 测试配置管理器
    logger.info("测试配置管理器...")
    
    # 测试设置和获取配置
    set_config("test.key1", "value1")
    set_config("test.key2", {"nested": "value2"})
    
    logger.info(f"test.key1 = {get_config('test.key1')}")
    logger.info(f"test.key2 = {get_config('test.key2')}")
    
    # 测试配置信息
    info = config_manager.get_config_info("test.key1")
    logger.info(f"test.key1 信息: {info}")
    
    # 测试导出配置
    config_manager.export_config("test_config_export.json")
    logger.info("配置已导出到 test_config_export.json")
    
    logger.info("配置管理器测试完成")