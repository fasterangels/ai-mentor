//! Backend auto-start and process management for the FastAPI backend.
//! Uses a global process handle and health checks with short timeouts.
//!
//! In dev, we spawn the Python backend via `backend/runner/start_backend.py`.
//! In packaged Windows installs, we prefer the bundled `ai-mentor-backend.exe`
//! sidecar (under `%LOCALAPPDATA%\AI_Mentor\service` or next to the Tauri exe).

use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::{Mutex, OnceLock};
use std::time::{Duration, Instant};

use crate::app_log;

const HEALTH_URL: &str = "http://127.0.0.1:8000/health";
const HEALTH_TIMEOUT_SECS: u64 = 4;
const POLL_INTERVAL_MS: u64 = 250;
const STARTUP_TIMEOUT_SECS: u64 = 20;

static BACKEND_CHILD: OnceLock<Mutex<Option<Child>>> = OnceLock::new();

fn log(msg: &str) {
    app_log(&format!("[backend_manager] {msg}"));
}

fn get_handle() -> &'static Mutex<Option<Child>> {
    BACKEND_CHILD.get_or_init(|| Mutex::new(None))
}

/// Returns repo root when running from target (dev): exe -> target/debug -> src-tauri -> app -> repo.
fn repo_root_from_exe() -> Option<PathBuf> {
    let exe = std::env::current_exe().ok()?;
    exe.parent()
        .and_then(|p| p.parent())
        .and_then(|p| p.parent())
        .and_then(|p| p.parent())
        .map(|p| p.to_path_buf())
}

fn script_path(repo_root: &std::path::Path) -> PathBuf {
    repo_root
        .join("backend")
        .join("runner")
        .join("start_backend.py")
}

/// Returns true if GET /health returns 200 and body contains "ok".
fn check_health() -> bool {
    let client = match reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(HEALTH_TIMEOUT_SECS))
        .build()
    {
        Ok(c) => c,
        Err(_) => return false,
    };
    let res = match client.get(HEALTH_URL).send() {
        Ok(r) => r,
        Err(_) => return false,
    };
    if !res.status().is_success() {
        return false;
    }
    let body = match res.text() {
        Ok(b) => b,
        Err(_) => return false,
    };
    body.contains("\"status\":\"ok\"") || body.contains("\"status\": \"ok\"") || body.contains("ok")
}

/// Spawn the Python backend using start_backend.py. Windows: py -3.11; macOS/Linux: python3.
fn spawn_python_backend(repo_root: &std::path::Path) -> Result<Child, String> {
    let script = script_path(repo_root);
    if !script.exists() {
        return Err(format!("Backend script not found: {}", script.display()));
    }

    let backend_path = repo_root.join("backend");

    #[cfg(windows)]
    let child = {
        log(&format!(
            "Spawning Python backend via script {}",
            script.display()
        ));
        let mut cmd = Command::new("py");
        cmd.arg("-3.11")
            .arg(&script)
            .current_dir(repo_root)
            .env("PYTHONUNBUFFERED", "1")
            .env("PYTHONPATH", &backend_path)
            .stdout(Stdio::null())
            .stderr(Stdio::null());
        cmd.spawn().map_err(|e| e.to_string())?
    };

    #[cfg(not(windows))]
    let child = {
        log(&format!(
            "Spawning Python backend via script {} (non-Windows)",
            script.display()
        ));
        let mut cmd = Command::new("python3");
        cmd.arg(&script)
            .current_dir(repo_root)
            .env("PYTHONUNBUFFERED", "1")
            .env("PYTHONPATH", &backend_path)
            .stdout(Stdio::null())
            .stderr(Stdio::null());
        cmd.spawn().map_err(|e| e.to_string())?
    };

    Ok(child)
}

/// Candidate locations for the packaged backend sidecar exe (Windows installed app).
#[cfg(windows)]
fn sidecar_candidate_paths() -> Vec<PathBuf> {
    let mut paths = Vec::new();

    // 1) Service location used by NSIS hooks: %LOCALAPPDATA%\AI_Mentor\service\ai-mentor-backend.exe
    if let Ok(local_app_data) = std::env::var("LOCALAPPDATA") {
        let service = PathBuf::from(local_app_data)
            .join("AI_Mentor")
            .join("service")
            .join("ai-mentor-backend.exe");
        paths.push(service);
    }

    // 2) Next to the main binary or in resources/bin (Tauri bundle layouts).
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(exe_dir) = exe_path.parent() {
            paths.push(exe_dir.join("ai-mentor-backend.exe"));
            paths.push(exe_dir.join("resources").join("ai-mentor-backend.exe"));
            paths.push(
                exe_dir
                    .join("resources")
                    .join("bin")
                    .join("ai-mentor-backend.exe"),
            );
        }
    }

    paths
}

