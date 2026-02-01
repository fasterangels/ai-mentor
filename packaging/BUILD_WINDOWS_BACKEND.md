# Build Windows Backend EXE (no-console)

Build the AI Mentor backend as a single Windows executable that runs without a console window, writes logs to `%LOCALAPPDATA%\AI_Mentor\logs\`, and chooses a port in 8000..8010.

## Prerequisites

- Windows 10/11
- Python 3.10+ on PATH
- No network required (offline build)

## Exact build steps

Run all commands from the **repository root** (the folder that contains `backend` and `packaging`).

### 1. Create a virtual environment

```cmd
python -m venv venv
venv\Scripts\activate
```

### 2. Install backend requirements and PyInstaller

```cmd
pip install -r backend\requirements.txt
pip install pyinstaller
```

### 3. Run PyInstaller

```cmd
pyinstaller packaging\pyinstaller_backend.spec
```

### 4. Where the EXE ends up

- **Output:** `dist\ai-mentor-backend.exe`
- Single-file executable; no console window (`console=False` in the spec).

## Runtime behavior (when you run the EXE)

- **No console window** — the process runs in the background.
- **Port:** First free port in 8000..8010 (tested with a bind socket).
- **Port file:** `%LOCALAPPDATA%\AI_Mentor\runtime\backend_port.json`  
  Contents: `{ "port": <int>, "base_url": "http://127.0.0.1:<port>", "written_at": "<ISO>" }`.
- **Logs:** `%LOCALAPPDATA%\AI_Mentor\logs\backend.log`
- **Database (packaged only):** `%LOCALAPPDATA%\AI_Mentor\data\ai_mentor.sqlite`
- **Host:** `127.0.0.1` only (offline/local).

## Verify

1. Run `dist\ai-mentor-backend.exe`.
2. Open `%LOCALAPPDATA%\AI_Mentor\runtime\backend_port.json` and note `port` (e.g. 8000).
3. In a browser or with curl: `http://127.0.0.1:<port>/health` → `{"status":"ok"}`.
4. Check `%LOCALAPPDATA%\AI_Mentor\logs\backend.log` for startup lines.

## If port 8000 is busy

The entrypoint tries 8000, then 8001, … up to 8010. The first port that binds successfully is written to `backend_port.json`. No crash; the EXE picks another port.

## Notes

- **Port file location:** `%LOCALAPPDATA%\AI_Mentor\runtime\backend_port.json`
- **Log file location:** `%LOCALAPPDATA%\AI_Mentor\logs\backend.log`
- PyInstaller is **build-time only**; it is not required at runtime.
