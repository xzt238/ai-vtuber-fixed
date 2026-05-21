@echo off
title GuguGaga AI VTuber

REM 鍒囨崲鍒伴」鐩牴鐩綍锛坆at 鏂囦欢鍦?scripts/ 瀛愮洰褰曚笅锛?cd /d "%~dp0.."

echo.
echo ========================================
echo    GuguGaga AI VTuber - Browser Mode
echo    version: 1.10.2
echo ========================================
echo.

REM ========== Environment Variables ==========
REM HuggingFace 妯″瀷缂撳瓨鐩綍锛堥」鐩牴鐩綍涓嬬殑 .cache/锛?set HF_HOME=%cd%\.cache\huggingface
set HF_ENDPOINT=https://hf-mirror.com

REM ========== Check Python (宓屽叆寮忎紭鍏堬紝鍥為€€绯荤粺瀹夎) ==========
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
