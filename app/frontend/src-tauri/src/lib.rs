// Desktop app: NO backend spawning. Backend runs as per-user Scheduled Task (AI_Mentor_Backend).
// API base is fixed: http://127.0.0.1:8000

use std::fs;
use std::io::Write;
use std::path::PathBuf;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

const LOCK_FILE_NAME: &str = "app.lock";
const APP_LOG_NAME: &str = "app.log";
const FIXED_API_BASE: &str = "http://127.0.0.1:8000";

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

#[tauri::command]
fn log_app_message(message: String) {
  app_log(&message);
}

#[tauri::command]
fn get_backend_base_url() -> Result<String, String> {
  Ok(FIXED_API_BASE.to_string())
}

#[tauri::command]
fn is_backend_ready() -> bool {
  true
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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  if let Err(e) = try_single_instance() {
    eprintln!("{}", e);
    std::process::exit(1);
  }

  tauri::Builder::default()
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_fs::init())
    .setup(|_app| {
      let build_id = std::env!("BUILD_ID");
      app_log(&format!("BUILD_ID={}", build_id));
      let exe_path = std::env::current_exe().unwrap_or_default();
      app_log(&format!("APP_START exe={} backend=Scheduled_Task fixed_url={}", exe_path.display(), FIXED_API_BASE));
      Ok(())
    })
    .invoke_handler(tauri::generate_handler![log_app_message, get_backend_base_url, is_backend_ready, run_backend_task])
    .on_window_event(|_window, event| {
      if let tauri::WindowEvent::CloseRequested { .. } = event {
        remove_lock();
      }
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
