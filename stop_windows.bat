@echo off
echo ========================================
echo AI Mentor - Stopping Application
echo ========================================
echo.

REM Stop Frontend (Node.js processes on port 3000)
echo Stopping Frontend...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":3000" ^| find "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Stop Backend (Python/Uvicorn processes on port 8000)
echo Stopping Backend...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Note: We don't stop Ollama as it might be used by other applications
echo.
echo Note: Ollama is still running. Stop it manually if needed.
echo.

echo ========================================
echo AI Mentor has been stopped.
echo ========================================
echo.
pause