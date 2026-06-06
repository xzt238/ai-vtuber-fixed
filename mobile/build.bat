@echo off
REM ============================================
REM GuguGaga AI VTuber Mobile - Windows 构建脚本
REM ============================================

echo ==========================================
echo   GuguGaga AI VTuber Mobile 构建工具
echo ==========================================
echo.

REM 检查 Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未找到 Node.js
    echo 请先安装 Node.js: https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Node.js 已安装

REM 检查 npm
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未找到 npm
    pause
    exit /b 1
)
echo [OK] npm 已安装

REM 检查参数
if "%1"=="" goto :help
if "%1"=="setup" goto :setup
if "%1"=="android" goto :android
if "%1"=="ios" goto :ios
if "%1"=="all" goto :all
if "%1"=="preview" goto :preview
if "%1"=="help" goto :help
goto :help

:setup
echo.
echo 正在初始化环境...
echo.

REM 安装 Expo CLI
where expo >nul 2>nul
if %errorlevel% neq 0 (
    echo 正在安装 Expo CLI...
    call npm install -g expo-cli
)
echo [OK] Expo CLI 已安装

REM 安装 EAS CLI
where eas >nul 2>nul
if %errorlevel% neq 0 (
    echo 正在安装 EAS CLI...
    call npm install -g eas-cli
)
echo [OK] EAS CLI 已安装

REM 安装依赖
echo.
echo 正在安装依赖...
call npm install
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
echo [OK] 依赖安装成功

REM 登录
echo.
echo 请登录 Expo 账号
echo 如果没有账号，请先注册: https://expo.dev/signup
echo.
call expo login

echo.
echo 请登录 EAS 账号
call eas login

echo.
echo [完成] 环境初始化完成！
echo 现在可以运行 "build.bat android" 或 "build.bat ios" 构建应用
pause
exit /b 0

:android
echo.
echo 开始构建 Android APK...
echo 这可能需要 10-30 分钟，请耐心等待...
echo.

call eas build --platform android --profile production

if %errorlevel% equ 0 (
    echo.
    echo [成功] Android APK 构建成功！
    echo 请在 EAS 控制台下载 APK 文件
    echo https://expo.dev/accounts/[username]/projects/gugu-ai-vtuber/builds
) else (
    echo [错误] Android APK 构建失败
)
pause
exit /b %errorlevel%

:ios
echo.
echo 开始构建 iOS IPA...
echo 注意: iOS 构建需要 Apple Developer 账号
echo 这可能需要 15-45 分钟，请耐心等待...
echo.

call eas build --platform ios --profile production

if %errorlevel% equ 0 (
    echo.
    echo [成功] iOS IPA 构建成功！
    echo 请在 EAS 控制台下载 IPA 文件
    echo https://expo.dev/accounts/[username]/projects/gugu-ai-vtuber/builds
) else (
    echo [错误] iOS IPA 构建失败
)
pause
exit /b %errorlevel%

:all
echo.
echo 开始构建所有平台...
echo.

call eas build --platform all --profile production

if %errorlevel% equ 0 (
    echo.
    echo [成功] 所有平台构建成功！
    echo 请在 EAS 控制台下载安装包
) else (
    echo [错误] 构建失败
)
pause
exit /b %errorlevel%

:preview
echo.
echo 启动本地预览...
echo 请使用 Expo Go 应用扫描二维码
echo.
call expo start
pause
exit /b 0

:help
echo.
echo 使用方法: build.bat [命令]
echo.
echo 命令:
echo   setup     - 初始化环境（安装依赖、登录）
echo   android   - 构建 Android APK
echo   ios       - 构建 iOS IPA
echo   all       - 构建所有平台
echo   preview   - 本地预览
echo   help      - 显示帮助
echo.
echo 示例:
echo   build.bat setup     # 首次使用，初始化环境
echo   build.bat android   # 构建 Android APK
echo   build.bat all       # 构建所有平台
echo.
pause
exit /b 0
