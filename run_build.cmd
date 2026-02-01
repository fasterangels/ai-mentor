@echo off
setlocal EnableDelayedExpansion
:: Single entrypoint: full build + [FINAL] installed-build test.
:: Switches to 8.3 short path so automation (cmd/Python) works without PowerShell encoding issues.
:: Usage: run from repo root (e.g. double-click or: run_build.cmd)

set "REPO=%~dp0"
set "REPO=%REPO:~0,-1%"
cd /d "%REPO%"
for %%I in ("%REPO%") do set "SHORT=%%~sI"
cd /d "!SHORT!"
python -m tooling.launchers.build_desktop_windows
exit /b %errorlevel%
