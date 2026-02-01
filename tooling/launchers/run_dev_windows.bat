@echo off
setlocal EnableDelayedExpansion
REM One-click DEV launcher: backend + frontend + browser
REM Script lives in tooling/launchers/; repo root is two levels up.

pushd "%~dp0..\.."
set "REPO_ROOT=%CD%"
popd

echo.
echo [AI Mentor DEV] Repo root: %REPO_ROOT%
echo.

REM Backend: new terminal, uvicorn on 127.0.0.1:8000
echo [AI Mentor DEV] Starting backend (uvicorn 127.0.0.1:8000)...
start "AI Mentor - Backend" cmd /k "cd /d "%REPO_ROOT%\backend" && echo Backend: %REPO_ROOT%\backend && echo. && .\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000"
if errorlevel 1 (
  echo [AI Mentor DEV] WARNING: Failed to start backend window. Check that backend\venv exists and uvicorn is installed.
)

REM Frontend: new terminal, vite on port 3000
echo [AI Mentor DEV] Starting frontend (Vite port 3000)...
start "AI Mentor - Frontend" cmd /k "cd /d "%REPO_ROOT%\app\frontend" && echo Frontend: %REPO_ROOT%\app\frontend && echo. && npm run dev"
if errorlevel 1 (
  echo [AI Mentor DEV] WARNING: Failed to start frontend window. Check that app\frontend exists and npm deps are installed.
)

REM Wait for servers to listen
echo [AI Mentor DEV] Waiting 3 seconds for servers to start...
timeout /t 3 /nobreak > nul

REM Open browser
echo [AI Mentor DEV] Opening http://localhost:3000
start "" "http://localhost:3000"

echo.
echo [AI Mentor DEV] Done. Backend and frontend run in separate windows.
echo   - If browser shows "connection refused": wait a few more seconds or check the Frontend window.
echo   - If Analyze fails: ensure the Backend window is running and shows "Uvicorn running on http://127.0.0.1:8000".
echo   - To stop: close the two server windows or press CTRL+C in each.
echo.
pause
