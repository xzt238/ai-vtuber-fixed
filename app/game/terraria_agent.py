import logging
"""
Terraria游戏代理实现

logger = logging.getLogger(__name__)

提供Terraria游戏的完整集成，包括：
- 通过tModLoader API连接到Terraria
- 获取游戏状态
- 执行游戏动作
- 发送聊天消息

作者: 咕咕嘎嘎
日期: 2026-06-03
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

from . import (
    GameType, GameState, GameAction, GameAgent
)


class TerrariaAgent(GameAgent):
    """Terraria游戏代理"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(GameType.TERRARIA)
        self.config = config or {}
        
        # 服务器配置
        self.host = self.config.get("host", "localhost")
        self.port = self.config.get("port", 7777)
        self.password = self.config.get("password", "")
        
        # RCON客户端（Terraria支持RCON）
        self._rcon = None
        
        # 状态轮询任务
        self._poll_task = None
        
        logger.info(f" Terraria代理初始化完成")
        logger.info(f" 服务器: {self.host}:{self.port}")
    
    async def connect(self) -> bool:
        """连接到Terraria服务器"""
        try:
            # 导入rcon库
            from rcon.source import RCONClient
            
            # 创建RCON客户端
            self._rcon = RCONClient(self.host, self.port)
            
            # 连接到服务器
            logger.info(f" 正在连接到Terraria服务器: {self.host}:{self.port}")
            
            # 使用asyncio运行同步的连接操作
            await asyncio.get_event_loop().run_in_executor(
                None, self._rcon.connect, self.password
            )
            
            self.connected = True
            logger.info(" Terraria连接成功")
            
            # 启动状态轮询
            self._poll_task = asyncio.create_task(self._poll_state())
            
            return True
            
        except ImportError:
            logger.info(" 未安装rcon库，请执行: pip install rcon")
            return False
        except Exception as e:
            logger.info(f" Terraria连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开Terraria连接"""
        try:
            # 停止状态轮询
            if self._poll_task:
                self._poll_task.cancel()
                try:
                    await self._poll_task
                except asyncio.CancelledError:
                    pass
            
            # 断开连接
            if self._rcon:
                await asyncio.get_event_loop().run_in_executor(
                    None, self._rcon.close
                )
                self._rcon = None
            
            self.connected = False
            logger.info(" Terraria连接已断开")
            
        except Exception as e:
            logger.info(f" Terraria断开连接失败: {e}")
    
    async def get_state(self) -> Optional[GameState]:
        """获取Terraria游戏状态"""
        try:
            if not self.connected or not self._rcon:
                logger.info(" 未连接到Terraria")
                return None
            
            # 获取游戏状态
            # Terraria RCON命令
            players_info = await self.send_command("/playing")
            time_info = await self.send_command("/time")
            world_info = await self.send_command("/world")
            
            # 解析玩家信息
            players = self._parse_players(players_info)
            
            # 创建游戏状态
            state = GameState(
                game_type=GameType.TERRARIA,
                player_position={"x": 0, "y": 0, "z": 0},
                player_health=100.0,
                player_inventory=[],
                world_info={
                    "time": time_info,
                    "world": world_info,
                    "players": players
                },
                entities=[],
                timestamp=asyncio.get_event_loop().time()
            )
            
            self.state = state
            self._notify_state(state)
            
            return state
            
        except Exception as e:
            logger.info(f" 获取Terraria状态失败: {e}")
            return None
    
    def _parse_players(self, players_info: str) -> List[Dict[str, Any]]:
        """解析玩家信息"""
        players = []
        
        if not players_info:
            return players
        
        # 解析玩家列表
        lines = players_info.strip().split("\n")
        for line in lines:
            if line.strip() and "playing" not in line.lower():
                players.append({"name": line.strip()})
        
        return players
    
    async def execute_action(self, action: GameAction) -> bool:
        """执行Terraria动作"""
        try:
            if not self.connected or not self._rcon:
                logger.info(" 未连接到Terraria")
                return False
            
            action_type = action.action_type
            parameters = action.parameters
            
            logger.info(f" 执行Terraria动作: {action_type}")
            logger.info(f" 参数: {parameters}")
            
            # 根据动作类型执行
            if action_type == "chat":
                await self._chat(parameters)
            elif action_type == "command":
                await self._command(parameters)
            elif action_type == "give":
                await self._give(parameters)
            elif action_type == "spawn":
                await self._spawn(parameters)
            elif action_type == "tp":
                await self._teleport(parameters)
            else:
                logger.info(f" 未知的动作类型: {action_type}")
                return False
            
            # 通知动作回调
            self._notify_action(action)
            
            logger.info(f" Terraria动作执行成功: {action_type}")
            return True
            
        except Exception as e:
            logger.info(f" Terraria动作执行失败: {e}")
            return False
    
    async def _chat(self, parameters: Dict[str, Any]):
        """发送聊天消息"""
        message = parameters.get("message", "")
        
        logger.info(f" 发送聊天: {message}")
        
        # 发送聊天命令
        await self.send_command(f"/say {message}")
    
    async def _command(self, parameters: Dict[str, Any]):
        """执行命令"""
        command = parameters.get("command", "")
        
        logger.info(f" 执行命令: {command}")
        
        # 发送命令
        await self.send_command(command)
    
    async def _give(self, parameters: Dict[str, Any]):
        """给予物品"""
        player = parameters.get("player", "")
        item = parameters.get("item", "")
        count = parameters.get("count", 1)
        
        logger.info(f" 给予物品: {player} {item} x{count}")
        
        # 发送给予命令
        await self.send_command(f"/give {player} {item} {count}")
    
    async def _spawn(self, parameters: Dict[str, Any]):
        """生成实体"""
        entity = parameters.get("entity", "")
        count = parameters.get("count", 1)
        
        logger.info(f" 生成实体: {entity} x{count}")
        
        # 发送生成命令
        await self.send_command(f"/spawn {entity} {count}")
    
    async def _teleport(self, parameters: Dict[str, Any]):
        """传送玩家"""
        player = parameters.get("player", "")
        x = parameters.get("x", 0)
        y = parameters.get("y", 0)
        
        logger.info(f" 传送玩家: {player} to ({x}, {y})")
        
        # 发送传送命令
        await self.send_command(f"/tp {player} {x} {y}")
    
    async def send_command(self, command: str) -> Optional[str]:
        """发送RCON命令"""
        try:
            if not self.connected or not self._rcon:
                logger.info(" 未连接到Terraria")
                return None
            
            logger.info(f" 发送命令: {command}")
            
            # 发送命令
            response = await asyncio.get_event_loop().run_in_executor(
                None, self._rcon.command, command
            )
            
            logger.info(f" 命令响应: {response}")
            return response
            
        except Exception as e:
            logger.info(f" 命令发送失败: {e}")
            return None
    
    async def chat(self, message: str) -> bool:
        """发送聊天消息"""
        return await self._chat({"message": message})
    
    async def give(self, player: str, item: str, count: int = 1) -> bool:
        """给予物品"""
        action = GameAction(
            action_type="give",
            parameters={"player": player, "item": item, "count": count}
        )
        return await self.execute_action(action)
    
    async def spawn(self, entity: str, count: int = 1) -> bool:
        """生成实体"""
        action = GameAction(
            action_type="spawn",
            parameters={"entity": entity, "count": count}
        )
        return await self.execute_action(action)
    
    async def teleport(self, player: str, x: int, y: int) -> bool:
        """传送玩家"""
        action = GameAction(
            action_type="tp",
            parameters={"player": player, "x": x, "y": y}
        )
        return await self.execute_action(action)
    
    async def _poll_state(self):
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
__all__ = ['TerrariaAgent']