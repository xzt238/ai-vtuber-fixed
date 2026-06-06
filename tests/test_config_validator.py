"""
配置验证器测试
"""

import pytest
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config_validator import ConfigValidator, ConfigType, ValidationResult


class TestConfigValidator:
    """配置验证器测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.validator = ConfigValidator()
    
    def test_validate_provider_config_valid(self):
        """测试有效的Provider配置验证"""
        valid_config = {
            "deepseek": {
                "label": "DeepSeek",
                "baseUrl": "https://api.deepseek.com",
                "models": ["deepseek-chat", "deepseek-reasoner"],
                "defaultModel": "deepseek-chat",
                "hint": "DeepSeek API",
                "keyPlaceholder": "在 platform.deepseek.com 获取"
            }
        }
        
        result = self.validator.validate_config(valid_config, ConfigType.PROVIDER)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_provider_config_missing_fields(self):
        """测试缺少字段的Provider配置验证"""
        invalid_config = {
            "deepseek": {
                "label": "DeepSeek",
                # 缺少 baseUrl, models, defaultModel
            }
        }
        
        result = self.validator.validate_config(invalid_config, ConfigType.PROVIDER)
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_validate_provider_config_invalid_url(self):
        """测试无效URL的Provider配置验证"""
        invalid_config = {
            "deepseek": {
                "label": "DeepSeek",
                "baseUrl": "invalid-url",  # 无效URL
                "models": ["deepseek-chat"],
                "defaultModel": "deepseek-chat"
            }
        }
        
        result = self.validator.validate_config(invalid_config, ConfigType.PROVIDER)
        assert len(result.warnings) > 0  # 应该有警告
    
    def test_validate_voice_config_valid(self):
        """测试有效的语音配置验证"""
        valid_config = [
            ("zh-CN-XiaoxiaoNeural", "中文女声"),
            ("zh-CN-YunxiNeural", "中文男声")
        ]
        
        result = self.validator.validate_config(valid_config, ConfigType.VOICE)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_voice_config_invalid(self):
        """测试无效的语音配置验证"""
        invalid_config = [
            ("", "空ID"),  # 空ID
            ("invalid", "无效格式")  # 无效格式
        ]
        
        result = self.validator.validate_config(invalid_config, ConfigType.VOICE)
        # 应该有警告或建议
        assert len(result.warnings) > 0 or len(result.suggestions) > 0
    
    def test_validate_expression_config_valid(self):
        """测试有效的表情配置验证"""
        valid_config = {
            "keywords": {
                "happy": ["开心", "高兴"],
                "sad": ["难过", "伤心"]
            },
            "map": {
                "happy": "f02",
                "sad": "f03"
            }
        }
        
        result = self.validator.validate_config(valid_config, ConfigType.EXPRESSION)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_port_config_valid(self):
        """测试有效的端口配置验证"""
        valid_config = {
            "HTTP_PORT": 12393,
            "WS_PORT": 12394
        }
        
        result = self.validator.validate_config(valid_config, ConfigType.PORT)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_port_config_invalid_range(self):
        """测试无效范围的端口配置验证"""
        invalid_config = {
            "HTTP_PORT": 80,  # 常用端口
            "WS_PORT": 12394
        }
        
        result = self.validator.validate_config(invalid_config, ConfigType.PORT)
        # 应该有警告
        assert len(result.warnings) > 0
    
    def test_validate_port_config_same_ports(self):
        """测试相同端口的配置验证"""
        invalid_config = {
            "HTTP_PORT": 12393,
            "WS_PORT": 12393  # 相同端口
        }
        
        result = self.validator.validate_config(invalid_config, ConfigType.PORT)
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_validate_path_config_valid(self):
        """测试有效的路径配置验证"""
        valid_config = {
            "PROJECT_DIR": os.path.dirname(__file__),  # 当前目录
            "CONFIG_DIR": os.path.dirname(__file__)
        }
        
        result = self.validator.validate_config(valid_config, ConfigType.PATH)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_path_config_nonexistent(self):
        """测试不存在的路径配置验证"""
        invalid_config = {
            "PROJECT_DIR": "/nonexistent/path"
        }
        
        result = self.validator.validate_config(invalid_config, ConfigType.PATH)
        # 应该有警告
        assert len(result.warnings) > 0
    
    def test_generate_validation_report(self):
        """测试生成验证报告"""
        report = self.validator.generate_validation_report()
        
        assert isinstance(report, str)
        assert "配置验证报告" in report
        assert "验证结果摘要" in report
        assert "详细验证结果" in report
        assert "统计信息" in report
    
    def test_validation_result_dataclass(self):
        """测试ValidationResult数据类"""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["警告1"],
            suggestions=["建议1"]
        )
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
        assert len(result.suggestions) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])