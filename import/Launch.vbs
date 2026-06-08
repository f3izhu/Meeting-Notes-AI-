Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Resolve absolute path of current directory
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)
venvPythonw = currentDir & "\.venv\Scripts\pythonw.exe"
launchScript = currentDir & "\launch.pyw"

If fso.FileExists(venvPythonw) Then
    ' Run silently (0 hides the window)
    WshShell.Run """" & venvPythonw & """ """ & launchScript & """", 0, False
Else
    WshShell.Run "pythonw.exe """ & launchScript & """", 0, False
End If
