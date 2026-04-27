@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

REM ================================================================
REM  GuguGaga AI-VTuber - One-Click Setup
REM  Safe encoding: all output uses ASCII-safe markers [OK]/[!!]/[--]
REM  Chinese only in echo, never in variable names or paths
REM ================================================================

title GuguGaga Setup

echo.
echo  ======================================================
echo.
echo    GuguGaga AI-VTuber - One-Click Setup
echo.
echo    This script will:
echo      1. Download embedded Python 3.11
echo      2. Install all Python packages
echo      3. Download AI model files
echo      4. Print verification report
echo.
echo    All downloads use China mirror sources
echo    Estimated time: 20-40 minutes
echo.
echo  ======================================================
echo.
echo  Press any key to start, or close to cancel...
pause >nul

REM Switch to project root
cd /d "%~dp0.."

REM ========== Mirror Source Config ==========
set PIP_MIRROR=-i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
set HF_MIRROR=https://hf-mirror.com
set PY_EMBED_URL=https://registry.npmmirror.com/-/binary/python/3.11.9/python-3.11.9-embed-amd64.zip
set TORCH_MIRROR=https://mirrors.aliyun.com/pytorch-wheels/cu124

set REPORT_FILE=%~dp0setup_report.txt
set STEP=0
set TOTAL_STEPS=7

REM Init report (ASCII only in report file to avoid encoding issues)
echo GuguGaga AI-VTuber - Setup Report > "%REPORT_FILE%"
echo Date: %date% %time% >> "%REPORT_FILE%"
echo ======================================== >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"

REM ================================================================
REM  STEP 1: Detect / Download Embedded Python 3.11
REM ================================================================
set /a STEP+=1
echo.
echo  [%STEP%/%TOTAL_STEPS%] Embedded Python 3.11
echo  ----------------------------------------
echo.

REM Check system Python first (needed to download embedded version)
set SYS_PYTHON=
py -3.11 --version >nul 2>&1
if not errorlevel 1 (
    set SYS_PYTHON=py -3.11
    echo    [OK] System Python 3.11 detected
) else (
    python --version 2>nul | findstr "3.11" >nul
    if not errorlevel 1 (
        set SYS_PYTHON=python
        echo    [OK] System Python 3.11 detected
    )
)

if exist "python\python.exe" (
    echo    [OK] Embedded Python already exists - skipping
    for /f "tokens=*" %%v in ('"python\python.exe" --version 2^>^&1') do echo       %%v
    set PYTHON_CMD=python\python.exe
    echo    [OK] Embedded Python exists >> "%REPORT_FILE%"
) else (
    if "%SYS_PYTHON%"=="" (
        echo    [!!] No Python detected on this system!
        echo.
        echo    Embedded Python download requires system Python.
        echo    Please install Python 3.11 first:
        echo      https://www.python.org/downloads/release/python-3119/
        echo      Check "Add to PATH" during installation
        echo.
        echo    [!!] No system Python, cannot download embedded >> "%REPORT_FILE%"
        pause
        exit /b 1
    )

    echo    Downloading embedded Python 3.11.9 (~10MB, npmmirror)...
    if not exist "python" mkdir "python"

    %SYS_PYTHON% -c "import requests;url='https://registry.npmmirror.com/-/binary/python/3.11.9/python-3.11.9-embed-amd64.zip';r=requests.get(url,stream=True);r.raise_for_status();f=open(r'python\python-3.11.9-embed-amd64.zip','wb');total=int(r.headers.get('content-length',0));done=0;[(done:=done+len(c),f.write(c),print(f'  {done/1024/1024:.1f}MB / {total/1024/1024:.1f}MB',end='\r')) for c in r.iter_content(8192) if c];f.close();print('\n  [OK] Download complete')" 2>nul
    if errorlevel 1 (
        echo    [!!] Download failed! Check network connection
        echo    [!!] Embedded Python download failed >> "%REPORT_FILE%"
        pause
        exit /b 1
    )

    echo    Extracting...
    %SYS_PYTHON% -c "import zipfile;zipfile.ZipFile(r'python\python-3.11.9-embed-amd64.zip','r').extractall(r'python');print('  [OK] Extract complete')"
    del "python\python-3.11.9-embed-amd64.zip" 2>nul

    REM Configure _pth
    echo    Configuring Python paths...
    %SYS_PYTHON% -c "f=open(r'python\python311._pth','w');f.write('python311.zip\nLib\nLib\\site-packages\n..\nimport site\n');f.close();print('  [OK] Path config complete')"

    REM Install pip
    echo    Installing pip...
    %SYS_PYTHON% -c "import urllib.request;urllib.request.urlretrieve('https://bootstrap.pypa.io/get-pip.py','python\\get-pip.py')" 2>nul
    "python\python.exe" "python\get-pip.py" -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn >nul 2>&1
    del "python\get-pip.py" 2>nul

    set PYTHON_CMD=python\python.exe
    echo    [OK] Embedded Python installed!
    echo    [OK] Embedded Python installed >> "%REPORT_FILE%"
)
echo. >> "%REPORT_FILE%"

