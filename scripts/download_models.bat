@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title GuguGaga - Model & Python Downloader

echo.
echo  ======================================================
echo   GuguGaga AI VTuber - Model & Runtime Downloader
echo   version: 1.9.30
echo  ======================================================
echo.

REM Switch to project root
cd /d "%~dp0.."

REM ========== Config ==========
set HF_MIRROR=https://hf-mirror.com
set MODELSCOPE_MIRROR=https://www.modelscope.cn/models
set NPMMIRROR=https://registry.npmmirror.com/-/binary/python
set REPORT_FILE=%~dp0download_report.txt
set DL_OK=0
set DL_FAIL=0
set DL_SKIP=0

REM Check Python (for download scripts)
if exist "%~dp0..\python\python.exe" (
    set PYTHON_CMD=%~dp0..\python\python.exe
    echo [OK] Using embedded Python
) else (
    set PYTHON_CMD=py -3.11
    echo [OK] Using system Python
)

REM Init report
echo GuguGaga AI VTuber - Model Download Report > "%REPORT_FILE%"
echo Date: %date% %time% >> "%REPORT_FILE%"
echo ======================================== >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"

REM ========================================
REM  1/5  Embedded Python 3.11
REM ========================================
echo.
echo ========================================
echo   1/5  Embedded Python 3.11
echo ========================================
echo.

