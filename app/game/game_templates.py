"""
游戏模板模块
提供常见游戏的UI元素模板和识别规则
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

class GameType(Enum):
    """游戏类型"""
    MINECRAFT = "minecraft"
    FACTORIO = "factorio"
    TERRARIA = "terraria"
    STARDEW_VALLEY = "stardew_valley"
    GENERIC = "generic"

@dataclass
class UIElement:
    """UI元素"""
    name: str
    description: str
    keywords: List[str]
    region: Dict[str, int] = field(default_factory=dict)  # x, y, width, height

@dataclass
class GameStateTemplate:
    """游戏状态模板"""
    game_type: GameType
    name: str
    description: str
    ui_elements: List[UIElement]
    state_keywords: Dict[str, List[str]]  # 状态 -> 关键词列表

# Minecraft模板
MINECRAFT_TEMPLATE = GameStateTemplate(
    game_type=GameType.MINECRAFT,
    name="Minecraft",
    description="Minecraft游戏状态模板",
    ui_elements=[
        UIElement(
            name="health_bar",
            description="生命值条",
            keywords=["生命", "血量", "HP"],
            region={"x": 0, "y": 0, "width": 200, "height": 30}
        ),
        UIElement(
            name="hunger_bar",
            description="饥饿值条",
            keywords=["饥饿", "饱食度"],
            region={"x": 0, "y": 30, "width": 200, "height": 30}
        ),
        UIElement(
            name="inventory",
            description="物品栏",
            keywords=["物品栏", "背包", "Inventory"],
            region={"x": 0, "y": 60, "width": 400, "height": 100}
        ),
        UIElement(
            name="chat",
            description="聊天框",
            keywords=["聊天", "Chat"],
            region={"x": 0, "y": 200, "width": 300, "height": 100}
        ),
        UIElement(
            name="coordinates",
            description="坐标显示",
            keywords=["坐标", "X:", "Y:", "Z:"],
            region={"x": 0, "y": 0, "width": 200, "height": 50}
        )
    ],
    state_keywords={
        "playing": ["生存", "创造", "冒险", "旁观"],
        "menu": ["主菜单", "选项", "设置"],
        "inventory_open": ["物品栏", "箱子", "熔炉"],
        "chat_open": ["聊天", "输入"],
        "death": ["你死了", "死亡", "重生"],
        "paused": ["暂停", "游戏菜单"]
    }
)

# Factorio模板
FACTORIO_TEMPLATE = GameStateTemplate(
    game_type=GameType.FACTORIO,
    name="Factorio",
    description="Factorio游戏状态模板",
    ui_elements=[
        UIElement(
            name="production_stats",
            description="生产统计",
            keywords=["生产", "Production", "每分钟"],
            region={"x": 0, "y": 0, "width": 300, "height": 200}
        ),
        UIElement(
            name="research",
            description="研究进度",
            keywords=["研究", "Research", "科技"],
            region={"x": 0, "y": 0, "width": 200, "height": 100}
        ),
        UIElement(
            name="map",
            description="地图",
            keywords=["地图", "Map"],
            region={"x": 0, "y": 0, "width": 400, "height": 400}
        ),
        UIElement(
            name="inventory",
            description="物品栏",
            keywords=["物品栏", "Inventory", "背包"],
            region={"x": 0, "y": 0, "width": 300, "height": 400}
        )
    ],
    state_keywords={
        "playing": ["自由模式", "关卡"],
        "menu": ["主菜单", "选项"],
        "researching": ["研究中", "Researching"],
        "inventory_open": ["物品栏", "Inventory"],
        "map_open": ["地图", "Map"]
    }
)

# Terraria模板
TERRARIA_TEMPLATE = GameStateTemplate(
    game_type=GameType.TERRARIA,
    name="Terraria",
    description="Terraria游戏状态模板",
    ui_elements=[
        UIElement(
            name="health_mana",
            description="生命值和魔力",
            keywords=["生命", "魔力", "HP", "Mana"],
            region={"x": 0, "y": 0, "width": 200, "height": 60}
        ),
        UIElement(
            name="inventory",
            description="物品栏",
            keywords=["物品栏", "Inventory", "背包"],
            region={"x": 0, "y": 0, "width": 400, "height": 300}
        ),
        UIElement(
            name="map",
            description="小地图",
            keywords=["地图", "Map"],
            region={"x": 0, "y": 0, "width": 200, "height": 200}
        ),
        UIElement(
            name="boss_health",
            description="Boss血量",
            keywords=["Boss", "血量"],
            region={"x": 0, "y": 0, "width": 400, "height": 50}
        )
    ],
    state_keywords={
        "playing": ["普通", "专家", "大师"],
        "menu": ["主菜单", "设置"],
        "inventory_open": ["物品栏", "Inventory"],
        "boss_fight": ["Boss", "boss"],
        "death": ["你死了", "死亡"]
    }
)

# Stardew Valley模板
STARDEW_VALLEY_TEMPLATE = GameStateTemplate(
    game_type=GameType.STARDEW_VALLEY,
    name="Stardew Valley",
    description="Stardew Valley游戏状态模板",
    ui_elements=[
        UIElement(
            name="energy",
            description="能量值",
            keywords=["能量", "Energy"],
            region={"x": 0, "y": 0, "width": 200, "height": 30}
        ),
        UIElement(
            name="time",
            description="时间显示",
            keywords=["时间", "AM", "PM", "春", "夏", "秋", "冬"],
            region={"x": 0, "y": 0, "width": 200, "height": 50}
        ),
        UIElement(
            name="inventory",
            description="物品栏",
            keywords=["物品栏", "Inventory", "背包"],
            region={"x": 0, "y": 0, "width": 400, "height": 200}
        ),
        UIElement(
            name="social",
            description="社交界面",
            keywords=["社交", "Social", "村民"],
            region={"x": 0, "y": 0, "width": 300, "height": 400}
        )
    ],
    state_keywords={
        "playing": ["农场", "矿洞", "城镇"],
        "menu": ["主菜单", "设置"],
        "inventory_open": ["物品栏", "Inventory"],
        "sleeping": ["睡觉", "睡眠"],
        "fishing": ["钓鱼", "Fishing"],
        "mining": ["挖矿", "Mining"]
    }
)

# 游戏模板注册表
GAME_TEMPLATES: Dict[GameType, GameStateTemplate] = {
    GameType.MINECRAFT: MINECRAFT_TEMPLATE,
    GameType.FACTORIO: FACTORIO_TEMPLATE,
    GameType.TERRARIA: TERRARIA_TEMPLATE,
    GameType.STARDEW_VALLEY: STARDEW_VALLEY_TEMPLATE
}

def get_game_template(game_type: GameType) -> Optional[GameStateTemplate]:
    """获取游戏模板"""
    return GAME_TEMPLATES.get(game_type)

def get_all_templates() -> Dict[GameType, GameStateTemplate]:
    """获取所有游戏模板"""
    return GAME_TEMPLATES.copy()

def detect_game_from_text(text: str) -> Optional[GameType]:
    """从文本检测游戏类型"""
    text_lower = text.lower()
    
    # Minecraft关键词
    minecraft_keywords = ["minecraft", "我的世界", "mojang", "creepers", "僵尸", "苦力怕"]
    if any(kw in text_lower for kw in minecraft_keywords):
        return GameType.MINECRAFT
    
    # Factorio关键词
    factorio_keywords = ["factorio", "异星工厂", "传送带", "机械臂", "科技包"]
    if any(kw in text_lower for kw in factorio_keywords):
        return GameType.FACTORIO
    
    # Terraria关键词
    terraria_keywords = ["terraria", "泰拉瑞亚", "克苏鲁", "史莱姆", "哥布林"]
    if any(kw in text_lower for kw in terraria_keywords):
        return GameType.TERRARIA
    
    # Stardew Valley关键词
    stardew_keywords = ["stardew", "星露谷", "农场", "祝尼魔", "joja"]
    if any(kw in text_lower for kw in stardew_keywords):
        return GameType.STARDEW_VALLEY
    
    return None

def detect_game_state(game_type: GameType, text: str) -> Optional[str]:
    """检测游戏状态"""
    template = get_game_template(game_type)
    if not template:
        return None
    
    text_lower = text.lower()
    
    # 遍历所有状态关键词
    for state, keywords in template.state_keywords.items():
        if any(kw in text_lower for kw in keywords):
            return state
    
    return None
