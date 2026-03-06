@echo off
:: Phase E proof: run AFTER launching the desktop app (backend must be listening on 127.0.0.1:8000)
echo A) netstat -ano ^| findstr :8000
netstat -ano | findstr :8000
echo.
echo B) curl.exe -i http://127.0.0.1:8000/health
curl.exe -i http://127.0.0.1:8000/health
echo.
echo C) Preflight OPTIONS
curl.exe -i -X OPTIONS "http://127.0.0.1:8000/api/v1/analyze" -H "Origin: http://tauri.localhost" -H "Access-Control-Request-Method: POST" -H "Access-Control-Request-Headers: content-type"
echo.
echo D) POST
curl.exe -i -X POST "http://127.0.0.1:8000/api/v1/analyze" -H "Origin: http://tauri.localhost" -H "Content-Type: application/json" --data "{\"home_team\":\"PAOK\",\"away_team\":\"AEK\"}"
