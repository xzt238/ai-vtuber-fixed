"""
Function Calling 执行器

处理 LLM 返回的 tool_calls，执行工具并将结果反馈回 LLM。

核心流程:
1. LLM 返回 tool_calls → 解析工具名和参数
2. 执行对应工具 → 获取结果
3. 将结果作为 tool message 反馈回 LLM
4. LLM 基于工具结果生成最终自然语言回复

UI 交互:
- on_tool_call 回调：工具执行前通知 UI 层显示状态提示
- _ui_actions：收集需要 UI 层执行的指令（如切换 Live2D 表情）

支持的 LLM 提供商:
- OpenAI (含兼容端点): tools 参数 + tool_calls 响应
- Anthropic: tool_use content block
- Ollama: 部分 model 支持 function calling

作者: 咕咕嘎嘎
日期: 2026-05-06
"""

import json
from typing import Dict, Any, List, Optional, Callable


# 工具名称 → 友好显示名 + 图标（用于聊天界面提示）
TOOL_DISPLAY_INFO = {
    "get_time": {"name": "获取时间", "icon": "🕐"},
    "get_weather": {"name": "查询天气", "icon": "🌤"},
    "set_reminder": {"name": "设置提醒", "icon": "⏰"},
    "remember_thing": {"name": "记住事项", "icon": "📝"},
    "change_expression": {"name": "切换表情", "icon": "😊"},
    "search_web": {"name": "搜索信息", "icon": "🔍"},
    "play_music": {"name": "播放音乐", "icon": "🎵"},
}


def get_tool_schemas() -> List[Dict[str, Any]]:
    """
    获取所有可用工具的 OpenAI FC schema

    Returns:
        工具 schema 列表，可直接传入 LLM API 的 tools 参数
    """
    try:
        from app.tools.companion import get_companion_tool_schemas
        return get_companion_tool_schemas()
    except Exception as e:
        print(f"[FC] 获取工具 schema 失败: {e}")
        return []


def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行单个工具调用

    Args:
        tool_name: 工具名称
        arguments: 工具参数

    Returns:
        工具执行结果
    """
    try:
        from app.tools.companion import execute_companion_tool
        result = execute_companion_tool(tool_name, arguments)
        return result
    except Exception as e:
        return {"success": False, "error": str(e), "content": f"工具执行出错: {str(e)}"}


def handle_tool_calls_stream(
    tool_calls: List[Dict],
    messages: List[Dict],
    session,       # requests.Session
    base_url: str,
    model: str,
    api_key: str,
    max_tokens: int = 2048,
    on_chunk: Optional[Callable] = None,
    chunk_size: int = 10,
    on_tool_call: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    流式处理 tool_calls: 执行工具 → 将结果反馈回 LLM → 获取最终回复

    Args:
        tool_calls: LLM 返回的 tool_calls 列表
        messages: 原始消息列表
        session: requests.Session
        base_url: API 基础 URL
        model: 模型名称
        api_key: API 密钥
        max_tokens: 最大 token 数
        on_chunk: 流式回调
        chunk_size: 回调触发字符阈值
        on_tool_call: 工具调用状态回调，签名 fn(tool_name, display_text, tool_args)
                      在每个工具执行前调用，用于 UI 显示"正在查天气…"等提示

    Returns:
        {"text": 最终回复文本, "tool_results": [工具执行结果列表], "action": None,
         "_ui_actions": [需要 UI 层执行的指令列表]}
    """
    import re

    # 1. 将 assistant 的 tool_calls 消息加入历史
    assistant_msg = {
        "role": "assistant",
        "content": None,
        "tool_calls": tool_calls
    }
    messages.append(assistant_msg)

    # 2. 逐个执行工具并添加 tool 结果消息
    tool_results = []
    _ui_actions = []  # 收集需要 UI 层执行的指令

    for tc in tool_calls:
        func = tc.get("function", {})
        tool_name = func.get("name", "")
        tool_args_str = func.get("arguments", "{}")
        tool_call_id = tc.get("id", "")

        try:
            arguments = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
        except json.JSONDecodeError:
            arguments = {}

        # 通知 UI 层：工具即将执行
        if on_tool_call:
            display_info = TOOL_DISPLAY_INFO.get(tool_name, {"name": tool_name, "icon": "🔧"})
            display_text = f"{display_info['icon']} 正在{display_info['name']}…"
            try:
                on_tool_call(tool_name, display_text, arguments)
            except Exception:
                pass

        # 执行工具
        result = execute_tool_call(tool_name, arguments)
        tool_results.append({"tool": tool_name, "result": result})

        # 收集 UI 指令（如 change_expression 需要驱动 Live2D）
        if tool_name == "change_expression" and result.get("success"):
            _ui_actions.append({
                "type": "change_expression",
                "emotion": result.get("emotion", "neutral"),
            })

        # 添加 tool message
        result_content = result.get("content", json.dumps(result, ensure_ascii=False))
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result_content
        })

        print(f"[FC] 工具执行: {tool_name}({arguments}) → {result_content[:100]}")

    # 3. 将工具结果反馈给 LLM，获取最终自然语言回复
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": max_tokens,
        "stream": bool(on_chunk),
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    full_text = ""
    buffer = ""

    try:
        if on_chunk:
            # 流式请求
            response = session.post(
                f"{base_url}/chat/completions",
                json=data, headers=headers, timeout=120, stream=True
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8")
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break

                try:
                    chunk = json.loads(data_str)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content") or ""
                    if content:
                        full_text += content
                        buffer += content
                        if len(buffer) >= chunk_size:
                            on_chunk(buffer)
                            buffer = ""
                except:
                    continue

            if buffer and on_chunk:
                on_chunk(buffer)
        else:
            # 非流式请求
            response = session.post(
                f"{base_url}/chat/completions",
                json=data, headers=headers, timeout=60
            )
            response.raise_for_status()
            result = response.json()
            full_text = result["choices"][0].get("message", {}).get("content", "")

    except Exception as e:
        full_text = f"工具结果处理失败: {str(e)}"
        print(f"[FC] 二次请求失败: {e}")

    return {
        "text": full_text,
        "tool_results": tool_results,
        "action": None,
        "_ui_actions": _ui_actions,
    }


def handle_tool_calls_non_stream(
    tool_calls: List[Dict],
    messages: List[Dict],
    session,
    base_url: str,
    model: str,
    api_key: str,
    max_tokens: int = 2048,
) -> Dict[str, Any]:
    """
    非流式处理 tool_calls（简化版）

    与 handle_tool_calls_stream 相同逻辑，但不支持流式回调。
    """
    return handle_tool_calls_stream(
        tool_calls, messages, session, base_url, model, api_key,
        max_tokens=max_tokens, on_chunk=None, chunk_size=10
    )
