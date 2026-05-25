@echo off
title GuguGaga AI VTuber
cd /d "%~dp0.."

echo.
echo ========================================
echo    GuguGaga AI VTuber - Browser Mode
echo    version: 1.11.1
echo ========================================
echo.

set HF_HOME=%cd%\.cache\huggingface
set HF_ENDPOINT=https://hf-mirror.com

REM -- Check Python --
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

echo.
echo [OK] Starting browser mode...
echo.

%PYTHON_CMD% -m app.main %*

pause
