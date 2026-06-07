"""
Discord Bot实现

提供Discord Bot的完整集成，包括：
- 连接到Discord
- 接收消息
- 发送消息
- 处理命令
- 文件上传

作者: 咕咕嘎嘎
日期: 2026-06-03
"""

import os
import asyncio
from typing import Dict, Any, List

from . import Bot, BotMessage
import logging

logger = logging.getLogger(__name__)


class DiscordBot(Bot):
    """Discord Bot实现"""
    
    def __init__(self, config: Dict[str, Any] = None) -> None:
        """内部方法"""
        super().__init__("discord_bot", "discord")
        self.config = config or {}
        
        # Discord配置
        self.token = self.config.get("token", "")
        self.guild_id = self.config.get("guild_id", "")
        self.channel_id = self.config.get("channel_id", "")
        self.command_prefix = self.config.get("command_prefix", "!")
        
        # Discord客户端
        self._client = None
        
        # 消息轮询任务
        self._poll_task = None
        
        logger.info(f" Discord Bot初始化完成")
        logger.info(f" 命令前缀: {self.command_prefix}")
    
    async def connect(self) -> bool:
        """连接到Discord"""
        try:
            # 导入discord库
            import discord
            from discord.ext import commands
            
            # 创建Bot实例
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            
            self._client = commands.Bot(
                command_prefix=self.command_prefix,
                intents=intents
            )
            
            # 注册事件
            @self._client.event
            async def on_ready() -> None:
                """On ready"""
                logger.info(f" Discord Bot已登录: {self._client.user}")
                self.connected = True
            
            @self._client.event
            async def on_message(message) -> None:
                """On message"""
                # 忽略自己的消息
                if message.author == self._client.user:
                    return
                
                # 创建BotMessage
                bot_message = BotMessage(
                    id=str(message.id),
                    platform="discord",
                    channel_id=str(message.channel.id),
                    user_id=str(message.author.id),
                    username=str(message.author),
                    content=message.content,
                    timestamp=message.created_at,
                    message_type="text",
                    metadata={
                        "guild_id": str(message.guild.id) if message.guild else None,
                        "channel_name": str(message.channel),
                    }
                )
                
                # 通知消息回调
                self._notify_message(bot_message)
                
                # 处理命令
                await self._client.process_commands(message)
            
            # 注册命令
            @self._client.command(name="ping")
            async def ping(ctx) -> None:
                """Ping"""
                await ctx.send("Pong!")
            
            @self._client.command(name="help")
            async def help_command(ctx) -> None:
                """Help command"""
                help_text = """
**可用命令:**
!ping - 测试连接
!help - 显示帮助
!status - 显示状态
!chat <消息> - 与AI聊天
"""
                await ctx.send(help_text)
            
            @self._client.command(name="status")
            async def status(ctx) -> None:
                """Status"""
                status_text = f"""
**Bot状态:**
- 连接状态: {'已连接' if self.connected else '未连接'}
- 服务器数量: {len(self._client.guilds)}
- 用户数量: {len(self._client.users)}
"""
                await ctx.send(status_text)
            
            @self._client.command(name="chat")
            async def chat(ctx, *, message: str) -> None:
                """Chat"""
                # 这里应该调用LLM生成回复
                # 简化实现，直接回复
                await ctx.send(f"收到消息: {message}")
            
            # 连接到Discord
            logger.info(f" 正在连接到Discord...")
            
            # 启动Bot
            asyncio.create_task(self._client.start(self.token))
            
            # 等待连接
            for _ in range(30):  # 最多等待30秒
                if self.connected:
                    break
                await asyncio.sleep(1)
            
            if self.connected:
                logger.info(" Discord Bot连接成功")
                return True
            else:
                logger.info(" Discord Bot连接超时")
                return False
            
        except ImportError:
            logger.info(" 未安装discord.py库，请执行: pip install discord.py")
            return False
        except Exception as e:
            logger.info(f" Discord Bot连接失败: {e}")
            return False
    
    async def disconnect(self) -> None:
        """断开Discord连接"""
        try:
            # 停止轮询
            if self._poll_task:
                self._poll_task.cancel()
                try:
                    await self._poll_task
                except asyncio.CancelledError:
                    pass
            
            # 断开连接
            if self._client:
                await self._client.close()
                self._client = None
            
            self.connected = False
            logger.info(" Discord Bot已断开")
            
        except Exception as e:
            logger.info(f" Discord Bot断开失败: {e}")
    
    async def send_message(self, channel_id: str, content: str, message_type: str = "text") -> bool:
        """发送Discord消息"""
        try:
            if not self.connected or not self._client:
                logger.info(" Discord Bot未连接")
                return False
            
            # 获取频道
            channel = self._client.get_channel(int(channel_id))
            if not channel:
                logger.info(f" 频道不存在: {channel_id}")
                return False
            
            # 发送消息
            await channel.send(content)
            
            logger.info(f" Discord消息发送成功: {content}")
            return True
            
        except Exception as e:
            logger.info(f" Discord消息发送失败: {e}")
            return False
    
    async def send_file(self, channel_id: str, file_path: str, caption: str = "") -> bool:
        """发送Discord文件"""
        try:
            if not self.connected or not self._client:
                logger.info(" Discord Bot未连接")
                return False
            
            # 获取频道
            channel = self._client.get_channel(int(channel_id))
            if not channel:
                logger.info(f" 频道不存在: {channel_id}")
                return False
            
            # 发送文件
            import discord
            file = discord.File(file_path)
            await channel.send(content=caption, file=file)
            
            logger.info(f" Discord文件发送成功: {file_path}")
            return True
            
        except Exception as e:
            logger.info(f" Discord文件发送失败: {e}")
            return False
    
    async def send_image(self, channel_id: str, image_path: str, caption: str = "") -> bool:
        """发送Discord图片"""
        return await self.send_file(channel_id, image_path, caption)
    
    def get_guilds(self) -> List[Dict[str, Any]]:
        """获取服务器列表"""
        if not self._client:
            return []
        
        return [
            {
                "id": str(guild.id),
                "name": guild.name,
                "member_count": guild.member_count,
            }
            for guild in self._client.guilds
        ]
    
    def get_channels(self, guild_id: str) -> List[Dict[str, Any]]:
        """获取频道列表"""
        if not self._client:
            return []
        
        guild = self._client.get_guild(int(guild_id))
        if not guild:
            return []
        
        return [
            {
                "id": str(channel.id),
                "name": channel.name,
                "type": str(channel.type),
            }
            for channel in guild.text_channels
        ]


# 导出主要类
__all__ = ['DiscordBot']