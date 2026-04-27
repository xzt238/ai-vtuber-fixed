@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
title GuguGaga - Smart Dependency Installer

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║  GuguGaga AI VTuber - 智能依赖安装器            ║
echo  ║  version: 1.9.30                                 ║
echo  ╚══════════════════════════════════════════════════╝
echo.

REM ========== 配置 ==========
set PIP_MIRROR=-i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
REM 检查 Python：嵌入式优先，回退系统安装
if exist "%~dp0..\python\python.exe" (
    set PYTHON_CMD=%~dp0..\python\python.exe
    echo    [OK] Using embedded Python
) else (
    set PYTHON_CMD=py -3.11
)
set REPORT_FILE=%~dp0install_report.txt
set TOTAL=0
set OK_COUNT=0
set MISS_COUNT=0
set FAIL_COUNT=0
set SKIP_COUNT=0

REM 初始化报告文件
echo GuguGaga AI VTuber - 依赖安装报告 > "%REPORT_FILE%"
echo 生成时间: %date% %time% >> "%REPORT_FILE%"
echo ======================================== >> "%REPORT_FILE%"
echo. >> "%REPORT_FILE%"

REM ========================================
REM  STEP 1: 检查 Python 3.11
REM ========================================
echo [1] 检查 Python 3.11...
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo    [错误] 未找到 Python 3.11！
    echo    请从以下地址安装: https://www.python.org/downloads/release/python-3119/
    echo    安装时请勾选 "Add to PATH"
    echo.
    echo [PYTHON] 缺失 - 未安装 >> "%REPORT_FILE%"
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('%PYTHON_CMD% --version 2^>^&1') do (
    echo    [OK] %%v
    echo [PYTHON] 已安装 - %%v >> "%REPORT_FILE%"
)
echo. >> "%REPORT_FILE%"

REM ========================================
REM  STEP 2: 升级 pip
REM ========================================
echo.
echo [2] 升级 pip...
%PYTHON_CMD% -m pip install --upgrade pip %PIP_MIRROR% >nul 2>&1
if errorlevel 1 (
    %PYTHON_CMD% -m pip install --upgrade pip >nul 2>&1
    if errorlevel 1 (
        echo    [警告] pip 升级失败，继续使用当前版本
    ) else (
        echo    [OK] pip 已升级 (PyPI)
    )
) else (
    echo    [OK] pip 已升级 (清华镜像)
)
echo. >> "%REPORT_FILE%"

REM ========================================
REM  STEP 3: 逐包检查与安装
REM ========================================
echo.
echo ========================================
echo   逐包检查与安装（清华镜像源）
echo ========================================
echo.

REM ===== 定义安装函数（通过 call :install_pkg 调用）=====
REM 参数: %1=import名, %2=pip包名, %3=分类, %4=是否必须(required/optional)

