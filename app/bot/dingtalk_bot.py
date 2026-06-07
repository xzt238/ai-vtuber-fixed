"""
钉钉 Bot实现

提供钉钉 Bot的完整集成，包括：
- 连接到钉钉
- 接收消息
- 发送消息
- 处理命令

作者: 咕咕嘎嘎
日期: 2026-06-03
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime

from . import Bot, BotMessage
import logging

logger = logging.getLogger(__name__)


class DingTalkBot(Bot):
    """钉钉 Bot实现"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("dingtalk_bot", "dingtalk")
        self.config = config or {}
        
        # 钉钉配置
        self.app_key = self.config.get("app_key", "")
        self.app_secret = self.config.get("app_secret", "")
        self.robot_code = self.config.get("robot_code", "")
        
        # 钉钉客户端
        self._client = None
        
        logger.info(f" 钉钉 Bot初始化完成")
        logger.info(f" App Key: {self.app_key}")
    
    async def connect(self) -> bool:
        """连接到钉钉"""
        try:
            # 导入dingtalk-sdk库
            from dingtalk.client import Client
            
            # 创建钉钉客户端
            self._client = Client(
                app_key=self.app_key,
                app_secret=self.app_secret
            )
            
            # 测试连接
            logger.info(f" 正在连接到钉钉...")
            
            # 获取access_token
            access_token = self._client.access_token
            
            if access_token:
                self.connected = True
                logger.info(" 钉钉 Bot连接成功")
                return True
            else:
                logger.info(" 钉钉 Bot连接失败")
                return False
            
        except ImportError:
            logger.info(" 未安装dingtalk-sdk库，请执行: pip install dingtalk-sdk")
            return False
        except Exception as e:
            logger.info(f" 钉钉 Bot连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开钉钉连接"""
        try:
            # 断开连接
            self._client = None
            
            self.connected = False
            logger.info(" 钉钉 Bot已断开")
            
        except Exception as e:
            logger.info(f" 钉钉 Bot断开失败: {e}")
    
    async def send_message(self, chat_id: str, content: str, message_type: str = "text") -> bool:
        """发送钉钉消息"""
        try:
            if not self.connected or not self._client:
                logger.info(" 钉钉 Bot未连接")
                return False
            
            # 构建消息内容
            msg = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
            
            # 发送消息
            self._client.message.send_to_chat(
                chat_id=chat_id,
                msg=msg
            )
            
            logger.info(f" 钉钉消息发送成功: {content}")
            return True
            
        except Exception as e:
            logger.info(f" 钉钉消息发送失败: {e}")
            return False
    
    async def send_markdown(self, chat_id: str, title: str, content: str) -> bool:
        """发送钉钉Markdown消息"""
        try:
            if not self.connected or not self._client:
                logger.info(" 钉钉 Bot未连接")
                return False
            
            # 构建消息内容
            msg = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": content
                }
            }
            
            # 发送消息
            self._client.message.send_to_chat(
                chat_id=chat_id,
                msg=msg
            )
            
            logger.info(f" 钉钉Markdown消息发送成功: {title}")
            return True
            
        except Exception as e:
            logger.info(f" 钉钉Markdown消息发送失败: {e}")
            return False
    
    async def send_action_card(self, chat_id: str, title: str, content: str, action_url: str) -> bool:
        """发送钉钉ActionCard消息"""
        try:
            if not self.connected or not self._client:
                logger.info(" 钉钉 Bot未连接")
                return False
            
            # 构建消息内容
            msg = {
                "msgtype": "actionCard",
                "actionCard": {
                    "title": title,
                    "text": content,
                    "singleTitle": "查看详情",
                    "singleURL": action_url
                }
            }
            
            # 发送消息
            self._client.message.send_to_chat(
                chat_id=chat_id,
                msg=msg
            )
            
            logger.info(f" 钉钉ActionCard消息发送成功: {title}")
            return True
            
        except Exception as e:
            logger.info(f" 钉钉ActionCard消息发送失败: {e}")
            return False
    
    def get_chat_list(self) -> List[Dict[str, Any]]:
        """获取聊天列表"""
        try:
            if not self.connected or not self._client:
                logger.info(" 钉钉 Bot未连接")
                return []
            
            # 获取聊天列表
            chats = self._client.chat.get_chat_list()
            
            return [
                {
                    "chat_id": chat.chat_id,
                    "name": chat.name,
                    "type": chat.chat_type,
                }
                for chat in chats
            ]
            
        except Exception as e:
            logger.info(f" 获取聊天列表失败: {e}")
            return []


# 导出主要类
__all__ = ['DingTalkBot']