# Backend sidecar binary

Tauri bundles the backend EXE as a sidecar. On Windows, the binary must be named:

`ai-mentor-backend-x86_64-pc-windows-msvc.exe`

**One-click build (recommended):** from repo root run  
`tooling\launchers\build_desktop_windows.bat`  
It builds the sidecar, copies it here, and runs the Tauri build. See `packaging/DESKTOP_BUILD_WINDOWS.md`.

**Manual setup:**

1. Build the backend sidecar EXE (from repo root):
   ```
   pyinstaller packaging\backend_sidecar\pyinstaller_sidecar.spec --noconfirm
   ```
2. Copy the output into this folder with the correct name:
   ```
   copy dist\ai-mentor-backend.exe app\frontend\src-tauri\bin\ai-mentor-backend-x86_64-pc-windows-msvc.exe
   ```
3. From `app/frontend`: `npm run build` then `npx tauri build`.
