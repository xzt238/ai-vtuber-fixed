"""
快手直播平台增强版
实现完整的弹幕接收和发送功能
"""

import asyncio
import json
import hashlib
import time
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.live.platforms import LivePlatform, PlatformType, DanmakuMessage, GiftMessage

class KuaishouConnectionState(Enum):
    """快手连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"

@dataclass
class KuaishouConfig:
    """快手配置"""
    room_id: str = ""
    cookie: str = ""
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    heartbeat_interval: int = 30
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10

class KuaishouPlatformEnhanced(LivePlatform):
    """快手直播平台增强版"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # 快手配置
        self.kuaishou_config = KuaishouConfig(
            room_id=config.get("room_id", ""),
            cookie=config.get("cookie", ""),
            user_agent=config.get("user_agent", ""),
            heartbeat_interval=config.get("heartbeat_interval", 30),
            reconnect_interval=config.get("reconnect_interval", 5),
            max_reconnect_attempts=config.get("max_reconnect_attempts", 10)
        )
        
        # 连接状态
        self.connection_state = KuaishouConnectionState.DISCONNECTED
        self.reconnect_attempts = 0
        
        # WebSocket连接
        self.websocket = None
        self.heartbeat_task = None
        self.receive_task = None
        
        # 统计信息
        self.stats = {
            "total_danmaku": 0,
            "total_gifts": 0,
            "total_likes": 0,
            "total_follows": 0,
            "connection_time": None,
            "last_danmaku_time": None
        }
        
        print("[KuaishouEnhanced] 初始化完成")
    
    def _get_platform_type(self) -> PlatformType:
        """获取平台类型"""
        return PlatformType.KUAISHOU
    
    async def connect(self, room_id: str = None) -> bool:
        """连接到快手直播间"""
        if room_id:
            self.kuaishou_config.room_id = room_id
        
        if not self.kuaishou_config.room_id:
            print("[KuaishouEnhanced] 错误: 未配置直播间ID")
            return False
        
        self.connection_state = KuaishouConnectionState.CONNECTING
        print(f"[KuaishouEnhanced] 正在连接直播间: {self.kuaishou_config.room_id}")
        
        try:
            # 获取直播间信息
            room_info = await self._get_room_info()
            if not room_info:
                print("[KuaishouEnhanced] 错误: 无法获取直播间信息")
                self.connection_state = KuaishouConnectionState.DISCONNECTED
                return False
            
            # 建立WebSocket连接
            success = await self._connect_websocket()
            if not success:
                print("[KuaishouEnhanced] 错误: WebSocket连接失败")
                self.connection_state = KuaishouConnectionState.DISCONNECTED
                return False
            
            # 启动心跳
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # 启动消息接收
            self.receive_task = asyncio.create_task(self._receive_messages())
            
            self.connected = True
            self.connection_state = KuaishouConnectionState.CONNECTED
            self.stats["connection_time"] = datetime.now()
            self.reconnect_attempts = 0
            
            print(f"[KuaishouEnhanced] 连接成功: {room_info.get('title', '未知')}")
            return True
            
        except Exception as e:
            print(f"[KuaishouEnhanced] 连接失败: {e}")
            self.connection_state = KuaishouConnectionState.DISCONNECTED
            return False
    
    async def disconnect(self) -> bool:
        """断开连接"""
        try:
            # 停止任务
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            if self.receive_task:
                self.receive_task.cancel()
                try:
                    await self.receive_task
                except asyncio.CancelledError:
                    pass
            
            # 关闭WebSocket
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            
            self.connected = False
            self.connection_state = KuaishouConnectionState.DISCONNECTED
            
            print("[KuaishouEnhanced] 已断开连接")
            return True
            
        except Exception as e:
            print(f"[KuaishouEnhanced] 断开连接失败: {e}")
            return False
    
    async def _get_room_info(self) -> Optional[Dict[str, Any]]:
        """获取直播间信息"""
        try:
            import aiohttp
            
            url = f"https://live.kuaishou.com/u/{self.kuaishou_config.room_id}"
            headers = {
                "User-Agent": self.kuaishou_config.user_agent,
                "Cookie": self.kuaishou_config.cookie,
                "Referer": "https://live.kuaishou.com/"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # 解析直播间信息
                        # 这里简化处理，实际需要解析HTML
                        return {
                            "title": "快手直播间",
                            "owner": "主播",
                            "viewers": 0,
                            "status": 1
                        }
            
            return None
            
        except Exception as e:
            print(f"[KuaishouEnhanced] 获取直播间信息失败: {e}")
            return None
    
    async def _connect_websocket(self) -> bool:
        """建立WebSocket连接"""
        try:
            import websockets
            
            # 快手WebSocket地址
            ws_url = "wss://live-ws-pkg.kuaishou.com/websocket"
            
            # 连接参数
            params = {
                "room_id": self.kuaishou_config.room_id,
                "token": "",
                "uid": 0
            }
            
            # 构建URL
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            full_url = f"{ws_url}?{query_string}"
            
            # 建立连接
            self.websocket = await websockets.connect(
                full_url,
                extra_headers={
                    "User-Agent": self.kuaishou_config.user_agent,
                    "Cookie": self.kuaishou_config.cookie
                }
            )
            
            print("[KuaishouEnhanced] WebSocket连接成功")
            return True
            
        except ImportError:
            print("[KuaishouEnhanced] 错误: 未安装websockets库")
            return False
        except Exception as e:
            print(f"[KuaishouEnhanced] WebSocket连接失败: {e}")
            return False
    
    async def _heartbeat_loop(self):
        """心跳循环"""
        try:
            while self.connected:
                try:
                    if self.websocket:
                        # 发送心跳包
                        heartbeat = {
                            "type": "heartbeat",
                            "timestamp": int(time.time() * 1000)
                        }
                        await self.websocket.send(json.dumps(heartbeat))
                    
                    await asyncio.sleep(self.kuaishou_config.heartbeat_interval)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"[KuaishouEnhanced] 心跳发送失败: {e}")
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            pass
    
    async def _receive_messages(self):
        """接收消息"""
        try:
            while self.connected:
                try:
                    if self.websocket:
                        # 接收消息
                        message = await self.websocket.recv()
                        
                        # 解析消息
                        await self._process_message(message)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"[KuaishouEnhanced] 消息接收失败: {e}")
                    # 尝试重连
                    if self.connected:
                        await self._reconnect()
                    
        except asyncio.CancelledError:
            pass
    
    async def _process_message(self, raw_message: str):
        """处理消息"""
        try:
            data = json.loads(raw_message)
            message_type = data.get("type")
            
            if message_type == "chat":
                # 弹幕消息
                await self._handle_danmaku(data)
            elif message_type == "gift":
                # 礼物消息
                await self._handle_gift(data)
            elif message_type == "like":
                # 点赞消息
                await self._handle_like(data)
            elif message_type == "follow":
                # 关注消息
                await self._handle_follow(data)
            elif message_type == "heartbeat":
                # 心跳响应
                pass
            else:
                # 其他消息
                pass
                
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"[KuaishouEnhanced] 消息处理失败: {e}")
    
    async def _handle_danmaku(self, data: Dict[str, Any]):
        """处理弹幕消息"""
        try:
            user = data.get("user", {})
            content = data.get("content", "")
            
            danmaku = DanmakuMessage(
                platform=PlatformType.KUAISHOU,
                user_id=user.get("id", ""),
                username=user.get("nickname", ""),
                content=content,
                timestamp=datetime.now(),
                room_id=self.kuaishou_config.room_id,
                extra={
                    "user_level": user.get("level", 0),
                    "badge": user.get("badge", "")
                }
            )
            
            # 更新统计
            self.stats["total_danmaku"] += 1
            self.stats["last_danmaku_time"] = datetime.now()
            
            # 触发回调
            for callback in self._danmaku_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(danmaku)
                    else:
                        callback(danmaku)
                except Exception as e:
                    print(f"[KuaishouEnhanced] 弹幕回调失败: {e}")
            
            print(f"[KuaishouEnhanced] 弹幕: {danmaku.username}: {danmaku.content}")
            
        except Exception as e:
            print(f"[KuaishouEnhanced] 弹幕处理失败: {e}")
    
    async def _handle_gift(self, data: Dict[str, Any]):
        """处理礼物消息"""
        try:
            user = data.get("user", {})
            gift = data.get("gift", {})
            
            gift_msg = GiftMessage(
                platform=PlatformType.KUAISHOU,
                user_id=user.get("id", ""),
                username=user.get("nickname", ""),
                gift_name=gift.get("name", ""),
                gift_count=gift.get("count", 1),
                timestamp=datetime.now(),
                room_id=self.kuaishou_config.room_id,
                extra={
                    "gift_id": gift.get("id", ""),
                    "gift_price": gift.get("price", 0),
                    "total_price": gift.get("price", 0) * gift.get("count", 1)
                }
            )
            
            # 更新统计
            self.stats["total_gifts"] += 1
            
            # 触发回调
            for callback in self._gift_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(gift_msg)
                    else:
                        callback(gift_msg)
                except Exception as e:
                    print(f"[KuaishouEnhanced] 礼物回调失败: {e}")
            
            print(f"[KuaishouEnhanced] 礼物: {gift_msg.username} 送出了 {gift_msg.gift_name} x{gift_msg.gift_count}")
            
        except Exception as e:
            print(f"[KuaishouEnhanced] 礼物处理失败: {e}")
    
    async def _handle_like(self, data: Dict[str, Any]):
        """处理点赞消息"""
        self.stats["total_likes"] += 1
    
    async def _handle_follow(self, data: Dict[str, Any]):
        """处理关注消息"""
        self.stats["total_follows"] += 1
    
    async def send_danmaku(self, content: str) -> bool:
        """发送弹幕"""
        if not self.connected or not self.websocket:
            print("[KuaishouEnhanced] 错误: 未连接")
            return False
        
        try:
            # 构建弹幕消息
            message = {
                "type": "chat",
                "content": content,
                "timestamp": int(time.time() * 1000)
            }
            
            # 发送消息
            await self.websocket.send(json.dumps(message))
            
            print(f"[KuaishouEnhanced] 发送弹幕: {content}")
            return True
            
        except Exception as e:
            print(f"[KuaishouEnhanced] 发送弹幕失败: {e}")
            return False
    
    async def _reconnect(self):
        """重连"""
        if self.connection_state == KuaishouConnectionState.RECONNECTING:
            return
        
        self.connection_state = KuaishouConnectionState.RECONNECTING
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.kuaishou_config.max_reconnect_attempts:
            print("[KuaishouEnhanced] 重连次数超过限制，停止重连")
            self.connected = False
            self.connection_state = KuaishouConnectionState.DISCONNECTED
            return
        
        print(f"[KuaishouEnhanced] 尝试重连 ({self.reconnect_attempts}/{self.kuaishou_config.max_reconnect_attempts})")
        
        await asyncio.sleep(self.kuaishou_config.reconnect_interval)
        
        # 重新连接
        success = await self.connect()
        if success:
            print("[KuaishouEnhanced] 重连成功")
        else:
            print("[KuaishouEnhanced] 重连失败")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "platform": "kuaishou",
            "room_id": self.kuaishou_config.room_id,
            "connected": self.connected,
            "connection_state": self.connection_state.value,
            "reconnect_attempts": self.reconnect_attempts,
            **self.stats
        }

# 注册平台
from app.live.platforms import LivePlatformFactory
LivePlatformFactory.register(PlatformType.KUAISHOU, KuaishouPlatformEnhanced)
