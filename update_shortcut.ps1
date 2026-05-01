$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath("Desktop")
$ExePath = "C:\Users\x\Desktop\ai-vtuber-fixed\GuguGaga.exe"
$IcoPath = "C:\Users\x\Desktop\ai-vtuber-fixed\assets\gugugaga_logo.ico"

# Check if shortcut exists
$ShortcutPath = "$Desktop\GuguGaga.lnk"
if (Test-Path $ShortcutPath) {
    # Update existing shortcut
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $ExePath
    $Shortcut.WorkingDirectory = "C:\Users\x\Desktop\ai-vtuber-fixed"
    $Shortcut.Description = "GuguGaga AI VTuber"
    $Shortcut.IconLocation = "$IcoPath,0"
    $Shortcut.Save()
    Write-Host "Updated shortcut with new penguin icon!"
} else {
    # Create new shortcut
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $ExePath
    $Shortcut.WorkingDirectory = "C:\Users\x\Desktop\ai-vtuber-fixed"
    $Shortcut.Description = "GuguGaga AI VTuber"
    $Shortcut.IconLocation = "$IcoPath,0"
    $Shortcut.Save()
    Write-Host "Created new shortcut with penguin icon!"
}

Write-Host ""
Write-Host "Now refresh desktop icons:"
Write-Host "  1. Press Ctrl+Shift+Esc to open Task Manager"
Write-Host "  2. Find 'Windows Explorer' in Processes tab"
Write-Host "  3. Right-click and select 'Restart'"
