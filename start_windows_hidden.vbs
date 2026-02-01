' AI Mentor - Hidden Launcher for Windows 11
' This script starts the application without showing console windows
' For debugging with visible console windows, use start_windows.bat instead

Set WshShell = CreateObject("WScript.Shell")

' Get the directory where this script is located
strScriptPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Change to the script directory
WshShell.CurrentDirectory = strScriptPath

' Run start_windows.bat hidden (0 = hidden window, False = don't wait)
WshShell.Run "cmd /c start_windows.bat", 0, False

' Show a brief notification (optional - comment out if not desired)
' WScript.Sleep 1000
' WshShell.Popup "AI Mentor is starting in the background..." & vbCrLf & "The browser will open shortly.", 3, "AI Mentor", 64