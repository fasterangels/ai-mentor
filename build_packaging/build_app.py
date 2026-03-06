import subprocess
import sys
from pathlib import Path

ENTRYPOINT = "tools/run_app.py"


def build() -> None:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--name",
        "AI_Mentor",
        ENTRYPOINT,
    ]

    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    build()

