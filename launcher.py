"""
AI Mentor - True Hidden Launcher for Windows
Starts backend, frontend, and Ollama without any visible console windows
Fixed version with proper backend startup, logging, and health checks
"""

import subprocess
import sys
import time
import os
from pathlib import Path
import ctypes

# Windows-specific flag to hide console windows
CREATE_NO_WINDOW = 0x08000000

def log_message(message, log_file_path):
    """Write a message to log file and print to console"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}\n"
    print(log_msg.strip())
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(log_msg)

def check_ollama(launcher_log):
    """Check if Ollama is running, start if not"""
    try:
        # Check if Ollama is running
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW
        )
        if result.returncode == 0:
            log_message("✅ Ollama is running", launcher_log)
            return True
    except Exception as e:
        log_message(f"⚠️  Ollama check failed: {e}", launcher_log)
    
    # Try to start Ollama
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        log_message("✅ Ollama started", launcher_log)
        time.sleep(2)
        return True
    except Exception as e:
        log_message(f"❌ Failed to start Ollama: {e}", launcher_log)
        return False

def warm_up_ollama(launcher_log):
    """Warm up Ollama model"""
    try:
        subprocess.run(
            ["ollama", "run", "llama3:8b", "Hello"],
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=30
        )
        log_message("✅ Ollama warm-up complete", launcher_log)
    except Exception as e:
        log_message(f"⚠️  Ollama warm-up failed: {e}", launcher_log)

def start_backend(launcher_log):
    """Start FastAPI backend with venv activation"""
    try:
        workspace_dir = Path(__file__).parent
        backend_path = workspace_dir / "backend"
        venv_python = backend_path / "venv" / "Scripts" / "python.exe"
        
        # Check if venv python exists
        if not venv_python.exists():
            log_message(f"❌ venv python not found at: {venv_python}", launcher_log)
            log_message("Using system python instead", launcher_log)
            venv_python = sys.executable
        
        # Create backend log file
        backend_log_path = workspace_dir / "logs" / "hidden_backend.log"
        backend_log = open(backend_log_path, "w", encoding="utf-8")
        
        log_message(f"Starting backend with: {venv_python}", launcher_log)
        log_message(f"Backend log: {backend_log_path}", launcher_log)
        
        # Start backend with hidden window
        process = subprocess.Popen(
            [str(venv_python), "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
            cwd=str(backend_path),
            creationflags=CREATE_NO_WINDOW,
            stdout=backend_log,
            stderr=backend_log
        )
        log_message(f"✅ Backend started (PID: {process.pid})", launcher_log)
        return process, backend_log_path
    except Exception as e:
        log_message(f"❌ Failed to start backend: {e}", launcher_log)
        return None, None

def start_frontend(launcher_log):
    """Start React frontend"""
    try:
        workspace_dir = Path(__file__).parent
        frontend_path = workspace_dir / "app" / "frontend"
        
        # Create frontend log file
        frontend_log_path = workspace_dir / "logs" / "hidden_frontend.log"
        frontend_log = open(frontend_log_path, "w", encoding="utf-8")
        
        log_message(f"Frontend log: {frontend_log_path}", launcher_log)
        
        # Start frontend with hidden window
        process = subprocess.Popen(
            ["pnpm", "run", "dev"],
            cwd=str(frontend_path),
            creationflags=CREATE_NO_WINDOW,
            stdout=frontend_log,
            stderr=frontend_log,
            shell=True
        )
        log_message(f"✅ Frontend started (PID: {process.pid})", launcher_log)
        return process
    except Exception as e:
        log_message(f"❌ Failed to start frontend: {e}", launcher_log)
        return None

def wait_for_backend_health(launcher_log, backend_log_path, max_wait=60):
    """Wait for backend to be healthy"""
    import requests
    
    log_message("Waiting for backend to be ready...", launcher_log)
    
    for i in range(max_wait):
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                log_message(f"✅ Backend is healthy (took {i+1}s)", launcher_log)
                return True
        except Exception as e:
            if i == 0:
                log_message(f"Waiting for backend... ({i+1}/{max_wait})", launcher_log)
            elif i % 10 == 0:
                log_message(f"Still waiting... ({i+1}/{max_wait})", launcher_log)
        time.sleep(1)
    
    # Backend failed to start
    log_message(f"❌ Backend failed to start after {max_wait}s", launcher_log)
    
    # Show error MessageBox
    error_msg = f"Backend failed to start.\n\nCheck log file:\n{backend_log_path}\n\nThe application will not work correctly."
    ctypes.windll.user32.MessageBoxW(0, error_msg, "AI Mentor - Backend Error", 0x10)
    
    return False

def open_browser(launcher_log):
    """Open browser to localhost:3000"""
    try:
        subprocess.Popen(
            ["cmd", "/c", "start", "http://localhost:3000"],
            creationflags=CREATE_NO_WINDOW,
            shell=True
        )
        log_message("✅ Browser opened", launcher_log)
    except Exception as e:
        log_message(f"⚠️  Failed to open browser: {e}", launcher_log)

def main():
    """Main launcher function"""
    # Create logs directory
    workspace_dir = Path(__file__).parent
    logs_dir = workspace_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Create launcher log
    launcher_log_path = logs_dir / "hidden_launcher.log"
    
    log_message("=" * 50, launcher_log_path)
    log_message("  AI MENTOR - HIDDEN LAUNCHER", launcher_log_path)
    log_message("=" * 50, launcher_log_path)
    log_message("", launcher_log_path)
    
    # Step 1: Check/Start Ollama
    log_message("Step 1: Checking Ollama...", launcher_log_path)
    if not check_ollama(launcher_log_path):
        log_message("❌ Ollama not available. Please install Ollama first.", launcher_log_path)
        ctypes.windll.user32.MessageBoxW(0, "Ollama not available. Please install Ollama first.", "AI Mentor - Error", 0x10)
        sys.exit(1)
    
    # Step 2: Warm up Ollama
    log_message("", launcher_log_path)
    log_message("Step 2: Warming up Ollama model...", launcher_log_path)
    warm_up_ollama(launcher_log_path)
    
    # Step 3: Start Backend
    log_message("", launcher_log_path)
    log_message("Step 3: Starting backend...", launcher_log_path)
    backend_process, backend_log_path = start_backend(launcher_log_path)
    if not backend_process:
        log_message("❌ Backend failed to start", launcher_log_path)
        ctypes.windll.user32.MessageBoxW(0, f"Backend failed to start.\n\nCheck log: {backend_log_path}", "AI Mentor - Error", 0x10)
        sys.exit(1)
    
    # Step 4: Wait for backend health check
    log_message("", launcher_log_path)
    log_message("Step 4: Waiting for backend to be ready...", launcher_log_path)
    if not wait_for_backend_health(launcher_log_path, backend_log_path):
        backend_process.terminate()
        sys.exit(1)
    
    # Step 5: Start Frontend
    log_message("", launcher_log_path)
    log_message("Step 5: Starting frontend...", launcher_log_path)
    frontend_process = start_frontend(launcher_log_path)
    if not frontend_process:
        log_message("❌ Frontend failed to start", launcher_log_path)
        backend_process.terminate()
        ctypes.windll.user32.MessageBoxW(0, "Frontend failed to start.", "AI Mentor - Error", 0x10)
        sys.exit(1)
    
    # Wait a bit for frontend to initialize
    time.sleep(5)
    
    # Step 6: Open Browser
    log_message("", launcher_log_path)
    log_message("Step 6: Opening browser...", launcher_log_path)
    open_browser(launcher_log_path)
    
    log_message("", launcher_log_path)
    log_message("=" * 50, launcher_log_path)
    log_message("  ✅ AI MENTOR STARTED SUCCESSFULLY", launcher_log_path)
    log_message("=" * 50, launcher_log_path)
    log_message("", launcher_log_path)
    log_message("Backend: http://localhost:8000", launcher_log_path)
    log_message("Frontend: http://localhost:3000", launcher_log_path)
    log_message("", launcher_log_path)
    log_message("Services are running in the background.", launcher_log_path)
    log_message("", launcher_log_path)
    log_message("Logs:", launcher_log_path)
    log_message(f"  - Launcher: {launcher_log_path}", launcher_log_path)
    log_message(f"  - Backend: {backend_log_path}", launcher_log_path)
    log_message(f"  - Frontend: {workspace_dir / 'logs' / 'hidden_frontend.log'}", launcher_log_path)
    log_message("", launcher_log_path)

if __name__ == "__main__":
    main()