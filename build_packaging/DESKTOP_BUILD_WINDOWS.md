# Build Windows Desktop App (Tauri + Sidecar Backend)

This document describes how to produce the **Windows desktop application**: a single window (Tauri) that bundles the FastAPI backend as a sidecar EXE. No browser, no console windows for the end user.

## Prerequisites

Install the following on Windows 10/11:

| Tool | Purpose |
|------|--------|
| **Node.js** (LTS) | Frontend build (Vite), Tauri CLI |
| **npm** | Comes with Node; used for `npm install` and `npm run build` |
| **Rust toolchain** | Tauri build (install from https://rustup.rs) |
| **Python 3.10+** | Backend and PyInstaller |
| **PyInstaller** | Build backend into `ai-mentor-backend.exe` |

### Quick checks

```cmd
node -v
npm -v
rustc --version
cargo --version
python --version
pip show pyinstaller
```

If any command is missing, install that tool before building.

### Python / PyInstaller

From the **repository root** (folder that contains `backend` and `app`):

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r backend\requirements.txt
pip install pyinstaller
```

## How to build the desktop app

### One-click build (recommended)

From the repo root, run:

```cmd
tooling\launchers\build_desktop_windows.bat
```

The script will:

1. Build the backend into `dist\ai-mentor-backend.exe` (PyInstaller, sidecar entrypoint).
2. Copy the EXE to `app\frontend\src-tauri\bin\ai-mentor-backend-x86_64-pc-windows-msvc.exe`.
3. Run `npm install` and `npm run build` in `app\frontend`.
4. Run `npx tauri build` (release build).

**TAURI_CONFIG guard:** The script clears the `TAURI_CONFIG` environment variable before the Tauri build so Tauri always uses `app/frontend/src-tauri/tauri.conf.json`. If `TAURI_CONFIG` is set (e.g. to another or empty file), Tauri would otherwise fail with "unable to parse JSON ... expected value at line 1 column 1". No manual steps are required when using the one-click script.

If you use a venv for Python, activate it **before** running the batch file:

```cmd
venv\Scripts\activate
tooling\launchers\build_desktop_windows.bat
```

### Manual build (same steps)

Run from the **repository root**:

```cmd
:: 1) Backend sidecar EXE
pyinstaller packaging\backend_sidecar\pyinstaller_sidecar.spec --noconfirm

:: 2) Copy into Tauri bin (required name for Windows x64)
mkdir app\frontend\src-tauri\bin 2>nul
copy /Y dist\ai-mentor-backend.exe app\frontend\src-tauri\bin\ai-mentor-backend-x86_64-pc-windows-msvc.exe

:: 3) Frontend
cd app\frontend
npm install
npm run build

:: 4) Tauri release
npx tauri build
```

## Where the output is

After a successful build:

| Output | Location |
|--------|----------|
| Backend EXE (intermediate) | `dist\ai-mentor-backend.exe` |
| Sidecar in Tauri | `app\frontend\src-tauri\bin\ai-mentor-backend-x86_64-pc-windows-msvc.exe` |
| Frontend dist | `app\frontend\dist` |
| **Installer / app** | `app\frontend\src-tauri\target\release\bundle\` |

Inside `bundle\` you will have:

- **msi\** — Windows Installer (`.msi`)
- **nsis\** — NSIS installer (`.exe`)

The end-user runs the installer or the portable EXE from one of these folders. The app opens as a **single desktop window** (no browser, no console). The backend runs automatically on `http://127.0.0.1:8000` and is started/stopped with the app.

## Troubleshooting

### "python" or "pyinstaller" not found

- Activate your venv: `venv\Scripts\activate`.
- Or install Python and add it to PATH, then: `pip install pyinstaller`.

### "Cannot find module" or PyInstaller build errors

- From repo root, run PyInstaller so that `backend` is on the path. The spec in `packaging\backend_sidecar\pyinstaller_sidecar.spec` assumes it is run from repo root.
- Ensure all backend deps are installed: `pip install -r backend\requirements.txt`.

### Port 8000 already in use

- The sidecar backend is fixed to port 8000. Close any other app using 8000 (e.g. another dev backend or a previous AI Mentor instance) before starting the desktop app.

### Tauri build fails: "Rust not found" / "cargo not found"

- Install the Rust toolchain: https://rustup.rs  
- Restart the terminal after installation.

### Tauri build fails: "unable to parse JSON Tauri config file ... expected value at line 1 column 1"

- **Cause:** `TAURI_CONFIG` is set and points to a different or invalid config file; Tauri uses it instead of `src-tauri/tauri.conf.json`.
- **Fix:** Use the one-click script `tooling\launchers\build_desktop_windows.bat` — it clears `TAURI_CONFIG` automatically before running Tauri. No manual PowerShell or cmd steps needed.
- If you build manually from `app\frontend`, run `set TAURI_CONFIG=` in the same cmd session before `npx tauri build`.

### Tauri build fails: "beforeBuildCommand" or npm/pnpm errors

- From `app\frontend`, run `npm install` and `npm run build` manually. If they succeed, run `npx tauri build` again.
- Ensure Node.js LTS is installed and `node -v` and `npm -v` work.

### Sidecar not found at runtime

- After PyInstaller, the EXE must be copied to `app\frontend\src-tauri\bin\` with the exact name: `ai-mentor-backend-x86_64-pc-windows-msvc.exe`. The one-click script does this; if you build manually, do not skip the copy step.

### App shows a console window

- The release build is built with the Windows GUI subsystem (see `app\frontend\src-tauri\src\main.rs`: `windows_subsystem = "windows"`). Do not run the app from `target\debug\`; use the built installer or the EXE from `target\release\bundle\`.

## Summary

- **One command:** `tooling\launchers\build_desktop_windows.bat` (with venv activated if you use one).
- **Result:** Installer and EXE under `app\frontend\src-tauri\target\release\bundle\` (msi and nsis).
- **End-user experience:** One desktop window; backend starts automatically on 127.0.0.1:8000; no browser, no console windows.
