@echo off
title GuguGaga AI VTuber

REM Switch to project root
cd /d "%~dp0.."

echo.
echo ========================================
echo    GuguGaga AI VTuber
echo    version: 1.9.82
echo ========================================
echo.

REM ========== Environment Variables ==========
set HF_HOME=%cd%\.cache\huggingface
set HF_ENDPOINT=https://hf-mirror.com
set PYTHONIOENCODING=utf-8

REM ========== Check Python (embedded first, fallback system) ==========
if exist "%~dp0..\python\python.exe" (
    set PYTHON_CMD=%~dp0..\python\python.exe
    echo [OK] Using embedded Python: %PYTHON_CMD%
) else (
    py -3.11 --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python 3.11 not found!
        echo Please run scripts\install_deps.bat first.
        pause
        exit /b 1
    )
    set PYTHON_CMD=py -3.11
    echo [OK] Using system Python: py -3.11
)

REM ========== Check PySide6 ==========
%PYTHON_CMD% -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo [INFO] PySide6 not installed, installing...
    %PYTHON_CMD% -m pip install PySide6 PySide6-Fluent-Widgets -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
)

REM ========== Check live2d ==========
%PYTHON_CMD% -c "import live2d" >nul 2>&1
if errorlevel 1 (
    echo [INFO] live2d-py not installed, installing...
    %PYTHON_CMD% -m pip install live2d-py -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
    if errorlevel 1 (
        echo [WARN] live2d-py install failed, Live2D will be disabled.
        echo        You can try manually: pip install live2d-py
    )
)

echo.
echo [OK] Environment ready. Starting native desktop...
echo.

REM Launch native desktop app
cd native
%PYTHON_CMD% main.py %*

pause
