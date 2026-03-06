// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    io::{Read, Write},
    net::TcpStream,
    path::{Path, PathBuf},
    process::{Child, Command},
    thread::sleep,
    time::{Duration, Instant},
};

fn spawn_packaged_backend(exe_dir: &Path) -> Option<Child> {
    // Prefer sidecar exe next to the main binary (dev + some packaged layouts).
    let direct = exe_dir.join("ai-mentor-backend.exe");
    if direct.exists() {
        println!("Starting packaged backend exe (sidecar): {:?}", direct);
        return Command::new(&direct)
            .spawn()
            .map_err(|e| {
                eprintln!("Failed to spawn packaged backend exe (sidecar): {e}");
                e
            })
            .ok();
    }

    // When bundled with Tauri resources on Windows, files under "bundle.resources"
    // (e.g. "bin/ai-mentor-backend.exe") are placed in a resources subfolder.
    let resource_sidecar = exe_dir
        .join("resources")
        .join("bin")
        .join("ai-mentor-backend.exe");
    if resource_sidecar.exists() {
        println!(
            "Starting packaged backend exe (resources/bin): {:?}",
            resource_sidecar
        );
        return Command::new(&resource_sidecar)
            .spawn()
            .map_err(|e| {
                eprintln!("Failed to spawn packaged backend exe (resources/bin): {e}");
                e
            })
            .ok();
    }

    None
}

fn spawn_python_backend(repo_root: &Path) -> Option<Child> {
    let script = repo_root
        .join("backend")
        .join("runner")
        .join("start_backend.py");
    if !script.exists() {
        eprintln!("Backend runner script not found at {:?}", script);
        return None;
    }

    println!(
        "Starting backend from Tauri via Python (script: {:?})...",
        script
    );

    let backend_path = repo_root.join("backend");

    let make_cmd = |python_cmd: &str| {
        let mut cmd = Command::new(python_cmd);
        cmd.arg(&script).current_dir(repo_root).env("PYTHONUNBUFFERED", "1");
        if backend_path.exists() {
            cmd.env("PYTHONPATH", &backend_path);
        }
        cmd.spawn()
    };

    match make_cmd("python") {
        Ok(child) => Some(child),
        Err(e) => {
            eprintln!("Failed to spawn backend with 'python': {e}");
            match make_cmd("python3") {
                Ok(child) => Some(child),
                Err(e2) => {
                    eprintln!("Failed to spawn backend with 'python3': {e2}");
                    None
                }
            }
        }
    }
}

fn spawn_backend() -> Option<Child> {
    let exe_path = std::env::current_exe().ok()?;
    let exe_dir = exe_path.parent()?;

    // 1) Prefer packaged sidecar exe in release/installed builds.
    if let Some(child) = spawn_packaged_backend(exe_dir) {
        return Some(child);
    }

    // 2) Fallback to Python runner script (dev or when repo tree is present).
    let repo_root: PathBuf = exe_path
        .parent() // .../target/{debug,release}
        .and_then(|p| p.parent()) // .../src-tauri
        .and_then(|p| p.parent()) // .../app
        .and_then(|p| p.parent()) // repo root
        .map(|p| p.to_path_buf())?;

    spawn_python_backend(&repo_root)
}

fn backend_healthy() -> bool {
    let addr = "127.0.0.1:8000"
        .parse()
        .expect("valid socket address for backend health check");

    if let Ok(mut stream) = TcpStream::connect_timeout(&addr, Duration::from_millis(500)) {
        let request = b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n";
        if stream.write_all(request).is_err() {
            return false;
        }
        let mut buf = [0u8; 256];
        if let Ok(n) = stream.read(&mut buf) {
            let resp = String::from_utf8_lossy(&buf[..n]);
            return resp.starts_with("HTTP/1.1 200")
                || resp.starts_with("HTTP/1.0 200")
                || resp.contains(" 200 ");
        }
    }
    false
}

fn wait_for_backend_ready(timeout: Duration) -> bool {
    let start = Instant::now();
    while start.elapsed() < timeout {
        if backend_healthy() {
            println!("Backend health check succeeded.");
            return true;
        }
        sleep(Duration::from_millis(250));
    }
    false
}

fn main() {
    println!("AI Mentor desktop starting; ensuring backend is running...");
    let backend = spawn_backend();

    if !wait_for_backend_ready(Duration::from_secs(10)) {
        eprintln!("Backend not reachable after 10 seconds.");
    }

    // Run the main Tauri application (UI thread).
    ai_mentor_desktop::run();

    // Ensure backend process is terminated when the app closes.
    if let Some(mut child) = backend {
        println!("Shutting down backend process...");
        if let Err(e) = child.kill() {
            eprintln!("Failed to kill backend process: {e}");
        }
    }
}

