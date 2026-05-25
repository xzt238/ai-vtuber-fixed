#!/bin/bash
# GuguGaga AI VTuber — 初次安装脚本 (Linux/macOS)
# 安装 Python 依赖、下载模型

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "GuguGaga 安装脚本 — $(uname -s)"

# 检查 Python
PYTHON=""
for py in python3.11 python3.12 python3 python; do
    if command -v $py &>/dev/null && $py -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
        PYTHON=$py
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "[ERROR] Python 3.11+ 未安装"
    echo "  macOS: brew install python@3.11"
    echo "  Ubuntu: sudo apt install python3.11 python3.11-venv"
    exit 1
fi

# 创建虚拟环境
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "创建虚拟环境..."
    $PYTHON -m venv $VENV_DIR
fi
source $VENV_DIR/bin/activate

# 安装 PyTorch（根据平台选择）
pip install --upgrade pip

if [ "$(uname)" = "Darwin" ]; then
    echo "安装 PyTorch (MPS for Apple Silicon)..."
    pip install torch torchvision torchaudio
else
    if command -v nvidia-smi &>/dev/null; then
        echo "安装 PyTorch (CUDA)..."
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
    else
        echo "安装 PyTorch (CPU)..."
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
    fi
fi

# 安装核心依赖
echo "安装核心依赖..."
pip install -r requirements.txt 2>/dev/null || pip install \
    PySide6 PySide6-Fluent-Widgets \
    numpy scipy sentencepiece \
    modelscope funasr \
    pyyaml requests websockets \
    Pillow opencv-python-headless \
    python-dotenv

# 下载模型
echo ""
echo "==========================================="
echo "  安装完成！运行 scripts/go.sh 启动应用"
echo "==========================================="
