@echo off
title GuguGaga Desktop

REM 切换到项目根目录（bat 文件在 scripts/ 子目录下）
cd /d "%~dp0.."

REM ============================================
REM  咕咕嘎嘎 AI-VTuber 桌面版启动器
REM  双击此文件即可启动桌面应用
REM ============================================

REM 环境变量
set HF_HOME=%cd%\.cache\huggingface
set HF_ENDPOINT=https://hf-mirror.com
set PYTHONIOENCODING=utf-8

REM 检查 Python（嵌入式优先，回退系统安装）
if exist "%~dp0..\python\python.exe" (
    set PYTHON_CMD=%~dp0..\python\python.exe
    echo [OK] Using embedded Python: %PYTHON_CMD%
) else (
    py -3.11 --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python 3.11 not found!
        echo Please run install_deps.bat first.
        pause
        exit /b 1
    )
    set PYTHON_CMD=py -3.11
    echo [OK] Using system Python: py -3.11
)

REM 检查 pywebview（桌面窗口库）
%PYTHON_CMD% -c "import webview" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing pywebview...
    %PYTHON_CMD% -m pip install pywebview
)

REM 检查 pystray（系统托盘，可选）
%PYTHON_CMD% -c "import pystray" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing pystray + Pillow...
    %PYTHON_CMD% -m pip install pystray Pillow
)

REM 解除 pip 下载 DLL 的网络锁定标记（否则 .NET 拒绝加载 WebView2）
powershell -Command "Get-ChildItem '%cd%\python\Lib\site-packages' -Recurse -Include *.dll,*.pyd | Unblock-File -ErrorAction SilentlyContinue" >nul 2>&1

REM 启动桌面应用
echo Starting GuguGaga Desktop...
%PYTHON_CMD% launcher\launcher.py
if errorlevel 1 (
    echo.
    echo [ERROR] GuguGaga Desktop exited with an error.
    pause
)
