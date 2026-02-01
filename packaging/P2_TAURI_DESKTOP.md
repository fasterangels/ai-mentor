# P2 — Tauri Desktop Shell + Backend Sidecar

Windows desktop app (Tauri) that shows the React frontend, starts the backend EXE as a hidden sidecar, and uses the port from `backend_port.json`.

## Prerequisites

- **Rust** (rustup) and **Node/pnpm** (for frontend)
- **Backend EXE** built first (see [BUILD_WINDOWS_BACKEND.md](BUILD_WINDOWS_BACKEND.md))
- **Icons** in `app/frontend/src-tauri/icons/` (e.g. run `pnpm tauri icon path/to/icon.png` from `app/frontend` to generate, or add `icon.ico` manually)

## Build steps

### 1. Build the backend EXE (if not done)

From **repo root**:

```cmd
pyinstaller packaging\pyinstaller_backend.spec
```

Output: `dist\ai-mentor-backend.exe`

### 2. Copy backend EXE into Tauri sidecar bin

From **repo root**:

```cmd
mkdir app\frontend\src-tauri\bin 2>nul
copy dist\ai-mentor-backend.exe app\frontend\src-tauri\bin\ai-mentor-backend-x86_64-pc-windows-msvc.exe
```

(Tauri expects the sidecar binary name with target triple on Windows.)

### 3. Install frontend deps and build Tauri app

From **app/frontend**:

```cmd
pnpm install
pnpm tauri build
```

### 4. Where the desktop app ends up

- **Output:** `app/frontend/src-tauri/target/release/` — you get a `.exe` and/or an installer depending on Tauri bundle config.
- Or run in dev: `pnpm tauri dev` (starts Vite dev server and opens the Tauri window).

## Runtime behavior

- **Double-click** the desktop EXE → opens a native window (no PowerShell).
- **Backend** starts as a **hidden sidecar** process (no console).
- **Port:** Backend writes `%LOCALAPPDATA%\AI_Mentor\runtime\backend_port.json`; the app reads it and calls `get_backend_base_url` so the UI uses the correct base URL.
- **Health:** The Rust side polls `/health` (up to ~10s) after spawning the sidecar; the frontend uses the base URL from the invoke command.
- **Close app** → backend process is terminated.
- **Single instance:** If another instance is already running (lock file present), the new process exits. (Optional enhancement: focus the existing window via a small listener.)

## Port file and logs

- **Port file:** `%LOCALAPPDATA%\AI_Mentor\runtime\backend_port.json` — `port`, `base_url`, `written_at`.
- **Backend logs:** `%LOCALAPPDATA%\AI_Mentor\logs\backend.log`.

## Frontend base URL

- **Desktop (Tauri):** The app calls `invoke('get_backend_base_url')` and uses the returned URL (from `backend_port.json`).
- **Browser / dev:** Uses `http://127.0.0.1:8000` (unchanged).

## Notes

- Backend logic is unchanged (P1 only); no cloud or external services.
- Sidecar is bundled via `externalBin`; the EXE must be named `ai-mentor-backend-x86_64-pc-windows-msvc.exe` in `src-tauri/bin/` for the Windows build.
