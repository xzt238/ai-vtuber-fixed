@echo off
REM ============================================
REM GuguGaga AI VTuber Mobile - 大版本重新构建脚本
REM 仅在以下情况使用：
REM   - 添加了新的 npm 依赖
REM   - 修改了 app.json 配置
REM   - 修改了原生权限/图标
REM   - 大版本更新
REM ============================================

echo ==========================================
echo   GuguGaga AI VTuber - 重新构建 APK
echo ==========================================
echo.

cd /d "%~dp0"

REM 检查是否在项目目录
if not exist "package.json" (
    echo [错误] 未找到 package.json
    pause
    exit /b 1
)

REM 版本号递增
echo [1/4] 更新版本号...
for /f "tokens=2 delims=:, " %%a in ('findstr "versionCode" app.json') do set /a v=%%a+1
echo 当前版本号: %v%

REM 提交代码
echo.
echo [2/4] 提交代码...
git add -A
git commit -m "Release v1.0.%v%" 2>nul

REM 构建 APK
echo.
echo [3/4] 开始构建 Android APK...
echo 这可能需要 10-20 分钟...
echo.

EAS_NO_VCS=1 npx eas-cli build --platform android --profile preview --non-interactive

if %errorlevel% equ 0 (
    echo.
    echo ==========================================
    echo   [成功] APK 构建完成！
    echo ==========================================
    echo.
    echo   请在 EAS 控制台下载 APK:
    echo   https://expo.dev/accounts/xzt238/projects/gugu-ai-vtuber/builds
    echo.
) else (
    echo.
    echo [错误] 构建失败
)

pause
