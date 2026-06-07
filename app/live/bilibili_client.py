import logging
"""
Bilibili直播客户端

logger = logging.getLogger(__name__)

提供Bilibili直播弹幕接收功能。
"""

import asyncio
import json
import struct
import zlib
from typing import Dict, Any, Optional, Callable
import aiohttp


class BilibiliClient:
    """Bilibili直播客户端"""
    
    # Bilibili直播弹幕服务器地址
    DANMAKU_SERVER = "wss://broadcastlv.chat.bilibili.com/sub"
    
    # 心跳包间隔（秒）
    HEARTBEAT_INTERVAL = 30
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.room_id = None
        self.session = None
        self.websocket = None
        self._message_handler = None
        self._connected = False
        self._heartbeat_task = None
        self._receive_task = None
        
        # 用户认证信息（可选）
        self.uid = self.config.get("uid", 0)
        self.token = self.config.get("token", "")
    
    def set_message_handler(self, handler: Callable):
        """设置消息处理回调"""
        self._message_handler = handler
    
    async def connect(self, room_id: str) -> bool:
        """连接到直播间"""
        try:
            self.room_id = room_id
            
            # 创建HTTP会话
            self.session = aiohttp.ClientSession()
            
            # 获取直播间信息
            room_info = await self._get_room_info(room_id)
            if not room_info:
                logger.info(f" 获取直播间信息失败: {room_id}")
                return False
            
            # 连接WebSocket
            self.websocket = await self.session.ws_connect(self.DANMAKU_SERVER)
            
            # 发送认证包
            await self._send_auth_packet(room_info)
            
            # 启动心跳任务
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # 启动接收任务
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            self._connected = True
            logger.info(f" Bilibili直播客户端连接成功: {room_id}")
            
            return True
            
        except Exception as e:
            logger.info(f" Bilibili直播客户端连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        try:
            self._connected = False
            
            # 取消任务
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
            if self._receive_task:
                self._receive_task.cancel()
            
            # 关闭WebSocket
            if self.websocket:
                await self.websocket.close()
            
            # 关闭HTTP会话
            if self.session:
                await self.session.close()
            
            logger.info(f" Bilibili直播客户端断开连接")
            
        except Exception as e:
            logger.info(f" Bilibili直播客户端断开失败: {e}")
    
    async def _get_room_info(self, room_id: str) -> Optional[Dict[str, Any]]:
        """获取直播间信息"""
        try:
            url = f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("code") == 0:
                        return data.get("data")
            
            return None
            
        except Exception as e:
            logger.info(f" 获取直播间信息失败: {e}")
            return None
    
    async def _send_auth_packet(self, room_info: Dict[str, Any]):
        """发送认证包"""
        try:
            # 构建认证数据
            auth_data = {
                "uid": self.uid,
                "roomid": room_info.get("room_id"),
                "protover": 2,
                "platform": "web",
                "clientver": "2.6.36",
                "type": 2,
                "key": self.token,
            }
            
            # 编码为JSON
            auth_json = json.dumps(auth_data)
            auth_bytes = auth_json.encode('utf-8')
            
            # 构建数据包
            packet = self._build_packet(auth_bytes, 7)
            
            # 发送认证包
            await self.websocket.send_bytes(packet)
            
            logger.info(f" 发送认证包成功")
            
        except Exception as e:
            logger.info(f" 发送认证包失败: {e}")
    
    async def _heartbeat_loop(self):
        """心跳循环"""
        try:
            while self._connected:
                # 发送心跳包
                heartbeat_packet = self._build_packet(b'[object Object]', 2)
                await self.websocket.send_bytes(heartbeat_packet)
                
                # 等待下一次心跳
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.info(f" 心跳循环失败: {e}")
    
    async def _receive_loop(self):
        """接收消息循环"""
        try:
            async for message in self.websocket:
                if message.type == aiohttp.WSMsgType.BINARY:
                    # 处理二进制消息
                    self._process_binary_message(message.data)
                elif message.type == aiohttp.WSMsgType.TEXT:
                    # 处理文本消息
                    self._process_text_message(message.data)
                elif message.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    # 连接关闭或错误
                    logger.info(f" WebSocket连接关闭: {message.type}")
                    break
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.info(f" 接收消息循环失败: {e}")
    
    def _process_binary_message(self, data: bytes):
        """处理二进制消息"""
        try:
            # 解析数据包
            packets = self._parse_packets(data)
            
            for packet in packets:
                if packet['operation'] == 5:
                    # 消息数据
                    try:
                        message_data = json.loads(packet['data'].decode('utf-8'))
                        if self._message_handler:
                            self._message_handler(message_data)
                    except json.JSONDecodeError:
                        pass
                        
        except Exception as e:
            logger.info(f" 处理二进制消息失败: {e}")
    
    def _process_text_message(self, data: str):
        """处理文本消息"""
        try:
            message_data = json.loads(data)
            if self._message_handler:
                self._message_handler(message_data)
        except json.JSONDecodeError:
            pass
    
    def _build_packet(self, data: bytes, operation: int) -> bytes:
        """构建数据包"""
        # 数据包头部
        header = struct.pack('>I', 16 + len(data))  # 数据包长度
        header += struct.pack('>H', 16)              # 头部长度
        header += struct.pack('>H', 1)               # 协议版本
        header += struct.pack('>I', operation)        # 操作类型
        header += struct.pack('>I', 1)                # 序列号
        
        return header + data
    
    def _parse_packets(self, data: bytes) -> list:
        """解析数据包"""
        packets = []
        offset = 0
        
        while offset < len(data):
            # 读取数据包长度
            if offset + 4 > len(data):
                break
            
            packet_length = struct.unpack('>I', data[offset:offset+4])[0]
            
            # 检查数据包长度
            if offset + packet_length > len(data):
                break
            
            # 读取头部
            header = data[offset:offset+16]
            header_length = struct.unpack('>H', header[4:6])[0]
            protocol_version = struct.unpack('>H', header[6:8])[0]
            operation = struct.unpack('>I', header[8:12])[0]
            
            # 读取数据
            packet_data = data[offset+header_length:offset+packet_length]
            
            # 处理压缩
            if protocol_version == 2:
                # zlib压缩
                try:
                    packet_data = zlib.decompress(packet_data)
                except zlib.error:
                    pass
            
            packets.append({
                'operation': operation,
                'data': packet_data,
            })
            
            offset += packet_length
        
        return packets