call :install_pkg "yaml"                    "pyyaml>=6.0"                      "核心"      "required"
call :install_pkg "requests"                "requests>=2.28.0"                  "核心"      "required"
call :install_pkg "edge_tts"               "edge-tts>=7.0"                    "核心"      "required"
call :install_pkg "websocket_server"        "websocket-server>=0.6"            "核心"      "required"
call :install_pkg "websockets"              "websockets>=10.0"                  "核心"      "required"
call :install_pkg "numpy"                   "numpy>=1.24.0,<2.0.0"            "音频/图像"  "required"
call :install_pkg "PIL"                     "pillow>=10.0"                     "音频/图像"  "required"
call :install_pkg "soundfile"               "soundfile"                         "音频/图像"  "required"
call :install_pkg "faster_whisper"          "faster-whisper>=1.0"              "ASR语音识别" "recommended"
call :install_pkg "funasr"                  "funasr>=1.0"                       "ASR语音识别" "recommended"
call :install_pkg "sounddevice"             "sounddevice>=0.4"                  "ASR语音识别" "recommended"
call :install_pkg "jieba"                   "jieba>=0.42"                       "中文NLP"   "required"
call :install_pkg "mss"                     "mss>=10.0"                         "屏幕捕获"  "recommended"
call :install_pkg "cv2"                     "opencv-python>=4.8"               "视觉/OCR"   "optional"
call :install_pkg "rapidocr_onnxruntime"    "rapidocr-onnxruntime>=1.3.0"      "视觉/OCR"   "optional"
call :install_pkg "modelscope"              "modelscope>=1.9.0"                "视觉/OCR"   "optional"
call :install_pkg "transformers"            "transformers>=4.44.0,<4.45.0"     "ML框架"    "required"
call :install_pkg "peft"                    "peft>=0.10.0"                      "ML框架"    "required"
call :install_pkg "accelerate"              "accelerate>=0.20.0"               "ML框架"    "required"
call :install_pkg "sentence_transformers"   "sentence-transformers>=2.0"       "记忆系统"  "optional"
call :install_pkg "chromadb"                "chromadb"                          "记忆系统"  "optional"
call :install_pkg "bitsandbytes"            "bitsandbytes"                      "MiniCPM视觉" "optional"
call :install_pkg "pytorch_lightning"       "pytorch-lightning>=2.4"            "GPT-SoVITS" "required"
call :install_pkg "matplotlib"              "matplotlib"                        "GPT-SoVITS" "required"
call :install_pkg "tensorboard"             "tensorboard"                       "GPT-SoVITS" "optional"
call :install_pkg "gradio"                  "gradio>=4.0,<5"                    "GPT-SoVITS" "optional"
call :install_pkg "scipy"                   "scipy"                             "GPT-SoVITS" "optional"
call :install_pkg "librosa"                 "librosa==0.10.2"                   "GPT-SoVITS" "optional"
call :install_pkg "numba"                   "numba"                             "GPT-SoVITS" "optional"
call :install_pkg "cn2an"                   "cn2an"                             "GPT-SoVITS" "optional"
call :install_pkg "pypinyin"                "pypinyin"                          "GPT-SoVITS" "optional"
call :install_pkg "pyopenjtalk"             "pyopenjtalk>=0.4.1"                "GPT-SoVITS" "optional"
call :install_pkg "g2p_en"                  "g2p_en"                            "GPT-SoVITS" "optional"
call :install_pkg "sentencepiece"           "sentencepiece"                     "GPT-SoVITS" "optional"
call :install_pkg "chardet"                 "chardet"                           "GPT-SoVITS" "optional"
call :install_pkg "psutil"                  "psutil"                            "GPT-SoVITS" "optional"
call :install_pkg "jieba_fast"              "jieba_fast"                        "GPT-SoVITS" "optional"
REM jieba_fast 编译需要 C++，如安装失败不影响核心功能（自动降级到 jieba）
call :install_pkg "split_lang"              "split-lang"                        "GPT-SoVITS" "optional"
call :install_pkg "fast_langdetect"         "fast-langdetect>=0.3.1"            "GPT-SoVITS" "optional"
call :install_pkg "wordsegment"             "wordsegment"                       "GPT-SoVITS" "optional"
call :install_pkg "rotary_embedding_torch"  "rotary-embedding-torch"            "GPT-SoVITS" "optional"
call :install_pkg "opencc"                  "OpenCC-python-reimplemented"       "GPT-SoVITS" "optional"
call :install_pkg "x_transformers"          "x_transformers"                    "GPT-SoVITS" "optional"
call :install_pkg "torchmetrics"            "torchmetrics<=1.5"                 "GPT-SoVITS" "optional"
call :install_pkg "ctranslate2"             "ctranslate2>=4.0,<5"               "GPT-SoVITS" "optional"
call :install_pkg "av"                      "av>=11"                            "GPT-SoVITS" "optional"
call :install_pkg "ffmpeg"                  "ffmpeg-python"                     "GPT-SoVITS" "optional"
call :install_pkg "tiktoken"                "tiktoken"                          "LLM工具"   "optional"

