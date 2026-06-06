#!/bin/bash

# ============================================
# GuguGaga AI VTuber Mobile - OTA 热更新脚本
# ============================================

echo "=========================================="
echo "  GuguGaga AI VTuber - OTA 热更新"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

# 检查是否在项目目录
if [ ! -f "package.json" ]; then
    echo "[错误] 未找到 package.json，请在项目目录运行此脚本"
    exit 1
fi

# 提交代码变更
echo "[1/3] 提交代码变更..."
git add -A
git commit -m "OTA update $(date '+%Y-%m-%d %H:%M:%S')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[提示] 没有新的变更需要提交"
fi

# 推送 OTA 更新
echo ""
echo "[2/3] 推送 OTA 热更新..."
echo "正在上传代码到 EAS..."
echo ""

EAS_NO_VCS=1 npx eas-cli update --auto --non-interactive

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "  [成功] OTA 热更新已推送！"
    echo "=========================================="
    echo ""
    echo "  用户打开 App 后会自动下载更新"
    echo "  无需重新安装 APK"
    echo ""
else
    echo ""
    echo "[错误] OTA 更新推送失败"
    echo "请检查网络连接和 EAS 登录状态"
    echo ""
fi
