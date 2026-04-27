# -*- coding: utf-8 -*-
"""
正确提取语义token的脚本
完全遵循官方 3-get-semantic.py 的方法
"""
import os
import sys
import torch
import numpy as np
from pathlib import Path

# 设置工作目录
GPT_SOVITS_ROOT = Path(__file__).parent
os.chdir(str(GPT_SOVITS_ROOT))
sys.path.insert(0, str(GPT_SOVITS_ROOT / "GPT_SoVITS"))
sys.path.insert(0, str(GPT_SOVITS_ROOT / "GPT_SoVITS" / "GPT_SoVITS"))

import utils
from process_ckpt import load_sovits_new

def extract_semantic_tokens(project_name: str, force: bool = False):
    """
    从HuBERT特征提取真实语义token

    Args:
        project_name: 项目名称
        force: 是否强制重新提取
    """
    # 项目数据目录
    data_dir = GPT_SOVITS_ROOT / "data" / f"web_{project_name}"
    gpt_data_dir = data_dir  # S1数据在 data/web_xxx/ 目录

    hubert_dir = gpt_data_dir / "4-cnhubert"
    semantic_path = gpt_data_dir / "6-name2semantic-0.tsv"

    print(f"[INFO] 项目: {project_name}")
    print(f"[INFO] HuBERT目录: {hubert_dir}")
    print(f"[INFO] 语义输出: {semantic_path}")

    # 检查HuBERT特征是否存在
    hubert_files = list(hubert_dir.glob("*.npy")) + list(hubert_dir.glob("*.pt"))
    if not hubert_files:
        print("[ERROR] 没有找到HuBERT特征文件！")
        return False

    print(f"[INFO] 找到 {len(hubert_files)} 个HuBERT特征文件")

    # 如果不是强制提取，检查是否已有有效的语义文件
    if not force and semantic_path.exists():
        with open(semantic_path, "r", encoding="utf-8") as f:
            lines = f.read().strip("\n").split("\n")
        if lines and "512" not in lines[0].split("\t")[1][:100]:  # 检查是否不是全512
            print("[INFO] 语义文件已存在且看起来有效，跳过")
            return True
        else:
            print("[WARN] 现有语义文件是无效的（全是512），强制重新提取")

    # 加载VQ模型
    print("[INFO] 加载预训练SoVITS VQ encoder...")
    pretrained_s2G = GPT_SOVITS_ROOT / "GPT_SoVITS" / "pretrained_models" / "s2Gv3.pth"

    if not pretrained_s2G.exists():
        print(f"[ERROR] 预训练模型不存在: {pretrained_s2G}")
        return False

    # 根据文件大小判断版本
    size = os.path.getsize(pretrained_s2G)
    if size < 82978 * 1024:
        version = "v1"
    elif size < 100 * 1024 * 1024:
        version = "v2"
    elif size < 103520 * 1024:
        version = "v1"
    elif size < 700 * 1024 * 1024:
        version = "v2"
    else:
        version = "v3"

    print(f"[INFO] 模型版本: {version}")

    # 加载模型
    from module.models import SynthesizerTrnV3 as SynthesizerTrn

    hps = utils.get_hparams(stage=2)  # 获取默认配置

    vq_model = SynthesizerTrn(
        hps.data.filter_length // 2 + 1,
        hps.train.segment_size // hps.data.hop_length,
        n_speakers=hps.data.n_speakers,
        version=version,
        **hps.model,
    )

    # 加载预训练权重
    dict_s2 = load_sovits_new(str(pretrained_s2G))
    vq_model.load_state_dict(dict_s2['weight'], strict=False)

    # 移动到GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    vq_model = vq_model.to(device)
    vq_model = vq_model.eval()
    if torch.cuda.is_available():
        vq_model = vq_model.half()

    print(f"[INFO] VQ encoder已加载到 {device}")

    # 读取filelist
    filelist_path = gpt_data_dir / "filelist_for_semantic.txt"
    if not filelist_path.exists():
        print("[ERROR] filelist_for_semantic.txt 不存在！")
        return False

    with open(filelist_path, "r", encoding="utf-8") as f:
        filelist = f.read().strip("\n").split("\n")

    print(f"[INFO] 共有 {len(filelist)} 个音频")

    # 提取语义token
    results = []
    for i, line in enumerate(filelist):
        try:
            # 解析 filelist 格式: name.wav|spk|lang|text
            parts = line.strip().split("|")
            wav_name = parts[0]
            # 去掉 .wav 后缀
            stem = wav_name.replace(".wav", "")

            # 查找HuBERT特征
            hubert_path = hubert_dir / f"{stem}.npy"
            if not hubert_path.exists():
                hubert_path = hubert_dir / f"{stem}.pt"
            if not hubert_path.exists():
                print(f"[WARN] 找不到 {stem} 的HuBERT特征，跳过")
                continue

            # 加载HuBERT特征
            if hubert_path.suffix == ".npy":
                ssl_content = np.load(hubert_path)
                ssl_content = torch.from_numpy(ssl_content).float()
            else:
                ssl_content = torch.load(hubert_path, map_location="cpu")

            # 确保形状正确
            if ssl_content.dim() == 2:
                ssl_content = ssl_content.unsqueeze(0)  # (1, T, D)
            elif ssl_content.dim() == 1:
                ssl_content = ssl_content.unsqueeze(0).unsqueeze(0)  # (1, 1, T)

            # 移动到设备
            ssl_content = ssl_content.to(device)
            if torch.cuda.is_available():
                ssl_content = ssl_content.half()

            # 提取语义token
            with torch.no_grad():
                codes = vq_model.extract_latent(ssl_content)

            # codes: (1, 1, T) -> 转为 list
            semantic_ids = codes[0, 0, :].tolist()
            semantic_str = " ".join([str(int(i)) for i in semantic_ids])

            results.append(f"{wav_name}\t{semantic_str}")

            if (i + 1) % 10 == 0:
                print(f"[PROGRESS] {i + 1}/{len(filelist)} 已提取")

        except Exception as e:
            print(f"[ERROR] 处理 {line} 失败: {e}")
            continue

    # 写入结果
    print(f"[INFO] 共提取 {len(results)} 个语义token")

    # 备份旧文件
    if semantic_path.exists():
        backup_path = semantic_path.with_suffix(".tsv.backup")
        semantic_path.rename(backup_path)
        print(f"[INFO] 旧文件已备份: {backup_path}")

    with open(semantic_path, "w", encoding="utf-8") as f:
        f.write("\n".join(results))

    print(f"[SUCCESS] 语义token已保存: {semantic_path}")

    # 显示样例
    if results:
        parts = results[0].split("\t")
        tokens = parts[1].split()[:20]
        print(f"[SAMPLE] 第一个样本前20个token: {' '.join(tokens)}")
        print(f"[SAMPLE] token总数: {len(parts[1].split())}")

    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", "-p", type=str, default="hongkong", help="项目名称")
    parser.add_argument("--force", "-f", action="store_true", help="强制重新提取")
    args = parser.parse_args()

    extract_semantic_tokens(args.project, force=args.force)
