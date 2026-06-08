$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath('Desktop')
$ShortcutPath = Join-Path $DesktopPath "Meeting Notes AI.lnk"

# Determine path names
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RootDir = Split-Path -Parent $ScriptDir

# Resolve Pythonw path from virtual environment, fallback to system pythonw.exe
$LaunchPyw = Join-Path $RootDir "launch.pyw"
$IconPath = Join-Path $RootDir "assets\MeetingNotesAI.ico"

$Pythonw = Join-Path $RootDir ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $Pythonw)) {
    $Pythonw = "pythonw.exe"
}

# Build the shell link
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $Pythonw
$Shortcut.Arguments = "`"$LaunchPyw`""
$Shortcut.WorkingDirectory = $RootDir
$Shortcut.Description = "Launch Local Meeting Notes AI (SAC Bypass)"
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = $IconPath
} else {
    $Shortcut.IconLocation = "shell32.dll, 269"
}
$Shortcut.Save()

Write-Host "Desktop shortcut created at: $ShortcutPath"
Write-Host "  Target: $($Shortcut.TargetPath)"
Write-Host "  Arguments: $($Shortcut.Arguments)"
Write-Host "  Working Directory: $RootDir"
