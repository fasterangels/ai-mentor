@echo off
setlocal

REM Build the backend sidecar EXE with PyInstaller.
REM Run from the repository root so the spec paths are correct.

echo [backend] Building ai-mentor-backend.exe via PyInstaller...
py -3.11 -m PyInstaller packaging\backend_sidecar\pyinstaller_sidecar.spec --noconfirm
if errorlevel 1 (
  echo [backend] PyInstaller build failed.
  exit /b 1
)

REM Ensure the Tauri bin folder exists.
if not exist app\frontend\src-tauri\bin (
  mkdir app\frontend\src-tauri\bin 2>nul
)

REM Copy the PyInstaller output into the Tauri bin folder with the expected names.
set "SRC=dist\ai-mentor-backend.exe"
set "BIN=app\frontend\src-tauri\bin"

if not exist "%SRC%" (
  echo [backend] Expected PyInstaller output not found at "%SRC%".
  exit /b 1
)

copy /Y "%SRC%" "%BIN%\ai-mentor-backend.exe" >nul
copy /Y "%SRC%" "%BIN%\ai-mentor-backend-x86_64-pc-windows-msvc.exe" >nul

echo [backend] Backend EXE built and copied to %BIN%.
exit /b 0

