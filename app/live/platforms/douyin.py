"""
抖音直播平台实现

提供抖音直播弹幕接收、发送等功能。

作者: 咕咕嘎嘎
日期: 2026-06-03
"""

import os
import json
import asyncio
import aiohttp
import time
from typing import Optional, Dict, Any
from datetime import datetime

from . import (
    PlatformType, LivePlatform, LivePlatformFactory,
    DanmakuMessage, GiftMessage, SystemMessage
)
import logging

logger = logging.getLogger(__name__)


@LivePlatformFactory.register(PlatformType.DOUYIN)
class DouyinPlatform(LivePlatform):
    """抖音直播平台"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # 抖音配置
        self.cookie = self.config.get("cookie", "")
        
        # WebSocket连接
        self._ws = None
        self._ws_task = None
        
        # 心跳任务
        self._heartbeat_task = None
        
        # API基础URL
        self._api_base = "https://live.douyin.com"
    
    def _get_platform_type(self) -> PlatformType:
        return PlatformType.DOUYIN
    
    async def connect(self, room_id: str, **kwargs) -> bool:
        """连接到抖音直播间"""
        try:
            self.room_id = room_id
            
            # 获取直播间信息
            room_info = await self._get_room_info(room_id)
            if not room_info:
                logger.info(f" 获取直播间信息失败: {room_id}")
                return False
            
            # 获取WebSocket连接信息
            ws_info = await self._get_ws_info(room_id)
            if not ws_info:
                logger.info(f" 获取WebSocket信息失败: {room_id}")
                return False
            
            # 连接WebSocket
            success = await self._connect_websocket(ws_info)
            
            if success:
                self.connected = True
                self._stats["connected_at"] = datetime.now()
                logger.info(f" 抖音直播间连接成功: {room_id}")
                
                # 启动心跳
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                
                # 启动消息接收
                self._ws_task = asyncio.create_task(self._receive_messages())
            else:
                logger.info(f" 抖音直播间连接失败: {room_id}")
            
            return success
            
        except Exception as e:
            logger.info(f" 抖音连接失败: {e}")
            self._stats["error_count"] += 1
            return False
    
    async def disconnect(self):
        """断开连接"""
        try:
            # 停止心跳
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            # 停止消息接收
            if self._ws_task:
                self._ws_task.cancel()
                try:
                    await self._ws_task
                except asyncio.CancelledError:
                    pass
            
            # 关闭WebSocket
            if self._ws:
                await self._ws.close()
                self._ws = None
            
            self.connected = False
            self.room_id = None
            self._stats["connected_at"] = None
            
            logger.info(" 抖音直播间已断开")
            
        except Exception as e:
            logger.info(f" 抖音断开连接失败: {e}")
            self._stats["error_count"] += 1
    
    async def send_danmaku(self, content: str) -> bool:
        """发送弹幕"""
        try:
            if not self.connected or not self.room_id:
                logger.info(" 未连接到直播间")
                return False
            
            # 抖音弹幕发送API
            # 注意：抖音的弹幕发送需要特殊的认证和参数
            # 这里提供基本框架，实际实现需要根据抖音API调整
            
            logger.info(f" 抖音弹幕发送功能需要进一步实现: {content}")
            return False
            
        except Exception as e:
            logger.info(f" 弹幕发送失败: {e}")
            self._stats["error_count"] += 1
            return False
    
    async def _get_room_info(self, room_id: str) -> Optional[Dict[str, Any]]:
        """获取直播间信息"""
        try:
            # 抖音直播间信息获取
            # 注意：抖音的API可能需要特殊的认证和参数
            # 这里提供基本框架，实际实现需要根据抖音API调整
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Cookie": self.cookie,
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self._api_base}/web/room/room_info",
                    params={"room_id": room_id},
                    headers=headers
                ) as response:
                    result = await response.json()
                    
                    if result.get("status_code") == 0:
                        return result.get("data", {}).get("room_info")
                    else:
                        logger.info(f" 获取直播间信息失败: {result}")
                        return None
            
        except Exception as e:
            logger.info(f" 获取直播间信息失败: {e}")
            return None
    
    async def _get_ws_info(self, room_id: str) -> Optional[Dict[str, Any]]:
        """获取WebSocket连接信息"""
        try:
            # 抖音WebSocket连接信息获取
            # 注意：抖音的WebSocket连接需要特殊的参数和认证
            # 这里提供基本框架，实际实现需要根据抖音API调整
            
            return {
                "url": "wss://webcast5-ws-web-lf.douyin.com/webcast/im/push/v2/",
                "params": {
                    "app_name": "douyin_web",
                    "version_code": "180800",
                    "webcast_sdk_version": "1.0.14",
                    "update_version_code": "1.0.14",
                    "compress": "gzip",
                    "device_platform": "web",
                    "cookie_enabled": "true",
                    "screen_width": "1920",
                    "screen_height": "1080",
                    "browser_language": "zh-CN",
                    "browser_platform": "Win32",
                    "browser_name": "Chrome",
                    "browser_version": "120.0.0.0",
                    "browser_online": "true",
                    "room_id": room_id,
                }
            }
            
        except Exception as e:
            logger.info(f" 获取WebSocket信息失败: {e}")
            return None
    
    async def _connect_websocket(self, ws_info: Dict[str, Any]) -> bool:
        """连接WebSocket"""
        try:
            import websockets
            
            url = ws_info.get("url")
            params = ws_info.get("params", {})
            
            # 构建URL
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            uri = f"{url}?{query_string}"
            
            # 连接WebSocket
            self._ws = await websockets.connect(uri)
            
            logger.info(f" 抖音WebSocket连接成功")
            return True
            
        except ImportError:
            logger.info(" 未安装websockets库，请执行: pip install websockets")
            return False
        except Exception as e:
            logger.info(f" 抖音WebSocket连接失败: {e}")
            return False
    
    async def _receive_messages(self):
        """接收消息"""
        try:
            async for message in self._ws:
                try:
                    # 解析消息
                    if isinstance(message, bytes):
                        # 抖音消息可能是二进制格式
                        # 需要根据实际情况解码
                        message = message.decode("utf-8", errors="ignore")
                    
                    # 解析JSON
                    data = json.loads(message)
                    
                    # 处理消息
                    await self._process_message(data)
                    
                except Exception as e:
                    logger.info(f" 消息解析失败: {e}")
                    self._stats["error_count"] += 1
            
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.info(f" 消息接收失败: {e}")
            self._stats["error_count"] += 1
    
    async def _process_message(self, data: Dict[str, Any]):
        """处理消息"""
        try:
            # 抖音消息处理
            # 注意：抖音的消息格式可能与Bilibili不同
            # 这里提供基本框架，实际实现需要根据抖音API调整
            
            method = data.get("method", "")
            
            if method == "WebcastChatMessage":
                # 弹幕消息
                payload = data.get("payload", {})
                user = payload.get("user", {})
                content = payload.get("content", "")
                
                danmaku = DanmakuMessage(
                    platform=PlatformType.DOUYIN,
                    user_id=str(user.get("id", "")),
                    username=user.get("nickname", ""),
                    content=content,
                    timestamp=datetime.now(),
                    room_id=self.room_id,
                    extra={"raw_data": data}
                )
                
                self._notify_danmaku(danmaku)
            
            elif method == "WebcastGiftMessage":
                # 礼物消息
                payload = data.get("payload", {})
                user = payload.get("user", {})
                gift = payload.get("gift", {})
                
                gift_msg = GiftMessage(
                    platform=PlatformType.DOUYIN,
                    user_id=str(user.get("id", "")),
                    username=user.get("nickname", ""),
                    gift_name=gift.get("name", ""),
                    gift_count=payload.get("repeat_count", 1),
                    timestamp=datetime.now(),
                    room_id=self.room_id,
                    extra={"raw_data": data}
                )
                
                self._notify_gift(gift_msg)
            
            elif method in ["WebcastRoomMessage", "WebcastSystemMessage"]:
                # 系统消息
                system_msg = SystemMessage(
                    platform=PlatformType.DOUYIN,
                    message_type=method,
                    content=json.dumps(data, ensure_ascii=False),
                    timestamp=datetime.now(),
                    room_id=self.room_id,
                    extra={"raw_data": data}
                )
                
                self._notify_system(system_msg)
            
        except Exception as e:
            logger.info(f" 消息处理失败: {e}")
            self._stats["error_count"] += 1
    
    async def _heartbeat_loop(self):
        """心跳循环"""
        try:
            while self.connected:
                try:
                    # 发送心跳包
                    heartbeat_msg = json.dumps({"method": "heartbeat"})
                    await self._ws.send(heartbeat_msg)
                    
                    # 等待30秒
                    await asyncio.sleep(30)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.info(f" 心跳发送失败: {e}")
                    self._stats["error_count"] += 1
                    await asyncio.sleep(5)
            
        except asyncio.CancelledError:
            pass


# 导出主要类
__all__ = ['DouyinPlatform']