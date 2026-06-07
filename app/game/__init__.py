"""
游戏感知框架模块

提供游戏感知和交互功能。

主要组件:
- GameAgent: 游戏代理接口
- MinecraftAgent: Minecraft游戏代理
- GameAgentManager: 游戏代理管理器

作者: 咕咕嘎嘎
日期: 2026-06-03
"""

import os
import asyncio
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# 版本信息
__version__ = "1.0.0"
__author__ = "咕咕嘎嘎"


class GameType(Enum):
    """游戏类型枚举"""
    MINECRAFT = "minecraft"
    FACTORIO = "factorio"
    TERRARIA = "terraria"
    STARDEW_VALLEY = "stardew_valley"
    GENERIC = "generic"


@dataclass
class GameState:
    """游戏状态"""
    game_type: GameType
    player_position: Dict[str, float] = None
    player_health: float = 100.0
    player_inventory: List[Dict[str, Any]] = None
    world_info: Dict[str, Any] = None
    entities: List[Dict[str, Any]] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.player_position is None:
            self.player_position = {"x": 0.0, "y": 0.0, "z": 0.0}
        if self.player_inventory is None:
            self.player_inventory = []
        if self.world_info is None:
            self.world_info = {}
        if self.entities is None:
            self.entities = []


@dataclass
class GameAction:
    """游戏动作"""
    action_type: str
    parameters: Dict[str, Any] = None
    priority: int = 0
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


class GameAgent:
    """游戏代理接口"""
    
    def __init__(self, game_type: GameType):
        self.game_type = game_type
        self.connected = False
        self.state = None
        self._state_callbacks: List[Callable] = []
        self._action_callbacks: List[Callable] = []
    
    def add_state_callback(self, callback: Callable):
        """添加状态回调"""
        self._state_callbacks.append(callback)
    
    def remove_state_callback(self, callback: Callable):
        """移除状态回调"""
        self._state_callbacks = [cb for cb in self._state_callbacks if cb != callback]
    
    def add_action_callback(self, callback: Callable):
        """添加动作回调"""
        self._action_callbacks.append(callback)
    
    def remove_action_callback(self, callback: Callable):
        """移除动作回调"""
        self._action_callbacks = [cb for cb in self._action_callbacks if cb != callback]
    
    def _notify_state(self, state: GameState):
        """通知状态回调"""
        for callback in self._state_callbacks:
            try:
                callback(state)
            except Exception as e:
                logger.info(f" 状态回调失败: {e}")
    
    def _notify_action(self, action: GameAction):
        """通知动作回调"""
        for callback in self._action_callbacks:
            try:
                callback(action)
            except Exception as e:
                logger.info(f" 动作回调失败: {e}")
    
    async def connect(self) -> bool:
        """连接到游戏"""
        raise NotImplementedError
    
    async def disconnect(self):
        """断开连接"""
        raise NotImplementedError
    
    async def get_state(self) -> Optional[GameState]:
        """获取游戏状态"""
        raise NotImplementedError
    
    async def execute_action(self, action: GameAction) -> bool:
        """执行游戏动作"""
        raise NotImplementedError
    
    async def send_command(self, command: str) -> bool:
        """发送命令"""
        raise NotImplementedError
    
    def is_connected(self) -> bool:
        """是否已连接"""
        return self.connected


