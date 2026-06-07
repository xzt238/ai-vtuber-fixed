"""
=====================================
国际化 (i18n) 模块
=====================================

支持中英文切换，基于 JSON 语言文件。

用法：
    from i18n import t, set_language, get_language

    # 获取翻译
    greeting = t("hello")  # "你好" 或 "Hello"

    # 切换语言
    set_language("en")

语言文件位置：
    app/i18n/zh_CN.json
    app/i18n/en_US.json

作者: 咕咕嘎嘎
日期: 2026-06-02
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

# 当前语言
_current_language = "zh_CN"

# 语言包缓存
_translations: Dict[str, Dict[str, str]] = {}

# 语言文件目录
_i18n_dir = Path(__file__).parent


def _load_language(lang: str) -> Dict[str, str]:
    """加载语言文件"""
    if lang in _translations:
        return _translations[lang]

    lang_file = _i18n_dir / f"{lang}.json"
    if not lang_file.exists():
        logger.warning(f"语言文件不存在: {lang_file}")
        return {}

    try:
        with open(lang_file, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        _translations[lang] = translations
        return translations
    except Exception as e:
        logger.error(f"加载语言文件失败: {e}")
        return {}


def set_language(lang: str) -> None:
    """设置当前语言

    Args:
        lang: 语言代码，如 "zh_CN", "en_US"
    """
    global _current_language
    _current_language = lang
    # 预加载语言文件
    _load_language(lang)
    logger.info(f"语言已切换为: {lang}")


def get_language() -> str:
    """获取当前语言"""
    return _current_language


def t(key: str, **kwargs) -> str:
    """获取翻译文本

    Args:
        key: 翻译键
        **kwargs: 格式化参数

    Returns:
        翻译后的文本，如果找不到则返回 key 本身

    Example:
        t("hello")  # "你好"
        t("greeting", name="小明")  # "你好，小明！"
    """
    translations = _load_language(_current_language)
    text = translations.get(key)

    if text is None:
        # 尝试加载英文作为 fallback
        if _current_language != "en_US":
            en_translations = _load_language("en_US")
            text = en_translations.get(key)

    if text is None:
        # 都找不到，返回 key 本身
        return key

    # 格式化参数
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text

    return text


def get_available_languages() -> list:
    """获取可用语言列表"""
    languages = []
    for f in _i18n_dir.glob("*.json"):
        lang = f.stem
        languages.append({
            "code": lang,
            "name": _get_language_name(lang)
        })
    return languages


def _get_language_name(lang_code: str) -> str:
    """获取语言显示名称"""
    names = {
        "zh_CN": "简体中文",
        "en_US": "English",
        "ja_JP": "日本語",
        "ko_KR": "한국어",
    }
    return names.get(lang_code, lang_code)
