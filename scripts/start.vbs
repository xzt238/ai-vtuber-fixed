Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' 获取脚本所在目录的父目录（scripts/ -> 项目根）
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
projectDir = fso.GetParentFolderName(scriptDir)

' 设置环境变量
Set env = WshShell.Environment("PROCESS")
env("HF_HOME") = projectDir & "\.cache\huggingface"
env("HF_ENDPOINT") = "https://hf-mirror.com"
env("PYTHONIOENCODING") = "utf-8"

' 找到 pythonw.exe
pythonw = projectDir & "\python\pythonw.exe"

If fso.FileExists(pythonw) Then
    ' 无窗口启动（第二个参数 0 = 隐藏窗口）
    WshShell.Run """" & pythonw & """ """ & projectDir & "\native\main.py""", 0, False
Else
    MsgBox "Python not found! Please run scripts\install_deps.bat first.", 48, "GuguGaga"
End If
