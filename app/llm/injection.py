"""
LLM Prompt 注入系统

包含 PromptInjection、PromptInjector 和 MemoryRAGInjector。
"""

import json
import re
import logging
from typing import Optional, List, Callable, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 从 prompts 模块导入
try:
    from .prompts import inject_memories
except ImportError:
    def inject_memories(t) -> None:
        return ""

@dataclass
class PromptInjection:
    """
    单个 Prompt 注入项

    【设计意图】
    将系统 Prompt 分解为多个独立片段（注入项），各功能模块（记忆、工具、OCR等）
    各自管理自己的 Prompt 片段，通过 PromptInjector 统一合并。
    
    比整个系统共享一个巨型 Prompt 更加模块化、易于维护。

    【属性说明】
    - text: Prompt 文本内容
    - priority: 优先级数字，越大越靠近末尾（LLM 对末尾内容关注度更高）
    """
    text: str           # 注入的文本内容
    priority: int = 0   # 排序优先级：0=最前（最先输出），100=最后（最重要）
    
    def __lt__(self, other) -> None:
        """
        【比较方法】实现 < 运算符，用于 list.sort() 按优先级排序

        【参数说明】
            other: 另一个 PromptInjection 实例

        【返回值】
            bool: 当前实例优先级小于 other 时返回 True（排在前面）
        
        【设计意图】
            dataclass 默认不提供排序支持，手动实现 __lt__ 后
            injections.sort() 即可按 priority 升序排列
        """
        return self.priority < other.priority


class PromptInjector:
    """
    Prompt 注入器（参考 Neuro-sama 架构）

    【设计意图】
    各功能模块（记忆系统、OCR、工具等）通过 register() 方法注册自己的
    Prompt 生成函数，最终由 build() 方法按优先级组装为完整系统 Prompt。
    
    这样的好处是：
    1. 各模块解耦，不需要修改核心代码即可添加新的 Prompt 片段
    2. 优先级控制哪些内容在 Prompt 中更突出（末尾更重要）
    3. 任一模块出错不影响其他模块
    """
    
    def __init__(self) -> None:
        """
        【功能说明】初始化 Prompt 注入器，创建空的模块注册列表

        【设计意图】
        使用函数列表而非对象列表，允许使用 lambda 或 bound method
        注册 Prompt 来源，更灵活
        """
        # 已注册的 Prompt 模块函数列表，每个函数返回 PromptInjection 对象
        self._modules: List[Callable[[], PromptInjection]] = []
    
    def register(self, module_fn: Callable[[], PromptInjection]) -> None:
        """
        【功能说明】注册一个 Prompt 模块函数

        【参数说明】
            module_fn: 无参可调用对象，调用时返回 PromptInjection 实例
                       例如：lambda: PromptInjection("工具说明...", priority=50)

        【设计意图】
        延迟求值：注册的是函数引用而非值，build() 时才实际调用，
        确保每次构建 Prompt 时都能获取最新的动态内容（如当前时间、状态）
        """
        self._modules.append(module_fn)
    
    def build(self) -> str:
        """
        【功能说明】遍历所有注册模块，收集并按优先级排序组装完整 Prompt

        【执行流程】
        1. 依次调用每个已注册的模块函数，获取 PromptInjection 对象
        2. 过滤掉空内容的注入项
        3. 按 priority 升序排序（priority 小的排前面）
        4. 用换行符连接所有文本片段

        【返回值】
            str: 组装好的完整 Prompt 字符串

        【设计意图】
        越重要的内容（priority 越大）越靠近末尾，
        因为 LLM 在实践中对 Prompt 末尾的指令更加关注（attention 集中效应）
        """
        injections = []
        
        # 依次调用每个注册的模块函数，收集注入项
        for module_fn in self._modules:
            try:
                inj = module_fn()
                # 过滤掉空内容的注入项，避免产生多余空行
                if inj and inj.text:
                    injections.append(inj)
            except Exception as e:
                # 单个模块失败不中断整体构建
                logger.info(f"[PromptInjector] 模块执行失败: {e}")
        
        # 按优先级升序排序（priority=0 最前，priority=100 最后）
        injections.sort()
        
        # 用换行符连接所有 Prompt 片段
        return "\n".join(inj.text for inj in injections)


