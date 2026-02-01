; AI Mentor: per-user Scheduled Task (no admin/UAC). Backend runs via AI_Mentor_Backend task at logon.
; POSTINSTALL: create dirs, copy backend exe + launcher, create task with schtasks /Create (NO /XML), run task.
; PREUNINSTALL: end task, delete task, remove service folder.
!macro NSIS_HOOK_PREINSTALL
!macroend

!macro NSIS_HOOK_POSTINSTALL
  CreateDirectory "$LOCALAPPDATA\AI_Mentor"
  CreateDirectory "$LOCALAPPDATA\AI_Mentor\service"
  CreateDirectory "$LOCALAPPDATA\AI_Mentor\logs"
  ; Copy backend exe
  IfFileExists "$INSTDIR\resources\ai-mentor-backend.exe" 0 +2
  CopyFiles /SILENT "$INSTDIR\resources\ai-mentor-backend.exe" "$LOCALAPPDATA\AI_Mentor\service\"
  IfFileExists "$INSTDIR\bin\ai-mentor-backend.exe" 0 +2
  CopyFiles /SILENT "$INSTDIR\bin\ai-mentor-backend.exe" "$LOCALAPPDATA\AI_Mentor\service\"
  IfFileExists "$INSTDIR\ai-mentor-backend.exe" 0 +2
  CopyFiles /SILENT "$INSTDIR\ai-mentor-backend.exe" "$LOCALAPPDATA\AI_Mentor\service\"
  ; Copy launcher only (no XML)
  IfFileExists "$INSTDIR\resources\launch_backend.cmd" 0 +2
  CopyFiles /SILENT "$INSTDIR\resources\launch_backend.cmd" "$LOCALAPPDATA\AI_Mentor\service\"
  IfFileExists "$INSTDIR\bin\launch_backend.cmd" 0 +2
  CopyFiles /SILENT "$INSTDIR\bin\launch_backend.cmd" "$LOCALAPPDATA\AI_Mentor\service\"
  ; Delete any old task first (idempotent; ignore errors)
  ExecWait '"$SYSDIR\schtasks.exe" /Delete /TN "AI_Mentor_Backend" /F' $0
  ; Create per-user task WITHOUT /XML: cmd.exe /c "path\to\launch_backend.cmd"
  ; /TR must be: "cmd.exe" /c "fullpath\to\launch_backend.cmd"
  ExecWait '"$SYSDIR\schtasks.exe" /Create /F /SC ONLOGON /TN "AI_Mentor_Backend" /TR "$\"$SYSDIR\cmd.exe$\" /c $\"$LOCALAPPDATA\AI_Mentor\service\launch_backend.cmd$\""' $0
  StrCmp $0 0 +5 0
  DetailPrint "Task create failed with code $0"
  MessageBox MB_ICONSTOP "Failed to register AI Mentor Backend task (code $0)."
  SetErrorLevel $0
  Abort
  ; Run task immediately
  ExecWait '"$SYSDIR\schtasks.exe" /Run /TN "AI_Mentor_Backend"' $0
  StrCmp $0 0 +5 0
  DetailPrint "Task run failed with code $0"
  MessageBox MB_ICONSTOP "Failed to start AI Mentor Backend task (code $0)."
  SetErrorLevel $0
  Abort
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  ExecWait '"$SYSDIR\schtasks.exe" /End /TN "AI_Mentor_Backend"' $0
  ExecWait '"$SYSDIR\schtasks.exe" /Delete /TN "AI_Mentor_Backend" /F' $0
  RMDir /r "$LOCALAPPDATA\AI_Mentor\service"
!macroend
