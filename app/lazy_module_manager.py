"""
懒加载模块管理器

负责管理 AIVTuber 的所有懒加载模块（ASR, TTS, LLM, Vision, Memory 等）。
通过 @property 实现延迟初始化，大幅缩短启动时间。

设计意图:
    - 将 AIVTuber 类中的懒加载属性提取到独立模块
    - 保持原有懒加载行为不变
    - 提高代码可维护性
"""

import logging
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class LazyModuleManager:
    """
    懒加载模块管理器

    管理所有需要延迟初始化的模块，通过 @property 实现首次访问时才加载。
    使用字典缓存已加载的模块实例，后续访问直接返回缓存。
    """

    def __init__(self, config: Any, logger_instance: Optional[Any] = None) -> None:
        """
        初始化懒加载管理器

        Args:
            config: Config 实例，包含所有模块的配置
            logger_instance: 可选的日志实例
        """
        self.config = config
        self.logger = logger_instance or logger
        self._lazy_modules: Dict[str, Any] = {}
        self._lazy_modules_lock = threading.Lock()

    def _get_module(self, module_name: str, factory_func: Any, *args: Any, **kwargs: Any) -> Any:
        """
        通用懒加载方法

        Args:
            module_name: 模块名称（用于缓存 key）
            factory_func: 工厂函数，用于创建模块实例
            *args, **kwargs: 传递给工厂函数的参数

        Returns:
            模块实例
        """
        if module_name not in self._lazy_modules:
            with self._lazy_modules_lock:
                if module_name not in self._lazy_modules:
                    self.logger.info(f"加载{module_name}模块...")
                    self._lazy_modules[module_name] = factory_func(*args, **kwargs)
        return self._lazy_modules[module_name]

    @property
    def asr(self) -> Any:
        """语音识别模块 (ASR) - 懒加载"""
        def _create_asr() -> Any:
            from asr import ASRFactory
            asr_config = self.config.config.get("asr", {})
            return ASRFactory.create(asr_config)
        return self._get_module("asr", _create_asr)

    @property
    def tts(self) -> Any:
        """语音合成模块 (TTS) - 懒加载"""
        def _create_tts() -> Any:
            from tts import TTSFactory
            tts_config = self.config.config.get("tts", {})
            return TTSFactory.create(tts_config)
        return self._get_module("tts", _create_tts)

    @property
    def llm(self) -> Any:
        """大语言模型模块 (LLM) - 懒加载"""
        def _create_llm() -> Any:
            from llm import LLMFactory
            llm_config = self.config.config.get("llm", {})
            return LLMFactory.create(llm_config)
        return self._get_module("llm", _create_llm)

    @property
    def memory(self) -> Any:
        """记忆系统模块 - 懒加载"""
        def _create_memory() -> Any:
            from memory import MemoryManager
            memory_config = self.config.config.get("memory", {})
            return MemoryManager(memory_config)
        return self._get_module("memory", _create_memory)

    @property
    def vision(self) -> Any:
        """视觉理解模块 - 懒加载"""
        def _create_vision() -> Any:
            from vision import VisionFactory
            vision_config = self.config.config.get("vision", {})
            return VisionFactory.create(vision_config)
        return self._get_module("vision", _create_vision)

    @property
    def live2d(self) -> Any:
        """Live2D 虚拟形象模块 - 懒加载"""
        def _create_live2d() -> Any:
            from live2d import Live2DManager
            live2d_config = self.config.config.get("live2d", {})
            return Live2DManager(live2d_config)
        return self._get_module("live2d", _create_live2d)

    @property
    def voice(self) -> Any:
        """语音输入模块 - 懒加载"""
        def _create_voice() -> Any:
            from voice import VoiceManager
            voice_config = self.config.config.get("voice", {})
            return VoiceManager(voice_config)
        return self._get_module("voice", _create_voice)

    @property
    def voice_web(self) -> Any:
        """Web 语音模块 - 懒加载"""
        def _create_voice_web() -> Any:
            from voice import VoiceWebManager
            voice_config = self.config.config.get("voice", {})
            return VoiceWebManager(voice_config)
        return self._get_module("voice_web", _create_voice_web)

    @property
    def executor(self) -> Any:
        """命令执行器 - 懒加载"""
        def _create_executor() -> Any:
            from main import ToolExecutor
            tools_config = self.config.config.get("tools", {})
            return ToolExecutor(tools_config)
        return self._get_module("executor", _create_executor)

    @property
    def tools(self) -> Any:
        """工具管理器 - 懒加载"""
        def _create_tools() -> Any:
            from tools import ToolManager
            tools_config = self.config.config.get("tools", {})
            return ToolManager(tools_config)
        return self._get_module("tools", _create_tools)

    @property
    def proactive(self) -> Any:
        """主动对话模块 - 懒加载"""
        def _create_proactive() -> Any:
            from proactive import ProactiveManager
            proactive_config = self.config.config.get("proactive", {})
            return ProactiveManager(proactive_config)
        return self._get_module("proactive", _create_proactive)

    @property
    def diary(self) -> Any:
        """日记模块 - 懒加载"""
        def _create_diary() -> Any:
            from diary import DiaryManager
            diary_config = self.config.config.get("diary", {})
            return DiaryManager(diary_config)
        return self._get_module("diary", _create_diary)

    @property
    def mcp(self) -> Any:
        """MCP 模块 - 懒加载"""
        def _create_mcp() -> Any:
            from mcp import MCPManager
            mcp_config = self.config.config.get("mcp", {})
            return MCPManager(mcp_config)
        return self._get_module("mcp", _create_mcp)

    @property
    def desktop_pet(self) -> Any:
        """桌面宠物模块 - 懒加载"""
        def _create_desktop_pet() -> Any:
            from desktop_pet import DesktopPetManager
            pet_config = self.config.config.get("desktop_pet", {})
            return DesktopPetManager(pet_config)
        return self._get_module("desktop_pet", _create_desktop_pet)

    @property
    def web_server(self) -> Any:
        """HTTP 服务器 - 懒加载"""
        def _create_web_server() -> Any:
            from web import WebServer
            web_config = self.config.config.get("web", {})
            return WebServer(web_config)
        return self._get_module("web_server", _create_web_server)

    @property
    def ws_server(self) -> Any:
        """WebSocket 服务器 - 懒加载"""
        def _create_ws_server() -> Any:
            from web import WebSocketServer
            web_config = self.config.config.get("web", {})
            return WebSocketServer(web_config)
        return self._get_module("ws_server", _create_ws_server)

    @property
    def emotion(self) -> Any:
        """情感分析模块 - 懒加载"""
        def _create_emotion() -> Any:
            from emotion import EmotionManager
            emotion_config = self.config.config.get("emotion", {})
            return EmotionManager(emotion_config)
        return self._get_module("emotion", _create_emotion)

    @property
    def roleplay(self) -> Any:
        """角色扮演模块 - 懒加载"""
        def _create_roleplay() -> Any:
            from roleplay import RoleplayManager
            roleplay_config = self.config.config.get("roleplay", {})
            return RoleplayManager(roleplay_config)
        return self._get_module("roleplay", _create_roleplay)

    @property
    def plugin(self) -> Any:
        """插件系统 - 懒加载"""
        def _create_plugin() -> Any:
            from plugin import PluginManager
            plugin_config = self.config.config.get("plugin", {})
            return PluginManager(plugin_config)
        return self._get_module("plugin", _create_plugin)

    @property
    def rag(self) -> Any:
        """RAG 检索增强生成模块 - 懒加载"""
        def _create_rag() -> Any:
            from rag import RAGManager
            rag_config = self.config.config.get("rag", {})
            return RAGManager(rag_config)
        return self._get_module("rag", _create_rag)

    @property
    def live(self) -> Any:
        """直播模块 - 懒加载"""
        def _create_live() -> Any:
            from live import LiveManager
            live_config = self.config.config.get("live", {})
            return LiveManager(live_config)
        return self._get_module("live", _create_live)

    @property
    def svc(self) -> Any:
        """SVC 变声模块 - 懒加载"""
        def _create_svc() -> Any:
            from svc import SVCManager
            svc_config = self.config.config.get("svc", {})
            return SVCManager(svc_config)
        return self._get_module("svc", _create_svc)

    @property
    def singing(self) -> Any:
        """唱歌模块 - 懒加载"""
        def _create_singing() -> Any:
            from singing import SingingManager
            singing_config = self.config.config.get("singing", {})
            return SingingManager(singing_config)
        return self._get_module("singing", _create_singing)

    @property
    def sd(self) -> Any:
        """Stable Diffusion 图像生成模块 - 懒加载"""
        def _create_sd() -> Any:
            from image_gen import ImageGenManager
            sd_config = self.config.config.get("image_gen", {})
            return ImageGenManager(sd_config)
        return self._get_module("sd", _create_sd)

    @property
    def game(self) -> Any:
        """游戏模块 - 懒加载"""
        def _create_game() -> Any:
            from game import GameManager
            game_config = self.config.config.get("game", {})
            return GameManager(game_config)
        return self._get_module("game", _create_game)

    @property
    def multi_agent(self) -> Any:
        """多智能体模块 - 懒加载"""
        def _create_multi_agent() -> Any:
            from multi_agent import MultiAgentManager
            agent_config = self.config.config.get("multi_agent", {})
            return MultiAgentManager(agent_config)
        return self._get_module("multi_agent", _create_multi_agent)

    @property
    def bot(self) -> Any:
        """机器人模块 - 懒加载"""
        def _create_bot() -> Any:
            from bot import BotManager
            bot_config = self.config.config.get("bot", {})
            return BotManager(bot_config)
        return self._get_module("bot", _create_bot)

    @property
    def vision_input(self) -> Any:
        """视觉输入模块 - 懒加载"""
        def _create_vision_input() -> Any:
            from vision_input import VisionInputManager
            vision_config = self.config.config.get("vision_input", {})
            return VisionInputManager(vision_config)
        return self._get_module("vision_input", _create_vision_input)

    @property
    def trainer(self) -> Any:
        """训练管理模块 - 懒加载"""
        def _create_trainer() -> Any:
            from trainer.manager import TrainerManager
            trainer_config = self.config.config.get("trainer", {})
            return TrainerManager(trainer_config)
        return self._get_module("trainer", _create_trainer)

    def get_module(self, module_name: str) -> Optional[Any]:
        """
        获取已加载的模块实例

        Args:
            module_name: 模块名称

        Returns:
            模块实例，如果未加载则返回 None
        """
        return self._lazy_modules.get(module_name)

    def is_loaded(self, module_name: str) -> bool:
        """
        检查模块是否已加载

        Args:
            module_name: 模块名称

        Returns:
            bool: 是否已加载
        """
        return module_name in self._lazy_modules

    def clear_cache(self) -> None:
        """清空所有缓存的模块实例"""
        with self._lazy_modules_lock:
            self._lazy_modules.clear()
            self.logger.info("已清空所有懒加载模块缓存")
