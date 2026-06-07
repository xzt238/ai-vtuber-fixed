import logging
"""
直播模块通信桥梁

logger = logging.getLogger(__name__)

实现直播模块与LLM、TTS等模块的通信。

主要功能:
- 接收直播弹幕
- 调用LLM生成回复
- 调用TTS合成语音
- 发送弹幕回复

作者: 咕咕嘎嘎
日期: 2026-06-03
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from dataclasses import dataclass

from .platforms import (
    PlatformType, DanmakuMessage, GiftMessage, SystemMessage,
    LivePlatform, LivePlatformFactory
)


@dataclass
class LiveResponse:
    """直播回复"""
    platform: PlatformType
    room_id: str
    user_id: str
    username: str
    original_message: str
    ai_response: str
    tts_audio_path: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class LiveBridge:
    """直播模块通信桥梁"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # 直播平台实例
        self._platforms: Dict[PlatformType, LivePlatform] = {}
        
        # LLM和TTS引用（延迟设置）
        self._llm = None
        self._tts = None
        self._memory = None
        
        # 回调函数
        self._response_callbacks: List[Callable] = []
        
        # 配置参数
        self._auto_reply = self.config.get("auto_reply", True)
        self._reply_delay = self.config.get("reply_delay", 1.0)  # 回复延迟（秒）
        self._max_reply_length = self.config.get("max_reply_length", 100)  # 最大回复长度
        
        # 统计信息
        self._stats = {
            "total_danmaku": 0,
            "total_replies": 0,
            "total_gifts": 0,
            "errors": 0,
        }
        
        logger.info(" 直播通信桥梁初始化完成")
    
    def set_llm(self, llm):
        """设置LLM引用"""
        self._llm = llm
        logger.info(" LLM已连接到直播桥梁")
    
    def set_tts(self, tts):
        """设置TTS引用"""
        self._tts = tts
        logger.info(" TTS已连接到直播桥梁")
    
    def set_memory(self, memory):
        """设置记忆系统引用"""
        self._memory = memory
        logger.info(" 记忆系统已连接到直播桥梁")
    
    def add_response_callback(self, callback: Callable):
        """添加回复回调"""
        self._response_callbacks.append(callback)
    
    def remove_response_callback(self, callback: Callable):
        """移除回复回调"""
        self._response_callbacks = [cb for cb in self._response_callbacks if cb != callback]
    
    async def connect_platform(self, platform_type: PlatformType, room_id: str, **kwargs) -> bool:
        """连接到直播平台"""
        try:
            # 获取平台配置
            platform_config = self.config.get(platform_type.value, {})
            platform_config.update(kwargs)
            
            # 创建平台实例
            platform = LivePlatformFactory.create(platform_type, platform_config)
            
            # 设置消息回调
            platform.add_danmaku_callback(self._handle_danmaku)
            platform.add_gift_callback(self._handle_gift)
            platform.add_system_callback(self._handle_system)
            
            # 连接到直播间
            success = await platform.connect(room_id)
            
            if success:
                self._platforms[platform_type] = platform
                logger.info(f" {platform_type.value}直播间连接成功: {room_id}")
            else:
                logger.info(f" {platform_type.value}直播间连接失败: {room_id}")
            
            return success
            
        except Exception as e:
            logger.info(f" 连接直播平台失败: {e}")
            self._stats["errors"] += 1
            return False
    
    async def disconnect_platform(self, platform_type: PlatformType):
        """断开直播平台连接"""
        try:
            if platform_type in self._platforms:
                platform = self._platforms[platform_type]
                await platform.disconnect()
                del self._platforms[platform_type]
                logger.info(f" {platform_type.value}已断开连接")
            
        except Exception as e:
            logger.info(f" 断开直播平台失败: {e}")
            self._stats["errors"] += 1
    
    async def disconnect_all(self):
        """断开所有直播平台连接"""
        try:
            for platform_type in list(self._platforms.keys()):
                await self.disconnect_platform(platform_type)
            
            logger.info(" 所有直播平台已断开连接")
            
        except Exception as e:
            logger.info(f" 断开所有直播平台失败: {e}")
            self._stats["errors"] += 1
    
    def _handle_danmaku(self, message: DanmakuMessage):
        """处理弹幕消息"""
        try:
            self._stats["total_danmaku"] += 1
            
            logger.info(f" 收到弹幕 [{message.platform.value}] {message.username}: {message.content}")
            
            # 如果启用了自动回复，生成AI回复
            if self._auto_reply:
                asyncio.create_task(self._generate_and_send_reply(message))
            
        except Exception as e:
            logger.info(f" 处理弹幕失败: {e}")
            self._stats["errors"] += 1
    
    def _handle_gift(self, message: GiftMessage):
        """处理礼物消息"""
        try:
            self._stats["total_gifts"] += 1
            
            logger.info(f" 收到礼物 [{message.platform.value}] {message.username}: {message.gift_name} x{message.gift_count}")
            
            # 生成感谢回复
            asyncio.create_task(self._send_gift_thanks(message))
            
        except Exception as e:
            logger.info(f" 处理礼物失败: {e}")
            self._stats["errors"] += 1
    
    def _handle_system(self, message: SystemMessage):
        """处理系统消息"""
        try:
            logger.info(f" 系统消息 [{message.platform.value}] {message.message_type}: {message.content}")
            
        except Exception as e:
            logger.info(f" 处理系统消息失败: {e}")
            self._stats["errors"] += 1
    
    async def _generate_and_send_reply(self, message: DanmakuMessage):
        """生成并发送回复"""
        try:
            # 延迟回复
            await asyncio.sleep(self._reply_delay)
            
            # 生成AI回复
            ai_response = await self._generate_ai_response(message)
            
            if ai_response:
                # 限制回复长度
                if len(ai_response) > self._max_reply_length:
                    ai_response = ai_response[:self._max_reply_length] + "..."
                
                # 发送弹幕回复
                await self._send_danmaku_reply(message.platform, message.room_id, ai_response)
                
                # 生成TTS音频（可选）
                tts_audio_path = None
                if self._tts:
                    tts_audio_path = await self._generate_tts(ai_response)
                
                # 创建回复对象
                response = LiveResponse(
                    platform=message.platform,
                    room_id=message.room_id,
                    user_id=message.user_id,
                    username=message.username,
                    original_message=message.content,
                    ai_response=ai_response,
                    tts_audio_path=tts_audio_path,
                )
                
                # 通知回复回调
                self._notify_response(response)
                
                self._stats["total_replies"] += 1
                
                logger.info(f" AI回复 [{message.platform.value}] {message.username}: {ai_response}")
            
        except Exception as e:
            logger.info(f" 生成并发送回复失败: {e}")
            self._stats["errors"] += 1
    
    async def _generate_ai_response(self, message: DanmakuMessage) -> Optional[str]:
        """生成AI回复"""
        try:
            if not self._llm:
                logger.info(" LLM未设置，无法生成回复")
                return None
            
            # 构建提示词
            prompt = self._build_prompt(message)
            
            # 调用LLM生成回复
            response = await self._llm.generate(prompt)
            
            return response
            
        except Exception as e:
            logger.info(f" 生成AI回复失败: {e}")
            self._stats["errors"] += 1
            return None
    
    def _build_prompt(self, message: DanmakuMessage) -> str:
        """构建提示词"""
        # 基础提示词
        prompt = f"""你是一个AI虚拟主播，正在直播间与观众互动。

观众 {message.username} 说：{message.content}

请用友好、有趣的语气回复观众的消息。回复要简洁明了，适合在直播弹幕中显示。
"""
        
        # 如果有记忆系统，添加上下文
        if self._memory:
            # 获取相关记忆
            memories = self._memory.search(message.content, top_k=3)
            if memories:
                memory_text = "\n".join([f"- {m.content}" for m in memories])
                prompt += f"\n相关记忆：\n{memory_text}"
        
        return prompt
    
    async def _send_danmaku_reply(self, platform_type: PlatformType, room_id: str, content: str):
        """发送弹幕回复"""
        try:
            if platform_type in self._platforms:
                platform = self._platforms[platform_type]
                success = await platform.send_danmaku(content)
                
                if success:
                    logger.info(f" 弹幕回复发送成功: {content}")
                else:
                    logger.info(f" 弹幕回复发送失败: {content}")
            
        except Exception as e:
            logger.info(f" 发送弹幕回复失败: {e}")
            self._stats["errors"] += 1
    
    async def _send_gift_thanks(self, message: GiftMessage):
        """发送礼物感谢"""
        try:
            # 生成感谢消息
            thanks_message = f"感谢 {message.username} 送的 {message.gift_name}！"
            
            # 发送弹幕感谢
            await self._send_danmaku_reply(message.platform, message.room_id, thanks_message)
            
        except Exception as e:
            logger.info(f" 发送礼物感谢失败: {e}")
            self._stats["errors"] += 1
    
    async def _generate_tts(self, text: str) -> Optional[str]:
        """生成TTS音频"""
        try:
            if not self._tts:
                return None
            
            # 调用TTS生成音频
            audio_path = await self._tts.synthesize(text)
            
            return audio_path
            
        except Exception as e:
            logger.info(f" 生成TTS音频失败: {e}")
            self._stats["errors"] += 1
            return None
    
    def _notify_response(self, response: LiveResponse):
        """通知回复回调"""
        for callback in self._response_callbacks:
            try:
                callback(response)
            except Exception as e:
                logger.info(f" 回调执行失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "connected_platforms": len(self._platforms),
            "platforms": [p.value for p in self._platforms.keys()],
            "total_danmaku": self._stats["total_danmaku"],
            "total_replies": self._stats["total_replies"],
            "total_gifts": self._stats["total_gifts"],
            "errors": self._stats["errors"],
            "auto_reply": self._auto_reply,
        }
    
    def get_platform_stats(self, platform_type: PlatformType) -> Optional[Dict[str, Any]]:
        """获取平台统计信息"""
        if platform_type in self._platforms:
            return self._platforms[platform_type].get_stats()
        return None
    
    def is_connected(self, platform_type: PlatformType) -> bool:
        """检查平台是否已连接"""
        return platform_type in self._platforms
    
    def get_connected_platforms(self) -> List[PlatformType]:
        """获取已连接的平台列表"""
        return list(self._platforms.keys())


# 全局直播桥梁实例
_live_bridge = None


def get_live_bridge(config: Dict[str, Any] = None) -> LiveBridge:
    """获取直播桥梁单例"""
    global _live_bridge
    if _live_bridge is None:
        _live_bridge = LiveBridge(config)
    return _live_bridge


# 导出主要类
__all__ = [
    'LiveResponse',
    'LiveBridge',
    'get_live_bridge',
]