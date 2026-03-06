"""
Generate app/frontend/src-tauri/windows/nsis/installer.nsi from Tauri's official template
with RequestExecutionLevel admin at top and .onInit admin check.
Run from repo root: python packaging/ensure_nsis_template.py
Used by build_desktop_windows.py before Tauri build.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
URL = "https://raw.githubusercontent.com/tauri-apps/tauri/dev/crates/tauri-bundler/src/bundle/windows/nsis/installer.nsi"
OUT = REPO_ROOT / "app" / "frontend" / "src-tauri" / "windows" / "nsis" / "installer.nsi"

OLD_BLOCK = """; Handle install mode, `perUser`, `perMachine` or `both`
!if "${INSTALLMODE}" == "perMachine"
 RequestExecutionLevel admin
!endif

!if "${INSTALLMODE}" == "currentUser"
 RequestExecutionLevel user
!endif

"""

ADMIN_CHECK = r"""Function .onInit
  ClearErrors
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI_Mentor_Admin_Check" "Test" "1"
  IfErrors 0 +4
  MessageBox MB_ICONSTOP "Administrator rights are required to install AI Mentor Backend service."
  Abort
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\AI_Mentor_Admin_Check"
 ${GetOptions}"""


def main() -> int:
    try:
        import urllib.request
        req = urllib.request.urlopen(URL, timeout=15)
        content = req.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"Failed to fetch template: {e}", file=sys.stderr)
        return 1

    content = "RequestExecutionLevel admin\n\n" + content
    if OLD_BLOCK in content:
        content = content.replace(OLD_BLOCK, "; Admin forced at top of template\n\n", 1)
    oninit_marker = "Function .onInit\n ${GetOptions}"
    if oninit_marker in content and ADMIN_CHECK not in content:
        content = content.replace(oninit_marker, ADMIN_CHECK, 1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(content, encoding="utf-8")
    print(f"Written: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
