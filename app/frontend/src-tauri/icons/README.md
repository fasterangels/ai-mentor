# App icons

Tauri needs at least one icon for the Windows build (e.g. `icon.ico`).

**Option 1:** Generate from a PNG (from `app/frontend`):

```cmd
pnpm tauri icon path\to\your\icon.png
```

**Option 2:** Copy `icon.ico` (and optionally 32x32.png, 128x128.png, etc.) into this folder.

Without icons, `tauri build` may fail; add at least `icon.ico` (e.g. 256x256 or multi-size).
