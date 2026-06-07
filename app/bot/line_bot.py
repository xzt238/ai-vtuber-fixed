"""
LINE Bot实现

提供LINE Bot的完整集成，包括：
- 连接到LINE
- 接收消息
- 发送消息
- 处理命令

作者: 咕咕嘎嘎
日期: 2026-06-03
"""

import os
from typing import Optional, Dict, Any

from . import Bot, BotMessage
import logging

logger = logging.getLogger(__name__)


class LineBot(Bot):
    """LINE Bot实现"""
    
    def __init__(self, config: Dict[str, Any] = None) -> None:
        """内部方法"""
        super().__init__("line_bot", "line")
        self.config = config or {}
        
        # LINE配置
        self.channel_access_token = self.config.get("channel_access_token", "")
        self.channel_secret = self.config.get("channel_secret", "")
        
        # LINE客户端
        self._handler = None
        
        logger.info(f" LINE Bot初始化完成")
    
    async def connect(self) -> bool:
        """连接到LINE"""
        try:
            # 导入line-bot-sdk库
            from linebot import LineBotApi, WebhookHandler
            from linebot.models import TextSendMessage, ImageSendMessage
            
            # 创建LINE Bot API客户端
            self._handler = WebhookHandler(self.channel_secret)
            self._line_bot_api = LineBotApi(self.channel_access_token)
            
            # 注册消息处理器
            @self._handler.add(MessageEvent, message=TextMessage)
            def handle_text_message(event) -> None:
                """Handle text message"""
                # 创建BotMessage
                bot_message = BotMessage(
                    id=event.message.id,
                    platform="line",
                    channel_id=event.source.user_id,
                    user_id=event.source.user_id,
                    username="",
                    content=event.message.text,
                    timestamp=event.timestamp,
                    message_type="text",
                    metadata={
                        "source_type": event.source.type,
                        "reply_token": event.reply_token,
                    }
                )
                
                # 通知消息回调
                self._notify_message(bot_message)
            
            # 测试连接
            logger.info(f" 正在连接到LINE...")
            
            # 获取Bot信息
            bot_info = self._line_bot_api.get_bot_info()
            
            if bot_info:
                self.connected = True
                logger.info(f" LINE Bot连接成功: {bot_info.display_name}")
                return True
            else:
                logger.info(" LINE Bot连接失败")
                return False
            
        except ImportError:
            logger.info(" 未安装line-bot-sdk库，请执行: pip install line-bot-sdk")
            return False
        except Exception as e:
            logger.info(f" LINE Bot连接失败: {e}")
            return False
    
    async def disconnect(self) -> None:
        """断开LINE连接"""
        try:
            # 断开连接
            self._handler = None
            self._line_bot_api = None
            
            self.connected = False
            logger.info(" LINE Bot已断开")
            
        except Exception as e:
            logger.info(f" LINE Bot断开失败: {e}")
    
    async def send_message(self, user_id: str, content: str, message_type: str = "text") -> bool:
        """发送LINE消息"""
        try:
            if not self.connected or not self._line_bot_api:
                logger.info(" LINE Bot未连接")
                return False
            
            # 发送消息
            self._line_bot_api.push_message(
                user_id,
                TextSendMessage(text=content)
            )
            
            logger.info(f" LINE消息发送成功: {content}")
            return True
            
        except Exception as e:
            logger.info(f" LINE消息发送失败: {e}")
            return False
    
    async def reply_message(self, reply_token: str, content: str) -> bool:
        """回复LINE消息"""
        try:
            if not self.connected or not self._line_bot_api:
                logger.info(" LINE Bot未连接")
                return False
            
            # 回复消息
            self._line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text=content)
            )
            
            logger.info(f" LINE消息回复成功: {content}")
            return True
            
        except Exception as e:
            logger.info(f" LINE消息回复失败: {e}")
            return False
    
    async def send_image(self, user_id: str, image_url: str, preview_url: str = "") -> bool:
        """发送LINE图片"""
        try:
            if not self.connected or not self._line_bot_api:
                logger.info(" LINE Bot未连接")
                return False
            
            # 发送图片
            self._line_bot_api.push_message(
                user_id,
                ImageSendMessage(
                    original_content_url=image_url,
                    preview_image_url=preview_url or image_url
                )
            )
            
            logger.info(f" LINE图片发送成功: {image_url}")
            return True
            
        except Exception as e:
            logger.info(f" LINE图片发送失败: {e}")
            return False
    
    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户资料"""
        try:
            if not self.connected or not self._line_bot_api:
                logger.info(" LINE Bot未连接")
                return None
            
            # 获取用户资料
            profile = self._line_bot_api.get_profile(user_id)
            
            return {
                "user_id": user_id,
                "display_name": profile.display_name,
                "picture_url": profile.picture_url,
                "status_message": profile.status_message,
            }
            
        except Exception as e:
            logger.info(f" 获取用户资料失败: {e}")
            return None


# 导出主要类
__all__ = ['LineBot']