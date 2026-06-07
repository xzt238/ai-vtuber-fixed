"""
角色扮演模块
支持角色创建、角色扮演、剧情系统
"""

import os
import json
import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime

# 日志模块
logger = logging.getLogger("roleplay")

class CharacterPersonality(Enum):
    """角色性格"""
    FRIENDLY = "friendly"  # 友好
    SHY = "shy"  # 害羞
    CHEERFUL = "cheerful"  # 开朗
    CALM = "calm"  # 冷静
    TSUNDERE = "tsundere"  # 傲娇
    MYSTERIOUS = "mysterious"  # 神秘
    CUTE = "cute"  # 可爱
    COOL = "cool"  # 酷

class SpeakingStyle(Enum):
    """说话风格"""
    GENTLE = "gentle"  # 温柔
    ENERGETIC = "energetic"  # 活泼
    FORMAL = "formal"  # 正式
    CASUAL = "casual"  # 随意
    CUTE = "cute"  # 可爱
    COOL = "cool"  # 冷酷
    HUMOROUS = "humorous"  # 幽默
    SERIOUS = "serious"  # 严肃

@dataclass
class Character:
    """角色"""
    id: str
    name: str
    personality: CharacterPersonality = CharacterPersonality.FRIENDLY
    speaking_style: SpeakingStyle = SpeakingStyle.GENTLE
    description: str = ""
    avatar: str = ""
    voice_id: str = ""  # 语音ID
    system_prompt: str = ""  # 系统提示词
    greeting: str = ""  # 问候语
    examples: List[str] = field(default_factory=list)  # 示例对话
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class Story:
    """剧情"""
    id: str
    title: str
    description: str = ""
    setting: str = ""  # 场景设定
    characters: List[str] = field(default_factory=list)  # 角色ID列表
    plot_points: List[str] = field(default_factory=list)  # 剧情点
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class RoleplaySession:
    """角色扮演会话"""
    id: str
    character_id: str
    story_id: Optional[str] = None
    user_id: str = ""
    history: List[Dict[str, str]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)