class MinecraftAgent(GameAgent):
    """Minecraft游戏代理"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(GameType.MINECRAFT)
        self.config = config or {}
        self.host = self.config.get("host", "localhost")
        self.port = self.config.get("port", 25565)
        self.username = self.config.get("username", "AI_VTuber")
        self.password = self.config.get("password", "")
        
        # Minecraft特定状态
        self.world_name = ""
        self.game_mode = "survival"
        self.difficulty = "normal"
        
        logger.info(f" Minecraft代理初始化完成")
        logger.info(f" 服务器: {self.host}:{self.port}")
        logger.info(f" 用户名: {self.username}")
    
    async def connect(self) -> bool:
        """连接到Minecraft服务器"""
        try:
            # 这里应该实现实际的Minecraft连接
            # 由于Minecraft连接需要特定的库，这里只是示例
            logger.info(f" 连接到Minecraft服务器: {self.host}:{self.port}")
            
            # 模拟连接
            await asyncio.sleep(1)
            
            self.connected = True
            logger.info(" Minecraft连接成功")
            
            return True
            
        except Exception as e:
            logger.info(f" Minecraft连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开Minecraft连接"""
        try:
            if self.connected:
                logger.info(" 断开Minecraft连接")
                self.connected = False
        except Exception as e:
            logger.info(f" 断开Minecraft连接失败: {e}")
    
    async def get_state(self) -> Optional[GameState]:
        """获取Minecraft游戏状态"""
        try:
            if not self.connected:
                logger.info(" 未连接到Minecraft")
                return None
            
            # 这里应该获取实际的游戏状态
            # 由于Minecraft状态获取需要特定的库，这里只是示例
            
            # 模拟状态
            state = GameState(
                game_type=GameType.MINECRAFT,
                player_position={"x": 100.0, "y": 64.0, "z": 200.0},
                player_health=20.0,
                player_inventory=[
                    {"name": "diamond_sword", "count": 1},
                    {"name": "bread", "count": 64},
                ],
                world_info={
                    "world_name": self.world_name,
                    "game_mode": self.game_mode,
                    "difficulty": self.difficulty,
                    "time": 6000,
                    "weather": "clear",
                },
                entities=[
                    {"type": "zombie", "position": {"x": 105.0, "y": 64.0, "z": 195.0}},
                    {"type": "skeleton", "position": {"x": 95.0, "y": 64.0, "z": 205.0}},
                ],
                timestamp=asyncio.get_event_loop().time(),
            )
            
            self.state = state
            self._notify_state(state)
            
            return state
            
        except Exception as e:
            logger.info(f" 获取Minecraft状态失败: {e}")
            return None
    
    async def execute_action(self, action: GameAction) -> bool:
        """执行Minecraft动作"""
        try:
            if not self.connected:
                logger.info(" 未连接到Minecraft")
                return False
            
            # 这里应该执行实际的游戏动作
            # 由于Minecraft动作执行需要特定的库，这里只是示例
            
            action_type = action.action_type
            parameters = action.parameters
            
            logger.info(f" 执行Minecraft动作: {action_type}")
            logger.info(f" 参数: {parameters}")
            
            # 模拟动作执行
            await asyncio.sleep(0.1)
            
            # 通知动作回调
            self._notify_action(action)
            
            logger.info(f" Minecraft动作执行成功: {action_type}")
            return True
            
        except Exception as e:
            logger.info(f" Minecraft动作执行失败: {e}")
            return False
    
    async def send_command(self, command: str) -> bool:
        """发送Minecraft命令"""
        try:
            if not self.connected:
                logger.info(" 未连接到Minecraft")
                return False
            
            logger.info(f" 发送Minecraft命令: {command}")
            
            # 这里应该发送实际的命令
            # 由于Minecraft命令发送需要特定的库，这里只是示例
            
            # 模拟命令发送
            await asyncio.sleep(0.1)
            
            logger.info(f" Minecraft命令发送成功: {command}")
            return True
            
        except Exception as e:
            logger.info(f" Minecraft命令发送失败: {e}")
            return False
    
    async def chat(self, message: str) -> bool:
        """发送聊天消息"""
        return await self.send_command(f"say {message}")
    
    async def move(self, x: float, y: float, z: float) -> bool:
        """移动到指定位置"""
        action = GameAction(
            action_type="move",
            parameters={"x": x, "y": y, "z": z}
        )
        return await self.execute_action(action)
    
    async def attack(self, target: str) -> bool:
        """攻击目标"""
        action = GameAction(
            action_type="attack",
            parameters={"target": target}
        )
        return await self.execute_action(action)
    
    async def mine(self, block_type: str) -> bool:
        """挖掘方块"""
        action = GameAction(
            action_type="mine",
            parameters={"block_type": block_type}
        )
        return await self.execute_action(action)
    
    async def place(self, block_type: str, x: float, y: float, z: float) -> bool:
        """放置方块"""
        action = GameAction(
            action_type="place",
            parameters={"block_type": block_type, "x": x, "y": y, "z": z}
        )
        return await self.execute_action(action)


