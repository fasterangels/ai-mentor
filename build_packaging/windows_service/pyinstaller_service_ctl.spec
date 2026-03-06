# PyInstaller spec for AI Mentor service controller (install/start/stop/uninstall).
# Run from repo root: pyinstaller packaging/windows_service/pyinstaller_service_ctl.spec --noconfirm
# Output: dist/ai-mentor-service.exe (deploy to %LOCALAPPDATA%\AI_Mentor\service\)

# -*- mode: python ; coding: utf-8 -*-

import os

block_cwd = os.path.dirname(os.path.abspath(SPEC))
# packaging/windows_service -> go up twice to repo root
repo_root = os.path.dirname(os.path.dirname(block_cwd))
service_dir = os.path.join(repo_root, "packaging", "windows_service")
script = os.path.join(service_dir, "service_ctl.py")

a = Analysis(
    [script],
    pathex=[repo_root, service_dir],
    binaries=[],
    datas=[],
    hiddenimports=[
        "packaging.windows_service.ai_mentor_backend_service",
        "ai_mentor_backend_service",
        "win32serviceutil",
        "win32service",
        "win32event",
        "win32api",
        "pywintypes",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ai-mentor-service",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
