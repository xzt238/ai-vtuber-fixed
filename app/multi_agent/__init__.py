import logging
"""
多AI群聊模块

logger = logging.getLogger(__name__)

提供多角色对话场景支持。

主要组件:
- Agent: AI代理接口
- AgentManager: 代理管理器
- ConversationManager: 对话管理器
- MultiAgentChat: 多Agent群聊

作者: 咕咕嘎嘎
日期: 2026-06-03
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import uuid

# 版本信息
__version__ = "1.0.0"
__author__ = "咕咕嘎嘎"


@dataclass
class AgentPersonality:
    """AI代理人格"""
    name: str
    description: str
    personality: str
    speaking_style: str
    background: str
    avatar: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "personality": self.personality,
            "speaking_style": self.speaking_style,
            "background": self.background,
            "avatar": self.avatar,
        }


@dataclass
class AgentMessage:
    """代理消息"""
    id: str
    agent_id: str
    agent_name: str
    content: str
    timestamp: datetime
    message_type: str = "text"  # text, image, action
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now()


class Agent:
    """AI代理接口"""
    
    def __init__(self, agent_id: str, personality: AgentPersonality, llm_callback: Callable = None):
        self.agent_id = agent_id
        self.personality = personality
        self.llm_callback = llm_callback
        self.conversation_history: List[AgentMessage] = []
        self.is_active = True
        
        logger.info(f" AI代理初始化完成: {personality.name}")
    
    def set_llm_callback(self, callback: Callable):
        """设置LLM回调函数"""
        self.llm_callback = callback
    
    async def generate_response(self, context: str, conversation_history: List[AgentMessage] = None) -> Optional[str]:
        """生成回复"""
        try:
            if self.llm_callback is None:
                return self._generate_default_response(context)
            
            # 构建提示词
            prompt = self._build_prompt(context, conversation_history)
            
            # 调用LLM
            response = await self.llm_callback(prompt)
            
            # 提取回复
            if isinstance(response, dict):
                return response.get("text", response.get("content", ""))
            elif isinstance(response, str):
                return response
            else:
                return str(response)
                
        except Exception as e:
            logger.info(f" 代理回复生成失败: {e}")
            return self._generate_default_response(context)
    
    def _build_prompt(self, context: str, conversation_history: List[AgentMessage] = None) -> str:
        """构建提示词"""
        # 构建人格描述
        personality_desc = f"""
你是一个名为"{self.personality.name}"的AI角色。

人格描述：{self.personality.personality}
说话风格：{self.personality.speaking_style}
背景故事：{self.personality.background}

当前对话上下文：
{context}
"""
        
        # 添加对话历史
        if conversation_history:
            history_text = "\n最近对话：\n"
            for msg in conversation_history[-5:]:  # 只保留最近5条
                history_text += f"{msg.agent_name}: {msg.content}\n"
            personality_desc += history_text
        
        personality_desc += "\n请以你的人格和说话风格回复："
        
        return personality_desc
    
    def _generate_default_response(self, context: str) -> str:
        """生成默认回复"""
        # 根据人格生成默认回复
        if "你好" in context or "hi" in context.lower():
            return f"你好！我是{self.personality.name}。{self.personality.personality}"
        elif "谢谢" in context or "感谢" in context:
            return f"不客气！很高兴能帮到你。"
        else:
            return f"我是{self.personality.name}，{self.personality.speaking_style}"
    
    def add_message(self, content: str, message_type: str = "text") -> AgentMessage:
        """添加消息到历史"""
        message = AgentMessage(
            id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            agent_name=self.personality.name,
            content=content,
            timestamp=datetime.now(),
            message_type=message_type,
        )
        self.conversation_history.append(message)
        return message
    
    def get_history(self, limit: int = 10) -> List[AgentMessage]:
        """获取对话历史"""
        return self.conversation_history[-limit:]


class AgentManager:
    """代理管理器"""
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        logger.info(" 代理管理器初始化完成")
    
    def create_agent(self, personality: AgentPersonality, llm_callback: Callable = None) -> Agent:
        """创建代理"""
        agent_id = f"agent_{len(self.agents) + 1}"
        agent = Agent(agent_id, personality, llm_callback)
        self.agents[agent_id] = agent
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """获取代理"""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> List[str]:
        """列出所有代理"""
        return list(self.agents.keys())
    
    def remove_agent(self, agent_id: str):
        """移除代理"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info(f" 代理移除成功: {agent_id}")
    
    def get_agent_by_name(self, name: str) -> Optional[Agent]:
        """根据名称获取代理"""
        for agent in self.agents.values():
            if agent.personality.name == name:
                return agent
        return None


