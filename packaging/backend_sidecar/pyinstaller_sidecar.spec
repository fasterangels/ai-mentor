# PyInstaller spec for AI Mentor backend SIDECAR — fixed port 8000, no console.
# Used by desktop build only. Run from repo root: pyinstaller packaging/backend_sidecar/pyinstaller_sidecar.spec
# Output: dist/ai-mentor-backend.exe (copy to src-tauri/bin/ai-mentor-backend-x86_64-pc-windows-msvc.exe for Tauri)

# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules

block_cwd = os.path.dirname(os.path.abspath(SPEC))
# packaging/backend_sidecar -> go up twice to repo root
repo_root = os.path.dirname(os.path.dirname(block_cwd))
backend_dir = os.path.join(repo_root, "backend")
script = os.path.join(backend_dir, "sidecar_entry.py")

# Ensure aiosqlite and all submodules are bundled (avoids ModuleNotFoundError at runtime)
_hidden_aiosqlite = ["aiosqlite"] + list(collect_submodules("aiosqlite"))

a = Analysis(
    [script],
    pathex=[backend_dir, repo_root],
    binaries=[],
    datas=[],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "fastapi",
        "starlette",
        "starlette.routing",
        "starlette.middleware",
        "starlette.middleware.cors",
        "sqlalchemy",
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.dialects.sqlite.aiosqlite",
        "sqlalchemy.ext.asyncio",
        "pydantic",
        "main",
        "core.config",
        "core.database",
        "core.dependencies",
        "core.logging",
        "routes.api_v1",
        "services.analysis_service",
        "analyzer.engine_v1",
        "analyzer.v2.engine",
        "pipeline.pipeline",
        "pipeline.types",
        "resolver.match_resolver",
        "evaluation.evaluation_v2",
    ] + _hidden_aiosqlite,
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
    name="ai-mentor-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
