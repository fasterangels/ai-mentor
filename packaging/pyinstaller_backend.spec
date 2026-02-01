# PyInstaller spec for AI Mentor backend — no-console Windows EXE.
# Run from repo root: pyinstaller packaging/pyinstaller_backend.spec
# Output: dist/ai-mentor-backend.exe (no console window)

# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# Run from repo root: pyinstaller packaging/pyinstaller_backend.spec
# SPEC = path to this .spec file when PyInstaller runs
block_cwd = os.path.dirname(os.path.abspath(SPEC))
repo_root = os.path.dirname(block_cwd)
backend_dir = os.path.join(repo_root, 'backend')
script = os.path.join(backend_dir, 'backend_entry.py')

a = Analysis(
    [script],
    pathex=[backend_dir, repo_root],
    binaries=[],
    datas=[],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'starlette',
        'starlette.routing',
        'starlette.middleware',
        'starlette.middleware.cors',
        'sqlalchemy',
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.ext.asyncio',
        'aiosqlite',
        'pydantic',
        'main',
        'core.config',
        'core.database',
        'core.dependencies',
        'core.logging',
        'routes.api_v1',
        'services.analysis_service',
        'analyzer.engine_v1',
        'analyzer.v2.engine',
        'pipeline.pipeline',
        'pipeline.types',
        'resolver.match_resolver',
        'evaluation.evaluation_v2',
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
    name='ai-mentor-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (--noconsole / --windowed)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
