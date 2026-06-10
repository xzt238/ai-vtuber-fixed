"""
=====================================
大语言模型模块 (LLM) - 重构版 v2.0
=====================================

【模块功能概述】
本模块是 AI VTuber 系统的"大脑核心"，负责与各种大语言模型 API 进行通信。
支持 MiniMax、OpenAI、Anthropic 三种主流 LLM 提供商，并提供统一接口。

【子模块】
- llm.prompts: 系统提示词和 Prompt 模板
- llm.injection: PromptInjector, MemoryRAGInjector 注入系统
- llm.infrastructure: RateLimiter, RetryStrategy, StreamAccumulator
- llm.engines: LLMEngine (ABC), MiniMaxLLM, OpenAILLM, AnthropicLLM

【v2.0 重构要点】
- 模块化拆分：按职责分为 4 个子模块
- 保持向后兼容：所有公开类从 __init__.py re-export

作者: 咕咕嘎嘎
日期: 2026-04-19
"""

import os
import sys
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# ==================== 提示词模块导入 ====================

try:
    from .prompts import (
        SYSTEM_PROMPT,
        AGENT_PROMPT,
        get_system_prompt,
        get_agent_prompt,
        build_system_prompt,
        inject_memories
    )
except ImportError:
    prompts_path = os.path.join(os.path.dirname(__file__), 'prompts.py')
    if os.path.exists(prompts_path):
        import importlib.util
        spec = importlib.util.spec_from_file_location("prompts", prompts_path)
        prompts_module = importlib.util.module_from_spec(spec)
        sys.modules["prompts"] = prompts_module
        spec.loader.exec_module(prompts_module)
        SYSTEM_PROMPT = prompts_module.SYSTEM_PROMPT
        AGENT_PROMPT = prompts_module.AGENT_PROMPT
        get_system_prompt = prompts_module.get_system_prompt
        build_system_prompt = prompts_module.build_system_prompt
        inject_memories = prompts_module.inject_memories
    else:
        SYSTEM_PROMPT = "你是一个AI助手。"
        AGENT_PROMPT = ""
        def get_system_prompt(e="") -> None:
            return SYSTEM_PROMPT
        def build_system_prompt(e="") -> None:
            return SYSTEM_PROMPT
        def inject_memories(t) -> None:
            return ""

# ==================== 从子模块导入公开类 ====================

from llm.engines import LLMEngine, MiniMaxLLM, OpenAILLM, AnthropicLLM


# ==================== LLM 工厂类 ====================

class LLMFactory:
    """
    LLM 工厂类

    【设计意图】
    工厂模式（Factory Pattern）：将对象创建逻辑集中在工厂中，
    调用方只需传入配置，无需知道具体要实例化哪个类。
    
    v1.9.43: 支持 10 个 provider（7 国内 + 2 国际 + 1 本地）
    v1.10.3: 新增 gemini + openrouter（OpenAI 兼容格式，base_url 自动设置）
    - minimax: MiniMaxLLM（支持 OpenAI/Anthropic 双格式自动判断）
    - anthropic: AnthropicLLM（原生 Anthropic API）
    - deepseek/kimi/glm/qwen/doubao/mimo/openai/gemini/openrouter: OpenAILLM（OpenAI 兼容格式）
    - ollama: OpenAILLM（_is_ollama 自动检测）
    """
    
    _OPENAI_COMPAT_PROVIDERS = {'deepseek', 'kimi', 'glm', 'qwen', 'doubao', 'mimo', 'openai', 'gemini', 'openrouter'}
    
    _DEFAULT_BASE_URLS = {
        'gemini': 'https://generativelanguage.googleapis.com/v1beta/openai/',
        'openrouter': 'https://openrouter.ai/api/v1',
    }
    
    @staticmethod
    def create(config: Dict[str, Any]) -> LLMEngine:
        """
        【功能说明】根据配置创建对应的 LLM 引擎实例

        【参数说明】
            config (Dict[str, Any]): 包含 provider 字段的配置字典

        【返回值】
            LLMEngine: 对应提供商的引擎实例
        """
        provider = config.get("provider", "minimax")
        
        if provider == "minimax":
            return MiniMaxLLM(config.get("minimax", {}))
        elif provider == "anthropic":
            return AnthropicLLM(config.get("anthropic", {}))
        elif provider == "ollama":
            return OpenAILLM(config.get("ollama", {}))
        elif provider in LLMFactory._OPENAI_COMPAT_PROVIDERS:
            sub_cfg = dict(config.get(provider, {}))
            if provider in LLMFactory._DEFAULT_BASE_URLS and not sub_cfg.get("base_url"):
                sub_cfg["base_url"] = LLMFactory._DEFAULT_BASE_URLS[provider]
            return OpenAILLM(sub_cfg)
        else:
            sub_cfg = config.get(provider, {})
            if sub_cfg.get("base_url"):
                logger.info(f"[LLM] 未知 provider '{provider}'，尝试 OpenAI 兼容格式")
                return OpenAILLM(sub_cfg)
            raise ValueError(f"未知 LLM 提供商: {provider}")
