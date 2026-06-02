"""
版本管理单元测试

测试版本号一致性和格式。
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))


class TestVersion:
    """版本号测试"""

    def test_version_format(self):
        """测试版本号格式为 x.y.z"""
        from version import __version__
        parts = __version__.split(".")
        assert len(parts) == 3, f"Version should be x.y.z, got {__version__}"
        for part in parts:
            assert part.isdigit(), f"Version part should be numeric, got {part}"

    def test_version_accessible(self):
        """测试版本号可访问"""
        from version import VERSION, __version__
        assert VERSION == __version__
        assert len(VERSION) > 0

    def test_version_is_recent(self):
        """测试版本号是 1.12.x 或更高"""
        from version import __version__
        major, minor, patch = __version__.split(".")
        assert int(major) >= 1
        assert int(minor) >= 12  # 当前应该是 1.12.x
