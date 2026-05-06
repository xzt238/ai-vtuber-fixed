; ============================================================
;  GuguGaga AI-VTuber v2.0 — Inno Setup 安装脚本
;
;  使用方法:
;    1. 先运行 build.bat 生成 dist\GuguGagaNative\
;    2. 用 Inno Setup Compiler 打开此文件并编译
;
;  要求: Inno Setup 6.x (https://jrsoftware.org/isdl.php)
; ============================================================

#define AppName "GuguGaga AI-VTuber"
#define AppVersion "2.0.0"
#define AppPublisher "GuguGaga"
#define AppURL "https://github.com/xzt238/ai-vtuber-fixed"
#define AppExeName "GuguGagaNative.exe"
#define AppCopyright "Copyright (C) 2026 GuguGaga"

[Setup]
; 基本信息
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppCopyright={#AppCopyright}

; 安装路径
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}

; 输出
OutputDir=installer_output
OutputBaseFilename=GuguGagaNative_Setup_{#AppVersion}
SetupIconFile=gugu_native\resources\app.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; 权限
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline

; 架构
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; 窗口
UninstallDisplayIcon={app}\{#AppExeName}
DisableProgramGroupPage=yes

; 许可协议（可选）
; LicenseFile=LICENSE.txt

; 版本信息
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Setup
VersionInfoCopyright={#AppCopyright}

; 安装界面设置
SetupScreenWidth=600
SetupScreenHeight=400

; 其他
CloseApplications=force
RestartApplications=no

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "开机自启动"; GroupDescription: "附加选项:"; Flags: unchecked

[Files]
; 主程序和所有依赖（从 PyInstaller 输出目录复制）
Source: "dist\GuguGagaNative\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\卸载 {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; 开机自启（注册表方式，与 AutoStartManager 一致）
Root: HKCU; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "GuguGagaAI-VTuber"; ValueData: """{app}\{#AppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
// 检查是否已安装
function InitializeSetup(): Boolean;
var
  OldVersion: String;
  UninstallerPath: String;
begin
  // 检查旧版本
  if RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}\',
    'UninstallString', UninstallerPath) then
  begin
    if MsgBox('检测到已安装的版本，是否先卸载？', mbConfirmation, MB_YESNO) = IDYES then
    begin
      UninstallerPath := RemoveQuotes(UninstallerPath);
      Exec(UninstallerPath, '/SILENT /NORESTART', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    end;
  end;
  Result := True;
end;
