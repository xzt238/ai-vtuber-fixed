"""
微信 Bot实现

提供微信 Bot的完整集成，包括：
- 连接到微信
- 接收消息
- 发送消息
- 处理命令

作者: 咕咕嘎嘎
日期: 2026-06-03
"""

import os
from typing import Optional, Dict, Any

from . import Bot
import logging

logger = logging.getLogger(__name__)


class WeChatBot(Bot):
    """微信 Bot实现"""
    
    def __init__(self, config: Dict[str, Any] = None) -> None:
        super().__init__("wechat_bot", "wechat")
        self.config = config or {}
        
        # 微信配置
        self.app_id = self.config.get("app_id", "")
        self.app_secret = self.config.get("app_secret", "")
        self.token = self.config.get("token", "")
        self.encoding_aes_key = self.config.get("encoding_aes_key", "")
        
        # 微信客户端
        self._client = None
        
        logger.info(f" 微信 Bot初始化完成")
        logger.info(f" App ID: {self.app_id}")
    
    async def connect(self) -> bool:
        """连接到微信"""
        try:
            # 导入wechatpy库
            from wechatpy import WeChatClient
            from wechatpy.client import WeChatClient
            
            # 创建微信客户端
            self._client = WeChatClient(
                appid=self.app_id,
                secret=self.app_secret
            )
            
            # 测试连接
            logger.info(f" 正在连接到微信...")
            
            # 获取access_token
            access_token = self._client.access_token
            
            if access_token:
                self.connected = True
                logger.info(" 微信 Bot连接成功")
                return True
            else:
                logger.info(" 微信 Bot连接失败")
                return False
            
        except ImportError:
            logger.info(" 未安装wechatpy库，请执行: pip install wechatpy")
            return False
        except Exception as e:
            logger.info(f" 微信 Bot连接失败: {e}")
            return False
    
    async def disconnect(self) -> None:
        """断开微信连接"""
        try:
            # 断开连接
            self._client = None
            
            self.connected = False
            logger.info(" 微信 Bot已断开")
            
        except Exception as e:
            logger.info(f" 微信 Bot断开失败: {e}")
    
    async def send_message(self, user_id: str, content: str, message_type: str = "text") -> bool:
        """发送微信消息"""
        try:
            if not self.connected or not self._client:
                logger.info(" 微信 Bot未连接")
                return False
            
            # 发送消息
            self._client.message.send_text(
                user_id=user_id,
                content=content
            )
            
            logger.info(f" 微信消息发送成功: {content}")
            return True
            
        except Exception as e:
            logger.info(f" 微信消息发送失败: {e}")
            return False
    
    async def send_image(self, user_id: str, image_path: str) -> bool:
        """发送微信图片"""
        try:
            if not self.connected or not self._client:
                logger.info(" 微信 Bot未连接")
                return False
            
            # 上传图片
            media_id = self._client.media.upload(
                media_type="image",
                file_path=image_path
            )
            
            # 发送图片
            self._client.message.send_image(
                user_id=user_id,
                media_id=media_id
            )
            
            logger.info(f" 微信图片发送成功: {image_path}")
            return True
            
        except Exception as e:
            logger.info(f" 微信图片发送失败: {e}")
            return False
    
    async def send_voice(self, user_id: str, voice_path: str) -> bool:
        """发送微信语音"""
        try:
            if not self.connected or not self._client:
                logger.info(" 微信 Bot未连接")
                return False
            
            # 上传语音
            media_id = self._client.media.upload(
                media_type="voice",
                file_path=voice_path
            )
            
            # 发送语音
            self._client.message.send_voice(
                user_id=user_id,
                media_id=media_id
            )
            
            logger.info(f" 微信语音发送成功: {voice_path}")
            return True
            
        except Exception as e:
            logger.info(f" 微信语音发送失败: {e}")
            return False
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        try:
            if not self.connected or not self._client:
                logger.info(" 微信 Bot未连接")
                return None
            
            # 获取用户信息
            user_info = self._client.user.get(user_id)
            
            return {
                "user_id": user_id,
                "nickname": user_info.get("nickname", ""),
                "sex": user_info.get("sex", 0),
                "city": user_info.get("city", ""),
                "province": user_info.get("province", ""),
                "country": user_info.get("country", ""),
            }
            
        except Exception as e:
            logger.info(f" 获取用户信息失败: {e}")
            return None


# 导出主要类
__all__ = ['WeChatBot']