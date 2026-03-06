import os
import subprocess
import sys


def main() -> None:
    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo_root = os.path.dirname(backend_root)
    app_server_path = os.path.join(backend_root, "app", "app_server.py")
    path_sep = os.pathsep
    pythonpath = path_sep.join([backend_root, repo_root])
    env = {**os.environ, "PYTHONPATH": pythonpath}
    env_copy = dict(env)

    # Interpreter candidates in order: A) sys.executable, B) python, C) python3, D) py -3.11, E) py -3
    candidates: list[list[str]] = []
    if sys.executable and os.path.isfile(sys.executable):
        candidates.append([sys.executable])
    candidates.append(["python"])
    candidates.append(["python3"])
    candidates.append(["py", "-3.11"])
    candidates.append(["py", "-3"])

    for argv in candidates:
        try:
            full_argv = argv + [app_server_path]
            subprocess.Popen(full_argv, cwd=backend_root, env=env_copy)
            return
        except (FileNotFoundError, OSError):
            continue

    raise RuntimeError(
        "No Python interpreter found. Install Python 3.11+ or ensure 'py' is available."
    )


if __name__ == "__main__":
    main()
