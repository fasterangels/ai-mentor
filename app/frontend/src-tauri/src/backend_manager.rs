//! Backend auto-start and process management for the Python FastAPI backend.
//! Uses a global process handle and health checks with short timeouts.

use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::{Mutex, OnceLock};
use std::time::{Duration, Instant};

const HEALTH_URL: &str = "http://127.0.0.1:8000/health";
const HEALTH_TIMEOUT_SECS: u64 = 4;
const POLL_INTERVAL_MS: u64 = 250;
const STARTUP_TIMEOUT_SECS: u64 = 10;

static BACKEND_CHILD: OnceLock<Mutex<Option<Child>>> = OnceLock::new();

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

/// Start the backend if not already healthy. Spawns process and polls /health for up to ~10s.
pub fn start_backend_if_needed() -> Result<(), String> {
    if check_health() {
        return Ok(());
    }

    let repo_root = repo_root_from_exe().ok_or_else(|| "Could not determine repo root (not running from target?)".to_string())?;
    let child = spawn_python_backend(&repo_root)?;

    {
        let mut guard = get_handle().lock().map_err(|e| e.to_string())?;
        if let Some(mut old) = guard.take() {
            let _ = old.kill();
        }
        *guard = Some(child);
    }

    let deadline = Instant::now() + Duration::from_secs(STARTUP_TIMEOUT_SECS);
    while Instant::now() < deadline {
        if check_health() {
            return Ok(());
        }
        std::thread::sleep(Duration::from_millis(POLL_INTERVAL_MS));
    }

    let mut guard = get_handle().lock().map_err(|e| e.to_string())?;
    if let Some(mut c) = guard.take() {
        let _ = c.kill();
    }
    Err("Backend did not become healthy within 10 seconds".to_string())
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