if exist "python\python.exe" (
    echo    [OK] Embedded Python already exists - skipping
    for /f "tokens=*" %%v in ('"python\python.exe" --version 2^>^&1') do echo       %%v
    echo    [OK] Embedded Python exists >> "%REPORT_FILE%"
    set /a DL_SKIP+=1
) else (
    echo    Embedded Python not found, downloading...
    echo    (Skip this if you don't need desktop mode)
    echo.
    set PY_ZIP_URL=https://registry.npmmirror.com/-/binary/python/3.11.9/python-3.11.9-embed-amd64.zip
    set PY_ZIP_PATH=python\python-3.11.9-embed-amd64.zip

    if not exist "python" mkdir "python"

    REM Check system Python
    %PYTHON_CMD% --version >nul 2>&1
    if not errorlevel 1 (
        echo    Downloading Python 3.11.9 embedded (~10MB, npmmirror)...
        %PYTHON_CMD% -c "import requests;url='https://registry.npmmirror.com/-/binary/python/3.11.9/python-3.11.9-embed-amd64.zip';r=requests.get(url,stream=True);r.raise_for_status();f=open(r'python\python-3.11.9-embed-amd64.zip','wb');total=int(r.headers.get('content-length',0));done=0;[(done:=done+len(c),f.write(c),print(f'  {done/1024/1024:.1f}MB / {total/1024/1024:.1f}MB',end='\r')) for c in r.iter_content(8192) if c];f.close();print('\n    [OK] Download complete')" 2>nul
        if not errorlevel 1 (
            echo    Extracting...
            %PYTHON_CMD% -c "import zipfile;zipfile.ZipFile(r'python\python-3.11.9-embed-amd64.zip','r').extractall(r'python');print('    [OK] Extracted')"
            if not errorlevel 1 (
                REM Install pip
                echo    Installing pip...
                %PYTHON_CMD% -c "import urllib.request;urllib.request.urlretrieve('https://bootstrap.pypa.io/get-pip.py','python\\get-pip.py')" 2>nul
                "python\python.exe" "python\get-pip.py" -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn >nul 2>&1
                del "python\get-pip.py" 2>nul

                REM Configure _pth
                echo    Configuring Python paths...
                %PYTHON_CMD% -c "f=open(r'python\python311._pth','w');f.write('python311.zip\nLib\nLib\\site-packages\n..\nimport site\n');f.close();print('    [OK] _pth configured')"

                REM Install PyTorch CUDA
                echo    Installing PyTorch CUDA cu124 (Aliyun mirror)...
                "python\python.exe" -m pip install torch torchaudio -f https://mirrors.aliyun.com/pytorch-wheels/cu124 -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn >nul 2>&1

                REM Unlock DLLs
                powershell -Command "Get-ChildItem 'python\Lib\site-packages' -Recurse -Include *.dll,*.pyd | Unblock-File -ErrorAction SilentlyContinue" >nul 2>&1

                echo    [OK] Embedded Python installed!
                echo    [OK] Embedded Python installed >> "%REPORT_FILE%"
                set /a DL_OK+=1
            ) else (
                echo    [!!] Extract failed
                echo    [!!] Embedded Python extract failed >> "%REPORT_FILE%"
                set /a DL_FAIL+=1
            )
            del "python\python-3.11.9-embed-amd64.zip" 2>nul
        ) else (
            echo    [!!] Download failed! Manual download:
            echo    URL: https://registry.npmmirror.com/-/binary/python/3.11.9/python-3.11.9-embed-amd64.zip
            echo    Extract to: python\ directory
            echo    [!!] Embedded Python download failed >> "%REPORT_FILE%"
            set /a DL_FAIL+=1
        )
    ) else (
        echo    [!!] No system Python found, cannot auto-download embedded version
        echo    Install Python 3.11 first: https://www.python.org/downloads/release/python-3119/
        echo    [!!] No system Python, cannot download embedded >> "%REPORT_FILE%"
        set /a DL_FAIL+=1
    )
)
echo. >> "%REPORT_FILE%"

REM ========================================
REM  2/5  GPT-SoVITS v3 Pretrained Models
REM ========================================
echo.
echo ========================================
echo   2/5  GPT-SoVITS v3 Pretrained Models
echo ========================================
echo.

set PRETRAINED_DIR=GPT-SoVITS\GPT_SoVITS\pretrained_models
if not exist "%PRETRAINED_DIR%" mkdir "%PRETRAINED_DIR%"

REM --- s2Gv3.pth ---
if exist "%PRETRAINED_DIR%\s2Gv3.pth" (
    echo    [OK] s2Gv3.pth already exists - skipping
    echo    [OK] s2Gv3.pth exists >> "%REPORT_FILE%"
    set /a DL_SKIP+=1
) else (
    echo    Downloading s2Gv3.pth (~733MB, HuggingFace CN mirror)...
    %PYTHON_CMD% -c "import requests;url='https://hf-mirror.com/jackal119/GPT-SoVITS-v3/resolve/main/pretrained_models/s2Gv3.pth';r=requests.get(url,stream=True);r.raise_for_status();f=open(r'%PRETRAINED_DIR%\s2Gv3.pth','wb');total=int(r.headers.get('content-length',0));done=0;[(done:=done+len(c),f.write(c),print(f'  {done/1024/1024:.1f}MB / {total/1024/1024:.1f}MB',end='\r')) for c in r.iter_content(8192) if c];f.close();print('\n    [OK] s2Gv3.pth download complete')" 2>nul
    if errorlevel 1 (
        echo    [!!] s2Gv3.pth download failed
        echo    Manual: https://hf-mirror.com/jackal119/GPT-SoVITS-v3/resolve/main/pretrained_models/s2Gv3.pth
        echo    Path: %PRETRAINED_DIR%\s2Gv3.pth
        echo    [!!] s2Gv3.pth download failed >> "%REPORT_FILE%"
        set /a DL_FAIL+=1
    ) else (
        echo    [OK] s2Gv3.pth downloaded
        echo    [OK] s2Gv3.pth downloaded >> "%REPORT_FILE%"
        set /a DL_OK+=1
    )
)

REM --- s1rv7.pth ---
if exist "%PRETRAINED_DIR%\s1rv7.pth" (
    echo    [OK] s1rv7.pth already exists - skipping
    echo    [OK] s1rv7.pth exists >> "%REPORT_FILE%"
    set /a DL_SKIP+=1
) else (
    echo    Downloading s1rv7.pth (~621MB, HuggingFace CN mirror)...
    %PYTHON_CMD% -c "import requests;url='https://hf-mirror.com/jackal119/GPT-SoVITS-v3/resolve/main/pretrained_models/s1rv7.pth';r=requests.get(url,stream=True);r.raise_for_status();f=open(r'%PRETRAINED_DIR%\s1rv7.pth','wb');total=int(r.headers.get('content-length',0));done=0;[(done:=done+len(c),f.write(c),print(f'  {done/1024/1024:.1f}MB / {total/1024/1024:.1f}MB',end='\r')) for c in r.iter_content(8192) if c];f.close();print('\n    [OK] s1rv7.pth download complete')" 2>nul
    if errorlevel 1 (
        echo    [!!] s1rv7.pth download failed
        echo    Manual: https://hf-mirror.com/jackal119/GPT-SoVITS-v3/resolve/main/pretrained_models/s1rv7.pth
        echo    Path: %PRETRAINED_DIR%\s1rv7.pth
        echo    [!!] s1rv7.pth download failed >> "%REPORT_FILE%"
        set /a DL_FAIL+=1
    ) else (
        echo    [OK] s1rv7.pth downloaded
        echo    [OK] s1rv7.pth downloaded >> "%REPORT_FILE%"
        set /a DL_OK+=1
    )
)

REM --- chinese-hubert-base ---
if exist "%PRETRAINED_DIR%\chinese-hubert-base\pytorch_model.bin" (
    echo    [OK] chinese-hubert-base already exists - skipping
    echo    [OK] chinese-hubert-base exists >> "%REPORT_FILE%"
    set /a DL_SKIP+=1
) else (
    echo    Downloading chinese-hubert-base (~1.2GB, HuggingFace CN mirror)...
    set HUBERT_DIR=%PRETRAINED_DIR%\chinese-hubert-base
    if not exist "%HUBERT_DIR%" mkdir "%HUBERT_DIR%"
    %PYTHON_CMD% -c "import requests;url='https://hf-mirror.com/TencentGameMate/chinese-hubert-base/resolve/main/pytorch_model.bin';r=requests.get(url,stream=True);r.raise_for_status();f=open(r'%HUBERT_DIR%\pytorch_model.bin','wb');total=int(r.headers.get('content-length',0));done=0;[(done:=done+len(c),f.write(c),print(f'  {done/1024/1024:.1f}MB / {total/1024/1024:.1f}MB',end='\r')) for c in r.iter_content(8192) if c];f.close();print('\n    [OK] chinese-hubert-base download complete')" 2>nul
    if errorlevel 1 (
        echo    [!!] chinese-hubert-base download failed
        echo    Manual: https://hf-mirror.com/TencentGameMate/chinese-hubert-base
        echo    [!!] chinese-hubert-base download failed >> "%REPORT_FILE%"
        set /a DL_FAIL+=1
    ) else (
        echo    [OK] chinese-hubert-base downloaded
        echo    [OK] chinese-hubert-base downloaded >> "%REPORT_FILE%"
        set /a DL_OK+=1
    )
)
echo. >> "%REPORT_FILE%"

REM ========================================
REM  3/5  G2PW Pinyin Model
REM ========================================
echo.
echo ========================================
echo   3/5  G2PW Pinyin Model
echo ========================================
echo.

set G2PW_DIR=GPT-SoVITS\GPT_SoVITS\text\G2PWModel
if exist "%G2PW_DIR%\g2pW.onnx" (
    echo    [OK] G2PW model already exists - skipping
    echo    [OK] G2PW model exists >> "%REPORT_FILE%"
    set /a DL_SKIP+=1
) else (
    echo    Downloading G2PW model (ModelScope CN mirror)...
    %PYTHON_CMD% -X utf8 -c "import os,requests,zipfile;model_dir=r'%G2PW_DIR%';os.makedirs(model_dir,exist_ok=True);parent=os.path.dirname(model_dir);zip_path=os.path.join(parent,'G2PWModel_1.1.zip');url='https://www.modelscope.cn/models/kamiorinn/g2pw/resolve/master/G2PWModel_1.1.zip';print('  Downloading...');r=requests.get(url,stream=True);r.raise_for_status();f=open(zip_path,'wb');[f.write(c) for c in r.iter_content(8192) if c];f.close();print('  Extracting...');zipfile.ZipFile(zip_path,'r').extractall(parent);os.rename(os.path.join(parent,'G2PWModel_1.1'),model_dir);os.remove(zip_path);print('  [OK] G2PW model downloaded!')" 2>nul
    if errorlevel 1 (
        echo    [!!] G2PW model download failed
        echo    [!!] G2PW model download failed >> "%REPORT_FILE%"
        set /a DL_FAIL+=1
    ) else (
        echo    [OK] G2PW model downloaded
        echo    [OK] G2PW model downloaded >> "%REPORT_FILE%"
        set /a DL_OK+=1
    )
)
echo. >> "%REPORT_FILE%"

REM ========================================
REM  4/5  ASR Model Info
REM ========================================
echo.
echo ========================================
echo   4/5  ASR Voice Recognition Models
echo ========================================
echo.
echo    ASR models auto-download on first start (via HuggingFace CN mirror)
echo    FunASR model: ~400MB, faster-whisper model: ~1.5GB
echo    If download fails, switch ASR provider in config.yaml
echo    [INFO] ASR models auto-download on first start >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"

REM ========================================
REM  5/5  Memory Embedding Model Info
REM ========================================
echo.
echo ========================================
echo   5/5  Memory System Embedding Model
echo ========================================
echo.
echo    Embedding model auto-downloads on first use
echo    Model: BAAI/bge-base-zh-v1.5 (~400MB)
echo    CN mirror: https://hf-mirror.com/BAAI/bge-base-zh-v1.5
echo    [INFO] Embedding model auto-downloads on first use >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"

REM ========================================
REM  Final Verification
REM ========================================
echo.
echo ========================================
echo   Final Verification
echo ========================================
echo.

set VERIFY_OK=0
set VERIFY_FAIL=0

echo [Verification Checklist] >> "%REPORT_FILE%"
echo ======================================== >> "%REPORT_FILE%"

REM Embedded Python
if exist "python\python.exe" (
    echo    [OK] python\python.exe
    echo    [OK] Embedded Python >> "%REPORT_FILE%"
    set /a VERIFY_OK+=1
) else (
    echo    [--] python\python.exe - MISSING (desktop mode unavailable, browser mode OK)
    echo    [--] Embedded Python MISSING >> "%REPORT_FILE%"
    set /a VERIFY_FAIL+=1
)

REM PyTorch CUDA
%PYTHON_CMD% -c "import torch; assert torch.cuda.is_available()" >nul 2>&1
if not errorlevel 1 (
    echo    [OK] PyTorch CUDA available
    echo    [OK] PyTorch CUDA >> "%REPORT_FILE%"
    set /a VERIFY_OK+=1
) else (
    echo    [--] PyTorch CUDA not available (GPU inference disabled)
    echo    [--] PyTorch CUDA not available >> "%REPORT_FILE%"
    set /a VERIFY_FAIL+=1
)

REM GPT-SoVITS base models
if exist "%PRETRAINED_DIR%\s2Gv3.pth" (
    echo    [OK] GPT-SoVITS SoVITS base model (s2Gv3.pth)
    echo    [OK] s2Gv3.pth >> "%REPORT_FILE%"
    set /a VERIFY_OK+=1
) else (
    echo    [!!] GPT-SoVITS SoVITS base model (s2Gv3.pth) - MISSING! Voice clone unavailable
    echo    [!!] s2Gv3.pth MISSING >> "%REPORT_FILE%"
    set /a VERIFY_FAIL+=1
)

if exist "%PRETRAINED_DIR%\s1rv7.pth" (
    echo    [OK] GPT-SoVITS GPT base model (s1rv7.pth)
    echo    [OK] s1rv7.pth >> "%REPORT_FILE%"
    set /a VERIFY_OK+=1
) else (
    echo    [!!] GPT-SoVITS GPT base model (s1rv7.pth) - MISSING! Voice clone unavailable
    echo    [!!] s1rv7.pth MISSING >> "%REPORT_FILE%"
    set /a VERIFY_FAIL+=1
)

if exist "%PRETRAINED_DIR%\chinese-hubert-base\pytorch_model.bin" (
    echo    [OK] chinese-hubert-base
    echo    [OK] chinese-hubert-base >> "%REPORT_FILE%"
    set /a VERIFY_OK+=1
) else (
    echo    [!!] chinese-hubert-base - MISSING! GPT-SoVITS unavailable
    echo    [!!] chinese-hubert-base MISSING >> "%REPORT_FILE%"
    set /a VERIFY_FAIL+=1
)

REM G2PW
if exist "%G2PW_DIR%\g2pW.onnx" (
    echo    [OK] G2PW pinyin model
    echo    [OK] G2PW model >> "%REPORT_FILE%"
    set /a VERIFY_OK+=1
) else (
    echo    [--] G2PW pinyin model - MISSING (Chinese TTS pinyin may be inaccurate)
    echo    [--] G2PW model MISSING >> "%REPORT_FILE%"
    set /a VERIFY_FAIL+=1
)

echo. >> "%REPORT_FILE%"
echo Verification: %VERIFY_OK% passed, %VERIFY_FAIL% failed >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"
echo ======================================== >> "%REPORT_FILE%"
echo   Download Stats >> "%REPORT_FILE%"
echo ======================================== >> "%REPORT_FILE%"
echo  Downloaded: %DL_OK% >> "%REPORT_FILE%"
echo  Failed:     %DL_FAIL% >> "%REPORT_FILE%"
echo  Skipped:    %DL_SKIP% >> "%REPORT_FILE%"

echo.
echo  ======================================================
echo   Download complete!
echo.
echo   Downloaded: %DL_OK%
echo   Failed:     %DL_FAIL%
echo   Skipped:    %DL_SKIP%
echo.
echo   Verification: [OK] %VERIFY_OK% passed  [!!] %VERIFY_FAIL% failed
echo.
echo   Report saved to: download_report.txt
echo  ======================================================
echo.

if "%VERIFY_FAIL%"=="0" (
    echo  All key files ready! Next steps:
    echo    scripts\install_deps.bat  - Install Python packages
    echo    scripts\go.bat            - Start AI VTuber
    echo    scripts\desktop.bat       - Start in desktop mode
) else (
    echo  [!!] %VERIFY_FAIL% check(s) failed. See [!!] marks above.
    echo    Missing files need manual download, URLs shown above.
)
echo.
pause
exit /b 0