class MemoryRAGInjector:
    """
    记忆 RAG 注入器（Retrieval-Augmented Generation）

    【设计意图】
    RAG（检索增强生成）模式：不将所有记忆直接放入 Prompt（会超出 token 限制），
    而是从记忆系统中检索最相关的内容动态注入，实现"按需记忆"。
    
    参考 Neuro-sama 的 memories/ 目录持久化 + 自动提取模式。
    
    【工作原理】
    1. 从工作记忆（working memory）获取最近 10 条对话
    2. 从情景记忆（episodic memory）获取最近 5 条重要事件摘要
    3. 格式化后通过 inject_memories() 注入到系统 Prompt
    """
    
    def __init__(self, memory_system=None) -> None:
        """
        【功能说明】初始化记忆 RAG 注入器

        【参数说明】
            memory_system: 记忆系统实例（memory/__init__.py 中的 MemorySystem）
                           如果为 None，则 get_injection() 返回空注入项

        【设计意图】
        允许 memory_system 为 None，使该注入器在无记忆系统时"静默降级"，
        不影响 LLM 的正常运行
        """
        self.memory = memory_system
    
    def get_injection(self) -> PromptInjection:
        """
        【功能说明】从记忆系统检索内容，生成 Prompt 注入项

        【执行流程】
        1. 无记忆系统时直接返回空注入项
        2. 获取工作记忆（最近对话，取最新 10 条）
        3. 获取情景记忆（历史摘要，取最新 5 条）
        4. 格式化为 [近期对话] 和 [重要事件摘要] 两段文本
        5. 调用 inject_memories() 包装为标准 Prompt 格式

        【返回值】
            PromptInjection: priority=100（高优先级，靠近 Prompt 末尾）
            
        【设计意图】
        记忆注入使用 priority=100，确保其紧跟在 Prompt 末尾，
        让 LLM 在生成回答时能"最后看到"记忆内容，提高记忆的实际影响力
        """
        # 无记忆系统时直接返回空注入项（不抛异常，静默降级）
        if not self.memory:
            return PromptInjection("")
        
        try:
            # 获取工作记忆（最近的对话轮次，短期记忆）
            working_memories = self.memory.get_working_memory()
            
            # 获取情景记忆（历史摘要，中长期记忆）
            episodic_memories = self.memory.get_episodic_memory()
            
            # 构建记忆文本的各段内容
            memory_parts = []
            
            # 【近期对话】从工作记忆中取最新 10 条（防止太长超出 context）
            if working_memories:
                recent = working_memories[-10:]  # 取最后 10 条（最新的）
                memory_parts.append("[近期对话]")
                for m in recent:
                    # 截取前 200 字符防止单条记忆过长
                    content = m.get("content", "")[:200]
                    role = m.get("role", "?")   # "user" 或 "assistant"
                    memory_parts.append(f"{role}: {content}")
            
            # 【重要摘要】从情景记忆中筛选标记为摘要的条目
            if episodic_memories:
                # 只取 is_summary=True 的条目（过滤普通对话记录）
                summaries = [m for m in episodic_memories if m.get("is_summary")]
                if summaries:
                    memory_parts.append("\n[重要事件摘要]")
                    # 最多取 5 条摘要（最新的 5 条）
                    for m in summaries[-5:]:
                        content = m.get("content", "")
                        memory_parts.append(content)
            
            # 无有效记忆内容时返回空注入项
            if not memory_parts:
                return PromptInjection("")
            
            # 将所有记忆部分用换行连接
            memory_text = "\n".join(memory_parts)
            
            # 使用 prompts.py 中的模板包装记忆文本，生成标准格式的记忆 Prompt
            injected = inject_memories(memory_text)
            
            return PromptInjection(
                text=injected,
                priority=100  # 高优先级：记忆内容靠近 Prompt 末尾，影响力最大
            )
            
        except Exception as e:
            # 记忆获取失败时静默降级，不中断对话流程
            logger.info(f"[MemoryRAGInjector] 错误: {e}")
            return PromptInjection("")


# ==================== 消息构建（无截断版）====================

