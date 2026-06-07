"""
弹幕发送器

提供Bilibili直播弹幕发送功能。
"""

import asyncio
import json
from typing import Dict, Any
import aiohttp
import logging

logger = logging.getLogger(__name__)


class DanmakuSender:
    """弹幕发送器"""
    
    # Bilibili直播弹幕发送API
    SEND_API = "https://api.live.bilibili.com/msg/send"
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.session = None
        
        # 用户认证信息
        self.csrf = self.config.get("csrf", "")
        self.cookie = self.config.get("cookie", "")
    
    async def send(self, room_id: str, message: str) -> bool:
        """发送弹幕"""
        try:
            # 创建HTTP会话
            if self.session is None:
                self.session = aiohttp.ClientSession()
            
            # 构建请求数据
            data = {
                "bubble": 0,
                "msg": message,
                "color": 16777215,  # 白色
                "mode": 1,         # 普通弹幕
                "fontsize": 25,    # 字体大小
                "rnd": int(asyncio.get_event_loop().time()),  # 随机数
                "roomid": room_id,
                "csrf_token": self.csrf,
                "csrf": self.csrf,
            }
            
            # 构建请求头
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": f"https://live.bilibili.com/{room_id}",
                "Cookie": self.cookie,
            }
            
            # 发送请求
            async with self.session.post(self.SEND_API, data=data, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    if result.get("code") == 0:
                        logger.info(f" 弹幕发送成功: {message}")
                        return True
                    else:
                        logger.info(f" 弹幕发送失败: {result.get('message', '未知错误')}")
                        return False
                else:
                    logger.info(f" 弹幕发送失败: HTTP {response.status}")
                    return False
                    
        except Exception as e:
            logger.info(f" 弹幕发送失败: {e}")
            return False
    
    async def send_with_retry(self, room_id: str, message: str, max_retries: int = 3) -> bool:
        """带重试的弹幕发送"""
        for attempt in range(max_retries):
            try:
                success = await self.send(room_id, message)
                if success:
                    return True
                
                # 等待一段时间后重试
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.info(f" 弹幕发送重试 {attempt + 1}/{max_retries} 失败: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        
        return False
    
    async def close(self):
        """关闭HTTP会话"""
        try:
            if self.session:
                await self.session.close()
                self.session = None
        except Exception as e:
            logger.info(f" 关闭HTTP会话失败: {e}")
    
    def set_auth(self, csrf: str, cookie: str):
        """设置认证信息"""
        self.csrf = csrf
        self.cookie = cookie
    
    def get_auth_status(self) -> Dict[str, Any]:
        """获取认证状态"""
        return {
            "has_csrf": bool(self.csrf),
            "has_cookie": bool(self.cookie),
        }