REM ================================================================
REM  STEP 2: Install Core Dependencies
REM ================================================================
set /a STEP+=1
echo.
echo  [%STEP%/%TOTAL_STEPS%] Python Packages (Tsinghua mirror)
echo  ----------------------------------------
echo.

REM Upgrade pip
echo    Upgrading pip...
%PYTHON_CMD% -m pip install --upgrade pip %PIP_MIRROR% >nul 2>&1
echo    [OK] pip upgraded

echo    Installing packages (may take several minutes)...
echo    [Package Install] >> "%REPORT_FILE%"

REM Core packages
call :install_pkg "yaml"                    "pyyaml>=6.0"                      "required"
call :install_pkg "requests"                "requests>=2.28.0"                  "required"
call :install_pkg "edge_tts"               "edge-tts>=7.0"                    "required"
call :install_pkg "websocket_server"        "websocket-server>=0.6"            "required"
call :install_pkg "websockets"              "websockets>=10.0"                  "required"
call :install_pkg "numpy"                   "numpy>=1.24.0,<2.0.0"            "required"
call :install_pkg "PIL"                     "pillow>=10.0"                     "required"
call :install_pkg "soundfile"               "soundfile"                         "required"
call :install_pkg "jieba"                   "jieba>=0.42"                       "required"
call :install_pkg "transformers"            "transformers>=4.44.0,<4.45.0"     "required"
call :install_pkg "peft"                    "peft>=0.10.0"                      "required"
call :install_pkg "accelerate"              "accelerate>=0.20.0"               "required"
call :install_pkg "pytorch_lightning"       "pytorch-lightning>=2.4"            "required"
call :install_pkg "matplotlib"              "matplotlib"                        "required"

REM ASR
call :install_pkg "faster_whisper"          "faster-whisper>=1.0"              "recommended"
call :install_pkg "funasr"                  "funasr>=1.0"                       "recommended"
call :install_pkg "sounddevice"             "sounddevice>=0.4"                  "recommended"

REM Vision/OCR
call :install_pkg "cv2"                     "opencv-python>=4.8"               "optional"
call :install_pkg "rapidocr_onnxruntime"    "rapidocr-onnxruntime>=1.3.0"      "optional"
call :install_pkg "modelscope"              "modelscope>=1.9.0"                "optional"

REM Memory system
call :install_pkg "sentence_transformers"   "sentence-transformers>=2.0"       "optional"
call :install_pkg "chromadb"                "chromadb"                          "optional"

REM GPT-SoVITS
call :install_pkg "bitsandbytes"            "bitsandbytes"                      "optional"
call :install_pkg "gradio"                  "gradio>=4.0,<5"                    "optional"
call :install_pkg "scipy"                   "scipy"                             "optional"
call :install_pkg "librosa"                 "librosa==0.10.2"                   "optional"
call :install_pkg "numba"                   "numba"                             "optional"
call :install_pkg "cn2an"                   "cn2an"                             "optional"
call :install_pkg "pypinyin"                "pypinyin"                          "optional"
call :install_pkg "sentencepiece"           "sentencepiece"                     "optional"
call :install_pkg "chardet"                 "chardet"                           "optional"
call :install_pkg "psutil"                  "psutil"                            "optional"
call :install_pkg "split_lang"              "split-lang"                        "optional"
call :install_pkg "fast_langdetect"         "fast-langdetect>=0.3.1"            "optional"
call :install_pkg "wordsegment"             "wordsegment"                       "optional"
call :install_pkg "rotary_embedding_torch"  "rotary-embedding-torch"            "optional"
call :install_pkg "opencc"                  "OpenCC-python-reimplemented"       "optional"
call :install_pkg "x_transformers"          "x_transformers"                    "optional"
call :install_pkg "torchmetrics"            "torchmetrics<=1.5"                 "optional"
call :install_pkg "ctranslate2"             "ctranslate2>=4.0,<5"               "optional"
call :install_pkg "av"                      "av>=11"                            "optional"
call :install_pkg "ffmpeg"                  "ffmpeg-python"                     "optional"
call :install_pkg "tiktoken"                "tiktoken"                          "optional"
call :install_pkg "mss"                     "mss>=10.0"                         "optional"

