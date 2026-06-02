"""
咕咕嘎嘎 AI VTuber — pytest 配置

提供共享的测试 fixtures 和工具函数。
"""

import os
import sys
import pytest
from pathlib import Path

# 添加项目路径
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "app"))
sys.path.insert(0, str(PROJECT_DIR / "native"))


@pytest.fixture
def project_dir():
    """项目根目录"""
    return PROJECT_DIR


@pytest.fixture
def app_dir():
    """app 目录"""
    return PROJECT_DIR / "app"


@pytest.fixture
def config_dir():
    """配置目录"""
    return PROJECT_DIR / "app" / "cache"


@pytest.fixture
def sample_config():
    """示例配置字典"""
    return {
        "llm": {
            "provider": "deepseek",
            "deepseek": {
                "api_key": "test-key",
                "model": "deepseek-chat"
            }
        },
        "tts": {
            "provider": "edge",
            "edge": {
                "voice": "zh-CN-XiaoxiaoNeural"
            }
        },
        "asr": {
            "provider": "funasr",
            "funasr": {
                "model": "paraformer-zh"
            }
        },
        "memory": {
            "enabled": True,
            "max_working_memory": 30
        },
        "web": {
            "port": 12393,
            "ws_port": 12394
        }
    }


@pytest.fixture
def sample_history():
    """示例对话历史"""
    return [
        {"role": "user", "content": "你好", "time": "2026-01-01T00:00:00"},
        {"role": "assistant", "content": "你好！我是咕咕嘎嘎，有什么可以帮你的吗？", "time": "2026-01-01T00:00:01"},
        {"role": "user", "content": "今天天气怎么样？", "time": "2026-01-01T00:01:00"},
        {"role": "assistant", "content": "抱歉，我暂时无法查询实时天气信息。", "time": "2026-01-01T00:01:01"},
    ]


@pytest.fixture
def tmp_cache(tmp_path):
    """临时缓存目录"""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir
