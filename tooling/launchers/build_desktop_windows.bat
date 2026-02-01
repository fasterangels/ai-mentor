@echo off
setlocal
:: One-click Windows desktop build (Unicode-safe). Calls Python driver so Greek paths work.
:: Run from anywhere; script switches to repo root then runs Python.
:: If Cursor/IDE breaks on Greek path: run from cmd with 8.3 path, e.g. cd C:\AI_Mentor\AIWIND~1.2 then python -m tooling.launchers.build_desktop_windows

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%..\.."
cd /d "%REPO_ROOT%"
if errorlevel 1 (
  echo ERROR: Could not cd to repo root: %REPO_ROOT%
  exit /b 1
)

:: Run Python build driver (pathlib/__file__ = Unicode-safe; no brittle quoting)
python -m tooling.launchers.build_desktop_windows
set EXIT_CODE=%errorlevel%
endlocal
exit /b %EXIT_CODE%
