@echo off
title GuguGaga AI VTuber

REM 閸掑洦宕查崚浼淬€嶉惄顔界壌閻╊喖缍嶉敍鍧哸t 閺傚洣娆㈤崷?scripts/ 鐎涙劗娲拌ぐ鏇氱瑓閿?cd /d "%~dp0.."

echo.
echo ========================================
echo    GuguGaga AI VTuber - Browser Mode
echo    version: 1.10.4
echo ========================================
echo.

REM ========== Environment Variables ==========
REM HuggingFace 濡€崇€风紓鎾崇摠閻╊喖缍嶉敍鍫ャ€嶉惄顔界壌閻╊喖缍嶆稉瀣畱 .cache/閿?set HF_HOME=%cd%\.cache\huggingface
set HF_ENDPOINT=https://hf-mirror.com

REM ========== Check Python (瀹撳苯鍙嗗蹇庣喘閸忓牞绱濋崶鐐衡偓鈧化鑽ょ埠鐎瑰顥? ==========
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
