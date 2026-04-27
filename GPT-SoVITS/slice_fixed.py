#!/usr/bin/env python3
"""
固定时间切片脚本 - 每 N 秒切一段
"""
import os
import sys
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal

def slice_fixed_time(input_path, output_dir, segment_duration=5, overlap=0.5, sr=32000):
    """
    固定时间切片
    
    Args:
        input_path: 输入音频路径
        output_dir: 输出目录
        segment_duration: 每段时长(秒)
        overlap: 重叠时长(秒)
        sr: 采样率
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 读取音频
    print(f"Loading: {input_path}")
    audio, orig_sr = sf.read(input_path, dtype='float32')
    
    # 转换为单声道
    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)
    
    # 重采样到 32kHz
    if orig_sr != sr:
        print(f"Resampling {orig_sr} -> {sr} Hz")
        num_samples = int(len(audio) * sr / orig_sr)
        audio = signal.resample(audio, num_samples)
    
    total_duration = len(audio) / sr
    print(f"Total duration: {total_duration:.2f}s")
    
    # 计算切片位置
    step = segment_duration - overlap  # 步长
    name = Path(input_path).stem
    output_paths = []
    
    start = 0
    i = 0
    while start < len(audio):
        end = min(start + segment_duration * sr, len(audio))
        segment = audio[start:end]
        
        # 跳过太短的片段
        if len(segment) < sr:  # 小于1秒
            break
            
        duration = len(segment) / sr
        out_path = os.path.join(output_dir, f"{name}_{i:03d}_{duration:.2f}s.wav")
        
        # 归一化
        max_val = np.abs(segment).max()
        if max_val > 0:
            segment = segment / max_val * 0.95
        
        sf.write(out_path, segment.astype(np.float32), sr)
        output_paths.append(out_path)
        print(f"  [{i+1}] {out_path} ({duration:.2f}s)")
        
        start += int(step * sr)
        i += 1
    
    return output_paths


if __name__ == "__main__":
    # 配置
    INPUT_FILE = "C:/Users/x/WorkBuddy/20260406213554/ai-vtuber-fixed/1.flac"
    OUTPUT_DIR = "C:/Users/x/WorkBuddy/20260406213554/ai-vtuber-fixed/GPT-SoVITS/data/gugu/raw"
    SEGMENT_DURATION = 5  # 每段 5 秒
    OVERLAP = 0.5  # 0.5 秒重叠
    
    print("=" * 50)
    print("GPT-SoVITS 固定时间切片")
    print(f"Segment duration: {SEGMENT_DURATION}s, Overlap: {OVERLAP}s")
    print("=" * 50)
    
    slices = slice_fixed_time(INPUT_FILE, OUTPUT_DIR, SEGMENT_DURATION, OVERLAP)
    print(f"\n切片完成！共 {len(slices)} 个片段")
