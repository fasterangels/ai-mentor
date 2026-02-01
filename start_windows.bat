@echo off
echo ============================================
echo   AI Mentor - Starting Application
echo ============================================
echo.

REM Check if Ollama is running
echo [1/5] Checking Ollama status...
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -Method GET -TimeoutSec 5 -UseBasicParsing; if ($response.StatusCode -eq 200) { Write-Host '  Ollama is running' -ForegroundColor Green; exit 0 } else { Write-Host '  Ollama not responding' -ForegroundColor Yellow; exit 1 } } catch { Write-Host '  Ollama not running, starting...' -ForegroundColor Yellow; Start-Process 'ollama' 'serve' -WindowStyle Hidden; Start-Sleep -Seconds 3; exit 0 }"

if errorlevel 1 (
    echo   Starting Ollama...
    start /B ollama serve
    timeout /t 3 /nobreak >nul
)

echo.
echo [2/5] Warming up AI model...
powershell -Command "try { $body = @{ model = 'llama3:8b'; prompt = 'Hello'; stream = $false; options = @{ num_predict = 10 } } | ConvertTo-Json; $response = Invoke-RestMethod -Uri 'http://localhost:11434/api/generate' -Method POST -Body $body -ContentType 'application/json' -TimeoutSec 30; Write-Host '  Model warmed up successfully' -ForegroundColor Green } catch { Write-Host '  Warm-up skipped (model will load on first request)' -ForegroundColor Yellow }"

echo.
echo [3/5] Starting Backend (FastAPI)...
start "AI Mentor Backend" cmd /k "cd /d %~dp0backend && uvicorn main:app --reload"
timeout /t 3 /nobreak >nul

echo.
echo [4/5] Starting Frontend (React)...
start "AI Mentor Frontend" cmd /k "cd /d %~dp0app\frontend && pnpm run dev"
timeout /t 5 /nobreak >nul

echo.
echo [5/5] Opening browser...
timeout /t 3 /nobreak >nul
start http://localhost:3000

echo.
echo ============================================
echo   AI Mentor is now running!
echo ============================================
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo   
echo   Close this window or press Ctrl+C to stop
echo ============================================
echo.

pause