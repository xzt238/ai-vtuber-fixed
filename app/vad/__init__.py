"""
VAD (Voice Activity Detection) 模块
使用 Silero VAD 进行高精度语音活动检测，支持实时语音打断
"""

import numpy as np
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable, List
import logging

logger = logging.getLogger(__name__)

class VADState(Enum):
    """VAD状态"""
    IDLE = "idle"           # 等待用户说话
    ACTIVE = "active"       # 用户正在说话
    INACTIVE = "inactive"   # 用户已停止说话

@dataclass
class VADConfig:
    """VAD配置"""
    prob_threshold: float = 0.4      # 语音概率阈值
    db_threshold: float = 60         # 音量阈值(dB)
    required_hits: int = 3           # 激活所需连续帧数
    required_misses: int = 24        # 停止所需连续帧数
    sample_rate: int = 16000         # 采样率
    chunk_size: int = 512            # 帧大小

class SileroVAD:
    """Silero VAD 语音活动检测器"""
    
    def __init__(self, config: VADConfig = None) -> None:
        """内部方法"""
        self.config = config or VADConfig()
        self.state = VADState.IDLE
        self.model = None
        self.model_loaded = False
        
        # 计数器
        self.hit_count = 0
        self.miss_count = 0
        
        # 统计信息
        self.stats = {
            "total_frames": 0,
            "speech_frames": 0,
            "silence_frames": 0,
            "state_transitions": 0
        }
        
        # 回调函数
        self.on_speech_start: Optional[Callable] = None
        self.on_speech_end: Optional[Callable] = None
        self.on_state_change: Optional[Callable] = None
        
        # 音频缓冲
        self.audio_buffer: List[np.ndarray] = []
        self.max_buffer_size = 50  # 最多保留50个音频块
        
        logger.info("[VAD] 初始化完成")
    
    async def load_model(self) -> bool:
        """加载Silero VAD模型"""
        try:
            # 尝试加载Silero VAD
            try:
                import torch
                self.model, _ = torch.hub.load(
                    repo_or_dir='snakers4/silero-vad',
                    model='silero_vad',
                    force_reload=False,
                    onnx=False
                )
                self.model_loaded = True
                logger.info("[VAD] Silero VAD模型加载成功")
                return True
            except Exception as e:
                logger.info(f"[VAD] Silero VAD加载失败，使用简化VAD: {e}")
                self.model_loaded = False
                return True  # 使用简化版本
                
        except Exception as e:
            logger.info(f"[VAD] 模型加载失败: {e}")
            return False
    
    async def process_audio(self, audio_chunk: np.ndarray) -> Optional[VADState]:
        """处理音频块，返回状态变化"""
        # 更新统计
        self.stats["total_frames"] += 1
        
        # 添加到缓冲
        self.audio_buffer.append(audio_chunk)
        if len(self.audio_buffer) > self.max_buffer_size:
            self.audio_buffer.pop(0)
        
        # 计算音量
        volume_db = self._calculate_volume_db(audio_chunk)
        
        # 计算语音概率
        if self.model_loaded and self.model is not None:
            speech_prob = self._predict_with_model(audio_chunk)
        else:
            speech_prob = self._estimate_speech_probability(audio_chunk, volume_db)
        
        # 更新统计
        if speech_prob > self.config.prob_threshold:
            self.stats["speech_frames"] += 1
        else:
            self.stats["silence_frames"] += 1
        
        # 状态机逻辑
        old_state = self.state
        new_state = None
        
        if self.state == VADState.IDLE:
            if speech_prob > self.config.prob_threshold and volume_db > self.config.db_threshold:
                self.hit_count += 1
                if self.hit_count >= self.config.required_hits:
                    # 检测到语音开始
                    self.state = VADState.ACTIVE
                    self.hit_count = 0
                    self.miss_count = 0
                    new_state = VADState.ACTIVE
                    self.stats["state_transitions"] += 1
                    logger.info("[VAD] 检测到语音开始 (IDLE -> ACTIVE)")
                    if self.on_speech_start:
                        await self.on_speech_start()
            else:
                self.hit_count = 0
        
        elif self.state == VADState.ACTIVE:
            if speech_prob <= self.config.prob_threshold or volume_db <= self.config.db_threshold:
                self.miss_count += 1
                if self.miss_count >= self.config.required_misses:
                    # 检测到语音结束
                    self.state = VADState.INACTIVE
                    self.miss_count = 0
                    new_state = VADState.INACTIVE
                    self.stats["state_transitions"] += 1
                    logger.info("[VAD] 检测到语音结束 (ACTIVE -> INACTIVE)")
                    if self.on_speech_end:
                        await self.on_speech_end()
            else:
                self.miss_count = 0
        
        elif self.state == VADState.INACTIVE:
            # 等待新语音或超时回到IDLE
            if speech_prob > self.config.prob_threshold:
                self.state = VADState.ACTIVE
                self.hit_count = 0
                new_state = VADState.ACTIVE
                self.stats["state_transitions"] += 1
                logger.info("[VAD] 检测到新语音 (INACTIVE -> ACTIVE)")
                if self.on_speech_start:
                    await self.on_speech_start()
        
        # 触发状态变化回调
        if new_state and self.on_state_change:
            await self.on_state_change(old_state, new_state)
        
        return new_state
    
    def _calculate_volume_db(self, audio_chunk: np.ndarray) -> float:
        """计算音量（分贝）"""
        rms = np.sqrt(np.mean(audio_chunk ** 2))
        if rms > 0:
            return 20 * np.log10(rms + 1e-10)
        return -100
    
    def _predict_with_model(self, audio_chunk: np.ndarray) -> float:
        """使用Silero VAD模型预测"""
        try:
            import torch
            # 转换为tensor
            tensor = torch.from_numpy(audio_chunk).float()
            if len(tensor.shape) == 1:
                tensor = tensor.unsqueeze(0)
            
            # 预测
            with torch.no_grad():
                prob = self.model(tensor, self.config.sample_rate).item()
            return prob
        except Exception as e:
            return self._estimate_speech_probability(audio_chunk, self._calculate_volume_db(audio_chunk))
    
    def _estimate_speech_probability(self, audio_chunk: np.ndarray, volume_db: float) -> float:
        """估算语音概率（简化版本）"""
        # 基于音量的简单估算
        if volume_db > self.config.db_threshold:
            # 音量越高，语音概率越高
            prob = min(1.0, (volume_db - self.config.db_threshold) / 20 + 0.5)
            return prob
        return 0.0
    
    def get_recent_audio(self, num_chunks: int = 10) -> np.ndarray:
        """获取最近的音频块"""
        if not self.audio_buffer:
            return np.array([])
        
        recent = self.audio_buffer[-num_chunks:]
        return np.concatenate(recent) if recent else np.array([])
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "state": self.state.value,
            "model_loaded": self.model_loaded,
            "total_frames": self.stats["total_frames"],
            "speech_frames": self.stats["speech_frames"],
            "silence_frames": self.stats["silence_frames"],
            "state_transitions": self.stats["state_transitions"],
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "buffer_size": len(self.audio_buffer)
        }
    
    def reset(self) -> None:
        """重置状态"""
        self.state = VADState.IDLE
        self.hit_count = 0
        self.miss_count = 0
        self.audio_buffer.clear()
        logger.info("[VAD] 状态已重置")

# 全局VAD实例
_vad: Optional[SileroVAD] = None

def get_vad(config: VADConfig = None) -> SileroVAD:
    """获取VAD实例"""
    global _vad
    if _vad is None:
        _vad = SileroVAD(config)
    return _vad
