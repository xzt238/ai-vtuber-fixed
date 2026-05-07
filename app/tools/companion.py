"""
伴侣场景专用工具集

这些工具专为 AI 女友/伴侣场景设计，让 AI 不仅能"说"还能"做"。
用户说"帮我设个闹钟" → AI 真的能设闹钟
用户说"现在几点了" → AI 能获取准确时间
用户说"你帮我看看外面下雨没" → AI 能查天气

每个工具都生成 OpenAI Function Calling 格式的 JSON Schema，
供 LLM API 的 tools 参数使用。

作者: 咕咕嘎嘎
日期: 2026-05-06
"""

import os
import json
import time
import datetime
from typing import Dict, Any, Optional

from . import Tool


class GetTimeTool(Tool):
    """获取当前时间/日期"""

    @property
    def description(self) -> str:
        return "获取当前日期和时间"

    def execute(self, **kwargs) -> Dict[str, Any]:
        now = datetime.datetime.now()
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekdays[now.weekday()]
        return {
            "success": True,
            "date": now.strftime("%Y年%m月%d日"),
            "time": now.strftime("%H:%M:%S"),
            "weekday": weekday,
            "content": f"现在是 {now.strftime('%Y年%m月%d日')} {weekday} {now.strftime('%H:%M:%S')}"
        }

    def is_read_only(self) -> bool:
        return True

    @staticmethod
    def get_schema() -> Dict[str, Any]:
        """OpenAI Function Calling 格式的工具 schema"""
        return {
            "type": "function",
            "function": {
                "name": "get_time",
                "description": "获取当前的日期、时间和星期",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }


class GetWeatherTool(Tool):
    """查询天气（使用 wttr.in 免费服务）"""

    @property
    def description(self) -> str:
        return "查询指定城市的天气"

    def execute(self, city: str = "北京", **kwargs) -> Dict[str, Any]:
        try:
            import urllib.request
            url = f"https://wttr.in/{city}?format=j1&lang=zh"
            req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            current = data.get("current_condition", [{}])[0]
            weather_desc = current.get("lang_zh", [{}])[0].get("value", current.get("weatherDesc", [{}])[0].get("value", "未知"))
            temp = current.get("temp_C", "?")
            feels_like = current.get("FeelsLikeC", "?")
            humidity = current.get("humidity", "?")
            wind_speed = current.get("windspeedKmph", "?")

            return {
                "success": True,
                "city": city,
                "weather": weather_desc,
                "temperature": f"{temp}°C",
                "feels_like": f"{feels_like}°C",
                "humidity": f"{humidity}%",
                "wind_speed": f"{wind_speed}km/h",
                "content": f"{city}现在{weather_desc}，气温{temp}°C（体感{feels_like}°C），湿度{humidity}%，风速{wind_speed}km/h"
            }
        except Exception as e:
            return {"success": False, "error": f"天气查询失败: {str(e)}", "content": f"抱歉，暂时查不到{city}的天气呢~"}

    def is_read_only(self) -> bool:
        return True

    @staticmethod
    def get_schema() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "查询指定城市的当前天气，包括温度、湿度、风速等",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "城市名称，如'北京'、'上海'、'Tokyo'"
                        }
                    },
                    "required": ["city"]
                }
            }
        }


class SetReminderTool(Tool):
    """设置提醒（存入本地文件）"""

    @property
    def description(self) -> str:
        return "设置提醒事项"

    def execute(self, content: str = "", remind_time: str = "", **kwargs) -> Dict[str, Any]:
        if not content:
            return {"success": False, "error": "提醒内容不能为空"}

        # 提醒存入 app/cache/reminders.json
        try:
            cache_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "app", "cache"
            )
            os.makedirs(cache_dir, exist_ok=True)
            reminders_file = os.path.join(cache_dir, "reminders.json")

            # 读取已有提醒
            reminders = []
            if os.path.exists(reminders_file):
                with open(reminders_file, "r", encoding="utf-8") as f:
                    reminders = json.load(f)

            # 添加新提醒
            reminder = {
                "id": str(int(time.time() * 1000)),
                "content": content,
                "remind_time": remind_time,
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "done": False
            }
            reminders.append(reminder)

            with open(reminders_file, "w", encoding="utf-8") as f:
                json.dump(reminders, f, ensure_ascii=False, indent=2)

            time_info = f"，提醒时间: {remind_time}" if remind_time else ""
            return {
                "success": True,
                "content": f"好的，我已经帮你记下来了: {content}{time_info}",
                "reminder_id": reminder["id"]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_schema() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "set_reminder",
                "description": "设置一个提醒事项，AI 会帮你记下来",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "提醒的内容，如'下午3点开会'、'记得买牛奶'"
                        },
                        "remind_time": {
                            "type": "string",
                            "description": "提醒时间，如'15:00'、'明天上午'（可选）"
                        }
                    },
                    "required": ["content"]
                }
            }
        }


