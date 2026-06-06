#!/bin/bash
# 咕咕嘎嘎 AI-VTuber 浏览器模式启动脚本 (macOS/Linux)

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 切换到项目目录
cd "$PROJECT_DIR"

# 检查Python环境
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "错误: 未找到Python，请先安装Python 3.11+"
    exit 1
fi

# 检查Python版本
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo "警告: Python版本 $PYTHON_VERSION 可能不兼容，建议使用Python 3.11+"
fi

# 启动应用
echo "启动咕咕嘎嘎 AI-VTuber (浏览器模式)..."
echo "Python: $PYTHON_CMD $PYTHON_VERSION"
echo "项目目录: $PROJECT_DIR"
echo "访问地址: http://localhost:12393"

$PYTHON_CMD -m app.main "$@"