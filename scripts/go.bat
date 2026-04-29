@echo off
title GuguGaga AI VTuber

REM 切换到项目根目录（bat 文件在 scripts/ 子目录下）
cd /d "%~dp0.."

echo.
echo ========================================
echo    GuguGaga AI VTuber - Browser Mode
echo    version: 1.9.38
echo ========================================
echo.

REM ========== Environment Variables ==========
REM HuggingFace 模型缓存目录（项目根目录下的 .cache/）
set HF_HOME=%cd%\.cache\huggingface
set HF_ENDPOINT=https://hf-mirror.com

REM ========== Check Python (嵌入式优先，回退系统安装) ==========
if exist "%~dp0..\python\python.exe" (
    set PYTHON_CMD=%~dp0..\python\python.exe
    echo [OK] Using embedded Python: %PYTHON_CMD%
) else (
    py -3.11 --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python 3.11 not found!
        echo Please run install_deps.bat first to install dependencies.
        pause
        exit /b 1
    )
    set PYTHON_CMD=py -3.11
    echo [OK] Using system Python: py -3.11
)

REM Launch the app
echo.
echo    GuguGaga AI VTuber - Browser Mode
echo    Model cache: %HF_HOME%
echo.

%PYTHON_CMD% -m app.main %*

pause
