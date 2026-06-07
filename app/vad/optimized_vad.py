"""
优化版 VAD (Voice Activity Detection) 模块
新增：自适应阈值、降噪、更精确的状态机
"""

import numpy as np
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable, Deque
from collections import deque
from datetime import datetime
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
    # 新增优化参数
    adaptive_threshold: bool = True  # 自适应阈值
    noise_gate_db: float = 30        # 噪声门限(dB)
    smoothing_window: int = 5        # 平滑窗口大小
    min_speech_duration_ms: int = 100  # 最小语音持续时间(ms)

class OptimizedSileroVAD:
    """优化版 Silero VAD 语音活动检测器"""
    
    def __init__(self, config: VADConfig = None) -> None:
        self.config = config or VADConfig()
        self.state = VADState.IDLE
        self.model = None
        self.model_loaded = False
        
        # 计数器
        self.hit_count = 0
        self.miss_count = 0
        
        # 自适应阈值
        self.noise_level = -60  # 噪音水平(dB)
        self.noise_samples: Deque[float] = deque(maxlen=100)
        self.speech_samples: Deque[float] = deque(maxlen=50)
        
        # 概率平滑
        self.prob_history: Deque[float] = deque(maxlen=self.config.smoothing_window)
        
        # 统计信息
        self.stats = {
            "total_frames": 0,
            "speech_frames": 0,
            "silence_frames": 0,
            "state_transitions": 0,
            "noise_level_db": self.noise_level,
            "adaptive_threshold_db": self.config.db_threshold
        }
        
        # 回调函数
        self.on_speech_start: Optional[Callable] = None
        self.on_speech_end: Optional[Callable] = None
        self.on_state_change: Optional[Callable] = None
        
        # 音频缓冲（环形缓冲区）
        self.audio_buffer: Deque[np.ndarray] = deque(maxlen=100)
        
        # 语音开始时间
        self.speech_start_time: Optional[datetime] = None
        
        logger.info("[OptimizedVAD] 初始化完成")
    
    async def load_model(self) -> bool:
        """加载Silero VAD模型"""
        try:
            try:
                import torch
                self.model, _ = torch.hub.load(
                    repo_or_dir='snakers4/silero-vad',
                    model='silero_vad',
                    force_reload=False,
                    onnx=False
                )
                self.model_loaded = True
                logger.info("[OptimizedVAD] Silero VAD模型加载成功")
                return True
            except Exception as e:
                logger.info(f"[OptimizedVAD] Silero VAD加载失败，使用简化VAD: {e}")
                self.model_loaded = False
                return True
        except Exception as e:
            logger.info(f"[OptimizedVAD] 模型加载失败: {e}")
            return False
    
    async def process_audio(self, audio_chunk: np.ndarray) -> Optional[VADState]:
        """处理音频块，返回状态变化"""
        # 更新统计
        self.stats["total_frames"] += 1
        
        # 添加到缓冲
        self.audio_buffer.append(audio_chunk)
        
        # 计算音量
        volume_db = self._calculate_volume_db(audio_chunk)
        
        # 噪声门限：低于噪声门限的音频直接忽略
        if volume_db < self.config.noise_gate_db:
            return None
        
        # 更新噪声水平（在静音时）
        if self.state == VADState.IDLE:
            self._update_noise_level(volume_db)
        
        # 计算语音概率
        if self.model_loaded and self.model is not None:
            speech_prob = self._predict_with_model(audio_chunk)
        else:
            speech_prob = self._estimate_speech_probability(audio_chunk, volume_db)
        
        # 概率平滑
        smoothed_prob = self._smooth_probability(speech_prob)
        
        # 自适应阈值
        effective_threshold = self._get_adaptive_threshold()
        
        # 更新统计
        if smoothed_prob > effective_threshold:
            self.stats["speech_frames"] += 1
        else:
            self.stats["silence_frames"] += 1
        
        # 状态机逻辑
        old_state = self.state
        new_state = None
        
        if self.state == VADState.IDLE:
            if smoothed_prob > effective_threshold and volume_db > self._get_adaptive_db_threshold():
                self.hit_count += 1
                if self.hit_count >= self.config.required_hits:
                    # 检测到语音开始
                    self.state = VADState.ACTIVE
                    self.hit_count = 0
                    self.miss_count = 0
                    self.speech_start_time = datetime.now()
                    new_state = VADState.ACTIVE
                    self.stats["state_transitions"] += 1
                    logger.info(f"[OptimizedVAD] 检测到语音开始 (IDLE -> ACTIVE), prob={smoothed_prob:.2f}")
                    if self.on_speech_start:
                        await self.on_speech_start()
            else:
                self.hit_count = max(0, self.hit_count - 1)  # 渐进式减少
        
        elif self.state == VADState.ACTIVE:
            if smoothed_prob <= effective_threshold or volume_db <= self._get_adaptive_db_threshold():
                self.miss_count += 1
                # 检查最小语音持续时间
                if self.speech_start_time:
                    duration_ms = (datetime.now() - self.speech_start_time).total_seconds() * 1000
                    if duration_ms < self.config.min_speech_duration_ms:
                        # 语音太短，可能是噪音
                        self.miss_count = 0
                
                if self.miss_count >= self.config.required_misses:
                    # 检测到语音结束
                    self.state = VADState.INACTIVE
                    self.miss_count = 0
                    new_state = VADState.INACTIVE
                    self.stats["state_transitions"] += 1
                    logger.info(f"[OptimizedVAD] 检测到语音结束 (ACTIVE -> INACTIVE)")
                    if self.on_speech_end:
                        await self.on_speech_end()
            else:
                self.miss_count = 0
        
        elif self.state == VADState.INACTIVE:
            if smoothed_prob > effective_threshold:
                self.state = VADState.ACTIVE
                self.hit_count = 0
                self.speech_start_time = datetime.now()
                new_state = VADState.ACTIVE
                self.stats["state_transitions"] += 1
                logger.info(f"[OptimizedVAD] 检测到新语音 (INACTIVE -> ACTIVE)")
                if self.on_speech_start:
                    await self.on_speech_start()
        
        # 触发状态变化回调
        if new_state and self.on_state_change:
            await self.on_state_change(old_state, new_state)
        
        return new_state
    
    def _calculate_volume_db(self, audio_chunk: np.ndarray) -> float:
        """计算音量（分贝）- 优化版"""
        # 使用更稳定的RMS计算
        rms = np.sqrt(np.mean(audio_chunk ** 2) + 1e-10)
        return 20 * np.log10(rms + 1e-10)
    
    def _update_noise_level(self, volume_db: float) -> None:
        """更新噪声水平"""
        self.noise_samples.append(volume_db)
        if len(self.noise_samples) >= 10:
            # 使用中位数作为噪声水平（更稳定）
            self.noise_level = np.median(list(self.noise_samples))
            self.stats["noise_level_db"] = float(self.noise_level)
    
    def _get_adaptive_threshold(self) -> float:
        """获取自适应概率阈值"""
        if not self.config.adaptive_threshold:
            return self.config.prob_threshold
        
        # 根据噪声水平调整阈值
        noise_offset = max(0, (self.noise_level - 40) / 40)  # 噪声越高，阈值越高
        return min(0.8, self.config.prob_threshold + noise_offset * 0.2)
    
    def _get_adaptive_db_threshold(self) -> float:
        """获取自适应音量阈值"""
        if not self.config.adaptive_threshold:
            return self.config.db_threshold
        
        # 噪声水平 + 余量
        return max(self.config.db_threshold, self.noise_level + 15)
    
    def _smooth_probability(self, prob: float) -> float:
        """概率平滑"""
        self.prob_history.append(prob)
        if len(self.prob_history) < 2:
            return prob
        
        # 加权平均（最近的权重更高）
        weights = np.linspace(0.5, 1.0, len(self.prob_history))
        return np.average(list(self.prob_history), weights=weights)
    
    def _predict_with_model(self, audio_chunk: np.ndarray) -> float:
        """使用Silero VAD模型预测"""
        try:
            import torch
            tensor = torch.from_numpy(audio_chunk).float()
            if len(tensor.shape) == 1:
                tensor = tensor.unsqueeze(0)
            with torch.no_grad():
                prob = self.model(tensor, self.config.sample_rate).item()
            return prob
        except Exception as e:
            return self._estimate_speech_probability(audio_chunk, self._calculate_volume_db(audio_chunk))
    
    def _estimate_speech_probability(self, audio_chunk: np.ndarray, volume_db: float) -> float:
        """估算语音概率（简化版本）- 优化版"""
        # 使用自适应阈值
        adaptive_db = self._get_adaptive_db_threshold()
        if volume_db > adaptive_db:
            # 使用更平滑的映射
            normalized = (volume_db - adaptive_db) / 30
            return min(1.0, 0.5 + normalized * 0.5)
        elif volume_db > self.config.noise_gate_db:
            # 在噪声门限和阈值之间，低概率
            normalized = (volume_db - self.config.noise_gate_db) / (adaptive_db - self.config.noise_gate_db)
            return normalized * 0.3
        return 0.0
    
    def get_recent_audio(self, num_chunks: int = 10) -> np.ndarray:
        """获取最近的音频块"""
        if not self.audio_buffer:
            return np.array([])
        recent = list(self.audio_buffer)[-num_chunks:]
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
            "buffer_size": len(self.audio_buffer),
            "noise_level_db": self.stats["noise_level_db"],
            "adaptive_threshold_db": self.stats["adaptive_threshold_db"]
        }
    
    def reset(self) -> None:
        """重置状态"""
        self.state = VADState.IDLE
        self.hit_count = 0
        self.miss_count = 0
        self.audio_buffer.clear()
        self.prob_history.clear()
        self.speech_start_time = None
        logger.info("[OptimizedVAD] 状态已重置")

# 全局实例
_optimized_vad: Optional[OptimizedSileroVAD] = None

def get_optimized_vad(config: VADConfig = None) -> OptimizedSileroVAD:
    """获取优化版VAD实例"""
    global _optimized_vad
    if _optimized_vad is None:
        _optimized_vad = OptimizedSileroVAD(config)
    return _optimized_vad
