"""
飞书 Bot实现

提供飞书 Bot的完整集成，包括：
- 连接到飞书
- 接收消息
- 发送消息
- 处理命令

作者: 咕咕嘎嘎
日期: 2026-06-03
"""

import os
import json
from typing import Dict, Any, List

from . import Bot
import logging

logger = logging.getLogger(__name__)


class FeishuBot(Bot):
    """飞书 Bot实现"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("feishu_bot", "feishu")
        self.config = config or {}
        
        # 飞书配置
        self.app_id = self.config.get("app_id", "")
        self.app_secret = self.config.get("app_secret", "")
        self.verification_token = self.config.get("verification_token", "")
        self.encrypt_key = self.config.get("encrypt_key", "")
        
        # 飞书客户端
        self._client = None
        
        logger.info(f" 飞书 Bot初始化完成")
        logger.info(f" App ID: {self.app_id}")
    
    async def connect(self) -> bool:
        """连接到飞书"""
        try:
            # 导入lark-oapi库
            import lark_oapi as lark
            from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
            
            # 创建飞书客户端
            self._client = lark.Client.builder() \
                .app_id(self.app_id) \
                .app_secret(self.app_secret) \
                .build()
            
            # 测试连接
            logger.info(f" 正在连接到飞书...")
            
            # 获取tenant_access_token
            request = lark.auth.v3.TenantAccessTokenInternalRequest.builder() \
                .request_body(lark.auth.v3.TenantAccessTokenInternalRequestBody.builder()
                    .app_id(self.app_id)
                    .app_secret(self.app_secret)
                    .build()) \
                .build()
            
            response = self._client.auth.v3.tenant_access_token_internal(request)
            
            if response.success():
                self.connected = True
                logger.info(" 飞书 Bot连接成功")
                return True
            else:
                logger.info(f" 飞书 Bot连接失败: {response.msg}")
                return False
            
        except ImportError:
            logger.info(" 未安装lark-oapi库，请执行: pip install lark-oapi")
            return False
        except Exception as e:
            logger.info(f" 飞书 Bot连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开飞书连接"""
        try:
            # 断开连接
            self._client = None
            
            self.connected = False
            logger.info(" 飞书 Bot已断开")
            
        except Exception as e:
            logger.info(f" 飞书 Bot断开失败: {e}")
    
    async def send_message(self, receive_id: str, content: str, message_type: str = "text") -> bool:
        """发送飞书消息"""
        try:
            if not self.connected or not self._client:
                logger.info(" 飞书 Bot未连接")
                return False
            
            # 构建消息内容
            msg_content = json.dumps({
                "text": content
            })
            
            # 创建消息请求
            request = CreateMessageRequest.builder() \
                .receive_id_type("chat_id") \
                .request_body(CreateMessageRequestBody.builder()
                    .receive_id(receive_id)
                    .msg_type("text")
                    .content(msg_content)
                    .build()) \
                .build()
            
            # 发送消息
            response = self._client.im.v1.message.create(request)
            
            if response.success():
                logger.info(f" 飞书消息发送成功: {content}")
                return True
            else:
                logger.info(f" 飞书消息发送失败: {response.msg}")
                return False
            
        except Exception as e:
            logger.info(f" 飞书消息发送失败: {e}")
            return False
    
    async def send_image(self, receive_id: str, image_path: str) -> bool:
        """发送飞书图片"""
        try:
            if not self.connected or not self._client:
                logger.info(" 飞书 Bot未连接")
                return False
            
            # 上传图片
            from lark_oapi.api.im.v1 import CreateImageRequest, CreateImageRequestBody
            
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            request = CreateImageRequest.builder() \
                .request_body(CreateImageRequestBody.builder()
                    .image_type("message")
                    .image(image_data)
                    .build()) \
                .build()
            
            response = self._client.im.v1.image.create(request)
            
            if response.success():
                image_key = response.data.image_key
                
                # 发送图片消息
                msg_content = json.dumps({
                    "image_key": image_key
                })
                
                from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody
                
                request = CreateMessageRequest.builder() \
                    .receive_id_type("chat_id") \
                    .request_body(CreateMessageRequestBody.builder()
                        .receive_id(receive_id)
                        .msg_type("image")
                        .content(msg_content)
                        .build()) \
                    .build()
                
                response = self._client.im.v1.message.create(request)
                
                if response.success():
                    logger.info(f" 飞书图片发送成功: {image_path}")
                    return True
                else:
                    logger.info(f" 飞书图片发送失败: {response.msg}")
                    return False
            else:
                logger.info(f" 飞书图片上传失败: {response.msg}")
                return False
            
        except Exception as e:
            logger.info(f" 飞书图片发送失败: {e}")
            return False
    
    def get_chat_list(self) -> List[Dict[str, Any]]:
        """获取聊天列表"""
        try:
            if not self.connected or not self._client:
                logger.info(" 飞书 Bot未连接")
                return []
            
            from lark_oapi.api.im.v1 import ListChatRequest
            
            request = ListChatRequest.builder().build()
            response = self._client.im.v1.chat.list(request)
            
            if response.success():
                return [
                    {
                        "chat_id": chat.chat_id,
                        "name": chat.name,
                        "type": chat.chat_type,
                    }
                    for chat in response.data.items
                ]
            else:
                logger.info(f" 获取聊天列表失败: {response.msg}")
                return []
            
        except Exception as e:
            logger.info(f" 获取聊天列表失败: {e}")
            return []


# 导出主要类
__all__ = ['FeishuBot']