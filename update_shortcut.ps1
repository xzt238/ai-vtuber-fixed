$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath("Desktop")
$ExePath = "C:\Users\x\Desktop\ai-vtuber-fixed\GuguGaga.exe"
$IcoPath = "C:\Users\x\Desktop\ai-vtuber-fixed\assets\gugugaga_logo.ico"

$ShortcutPath = "$Desktop\GuguGaga.lnk"
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = "C:\Users\x\Desktop\ai-vtuber-fixed"
$Shortcut.Description = "GuguGaga AI VTuber"
$Shortcut.IconLocation = "$IcoPath,0"
$Shortcut.Save()

Write-Host "Updated! Restart Windows Explorer to see new icon."
