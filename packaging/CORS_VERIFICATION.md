# CORS / preflight verification

Use these commands to confirm the backend accepts preflight and POST from the frontend.

## 1) Start backend

```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

**Expected:**
- Server starts successfully
- Listening on http://127.0.0.1:8000

## 2) Preflight OPTIONS test

```powershell
curl.exe -i -X OPTIONS "http://127.0.0.1:8000/api/v1/analyze" ^
  -H "Origin: http://localhost:3000" ^
  -H "Access-Control-Request-Method: POST" ^
  -H "Access-Control-Request-Headers: content-type"
```

**Expected:**
- Status: **200** or **204**
- Response headers include:
  - `Access-Control-Allow-Origin: http://localhost:3000`
  - `Access-Control-Allow-Methods` (includes POST)
  - `Access-Control-Allow-Headers` (includes content-type)

## 3) POST request test

```powershell
curl.exe -i -X POST "http://127.0.0.1:8000/api/v1/analyze" ^
  -H "Origin: http://localhost:3000" ^
  -H "Content-Type: application/json" ^
  --data "{\"home_team\":\"PAOK\",\"away_team\":\"AEK\"}"
```

**Expected:**
- /api/v1/analyze is intentionally not supported (501). Use /pipeline/shadow/run.
- Status: **501 Not Implemented** with JSON body `{"error":{"code":"ANALYZE_ENDPOINT_NOT_SUPPORTED",...}}`
- No CORS or network errors

## 4) Browser test

1. Open **http://localhost:3000** or **http://127.0.0.1:3000**
2. Enter home/away teams
3. Click **Analyze**

**Expected:**
- Analysis result is rendered
- No "Failed to fetch" or "Backend not reachable" error
