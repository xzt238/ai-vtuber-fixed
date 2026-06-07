"""
直播平台统一接口

提供统一的直播平台接口，支持多平台扩展。

主要组件:
- LivePlatform: 直播平台基类
- BilibiliPlatform: Bilibili直播平台
- DouyinPlatform: 抖音直播平台
- KuaishouPlatform: 快手直播平台
- YouTubePlatform: YouTube直播平台
- TwitchPlatform: Twitch直播平台

作者: 咕咕嘎嘎
日期: 2026-06-03
"""

import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PlatformType(Enum):
    """平台类型枚举"""
    BILIBILI = "bilibili"
    DOUYIN = "douyin"
    KUAISHOU = "kuaishou"
    YOUTUBE = "youtube"
    TWITCH = "twitch"
    TIKTOK = "tiktok"
    HUYA = "huya"
    DOUYU = "douyu"
    WEIXIN_VIDEO = "weixin_video"


@dataclass
class DanmakuMessage:
    """弹幕消息"""
    platform: PlatformType
    user_id: str
    username: str
    content: str
    timestamp: datetime
    room_id: str
    extra: Dict[str, Any] = None
    
    def __post_init__(self) -> None:
        if self.extra is None:
            self.extra = {}


@dataclass
class GiftMessage:
    """礼物消息"""
    platform: PlatformType
    user_id: str
    username: str
    gift_name: str
    gift_count: int
    timestamp: datetime
    room_id: str
    extra: Dict[str, Any] = None
    
    def __post_init__(self) -> None:
        if self.extra is None:
            self.extra = {}


@dataclass
class SystemMessage:
    """系统消息"""
    platform: PlatformType
    message_type: str
    content: str
    timestamp: datetime
    room_id: str
    extra: Dict[str, Any] = None
    
    def __post_init__(self) -> None:
        if self.extra is None:
            self.extra = {}


class LivePlatform(ABC):
    """直播平台基类"""
    
    def __init__(self, config: Dict[str, Any] = None) -> None:
        self.config = config or {}
        self.platform_type = self._get_platform_type()
        self.connected = False
        self.room_id = None
        
        # 消息回调
        self._danmaku_callbacks: List[Callable] = []
        self._gift_callbacks: List[Callable] = []
        self._system_callbacks: List[Callable] = []
        
        # 统计信息
        self._stats = {
            "connected_at": None,
            "danmaku_count": 0,
            "gift_count": 0,
            "error_count": 0,
        }
    
    @abstractmethod
    def _get_platform_type(self) -> PlatformType:
        """获取平台类型"""
        pass
    
    @abstractmethod
    async def connect(self, room_id: str, **kwargs) -> bool:
        """连接到直播间"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass
    
    @abstractmethod
    async def send_danmaku(self, content: str) -> bool:
        """发送弹幕"""
        pass
    
    @abstractmethod
    async def _receive_messages(self) -> None:
        """接收消息（内部实现）"""
        pass
    
    def add_danmaku_callback(self, callback: Callable) -> None:
        """添加弹幕回调"""
        self._danmaku_callbacks.append(callback)
    
    def add_gift_callback(self, callback: Callable) -> None:
        """添加礼物回调"""
        self._gift_callbacks.append(callback)
    
    def add_system_callback(self, callback: Callable) -> None:
        """添加系统消息回调"""
        self._system_callbacks.append(callback)
    
    def remove_danmaku_callback(self, callback: Callable) -> None:
        """移除弹幕回调"""
        self._danmaku_callbacks = [cb for cb in self._danmaku_callbacks if cb != callback]
    
    def remove_gift_callback(self, callback: Callable) -> None:
        """移除礼物回调"""
        self._gift_callbacks = [cb for cb in self._gift_callbacks if cb != callback]
    
    def remove_system_callback(self, callback: Callable) -> None:
        """移除系统消息回调"""
        self._system_callbacks = [cb for cb in self._system_callbacks if cb != callback]
    
    def _notify_danmaku(self, message: DanmakuMessage) -> None:
        """通知弹幕回调"""
        self._stats["danmaku_count"] += 1
        for callback in self._danmaku_callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.info(f" 弹幕回调失败: {e}")
    
    def _notify_gift(self, message: GiftMessage) -> None:
        """通知礼物回调"""
        self._stats["gift_count"] += 1
        for callback in self._gift_callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.info(f" 礼物回调失败: {e}")
    
    def _notify_system(self, message: SystemMessage) -> None:
        """通知系统消息回调"""
        for callback in self._system_callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.info(f" 系统消息回调失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "platform": self.platform_type.value,
            "connected": self.connected,
            "room_id": self.room_id,
            "connected_at": self._stats["connected_at"].isoformat() if self._stats["connected_at"] else None,
            "danmaku_count": self._stats["danmaku_count"],
            "gift_count": self._stats["gift_count"],
            "error_count": self._stats["error_count"],
        }
    
    def is_connected(self) -> bool:
        """是否已连接"""
        return self.connected
    
    def get_room_id(self) -> Optional[str]:
        """获取房间ID"""
        return self.room_id


class LivePlatformFactory:
    """直播平台工厂"""
    
    _platforms: Dict[PlatformType, type] = {}
    
    @classmethod
    def register(cls, platform_type: PlatformType) -> None:
        """注册平台装饰器"""
        def decorator(platform_class) -> None:
            cls._platforms[platform_type] = platform_class
            return platform_class
        return decorator
    
    @classmethod
    def create(cls, platform_type: PlatformType, config: Dict[str, Any] = None) -> LivePlatform:
        """创建平台实例"""
        if platform_type not in cls._platforms:
            raise ValueError(f"未注册的平台类型: {platform_type}")
        
        platform_class = cls._platforms[platform_type]
        return platform_class(config)
    
    @classmethod
    def create_by_name(cls, platform_name: str, config: Dict[str, Any] = None) -> LivePlatform:
        """根据名称创建平台实例"""
        try:
            platform_type = PlatformType(platform_name)
            return cls.create(platform_type, config)
        except ValueError:
            raise ValueError(f"未知的平台名称: {platform_name}")
    
    @classmethod
    def get_supported_platforms(cls) -> List[PlatformType]:
        """获取支持的平台列表"""
        return list(cls._platforms.keys())
    
    @classmethod
    def get_platform_info(cls) -> List[Dict[str, Any]]:
        """获取平台信息列表"""
        return [
            {
                "type": platform_type.value,
                "name": platform_type.name,
                "class": platform_class.__name__,
            }
            for platform_type, platform_class in cls._platforms.items()
        ]


# 导出主要类
__all__ = [
    'PlatformType',
    'DanmakuMessage',
    'GiftMessage',
    'SystemMessage',
    'LivePlatform',
    'LivePlatformFactory',
]

# 导入所有平台实现（触发注册）
from .bilibili import BilibiliPlatform
from .douyin import DouyinPlatform
from .kuaishou import KuaishouPlatform
from .youtube import YouTubePlatform
from .twitch import TwitchPlatform