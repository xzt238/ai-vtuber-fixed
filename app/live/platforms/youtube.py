import logging
"""
YouTube直播平台实现

logger = logging.getLogger(__name__)

提供YouTube直播弹幕接收、发送等功能。

作者: 咕咕嘎嘎
日期: 2026-06-03
"""

import os
import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List
from datetime import datetime

from . import (
    PlatformType, LivePlatform, LivePlatformFactory,
    DanmakuMessage, GiftMessage, SystemMessage
)


@LivePlatformFactory.register(PlatformType.YOUTUBE)
class YouTubePlatform(LivePlatform):
    """YouTube直播平台"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # YouTube配置
        self.channel_id = self.config.get("channel_id", "")
        self.api_key = self.config.get("api_key", "")
        
        # HTTP会话
        self._session = None
        
        # 轮询任务
        self._poll_task = None
        
        # API基础URL
        self._api_base = "https://www.googleapis.com/youtube/v3"
        
        # 直播聊天ID
        self._live_chat_id = None
        self._next_page_token = None
    
    def _get_platform_type(self) -> PlatformType:
        return PlatformType.YOUTUBE
    
    async def connect(self, room_id: str, **kwargs) -> bool:
        """连接到YouTube直播间"""
        try:
            self.room_id = room_id
            
            # 获取直播聊天ID
            live_chat_id = await self._get_live_chat_id(room_id)
            if not live_chat_id:
                logger.info(f" 获取直播聊天ID失败: {room_id}")
                return False
            
            self._live_chat_id = live_chat_id
            self.connected = True
            self._stats["connected_at"] = datetime.now()
            
            logger.info(f" YouTube直播间连接成功: {room_id}")
            
            # 启动消息轮询
            self._poll_task = asyncio.create_task(self._poll_messages())
            
            return True
            
        except Exception as e:
            logger.info(f" YouTube连接失败: {e}")
            self._stats["error_count"] += 1
            return False
    
    async def disconnect(self):
        """断开连接"""
        try:
            # 停止轮询
            if self._poll_task:
                self._poll_task.cancel()
                try:
                    await self._poll_task
                except asyncio.CancelledError:
                    pass
            
            # 关闭会话
            if self._session:
                await self._session.close()
                self._session = None
            
            self.connected = False
            self.room_id = None
            self._live_chat_id = None
            self._next_page_token = None
            self._stats["connected_at"] = None
            
            logger.info(" YouTube直播间已断开")
            
        except Exception as e:
            logger.info(f" YouTube断开连接失败: {e}")
            self._stats["error_count"] += 1
    
    async def send_danmaku(self, content: str) -> bool:
        """发送弹幕"""
        try:
            if not self.connected or not self._live_chat_id:
                logger.info(" 未连接到直播间")
                return False
            
            # YouTube弹幕发送API
            logger.info(f" YouTube弹幕发送功能需要进一步实现: {content}")
            return False
            
        except Exception as e:
            logger.info(f" 弹幕发送失败: {e}")
            self._stats["error_count"] += 1
            return False
    
    async def _get_live_chat_id(self, video_id: str) -> Optional[str]:
        """获取直播聊天ID"""
        try:
            if not self._session:
                self._session = aiohttp.ClientSession()
            
            # 获取视频信息
            params = {
                "part": "liveStreamingDetails",
                "id": video_id,
                "key": self.api_key,
            }
            
            async with self._session.get(
                f"{self._api_base}/videos",
                params=params
            ) as response:
                result = await response.json()
                
                if "items" in result and len(result["items"]) > 0:
                    live_details = result["items"][0].get("liveStreamingDetails", {})
                    return live_details.get("activeLiveChatId")
                else:
                    logger.info(f" 获取视频信息失败: {result}")
                    return None
            
        except Exception as e:
            logger.info(f" 获取直播聊天ID失败: {e}")
            return None
    
    async def _receive_messages(self):
        """接收消息（实现抽象方法）"""
        # YouTube使用轮询方式，而不是WebSocket
        # 这个方法在connect中通过_poll_task调用
        pass
    
    async def _poll_messages(self):
        """轮询消息"""
        try:
            while self.connected:
                try:
                    # 获取聊天消息
                    messages = await self._get_chat_messages()
                    
                    # 处理消息
                    for message in messages:
                        await self._process_message(message)
                    
                    # 等待一段时间再轮询
                    await asyncio.sleep(5)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.info(f" 消息轮询失败: {e}")
                    self._stats["error_count"] += 1
                    await asyncio.sleep(10)
            
        except asyncio.CancelledError:
            pass
    
    async def _get_chat_messages(self) -> List[Dict[str, Any]]:
        """获取聊天消息"""
        try:
            if not self._session:
                self._session = aiohttp.ClientSession()
            
            params = {
                "part": "snippet,authorDetails",
                "liveChatId": self._live_chat_id,
                "key": self.api_key,
            }
            
            if self._next_page_token:
                params["pageToken"] = self._next_page_token
            
            async with self._session.get(
                f"{self._api_base}/liveChat/messages",
                params=params
            ) as response:
                result = await response.json()
                
                if "items" in result:
                    self._next_page_token = result.get("nextPageToken")
                    return result["items"]
                else:
                    logger.info(f" 获取聊天消息失败: {result}")
                    return []
            
        except Exception as e:
            logger.info(f" 获取聊天消息失败: {e}")
            return []
    
    async def _process_message(self, message: Dict[str, Any]):
        """处理消息"""
        try:
            snippet = message.get("snippet", {})
            author = message.get("authorDetails", {})
            
            message_type = snippet.get("type", "")
            
            if message_type == "textMessageEvent":
                # 文本消息
                danmaku = DanmakuMessage(
                    platform=PlatformType.YOUTUBE,
                    user_id=author.get("channelId", ""),
                    username=author.get("displayName", ""),
                    content=snippet.get("displayMessage", ""),
                    timestamp=datetime.now(),
                    room_id=self.room_id,
                    extra={"raw_message": message}
                )
                
                self._notify_danmaku(danmaku)
            
            elif message_type == "superChatEvent":
                # Super Chat
                gift_msg = GiftMessage(
                    platform=PlatformType.YOUTUBE,
                    user_id=author.get("channelId", ""),
                    username=author.get("displayName", ""),
                    gift_name="Super Chat",
                    gift_count=1,
                    timestamp=datetime.now(),
                    room_id=self.room_id,
                    extra={"raw_message": message}
                )
                
                self._notify_gift(gift_msg)
            
        except Exception as e:
            logger.info(f" 消息处理失败: {e}")
            self._stats["error_count"] += 1


# 导出主要类
__all__ = ['YouTubePlatform']