# AI Mentor — DEV launcher (Windows)

## What the launcher does

The one-click dev launcher:

1. **Starts the backend** in a new terminal: uvicorn on `http://127.0.0.1:8000` (from `backend/` with `venv`).
2. **Starts the frontend** in a new terminal: Vite dev server on port 3000 (from `app/frontend`).
3. **Waits** a few seconds for servers to start.
4. **Opens the browser** to `http://localhost:3000`.

Both servers keep running in their own terminal windows until you close them or press CTRL+C.

## How to run it

- **Double-click:** `tooling\launchers\run_dev_windows.bat`
- **From terminal (repo root):** `tooling\launchers\run_dev_windows.bat`
- **From terminal (anywhere):** run the batch file by full path; it will resolve the repo root from its own location.

## Requirements

- **Backend:** Python virtualenv at `backend\venv` with uvicorn and app dependencies installed (e.g. `pip install -r backend/requirements.txt`).
- **Frontend:** Node and npm (or pnpm) with dependencies installed in `app\frontend` (e.g. `npm install` or `pnpm install`). The launcher runs `npm run dev`; if you use pnpm only, run `pnpm run dev` manually in `app\frontend` or edit the batch file.

## Troubleshooting

| Symptom | Likely cause | What to do |
|--------|---------------|------------|
| Browser says "connection refused" or cannot connect | Frontend not running yet or failed to start | Wait a few more seconds; check the "AI Mentor - Frontend" window for errors. Ensure port 3000 is free. |
| Analyze fails / "Backend not reachable" | Backend not running or wrong port | Check the "AI Mentor - Backend" window. It should show "Uvicorn running on http://127.0.0.1:8000". Ensure port 8000 is free. |
| "Port already in use" in a server window | Another process is using 8000 or 3000 | Stop the other process or use a different port (would require changing the launcher or app config). |

## How to stop

- Close the **AI Mentor - Backend** and **AI Mentor - Frontend** terminal windows, or
- In each window, press **CTRL+C** to stop the server.

No backend or frontend application logic was modified; this launcher only starts processes and opens the browser.
