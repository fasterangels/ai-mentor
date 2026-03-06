@echo off
setlocal enabledelayedexpansion
set "BASE=%LOCALAPPDATA%\AI_Mentor"
set "SVC=%BASE%\service"
set "LOG_DIR=%BASE%\logs"
set "LOG_FILE=%LOG_DIR%\backend.log"
set "EXE=%SVC%\ai-mentor-backend.exe"
set AI_MENTOR_BASE_DIR=%BASE%
set AI_MENTOR_PORT=8000

if not exist "%BASE%" mkdir "%BASE%"
if not exist "%SVC%" mkdir "%SVC%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: ISO-like timestamp via wmic (cmd only)
set "ISOT="
for /f "skip=1 delims=" %%a in ('wmic os get localdatetime 2^>nul') do set "DTTM=%%a"
if defined DTTM set "ISOT=%DTTM:~0,4%-%DTTM:~4,2%-%DTTM:~6,2%T%DTTM:~8,2%:%DTTM:~10,2%:%DTTM:~12,2%"
if not defined ISOT set "ISOT=%date% %time%"

echo TASK_START at=%ISOT% exe_path=%EXE% base_dir=%BASE% port=8000 >> "%LOG_FILE%"

:: If port 8000 already LISTENING -> backend already running; success
netstat -an | findstr "LISTENING" | findstr ":8000" >nul 2>&1
if %errorlevel% equ 0 (
  echo PORT_IN_USE >> "%LOG_FILE%"
  exit /b 0
)

:: Start backend in background, append stdout+stderr to log
start /B "" "%EXE%" >> "%LOG_FILE%" 2>&1

:: Wait up to 30s for health 200 (curl.exe; retry every 1s)
set /a count=0
:health_loop
if !count! geq 30 goto health_fail
for /f "delims=" %%c in ('curl.exe -s -o NUL -w "%%{http_code}" -m 1 http://127.0.0.1:8000/health 2^>nul') do set "HTTP=%%c"
if "!HTTP!"=="200" (
  echo HEALTH_OK >> "%LOG_FILE%"
  exit /b 0
)
timeout /t 1 /nobreak >nul
set /a count+=1
goto health_loop

:health_fail
echo TASK_FAIL_HEALTH >> "%LOG_FILE%"
exit /b 2
