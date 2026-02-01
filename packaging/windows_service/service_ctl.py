"""
Service controller CLI: install / start / stop / uninstall AI_Mentor_Backend.
Non-interactive; exit codes matter. Run as admin for install/uninstall/start/stop.
"""
from __future__ import annotations

import sys

try:
    import win32serviceutil
except ImportError:
    print("pywin32 required. pip install pywin32>=306", file=sys.stderr)
    sys.exit(1)

# Same-dir import so PyInstaller bundles both modules when entry is service_ctl.py
try:
    from packaging.windows_service.ai_mentor_backend_service import AIMentorBackendService
except ImportError:
    from ai_mentor_backend_service import AIMentorBackendService  # type: ignore

if AIMentorBackendService is None:
    print("Service class not available (pywin32 missing?).", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    # When SCM starts the service, argv may have no subcommand; HandleCommandLine handles that.
    try:
        win32serviceutil.HandleCommandLine(AIMentorBackendService)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
