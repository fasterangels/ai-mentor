@echo off
:: CORS verification: run with backend already running on 127.0.0.1:8000
echo 1. Health:
curl.exe http://127.0.0.1:8000/health
echo.
echo.
echo 2. Preflight OPTIONS (must return 200/204 and Access-Control-Allow-Origin):
curl.exe -i -X OPTIONS "http://127.0.0.1:8000/api/v1/analyze" -H "Origin: http://tauri.localhost" -H "Access-Control-Request-Method: POST" -H "Access-Control-Request-Headers: content-type"
echo.
echo.
echo 3. POST:
curl.exe -i -X POST "http://127.0.0.1:8000/api/v1/analyze" -H "Origin: http://tauri.localhost" -H "Content-Type: application/json" --data "{\"home_team\":\"PAOK\",\"away_team\":\"AEK\"}"
