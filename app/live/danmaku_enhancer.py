"""
弹幕增强模块
提供智能弹幕回复、礼物感谢、自动互动等功能
"""

import asyncio
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

class ReplyStrategy(Enum):
    """回复策略"""
    IMMEDIATE = "immediate"      # 立即回复
    BATCH = "batch"              # 批量回复
    SMART = "smart"              # 智能回复（根据内容决定）
    KEYWORD = "keyword"          # 关键词触发

@dataclass
class DanmakuReply:
    """弹幕回复"""
    original_message: str        # 原始消息
    reply_content: str           # 回复内容
    user_id: str                 # 用户ID
    username: str                # 用户名
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 0            # 优先级 (0-10)

@dataclass
class GiftResponse:
    """礼物感谢"""
    user_id: str
    username: str
    gift_name: str
    gift_count: int
    thank_message: str
    timestamp: datetime = field(default_factory=datetime.now)

class DanmakuEnhancer:
    """弹幕增强器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # 回复策略
        self.reply_strategy = ReplyStrategy(self.config.get("reply_strategy", "smart"))
        
        # 关键词触发词
        self.trigger_keywords = self.config.get("trigger_keywords", [
            "你好", "hi", "hello", "嗨", "在吗", "有人吗"
        ])
        
        # 礼物感谢模板
        self.gift_thanks_templates = self.config.get("gift_thanks_templates", [
            "谢谢{username}送的{gift_name}！",
            "感谢{username}的{gift_name}，太感动了！",
            "{username}送了{gift_name}，谢谢支持！"
        ])
        
        # 忽略的用户（如机器人）
        self.ignored_users = set(self.config.get("ignored_users", []))
        
        # 回复队列
        self.reply_queue: asyncio.Queue = asyncio.Queue()
        
        # 礼物感谢队列
        self.gift_queue: asyncio.Queue = asyncio.Queue()
        
        # 统计信息
        self.stats = {
            "total_danmaku": 0,
            "replied_danmaku": 0,
            "total_gifts": 0,
            "thanked_gifts": 0
        }
        
        # 回复历史（防止重复回复）
        self.reply_history: Dict[str, datetime] = {}
        self.reply_cooldown = timedelta(seconds=5)  # 同一用户5秒内不重复回复
        
        # 最近的弹幕（用于上下文）
        self.recent_danmaku: List[Dict[str, Any]] = []
        self.max_recent = 50
        
        print("[DanmakuEnhancer] 初始化完成")
    
    async def process_danmaku(self, user_id: str, username: str, 
                             content: str, room_id: str) -> Optional[DanmakuReply]:
        """处理弹幕消息"""
        self.stats["total_danmaku"] += 1
        
        # 检查是否忽略
        if user_id in self.ignored_users:
            return None
        
        # 检查冷却时间
        if not self._check_cooldown(user_id):
            return None
        
        # 记录到最近弹幕
        self._add_to_recent({
            "user_id": user_id,
            "username": username,
            "content": content,
            "timestamp": datetime.now()
        })
        
        # 根据策略决定是否回复
        should_reply = self._should_reply(content)
        
        if should_reply:
            # 生成回复
            reply_content = await self._generate_reply(content, username)
            
            if reply_content:
                reply = DanmakuReply(
                    original_message=content,
                    reply_content=reply_content,
                    user_id=user_id,
                    username=username,
                    priority=self._calculate_priority(content)
                )
                
                # 更新统计
                self.stats["replied_danmaku"] += 1
                
                # 记录回复历史
                self.reply_history[user_id] = datetime.now()
                
                return reply
        
        return None
    
    def _check_cooldown(self, user_id: str) -> bool:
        """检查用户冷却时间"""
        if user_id in self.reply_history:
            last_reply = self.reply_history[user_id]
            if datetime.now() - last_reply < self.reply_cooldown:
                return False
        return True
    
    def _should_reply(self, content: str) -> bool:
        """判断是否应该回复"""
        # 关键词策略
        if self.reply_strategy == ReplyStrategy.KEYWORD:
            return any(keyword in content for keyword in self.trigger_keywords)
        
        # 智能策略
        if self.reply_strategy == ReplyStrategy.SMART:
            # 问题类型
            if any(q in content for q in ["？", "?", "吗", "呢", "什么", "怎么", "为什么"]):
                return True
            # 提及主播
            if any(kw in content for kw in ["主播", "咕咕", "嘎嘎"]):
                return True
            # 关键词触发
            if any(keyword in content for keyword in self.trigger_keywords):
                return True
            return False
        
        # 立即回复策略
        if self.reply_strategy == ReplyStrategy.IMMEDIATE:
            return True
        
        # 批量回复策略（由外部控制）
        return False
    
    async def _generate_reply(self, content: str, username: str) -> Optional[str]:
        """生成回复内容"""
        # 这里可以集成LLM来生成更智能的回复
        # 目前使用简单的模板回复
        
        # 问候语回复
        greetings = ["你好", "hi", "hello", "嗨"]
        if any(g in content.lower() for g in greetings):
            return f"你好呀，{username}！欢迎来到直播间！"
        
        # 问题回复
        if "？" in content or "?" in content:
            return f"@{username} 好问题！让我想想..."
        
        # 提及主播
        if "主播" in content:
            return f"@{username} 我在呢！有什么事吗？"
        
        return None
    
    def _calculate_priority(self, content: str) -> int:
        """计算回复优先级"""
        priority = 5  # 默认优先级
        
        # 问题类型优先级高
        if "？" in content or "?" in content:
            priority += 2
        
        # 提及主播优先级高
        if "主播" in content:
            priority += 3
        
        # 关键词触发优先级中等
        if any(keyword in content for keyword in self.trigger_keywords):
            priority += 1
        
        return min(10, priority)
    
    def _add_to_recent(self, danmaku: Dict[str, Any]):
        """添加到最近弹幕"""
        self.recent_danmaku.append(danmaku)
        if len(self.recent_danmaku) > self.max_recent:
            self.recent_danmaku.pop(0)
    
    async def process_gift(self, user_id: str, username: str, 
                          gift_name: str, gift_count: int) -> GiftResponse:
        """处理礼物"""
        self.stats["total_gifts"] += 1
        
        # 选择感谢模板
        import random
        template = random.choice(self.gift_thanks_templates)
        
        # 生成感谢消息
        thank_message = template.format(
            username=username,
            gift_name=gift_name,
            gift_count=gift_count
        )
        
        response = GiftResponse(
            user_id=user_id,
            username=username,
            gift_name=gift_name,
            gift_count=gift_count,
            thank_message=thank_message
        )
        
        # 更新统计
        self.stats["thanked_gifts"] += 1
        
        return response
    
    def get_context(self, count: int = 10) -> List[Dict[str, Any]]:
        """获取最近的弹幕上下文"""
        return self.recent_danmaku[-count:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_danmaku": self.stats["total_danmaku"],
            "replied_danmaku": self.stats["replied_danmaku"],
            "reply_rate": self.stats["replied_danmaku"] / max(1, self.stats["total_danmaku"]),
            "total_gifts": self.stats["total_gifts"],
            "thanked_gifts": self.stats["thanked_gifts"],
            "reply_strategy": self.reply_strategy.value,
            "recent_count": len(self.recent_danmaku)
        }
    
    def update_config(self, config: Dict[str, Any]):
        """更新配置"""
        if "reply_strategy" in config:
            self.reply_strategy = ReplyStrategy(config["reply_strategy"])
        if "trigger_keywords" in config:
            self.trigger_keywords = config["trigger_keywords"]
        if "gift_thanks_templates" in config:
            self.gift_thanks_templates = config["gift_thanks_templates"]
        if "ignored_users" in config:
            self.ignored_users = set(config["ignored_users"])
        
        print(f"[DanmakuEnhancer] 配置已更新")

# 全局实例
_danmaku_enhancer: Optional[DanmakuEnhancer] = None

def get_danmaku_enhancer(config: Dict[str, Any] = None) -> DanmakuEnhancer:
    """获取弹幕增强器实例"""
    global _danmaku_enhancer
    if _danmaku_enhancer is None:
        _danmaku_enhancer = DanmakuEnhancer(config)
    return _danmaku_enhancer
