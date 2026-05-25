#!/bin/bash
# GuguGaga AI VTuber — 一键启动 (Linux/macOS)
# 自动检查依赖并启动原生桌面应用

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  GuguGaga AI VTuber"
echo "  Platform: $(uname -s)"
echo "========================================"

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
    exit 1
fi
echo "[OK] Python: $($PYTHON --version)"

# 检查关键模块
echo "Checking dependencies..."
$PYTHON -c "import PySide6" 2>/dev/null || {
    echo "[WARN] PySide6 未安装，尝试安装..."
    $PYTHON -m pip install PySide6 PySide6-Fluent-Widgets
}
echo "[OK] Dependencies OK"

# 启动应用
echo "Starting GuguGaga..."
$PYTHON native/main.py "$@"
