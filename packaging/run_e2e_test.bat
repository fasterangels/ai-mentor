@echo off
setlocal
cd /d "%~dp0\.."
python "%~dp0test_installed_task_end_to_end.py" --repo-root "%~dp0\.."
set RC=%ERRORLEVEL%
if %RC% neq 0 exit /b %RC%
echo.
echo TASK E2E TEST: PASS
exit /b 0