def build_messages(
    message: str, 
    history: List[Dict] = None,
    system_prompt: str = None,
    memory_system = None
) -> List[Dict]:
    """
    【功能说明】构建发送给 LLM 的完整消息列表（v2.0 无硬截断版）

    【参数说明】
        message (str): 当前用户消息
        history (List[Dict]): 对话历史（[{"role": "user/assistant", "content": "..."}]）
        system_prompt (str): 覆盖默认系统提示词，None 则使用 SYSTEM_PROMPT
        memory_system: 记忆系统实例，用于 RAG 注入

    【返回值】
        List[Dict]: 符合 OpenAI Chat API 格式的消息列表
                    结构：[system] + [history...] + [current_user_message]

    【v2.0 改动说明】
    - 去掉 history[-20:] 硬截断：完整传递所有历史（由 context window 自然限制）
    - 去掉每条 200 字符截断：保留原始消息完整性
    - 新增记忆 RAG 注入：将记忆系统内容动态追加到系统 Prompt

    【设计意图】
    v1.x 的截断设计是为了节省 token，但会导致 LLM 遗忘早期对话。
    v2.0 的 max_tokens 提升到 2048，context window 更大，不再需要截断。
    """
    # 使用传入的 system_prompt，没有则使用模块级全局常量 SYSTEM_PROMPT
    base_system = system_prompt or SYSTEM_PROMPT
    
    # 【记忆 RAG 注入】如果提供了记忆系统，动态检索并追加到系统 Prompt
    if memory_system:
        rag_injector = MemoryRAGInjector(memory_system)
        memory_inj = rag_injector.get_injection()
        if memory_inj.text:
            # 将记忆内容追加到系统 Prompt 末尾（两个换行分隔）
            base_system = base_system + "\n\n" + memory_inj.text
    
    # 构建消息列表：第一条必须是 system 消息
    messages = [{"role": "system", "content": base_system}]
    
    # 【无截断历史注入】完整传递所有对话历史，让 LLM 看到完整上下文
    if history:
        messages.extend(history)
    
    # 当前用户消息追加到最后
    messages.append({"role": "user", "content": message})
    
    return messages


# ==================== 兼容旧接口 =====================

def _build_messages(message: str, history: List[Dict] = None,
                    system_prompt: str = None) -> List[Dict]:
    """
    【功能说明】兼容旧版接口（thin wrapper 调用新版 build_messages）

    【设计意图】
    v1.x 中使用 _build_messages（私有函数命名），v2.0 改名为 build_messages
    保留此函数避免其他模块的调用链断裂（向后兼容）
    """
    return build_messages(message, history, system_prompt)


# ==================== 动作解析 =====================

# 【预编译正则】匹配 LLM 回复中的 "COMMAND: <命令>" 格式
# re.DOTALL 让 . 匹配包括换行在内的所有字符
_COMMAND_RE = re.compile(r"COMMAND:\s*(.+?)(?:\n|$)", re.DOTALL)

def _parse_action(text: str) -> Optional[str]:
    """
    【功能说明】从 LLM 回复文本中解析 Agent 动作指令

    【参数说明】
        text (str): LLM 的回复文本，可能包含 "ACTION: execute" + "COMMAND: <命令>"

    【返回值】
        Optional[str]: 如果找到动作指令，返回 JSON 字符串；否则返回 None
                       格式：'{"type": "execute", "command": "<命令>"}'

    【设计意图】
    AI VTuber 可以通过在回复中嵌入特定格式触发工具调用。
    此函数解析这些隐式指令，与 tools/__init__.py 的工具系统配合使用。
    """
    if not text:
        return None
    # 检测是否包含执行动作标记
    if "ACTION: execute" in text or "COMMAND:" in text:
        match = _COMMAND_RE.search(text)
        if match:
            # 提取命令文本并序列化为 JSON 字符串，供调用方解析
            return json.dumps({"type": "execute", "command": match.group(1).strip()})
    return None


# Qwen3 thinking 标签清理正则
_THINK_RE = re.compile(r"<think\s*>.*?</think\s*>", re.DOTALL)


def _strip_thinking(text: str) -> str:
    """
    【功能说明】移除 Qwen3 等模型的 <think >...</think > 思考过程标签

    【参数说明】
        text (str): LLM 原始输出文本

    【返回值】
        str: 清理后的文本（移除 thinking 标签及内容）

    【设计意图】
    Qwen3 支持 thinking 模式，会在回复中嵌入 <think >...</think > 标签。
    虽然已通过 /no_think 指令和 Ollama reasoning 字段分离来抑制，
    但部分版本/场景下 thinking 内容仍可能出现在 content 中，
    此函数作为兜底清理，防止 TTS 读出思考过程。
    """
    if not text:
        return ""
    cleaned = _THINK_RE.sub("", text).strip()
    return cleaned if cleaned else text  # 如果清理后为空，返回原文


def _clean_response(text: str) -> None:
    """
    【功能说明】统一清理 LLM 回复：去除 thinking 标签 + 解析动作指令

    将 _strip_thinking 和 _parse_action 合并为一个调用，消除 7 处重复代码。

    【参数说明】
        text (str): LLM 原始输出文本

    【返回值】
        tuple: (clean_text, action_str_or_None)
            - clean_text: 清理后的文本
            - action_str: JSON 字符串或 None（由调用方决定是否 json.loads）

    【设计意图】
    之前每个 chat/stream 方法都独立调用 _strip_thinking + _parse_action，
    产生大量重复代码。统一为单次调用，降低维护成本，保证行为一致。
    """
    clean_text = _strip_thinking(text)
    action_str = _parse_action(clean_text)
    return clean_text, action_str


# ==================== 速率限制 & 重试 =====================