REM Windows
call :install_pkg "win32api"                "pywin32>=306"                      "optional"

echo    [OK] Package installation complete
echo. >> "%REPORT_FILE%"

REM ================================================================
REM  STEP 3: PyTorch CUDA
REM ================================================================
set /a STEP+=1
echo.
echo  [%STEP%/%TOTAL_STEPS%] PyTorch CUDA cu124 (Aliyun mirror)
echo  ----------------------------------------
echo.

%PYTHON_CMD% -X utf8 -c "import torch; has_cuda=torch.cuda.is_available(); ver=torch.__version__; print(f'VERSION={ver}'); print(f'CUDA={has_cuda}')" > "%TEMP%\torch_check.txt" 2>nul
set TORCH_CUDA=0
for /f "tokens=1,2 delims==" %%a in ('type "%TEMP%\torch_check.txt" 2^>nul ^| findstr "CUDA"') do (
    if "%%a"=="CUDA" if "%%b"=="True" set TORCH_CUDA=1
)

if "%TORCH_CUDA%"=="1" (
    echo    [OK] PyTorch CUDA already available
    echo    [OK] PyTorch CUDA already available >> "%REPORT_FILE%"
) else (
    echo    PyTorch CUDA not available, installing...
    echo    (Uninstalling old version first, then installing CUDA version)
    %PYTHON_CMD% -m pip uninstall torch torchvision torchaudio -y >nul 2>&1
    %PYTHON_CMD% -m pip install torch torchaudio torchvision -f %TORCH_MIRROR% %PIP_MIRROR%
    if errorlevel 1 (
        echo    [!!] PyTorch CUDA install failed! GPU inference unavailable
        echo    [!!] PyTorch CUDA install failed >> "%REPORT_FILE%"
    ) else (
        echo    [OK] PyTorch CUDA cu124 installed
        echo    [OK] PyTorch CUDA installed >> "%REPORT_FILE%"
    )
)
echo. >> "%REPORT_FILE%"

REM Unlock DLL (pip-downloaded DLLs have network marks, .NET refuses to load)
echo    Unlocking DLL security marks...
powershell -Command "Get-ChildItem 'python\Lib\site-packages' -Recurse -Include *.dll,*.pyd | Unblock-File -ErrorAction SilentlyContinue" >nul 2>&1
echo    [OK] DLLs unlocked

REM ================================================================
REM  STEP 4: GPT-SoVITS Pretrained Models
REM ================================================================
set /a STEP+=1
echo.
echo  [%STEP%/%TOTAL_STEPS%] GPT-SoVITS v3 Pretrained Models
echo  ----------------------------------------
echo.

set PRETRAINED_DIR=GPT-SoVITS\GPT_SoVITS\pretrained_models
if not exist "%PRETRAINED_DIR%" mkdir "%PRETRAINED_DIR%"

