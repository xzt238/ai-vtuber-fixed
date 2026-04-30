; ============================================================
; GuguGaga AI-VTuber NSIS 安装器
; ============================================================
; 使用方法:
;   1. 安装 NSIS: https://nsis.sourceforge.io/Download
;   2. 右键此文件 → "Compile NSIS Script"
;   或命令行: makensis installer.nsi
;
; 安装目录结构:
;   C:\Program Files\GuguGaga\
;   ├── GuguGaga.exe
;   ├── python\
;   ├── app\
;   ├── GPT-SoVITS\
;   ├── launcher\
;   │   └── splash.html
;   ├── docs\
;   └── uninstall.exe
; ============================================================

!define PRODUCT_NAME "GuguGaga AI-VTuber"
!define PRODUCT_VERSION "1.9.45"
!define PRODUCT_PUBLISHER "咕咕嘎嘎"
!define PRODUCT_WEB_SITE "https://github.com/gugugaga/ai-vtuber"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\GuguGaga.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

; ========== 现代界面设置 ==========
!include "MUI2.nsh"
!include "FileFunc.nsh"

; 压缩设置
SetCompressor /SOLID lzma
SetCompressorDictSize 64

; 安装器属性
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "GuguGaga-Setup-${PRODUCT_VERSION}.exe"
InstallDir "$PROGRAMFILES64\${PRODUCT_NAME}"
InstallDirRegKey HKLM "Software\${PRODUCT_NAME}" "InstallDir"
ShowInstDetails show
ShowUnInstDetails show
RequestExecutionLevel admin

; ========== 界面配置 ==========
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; 欢迎页
!insertmacro MUI_PAGE_WELCOME

; 许可协议页（可选）
; !insertmacro MUI_PAGE_LICENSE "LICENSE.txt"

; 安装目录选择页
!insertmacro MUI_PAGE_DIRECTORY

; 安装进程页
!insertmacro MUI_PAGE_INSTFILES

; 完成页
!define MUI_FINISHPAGE_RUN "$INSTDIR\GuguGaga.exe"
!define MUI_FINISHPAGE_RUN_TEXT "启动 GuguGaga AI-VTuber"
!insertmacro MUI_PAGE_FINISH

; 卸载页面
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; 语言
!insertmacro MUI_LANGUAGE "SimpChinese"

