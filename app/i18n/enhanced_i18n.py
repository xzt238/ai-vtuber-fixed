import logging
"""
增强版国际化模块
支持多语言、动态翻译、语言包管理
"""

logger = logging.getLogger(__name__)

import os
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

class Language(Enum):
    """支持的语言"""
    ZH_CN = "zh-CN"  # 简体中文
    ZH_TW = "zh-TW"  # 繁体中文
    EN_US = "en-US"  # 美式英语
    EN_GB = "en-GB"  # 英式英语
    JA_JP = "ja-JP"  # 日语
    KO_KR = "ko-KR"  # 韩语
    FR_FR = "fr-FR"  # 法语
    DE_DE = "de-DE"  # 德语
    ES_ES = "es-ES"  # 西班牙语
    PT_BR = "pt-BR"  # 葡萄牙语
    RU_RU = "ru-RU"  # 俄语
    AR_SA = "ar-SA"  # 阿拉伯语

@dataclass
class TranslationEntry:
    """翻译条目"""
    key: str
    translations: Dict[str, str]  # language_code -> translation
    context: str = ""
    description: str = ""

class I18nManager:
    """国际化管理器"""
    
    def __init__(self, storage_dir: str = "./i18n"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 当前语言
        self.current_language = Language.ZH_CN
        
        # 翻译字典
        self.translations: Dict[str, Dict[str, str]] = {}
        
        # 语言包文件
        self.language_files: Dict[str, Path] = {}
        
        # 加载所有语言包
        self._load_language_packages()
        
        logger.info(f"[I18n] 初始化完成，当前语言: {self.current_language.value}")
    
    def _load_language_packages(self):
        """加载语言包"""
        try:
            # 扫描语言包文件
            for file_path in self.storage_dir.glob("*.json"):
                lang_code = file_path.stem
                self.language_files[lang_code] = file_path
                
                # 加载翻译
                with open(file_path, "r", encoding="utf-8") as f:
                    translations = json.load(f)
                    self.translations[lang_code] = translations
            
            logger.info(f"[I18n] 加载了 {len(self.language_files)} 个语言包")
            
        except Exception as e:
            logger.info(f"[I18n] 加载语言包失败: {e}")
    
    def set_language(self, language: Language):
        """设置当前语言"""
        self.current_language = language
        logger.info(f"[I18n] 切换语言: {language.value}")
    
    def get_text(self, key: str, **kwargs) -> str:
        """获取翻译文本"""
        lang_code = self.current_language.value
        
        # 查找翻译
        if lang_code in self.translations:
            text = self.translations[lang_code].get(key)
            if text:
                # 替换变量
                if kwargs:
                    text = text.format(**kwargs)
                return text
        
        # 回退到简体中文
        if "zh-CN" in self.translations:
            text = self.translations["zh-CN"].get(key)
            if text:
                if kwargs:
                    text = text.format(**kwargs)
                return text
        
        # 返回key本身
        return key
    
    def add_translation(self, key: str, translations: Dict[str, str]):
        """添加翻译"""
        for lang_code, text in translations.items():
            if lang_code not in self.translations:
                self.translations[lang_code] = {}
            self.translations[lang_code][key] = text
        
        # 保存到文件
        self._save_translations()
    
    def _save_translations(self):
        """保存翻译到文件"""
        try:
            for lang_code, translations in self.translations.items():
                file_path = self.storage_dir / f"{lang_code}.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(translations, f, ensure_ascii=False, indent=2)
            
            logger.info("[I18n] 翻译已保存")
            
        except Exception as e:
            logger.info(f"[I18n] 保存翻译失败: {e}")
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """获取支持的语言列表"""
        languages = []
        for lang in Language:
            languages.append({
                "code": lang.value,
                "name": self._get_language_name(lang),
                "native_name": self._get_native_name(lang)
            })
        return languages
    
    def _get_language_name(self, language: Language) -> str:
        """获取语言英文名称"""
        names = {
            Language.ZH_CN: "Chinese (Simplified)",
            Language.ZH_TW: "Chinese (Traditional)",
            Language.EN_US: "English (US)",
            Language.EN_GB: "English (UK)",
            Language.JA_JP: "Japanese",
            Language.KO_KR: "Korean",
            Language.FR_FR: "French",
            Language.DE_DE: "German",
            Language.ES_ES: "Spanish",
            Language.PT_BR: "Portuguese",
            Language.RU_RU: "Russian",
            Language.AR_SA: "Arabic"
        }
        return names.get(language, language.value)
    
    def _get_native_name(self, language: Language) -> str:
        """获取语言本地名称"""
        names = {
            Language.ZH_CN: "简体中文",
            Language.ZH_TW: "繁體中文",
            Language.EN_US: "English",
            Language.EN_GB: "English",
            Language.JA_JP: "日本語",
            Language.KO_KR: "한국어",
            Language.FR_FR: "Français",
            Language.DE_DE: "Deutsch",
            Language.ES_ES: "Español",
            Language.PT_BR: "Português",
            Language.RU_RU: "Русский",
            Language.AR_SA: "العربية"
        }
        return names.get(language, language.value)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "current_language": self.current_language.value,
            "supported_languages": len(Language),
            "loaded_language_packages": len(self.language_files),
            "total_translations": sum(len(t) for t in self.translations.values())
        }

# 全局实例
_i18n_manager: Optional[I18nManager] = None

def get_i18n_manager(storage_dir: str = None) -> I18nManager:
    """获取国际化管理器实例"""
    global _i18n_manager
    if _i18n_manager is None:
        _i18n_manager = I18nManager(storage_dir or "./i18n")
    return _i18n_manager

# 便捷函数
def t(key: str, **kwargs) -> str:
    """翻译便捷函数"""
    manager = get_i18n_manager()
    return manager.get_text(key, **kwargs)
