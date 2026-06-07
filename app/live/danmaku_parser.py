import logging
"""
弹幕解析器

logger = logging.getLogger(__name__)

提供Bilibili直播弹幕解析功能。
"""

from typing import Dict, Any, Optional
from datetime import datetime

from . import Danmaku, Gift, LiveMessage


class DanmakuParser:
    """弹幕解析器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
    
    def parse(self, message: Dict[str, Any]) -> Optional[LiveMessage]:
        """解析消息"""
        try:
            cmd = message.get("cmd", "")
            
            if cmd == "DANMU_MSG":
                # 弹幕消息
                return self._parse_danmaku(message)
            elif cmd == "SEND_GIFT":
                # 礼物消息
                return self._parse_gift(message)
            elif cmd == "SYSTEM_MSG":
                # 系统消息
                return self._parse_system_message(message)
            elif cmd == "WELCOME":
                # 欢迎消息
                return self._parse_welcome(message)
            elif cmd == "INTERACT_WORD":
                # 互动消息
                return self._parse_interact(message)
            else:
                # 其他消息
                return self._parse_other(message)
                
        except Exception as e:
            logger.info(f" 消息解析失败: {e}")
            return None
    
    def _parse_danmaku(self, message: Dict[str, Any]) -> Optional[LiveMessage]:
        """解析弹幕消息"""
        try:
            # 获取弹幕信息
            info = message.get("info", [])
            
            if len(info) < 3:
                return None
            
            # 弹幕内容
            content = info[1]
            
            # 用户信息
            user_info = info[2]
            if len(user_info) < 2:
                return None
            
            user_id = str(user_info[0])
            username = user_info[1]
            
            # 房间ID
            room_id = str(info[3].get("roomid", "")) if len(info) > 3 else ""
            
            # 创建弹幕对象
            danmaku = Danmaku(
                id=f"{user_id}_{datetime.now().timestamp()}",
                user_id=user_id,
                username=username,
                content=content,
                timestamp=datetime.now(),
                room_id=room_id,
                extra={
                    "raw_info": info,
                }
            )
            
            return LiveMessage(
                type="danmaku",
                data=danmaku,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.info(f" 弹幕解析失败: {e}")
            return None
    
    def _parse_gift(self, message: Dict[str, Any]) -> Optional[LiveMessage]:
        """解析礼物消息"""
        try:
            data = message.get("data", {})
            
            # 礼物信息
            gift_name = data.get("giftName", "")
            gift_count = data.get("num", 0)
            
            # 用户信息
            user_id = str(data.get("uid", ""))
            username = data.get("uname", "")
            
            # 房间ID
            room_id = str(data.get("roomid", ""))
            
            # 创建礼物对象
            gift = Gift(
                id=f"{user_id}_{datetime.now().timestamp()}",
                user_id=user_id,
                username=username,
                gift_name=gift_name,
                gift_count=gift_count,
                timestamp=datetime.now(),
                room_id=room_id,
                extra={
                    "raw_data": data,
                }
            )
            
            return LiveMessage(
                type="gift",
                data=gift,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.info(f" 礼物解析失败: {e}")
            return None
    
    def _parse_system_message(self, message: Dict[str, Any]) -> Optional[LiveMessage]:
        """解析系统消息"""
        try:
            data = message.get("data", {})
            content = data.get("msg", "")
            
            return LiveMessage(
                type="system",
                data={
                    "content": content,
                    "raw_data": data,
                },
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.info(f" 系统消息解析失败: {e}")
            return None
    
    def _parse_welcome(self, message: Dict[str, Any]) -> Optional[LiveMessage]:
        """解析欢迎消息"""
        try:
            data = message.get("data", {})
            username = data.get("uname", "")
            
            return LiveMessage(
                type="welcome",
                data={
                    "username": username,
                    "raw_data": data,
                },
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.info(f" 欢迎消息解析失败: {e}")
            return None
    
    def _parse_interact(self, message: Dict[str, Any]) -> Optional[LiveMessage]:
        """解析互动消息"""
        try:
            data = message.get("data", {})
            username = data.get("uname", "")
            msg_type = data.get("msg_type", 0)
            
            # 根据消息类型确定互动类型
            interact_type = "unknown"
            if msg_type == 1:
                interact_type = "follow"
            elif msg_type == 2:
                interact_type = "share"
            elif msg_type == 3:
                interact_type = "like"
            
            return LiveMessage(
                type="interact",
                data={
                    "username": username,
                    "interact_type": interact_type,
                    "msg_type": msg_type,
                    "raw_data": data,
                },
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.info(f" 互动消息解析失败: {e}")
            return None
    
    def _parse_other(self, message: Dict[str, Any]) -> Optional[LiveMessage]:
        """解析其他消息"""
        try:
            cmd = message.get("cmd", "UNKNOWN")
            
            return LiveMessage(
                type="other",
                data={
                    "cmd": cmd,
                    "raw_message": message,
                },
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.info(f" 其他消息解析失败: {e}")
            return None