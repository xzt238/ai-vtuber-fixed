"""
TTS 缓存单元测试

测试缓存键生成、LRU 淘汰、过期清理。
"""

import pytest
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))


class TestTTSCache:
    """TTSCache 缓存测试"""

    @pytest.fixture
    def cache(self, tmp_path):
        """创建临时缓存实例"""
        from tts_cache import TTSCache
        return TTSCache(
            cache_dir=str(tmp_path / "tts_cache"),
            max_age_days=7,
            max_size_mb=10
        )

    def test_cache_key_generation(self, cache):
        """测试缓存键生成"""
        key1 = cache.get_cache_key("你好", "zh-CN-XiaoxiaoNeural", "edge")
        key2 = cache.get_cache_key("你好", "zh-CN-XiaoxiaoNeural", "edge")
        key3 = cache.get_cache_key("你好", "zh-CN-YunxiNeural", "edge")

        assert key1 == key2  # 相同输入应该生成相同键
        assert key1 != key3  # 不同输入应该生成不同键
        assert len(key1) == 32  # MD5 哈希长度

    def test_cache_miss(self, cache):
        """测试缓存未命中"""
        result = cache.get("不存在的文本", "voice", "provider")
        assert result is None

    def test_cache_set_and_get(self, cache, tmp_path):
        """测试缓存写入和读取"""
        # 创建一个假的音频文件
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        # 写入缓存
        cache.set("测试文本", "voice", "provider", str(audio_file))

        # 读取缓存
        result = cache.get("测试文本", "voice", "provider")
        assert result is not None
        assert Path(result).exists()

    def test_cache_different_voice(self, cache, tmp_path):
        """测试不同语音使用不同缓存"""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        cache.set("文本", "voice1", "provider", str(audio_file))
        cache.set("文本", "voice2", "provider", str(audio_file))

        result1 = cache.get("文本", "voice1", "provider")
        result2 = cache.get("文本", "voice2", "provider")

        # 两个缓存应该独立
        assert result1 is not None
        assert result2 is not None
