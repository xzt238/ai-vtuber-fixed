#!/usr/bin/env python3
"""
音频切片脚本 - 使用 soundfile + scipy
不需要 FFmpeg
"""
import os
import sys
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.io import wavfile
from scipy import signal

# 添加 GPT-SoVITS 路径
GPT_SOVITS_DIR = Path(__file__).parent


class SimpleSlicer:
    """简化版音频切片器"""
    
    def __init__(self, sr=32000, threshold=-40, min_length=3000, min_interval=500, hop_size=512, max_sil_kept=1000):
        self.sr = sr
        self.threshold_db = threshold
        self.threshold = 10 ** (threshold / 20.0)  # 转换为线性
        self.min_length = min_length  # 最小切片长度(ms)
        self.min_interval = min_interval  # 最小切片间隔(ms)
        self.hop_size = hop_size
        self.max_sil_kept = max_sil_kept  # 静音最大保留(ms)
        
    def slice(self, audio):
        """切片音频，返回 [(chunk, start, end), ...]"""
        # 计算音量包络
        length = len(audio)
        
        # 计算 RMS 音量
        rms = []
        hop = self.hop_size
        for i in range(0, length - hop, hop):
            chunk = audio[i:i + hop]
            rms.append(np.sqrt(np.mean(chunk ** 2)))
        rms = np.array(rms)
        
        # 找静音区间
        sil_mask = rms < self.threshold
        
        # 找切割点（在静音区间开始和结束处）
        cuts = []
        in_sil = False
        sil_start = 0
        
        for i, is_sil in enumerate(sil_mask):
            if is_sil and not in_sil:
                # 静音开始
                in_sil = True
                sil_start = i * hop
            elif not is_sil and in_sil:
                # 静音结束
                in_sil = False
                sil_end = i * hop
                sil_dur = sil_end - sil_start
                
                # 如果静音足够长，考虑切割
                if sil_dur > self.min_interval:
                    cuts.append((sil_start, sil_end))
        
        # 添加首尾点
        if not cuts:
            return [(audio, 0, length)]
        
        # 生成切片
        segments = []
        prev_end = 0
        
        for cut_start, cut_end in cuts:
            cut_start = int(cut_start)
            cut_end = int(cut_end)
            
            # 确保最小长度
            seg = audio[prev_end:cut_start]
            seg_len = len(seg)
            
            if seg_len > self.sr * self.min_length / 1000:
                segments.append((seg, prev_end, cut_start))
            
            prev_end = cut_end
        
        # 最后一个片段
        final_seg = audio[prev_end:]
        if len(final_seg) > self.sr * self.min_length / 1000:
            segments.append((final_seg, prev_end, length))
        
        return segments


def slice_audio(input_path, output_dir, threshold=-40, min_length=3, min_interval=0.5, max_sil_kept=1):
    """
    切片音频文件
    
    Args:
        input_path: 输入音频路径
        output_dir: 输出目录
        threshold: 音量阈值(dB)
        min_length: 最小切片长度(秒)
        min_interval: 最小切片间隔(秒)
        max_sil_kept: 最大保留静音(秒)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 读取音频
    print(f"Loading: {input_path}")
    audio, sr = sf.read(input_path, dtype='float32')
    
    # 转换为单声道
    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)
    
    # 重采样到 32kHz
    if sr != 32000:
        print(f"Resampling {sr} -> 32000 Hz")
        num_samples = int(len(audio) * 32000 / sr)
        audio = signal.resample(audio, num_samples)
        sr = 32000
    
    print(f"Audio duration: {len(audio) / sr:.2f}s, Sample rate: {sr}")
    
    # 切片
    slicer = SimpleSlicer(
        sr=sr,
        threshold=threshold,
        min_length=min_length * 1000,  # 转换为 ms
        min_interval=min_interval * 1000,
        max_sil_kept=max_sil_kept * 1000
    )
    
    segments = slicer.slice(audio)
    print(f"Found {len(segments)} segments")
    
    # 保存切片
    name = Path(input_path).stem
    output_paths = []
    
    for i, (seg, start, end) in enumerate(segments):
        duration = len(seg) / sr
        out_path = os.path.join(output_dir, f"{name}_{i:03d}_{duration:.2f}s.wav")
        
        # 归一化
        max_val = np.abs(seg).max()
        if max_val > 0:
            seg = seg / max_val * 0.95
        
        sf.write(out_path, seg.astype(np.float32), sr)
        output_paths.append(out_path)
        print(f"  [{i+1}] {out_path} ({duration:.2f}s)")
    
    return output_paths


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python slice_audio_simple.py <input.wav> <output_dir> [threshold] [min_length]")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_dir = sys.argv[2]
    threshold = float(sys.argv[3]) if len(sys.argv) > 3 else -40
    min_length = float(sys.argv[4]) if len(sys.argv) > 4 else 3
    
    slice_audio(input_path, output_dir, threshold, min_length)
    print("\nDone!")
