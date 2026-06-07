"""
音频预处理模块
提供降噪、音量标准化、静音检测等功能
"""

import numpy as np
from typing import Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class AudioPreprocessorConfig:
    """音频预处理器配置"""
    # 降噪配置
    noise_reduce_strength: float = 0.5  # 降噪强度 (0-1)
    noise_sample_duration: float = 0.5  # 噪声采样时长(秒)
    
    # 音量标准化
    target_db: float = -20.0  # 目标音量(dB)
    enable_normalization: bool = True
    
    # 静音检测
    silence_threshold_db: float = -40.0  # 静音阈值(dB)
    min_silence_duration_ms: int = 300  # 最小静音时长(ms)
    
    # 高通滤波
    highpass_freq: int = 80  # 高通滤波频率(Hz)
    enable_highpass: bool = True
    
    # 低通滤波
    lowpass_freq: int = 8000  # 低通滤波频率(Hz)
    enable_lowpass: bool = True

class AudioPreprocessor:
    """音频预处理器"""
    
    def __init__(self, config: AudioPreprocessorConfig = None, sample_rate: int = 16000):
        self.config = config or AudioPreprocessorConfig()
        self.sample_rate = sample_rate
        
        # 噪声样本
        self.noise_samples: list = []
        self.noise_profile: Optional[np.ndarray] = None
        
        logger.info("[AudioPreprocessor] 初始化完成")
    
    def process(self, audio: np.ndarray) -> np.ndarray:
        """处理音频"""
        if len(audio) == 0:
            return audio
        
        # 复制音频，避免修改原始数据
        processed = audio.copy()
        
        # 1. 高通滤波（去除低频噪音）
        if self.config.enable_highpass:
            processed = self._highpass_filter(processed)
        
        # 2. 低通滤波（去除高频噪音）
        if self.config.enable_lowpass:
            processed = self._lowpass_filter(processed)
        
        # 3. 降噪
        if self.config.noise_reduce_strength > 0:
            processed = self._reduce_noise(processed)
        
        # 4. 音量标准化
        if self.config.enable_normalization:
            processed = self._normalize_volume(processed)
        
        return processed
    
    def _highpass_filter(self, audio: np.ndarray) -> np.ndarray:
        """高通滤波（简单实现）"""
        # 使用一阶IIR高通滤波器
        # y[n] = x[n] - x[n-1] + alpha * y[n-1]
        alpha = np.exp(-2 * np.pi * self.config.highpass_freq / self.sample_rate)
        
        filtered = np.zeros_like(audio)
        filtered[0] = audio[0]
        
        for i in range(1, len(audio)):
            filtered[i] = audio[i] - audio[i-1] + alpha * filtered[i-1]
        
        return filtered
    
    def _lowpass_filter(self, audio: np.ndarray) -> np.ndarray:
        """低通滤波（简单实现）"""
        # 使用一阶IIR低通滤波器
        # y[n] = (1-alpha) * x[n] + alpha * y[n-1]
        alpha = np.exp(-2 * np.pi * self.config.lowpass_freq / self.sample_rate)
        
        filtered = np.zeros_like(audio)
        filtered[0] = audio[0]
        
        for i in range(1, len(audio)):
            filtered[i] = (1 - alpha) * audio[i] + alpha * filtered[i-1]
        
        return filtered
    
    def _reduce_noise(self, audio: np.ndarray) -> np.ndarray:
        """降噪处理"""
        # 如果没有噪声样本，使用音频开头作为噪声样本
        if self.noise_profile is None:
            # 假设前0.5秒是噪音
            noise_samples = int(self.config.noise_sample_duration * self.sample_rate)
            if len(audio) > noise_samples:
                self.noise_profile = np.mean(np.abs(audio[:noise_samples]))
            else:
                return audio
        
        # 简单的谱减法降噪
        # 计算频谱
        fft = np.fft.rfft(audio)
        magnitude = np.abs(fft)
        phase = np.angle(fft)
        
        # 估计噪声频谱
        noise_magnitude = self.noise_profile * np.ones_like(magnitude)
        
        # 谱减法
        alpha = self.config.noise_reduce_strength
        cleaned_magnitude = magnitude - alpha * noise_magnitude
        cleaned_magnitude = np.maximum(cleaned_magnitude, 0)  # 防止负值
        
        # 重建音频
        cleaned_fft = cleaned_magnitude * np.exp(1j * phase)
        cleaned_audio = np.fft.irfft(cleaned_fft, len(audio))
        
        return cleaned_audio
    
    def _normalize_volume(self, audio: np.ndarray) -> np.ndarray:
        """音量标准化"""
        # 计算当前音量
        rms = np.sqrt(np.mean(audio ** 2))
        if rms < 1e-10:
            return audio
        
        current_db = 20 * np.log10(rms)
        
        # 计算增益
        gain_db = self.config.target_db - current_db
        gain = 10 ** (gain_db / 20)
        
        # 限制增益，防止过度放大
        max_gain = 10  # 最大增益10倍
        gain = min(gain, max_gain)
        
        # 应用增益
        normalized = audio * gain
        
        # 防止削波
        max_val = np.max(np.abs(normalized))
        if max_val > 1.0:
            normalized = normalized / max_val
        
        return normalized
    
    def detect_silence(self, audio: np.ndarray) -> list:
        """检测静音区间"""
        # 计算每帧的音量
        frame_size = int(0.025 * self.sample_rate)  # 25ms帧
        hop_size = int(0.010 * self.sample_rate)  # 10ms跳
        
        silence_regions = []
        in_silence = False
        silence_start = 0
        
        for i in range(0, len(audio) - frame_size, hop_size):
            frame = audio[i:i + frame_size]
            rms = np.sqrt(np.mean(frame ** 2))
            
            if rms < 1e-10:
                db = -100
            else:
                db = 20 * np.log10(rms)
            
            if db < self.config.silence_threshold_db:
                if not in_silence:
                    in_silence = True
                    silence_start = i
            else:
                if in_silence:
                    silence_end = i
                    duration_ms = (silence_end - silence_start) / self.sample_rate * 1000
                    
                    if duration_ms >= self.config.min_silence_duration_ms:
                        silence_regions.append((silence_start, silence_end))
                    
                    in_silence = False
        
        # 检查最后一个静音区间
        if in_silence:
            silence_end = len(audio)
            duration_ms = (silence_end - silence_start) / self.sample_rate * 1000
            
            if duration_ms >= self.config.min_silence_duration_ms:
                silence_regions.append((silence_start, silence_end))
        
        return silence_regions
    
    def remove_silence(self, audio: np.ndarray, keep_margin_ms: int = 100) -> np.ndarray:
        """移除静音区间"""
        silence_regions = self.detect_silence(audio)
        
        if not silence_regions:
            return audio
        
        # 保留每个静音区间前后的一小段
        margin_samples = int(keep_margin_ms / 1000 * self.sample_rate)
        
        # 合并重叠的静音区间
        merged_regions = [silence_regions[0]]
        for start, end in silence_regions[1:]:
            if start <= merged_regions[-1][1]:
                merged_regions[-1] = (merged_regions[-1][0], end)
            else:
                merged_regions.append((start, end))
        
        # 提取非静音区间
        segments = []
        prev_end = 0
        
        for start, end in merged_regions:
            # 添加静音区间前的音频
            segment_start = max(0, start - margin_samples)
            if segment_start > prev_end:
                segments.append(audio[prev_end:segment_start])
            
            # 添加一小段静音
            silence_segment = audio[start:min(start + margin_samples, end)]
            segments.append(silence_segment)
            
            prev_end = end + margin_samples
        
        # 添加最后一个区间后的音频
        if prev_end < len(audio):
            segments.append(audio[prev_end:])
        
        if segments:
            return np.concatenate(segments)
        else:
            return audio
    
    def get_audio_stats(self, audio: np.ndarray) -> dict:
        """获取音频统计信息"""
        if len(audio) == 0:
            return {
                "duration_ms": 0,
                "rms_db": -100,
                "peak_db": -100,
                "silence_ratio": 1.0
            }
        
        # 计算时长
        duration_ms = len(audio) / self.sample_rate * 1000
        
        # 计算RMS音量
        rms = np.sqrt(np.mean(audio ** 2))
        rms_db = 20 * np.log10(rms + 1e-10)
        
        # 计算峰值音量
        peak = np.max(np.abs(audio))
        peak_db = 20 * np.log10(peak + 1e-10)
        
        # 计算静音比例
        silence_regions = self.detect_silence(audio)
        silence_samples = sum(end - start for start, end in silence_regions)
        silence_ratio = silence_samples / len(audio)
        
        return {
            "duration_ms": duration_ms,
            "rms_db": rms_db,
            "peak_db": peak_db,
            "silence_ratio": silence_ratio
        }

# 全局实例
_preprocessor: Optional[AudioPreprocessor] = None

def get_audio_preprocessor(config: AudioPreprocessorConfig = None, 
                          sample_rate: int = 16000) -> AudioPreprocessor:
    """获取音频预处理器实例"""
    global _preprocessor
    if _preprocessor is None:
        _preprocessor = AudioPreprocessor(config, sample_rate)
    return _preprocessor
