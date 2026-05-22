@echo off
title GuguGaga Desktop

REM 閸掑洦宕查崚浼淬€嶉惄顔界壌閻╊喖缍嶉敍鍧哸t 閺傚洣娆㈤崷?scripts/ 鐎涙劗娲拌ぐ鏇氱瑓閿?
cd /d "%~dp0.."

REM ============================================
REM  閸滄洖鎸勯崲搴℃ AI-VTuber 濡楀矂娼伴悧鍫濇儙閸斻劌娅?
REM  閸欏苯鍤銈嗘瀮娴犺泛宓嗛崣顖氭儙閸斻劍顢戦棃銏犵安閻?
REM ============================================

REM 閻滎垰顣ㄩ崣姗€鍣?
set HF_HOME=%cd%\.cache\huggingface
set HF_ENDPOINT=https://hf-mirror.com
set PYTHONIOENCODING=utf-8

REM 濡偓閺?Python閿涘牆绁甸崗銉ョ础娴兼ê鍘涢敍灞芥礀闁偓缁崵绮虹€瑰顥婇敍?
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

REM 濡偓閺?pywebview閿涘牊顢戦棃銏㈢崶閸欙絽绨遍敍?
%PYTHON_CMD% -c "import webview" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing pywebview...
    %PYTHON_CMD% -m pip install pywebview
)

REM 濡偓閺?pystray閿涘牏閮寸紒鐔稿閻╂﹫绱濋崣顖炩偓澶涚礆
%PYTHON_CMD% -c "import pystray" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing pystray + Pillow...
    %PYTHON_CMD% -m pip install pystray Pillow
)

REM 鐟欙綁娅?pip 娑撳娴?DLL 閻ㄥ嫮缍夌紒婊堟敚鐎规碍鐖ｇ拋甯礄閸氾箑鍨?.NET 閹锋帞绮烽崝鐘烘祰 WebView2閿?
REM v1.9.59: 濡偓閺屻儲鐖ｇ拋鐗堟瀮娴犺绱濋崣顏囩箥鐞涘奔绔村▎?
if not exist "%cd%\logs\.dlls_unblocked" (
    powershell -Command "Get-ChildItem '%cd%\python\Lib\site-packages' -Recurse -Include *.dll,*.pyd | Unblock-File -ErrorAction SilentlyContinue" >nul 2>&1
    if not exist "%cd%\logs" mkdir "%cd%\logs"
    echo. > "%cd%\logs\.dlls_unblocked"
)

REM 閸氼垰濮╁宀勬桨鎼存梻鏁?
echo Starting GuguGaga Desktop...
%PYTHON_CMD% launcher\launcher.py
if errorlevel 1 (
    echo.
    echo [ERROR] GuguGaga Desktop exited with an error.
    pause
)
