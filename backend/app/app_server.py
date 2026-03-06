"""
FastAPI entrypoint for Tauri backend runner. Exposes the same app as main.py.
Run from repo root: uvicorn backend.app.app_server:app --host 127.0.0.1 --port 8000
"""
from backend.main import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.app_server:app", host="127.0.0.1", port=8000)
