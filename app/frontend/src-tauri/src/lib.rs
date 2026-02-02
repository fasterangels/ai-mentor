// Desktop app: optional backend sidecar auto-start in release only.
// API base is fixed: http://127.0.0.1:8000

use std::fs;
use tauri::Manager;
use std::io::Write;
use std::path::PathBuf;
use std::sync::Mutex;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

#[cfg(windows)]
use std::os::windows::process::CommandExt;

const LOCK_FILE_NAME: &str = "app.lock";
const APP_LOG_NAME: &str = "app.log";
const BACKEND_AUTOSTART_LOG_NAME: &str = "backend_autostart.log";
const FIXED_API_BASE: &str = "http://127.0.0.1:8000";
const HEALTH_URL: &str = "http://127.0.0.1:8000/health";
const HEALTH_POLL_MS: u64 = 250;
const HEALTH_TIMEOUT_MS: u64 = 10_000;

/// Windows CREATE_NO_WINDOW to avoid black console.
#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

fn local_app_data() -> PathBuf {
  std::env::var_os("LOCALAPPDATA")
    .map(PathBuf::from)
    .unwrap_or_else(|| std::env::var_os("USERPROFILE").map(PathBuf::from).unwrap_or_default())
}

fn app_base_dir() -> PathBuf {
  local_app_data().join("AI_Mentor")
}

fn logs_dir() -> PathBuf {
  app_base_dir().join("logs")
}

fn app_log_path() -> PathBuf {
  logs_dir().join(APP_LOG_NAME)
}

fn backend_autostart_log_path() -> PathBuf {
  logs_dir().join(BACKEND_AUTOSTART_LOG_NAME)
}

fn app_log(msg: &str) {
  let path = app_log_path();
  if let Some(parent) = path.parent() {
    let _ = fs::create_dir_all(parent);
  }
  let ts = SystemTime::now()
    .duration_since(UNIX_EPOCH)
    .map(|d| d.as_secs())
    .unwrap_or(0);
  if let Ok(mut f) = fs::OpenOptions::new().create(true).append(true).open(&path) {
    let _ = writeln!(f, "[{}] {}", ts, msg);
    let _ = f.flush();
  }
}

fn backend_autostart_log(msg: &str) {
  let path = backend_autostart_log_path();
  if let Some(parent) = path.parent() {
    let _ = fs::create_dir_all(parent);
  }
  let ts = SystemTime::now()
    .duration_since(UNIX_EPOCH)
    .map(|d| d.as_secs())
    .unwrap_or(0);
  if let Ok(mut f) = fs::OpenOptions::new().create(true).append(true).open(&path) {
    let _ = writeln!(f, "[{}] {}", ts, msg);
    let _ = f.flush();
  }
}

fn lock_file_path() -> PathBuf {
  app_base_dir().join("runtime").join(LOCK_FILE_NAME)
}

fn try_single_instance() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
  let lock_path = lock_file_path();
  if let Ok(meta) = fs::metadata(&lock_path) {
    if meta.is_file() {
      if let Ok(modified) = meta.modified() {
        let age = SystemTime::now()
          .duration_since(modified)
          .unwrap_or(Duration::from_secs(999));
        if age < Duration::from_secs(60) {
          return Err("Another instance is already running".into());
        }
      }
    }
  }
  if let Some(p) = lock_path.parent() {
    let _ = fs::create_dir_all(p);
  }
  fs::write(&lock_path, std::process::id().to_string())?;
  Ok(())
}

fn remove_lock() {
  let _ = fs::remove_file(lock_file_path());
}

/// Only auto-start backend in release build and when env AI_MENTOR_AUTOSTART_BACKEND != "0".
/// Set AI_MENTOR_AUTOSTART_BACKEND=0 to disable (default ON for release).
fn autostart_enabled() -> bool {
  if cfg!(debug_assertions) {
    return false;
  }
  match std::env::var("AI_MENTOR_AUTOSTART_BACKEND") {
    Ok(v) => v != "0",
    Err(_) => true,
  }
}