class RememberThingTool(Tool):
    """主动记住重要的事（写入记忆系统）"""

    @property
    def description(self) -> str:
        return "主动记住用户说的重要事情"

    def execute(self, content: str = "", category: str = "important", **kwargs) -> Dict[str, Any]:
        if not content:
            return {"success": False, "error": "要记住的内容不能为空"}

        # 存入 app/cache/remembered_things.json
        try:
            cache_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "app", "cache"
            )
            os.makedirs(cache_dir, exist_ok=True)
            mem_file = os.path.join(cache_dir, "remembered_things.json")

            memories = []
            if os.path.exists(mem_file):
                with open(mem_file, "r", encoding="utf-8") as f:
                    memories = json.load(f)

            memory_entry = {
                "content": content,
                "category": category,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            memories.append(memory_entry)

            with open(mem_file, "w", encoding="utf-8") as f:
                json.dump(memories, f, ensure_ascii=False, indent=2)

            return {
                "success": True,
                "content": f"嗯嗯，我记住了: {content}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_schema() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "remember_thing",
                "description": "主动记住用户提到的重要事情，比如喜好、生日、重要日期等",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "要记住的内容"
                        },
                        "category": {
                            "type": "string",
                            "description": "分类，如'喜好'、'生日'、'重要日期'、'重要'",
                            "enum": ["喜好", "生日", "重要日期", "重要", "其他"]
                        }
                    },
                    "required": ["content"]
                }
            }
        }


class ChangeExpressionTool(Tool):
    """切换 Live2D 表情（FC 驱动）"""

    @property
    def description(self) -> str:
        return "切换 AI 的表情"

    def execute(self, emotion: str = "neutral", **kwargs) -> Dict[str, Any]:
        # 这个工具的执行结果会通过信号传到 UI 层
        # 在 FC 执行循环中会特殊处理
        return {
            "success": True,
            "emotion": emotion,
            "content": f"(表情切换: {emotion})"
        }

    @staticmethod
    def get_schema() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "change_expression",
                "description": "切换你的表情，让你的情绪表达更丰富",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "emotion": {
                            "type": "string",
                            "description": "要表现的情绪",
                            "enum": ["happy", "sad", "angry", "surprised", "shy", "love", "neutral"]
                        }
                    },
                    "required": ["emotion"]
                }
            }
        }


class SearchWebTool(Tool):
    """简单网页搜索（使用 DuckDuckGo）"""

    @property
    def description(self) -> str:
        return "搜索网页信息"

    def execute(self, query: str = "", **kwargs) -> Dict[str, Any]:
        if not query:
            return {"success": False, "error": "搜索关键词不能为空"}

        try:
            import urllib.request
            import urllib.parse

            # 使用 DuckDuckGo Instant Answer API（免费，无需 API Key）
            url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            abstract = data.get("Abstract", "")
            answer = data.get("Answer", "")
            result_text = abstract or answer

            if not result_text:
                # 尝试获取相关主题
                related = data.get("RelatedTopics", [])
                if related:
                    for topic in related[:3]:
                        if isinstance(topic, dict) and topic.get("Text"):
                            result_text += topic["Text"] + "\n"
                if not result_text:
                    result_text = "没有找到相关信息呢~"

            return {
                "success": True,
                "query": query,
                "content": result_text.strip()
            }
        except Exception as e:
            return {"success": False, "error": str(e), "content": "搜索出了点问题，稍后再试试吧~"}

    def is_read_only(self) -> bool:
        return True

    @staticmethod
    def get_schema() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "搜索网页获取信息，当你不确定某个事实时可以使用",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索关键词"
                        }
                    },
                    "required": ["query"]
                }
            }
        }


class PlayMusicTool(Tool):
    """播放音乐（简单的本地播放）"""

    @property
    def description(self) -> str:
        return "播放音乐"

    def execute(self, action: str = "play", **kwargs) -> Dict[str, Any]:
        # 这是一个占位实现 — 后续可接入实际音乐播放
        return {
            "success": True,
            "action": action,
            "content": f"好的，{( '播放音乐中' if action == 'play' else '已暂停' )}~ （音乐功能开发中，敬请期待！）"
        }

    @staticmethod
    def get_schema() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "play_music",
                "description": "播放或暂停背景音乐",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "操作类型",
                            "enum": ["play", "pause", "stop"]
                        }
                    },
                    "required": []
                }
            }
        }


# ========== 工具 Schema 注册表 ==========

# 所有伴侣工具的 OpenAI FC schema 列表
COMPANION_TOOL_SCHEMAS = [
    GetTimeTool.get_schema(),
    GetWeatherTool.get_schema(),
    SetReminderTool.get_schema(),
    RememberThingTool.get_schema(),
    ChangeExpressionTool.get_schema(),
    SearchWebTool.get_schema(),
    PlayMusicTool.get_schema(),
]

# 工具名称 → 工具类 映射
COMPANION_TOOLS = {
    "get_time": GetTimeTool,
    "get_weather": GetWeatherTool,
    "set_reminder": SetReminderTool,
    "remember_thing": RememberThingTool,
    "change_expression": ChangeExpressionTool,
    "search_web": SearchWebTool,
    "play_music": PlayMusicTool,
}


def get_companion_tool_schemas() -> list:
    """获取所有伴侣工具的 OpenAI FC schema 列表"""
    return COMPANION_TOOL_SCHEMAS


def execute_companion_tool(tool_name: str, arguments: dict) -> Dict[str, Any]:
    """
    执行伴侣工具

    Args:
        tool_name: 工具名称
        arguments: 工具参数

    Returns:
        执行结果字典
    """
    tool_class = COMPANION_TOOLS.get(tool_name)
    if not tool_class:
        return {"success": False, "error": f"未知工具: {tool_name}"}

    tool = tool_class()
    return tool.execute(**arguments)