/// Try to spawn the packaged backend sidecar exe. Returns the child process on success.
#[cfg(windows)]
fn spawn_sidecar_backend() -> Result<Child, String> {
    let candidates = sidecar_candidate_paths();
    if candidates.is_empty() {
        return Err("No sidecar candidate paths discovered".to_string());
    }

    log(&format!(
        "Attempting to spawn sidecar backend from {} candidate paths",
        candidates.len()
    ));

    for path in candidates {
        if !path.exists() {
            continue;
        }
        log(&format!(
            "Trying sidecar backend exe at: {}",
            path.display()
        ));
        let mut cmd = Command::new(&path);
        cmd.stdout(Stdio::null()).stderr(Stdio::null());
        match cmd.spawn() {
            Ok(child) => {
                log(&format!(
                    "Spawned sidecar backend (pid={}) from {}",
                    child.id(),
                    path.display()
                ));
                return Ok(child);
            }
            Err(e) => {
                log(&format!(
                    "Failed to spawn sidecar backend at {}: {}",
                    path.display(),
                    e
                ));
            }
        }
    }

    Err("Failed to spawn sidecar backend from any candidate path".to_string())
}

/// Spawn backend process depending on environment: prefer packaged sidecar exe on Windows,
/// fall back to Python dev script when running from a repo checkout.
fn spawn_backend_process() -> Result<Child, String> {
    #[cfg(windows)]
    {
        if let Ok(child) = spawn_sidecar_backend() {
            return Ok(child);
        }
        log("Sidecar backend spawn failed; falling back to Python dev backend if possible.");
    }

    let repo_root = repo_root_from_exe()
        .ok_or_else(|| "Could not determine repo root (not running from target?)".to_string())?;
    spawn_python_backend(&repo_root)
}

/// Start the backend if not already healthy. Spawns process and polls /health for up to ~20s.
pub fn start_backend_if_needed() -> Result<(), String> {
    log("start_backend_if_needed: checking backend health...");
    if check_health() {
        log("start_backend_if_needed: backend already healthy; no spawn needed.");
        return Ok(());
    }

    log("start_backend_if_needed: backend not healthy; attempting to spawn process...");
    let child = spawn_backend_process()?;

    {
        let mut guard = get_handle().lock().map_err(|e| e.to_string())?;
        if let Some(mut old) = guard.take() {
            let _ = old.kill();
        }
        *guard = Some(child);
    }

    log(&format!(
        "start_backend_if_needed: spawned backend; waiting up to {}s for /health...",
        STARTUP_TIMEOUT_SECS
    ));
    let deadline = Instant::now() + Duration::from_secs(STARTUP_TIMEOUT_SECS);
    while Instant::now() < deadline {
        if check_health() {
            log("start_backend_if_needed: backend became healthy.");
            return Ok(());
        }
        std::thread::sleep(Duration::from_millis(POLL_INTERVAL_MS));
    }

    let mut guard = get_handle().lock().map_err(|e| e.to_string())?;
    if let Some(mut c) = guard.take() {
        let _ = c.kill();
    }
    log("start_backend_if_needed: backend did not become healthy within timeout; killed child.");
    Err(format!(
        "Backend did not become healthy within {} seconds",
        STARTUP_TIMEOUT_SECS
    ))
}

/// Returns true if GET /health responds OK.
#[allow(dead_code)]
pub fn is_backend_running() -> bool {
    check_health()
}

/// Best-effort stop: kill the stored child process if any.
pub fn stop_backend() -> Result<(), String> {
    let mut guard = get_handle().lock().map_err(|e| e.to_string())?;
    if let Some(mut child) = guard.take() {
        let _ = child.kill();
    }
    Ok(())
}

/// Fetch /health response body as string. Uses short timeout.
pub fn backend_health_response() -> Result<String, String> {
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(HEALTH_TIMEOUT_SECS))
        .build()
        .map_err(|e| e.to_string())?;
    let res = client.get(HEALTH_URL).send().map_err(|e| e.to_string())?;
    let status = res.status();
    let body = res.text().map_err(|e| e.to_string())?;
    if status.is_success() {
        Ok(body)
    } else {
        Err(format!("HTTP {}: {}", status.as_u16(), body))
    }
}