REM --- s2Gv3.pth ---
if exist "%PRETRAINED_DIR%\s2Gv3.pth" (
    for %%F in ("%PRETRAINED_DIR%\s2Gv3.pth") do (
        if %%~zF GTR 100000000 (
            echo    [OK] s2Gv3.pth already exists (%%~zF bytes) - skipping
            echo    [OK] s2Gv3.pth exists >> "%REPORT_FILE%"
        ) else (
            echo    [--] s2Gv3.pth exists but too small (corrupted?), re-downloading...
            del "%PRETRAINED_DIR%\s2Gv3.pth" 2>nul
        )
    )
)
if not exist "%PRETRAINED_DIR%\s2Gv3.pth" (
    echo    Downloading s2Gv3.pth (~733MB, HuggingFace CN mirror)...
    %PYTHON_CMD% -c "import requests;url='https://hf-mirror.com/jackal119/GPT-SoVITS-v3/resolve/main/pretrained_models/s2Gv3.pth';r=requests.get(url,stream=True);r.raise_for_status();f=open(r'%PRETRAINED_DIR%\s2Gv3.pth','wb');total=int(r.headers.get('content-length',0));done=0;[(done:=done+len(c),f.write(c),print(f'  {done/1024/1024:.1f}MB / {total/1024/1024:.1f}MB',end='\r')) for c in r.iter_content(8192) if c];f.close();print('\n  [OK] s2Gv3.pth download complete')" 2>nul
    if errorlevel 1 (
        echo    [!!] s2Gv3.pth download failed
        echo    Manual: https://hf-mirror.com/jackal119/GPT-SoVITS-v3/resolve/main/pretrained_models/s2Gv3.pth
        echo    [!!] s2Gv3.pth download failed >> "%REPORT_FILE%"
    ) else (
        echo    [OK] s2Gv3.pth download complete
        echo    [OK] s2Gv3.pth downloaded >> "%REPORT_FILE%"
    )
)

REM --- s1rv7.pth ---
if exist "%PRETRAINED_DIR%\s1rv7.pth" (
    for %%F in ("%PRETRAINED_DIR%\s1rv7.pth") do (
        if %%~zF GTR 100000000 (
            echo    [OK] s1rv7.pth already exists (%%~zF bytes) - skipping
            echo    [OK] s1rv7.pth exists >> "%REPORT_FILE%"
        ) else (
            echo    [--] s1rv7.pth exists but too small (corrupted?), re-downloading...
            del "%PRETRAINED_DIR%\s1rv7.pth" 2>nul
        )
    )
)
if not exist "%PRETRAINED_DIR%\s1rv7.pth" (
    echo    Downloading s1rv7.pth (~621MB, HuggingFace CN mirror)...
    %PYTHON_CMD% -c "import requests;url='https://hf-mirror.com/jackal119/GPT-SoVITS-v3/resolve/main/pretrained_models/s1rv7.pth';r=requests.get(url,stream=True);r.raise_for_status();f=open(r'%PRETRAINED_DIR%\s1rv7.pth','wb');total=int(r.headers.get('content-length',0));done=0;[(done:=done+len(c),f.write(c),print(f'  {done/1024/1024:.1f}MB / {total/1024/1024:.1f}MB',end='\r')) for c in r.iter_content(8192) if c];f.close();print('\n  [OK] s1rv7.pth download complete')" 2>nul
    if errorlevel 1 (
        echo    [!!] s1rv7.pth download failed
        echo    Manual: https://hf-mirror.com/jackal119/GPT-SoVITS-v3/resolve/main/pretrained_models/s1rv7.pth
        echo    [!!] s1rv7.pth download failed >> "%REPORT_FILE%"
    ) else (
        echo    [OK] s1rv7.pth download complete
        echo    [OK] s1rv7.pth downloaded >> "%REPORT_FILE%"
    )
)

