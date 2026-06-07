"""
直播平台集成模块

提供Bilibili直播弹幕接收、解析、AI回复、弹幕发送等功能。

主要组件:
- BilibiliClient: Bilibili直播客户端
- DanmakuParser: 弹幕解析器
- LiveAIResponder: AI回复生成器
- DanmakuSender: 弹幕发送器

作者: 咕咕嘎嘎
日期: 2026-06-03
"""

import os
import asyncio
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 版本信息
__version__ = "1.0.0"
__author__ = "咕咕嘎嘎"


@dataclass
class Danmaku:
    """弹幕数据结构"""
    id: str
    user_id: str
    username: str
    content: str
    timestamp: datetime
    room_id: str
    extra: Dict[str, Any] = None
    
    def __post_init__(self) -> None:
        """内部方法"""
        if self.extra is None:
            self.extra = {}


@dataclass
class Gift:
    """礼物数据结构"""
    id: str
    user_id: str
    username: str
    gift_name: str
    gift_count: int
    timestamp: datetime
    room_id: str
    extra: Dict[str, Any] = None
    
    def __post_init__(self) -> None:
        """内部方法"""
        if self.extra is None:
            self.extra = {}


@dataclass
class LiveMessage:
    """直播消息"""
    type: str  # danmaku, gift, system
    data: Any
    timestamp: datetime


class LiveSystem:
    """直播系统主类"""
    
    def __init__(self, config: Dict[str, Any] = None) -> None:
        """内部方法"""
        self.config = config or {}
        self.storage_dir = self.config.get("storage_dir", "./memory/live")
        
        # 确保存储目录存在
        if not os.path.isabs(self.storage_dir):
            from app.shared_config import PROJECT_DIR
            self.storage_dir = os.path.join(PROJECT_DIR, self.storage_dir)
            self.storage_dir = os.path.normpath(self.storage_dir)
        
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # 初始化组件
        self._bilibili_client = None
        self._danmaku_parser = None
        self._ai_responder = None
        self._danmaku_sender = None
        
        # 消息回调
        self._message_callbacks: List[Callable] = []
        
        # 连接状态
        self._connected = False
        self._room_id = None
        
        logger.info(f" 直播系统初始化完成")
        logger.info(f" 存储目录: {self.storage_dir}")
    
    @property
    def bilibili_client(self) -> None:
        """延迟加载Bilibili客户端"""
        if self._bilibili_client is None:
            from .bilibili_client import BilibiliClient
            self._bilibili_client = BilibiliClient(self.config)
        return self._bilibili_client
    
    @property
    def danmaku_parser(self) -> None:
        """延迟加载弹幕解析器"""
        if self._danmaku_parser is None:
            from .danmaku_parser import DanmakuParser
            self._danmaku_parser = DanmakuParser(self.config)
        return self._danmaku_parser
    
    @property
    def ai_responder(self) -> None:
        """延迟加载AI回复生成器"""
        if self._ai_responder is None:
            from .ai_responder import AIResponder
            self._ai_responder = AIResponder(self.config)
        return self._ai_responder
    
    @property
    def danmaku_sender(self) -> None:
        """延迟加载弹幕发送器"""
        if self._danmaku_sender is None:
            from .danmaku_sender import DanmakuSender
            self._danmaku_sender = DanmakuSender(self.config)
        return self._danmaku_sender
    
    def add_message_callback(self, callback: Callable) -> None:
        """添加消息回调"""
        self._message_callbacks.append(callback)
    
    def remove_message_callback(self, callback: Callable) -> None:
        """移除消息回调"""
        self._message_callbacks = [cb for cb in self._message_callbacks if cb != callback]
    
    def _notify_message(self, message: LiveMessage) -> None:
        """通知消息回调"""
        for callback in self._message_callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.info(f" 消息回调失败: {e}")
    
    async def connect(self, room_id: str) -> bool:
        """连接到直播间"""
        try:
            self._room_id = room_id
            
            # 连接Bilibili直播服务器
            success = await self.bilibili_client.connect(room_id)
            
            if success:
                self._connected = True
                logger.info(f" 连接直播间成功: {room_id}")
                
                # 设置消息处理回调
                self.bilibili_client.set_message_handler(self._handle_message)
            else:
                logger.info(f" 连接直播间失败: {room_id}")
            
            return success
            
        except Exception as e:
            logger.info(f" 连接直播间失败: {e}")
            return False
    
    async def disconnect(self) -> None:
        """断开连接"""
        try:
            if self._bilibili_client:
                await self._bilibili_client.disconnect()
            
            self._connected = False
            self._room_id = None
            
            logger.info(f" 断开直播间连接")
            
        except Exception as e:
            logger.info(f" 断开连接失败: {e}")
    
    def _handle_message(self, message: Dict[str, Any]) -> None:
        """处理接收到的消息"""
        try:
            # 解析消息
            parsed_message = self.danmaku_parser.parse(message)
            
            if parsed_message:
                # 通知消息回调
                self._notify_message(parsed_message)
                
                # 如果是弹幕消息，生成AI回复
                if parsed_message.type == "danmaku":
                    self._handle_danmaku(parsed_message.data)
                
        except Exception as e:
            logger.info(f" 消息处理失败: {e}")
    
    def _handle_danmaku(self, danmaku: Danmaku) -> None:
        """处理弹幕消息"""
        try:
            # 生成AI回复
            response = self.ai_responder.generate_response(danmaku)
            
            if response:
                # 发送弹幕回复
                asyncio.create_task(self._send_danmaku_response(response))
                
                # 通知消息回调
                response_message = LiveMessage(
                    type="response",
                    data={
                        "original": danmaku,
                        "response": response,
                    },
                    timestamp=datetime.now()
                )
                self._notify_message(response_message)
                
        except Exception as e:
            logger.info(f" 弹幕处理失败: {e}")
    
    async def _send_danmaku_response(self, response: str) -> None:
        """发送弹幕回复"""
        try:
            if self._connected and self._room_id:
                success = await self.danmaku_sender.send(self._room_id, response)
                
                if success:
                    logger.info(f" 弹幕回复发送成功: {response}")
                else:
                    logger.info(f" 弹幕回复发送失败: {response}")
                    
        except Exception as e:
            logger.info(f" 弹幕回复发送失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取直播系统统计信息"""
        return {
            "connected": self._connected,
            "room_id": self._room_id,
            "message_callbacks": len(self._message_callbacks),
        }
    
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected
    
    def get_room_id(self) -> Optional[str]:
        """获取房间ID"""
        return self._room_id


# 全局直播系统实例
_live_system = None


def get_live_system(config: Dict[str, Any] = None) -> LiveSystem:
    """获取直播系统单例"""
    global _live_system
    if _live_system is None:
        _live_system = LiveSystem(config)
    return _live_system


async def connect_to_live(room_id: str) -> bool:
    """连接到直播间的便捷函数"""
    live = get_live_system()
    return await live.connect(room_id)


async def disconnect_from_live() -> None:
    """断开直播连接的便捷函数"""
    live = get_live_system()
    await live.disconnect()


def add_live_message_callback(callback: Callable) -> None:
    """添加直播消息回调的便捷函数"""
    live = get_live_system()
    live.add_message_callback(callback)


# 导出主要类
__all__ = [
    'LiveSystem',
    'Danmaku',
    'Gift',
    'LiveMessage',
    'get_live_system',
    'connect_to_live',
    'disconnect_from_live',
    'add_live_message_callback',
]