/// Backend process state: READY | STARTING | NOT_READY.
struct BackendStateInner {
  status: String,
  child: Option<std::process::Child>,
}

struct BackendState {
  inner: Mutex<BackendStateInner>,
}

impl Default for BackendState {
  fn default() -> Self {
    Self {
      inner: Mutex::new(BackendStateInner {
        status: "NOT_READY".to_string(),
        child: None,
      }),
    }
  }
}

fn open_append_log(path: &PathBuf) -> Option<std::fs::File> {
  if let Some(parent) = path.parent() {
    let _ = fs::create_dir_all(parent);
  }
  fs::OpenOptions::new()
    .create(true)
    .append(true)
    .open(path)
    .ok()
}

fn try_spawn_and_health(state: std::sync::Arc<BackendState>, exe_path: PathBuf, log_path: PathBuf) {
  backend_autostart_log("autostart: begin");
  let stdout_file = match open_append_log(&log_path) {
    Some(f) => f,
    None => {
      backend_autostart_log("autostart: failed to open log file");
      if let Ok(mut g) = state.inner.lock() {
        g.status = "NOT_READY".to_string();
      }
      return;
    }
  };
  let stderr_file = match open_append_log(&log_path) {
    Some(f) => f,
    None => {
      backend_autostart_log("autostart: failed to open log file (stderr)");
      if let Ok(mut g) = state.inner.lock() {
        g.status = "NOT_READY".to_string();
      }
      return;
    }
  };

  let mut cmd = std::process::Command::new(&exe_path);
  cmd.stdout(std::process::Stdio::from(stdout_file));
  cmd.stderr(std::process::Stdio::from(stderr_file));
  #[cfg(windows)]
  cmd.creation_flags(CREATE_NO_WINDOW);

  let child = match cmd.spawn() {
    Ok(c) => {
      backend_autostart_log("autostart: process spawned");
      c
    }
    Err(e) => {
      backend_autostart_log(&format!("autostart: spawn failed: {}", e));
      if let Ok(mut g) = state.inner.lock() {
        g.status = "NOT_READY".to_string();
      }
      return;
    }
  };

  {
    let mut g = state.inner.lock().unwrap();
    g.status = "STARTING".to_string();
    g.child = Some(child);
  }

  let deadline = SystemTime::now() + Duration::from_millis(HEALTH_TIMEOUT_MS);
  let client = reqwest::blocking::Client::builder()
    .timeout(Duration::from_millis(500))
    .build()
    .unwrap_or_default();

  while SystemTime::now() < deadline {
    if let Ok(res) = client.get(HEALTH_URL).send() {
      if res.status().is_success() {
        backend_autostart_log("autostart: health OK");
        if let Ok(mut g) = state.inner.lock() {
          g.status = "READY".to_string();
        }
        app_log("backend autostart: READY");
        return;
      }
    }
    std::thread::sleep(Duration::from_millis(HEALTH_POLL_MS));
  }

  backend_autostart_log("autostart: health timeout");
  if let Ok(mut g) = state.inner.lock() {
    g.status = "NOT_READY".to_string();
    g.child.take();
  }
  app_log("backend autostart: NOT_READY (timeout)");
}

#[tauri::command]
fn log_app_message(message: String) {
  app_log(&message);
}

#[tauri::command]
fn get_backend_base_url() -> Result<String, String> {
  Ok(FIXED_API_BASE.to_string())
}

#[tauri::command]
fn is_backend_ready(state: tauri::State<std::sync::Arc<BackendState>>) -> bool {
  let g = state.inner.lock().unwrap();
  g.status == "READY"
}

#[tauri::command]
fn get_backend_status(state: tauri::State<std::sync::Arc<BackendState>>) -> String {
  let g = state.inner.lock().unwrap();
  g.status.clone()
}

