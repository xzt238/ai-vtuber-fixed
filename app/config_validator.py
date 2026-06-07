"""
配置验证模块

提供配置验证、错误检查和配置优化功能。
"""

import os
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """配置验证错误"""
    pass


class ConfigType(Enum):
    """配置类型枚举"""
    PROVIDER = "provider"
    VOICE = "voice"
    EXPRESSION = "expression"
    PORT = "port"
    PATH = "path"


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self):
        self.validation_rules = {
            ConfigType.PROVIDER: self._validate_provider_config,
            ConfigType.VOICE: self._validate_voice_config,
            ConfigType.EXPRESSION: self._validate_expression_config,
            ConfigType.PORT: self._validate_port_config,
            ConfigType.PATH: self._validate_path_config,
        }
    
    def validate_config(self, config_data: Dict[str, Any], config_type: ConfigType) -> ValidationResult:
        """验证配置数据"""
        errors = []
        warnings = []
        suggestions = []
        
        try:
            # 获取验证函数
            validator = self.validation_rules.get(config_type)
            if validator:
                validation_result = validator(config_data)
                errors.extend(validation_result.get('errors', []))
                warnings.extend(validation_result.get('warnings', []))
                suggestions.extend(validation_result.get('suggestions', []))
            else:
                errors.append(f"未知的配置类型: {config_type}")
        
        except Exception as e:
            errors.append(f"配置验证失败: {str(e)}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _validate_provider_config(self, config: Dict[str, Any]) -> Dict[str, List[str]]:
        """验证LLM Provider配置"""
        errors = []
        warnings = []
        suggestions = []
        
        required_fields = ['label', 'baseUrl', 'models', 'defaultModel']
        
        for provider_name, provider_config in config.items():
            # 检查必需字段
            for field in required_fields:
                if field not in provider_config:
                    errors.append(f"Provider '{provider_name}' 缺少必需字段: {field}")
            
            # 检查baseUrl格式
            base_url = provider_config.get('baseUrl', '')
            if base_url and not base_url.startswith(('http://', 'https://')):
                warnings.append(f"Provider '{provider_name}' 的 baseUrl 可能格式不正确: {base_url}")
            
            # 检查models列表
            models = provider_config.get('models', [])
            if not models:
                warnings.append(f"Provider '{provider_name}' 没有配置模型列表")
            
            # 检查defaultModel是否在models列表中
            default_model = provider_config.get('defaultModel', '')
            if default_model and default_model not in models:
                warnings.append(f"Provider '{provider_name}' 的默认模型 '{default_model}' 不在模型列表中")
            
            # 检查hint字段
            if 'hint' not in provider_config:
                suggestions.append(f"Provider '{provider_name}' 建议添加 hint 字段，提供使用提示")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'suggestions': suggestions
        }
    
    def _validate_voice_config(self, config: List[tuple]) -> Dict[str, List[str]]:
        """验证语音配置"""
        errors = []
        warnings = []
        suggestions = []
        
        if not config:
            errors.append("语音配置列表为空")
            return {'errors': errors, 'warnings': warnings, 'suggestions': suggestions}
        
        for i, voice_item in enumerate(config):
            if not isinstance(voice_item, tuple) or len(voice_item) != 2:
                errors.append(f"语音配置项 {i} 格式错误，应为 (voice_id, label) 元组")
                continue
            
            voice_id, label = voice_item
            
            # 检查voice_id格式
            if not voice_id or not isinstance(voice_id, str):
                errors.append(f"语音配置项 {i} 的 voice_id 无效")
            
            # 检查label
            if not label or not isinstance(label, str):
                warnings.append(f"语音配置项 {i} 的 label 为空或无效")
            
            # 检查voice_id格式（应该包含语言代码）
            if voice_id and '-' not in voice_id:
                suggestions.append(f"语音配置项 {i} 的 voice_id '{voice_id}' 可能缺少语言代码")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'suggestions': suggestions
        }
    
    def _validate_expression_config(self, config: Dict[str, Any]) -> Dict[str, List[str]]:
        """验证表情配置"""
        errors = []
        warnings = []
        suggestions = []
        
        # 检查EXPRESSION_KEYWORDS
        if 'keywords' in config:
            keywords = config['keywords']
            if not isinstance(keywords, dict):
                errors.append("表情关键词配置应为字典类型")
            else:
                for emotion, words in keywords.items():
                    if not isinstance(words, list):
                        errors.append(f"表情 '{emotion}' 的关键词应为列表类型")
                    elif not words:
                        warnings.append(f"表情 '{emotion}' 没有配置关键词")
        
        # 检查EXPRESSION_MAP
        if 'map' in config:
            expression_map = config['map']
            if not isinstance(expression_map, dict):
                errors.append("表情映射配置应为字典类型")
            else:
                for emotion, expression_id in expression_map.items():
                    if not expression_id:
                        warnings.append(f"表情 '{emotion}' 没有映射到表情ID")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'suggestions': suggestions
        }
    
    def _validate_port_config(self, config: Dict[str, Any]) -> Dict[str, List[str]]:
        """验证端口配置"""
        errors = []
        warnings = []
        suggestions = []
        
        http_port = config.get('HTTP_PORT')
        ws_port = config.get('WS_PORT')
        
        # 检查端口范围
        if http_port and not (1024 <= http_port <= 65535):
            errors.append(f"HTTP端口 {http_port} 不在有效范围内 (1024-65535)")
        
        if ws_port and not (1024 <= ws_port <= 65535):
            errors.append(f"WebSocket端口 {ws_port} 不在有效范围内 (1024-65535)")
        
        # 检查端口冲突
        if http_port and ws_port and http_port == ws_port:
            errors.append("HTTP端口和WebSocket端口不能相同")
        
        # 检查常用端口
        common_ports = [80, 443, 8080, 8443, 3000, 5000]
        if http_port in common_ports:
            warnings.append(f"HTTP端口 {http_port} 是常用端口，可能与其他服务冲突")
        
        if ws_port in common_ports:
            warnings.append(f"WebSocket端口 {ws_port} 是常用端口，可能与其他服务冲突")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'suggestions': suggestions
        }
    
    def _validate_path_config(self, config: Dict[str, Any]) -> Dict[str, List[str]]:
        """验证路径配置"""
        errors = []
        warnings = []
        suggestions = []
        
        for path_name, path_value in config.items():
            if not isinstance(path_value, str):
                errors.append(f"路径 '{path_name}' 应为字符串类型")
                continue
            
            # 检查路径是否存在
            if path_value and not os.path.exists(path_value):
                warnings.append(f"路径 '{path_name}' 不存在: {path_value}")
            
            # 检查路径权限
            if path_value and os.path.exists(path_value):
                if not os.access(path_value, os.R_OK):
                    errors.append(f"路径 '{path_name}' 没有读取权限: {path_value}")
                if not os.access(path_value, os.W_OK):
                    warnings.append(f"路径 '{path_name}' 没有写入权限: {path_value}")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'suggestions': suggestions
        }
    
    def validate_all_configs(self) -> Dict[str, ValidationResult]:
        """验证所有配置"""
        results = {}
        
        try:
            # 导入配置模块
            from app.shared_config import (
                PROVIDER_CONFIG, EDGE_VOICES, 
                EXPRESSION_KEYWORDS, EXPRESSION_MAP,
                HTTP_PORT, WS_PORT, PROJECT_DIR
            )
            
            # 验证Provider配置
            results['provider'] = self.validate_config(
                PROVIDER_CONFIG, ConfigType.PROVIDER
            )
            
            # 验证语音配置
            results['voice'] = self.validate_config(
                EDGE_VOICES, ConfigType.VOICE
            )
            
            # 验证表情配置
            expression_config = {
                'keywords': EXPRESSION_KEYWORDS,
                'map': EXPRESSION_MAP
            }
            results['expression'] = self.validate_config(
                expression_config, ConfigType.EXPRESSION
            )
            
            # 验证端口配置
            port_config = {
                'HTTP_PORT': HTTP_PORT,
                'WS_PORT': WS_PORT
            }
            results['port'] = self.validate_config(
                port_config, ConfigType.PORT
            )
            
            # 验证路径配置
            path_config = {
                'PROJECT_DIR': PROJECT_DIR,
                'CONFIG_DIR': os.path.join(PROJECT_DIR, 'app'),
                'CACHE_DIR': os.path.join(PROJECT_DIR, 'app', 'cache'),
            }
            results['path'] = self.validate_config(
                path_config, ConfigType.PATH
            )
            
        except Exception as e:
            results['import_error'] = ValidationResult(
                is_valid=False,
                errors=[f"导入配置模块失败: {str(e)}"],
                warnings=[],
                suggestions=[]
            )
        
        return results
    
    def generate_validation_report(self) -> str:
        """生成验证报告"""
        results = self.validate_all_configs()
        
        report_lines = [
            "# 配置验证报告",
            "",
            f"**验证时间**: {__import__('datetime').datetime.now().isoformat()}",
            "",
            "## 验证结果摘要",
            "",
        ]
        
        total_errors = 0
        total_warnings = 0
        total_suggestions = 0
        
        for config_name, result in results.items():
            total_errors += len(result.errors)
            total_warnings += len(result.warnings)
            total_suggestions += len(result.suggestions)
            
            status = "✅ 通过" if result.is_valid else "❌ 失败"
            report_lines.append(f"- **{config_name}**: {status}")
        
        report_lines.extend([
            "",
            "## 详细验证结果",
            "",
        ])
        
        for config_name, result in results.items():
            report_lines.extend([
                f"### {config_name}",
                "",
            ])
            
            if result.errors:
                report_lines.append("**错误**:")
                for error in result.errors:
                    report_lines.append(f"- ❌ {error}")
                report_lines.append("")
            
            if result.warnings:
                report_lines.append("**警告**:")
                for warning in result.warnings:
                    report_lines.append(f"- ⚠️ {warning}")
                report_lines.append("")
            
            if result.suggestions:
                report_lines.append("**建议**:")
                for suggestion in result.suggestions:
                    report_lines.append(f"- 💡 {suggestion}")
                report_lines.append("")
        
        report_lines.extend([
            "## 统计信息",
            "",
            f"- **总错误数**: {total_errors}",
            f"- **总警告数**: {total_warnings}",
            f"- **总建议数**: {total_suggestions}",
            "",
            "## 建议操作",
            "",
        ])
        
        if total_errors > 0:
            report_lines.append("1. **立即修复错误** - 错误可能导致系统无法正常运行")
        
        if total_warnings > 0:
            report_lines.append("2. **检查警告** - 警告可能影响系统稳定性")
        
        if total_suggestions > 0:
            report_lines.append("3. **考虑建议** - 建议可以提高系统质量")
        
        if total_errors == 0 and total_warnings == 0:
            report_lines.append("✅ 所有配置验证通过，无需立即操作")
        
        return "\n".join(report_lines)


# 全局配置验证器实例
config_validator = ConfigValidator()


def validate_config() -> ValidationResult:
    """验证配置的便捷函数"""
    return config_validator.validate_all_configs()


def generate_validation_report() -> str:
    """生成验证报告的便捷函数"""
    return config_validator.generate_validation_report()


if __name__ == "__main__":
    # 测试配置验证
    logger.info("开始配置验证...")
    report = generate_validation_report()
    logger.info(report)
    logger.info("配置验证完成")