; ============================================================
; 安装段
; ============================================================
Section "!主程序" SEC01
    SetOutPath "$INSTDIR"
    SetOverwrite ifnewer

    ; ---- 启动器 EXE ----
    File "GuguGaga.exe"

    ; ---- 应用代码 ----
    SetOutPath "$INSTDIR\app"
    File /r "app\*.py"
    File /r "app\*.yaml"
    File /r "app\*.json"
    File /r "app\*.html"
    File /r "app\*.css"
    File /r "app\*.js"
    File /r "app\*.txt"

    ; ---- 应用子目录结构 ----
    ; ASR
    SetOutPath "$INSTDIR\app\asr"
    File /r "app\asr\*.py"

    ; TTS
    SetOutPath "$INSTDIR\app\tts"
    File /r "app\tts\*.py"

    ; LLM
    SetOutPath "$INSTDIR\app\llm"
    File /r "app\llm\*.py"

    ; Vision
    SetOutPath "$INSTDIR\app\vision"
    File /r "app\vision\*.py"

    ; Memory
    SetOutPath "$INSTDIR\app\memory"
    File /r "app\memory\*.py"

    ; Web
    SetOutPath "$INSTDIR\app\web"
    File /r "app\web\*.py"
    SetOutPath "$INSTDIR\app\web\static"
    File /r "app\web\static\*.*"

    ; Live2D
    SetOutPath "$INSTDIR\app\live2d"
    File /r "app\live2d\*.*"

    ; Voice
    SetOutPath "$INSTDIR\app\voice"
    File /r "app\voice\*.py"

    ; Trainer
    SetOutPath "$INSTDIR\app\trainer"
    File /r "app\trainer\*.py"

    ; Tools
    SetOutPath "$INSTDIR\app\tools"
    File /r "app\tools\*.py"

    ; Cache 目录（创建空目录）
    SetOutPath "$INSTDIR\app\cache"
    ; 写入 .gitkeep 保持空目录
    FileOpen $0 "$INSTDIR\app\cache\.gitkeep" w
    FileClose $0

    ; Logs 目录
    SetOutPath "$INSTDIR\app\logs"
    FileOpen $0 "$INSTDIR\app\logs\.gitkeep" w
    FileClose $0

    ; ---- 启动器资源 ----
    SetOutPath "$INSTDIR\launcher"
    File "launcher\splash.html"

    ; ---- 文档 ----
    SetOutPath "$INSTDIR\docs"
    File /r "docs\*.*"

    ; ---- GPT-SoVITS ----
    SetOutPath "$INSTDIR\GPT-SoVITS"
    File /r "GPT-SoVITS\*.py"
    File /r "GPT-SoVITS\*.txt"
    File /r "GPT-SoVITS\*.md"
    File /r "GPT-SoVITS\*.json"
    File /r "GPT-SoVITS\*.yaml"
    File /r "GPT-SoVITS\*.yml"

    ; GPT-SoVITS 核心代码
    SetOutPath "$INSTDIR\GPT-SoVITS\GPT_SoVITS"
    File /r /x "__pycache__" /x "*.pyc" /x "pretrained_models" /x "ckpt" "GPT-SoVITS\GPT_SoVITS\*.py"
    File /r /x "__pycache__" /x "*.pyc" "GPT-SoVITS\GPT_SoVITS\*.json"
    File /r /x "__pycache__" /x "*.pyc" "GPT-SoVITS\GPT_SoVITS\*.yaml"

    ; GPT-SoVITS text 目录（含 G2PW 模型）
    SetOutPath "$INSTDIR\GPT-SoVITS\GPT_SoVITS\text"
    File /r /x "__pycache__" /x "*.pyc" "GPT-SoVITS\GPT_SoVITS\text\*.*"

    ; GPT-SoVITS tools
    SetOutPath "$INSTDIR\GPT-SoVITS\tools"
    File /r /x "__pycache__" /x "*.pyc" /x "asr\models" /x "uvr5\uvr5_weights" /x "denoise-model" "GPT-SoVITS\tools\*.py"

    ; ---- 模型缓存目录（空） ----
    SetOutPath "$INSTDIR\models"
    FileOpen $0 "$INSTDIR\models\.gitkeep" w
    FileClose $0

    SetOutPath "$INSTDIR\.cache"
    FileOpen $0 "$INSTDIR\.cache\.gitkeep" w
    FileClose $0

    ; ---- 启动脚本（兼容旧方式） ----
    SetOutPath "$INSTDIR"
    File "go.bat"
    File "desktop.bat"
    File "install_deps.bat"
    File "setup_embedded_python.bat"

    ; ---- 创建运行时需要的空目录 ----
    SetOutPath "$INSTDIR\logs"
    FileOpen $0 "$INSTDIR\logs\.gitkeep" w
    FileClose $0

    SetOutPath "$INSTDIR\memory"
    FileOpen $0 "$INSTDIR\memory\.gitkeep" w
    FileClose $0

SectionEnd

; ============================================================
; 嵌入式 Python 段（可选）
; ============================================================
Section "嵌入式 Python 3.11.2" SEC02
    SetOutPath "$INSTDIR\python"
    
    ; 注意：如果 python/ 目录已预先准备好，直接打包
    ; 否则安装后会提示用户运行 setup_embedded_python.bat
    IfFileExists "$INSTDIR\python\python.exe" py_done py_missing
    
py_missing:
    ; 创建标记文件，首次启动时提示安装
    FileOpen $0 "$INSTDIR\python\.needs_setup" w
    FileWrite $0 "1"
    FileClose $0
    DetailPrint "嵌入式 Python 未包含，安装后请运行 setup_embedded_python.bat"
    
py_done:
    ; python/ 已包含
    DetailPrint "嵌入式 Python 已就绪"
SectionEnd

