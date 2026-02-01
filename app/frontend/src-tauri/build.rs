fn main() {
    let build_id = std::env::var("VITE_BUILD_ID").unwrap_or_else(|_| "UNKNOWN_BUILD".to_string());
    println!("cargo:rustc-env=BUILD_ID={}", build_id);
    tauri_build::build()
}