REM ========================================
REM  STEP 4: PyTorch CUDA 版本
REM ========================================
echo.
echo ========================================
echo   PyTorch CUDA 检查与安装
echo ========================================
echo.

%PYTHON_CMD% -X utf8 -c "import torch; has_cuda=torch.cuda.is_available(); ver=torch.__version__; print(f'VERSION={ver}'); print(f'CUDA={has_cuda}')" > "%TEMP%\torch_check.txt" 2>nul
set TORCH_OK=0
set TORCH_CUDA=0
for /f "tokens=1,2 delims==" %%a in ('type "%TEMP%\torch_check.txt" 2^>nul ^| findstr "VERSION CUDA"') do (
    if "%%a"=="VERSION" set TORCH_VER=%%b
    if "%%a"=="CUDA" (
        if "%%b"=="True" set TORCH_CUDA=1
    )
)

if defined TORCH_VER (
    echo    当前 PyTorch: %TORCH_VER%
    if "%TORCH_CUDA%"=="1" (
        echo    [OK] CUDA 可用
        echo [PyTorch] 已安装 - %TORCH_VER% (CUDA可用) >> "%REPORT_FILE%"
        set TORCH_OK=1
    ) else (
        echo    [警告] PyTorch 已安装但 CUDA 不可用
        echo    正在重新安装 CUDA 版本...
        echo [PyTorch] 已安装但CUDA不可用，重新安装中... >> "%REPORT_FILE%"
    )
) else (
    echo    PyTorch 未安装，正在安装 CUDA 版本...
    echo [PyTorch] 未安装，正在安装CUDA版本... >> "%REPORT_FILE%"
)

if "%TORCH_OK%"=="0" (
    echo.
    echo    正在安装 PyTorch CUDA cu124 版本...
    echo    (先卸载旧版本，再从阿里云镜像安装)
    %PYTHON_CMD% -m pip uninstall torch torchvision torchaudio -y >nul 2>&1
    %PYTHON_CMD% -m pip install torch torchaudio torchvision -f https://mirrors.aliyun.com/pytorch-wheels/cu124 %PIP_MIRROR%
    if errorlevel 1 (
        echo    [失败] PyTorch CUDA 安装失败！MiniCPM/GPT-SoVITS GPU 推理将不可用
        echo [PyTorch] 安装失败 - CUDA cu124 安装错误 >> "%REPORT_FILE%"
        set /a FAIL_COUNT+=1
    ) else (
        echo    [OK] PyTorch CUDA cu124 已安装
        echo [PyTorch] 已安装 - CUDA cu124 >> "%REPORT_FILE%"
        set /a OK_COUNT+=1
    )
)
echo. >> "%REPORT_FILE%"

REM ========================================
REM  STEP 5: G2PW 模型下载
REM ========================================
echo.
echo ========================================
echo   G2PW 模型检查
echo ========================================
echo.

set G2PW_DIR=%~dp0GPT-SoVITS\GPT_SoVITS\text\G2PWModel
if exist "%G2PW_DIR%\g2pW.onnx" (
    echo    [OK] G2PW 模型已存在
    echo [G2PW模型] 已存在 >> "%REPORT_FILE%"
) else (
    echo    正在下载 G2PW 模型 (ModelScope)...
    %PYTHON_CMD% -X utf8 -c "import os,requests,zipfile;model_dir=r'%G2PW_DIR%';os.makedirs(model_dir,exist_ok=True);parent=os.path.dirname(model_dir);zip_path=os.path.join(parent,'G2PWModel_1.1.zip');url='https://www.modelscope.cn/models/kamiorinn/g2pw/resolve/master/G2PWModel_1.1.zip';print('Downloading...');r=requests.get(url,stream=True);r.raise_for_status();f=open(zip_path,'wb');[f.write(c) for c in r.iter_content(8192) if c];f.close();print('Extracting...');zipfile.ZipFile(zip_path,'r').extractall(parent);os.rename(os.path.join(parent,'G2PWModel_1.1'),model_dir);os.remove(zip_path);print('G2PW model downloaded!')" 2>nul
    if errorlevel 1 (
        echo    [警告] G2PW 模型下载失败 - 首次使用时会自动重试
        echo [G2PW模型] 下载失败 >> "%REPORT_FILE%"
        set /a MISS_COUNT+=1
    ) else (
        echo    [OK] G2PW 模型已下载
        echo [G2PW模型] 已下载 >> "%REPORT_FILE%"
    )
)
echo. >> "%REPORT_FILE%"