; ============================================================
; 快捷方式段
; ============================================================
Section "创建快捷方式" SEC03
    ; 桌面快捷方式
    CreateShortCut "$DESKTOP\GuguGaga AI-VTuber.lnk" "$INSTDIR\GuguGaga.exe" "" "$INSTDIR\GuguGaga.exe" 0
    
    ; 开始菜单
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\GuguGaga AI-VTuber.lnk" "$INSTDIR\GuguGaga.exe" "" "$INSTDIR\GuguGaga.exe" 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\浏览器模式.lnk" "$INSTDIR\go.bat" "" "" 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\安装依赖.lnk" "$INSTDIR\install_deps.bat" "" "" 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\卸载.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0
SectionEnd

; ============================================================
; 注册表和卸载信息
; ============================================================
Section -Post
    ; 写入注册表
    WriteUninstaller "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "Software\${PRODUCT_NAME}" "InstallDir" "$INSTDIR"
    WriteRegStr HKLM "Software\${PRODUCT_NAME}" "Version" "${PRODUCT_VERSION}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\GuguGaga.exe"
    
    ; 计算安装大小
    ${GetSize} "$INSTDIR" "/S=0K" $0
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "EstimatedSize" "$0"
SectionEnd

; ============================================================
; 卸载段
; ============================================================
Section Uninstall
    ; 删除快捷方式
    Delete "$DESKTOP\GuguGaga AI-VTuber.lnk"
    RMDir /r "$SMPROGRAMS\${PRODUCT_NAME}"
    
    ; 删除注册表
    DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
    DeleteRegKey HKLM "Software\${PRODUCT_NAME}"
    DeleteRegValue HKLM "${PRODUCT_DIR_REGKEY}" ""
    
    ; 删除安装文件（保留用户数据）
    Delete "$INSTDIR\GuguGaga.exe"
    Delete "$INSTDIR\go.bat"
    Delete "$INSTDIR\desktop.bat"
    Delete "$INSTDIR\install_deps.bat"
    Delete "$INSTDIR\setup_embedded_python.bat"
    Delete "$INSTDIR\build_launcher.bat"
    Delete "$INSTDIR\uninstall.exe"
    
    ; 删除应用代码
    RMDir /r "$INSTDIR\app"
    RMDir /r "$INSTDIR\launcher"
    RMDir /r "$INSTDIR\docs"
    RMDir /r "$INSTDIR\GPT-SoVITS"
    RMDir /r "$INSTDIR\python"
    RMDir /r "$INSTDIR\models"
    RMDir /r "$INSTDIR\logs"
    RMDir /r "$INSTDIR\memory"
    RMDir /r "$INSTDIR\.cache"
    
    ; 尝试删除安装目录
    RMDir "$INSTDIR"
    
    SetAutoClose true
SectionEnd

; ============================================================
; 安装前检查
; ============================================================
Function .onInit
    ; 检查是否已安装
    ReadRegStr $0 HKLM "Software\${PRODUCT_NAME}" "InstallDir"
    StrCmp $0 "" new_install
    
    MessageBox MB_YESNO|MB_ICONQUESTION \
        "检测到已安装 ${PRODUCT_NAME}，路径: $0$\n$\n是否卸载旧版本后继续安装？" \
        /SD IDYES IDYES uninst_old IDNO abort_install
    
uninst_old:
    ExecWait '"$0\uninstall.exe" /S _?=$0'
    Delete "$0\uninstall.exe"
    RMDir "$0"
    Goto new_install
    
abort_install:
    Abort
    
new_install:
FunctionEnd

; ============================================================
; 安装完成回调
; ============================================================
Function .onInstSuccess
    ; 检查是否需要安装嵌入式 Python
    IfFileExists "$INSTDIR\python\python.exe" py_ok py_missing
    
py_missing:
    MessageBox MB_YESNO|MB_ICONINFORMATION \
        "嵌入式 Python 尚未安装。$\n$\n是否现在运行 setup_embedded_python.bat 安装 Python 3.11.2 及依赖？$\n$\n（需要网络连接，安装时间约 20-60 分钟）" \
        /SD IDNO IDYES run_setup
    Goto py_ok
    
run_setup:
    Exec '"$INSTDIR\setup_embedded_python.bat"'
    
py_ok:
FunctionEnd
