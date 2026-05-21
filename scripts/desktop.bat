@echo off
title GuguGaga Desktop

REM 鍒囨崲鍒伴」鐩牴鐩綍锛坆at 鏂囦欢鍦?scripts/ 瀛愮洰褰曚笅锛?
cd /d "%~dp0.."

REM ============================================
REM  鍜曞挄鍢庡槑 AI-VTuber 妗岄潰鐗堝惎鍔ㄥ櫒
REM  鍙屽嚮姝ゆ枃浠跺嵆鍙惎鍔ㄦ闈㈠簲鐢?
REM ============================================

REM 鐜鍙橀噺
set HF_HOME=%cd%\.cache\huggingface
set HF_ENDPOINT=https://hf-mirror.com
set PYTHONIOENCODING=utf-8

REM 妫€鏌?Python锛堝祵鍏ュ紡浼樺厛锛屽洖閫€绯荤粺瀹夎锛?
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

REM 妫€鏌?pywebview锛堟闈㈢獥鍙ｅ簱锛?
%PYTHON_CMD% -c "import webview" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing pywebview...
    %PYTHON_CMD% -m pip install pywebview
)

REM 妫€鏌?pystray锛堢郴缁熸墭鐩橈紝鍙€夛級
%PYTHON_CMD% -c "import pystray" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing pystray + Pillow...
    %PYTHON_CMD% -m pip install pystray Pillow
)

REM 瑙ｉ櫎 pip 涓嬭浇 DLL 鐨勭綉缁滈攣瀹氭爣璁帮紙鍚﹀垯 .NET 鎷掔粷鍔犺浇 WebView2锛?
REM v1.9.59: 妫€鏌ユ爣璁版枃浠讹紝鍙繍琛屼竴娆?
if not exist "%cd%\logs\.dlls_unblocked" (
    powershell -Command "Get-ChildItem '%cd%\python\Lib\site-packages' -Recurse -Include *.dll,*.pyd | Unblock-File -ErrorAction SilentlyContinue" >nul 2>&1
    if not exist "%cd%\logs" mkdir "%cd%\logs"
    echo. > "%cd%\logs\.dlls_unblocked"
)

REM 鍚姩妗岄潰搴旂敤
echo Starting GuguGaga Desktop...
%PYTHON_CMD% launcher\launcher.py
if errorlevel 1 (
    echo.
    echo [ERROR] GuguGaga Desktop exited with an error.
    pause
)
