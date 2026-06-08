"""
Stardew Valley游戏代理实现

提供Stardew Valley游戏的完整集成，包括：
- 通过SMAPI连接到Stardew Valley
- 获取游戏状态
- 执行游戏动作
- 发送聊天消息

作者: 咕咕嘎嘎
日期: 2026-06-03
"""

import time
import os
import json
import asyncio
from typing import Optional, Dict, Any

from . import (
    GameType, GameState, GameAction, GameAgent
)
import logging

logger = logging.getLogger(__name__)


class StardewValleyAgent(GameAgent):
    """Stardew Valley游戏代理"""
    
    def __init__(self, config: Dict[str, Any] = None) -> None:
        super().__init__(GameType.STARDEW_VALLEY)
        self.config = config or {}
        
        # SMAPI配置
        self.host = self.config.get("host", "localhost")
        self.port = self.config.get("port", 24642)
        self.api_key = self.config.get("api_key", "")
        
        # HTTP客户端
        self._session = None
        
        # API基础URL
        self._api_base = f"http://{self.host}:{self.port}/api"
        
        # 状态轮询任务
        self._poll_task = None
        
        logger.info(f" Stardew Valley代理初始化完成")
        logger.info(f" SMAPI服务器: {self.host}:{self.port}")
    
    async def connect(self) -> bool:
        """连接到Stardew Valley SMAPI服务器"""
        try:
            import aiohttp
            
            # 创建HTTP会话
            self._session = aiohttp.ClientSession()
            
            # 测试连接
            logger.info(f" 正在连接到Stardew Valley SMAPI服务器: {self.host}:{self.port}")
            
            # 测试API
            async with self._session.get(f"{self._api_base}/info") as response:
                if response.status == 200:
                    info = await response.json()
                    logger.info(f" SMAPI版本: {info.get('version', '未知')}")
                    
                    self.connected = True
                    logger.info(" Stardew Valley连接成功")
                    
                    # 启动状态轮询
                    self._poll_task = asyncio.create_task(self._poll_state())
                    
                    return True
                else:
                    logger.info(f" Stardew Valley连接失败: HTTP {response.status}")
                    return False
            
        except ImportError:
            logger.info(" 未安装aiohttp库，请执行: pip install aiohttp")
            return False
        except Exception as e:
            logger.info(f" Stardew Valley连接失败: {e}")
            return False
    
    async def disconnect(self) -> None:
        """断开Stardew Valley连接"""
        try:
            # 停止状态轮询
            if self._poll_task:
                self._poll_task.cancel()
                try:
                    await self._poll_task
                except asyncio.CancelledError:
                    pass
            
            # 关闭会话
            if self._session:
                await self._session.close()
                self._session = None
            
            self.connected = False
            logger.info(" Stardew Valley连接已断开")
            
        except Exception as e:
            logger.info(f" Stardew Valley断开连接失败: {e}")
    
    async def get_state(self) -> Optional[GameState]:
        """获取Stardew Valley游戏状态"""
        try:
            if not self.connected or not self._session:
                logger.info(" 未连接到Stardew Valley")
                return None
            
            # 获取游戏状态
            async with self._session.get(
                f"{self._api_base}/game",
                headers=self._get_headers()
            ) as response:
                if response.status == 200:
                    game_info = await response.json()
                    
                    # 获取玩家信息
                    player_info = game_info.get("player", {})
                    
                    # 获取位置
                    position = {
                        "x": player_info.get("x", 0),
                        "y": player_info.get("y", 0),
                        "z": 0
                    }
                    
                    # 获取生命值
                    health = player_info.get("health", 100)
                    
                    # 获取物品栏
                    inventory = []
                    for item in player_info.get("inventory", []):
                        if item:
                            inventory.append({
                                "name": item.get("name", ""),
                                "count": item.get("stack", 1),
                                "quality": item.get("quality", 0)
                            })
                    
                    # 获取世界信息
                    world_info = {
                        "time": game_info.get("time", 0),
                        "day": game_info.get("day", 1),
                        "season": game_info.get("season", "spring"),
                        "year": game_info.get("year", 1),
                        "weather": game_info.get("weather", "sunny")
                    }
                    
                    # 创建游戏状态
                    state = GameState(
                        game_type=GameType.STARDEW_VALLEY,
                        player_position=position,
                        player_health=health,
                        player_inventory=inventory,
                        world_info=world_info,
                        entities=[],
                        timestamp=asyncio.get_event_loop().time()
                    )
                    
                    self.state = state
                    self._notify_state(state)
                    
                    return state
                else:
                    logger.info(f" 获取游戏状态失败: HTTP {response.status}")
                    return None
            
        except Exception as e:
            logger.info(f" 获取Stardew Valley状态失败: {e}")
            return None
    
    async def execute_action(self, action: GameAction) -> bool:
        """执行Stardew Valley动作"""
        try:
            if not self.connected or not self._session:
                logger.info(" 未连接到Stardew Valley")
                return False
            
            action_type = action.action_type
            parameters = action.parameters
            
            logger.info(f" 执行Stardew Valley动作: {action_type}")
            logger.info(f" 参数: {parameters}")
            
            # 根据动作类型执行
            if action_type == "chat":
                await self._chat(parameters)
            elif action_type == "command":
                await self._command(parameters)
            elif action_type == "give":
                await self._give(parameters)
            elif action_type == "warp":
                await self._warp(parameters)
            elif action_type == "time":
                await self._set_time(parameters)
            else:
                logger.info(f" 未知的动作类型: {action_type}")
                return False
            
            # 通知动作回调
            self._notify_action(action)
            
            logger.info(f" Stardew Valley动作执行成功: {action_type}")
            return True
            
        except Exception as e:
            logger.info(f" Stardew Valley动作执行失败: {e}")
            return False
    
    async def _chat(self, parameters: Dict[str, Any]) -> None:
        """发送聊天消息"""
        message = parameters.get("message", "")
        
        logger.info(f" 发送聊天: {message}")
        
        # 发送聊天命令
        await self.send_command(f"say {message}")
    
    async def _command(self, parameters: Dict[str, Any]) -> None:
        """执行命令"""
        command = parameters.get("command", "")
        
        logger.info(f" 执行命令: {command}")
        
        # 发送命令
        await self.send_command(command)
    
    async def _give(self, parameters: Dict[str, Any]) -> None:
        """给予物品"""
        player = parameters.get("player", "")
        item = parameters.get("item", "")
        count = parameters.get("count", 1)
        
        logger.info(f" 给予物品: {player} {item} x{count}")
        
        # 发送给予命令
        await self.send_command(f"player_additem {item} {count}")
    
    async def _warp(self, parameters: Dict[str, Any]) -> None:
        """传送到位置"""
        location = parameters.get("location", "")
        x = parameters.get("x", 0)
        y = parameters.get("y", 0)
        
        logger.info(f" 传送到: {location} ({x}, {y})")
        
        # 发送传送命令
        await self.send_command(f"world_settime {location} {x} {y}")
    
    async def _set_time(self, parameters: Dict[str, Any]) -> None:
        """设置时间"""
        time = parameters.get("time", 0)
        
        logger.info(f" 设置时间: {time}")
        
        # 发送时间命令
        await self.send_command(f"world_settime {time}")
    
    async def send_command(self, command: str) -> Optional[str]:
        """发送SMAPI命令"""
        try:
            if not self.connected or not self._session:
                logger.info(" 未连接到Stardew Valley")
                return None
            
            logger.info(f" 发送命令: {command}")
            
            # 发送命令
            async with self._session.post(
                f"{self._api_base}/command",
                json={"command": command},
                headers=self._get_headers()
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f" 命令响应: {result}")
                    return result.get("result", "")
                else:
                    logger.info(f" 命令发送失败: HTTP {response.status}")
                    return None
            
        except Exception as e:
            logger.info(f" 命令发送失败: {e}")
            return None
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers
    
    async def chat(self, message: str) -> bool:
        """发送聊天消息"""
        return await self._chat({"message": message})
    
    async def give(self, item: str, count: int = 1) -> bool:
        """给予物品"""
        action = GameAction(
            action_type="give",
            parameters={"item": item, "count": count}
        )
        return await self.execute_action(action)
    
    async def warp(self, location: str, x: int = 0, y: int = 0) -> bool:
        """传送到位置"""
        action = GameAction(
            action_type="warp",
            parameters={"location": location, "x": x, "y": y}
        )
        return await self.execute_action(action)
    
    async def set_time(self, time: int) -> bool:
        """设置时间"""
        action = GameAction(
            action_type="time",
            parameters={"time": time}
        )
        return await self.execute_action(action)
    
    async def _poll_state(self) -> None:
        """轮询游戏状态"""
        try:
            while self.connected:
                try:
                    # 获取游戏状态
                    await self.get_state()
                    
                    # 等待一段时间再轮询
                    await asyncio.sleep(5)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.info(f" 状态轮询失败: {e}")
                    await asyncio.sleep(10)
            
        except asyncio.CancelledError:
            pass


# 导出主要类
__all__ = ['StardewValleyAgent']