class ConversationManager:
    """对话管理器"""
    
    def __init__(self):
        self.conversations: Dict[str, List[AgentMessage]] = {}
        logger.info(" 对话管理器初始化完成")
    
    def create_conversation(self, conversation_id: str = None) -> str:
        """创建对话"""
        if conversation_id is None:
            conversation_id = f"conv_{len(self.conversations) + 1}"
        self.conversations[conversation_id] = []
        return conversation_id
    
    def add_message(self, conversation_id: str, message: AgentMessage):
        """添加消息到对话"""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        self.conversations[conversation_id].append(message)
    
    def get_conversation(self, conversation_id: str, limit: int = 20) -> List[AgentMessage]:
        """获取对话历史"""
        if conversation_id in self.conversations:
            return self.conversations[conversation_id][-limit:]
        return []
    
    def list_conversations(self) -> List[str]:
        """列出所有对话"""
        return list(self.conversations.keys())
    
    def delete_conversation(self, conversation_id: str):
        """删除对话"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]


class MultiAgentChat:
    """多Agent群聊"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.agent_manager = AgentManager()
        self.conversation_manager = ConversationManager()
        
        # 群聊配置
        self.max_agents = self.config.get("max_agents", 10)
        self.conversation_timeout = self.config.get("conversation_timeout", 3600)  # 1小时
        
        # 回调函数
        self._message_callbacks: List[Callable] = []
        
        logger.info(" 多Agent群聊初始化完成")
    
    def add_message_callback(self, callback: Callable):
        """添加消息回调"""
        self._message_callbacks.append(callback)
    
    def remove_message_callback(self, callback: Callable):
        """移除消息回调"""
        self._message_callbacks = [cb for cb in self._message_callbacks if cb != callback]
    
    def _notify_message(self, message: AgentMessage):
        """通知消息回调"""
        for callback in self._message_callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.info(f" 消息回调失败: {e}")
    
    def create_agent(self, personality: AgentPersonality, llm_callback: Callable = None) -> Agent:
        """创建代理"""
        if len(self.agent_manager.agents) >= self.max_agents:
            logger.info(f" 已达到最大代理数量: {self.max_agents}")
            return None
        
        return self.agent_manager.create_agent(personality, llm_callback)
    
    def start_conversation(self, conversation_id: str = None) -> str:
        """开始对话"""
        return self.conversation_manager.create_conversation(conversation_id)
    
    async def send_message(self, conversation_id: str, agent_id: str, content: str) -> bool:
        """发送消息"""
        try:
            # 获取代理
            agent = self.agent_manager.get_agent(agent_id)
            if agent is None:
                logger.info(f" 代理不存在: {agent_id}")
                return False
            
            # 创建消息
            message = agent.add_message(content)
            
            # 添加到对话
            self.conversation_manager.add_message(conversation_id, message)
            
            # 通知消息回调
            self._notify_message(message)
            
            logger.info(f" 消息发送成功: {agent.personality.name}: {content}")
            return True
            
        except Exception as e:
            logger.info(f" 消息发送失败: {e}")
            return False
    
    async def generate_response(self, conversation_id: str, agent_id: str, context: str = None) -> Optional[str]:
        """生成回复"""
        try:
            # 获取代理
            agent = self.agent_manager.get_agent(agent_id)
            if agent is None:
                logger.info(f" 代理不存在: {agent_id}")
                return None
            
            # 获取对话历史
            conversation_history = self.conversation_manager.get_conversation(conversation_id)
            
            # 生成回复
            response = await agent.generate_response(context or "", conversation_history)
            
            if response:
                # 添加回复到对话
                await self.send_message(conversation_id, agent_id, response)
            
            return response
            
        except Exception as e:
            logger.info(f" 回复生成失败: {e}")
            return None
    
    async def multi_agent_conversation(self, conversation_id: str, topic: str, rounds: int = 3) -> List[AgentMessage]:
        """多代理对话"""
        try:
            messages = []
            
            for round_num in range(rounds):
                logger.info(f" 对话轮次: {round_num + 1}/{rounds}")
                
                # 每个代理轮流发言
                for agent_id, agent in self.agent_manager.agents.items():
                    if not agent.is_active:
                        continue
                    
                    # 生成上下文
                    context = f"话题: {topic}\n轮次: {round_num + 1}\n当前发言者: {agent.personality.name}"
                    
                    # 生成回复
                    response = await self.generate_response(conversation_id, agent_id, context)
                    
                    if response:
                        # 获取消息
                        conversation_history = self.conversation_manager.get_conversation(conversation_id)
                        if conversation_history:
                            messages.append(conversation_history[-1])
            
            return messages
            
        except Exception as e:
            logger.info(f" 多代理对话失败: {e}")
            return []
    
    def get_conversation_history(self, conversation_id: str, limit: int = 20) -> List[AgentMessage]:
        """获取对话历史"""
        return self.conversation_manager.get_conversation(conversation_id, limit)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_agents": len(self.agent_manager.agents),
            "total_conversations": len(self.conversation_manager.conversations),
            "agent_names": [agent.personality.name for agent in self.agent_manager.agents.values()],
        }


# 全局多Agent群聊实例
_multi_agent_chat = None


def get_multi_agent_chat(config: Dict[str, Any] = None) -> MultiAgentChat:
    """获取多Agent群聊单例"""
    global _multi_agent_chat
    if _multi_agent_chat is None:
        _multi_agent_chat = MultiAgentChat(config)
    return _multi_agent_chat


def create_agent(personality: AgentPersonality, llm_callback: Callable = None) -> Agent:
    """创建代理的便捷函数"""
    chat = get_multi_agent_chat()
    return chat.create_agent(personality, llm_callback)


async def start_multi_agent_conversation(topic: str, rounds: int = 3) -> List[AgentMessage]:
    """开始多代理对话的便捷函数"""
    chat = get_multi_agent_chat()
    conversation_id = chat.start_conversation()
    return await chat.multi_agent_conversation(conversation_id, topic, rounds)


# 导出主要类
__all__ = [
    'AgentPersonality',
    'AgentMessage',
    'Agent',
    'AgentManager',
    'ConversationManager',
    'MultiAgentChat',
    'get_multi_agent_chat',
    'create_agent',
    'start_multi_agent_conversation',
]