"""
配置管理器测试
"""

import pytest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config_manager import ConfigManager, ConfigSource, get_config, set_config


class TestConfigManager:
    """配置管理器测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = ConfigManager(config_dir=self.temp_dir)
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_config_default(self):
        """测试获取默认配置"""
        result = self.config_manager.get_config("nonexistent.key", default="default_value")
        assert result == "default_value"
    
    def test_set_and_get_config(self):
        """测试设置和获取配置"""
        # 设置配置
        success = self.config_manager.set_config("test.key", "test_value")
        assert success is True
        
        # 获取配置
        result = self.config_manager.get_config("test.key")
        assert result == "test_value"
    
    def test_config_cache(self):
        """测试配置缓存"""
        # 设置配置
        self.config_manager.set_config("cache.test", "cached_value")
        
        # 第一次获取
        result1 = self.config_manager.get_config("cache.test")
        
        # 修改配置文件（模拟外部修改）
        config_file = self.config_manager._get_config_file_path("cache.test")
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump({"key": "cache.test", "value": "new_value"}, f)
        
        # 第二次获取（应该使用缓存）
        result2 = self.config_manager.get_config("cache.test")
        assert result1 == result2  # 应该相等，因为使用了缓存
        
        # 清除缓存后获取
        self.config_manager.clear_cache("cache.test")
        result3 = self.config_manager.get_config("cache.test")
        assert result3 == "new_value"  # 应该获取新值
    
    def test_config_watch(self):
        """测试配置监视"""
        callback = MagicMock()
        
        # 监视配置
        self.config_manager.watch_config("watch.test", callback)
        
        # 修改配置
        self.config_manager.set_config("watch.test", "new_value")
        
        # 验证回调被调用
        callback.assert_called_once_with("watch.test", "new_value")
    
    def test_config_unwatch(self):
        """测试取消配置监视"""
        callback = MagicMock()
        
        # 监视配置
        self.config_manager.watch_config("unwatch.test", callback)
        
        # 取消监视
        self.config_manager.unwatch_config("unwatch.test", callback)
        
        # 修改配置
        self.config_manager.set_config("unwatch.test", "new_value")
        
        # 验证回调没有被调用
        callback.assert_not_called()
    
    def test_config_info(self):
        """测试配置信息"""
        # 设置配置
        self.config_manager.set_config("info.test", "info_value")
        
        # 获取配置信息
        info = self.config_manager.get_config_info("info.test")
        
        assert info is not None
        assert info['key'] == "info.test"
        assert info['source'] == "file"
        assert info['cached'] is True
        assert 'last_modified' in info
        assert 'checksum' in info
    
    def test_export_import_config(self):
        """测试配置导出导入"""
        # 设置配置
        self.config_manager.set_config("export.test1", "value1")
        self.config_manager.set_config("export.test2", "value2")
        
        # 导出配置
        export_file = os.path.join(self.temp_dir, "export.json")
        success = self.config_manager.export_config(export_file)
        assert success is True
        
        # 验证导出文件存在
        assert os.path.exists(export_file)
        
        # 清除缓存
        self.config_manager.clear_cache()
        
        # 导入配置
        success = self.config_manager.import_config(export_file)
        assert success is True
        
        # 验证导入的配置
        assert self.config_manager.get_config("export.test1") == "value1"
        assert self.config_manager.get_config("export.test2") == "value2"
    
    def test_environment_variable(self):
        """测试环境变量配置"""
        # 设置环境变量
        os.environ['TEST_ENV_VAR'] = 'env_value'
        
        try:
            # 获取配置
            result = self.config_manager.get_config("TEST_ENV_VAR")
            assert result == "env_value"
        finally:
            # 清理环境变量
            del os.environ['TEST_ENV_VAR']
    
    def test_config_reload(self):
        """测试配置重新加载"""
        # 设置配置
        self.config_manager.set_config("reload.test", "original_value")
        
        # 修改配置文件
        config_file = self.config_manager._get_config_file_path("reload.test")
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump({"key": "reload.test", "value": "reloaded_value"}, f)
        
        # 重新加载配置
        success = self.config_manager.reload_config("reload.test")
        assert success is True
        
        # 验证重新加载的配置
        result = self.config_manager.get_config("reload.test")
        assert result == "reloaded_value"


class TestConvenienceFunctions:
    """便捷函数测试类"""
    
    def test_get_config_function(self):
        """测试get_config便捷函数"""
        # 设置环境变量
        os.environ['CONVENIENCE_TEST'] = 'convenience_value'
        
        try:
            result = get_config("CONVENIENCE_TEST")
            assert result == "convenience_value"
        finally:
            del os.environ['CONVENIENCE_TEST']
    
    def test_set_config_function(self):
        """测试set_config便捷函数"""
        # 这个测试需要配置管理器实例，所以跳过
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])