class GameAgentManager:
    """游戏代理管理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.storage_dir = self.config.get("storage_dir", "./cache/game")
        
        # 确保存储目录存在
        if not os.path.isabs(self.storage_dir):
            from app.shared_config import PROJECT_DIR
            self.storage_dir = os.path.join(PROJECT_DIR, self.storage_dir)
            self.storage_dir = os.path.normpath(self.storage_dir)
        
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # 游戏代理缓存
        self.agents: Dict[str, GameAgent] = {}
        
        logger.info(f" 游戏代理管理器初始化完成")
        logger.info(f" 存储目录: {self.storage_dir}")
    
    def create_agent(self, game_type: GameType, config: Dict[str, Any] = None) -> Optional[GameAgent]:
        """创建游戏代理"""
        try:
            if game_type == GameType.MINECRAFT:
                from .minecraft_agent import MinecraftAgent
                agent = MinecraftAgent(config)
            elif game_type == GameType.FACTORIO:
                from .factorio_agent import FactorioAgent
                agent = FactorioAgent(config)
            elif game_type == GameType.TERRARIA:
                from .terraria_agent import TerrariaAgent
                agent = TerrariaAgent(config)
            elif game_type == GameType.STARDEW_VALLEY:
                from .stardew_valley_agent import StardewValleyAgent
                agent = StardewValleyAgent(config)
            else:
                logger.info(f" 不支持的游戏类型: {game_type}")
                return None
            
            # 生成代理ID
            agent_id = f"{game_type.value}_{len(self.agents)}"
            self.agents[agent_id] = agent
            
            logger.info(f" 游戏代理创建成功: {agent_id}")
            return agent
            
        except Exception as e:
            logger.info(f" 游戏代理创建失败: {e}")
            return None
    
    def get_agent(self, agent_id: str) -> Optional[GameAgent]:
        """获取游戏代理"""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> List[str]:
        """列出所有代理"""
        return list(self.agents.keys())
    
    def remove_agent(self, agent_id: str):
        """移除游戏代理"""
        try:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                asyncio.create_task(agent.disconnect())
                del self.agents[agent_id]
                logger.info(f" 游戏代理移除成功: {agent_id}")
            else:
                logger.info(f" 游戏代理不存在: {agent_id}")
                
        except Exception as e:
            logger.info(f" 游戏代理移除失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_agents": len(self.agents),
            "agent_ids": list(self.agents.keys()),
            "storage_dir": self.storage_dir,
        }


# 全局游戏代理管理器实例
_game_agent_manager = None


def get_game_agent_manager(config: Dict[str, Any] = None) -> GameAgentManager:
    """获取游戏代理管理器单例"""
    global _game_agent_manager
    if _game_agent_manager is None:
        _game_agent_manager = GameAgentManager(config)
    return _game_agent_manager


def create_minecraft_agent(config: Dict[str, Any] = None) -> Optional[MinecraftAgent]:
    """创建Minecraft代理的便捷函数"""
    manager = get_game_agent_manager()
    return manager.create_agent(GameType.MINECRAFT, config)


# 导出主要类
__all__ = [
    'GameType',
    'GameState',
    'GameAction',
    'GameAgent',
    'MinecraftAgent',
    'GameAgentManager',
    'get_game_agent_manager',
    'create_minecraft_agent',
]