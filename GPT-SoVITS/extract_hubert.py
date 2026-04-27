# -*- coding: utf-8 -*-
"""
简化版 HuBERT 特征提取 - 使用 soundfile 直接读取（无需 ffmpeg）
"""
import os
import sys

# 先切换到正确目录
os.chdir(r'C:\Users\x\WorkBuddy\20260406213554\ai-vtuber-fixed\GPT-SoVITS')
sys.path.insert(0, r'C:\Users\x\WorkBuddy\20260406213554\ai-vtuber-fixed\GPT-SoVITS\GPT_SoVITS')
sys.path.insert(0, r'C:\Users\x\WorkBuddy\20260406213554\ai-vtuber-fixed\GPT-SoVITS')

# 设置环境变量
os.environ['cnhubert_base_dir'] = r'C:\Users\x\WorkBuddy\20260406213554\ai-vtuber-fixed\GPT-SoVITS\GPT_SoVITS\pretrained_models\chinese-hubert-base'

inp_text = r'C:\Users\x\WorkBuddy\20260406213554\ai-vtuber-fixed\GPT-SoVITS\data\gugu32k\filelist.txt'
inp_wav_dir = r'C:\Users\x\WorkBuddy\20260406213554\ai-vtuber-fixed\GPT-SoVITS\data\gugu32k'
opt_dir = r'C:\Users\x\WorkBuddy\20260406213554\ai-vtuber-fixed\GPT-SoVITS\data\gugu60s'
i_part = '0'
is_half = True

import torch
import numpy as np
import soundfile as sf
import librosa
from scipy.io import wavfile
from feature_extractor import cnhubert
from time import time as ttime
import shutil

def my_save(fea, path):
    dir = os.path.dirname(path)
    name = os.path.basename(path)
    tmp_path = "%s%s.pth" % (ttime(), i_part)
    torch.save(fea, tmp_path)
    shutil.move(tmp_path, "%s/%s" % (dir, name))

hubert_dir = "%s/4-cnhubert" % (opt_dir)
wav32dir = "%s/5-wav32k" % (opt_dir)
os.makedirs(opt_dir, exist_ok=True)
os.makedirs(hubert_dir, exist_ok=True)
os.makedirs(wav32dir, exist_ok=True)

maxx = 0.95
alpha = 0.5
device = "cuda:0" if torch.cuda.is_available() else "cpu"

cnhubert.cnhubert_base_path = os.environ['cnhubert_base_dir']
print("加载 HuBERT 模型...")
model = cnhubert.get_model()
if is_half:
    model = model.half().to(device)
else:
    model = model.to(device)

print("读取训练文件...")
with open(inp_text, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"找到 {len(lines)} 个音频文件")

for line in lines:
    line = line.strip()
    if not line:
        continue
    
    parts = line.split('|')
    wav_name = parts[0]
    wav_path = os.path.join(inp_wav_dir, wav_name)
    print(f"处理: {wav_name}")
    
    hubert_path = "%s/%s.pt" % (hubert_dir, wav_name)
    if os.path.exists(hubert_path):
        print(f"  已存在，跳过")
        continue
    
    try:
        # 直接用 soundfile 读取（音频已经是 32k）
        audio, sr = sf.read(wav_path, dtype='float32')
        
        # 转单声道
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        
        tmp_max = np.abs(audio).max()
        if tmp_max > 2.2:
            print(f"  过滤 (振幅过大: {tmp_max})")
            continue
        
        # 处理音频
        audio32 = (audio / tmp_max * (maxx * alpha * 32768)) + ((1 - alpha) * 32768) * audio
        audio32b = (audio / tmp_max * (maxx * alpha * 1145.14)) + ((1 - alpha) * 1145.14) * audio
        audio16 = librosa.resample(audio32b, orig_sr=32000, target_sr=16000)
        
        tensor_wav16 = torch.from_numpy(audio16)
        if is_half:
            tensor_wav16 = tensor_wav16.half().to(device)
        else:
            tensor_wav16 = tensor_wav16.to(device)
        
        ssl = model.model(tensor_wav16.unsqueeze(0))["last_hidden_state"].transpose(1, 2).cpu()
        
        if np.isnan(ssl.detach().numpy()).sum() != 0:
            print(f"  过滤 (NaN)")
            continue
        
        # 保存
        my_save(ssl, hubert_path)
        wavfile.write("%s/%s" % (wav32dir, wav_name), 32000, audio)
        print(f"  完成")
        
    except Exception as e:
        print(f"  错误: {e}")

print("\nHuBERT 特征提取完成！")
