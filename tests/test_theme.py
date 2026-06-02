"""
主题系统单元测试

测试 QSS 生成、主题切换、缓存机制。
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "native"))


class TestThemeQSS:
    """QSS 生成测试"""

    def test_get_colors_returns_valid(self):
        """测试 get_colors 返回有效颜色"""
        from gugu_native.theme import get_colors
        c = get_colors()

        assert c.window_bg is not None
        assert c.window_bg.startswith("#")
        assert len(c.window_bg) == 7  # #RRGGBB

    def test_build_qss_v5_no_missing_vars(self):
        """测试 QSS 模板没有未解析变量"""
        from gugu_native.theme import build_global_qss_v5
        qss = build_global_qss_v5()

        # 检查没有未解析的变量
        assert "%(" not in qss, "QSS contains unresolved variables"
        assert len(qss) > 100, "QSS is too short"

    def test_qss_contains_expected_selectors(self):
        """测试 QSS 包含预期的选择器"""
        from gugu_native.theme import build_global_qss_v5
        qss = build_global_qss_v5()

        assert "QWidget" in qss
        assert "QLabel" in qss
        assert "QLineEdit" in qss

    def test_qss_cache(self):
        """测试 QSS 缓存机制"""
        from gugu_native.theme import get_global_qss, clear_qss_cache, _qss_cache

        clear_qss_cache()
        assert len(_qss_cache) == 0

        qss1 = get_global_qss()
        assert len(_qss_cache) > 0

        qss2 = get_global_qss()
        assert qss1 == qss2  # 缓存命中，结果相同

        clear_qss_cache()
        assert len(_qss_cache) == 0


class TestAppColors:
    """AppColors 数据类测试"""

    def test_default_colors(self):
        """测试默认颜色值"""
        from gugu_native.theme import AppColors
        c = AppColors()

        assert c.window_bg == "#1a1b2e"
        assert c.text_primary == "#e8e8f0"
        assert c.accent == "#4263eb"

    def test_color_format(self):
        """测试颜色格式正确"""
        from gugu_native.theme import AppColors
        c = AppColors()

        for attr in ['window_bg', 'card_bg', 'text_primary', 'accent']:
            color = getattr(c, attr)
            assert color.startswith("#"), f"{attr} should start with #"
            assert len(color) == 7, f"{attr} should be #RRGGBB format"
