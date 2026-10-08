Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonwPath = currDir & "\.venv\Scripts\pythonw.exe"
runPyPath = currDir & "\run_server.py"

WshShell.CurrentDirectory = currDir
WshShell.Run """" & pythonwPath & """ """ & runPyPath & """", 0, False
