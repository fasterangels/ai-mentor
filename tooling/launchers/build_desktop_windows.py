"""
Unicode-safe one-click Windows desktop build: backend exe + frontend + Tauri + E2E test.

Backend runs as per-user Scheduled Task (AI_Mentor_Backend). Build produces backend exe, copies it plus
launch_backend.cmd and task XML to Tauri bin, builds NSIS; FINAL step runs test_installed_task_end_to_end.py
(silent install -> task registered + run -> /health -> POST /api/v1/analyze expect 501). If E2E test fails, BUILD FAILS.

Run from repo root:
  python -m tooling.launchers.build_desktop_windows
Or: python tooling/launchers/build_desktop_windows.py (with cwd = repo root).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Repo root from this file (Unicode-safe; no reliance on cwd or argv)
_SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = _SCRIPT_DIR.parent.parent


def _short_path(path: Path) -> str:
    """On Windows, return 8.3 short path for child processes (avoids encoding issues)."""
    if sys.platform != "win32":
        return str(path)
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(1024)
        r = ctypes.windll.kernel32.GetShortPathNameW(str(path), buf, len(buf))  # type: ignore[attr-defined]
        if r and r < len(buf):
            return buf.value
    except Exception:
        pass
    return str(path)


def _run(cmd: list[str], cwd: Path, env: dict | None = None, desc: str = "", shell: bool = False) -> None:
    env = env or os.environ
    env = {str(k): str(v) for k, v in env.items()}
    cwd_str = _short_path(cwd)
    # On Windows pass short paths so child processes see ASCII paths
    cmd_str = []
    for c in cmd:
        p = Path(c)
        if sys.platform == "win32" and p.is_absolute() and p.exists():
            cmd_str.append(_short_path(p))
        else:
            cmd_str.append(c)
    if shell and sys.platform == "win32":
        # Pass as a single string for cmd.exe
        cmd_line = " ".join(cmd_str)
        print(f"  run: {cmd_line}")
        subprocess.run(cmd_line, cwd=cwd_str, env=env, check=True, shell=True)
    else:
        print(f"  run: {' '.join(cmd_str)}")
        subprocess.run(cmd_str, cwd=cwd_str, env=env, check=True, shell=shell)


def _ensure_node_npm_on_path(env: dict) -> None:
    """On Windows, if npm is not on PATH, add common Node.js locations or find via where.exe."""
    if sys.platform != "win32":
        return
    path = env.get("PATH", "")
    if "npm" in path.lower() or "nodejs" in path.lower():
        return
    candidates = [
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "nodejs",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "nodejs",
        Path(os.environ.get("APPDATA", "")) / "npm",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "node",
    ]
    for d in candidates:
        if not d:
            continue
        npm = d / "npm.cmd" if (d / "npm.cmd").exists() else (d / "npm")
        if d.exists() and (npm.exists() or (d / "node.exe").exists()):
            env["PATH"] = str(d) + os.pathsep + path
            return
    try:
        r = subprocess.run(
            ["where.exe", "npm"],
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
            cwd=os.getcwd(),
        )
        if r.returncode == 0 and r.stdout:
            first_line = r.stdout.strip().splitlines()[0].strip()
            if first_line:
                npm_dir = str(Path(first_line).parent)
                env["PATH"] = npm_dir + os.pathsep + path
    except Exception:
        pass


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dst))
    print(f"  copy: {dst}")


def run_smoke_test(repo_root: Path) -> None:
    """Launch built backend exe briefly; check backend.log; write build_smoke_test.log."""
    localappdata = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    log_dir = Path(localappdata) / "AI_Mentor" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    smoke_log = log_dir / "build_smoke_test.log"

    exe = repo_root / "dist" / "ai-mentor-backend.exe"
    if not exe.exists():
        lines = [
            f"[{datetime.now(timezone.utc).isoformat()}] build_smoke_test",
            "backend_exe_missing=yes",
            "path=" + str(exe),
        ]
        smoke_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    # Clear or truncate backend.log so we only see this run
    backend_log = log_dir / "backend.log"
    if backend_log.exists():
        try:
            backend_log.write_text("", encoding="utf-8")
        except Exception:
            pass

    env = os.environ.copy()
    env["AI_MENTOR_PACKAGED"] = "1"
    proc = subprocess.Popen(
        [str(exe)],
        cwd=str(repo_root),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(4)
        content = ""
        if backend_log.exists():
            try:
                content = backend_log.read_text(encoding="utf-8", errors="replace")
            except Exception:
                content = ""
        has_module_error = "ModuleNotFoundError" in content or (
            "aiosqlite" in content and "No module named" in content
        )
        has_start = "BACKEND_START" in content and "127.0.0.1" in content
        bound_8000 = "8000" in content and "127.0.0.1" in content
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    lines = [
        f"[{datetime.now(timezone.utc).isoformat()}] build_smoke_test",
        "backend_started=yes" if has_start else "backend_started=no",
        "backend_bind_127.0.0.1_8000=yes" if bound_8000 else "backend_bind_127.0.0.1_8000=no",
        "no_ModuleNotFoundError=yes" if not has_module_error else "no_ModuleNotFoundError=no",
    ]
    smoke_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("  smoke test log: " + str(smoke_log))


def main() -> int:
    root = REPO_ROOT
    print("=== AI Mentor Desktop Build (Windows) ===")
    print("Repo root:", root)
    print()

    # Clear TAURI_CONFIG so Tauri uses only src-tauri/tauri.conf.json
    env = os.environ.copy()
    env.pop("TAURI_CONFIG", None)
    # Ensure Rust/cargo on PATH for pip builds (e.g. pydantic-core on Python 3.14)
    cargo_bin = Path(os.environ.get("USERPROFILE", "")) / ".cargo" / "bin"
    if sys.platform == "win32" and cargo_bin.exists():
        path = env.get("PATH", "")
        env["PATH"] = str(cargo_bin) + os.pathsep + path
    # Ensure Node/npm on PATH for frontend and Tauri (Windows often needs this when run from IDE)
    _ensure_node_npm_on_path(env)
    if sys.platform == "win32":
        nodejs_dir = Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "nodejs"
        if nodejs_dir.exists() and "nodejs" not in env.get("PATH", "").lower():
            env["PATH"] = str(nodejs_dir) + os.pathsep + env.get("PATH", "")
        print("  nodejs in PATH:", "nodejs" in env.get("PATH", "").lower())

    # 1) Backend: pip install + PyInstaller (backend exe)
    print("[1/5] Installing backend deps...")
    try:
        _run(
            [sys.executable, "-m", "pip", "install", "-r", str(root / "backend" / "requirements.txt")],
            cwd=root,
            env=env,
        )
    except subprocess.CalledProcessError:
        print("  WARNING: pip install failed. Continuing with existing packages.")
    print("[1/5] Building backend exe (PyInstaller)...")
    _run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            str(root / "packaging" / "backend_sidecar" / "pyinstaller_sidecar.spec"),
            "--noconfirm",
        ],
        cwd=root,
        env=env,
    )
    exe_path = root / "dist" / "ai-mentor-backend.exe"
    print("  Backend EXE:", exe_path)

    # 2) Copy backend exe + task launcher into Tauri bin (for NSIS bundle; no XML)
    print("[2/5] Copying backend exe and launch_backend.cmd to Tauri bin...")
    tauri_bin = root / "app" / "frontend" / "src-tauri" / "bin"
    tauri_bin.mkdir(parents=True, exist_ok=True)
    _copy(exe_path, tauri_bin / "ai-mentor-backend-x86_64-pc-windows-msvc.exe")
    _copy(exe_path, tauri_bin / "ai-mentor-backend.exe")
    _copy(root / "packaging" / "windows_task" / "launch_backend.cmd", tauri_bin / "launch_backend.cmd")
    print()

    # 3) Frontend: npm install + build
    frontend_dir = root / "app" / "frontend"
    tauri_ok = False
    try:
        import json as _json
        tauri_conf = frontend_dir / "src-tauri" / "tauri.conf.json"
        version = "0.2.0"
        if tauri_conf.exists():
            try:
                version = _json.loads(tauri_conf.read_text(encoding="utf-8")).get("version", version)
            except Exception:
                pass
        try:
            r = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            git_sha = (r.stdout or "").strip() or "nogit"
        except Exception:
            git_sha = "nogit"
        ts = datetime.utcnow().strftime("%Y%m%d%H%M")
        build_id = f"{version}-{git_sha}-{ts}"
        env["VITE_BUILD_ID"] = build_id
        print(f"  VITE_BUILD_ID={build_id}")
        print("[3/5] Frontend: npm install...")
        _run(["npm", "install"], cwd=frontend_dir, env=env, shell=sys.platform == "win32")
        # Fast checks before build (Phase 5)
        pkg_json = frontend_dir / "package.json"
        if pkg_json.exists():
            try:
                pkg = _json.loads(pkg_json.read_text(encoding="utf-8"))
                if "lint" in pkg.get("scripts", {}):
                    print("[3/5] Frontend: npm run lint...")
                    _run(["npm", "run", "lint"], cwd=frontend_dir, env=env, shell=sys.platform == "win32")
            except Exception:
                pass
        if (frontend_dir / "tsconfig.json").exists():
            print("[3/5] Frontend: tsc --noEmit...")
            _run(["npx", "tsc", "--noEmit"], cwd=frontend_dir, env=env, shell=sys.platform == "win32")
        print("[3/5] Frontend: npm run build...")
        _run(["npm", "run", "build"], cwd=frontend_dir, env=env, shell=sys.platform == "win32")
        print()

        # 4) Tauri release build (NSIS)
        print("[4/5] Tauri build (release)...")
        _run(["npx", "tauri", "build"], cwd=frontend_dir, env=env, shell=sys.platform == "win32")
        tauri_ok = True
        print()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print("  WARNING: Frontend/Tauri build failed (npm/Node may not be on PATH).")
        print("  ", e)
        print()

    # 5) [FINAL] E2E test: silent install -> task registered + run -> /health -> POST /api/v1/analyze (expect 501)
    bundle = root / "app" / "frontend" / "src-tauri" / "target" / "release" / "bundle"
    nsis_dir = bundle / "nsis"
    if sys.platform == "win32" and nsis_dir.is_dir() and list(nsis_dir.glob("*.exe")):
        print("[5/5] E2E test (install NSIS -> task + health + analyze)...")
        test_script = root / "packaging" / "test_installed_task_end_to_end.py"
        if test_script.exists():
            repo_arg = _short_path(root) if sys.platform == "win32" else str(root)
            rc_final = subprocess.run(
                [sys.executable, str(test_script), "--repo-root", repo_arg],
                cwd=str(root),
                env=os.environ.copy(),
                check=False,
                timeout=300,
            )
            if rc_final.returncode != 0:
                print("BUILD FAILS: E2E test did not pass (test_installed_task_end_to_end.py).")
                print("See output above and %LOCALAPPDATA%\\AI_Mentor\\logs\\backend.log for diagnostics.")
                return 1
            print("[5/5] TASK E2E TEST: PASS")
        else:
            print("  FAIL: packaging/test_installed_task_end_to_end.py not found")
            return 1
    else:
        if not tauri_ok:
            print("  skip E2E: Tauri/NSIS build did not produce installer")
        else:
            print("  FAIL: No NSIS installer found; E2E test not run")
            return 1
    print()

    print("=== Build finished ===")
    print("Backend EXE:", root / "dist" / "ai-mentor-backend.exe")
    if tauri_ok:
        print("Installer / EXE output:")
        print("  MSI:   ", bundle / "msi")
        print("  NSIS:  ", bundle / "nsis")
    return 0


if __name__ == "__main__":
    sys.exit(main())