/// Retry backend start (spawn sidecar + health wait). Kills previous child if any.
#[tauri::command]
fn retry_backend_start(app: tauri::AppHandle, state: tauri::State<std::sync::Arc<BackendState>>) -> Result<(), String> {
  let exe_path = app
    .path()
    .resolve("bin/ai-mentor-backend.exe", tauri::path::BaseDirectory::Resource)
    .map_err(|e| format!("{:?}", e))?;
  let log_path = backend_autostart_log_path();

  let mut g = state.inner.lock().map_err(|e| e.to_string())?;
  if let Some(mut child) = g.child.take() {
    let _ = child.kill();
    g.status = "NOT_READY".to_string();
  }
  drop(g);

  let state_clone = state.inner().clone();
  std::thread::spawn(move || try_spawn_and_health(state_clone, exe_path, log_path));
  Ok(())
}

/// Ask Task Scheduler to run AI_Mentor_Backend task (Windows only). Does not spawn backend exe.
#[tauri::command]
fn run_backend_task() -> Result<(), String> {
  #[cfg(not(target_os = "windows"))]
  return Err("Windows only".to_string());
  #[cfg(target_os = "windows")]
  {
    std::process::Command::new("schtasks")
      .args(["/Run", "/TN", "AI_Mentor_Backend"])
      .status()
      .map_err(|e| e.to_string())?;
    Ok(())
  }
}

#[tauri::command]
fn get_backend_autostart_log_path() -> PathBuf {
  backend_autostart_log_path()
}

/// Open the logs folder in the system file manager (e.g. Explorer on Windows).
#[tauri::command]
fn open_logs_folder() -> Result<(), String> {
  let path = logs_dir();
  if let Some(parent) = path.parent() {
    let _ = fs::create_dir_all(parent);
  }
  #[cfg(target_os = "windows")]
  {
    std::process::Command::new("explorer")
      .args([path.as_os_str()])
      .status()
      .map_err(|e| e.to_string())?;
  }
  #[cfg(not(target_os = "windows"))]
  {
    let _ = path;
    return Err("Open logs folder is supported on Windows only".to_string());
  }
  Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  if let Err(e) = try_single_instance() {
    eprintln!("{}", e);
    std::process::exit(1);
  }

  let backend_state = std::sync::Arc::new(BackendState::default());

  tauri::Builder::default()
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_fs::init())
    .manage(backend_state.clone())
    .setup(|app| {
      let build_id = std::env!("BUILD_ID");
      app_log(&format!("BUILD_ID={}", build_id));
      let exe_path = std::env::current_exe().unwrap_or_default();
      app_log(&format!(
        "APP_START exe={} fixed_url={} autostart={}",
        exe_path.display(),
        FIXED_API_BASE,
        autostart_enabled()
      ));

      if autostart_enabled() {
        let state = app.try_state::<std::sync::Arc<BackendState>>().unwrap().inner().clone();
        let exe_path = app
          .path()
          .resolve("bin/ai-mentor-backend.exe", tauri::path::BaseDirectory::Resource)
          .ok();
        if let Some(path) = exe_path {
          let log_path = backend_autostart_log_path();
          std::thread::spawn(move || try_spawn_and_health(state, path, log_path));
        } else {
          app_log("backend autostart: exe not found (resource), NOT_READY");
          if let Some(s) = app.try_state::<std::sync::Arc<BackendState>>() {
            if let Ok(mut g) = s.inner().inner.lock() {
              g.status = "NOT_READY".to_string();
            }
          }
        }
      }

      Ok(())
    })
    .invoke_handler(tauri::generate_handler![
      log_app_message,
      get_backend_base_url,
      is_backend_ready,
      get_backend_status,
      retry_backend_start,
      run_backend_task,
      get_backend_autostart_log_path,
      open_logs_folder,
    ])
    .on_window_event(|_window, event| {
      if let tauri::WindowEvent::CloseRequested { .. } = event {
        remove_lock();
      }
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
