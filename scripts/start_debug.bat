@echo off
chcp 65001 >nul 2>&1
title GuguGaga AI VTuber (Debug)
cd /d "%~dp0.."

echo.
echo   ============================================
echo.
echo         GuguGaga AI VTuber (Debug Mode)
echo.
echo   ============================================
echo.

set HF_HOME=%cd%\.cache\huggingface
set HF_ENDPOINT=https://hf-mirror.com
set PYTHONIOENCODING=utf-8

echo   [1/4] Checking Python runtime...
if exist "%~dp0..\python\python.exe" (
    set PYTHON_CMD=%~dp0..\python\python.exe
    echo          OK - embedded Python
) else (
    py -3.11 --version >nul 2>&1
    if errorlevel 1 (
        echo          [ERROR] Python 3.11 not found!
        echo          Please run scripts\install_deps.bat first.
        pause
        exit /b 1
    )
    set PYTHON_CMD=py -3.11
    echo          OK - system Python: py -3.11
)

echo   [2/4] Checking dependencies...
%PYTHON_CMD% -m pip show PySide6 >nul 2>&1
if errorlevel 1 (
    echo          Installing PySide6...
    %PYTHON_CMD% -m pip install PySide6 PySide6-Fluent-Widgets PySide6-WebEngine -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
) else (
    echo          OK - PySide6
)

echo   [3/4] Setting up environment...
echo          HF_HOME: %cd%\.cache\huggingface
echo          HF_ENDPOINT: https://hf-mirror.com

echo   [4/4] Launching native desktop (debug mode)...
echo.
echo   ============================================
echo    Debug mode: CMD window remains open.
echo    For normal mode, use scripts\start.bat instead.
echo   ============================================
echo.

cd native
%PYTHON_CMD% main.py %*

pause
