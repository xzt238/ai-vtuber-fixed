import logging
"""
Twitch直播平台实现

logger = logging.getLogger(__name__)

提供Twitch直播弹幕接收、发送等功能。

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


@LivePlatformFactory.register(PlatformType.TWITCH)
class TwitchPlatform(LivePlatform):
    """Twitch直播平台"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # Twitch配置
        self.channel = self.config.get("channel", "")
        self.oauth_token = self.config.get("oauth_token", "")
        
        # WebSocket连接
        self._ws = None
        self._ws_task = None
        
        # 心跳任务
        self._heartbeat_task = None
        
        # IRC服务器
        self._irc_server = "irc.chat.twitch.tv"
        self._irc_port = 6667
    
    def _get_platform_type(self) -> PlatformType:
        return PlatformType.TWITCH
    
    async def connect(self, room_id: str, **kwargs) -> bool:
        """连接到Twitch直播间"""
        try:
            self.room_id = room_id
            self.channel = room_id
            
            # 连接IRC服务器
            success = await self._connect_irc()
            
            if success:
                self.connected = True
                self._stats["connected_at"] = datetime.now()
                logger.info(f" Twitch直播间连接成功: {room_id}")
                
                # 启动消息接收
                self._ws_task = asyncio.create_task(self._receive_messages())
            else:
                logger.info(f" Twitch直播间连接失败: {room_id}")
            
            return success
            
        except Exception as e:
            logger.info(f" Twitch连接失败: {e}")
            self._stats["error_count"] += 1
            return False
    
    async def disconnect(self):
        """断开连接"""
        try:
            # 停止消息接收
            if self._ws_task:
                self._ws_task.cancel()
                try:
                    await self._ws_task
                except asyncio.CancelledError:
                    pass
            
            # 关闭连接
            if self._ws:
                self._ws.close()
                self._ws = None
            
            self.connected = False
            self.room_id = None
            self._stats["connected_at"] = None
            
            logger.info(" Twitch直播间已断开")
            
        except Exception as e:
            logger.info(f" Twitch断开连接失败: {e}")
            self._stats["error_count"] += 1
    
    async def send_danmaku(self, content: str) -> bool:
        """发送弹幕"""
        try:
            if not self.connected or not self._ws:
                logger.info(" 未连接到直播间")
                return False
            
            # 发送IRC消息
            message = f"PRIVMSG #{self.channel} :{content}\r\n"
            self._ws.send(message)
            
            logger.info(f" 弹幕发送成功: {content}")
            return True
            
        except Exception as e:
            logger.info(f" 弹幕发送失败: {e}")
            self._stats["error_count"] += 1
            return False
    
    async def _connect_irc(self) -> bool:
        """连接IRC服务器"""
        try:
            import socket
            
            # 创建TCP连接
            self._ws = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._ws.connect((self._irc_server, self._irc_port))
            
            # 发送认证
            self._ws.send(f"PASS {self.oauth_token}\r\n".encode())
            self._ws.send(f"NICK {self.channel}\r\n".encode())
            self._ws.send(f"JOIN #{self.channel}\r\n".encode())
            
            logger.info(f" Twitch IRC连接成功")
            return True
            
        except Exception as e:
            logger.info(f" Twitch IRC连接失败: {e}")
            return False
    
    async def _receive_messages(self):
        """接收消息"""
        try:
            while self.connected:
                try:
                    # 接收数据
                    data = self._ws.recv(4096).decode("utf-8", errors="ignore")
                    
                    if not data:
                        continue
                    
                    # 处理消息
                    for line in data.split("\r\n"):
                        if line:
                            await self._process_message(line)
                    
                    # 响应PING
                    if "PING" in data:
                        self._ws.send("PONG :tmi.twitch.tv\r\n".encode())
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.info(f" 消息接收失败: {e}")
                    self._stats["error_count"] += 1
                    await asyncio.sleep(1)
            
        except asyncio.CancelledError:
            pass
    
    async def _process_message(self, message: str):
        """处理消息"""
        try:
            # 解析IRC消息
            if "PRIVMSG" in message:
                # 提取用户名和内容
                parts = message.split("!")
                if len(parts) > 1:
                    username = parts[0].split(":")[1]
                    
                    content_parts = message.split("PRIVMSG")
                    if len(content_parts) > 1:
                        content = content_parts[1].split(":")[1]
                        
                        danmaku = DanmakuMessage(
                            platform=PlatformType.TWITCH,
                            user_id=username,
                            username=username,
                            content=content,
                            timestamp=datetime.now(),
                            room_id=self.room_id,
                            extra={"raw_message": message}
                        )
                        
                        self._notify_danmaku(danmaku)
            
        except Exception as e:
            logger.info(f" 消息处理失败: {e}")
            self._stats["error_count"] += 1


# 导出主要类
__all__ = ['TwitchPlatform']