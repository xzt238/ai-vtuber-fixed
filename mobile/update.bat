@echo off
REM ============================================
REM GuguGaga AI VTuber Mobile - OTA 热更新脚本
REM ============================================

echo ==========================================
echo   GuguGaga AI VTuber - OTA 热更新
echo ==========================================
echo.

cd /d "%~dp0"

REM 检查是否在项目目录
if not exist "package.json" (
    echo [错误] 未找到 package.json
    pause
    exit /b 1
)

REM 提交代码变更
echo [1/2] 提交代码变更...
git add -A
git commit -m "OTA update %date% %time%" 2>nul
if %errorlevel% neq 0 (
    echo [提示] 没有新的变更
)

REM 推送 OTA 更新
echo.
echo [2/2] 推送 OTA 热更新...
EAS_NO_VCS=1 npx eas-cli update --branch preview --message "Update %date% %time%" --non-interactive

if %errorlevel% equ 0 (
    echo.
    echo ==========================================
    echo   [成功] OTA 热更新已推送！
    echo   用户打开 App 自动下载更新
    echo ==========================================
) else (
    echo.
    echo [错误] OTA 更新推送失败
)

pause