REM --- chinese-hubert-base ---
if exist "%PRETRAINED_DIR%\chinese-hubert-base\pytorch_model.bin" (
    for %%F in ("%PRETRAINED_DIR%\chinese-hubert-base\pytorch_model.bin") do (
        if %%~zF GTR 100000000 (
            echo    [OK] chinese-hubert-base already exists (%%~zF bytes) - skipping
            echo    [OK] chinese-hubert-base exists >> "%REPORT_FILE%"
        ) else (
            echo    [--] chinese-hubert-base exists but too small, re-downloading...
            del "%PRETRAINED_DIR%\chinese-hubert-base\pytorch_model.bin" 2>nul
        )
    )
)
if not exist "%PRETRAINED_DIR%\chinese-hubert-base\pytorch_model.bin" (
    echo    Downloading chinese-hubert-base (~1.2GB, HuggingFace CN mirror)...
    set HUBERT_DIR=%PRETRAINED_DIR%\chinese-hubert-base
    if not exist "%HUBERT_DIR%" mkdir "%HUBERT_DIR%"
    %PYTHON_CMD% -c "import requests;url='https://hf-mirror.com/TencentGameMate/chinese-hubert-base/resolve/main/pytorch_model.bin';r=requests.get(url,stream=True);r.raise_for_status();f=open(r'%HUBERT_DIR%\pytorch_model.bin','wb');total=int(r.headers.get('content-length',0));done=0;[(done:=done+len(c),f.write(c),print(f'  {done/1024/1024:.1f}MB / {total/1024/1024:.1f}MB',end='\r')) for c in r.iter_content(8192) if c];f.close();print('\n  [OK] chinese-hubert-base download complete')" 2>nul
    if errorlevel 1 (
        echo    [!!] chinese-hubert-base download failed
        echo    [!!] chinese-hubert-base download failed >> "%REPORT_FILE%"
    ) else (
        echo    [OK] chinese-hubert-base download complete
        echo    [OK] chinese-hubert-base downloaded >> "%REPORT_FILE%"
    )
)
echo. >> "%REPORT_FILE%"

REM ================================================================
REM  STEP 5: G2PW Model
REM ================================================================
set /a STEP+=1
echo.
echo  [%STEP%/%TOTAL_STEPS%] G2PW Pinyin Model
echo  ----------------------------------------
echo.

set G2PW_DIR=GPT-SoVITS\GPT_SoVITS\text\G2PWModel
if exist "%G2PW_DIR%\g2pW.onnx" (
    for %%F in ("%G2PW_DIR%\g2pW.onnx") do (
        if %%~zF GTR 1000000 (
            echo    [OK] G2PW model already exists (%%~zF bytes) - skipping
            echo    [OK] G2PW model exists >> "%REPORT_FILE%"
        ) else (
            echo    [--] G2PW model exists but too small, re-downloading...
            rmdir /s /q "%G2PW_DIR%" 2>nul
        )
    )
)
if not exist "%G2PW_DIR%\g2pW.onnx" (
    echo    Downloading G2PW model (ModelScope CN mirror)...
    %PYTHON_CMD% -X utf8 -c "import os,requests,zipfile;model_dir=r'%G2PW_DIR%';os.makedirs(model_dir,exist_ok=True);parent=os.path.dirname(model_dir);zip_path=os.path.join(parent,'G2PWModel_1.1.zip');url='https://www.modelscope.cn/models/kamiorinn/g2pw/resolve/master/G2PWModel_1.1.zip';print('  Downloading...');r=requests.get(url,stream=True);r.raise_for_status();f=open(zip_path,'wb');[f.write(c) for c in r.iter_content(8192) if c];f.close();print('  Extracting...');zipfile.ZipFile(zip_path,'r').extractall(parent);os.rename(os.path.join(parent,'G2PWModel_1.1'),model_dir);os.remove(zip_path);print('  [OK] G2PW download complete')" 2>nul
    if errorlevel 1 (
        echo    [!!] G2PW model download failed
        echo    [!!] G2PW model download failed >> "%REPORT_FILE%"
    ) else (
        echo    [OK] G2PW model downloaded
        echo    [OK] G2PW model downloaded >> "%REPORT_FILE%"
    )
)
echo. >> "%REPORT_FILE%"

REM ================================================================
REM  STEP 6: Auto-download models info
REM ================================================================
set /a STEP+=1
echo.
echo  [%STEP%/%TOTAL_STEPS%] First-Start Auto-Download Models
echo  ----------------------------------------
echo.
echo    The following models will auto-download on first start:
echo.
echo    - ASR model (FunASR ~400MB / faster-whisper ~1.5GB)
echo    - Memory Embedding model (bge-base-zh-v1.5 ~400MB)
echo.
echo    If download fails, switch provider in config.yaml.
echo    [INFO] ASR + Embedding models auto-download on first start >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"

REM ================================================================
REM  STEP 7: Final Verification Report
REM ================================================================
set /a STEP+=1
echo.
echo  [%STEP%/%TOTAL_STEPS%] Final Verification
echo  ----------------------------------------
echo.

set VERIFY_OK=0
set VERIFY_FAIL=0
set VERIFY_WARN=0

