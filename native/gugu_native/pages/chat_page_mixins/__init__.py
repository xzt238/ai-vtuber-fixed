"""
ChatPage Mixin 模块

将 ChatPage 的功能拆分为多个 Mixin 类，提高代码可维护性。
"""

from .live2d_mixin import ChatPageLive2DMixin
from .audio_mixin import ChatPageAudioMixin
from .message_mixin import ChatPageMessageMixin
from .vision_mixin import ChatPageVisionMixin
from .tts_config_mixin import ChatPageTTSConfigMixin

__all__ = [
    'ChatPageLive2DMixin',
    'ChatPageAudioMixin', 
    'ChatPageMessageMixin',
    'ChatPageVisionMixin',
    'ChatPageTTSConfigMixin',
]
