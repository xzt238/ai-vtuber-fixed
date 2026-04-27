"""
s2_train_wrapper.py
====================
官方 S2 训练 thin wrapper。

功能：
1. 切换到 GPT_SoVITS/GPT_SoVITS 目录（让相对路径生效）
2. 用 get_hparams_from_file() 加载配置（绕过 argparse）
3. 调用官方 s2_train_v3.run() 完整训练流程
4. 直接在主进程运行（不用 spawn），Windows 下更稳定

用法（从 GPT-SoVITS 根目录运行）：
    python GPT_SoVITS/s2_train_wrapper.py configs/s2_web_hongkong.json
"""

import os
import sys
import json

# 切换到 GPT_SoVITS/GPT_SoVITS 目录（官方脚本的工作目录）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)
print(f"[S2 Wrapper] 工作目录: {os.getcwd()}")

# 确保 sys.path 指向当前目录（GPT_SoVITS/GPT_SoVITS）
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# 添加 GPT-SoVITS 根目录（s2_train_v3.py 内部需要 from tools.my_utils import ...）
GPT_SOVITS_ROOT = os.path.dirname(SCRIPT_DIR)  # GPT-SoVITS/
if GPT_SOVITS_ROOT not in sys.path:
    sys.path.insert(0, GPT_SOVITS_ROOT)
print(f"[S2 Wrapper] 添加到 sys.path: {GPT_SOVITS_ROOT}")

# 替换 sys.modules['utils']，避免 app.utils 干扰
# s2_train_v3.py 顶部的 "import utils" 会命中 sys.modules
import utils as gpt_sovits_utils
_original_utils = sys.modules.pop("utils", None)
sys.modules["utils"] = gpt_sovits_utils
print(f"[S2 Wrapper] sys.modules['utils'] -> {gpt_sovits_utils.__file__}")


def main():
    # 支持两种调用格式：
    #   python s2_train_wrapper.py -c config.json   (标准 argparse 格式)
    #   python s2_train_wrapper.py config.json     (兼容旧格式)
    if len(sys.argv) < 2:
        print("用法: python s2_train_wrapper.py [-c] <config.json>")
        sys.exit(1)

    if sys.argv[1] == "-c" and len(sys.argv) >= 3:
        config_path = sys.argv[2]
    else:
        config_path = sys.argv[1]
    if not os.path.isabs(config_path):
        config_path = os.path.join(SCRIPT_DIR, config_path)

    print(f"[S2 Wrapper] 配置文件: {config_path}")

    # 模拟命令行参数，让官方 get_hparams() 加载我们的配置
    # s2_train_v3.py 顶部: hps = utils.get_hparams(stage=2)
    # get_hparams() 内部: parser.parse_args() → -c <config_path>
    _orig_argv = sys.argv
    sys.argv = [
        "s2_train_wrapper.py",
        "-c", config_path,
    ]

    # 加载配置（使用官方 get_hparams，它会创建 s2_ckpt_dir 并复制配置）
    from utils import get_hparams
    hps = get_hparams(stage=2)   # stage=2 表示 S2 训练
    sys.argv = _orig_argv        # 恢复原 argv，不干扰后续代码

    # 设置 CUDA 环境（和官方 s2_train_v3.py 相同）
    if hasattr(hps.train, "gpu_numbers"):
        os.environ["CUDA_VISIBLE_DEVICES"] = hps.train.gpu_numbers.replace("-", ",")

    # 设置分布式环境（单 GPU）
    os.environ["MASTER_ADDR"] = "localhost"
    os.environ["MASTER_PORT"] = "29500"

    print(f"[S2 Wrapper] exp_dir: {hps.data.exp_dir}")
    print(f"[S2 Wrapper] s2_ckpt_dir: {hps.s2_ckpt_dir}")
    print(f"[S2 Wrapper] 模型版本: {hps.model.version}")
    print(f"[S2 Wrapper] 开始训练...")

    # 调用官方训练函数（完整的 train_and_evaluate 循环）
    from s2_train_v3 import run
    run(rank=0, n_gpus=1, hps=hps)

    print("[S2 Wrapper] 训练完成!")

    # 恢复 sys.modules
    if _original_utils is not None:
        sys.modules["utils"] = _original_utils
    else:
        sys.modules.pop("utils", None)


if __name__ == "__main__":
    main()
