import logging
"""
ElevenLabs TTS引擎

logger = logging.getLogger(__name__)

提供ElevenLabs高质量语音合成功能。
"""

import os
import json
import asyncio
import tempfile
from typing import Optional, Dict, Any
from pathlib import Path

from . import TTSEngine


class ElevenLabsTTS(TTSEngine):
    """ElevenLabs TTS引擎"""
    
    # ElevenLabs API配置
    API_BASE = "https://api.elevenlabs.io/v1"
    
    # 默认语音ID
    DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__()
        self.config = config or {}
        
        # API配置
        self.api_key = self.config.get("api_key", "")
        self.voice_id = self.config.get("voice_id", self.DEFAULT_VOICE_ID)
        self.model_id = self.config.get("model_id", "eleven_monolingual_v1")
        
        # 语音参数
        self.stability = self.config.get("stability", 0.5)
        self.similarity_boost = self.config.get("similarity_boost", 0.75)
        self.style = self.config.get("style", 0.0)
        self.use_speaker_boost = self.config.get("use_speaker_boost", True)
        
        # 输出配置
        self.output_format = self.config.get("output_format", "mp3_44100_128")
        
        # 缓存目录
        self.cache_dir = self.config.get("cache_dir", "./cache/tts/elevenlabs")
        if not os.path.isabs(self.cache_dir):
            from app.shared_config import PROJECT_DIR
            self.cache_dir = os.path.join(PROJECT_DIR, self.cache_dir)
            self.cache_dir = os.path.normpath(self.cache_dir)
        
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 会话
        self.session = None
        
        logger.info(f" ElevenLabs TTS引擎初始化完成")
        logger.info(f" 语音ID: {self.voice_id}")
        logger.info(f" 模型ID: {self.model_id}")
    
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        return bool(self.api_key)
    
    async def _ensure_session(self):
        """确保HTTP会话存在"""
        if self.session is None:
            import aiohttp
            self.session = aiohttp.ClientSession()
    
    async def _close_session(self):
        """关闭HTTP会话"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def speak_async(self, text: str, output_path: str = None) -> Optional[str]:
        """异步语音合成"""
        try:
            if not self.is_available():
                logger.info(" ElevenLabs API密钥未配置")
                return None
            
            # 确保会话存在
            await self._ensure_session()
            
            # 生成输出路径
            if output_path is None:
                import hashlib
                text_hash = hashlib.md5(text.encode()).hexdigest()[:16]
                output_path = os.path.join(self.cache_dir, f"{text_hash}.mp3")
            
            # 构建请求数据
            request_data = {
                "text": text,
                "model_id": self.model_id,
                "voice_settings": {
                    "stability": self.stability,
                    "similarity_boost": self.similarity_boost,
                    "style": self.style,
                    "use_speaker_boost": self.use_speaker_boost,
                }
            }
            
            # 构建请求头
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            }
            
            # 发送请求
            url = f"{self.API_BASE}/text-to-speech/{self.voice_id}"
            
            async with self.session.post(url, json=request_data, headers=headers) as response:
                if response.status == 200:
                    # 读取音频数据
                    audio_data = await response.read()
                    
                    # 保存到文件
                    with open(output_path, 'wb') as f:
                        f.write(audio_data)
                    
                    logger.info(f" ElevenLabs语音合成成功: {output_path}")
                    return output_path
                else:
                    error_text = await response.text()
                    logger.info(f" ElevenLabs语音合成失败: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.info(f" ElevenLabs语音合成失败: {e}")
            return None
    
    def speak(self, text: str, output_path: str = None) -> Optional[str]:
        """同步语音合成"""
        try:
            # 运行异步方法
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self.speak_async(text, output_path))
                return result
            finally:
                loop.run_until_complete(self._close_session())
                loop.close()
                
        except Exception as e:
            logger.info(f" ElevenLabs语音合成失败: {e}")
            return None
    
    async def get_voices(self) -> list:
        """获取可用语音列表"""
        try:
            if not self.is_available():
                return []
            
            await self._ensure_session()
            
            headers = {
                "xi-api-key": self.api_key,
            }
            
            url = f"{self.API_BASE}/voices"
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("voices", [])
                else:
                    logger.info(f" 获取语音列表失败: {response.status}")
                    return []
                    
        except Exception as e:
            logger.info(f" 获取语音列表失败: {e}")
            return []
    
    def set_voice(self, voice_id: str):
        """设置语音ID"""
        self.voice_id = voice_id
        logger.info(f" 语音ID已更新: {voice_id}")
    
    def set_model(self, model_id: str):
        """设置模型ID"""
        self.model_id = model_id
        logger.info(f" 模型ID已更新: {model_id}")
    
    def set_voice_settings(self, stability: float = None, similarity_boost: float = None, 
                          style: float = None, use_speaker_boost: bool = None):
        """设置语音参数"""
        if stability is not None:
            self.stability = stability
        if similarity_boost is not None:
            self.similarity_boost = similarity_boost
        if style is not None:
            self.style = style
        if use_speaker_boost is not None:
            self.use_speaker_boost = use_speaker_boost
        
        logger.info(f" 语音参数已更新: stability={self.stability}, similarity_boost={self.similarity_boost}")
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return {
            "api_key": self.api_key,
            "voice_id": self.voice_id,
            "model_id": self.model_id,
            "stability": self.stability,
            "similarity_boost": self.similarity_boost,
            "style": self.style,
            "use_speaker_boost": self.use_speaker_boost,
            "output_format": self.output_format,
        }