REM ========================================
REM  STEP 6: pywin32 (Windows 专用)
REM ========================================
echo.
echo 检查 pywin32 (Windows 专用)...
%PYTHON_CMD% -c "import win32api" >nul 2>&1
if errorlevel 1 (
    echo    pywin32 未安装，正在安装...
    %PYTHON_CMD% -m pip install pywin32>=306 %PIP_MIRROR%
    if errorlevel 1 (
        echo    [失败] pywin32 安装失败
        echo [pywin32] 安装失败 >> "%REPORT_FILE%"
        set /a FAIL_COUNT+=1
    ) else (
        echo    [OK] pywin32 已安装
        echo [pywin32] 已安装 >> "%REPORT_FILE%"
        set /a OK_COUNT+=1
    )
) else (
    echo    [OK] pywin32 已存在
    echo [pywin32] 已存在 >> "%REPORT_FILE%"
)
echo. >> "%REPORT_FILE%"

REM ========================================
REM  生成报告
REM ========================================
echo. >> "%REPORT_FILE%"
echo ======================================== >> "%REPORT_FILE%"
echo   安装统计 >> "%REPORT_FILE%"
echo ======================================== >> "%REPORT_FILE%"
echo  已安装/已存在:  %OK_COUNT% 个 >> "%REPORT_FILE%"
echo  新安装成功:    %MISS_COUNT% 个 >> "%REPORT_FILE%"
echo  安装失败:      %FAIL_COUNT% 个 >> "%REPORT_FILE%"
echo  跳过(可选):    %SKIP_COUNT% 个 >> "%REPORT_FILE%"
echo ======================================== >> "%REPORT_FILE%"

REM ========================================
REM  STEP 7: 最终核对报告
REM ========================================
echo.
echo ========================================
echo   最终核对 — 验证所有关键依赖
echo ========================================
echo.

set CHECK_OK=0
set CHECK_FAIL=0

echo [核对清单] >> "%REPORT_FILE%"
echo ======================================== >> "%REPORT_FILE%"

REM Core dependency check
for %%P in (yaml requests edge_tts websocket_server websockets numpy PIL soundfile jieba transformers peft accelerate pytorch_lightning matplotlib torch) do (
    %PYTHON_CMD% -c "import %%P" >nul 2>&1
    if not errorlevel 1 (
        echo    [OK] %%P
        echo    [OK] %%P >> "%REPORT_FILE%"
        set /a CHECK_OK+=1
    ) else (
        echo    [!!] %%P  - MISSING!
        echo    [!!] %%P - MISSING >> "%REPORT_FILE%"
        set /a CHECK_FAIL+=1
    )
)

REM CUDA check
%PYTHON_CMD% -c "import torch; assert torch.cuda.is_available()" >nul 2>&1
if not errorlevel 1 (
    echo    [OK] CUDA available
    echo    [OK] CUDA available >> "%REPORT_FILE%"
    set /a CHECK_OK+=1
) else (
    echo    [--] CUDA not available (GPU inference disabled)
    echo    [--] CUDA not available >> "%REPORT_FILE%"
    set /a CHECK_FAIL+=1
)

echo. >> "%REPORT_FILE%"
echo 核对结果: %CHECK_OK% 通过, %CHECK_FAIL% 失败 >> "%REPORT_FILE%"

echo.
echo  ======================================================
echo   Install complete!
echo.
echo   Existing:    %OK_COUNT%
echo   New install: %MISS_COUNT%
echo   Failed:      %FAIL_COUNT%
echo   Skipped:     %SKIP_COUNT%
echo.
echo   Verification: [OK] %CHECK_OK% passed  [!!] %CHECK_FAIL% failed
echo.
echo   Report saved to: install_report.txt
echo  ======================================================
echo.