echo [Verification Checklist] >> "%REPORT_FILE%"
echo ======================================== >> "%REPORT_FILE%"

REM 1. Python
if exist "python\python.exe" (
    echo    [OK] Embedded Python
    echo    [OK] Embedded Python >> "%REPORT_FILE%"
    set /a VERIFY_OK+=1
) else (
    echo    [!!] Embedded Python - MISSING
    echo    [!!] Embedded Python MISSING >> "%REPORT_FILE%"
    set /a VERIFY_FAIL+=1
)

REM 2. pip
%PYTHON_CMD% -m pip --version >nul 2>&1
if not errorlevel 1 (
    echo    [OK] pip
    echo    [OK] pip >> "%REPORT_FILE%"
    set /a VERIFY_OK+=1
) else (
    echo    [!!] pip - MISSING
    echo    [!!] pip MISSING >> "%REPORT_FILE%"
    set /a VERIFY_FAIL+=1
)

REM 3. PyTorch CUDA
%PYTHON_CMD% -c "import torch; assert torch.cuda.is_available()" >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%v in ('%PYTHON_CMD% -c "import torch; print(torch.__version__)" 2^>nul') do set TORCH_VER=%%v
    echo    [OK] PyTorch CUDA !TORCH_VER!
    echo    [OK] PyTorch CUDA !TORCH_VER! >> "%REPORT_FILE%"
    set /a VERIFY_OK+=1
) else (
    echo    [--] PyTorch CUDA - NOT AVAILABLE (CPU mode only)
    echo    [--] PyTorch CUDA not available >> "%REPORT_FILE%"
    set /a VERIFY_WARN+=1
)

REM 4. Core packages
for %%P in (yaml requests edge_tts websocket_server websockets numpy PIL soundfile jieba transformers peft accelerate pytorch_lightning matplotlib) do (
    %PYTHON_CMD% -c "import %%P" >nul 2>&1
    if not errorlevel 1 (
        echo    [OK] %%P
        echo    [OK] %%P >> "%REPORT_FILE%"
        set /a VERIFY_OK+=1
    ) else (
        echo    [!!] %%P - MISSING!
        echo    [!!] %%P MISSING >> "%REPORT_FILE%"
        set /a VERIFY_FAIL+=1
    )
)

REM 5. Model files
if exist "%PRETRAINED_DIR%\s2Gv3.pth" (
    for %%F in ("%PRETRAINED_DIR%\s2Gv3.pth") do (
        if %%~zF GTR 100000000 (
            echo    [OK] GPT-SoVITS SoVITS base model
            echo    [OK] s2Gv3.pth >> "%REPORT_FILE%"
            set /a VERIFY_OK+=1
        ) else (
            echo    [--] GPT-SoVITS SoVITS base model - FILE CORRUPTED
            echo    [--] s2Gv3.pth corrupted >> "%REPORT_FILE%"
            set /a VERIFY_WARN+=1
        )
    )
) else (
    echo    [!!] GPT-SoVITS SoVITS base model - MISSING!
    echo    [!!] s2Gv3.pth MISSING >> "%REPORT_FILE%"
    set /a VERIFY_FAIL+=1
)

if exist "%PRETRAINED_DIR%\s1rv7.pth" (
    for %%F in ("%PRETRAINED_DIR%\s1rv7.pth") do (
        if %%~zF GTR 100000000 (
            echo    [OK] GPT-SoVITS GPT base model
            echo    [OK] s1rv7.pth >> "%REPORT_FILE%"
            set /a VERIFY_OK+=1
        ) else (
            echo    [--] GPT-SoVITS GPT base model - FILE CORRUPTED
            echo    [--] s1rv7.pth corrupted >> "%REPORT_FILE%"
            set /a VERIFY_WARN+=1
        )
    )
) else (
    echo    [!!] GPT-SoVITS GPT base model - MISSING!
    echo    [!!] s1rv7.pth MISSING >> "%REPORT_FILE%"
    set /a VERIFY_FAIL+=1
)

