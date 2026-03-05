import os
import subprocess
import sys


def main() -> None:
    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo_root = os.path.dirname(backend_root)
    path_sep = os.pathsep
    pythonpath = path_sep.join([backend_root, repo_root])
    env = {**os.environ, "PYTHONPATH": pythonpath}
    subprocess.Popen(
        [sys.executable, os.path.join(backend_root, "app", "app_server.py")],
        cwd=backend_root,
        env=env,
    )


if __name__ == "__main__":
    main()
