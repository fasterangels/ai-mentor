# Create a desktop shortcut for the DEV launcher

To run the AI Mentor dev environment with one double-click from your desktop:

1. **Right-click** on the desktop (or in a folder where you want the shortcut).
2. Choose **New** → **Shortcut**.
3. **Target:** Click **Browse** and go to your repo folder, then into `tooling\launchers\` and select **run_dev_windows.bat**.
   - Or type the full path by hand, for example:
     - `C:\AI_Mentor\AI Μέντορας για Windows v.0.2\tooling\launchers\run_dev_windows.bat`
4. Click **Next**.
5. **Name:** e.g. `AI Mentor DEV`.
6. Click **Finish**.

**Optional:** Right-click the new shortcut → **Properties** → set **Start in** to your repo root (e.g. `C:\AI_Mentor\AI Μέντορας για Windows v.0.2`) so the batch file’s relative paths resolve correctly. The batch file already derives the repo root from its own location, so this is only needed if you see path-related errors.

Double-click the shortcut to start backend, frontend, and open the browser.
