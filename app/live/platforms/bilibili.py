"""
Bilibili直播平台实现

提供Bilibili直播弹幕接收、发送等功能。

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


@LivePlatformFactory.register(PlatformType.BILIBILI)
class BilibiliPlatform(LivePlatform):
    """Bilibili直播平台"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # Bilibili配置
        self.uid = self.config.get("uid", 0)
        self.token = self.config.get("token", "")
        
        # WebSocket连接
        self._ws = None
        self._ws_task = None
        
        # 心跳任务
        self._heartbeat_task = None
        
        # API基础URL
        self._api_base = "https://api.live.bilibili.com"
    
    def _get_platform_type(self) -> PlatformType:
        return PlatformType.BILIBILI
    
    async def connect(self, room_id: str, **kwargs) -> bool:
        """连接到Bilibili直播间"""
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
                logger.info(f" Bilibili直播间连接成功: {room_id}")
                
                # 启动心跳
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                
                # 启动消息接收
                self._ws_task = asyncio.create_task(self._receive_messages())
            else:
                logger.info(f" Bilibili直播间连接失败: {room_id}")
            
            return success
            
        except Exception as e:
            logger.info(f" Bilibili连接失败: {e}")
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
            
            logger.info(" Bilibili直播间已断开")
            
        except Exception as e:
            logger.info(f" Bilibili断开连接失败: {e}")
            self._stats["error_count"] += 1
    
    async def send_danmaku(self, content: str) -> bool:
        """发送弹幕"""
        try:
            if not self.connected or not self.room_id:
                logger.info(" 未连接到直播间")
                return False
            
            # 构建请求数据
            data = {
                "bubble": 0,
                "msg": content,
                "color": 16777215,
                "mode": 1,
                "fontsize": 25,
                "rnd": int(time.time()),
                "roomid": self.room_id,
                "csrf": self._get_csrf(),
            }
            
            # 发送请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self._api_base}/msg/send",
                    data=data,
                    headers=self._get_headers()
                ) as response:
                    result = await response.json()
                    
                    if result.get("code") == 0:
                        logger.info(f" 弹幕发送成功: {content}")
                        return True
                    else:
                        logger.info(f" 弹幕发送失败: {result.get('message', '未知错误')}")
                        return False
            
        except Exception as e:
            logger.info(f" 弹幕发送失败: {e}")
            self._stats["error_count"] += 1
            return False
    
    async def _get_room_info(self, room_id: str) -> Optional[Dict[str, Any]]:
        """获取直播间信息"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self._api_base}/room/v1/Room/get_info",
                    params={"room_id": room_id}
                ) as response:
                    result = await response.json()
                    
                    if result.get("code") == 0:
                        return result.get("data")
                    else:
                        logger.info(f" 获取直播间信息失败: {result.get('message', '未知错误')}")
                        return None
            
        except Exception as e:
            logger.info(f" 获取直播间信息失败: {e}")
            return None
    
    async def _get_ws_info(self, room_id: str) -> Optional[Dict[str, Any]]:
        """获取WebSocket连接信息"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self._api_base}/room/v1/Danmu/getConf",
                    params={"room_id": room_id}
                ) as response:
                    result = await response.json()
                    
                    if result.get("code") == 0:
                        return result.get("data")
                    else:
                        logger.info(f" 获取WebSocket信息失败: {result.get('message', '未知错误')}")
                        return None
            
        except Exception as e:
            logger.info(f" 获取WebSocket信息失败: {e}")
            return None
    
    async def _connect_websocket(self, ws_info: Dict[str, Any]) -> bool:
        """连接WebSocket"""
        try:
            import websockets
            
            # 获取WebSocket服务器列表
            host_list = ws_info.get("host_server_list", [])
            if not host_list:
                logger.info(" 无可用的WebSocket服务器")
                return False
            
            # 连接到第一个可用的服务器
            for host_info in host_list:
                try:
                    host = host_info.get("host")
                    port = host_info.get("wss_port", 443)
                    token = ws_info.get("token", "")
                    
                    uri = f"wss://{host}:{port}/sub"
                    
                    self._ws = await websockets.connect(uri)
                    
                    # 发送认证消息
                    auth_msg = {
                        "uid": self.uid,
                        "roomid": self.room_id,
                        "protover": 3,
                        "platform": "web",
                        "type": 2,
                        "key": token,
                    }
                    await self._ws.send(json.dumps(auth_msg))
                    
                    logger.info(f" WebSocket连接成功: {host}:{port}")
                    return True
                    
                except Exception as e:
                    logger.info(f" WebSocket连接失败 {host}:{port}: {e}")
                    continue
            
            logger.info(" 所有WebSocket服务器连接失败")
            return False
            
        except ImportError:
            logger.info(" 未安装websockets库，请执行: pip install websockets")
            return False
        except Exception as e:
            logger.info(f" WebSocket连接失败: {e}")
            return False
    
    async def _receive_messages(self):
        """接收消息"""
        try:
            import zlib
            
            async for message in self._ws:
                try:
                    # 解析消息
                    if isinstance(message, bytes):
                        # 解压消息
                        message = zlib.decompress(message)
                        message = message.decode("utf-8")
                    
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
            cmd = data.get("cmd", "")
            
            if cmd == "DANMU_MSG":
                # 弹幕消息
                info = data.get("info", [])
                if len(info) >= 2:
                    user_info = info[2]
                    content = info[1]
                    
                    danmaku = DanmakuMessage(
                        platform=PlatformType.BILIBILI,
                        user_id=str(user_info[0]),
                        username=user_info[1],
                        content=content,
                        timestamp=datetime.now(),
                        room_id=self.room_id,
                        extra={"raw_info": info}
                    )
                    
                    self._notify_danmaku(danmaku)
            
            elif cmd == "SEND_GIFT":
                # 礼物消息
                data_info = data.get("data", {})
                
                gift = GiftMessage(
                    platform=PlatformType.BILIBILI,
                    user_id=str(data_info.get("uid", "")),
                    username=data_info.get("uname", ""),
                    gift_name=data_info.get("giftName", ""),
                    gift_count=data_info.get("num", 0),
                    timestamp=datetime.now(),
                    room_id=self.room_id,
                    extra={"raw_data": data_info}
                )
                
                self._notify_gift(gift)
            
            elif cmd in ["WELCOME", "WELCOME_GUARD", "SYS_MSG", "NOTICE_MSG"]:
                # 系统消息
                system_msg = SystemMessage(
                    platform=PlatformType.BILIBILI,
                    message_type=cmd,
                    content=json.dumps(data.get("data", {}), ensure_ascii=False),
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
                    heartbeat_msg = json.dumps({"cmd": "HEARTBEAT"})
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
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://live.bilibili.com",
            "Content-Type": "application/x-www-form-urlencoded",
        }
    
    def _get_csrf(self) -> str:
        """获取CSRF Token"""
        # 这里应该从cookie中获取csrf token
        # 简化实现，返回空字符串
        return ""


# 导出主要类
__all__ = ['BilibiliPlatform']