if "%CHECK_FAIL%"=="0" (
    echo  All key dependencies installed! Next steps:
    echo    scripts\download_models.bat  - Download model files
    echo    scripts\go.bat               - Start AI VTuber
) else (
    echo  [!!] %CHECK_FAIL% check(s) failed. See [!!] marks above.
    echo    Some features may not work, but core should be fine.
)
echo.
pause
exit /b 0


REM ========================================
REM  安装函数: install_pkg
REM  参数: %1=import名 %2=pip包名 %3=分类 %4=必须性
REM ========================================
:install_pkg
set "PKG_IMPORT=%~1"
set "PKG_PIP=%~2"
set "PKG_CATEGORY=%~3"
set "PKG_LEVEL=%~4"

set /a TOTAL+=1

REM 检查包是否已安装
%PYTHON_CMD% -c "import %PKG_IMPORT%" >nul 2>&1
if not errorlevel 1 (
    REM 已安装，获取版本号
    for /f "tokens=*" %%v in ('%PYTHON_CMD% -c "import %PKG_IMPORT%; print(getattr(%PKG_IMPORT%, '__version__', 'unknown'))" 2^>nul') do set PKG_VER=%%v
    echo    [OK]   %PKG_PIP%  (%PKG_VER%)
    echo   [已存在] %PKG_PIP% - %PKG_VER% >> "%REPORT_FILE%"
    set /a OK_COUNT+=1
    goto :eof
)

REM 未安装，开始安装
echo    [安装] %PKG_PIP%  (%PKG_CATEGORY%, %PKG_LEVEL%)...

REM 第一次尝试：清华镜像
%PYTHON_CMD% -m pip install %PKG_PIP% %PIP_MIRROR% >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%v in ('%PYTHON_CMD% -c "import %PKG_IMPORT%; print(getattr(%PKG_IMPORT%, '__version__', 'unknown'))" 2^>nul') do set PKG_VER=%%v
    echo           [OK] %PKG_PIP% 已安装 (%PKG_VER%, 清华镜像)
    echo   [新安装] %PKG_PIP% - %PKG_VER% (清华镜像) >> "%REPORT_FILE%"
    set /a MISS_COUNT+=1
    goto :eof
)

REM 第二次尝试：默认 PyPI
%PYTHON_CMD% -m pip install %PKG_PIP% >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%v in ('%PYTHON_CMD% -c "import %PKG_IMPORT%; print(getattr(%PKG_IMPORT%, '__version__', 'unknown'))" 2^>nul') do set PKG_VER=%%v
    echo           [OK] %PKG_PIP% 已安装 (%PKG_VER%, PyPI)
    echo   [新安装] %PKG_PIP% - %PKG_VER% (PyPI) >> "%REPORT_FILE%"
    set /a MISS_COUNT+=1
    goto :eof
)

REM 安装失败
if "%PKG_LEVEL%"=="required" (
    echo           [失败] %PKG_PIP% 安装失败！(必需依赖)
    echo   [失败-必需] %PKG_PIP% - 清华镜像和PyPI均安装失败 >> "%REPORT_FILE%"
    set /a FAIL_COUNT+=1
) else if "%PKG_LEVEL%"=="recommended" (
    echo           [失败] %PKG_PIP% 安装失败 (推荐，部分功能不可用)
    echo   [失败-推荐] %PKG_PIP% - 清华镜像和PyPI均安装失败 >> "%REPORT_FILE%"
    set /a FAIL_COUNT+=1
) else (
    echo           [跳过] %PKG_PIP% 安装失败 (可选，不影响核心功能)
    echo   [跳过-可选] %PKG_PIP% - 安装失败，不影响核心功能 >> "%REPORT_FILE%"
    set /a SKIP_COUNT+=1
)

goto :eof