class CharacterManager:
    """角色管理器"""
    
    def __init__(self, storage_dir: str = "./memory/characters"):
        self.storage_dir = Path(storage_dir)
        self.characters_file = self.storage_dir / "characters.json"
        self.characters: Dict[str, Character] = {}
        
        # 加载已有角色
        self._load_characters()
        
        # 如果没有角色，创建预设角色
        if not self.characters:
            self._create_preset_characters()
    
    def _load_characters(self):
        """加载角色"""
        try:
            if self.characters_file.exists():
                with open(self.characters_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for char_id, char_dict in data.items():
                        self.characters[char_id] = Character(**char_dict)
                logger.info(f"加载了 {len(self.characters)} 个角色")
        except Exception as e:
            logger.error(f"加载角色失败: {e}")
    
    def _save_characters(self):
        """保存角色"""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            
            data = {}
            for char_id, char in self.characters.items():
                data[char_id] = {
                    "id": char.id,
                    "name": char.name,
                    "personality": char.personality.value,
                    "speaking_style": char.speaking_style.value,
                    "description": char.description,
                    "avatar": char.avatar,
                    "voice_id": char.voice_id,
                    "system_prompt": char.system_prompt,
                    "greeting": char.greeting,
                    "examples": char.examples,
                    "metadata": char.metadata
                }
            
            with open(self.characters_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"保存角色失败: {e}")
    
    def _create_preset_characters(self):
        """创建预设角色"""
        presets = [
            Character(
                id="assistant",
                name="小助手",
                personality=CharacterPersonality.FRIENDLY,
                speaking_style=SpeakingStyle.GENTLE,
                description="一个友好、乐于助人的AI助手",
                system_prompt="你是一个友好、乐于助人的AI助手。你会用温柔、亲切的语气回答用户的问题。",
                greeting="你好！我是小助手，很高兴认识你！有什么我可以帮助你的吗？",
                examples=[
                    "你好呀！今天过得怎么样？",
                    "有什么我可以帮助你的吗？",
                    "这个问题我可以帮你解决！"
                ]
            ),
            Character(
                id="companion",
                name="小陪伴",
                personality=CharacterPersonality.CUTE,
                speaking_style=SpeakingStyle.CUTE,
                description="一个可爱、温暖的AI陪伴者",
                system_prompt="你是一个可爱、温暖的AI陪伴者。你会用可爱的语气和用户聊天，关心用户的心情。",
                greeting="呜喵～你好呀！我是小陪伴，让我陪在你身边吧！",
                examples=[
                    "呜喵～今天开心吗？",
                    "抱抱你～不要难过哦！",
                    "嘻嘻，和你聊天好开心！"
                ]
            ),
            Character(
                id="teacher",
                name="小老师",
                personality=CharacterPersonality.CALM,
                speaking_style=SpeakingStyle.FORMAL,
                description="一个耐心、专业的AI老师",
                system_prompt="你是一个耐心、专业的AI老师。你会用清晰、易懂的方式解释复杂的概念。",
                greeting="你好！我是小老师，准备好学习新知识了吗？",
                examples=[
                    "这个问题很好，让我来解释一下...",
                    "理解了吗？不理解的话我可以再讲一遍。",
                    "学习需要耐心，慢慢来！"
                ]
            ),
            Character(
                id="friend",
                name="小好友",
                personality=CharacterPersonality.CHEERFUL,
                speaking_style=SpeakingStyle.ENERGETIC,
                description="一个开朗、活力的AI朋友",
                system_prompt="你是一个开朗、活力的AI朋友。你会用活泼、热情的语气和用户聊天。",
                greeting="嘿！我是小好友！一起聊天吧！",
                examples=[
                    "嘿！今天有什么有趣的事吗？",
                    "太棒了！我也这么觉得！",
                    "哈哈哈，你真有趣！"
                ]
            ),
            Character(
                id="advisor",
                name="小顾问",
                personality=CharacterPersonality.MYSTERIOUS,
                speaking_style=SpeakingStyle.COOL,
                description="一个智慧、神秘的AI顾问",
                system_prompt="你是一个智慧、神秘的AI顾问。你会用深沉、有哲理的语气回答问题。",
                greeting="...你来了。我一直在等你。",
                examples=[
                    "这个问题...值得深思。",
                    "答案就在你心中。",
                    "让我为你指引方向。"
                ]
            )
        ]
        
        for char in presets:
            self.characters[char.id] = char
        
        self._save_characters()
        logger.info(f"创建了 {len(presets)} 个预设角色")
    
    def create_character(self, character_data: Dict[str, Any]) -> Optional[Character]:
        """创建角色"""
        try:
            char_id = character_data.get("id", f"char_{len(self.characters)}")
            
            character = Character(
                id=char_id,
                name=character_data.get("name", "未命名"),
                personality=CharacterPersonality(character_data.get("personality", "friendly")),
                speaking_style=SpeakingStyle(character_data.get("speaking_style", "gentle")),
                description=character_data.get("description", ""),
                avatar=character_data.get("avatar", ""),
                voice_id=character_data.get("voice_id", ""),
                system_prompt=character_data.get("system_prompt", ""),
                greeting=character_data.get("greeting", ""),
                examples=character_data.get("examples", []),
                metadata=character_data.get("metadata", {})
            )
            
            self.characters[char_id] = character
            self._save_characters()
            
            logger.info(f"角色创建成功: {char_id}")
            return character
            
        except Exception as e:
            logger.error(f"角色创建失败: {e}")
            return None
    
    def get_character(self, character_id: str) -> Optional[Character]:
        """获取角色"""
        return self.characters.get(character_id)
    
    def list_characters(self) -> List[Character]:
        """列出所有角色"""
        return list(self.characters.values())
    
    def update_character(self, character_id: str, updates: Dict[str, Any]) -> bool:
        """更新角色"""
        if character_id not in self.characters:
            return False
        
        try:
            char = self.characters[character_id]
            
            if "name" in updates:
                char.name = updates["name"]
            if "personality" in updates:
                char.personality = CharacterPersonality(updates["personality"])
            if "speaking_style" in updates:
                char.speaking_style = SpeakingStyle(updates["speaking_style"])
            if "description" in updates:
                char.description = updates["description"]
            if "system_prompt" in updates:
                char.system_prompt = updates["system_prompt"]
            if "greeting" in updates:
                char.greeting = updates["greeting"]
            if "examples" in updates:
                char.examples = updates["examples"]
            
            char.updated_at = datetime.now()
            self._save_characters()
            
            logger.info(f"角色更新成功: {character_id}")
            return True
            
        except Exception as e:
            logger.error(f"角色更新失败: {e}")
            return False
    
    def delete_character(self, character_id: str) -> bool:
        """删除角色"""
        if character_id not in self.characters:
            return False
        
        try:
            del self.characters[character_id]
            self._save_characters()
            logger.info(f"角色删除成功: {character_id}")
            return True
        except Exception as e:
            logger.error(f"角色删除失败: {e}")
            return False

class StoryManager:
    """剧情管理器"""
    
    def __init__(self, storage_dir: str = "./memory/stories"):
        self.storage_dir = Path(storage_dir)
        self.stories_file = self.storage_dir / "stories.json"
        self.stories: Dict[str, Story] = {}
        
        self._load_stories()
    
    def _load_stories(self):
        """加载剧情"""
        try:
            if self.stories_file.exists():
                with open(self.stories_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for story_id, story_dict in data.items():
                        self.stories[story_id] = Story(**story_dict)
                logger.info(f"加载了 {len(self.stories)} 个剧情")
        except Exception as e:
            logger.error(f"加载剧情失败: {e}")
    
    def _save_stories(self):
        """保存剧情"""
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            
            data = {}
            for story_id, story in self.stories.items():
                data[story_id] = {
                    "id": story.id,
                    "title": story.title,
                    "description": story.description,
                    "setting": story.setting,
                    "characters": story.characters,
                    "plot_points": story.plot_points,
                    "metadata": story.metadata
                }
            
            with open(self.stories_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"保存剧情失败: {e}")
    
    def create_story(self, story_data: Dict[str, Any]) -> Optional[Story]:
        """创建剧情"""
        try:
            story_id = story_data.get("id", f"story_{len(self.stories)}")
            
            story = Story(
                id=story_id,
                title=story_data.get("title", "未命名剧情"),
                description=story_data.get("description", ""),
                setting=story_data.get("setting", ""),
                characters=story_data.get("characters", []),
                plot_points=story_data.get("plot_points", []),
                metadata=story_data.get("metadata", {})
            )
            
            self.stories[story_id] = story
            self._save_stories()
            
            logger.info(f"剧情创建成功: {story_id}")
            return story
            
        except Exception as e:
            logger.error(f"剧情创建失败: {e}")
            return None
    
    def get_story(self, story_id: str) -> Optional[Story]:
        """获取剧情"""
        return self.stories.get(story_id)
    
    def list_stories(self) -> List[Story]:
        """列出所有剧情"""
        return list(self.stories.values())
    
    def delete_story(self, story_id: str) -> bool:
        """删除剧情"""
        if story_id not in self.stories:
            return False
        
        try:
            del self.stories[story_id]
            self._save_stories()
            logger.info(f"剧情删除成功: {story_id}")
            return True
        except Exception as e:
            logger.error(f"剧情删除失败: {e}")
            return False

class RoleplayManager:
    """角色扮演管理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        storage_dir = self.config.get("storage_dir", "./memory/roleplay")
        characters_dir = self.config.get("characters", {}).get("storage_dir", "./memory/characters")
        stories_dir = self.config.get("stories", {}).get("storage_dir", "./memory/stories")
        
        self.character_manager = CharacterManager(characters_dir)
        self.story_manager = StoryManager(stories_dir)
        
        # 活跃会话
        self.sessions: Dict[str, RoleplaySession] = {}
        
        logger.info(f"初始化完成")
    
    def start_session(self, character_id: str, user_id: str = "", 
                     story_id: str = None) -> Optional[RoleplaySession]:
        """开始角色扮演会话"""
        # 检查角色是否存在
        character = self.character_manager.get_character(character_id)
        if not character:
            logger.warning(f"角色不存在: {character_id}")
            return None
        
        # 创建会话
        session_id = f"session_{character_id}_{len(self.sessions)}"
        session = RoleplaySession(
            id=session_id,
            character_id=character_id,
            story_id=story_id,
            user_id=user_id
        )
        
        # 添加问候语
        if character.greeting:
            session.history.append({
                "role": "assistant",
                "content": character.greeting
            })
        
        self.sessions[session_id] = session
        
        logger.info(f"会话开始: {session_id}, 角色: {character.name}")
        return session
    
    def get_session(self, session_id: str) -> Optional[RoleplaySession]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def end_session(self, session_id: str) -> bool:
        """结束会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"会话结束: {session_id}")
            return True
        return False
    
    def get_character_prompt(self, character_id: str) -> str:
        """获取角色提示词"""
        character = self.character_manager.get_character(character_id)
        if not character:
            return ""
        
        # 构建完整的提示词
        prompt_parts = []
        
        if character.system_prompt:
            prompt_parts.append(character.system_prompt)
        
        if character.description:
            prompt_parts.append(f"角色描述: {character.description}")
        
        prompt_parts.append(f"性格: {character.personality.value}")
        prompt_parts.append(f"说话风格: {character.speaking_style.value}")
        
        if character.examples:
            prompt_parts.append("示例对话:")
            for example in character.examples[:3]:  # 最多3个示例
                prompt_parts.append(f"- {example}")
        
        return "\n".join(prompt_parts)
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "characters": len(self.character_manager.characters),
            "stories": len(self.story_manager.stories),
            "active_sessions": len(self.sessions),
            "characters_list": [c.name for c in self.character_manager.list_characters()]
        }

# 全局角色扮演管理器实例
_roleplay_manager: Optional[RoleplayManager] = None

def get_roleplay_manager(config: Dict[str, Any] = None) -> RoleplayManager:
    """获取角色扮演管理器实例"""
    global _roleplay_manager
    if _roleplay_manager is None:
        _roleplay_manager = RoleplayManager(config)
    return _roleplay_manager
