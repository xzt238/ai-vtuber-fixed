"""
Slack Bot实现

提供Slack Bot的完整集成，包括：
- 连接到Slack
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


class SlackBot(Bot):
    """Slack Bot实现"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("slack_bot", "slack")
        self.config = config or {}
        
        # Slack配置
        self.token = self.config.get("token", "")
        self.app_token = self.config.get("app_token", "")
        self.signing_secret = self.config.get("signing_secret", "")
        
        # Slack客户端
        self._client = None
        self._socket_mode_client = None
        
        logger.info(f" Slack Bot初始化完成")
    
    async def connect(self) -> bool:
        """连接到Slack"""
        try:
            # 导入slack_sdk库
            from slack_sdk import WebClient
            from slack_sdk.socket_mode import SocketModeClient
            from slack_sdk.socket_mode.response import SocketModeResponse
            from slack_sdk.socket_mode.request import SocketModeRequest
            
            # 创建Web客户端
            self._client = WebClient(token=self.token)
            
            # 创建Socket Mode客户端
            self._socket_mode_client = SocketModeClient(
                app_token=self.app_token,
                web_client=self._client
            )
            
            # 定义事件处理器
            def process(client: SocketModeClient, req: SocketModeRequest):
                if req.type == "events_api":
                    # 响应Socket Mode请求
                    response = SocketModeResponse(envelope_id=req.envelope_id)
                    client.send_socket_mode_response(response)
                    
                    # 处理事件
                    event = req.payload.get("event", {})
                    if event.get("type") == "message":
                        # 创建BotMessage
                        bot_message = BotMessage(
                            id=event.get("ts", ""),
                            platform="slack",
                            channel_id=event.get("channel", ""),
                            user_id=event.get("user", ""),
                            username=event.get("user", ""),
                            content=event.get("text", ""),
                            timestamp=datetime.fromtimestamp(float(event.get("ts", 0))),
                            message_type="text",
                            metadata={
                                "channel_type": event.get("channel_type", ""),
                            }
                        )
                        
                        # 通知消息回调
                        self._notify_message(bot_message)
            
            # 注册事件处理器
            self._socket_mode_client.socket_mode_request_listeners.append(process)
            
            # 连接到Slack
            logger.info(f" 正在连接到Slack...")
            
            # 启动Socket Mode
            asyncio.create_task(self._socket_mode_client.connect())
            
            # 等待连接
            await asyncio.sleep(2)
            
            self.connected = True
            logger.info(" Slack Bot连接成功")
            
            return True
            
        except ImportError:
            logger.info(" 未安装slack_sdk库，请执行: pip install slack_sdk")
            return False
        except Exception as e:
            logger.info(f" Slack Bot连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开Slack连接"""
        try:
            # 断开连接
            if self._socket_mode_client:
                self._socket_mode_client.close()
                self._socket_mode_client = None
            
            self._client = None
            
            self.connected = False
            logger.info(" Slack Bot已断开")
            
        except Exception as e:
            logger.info(f" Slack Bot断开失败: {e}")
    
    async def send_message(self, channel: str, content: str, message_type: str = "text") -> bool:
        """发送Slack消息"""
        try:
            if not self.connected or not self._client:
                logger.info(" Slack Bot未连接")
                return False
            
            # 发送消息
            response = self._client.chat_postMessage(
                channel=channel,
                text=content
            )
            
            if response["ok"]:
                logger.info(f" Slack消息发送成功: {content}")
                return True
            else:
                logger.info(f" Slack消息发送失败: {response['error']}")
                return False
            
        except Exception as e:
            logger.info(f" Slack消息发送失败: {e}")
            return False
    
    async def send_file(self, channel: str, file_path: str, title: str = "") -> bool:
        """发送Slack文件"""
        try:
            if not self.connected or not self._client:
                logger.info(" Slack Bot未连接")
                return False
            
            # 上传文件
            response = self._client.files_upload(
                channels=channel,
                file=file_path,
                title=title
            )
            
            if response["ok"]:
                logger.info(f" Slack文件发送成功: {file_path}")
                return True
            else:
                logger.info(f" Slack文件发送失败: {response['error']}")
                return False
            
        except Exception as e:
            logger.info(f" Slack文件发送失败: {e}")
            return False
    
    def get_channels(self) -> List[Dict[str, Any]]:
        """获取频道列表"""
        try:
            if not self.connected or not self._client:
                logger.info(" Slack Bot未连接")
                return []
            
            # 获取频道列表
            response = self._client.conversations_list()
            
            if response["ok"]:
                return [
                    {
                        "id": channel["id"],
                        "name": channel["name"],
                        "type": channel["type"],
                    }
                    for channel in response["channels"]
                ]
            else:
                logger.info(f" 获取频道列表失败: {response['error']}")
                return []
            
        except Exception as e:
            logger.info(f" 获取频道列表失败: {e}")
            return []


# 导出主要类
__all__ = ['SlackBot']