if exist "%PRETRAINED_DIR%\chinese-hubert-base\pytorch_model.bin" (
    for %%F in ("%PRETRAINED_DIR%\chinese-hubert-base\pytorch_model.bin") do (
        if %%~zF GTR 100000000 (
            echo    [OK] chinese-hubert-base
            echo    [OK] chinese-hubert-base >> "%REPORT_FILE%"
            set /a VERIFY_OK+=1
        ) else (
            echo    [--] chinese-hubert-base - FILE CORRUPTED
            echo    [--] chinese-hubert-base corrupted >> "%REPORT_FILE%"
            set /a VERIFY_WARN+=1
        )
    )
) else (
    echo    [!!] chinese-hubert-base - MISSING!
    echo    [!!] chinese-hubert-base MISSING >> "%REPORT_FILE%"
    set /a VERIFY_FAIL+=1
)

if exist "%G2PW_DIR%\g2pW.onnx" (
    for %%F in ("%G2PW_DIR%\g2pW.onnx") do (
        if %%~zF GTR 1000000 (
            echo    [OK] G2PW pinyin model
            echo    [OK] G2PW model >> "%REPORT_FILE%"
            set /a VERIFY_OK+=1
        ) else (
            echo    [--] G2PW pinyin model - FILE CORRUPTED
            echo    [--] G2PW model corrupted >> "%REPORT_FILE%"
            set /a VERIFY_WARN+=1
        )
    )
) else (
    echo    [--] G2PW pinyin model - MISSING (Chinese TTS pinyin may be inaccurate)
    echo    [--] G2PW model MISSING >> "%REPORT_FILE%"
    set /a VERIFY_WARN+=1
)

echo. >> "%REPORT_FILE%"
echo Result: !VERIFY_OK! passed, !VERIFY_FAIL! failed, !VERIFY_WARN! warnings >> "%REPORT_FILE%"

REM ================================================================
REM  Final Summary
REM ================================================================
echo.
echo  ======================================================
echo.
if !VERIFY_FAIL!==0 (
    echo    SETUP COMPLETE - All checks passed!
) else (
    echo    SETUP COMPLETE - !VERIFY_FAIL! check(s) failed
)
echo.
echo    Results: [OK] !VERIFY_OK! passed  [!!] !VERIFY_FAIL! failed  [--] !VERIFY_WARN! warnings
echo.
echo    Report saved to: scripts\setup_report.txt
echo.
echo  ======================================================
echo.

if !VERIFY_FAIL!==0 (
    echo  Next steps:
    echo    1. Run scripts\go.bat to start browser mode
    echo    2. Enter your API key in the WebUI settings panel
    echo    3. Start chatting!
    echo.
) else (
    echo  [!!] Some checks failed. See [!!] marks above.
    echo    Core features may still work. Missing files can be
    echo    downloaded manually (see report for URLs).
    echo.
)

pause
exit /b 0


REM ========================================
REM  Function: install_pkg
REM  Args: %1=import name  %2=pip package  %3=required/recommended/optional
REM ========================================
:install_pkg
set "PKG_IMPORT=%~1"
set "PKG_PIP=%~2"
set "PKG_LEVEL=%~3"

REM Check if already installed - skip if present
%PYTHON_CMD% -c "import %PKG_IMPORT%" >nul 2>&1
if not errorlevel 1 (
    goto :eof
)

REM Not installed, proceed with installation
echo    [Installing] %PKG_PIP%...

REM First try: Tsinghua mirror
%PYTHON_CMD% -m pip install %PKG_PIP% %PIP_MIRROR% >nul 2>&1
if not errorlevel 1 (
    echo           [OK] %PKG_PIP%
    echo    [OK] %PKG_PIP% (Tsinghua mirror) >> "%REPORT_FILE%"
    goto :eof
)

REM Second try: Default PyPI
%PYTHON_CMD% -m pip install %PKG_PIP% >nul 2>&1
if not errorlevel 1 (
    echo           [OK] %PKG_PIP%
    echo    [OK] %PKG_PIP% (PyPI) >> "%REPORT_FILE%"
    goto :eof
)

REM Failed
if "%PKG_LEVEL%"=="required" (
    echo           [!!] %PKG_PIP% FAILED! (required)
    echo    [!!] %PKG_PIP% install failed - required >> "%REPORT_FILE%"
) else (
    echo           [--] %PKG_PIP% failed (optional, core still works)
    echo    [--] %PKG_PIP% install failed - optional >> "%REPORT_FILE%"
)

goto :eof
