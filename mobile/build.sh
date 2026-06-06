#!/bin/bash

# ============================================
# GuguGaga AI VTuber Mobile - 构建脚本
# ============================================

echo "=========================================="
echo "  GuguGaga AI VTuber Mobile 构建工具"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查 Node.js
check_node() {
    if ! command -v node &> /dev/null; then
        echo -e "${RED}错误: 未找到 Node.js${NC}"
        echo "请先安装 Node.js: https://nodejs.org/"
        exit 1
    fi
    echo -e "${GREEN}✓ Node.js 已安装: $(node --version)${NC}"
}

# 检查 npm
check_npm() {
    if ! command -v npm &> /dev/null; then
        echo -e "${RED}错误: 未找到 npm${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ npm 已安装: $(npm --version)${NC}"
}

# 检查 Expo CLI
check_expo() {
    if ! command -v expo &> /dev/null; then
        echo -e "${YELLOW}正在安装 Expo CLI...${NC}"
        npm install -g expo-cli
    fi
    echo -e "${GREEN}✓ Expo CLI 已安装${NC}"
}

# 检查 EAS CLI
check_eas() {
    if ! command -v eas &> /dev/null; then
        echo -e "${YELLOW}正在安装 EAS CLI...${NC}"
        npm install -g eas-cli
    fi
    echo -e "${GREEN}✓ EAS CLI 已安装${NC}"
}

# 安装依赖
install_dependencies() {
    echo ""
    echo -e "${BLUE}正在安装依赖...${NC}"
    npm install
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 依赖安装成功${NC}"
    else
        echo -e "${RED}✗ 依赖安装失败${NC}"
        exit 1
    fi
}

# 登录 Expo
login_expo() {
    echo ""
    echo -e "${BLUE}请登录 Expo 账号${NC}"
    echo "如果没有账号，请先注册: https://expo.dev/signup"
    echo ""
    expo login
}

# 登录 EAS
login_eas() {
    echo ""
    echo -e "${BLUE}请登录 EAS 账号${NC}"
    eas login
}

# 构建 Android APK
build_android() {
    echo ""
    echo -e "${BLUE}开始构建 Android APK...${NC}"
    echo "这可能需要 10-30 分钟，请耐心等待..."
    echo ""
    
    eas build --platform android --profile production
    
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✓ Android APK 构建成功！${NC}"
        echo "请在 EAS 控制台下载 APK 文件: https://expo.dev/accounts/[username]/projects/gugu-ai-vtuber/builds"
    else
        echo -e "${RED}✗ Android APK 构建失败${NC}"
        exit 1
    fi
}

# 构建 iOS IPA
build_ios() {
    echo ""
    echo -e "${BLUE}开始构建 iOS IPA...${NC}"
    echo "注意: iOS 构建需要 Apple Developer 账号"
    echo "这可能需要 15-45 分钟，请耐心等待..."
    echo ""
    
    eas build --platform ios --profile production
    
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✓ iOS IPA 构建成功！${NC}"
        echo "请在 EAS 控制台下载 IPA 文件: https://expo.dev/accounts/[username]/projects/gugu-ai-vtuber/builds"
    else
        echo -e "${RED}✗ iOS IPA 构建失败${NC}"
        exit 1
    fi
}

# 构建所有平台
build_all() {
    echo ""
    echo -e "${BLUE}开始构建所有平台...${NC}"
    
    eas build --platform all --profile production
    
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✓ 所有平台构建成功！${NC}"
        echo "请在 EAS 控制台下载安装包: https://expo.dev/accounts/[username]/projects/gugu-ai-vtuber/builds"
    else
        echo -e "${RED}✗ 构建失败${NC}"
        exit 1
    fi
}

# 本地预览
preview() {
    echo ""
    echo -e "${BLUE}启动本地预览...${NC}"
    echo "请使用 Expo Go 应用扫描二维码"
    echo ""
    
    expo start
}

# 显示帮助
show_help() {
    echo "使用方法: ./build.sh [命令]"
    echo ""
    echo "命令:"
    echo "  setup     - 初始化环境（安装依赖、登录）"
    echo "  android   - 构建 Android APK"
    echo "  ios       - 构建 iOS IPA"
    echo "  all       - 构建所有平台"
    echo "  preview   - 本地预览"
    echo "  help      - 显示帮助"
    echo ""
    echo "示例:"
    echo "  ./build.sh setup     # 首次使用，初始化环境"
    echo "  ./build.sh android   # 构建 Android APK"
    echo "  ./build.sh all       # 构建所有平台"
}

# 主程序
main() {
    check_node
    check_npm
    
    case "$1" in
        setup)
            check_expo
            check_eas
            install_dependencies
            login_expo
            login_eas
            echo ""
            echo -e "${GREEN}✓ 环境初始化完成！${NC}"
            echo "现在可以运行 './build.sh android' 或 './build.sh ios' 构建应用"
            ;;
        android)
            build_android
            ;;
        ios)
            build_ios
            ;;
        all)
            build_all
            ;;
        preview)
            preview
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            show_help
            ;;
    esac
}

main "$@"
