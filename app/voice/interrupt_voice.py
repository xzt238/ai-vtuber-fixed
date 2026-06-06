"""
=====================================
支持打断的语音输入模块
=====================================

【模块功能概述】
本模块实现了支持实时语音打断的语音输入功能，
用户可以在AI说话时插嘴，AI会立即停止说话并听取用户新输入。

【核心特性】
1. VAD状态机 - 高精度语音活动检测
2. 打断机制 - 检测到用户说话时自动打断AI
3. asyncio集成 - 支持异步任务取消

作者: 咕咕嘎嘎
日期: 2026-06-04
"""

import os
import asyncio
import tempfile
import threading
import numpy as np
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from app.vad import get_vad, VADConfig, VADState
from app.interrupt import get_interrupt_handler, InterruptReason


class InterruptibleVoiceInput:
    """
    【核心类】支持打断的语音输入管理器
    
    集成VAD状态机和打断处理器，实现：
    1. 高精度语音活动检测
    2. 用户打断AI说话
    3. 实时语音处理
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化"""
        self.config = config
        
        # 基础配置
        self.enabled = config.get("enabled", True)
        self.device = config.get("device", "default")
        self.sample_rate = config.get("sample_rate", 16000)
        self.chunk_size = config.get("chunk_size", 512)
        
        # VAD配置
        vad_config = VADConfig(
            prob_threshold=config.get("vad_threshold", 0.4),
            db_threshold=config.get("db_threshold", 60),
            required_hits=config.get("required_hits", 3),
            required_misses=config.get("required_misses", 24),
            sample_rate=self.sample_rate,
            chunk_size=self.chunk_size
        )
        
        # 初始化VAD
        self.vad = get_vad(vad_config)
        
        # 初始化打断处理器
        self.interrupt_handler = get_interrupt_handler()
        
        # 录音状态
        self.is_recording = False
        self.is_ai_speaking = False
        self.current_ai_response = ""
        
        # 音频缓冲
        self.audio_buffer = []
        self.speech_audio = []  # 用户语音音频
        
        # 回调函数
        self.on_speech_ready: Optional[Callable] = None
        self.on_interrupt: Optional[Callable] = None
        
        # 录音器
        self.recorder = None
        
        # 设置VAD回调
        self.vad.on_speech_start = self._on_vad_speech_start
        self.vad.on_speech_end = self._on_vad_speech_end
        
        print("[InterruptibleVoice] 初始化完成")
    
    async def initialize(self) -> bool:
        """异步初始化"""
        # 加载VAD模型
        success = await self.vad.load_model()
        if success:
            print("[InterruptibleVoice] VAD模型加载成功")
        return success
    
    def is_available(self) -> bool:
        """检查是否可用"""
        if not self.enabled:
            return False
        
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            if devices is None:
                return False
            default_input = sd.query_devices(kind='input')
            return default_input is not None and default_input.get('max_input_channels', 0) > 0
        except Exception:
            return False
    
    def set_callbacks(self, on_speech_ready: Callable = None, on_interrupt: Callable = None):
        """设置回调函数"""
        self.on_speech_ready = on_speech_ready
        self.on_interrupt = on_interrupt
    
    def set_ai_speaking(self, is_speaking: bool, response: str = ""):
        """设置AI说话状态"""
        self.is_ai_speaking = is_speaking
        self.current_ai_response = response
        print(f"[InterruptibleVoice] AI说话状态: {is_speaking}")
    
    async def start(self) -> bool:
        """开始录音"""
        if self.is_recording:
            return False
        
        if not self.is_available():
            print("[InterruptibleVoice] 语音输入不可用")
            return False
        
        try:
            import sounddevice as sd
            
            self.is_recording = True
            self.audio_buffer = []
            self.speech_audio = []
            
            # 定义音频回调
            def audio_callback(indata, frames, time, status):
                if status:
                    print(f"[InterruptibleVoice] 录音状态: {status}")
                
                # 复制音频数据
                audio_chunk = indata.copy().flatten()
                self.audio_buffer.append(audio_chunk)
                
                # 异步处理VAD（需要通过事件循环）
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self._process_audio(audio_chunk),
                        loop
                    )
            
            # 创建录音流
            self.recorder = sd.InputStream(
                device=self.device,
                channels=1,
                samplerate=self.sample_rate,
                dtype='float32',
                blocksize=self.chunk_size,
                callback=audio_callback
            )
            self.recorder.start()
            
            print("[InterruptibleVoice] 开始录音")
            return True
            
        except Exception as e:
            print(f"[InterruptibleVoice] 开始录音失败: {e}")
            self.is_recording = False
            return False
    
    async def _process_audio(self, audio_chunk: np.ndarray):
        """处理音频块"""
        # 添加到语音音频缓冲
        self.speech_audio.append(audio_chunk)
        
        # 保持最近的音频（约5秒）
        max_chunks = int(5 * self.sample_rate / self.chunk_size)
        if len(self.speech_audio) > max_chunks:
            self.speech_audio = self.speech_audio[-max_chunks:]
        
        # 处理VAD
        await self.vad.process_audio(audio_chunk)
    
    async def _on_vad_speech_start(self):
        """VAD检测到语音开始"""
        print("[InterruptibleVoice] 检测到用户开始说话")
        
        # 如果AI正在说话，触发打断
        if self.is_ai_speaking:
            print("[InterruptibleVoice] 触发打断AI说话")
            await self.interrupt_handler.handle_interrupt(
                heard_response=self.current_ai_response,
                reason=InterruptReason.USER_SPEECH
            )
            
            # 触发打断回调
            if self.on_interrupt:
                await self.on_interrupt(self.current_ai_response)
    
    async def _on_vad_speech_end(self):
        """VAD检测到语音结束"""
        print("[InterruptibleVoice] 检测到用户停止说话")
        
        # 保存语音音频
        if self.speech_audio:
            audio_data = np.concatenate(self.speech_audio)
            
            # 保存为WAV文件
            wav_path = self._save_wav(audio_data)
            
            # 触发回调
            if self.on_speech_ready and wav_path:
                await self.on_speech_ready(wav_path)
            
            # 清空语音缓冲
            self.speech_audio = []
    
    def _save_wav(self, audio_data: np.ndarray) -> Optional[str]:
        """保存音频为WAV文件"""
        try:
            import wave
            
            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_file.close()
            
            # 保存为WAV
            with wave.open(temp_file.name, 'wb') as f:
                f.setnchannels(1)
                f.setsampwidth(2)  # 16-bit
                f.setframerate(self.sample_rate)
                # float32 -> int16
                audio_int = (audio_data * 32767).astype('int16')
                f.writeframes(audio_int.tobytes())
            
            print(f"[InterruptibleVoice] 保存音频: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            print(f"[InterruptibleVoice] 保存音频失败: {e}")
            return None
    
    async def stop(self) -> Optional[str]:
        """停止录音"""
        if not self.is_recording:
            return None
        
        try:
            import sounddevice as sd
            
            # 停止录音
            if self.recorder:
                self.recorder.stop()
                self.recorder.close()
                self.recorder = None
            
            self.is_recording = False
            
            # 保存剩余音频
            if self.speech_audio:
                audio_data = np.concatenate(self.speech_audio)
                wav_path = self._save_wav(audio_data)
                self.speech_audio = []
                return wav_path
            
            return None
            
        except Exception as e:
            print(f"[InterruptibleVoice] 停止录音失败: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "is_recording": self.is_recording,
            "is_ai_speaking": self.is_ai_speaking,
            "vad_stats": self.vad.get_stats(),
            "interrupt_stats": self.interrupt_handler.get_stats(),
            "buffer_size": len(self.audio_buffer),
            "speech_buffer_size": len(self.speech_audio)
        }


# 全局实例
_voice_input: Optional[InterruptibleVoiceInput] = None

def get_interruptible_voice(config: Dict[str, Any] = None) -> InterruptibleVoiceInput:
    """获取支持打断的语音输入实例"""
    global _voice_input
    if _voice_input is None:
        _voice_input = InterruptibleVoiceInput(config or {})
    return _voice_input
