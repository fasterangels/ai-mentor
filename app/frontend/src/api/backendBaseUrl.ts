/**
 * Backend base URL: fixed http://127.0.0.1:8000 in desktop (backend runs as per-user Scheduled Task).
 * In browser/dev mode same default. No spawn; backend is expected to be running.
 */

const DEFAULT_BASE_URL = "http://127.0.0.1:8000";

let cachedBaseUrl: string | null = null;

export function getDefaultBaseUrl(): string {
  return DEFAULT_BASE_URL;
}

/**
 * Returns true if the app is running inside Tauri (desktop).
 */
export function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI__" in window;
}

/** In desktop mode backend is the Scheduled Task; we always allow fetch (task may be down). */
export function isBackendReady(): boolean {
  return true;
}

/** No-op; kept for API compatibility. */
export function setBackendReady(_ready: boolean): void {}

/** No-op; backend is always "ready" to attempt fetch. */
export function requireBackendReady(): void {}

/**
 * Get backend base URL. Always http://127.0.0.1:8000 in desktop; same in browser unless overridden.
 */
export async function getBackendBaseUrl(): Promise<string> {
  if (cachedBaseUrl) return cachedBaseUrl;
  if (!isTauri()) {
    cachedBaseUrl = DEFAULT_BASE_URL;
    return cachedBaseUrl;
  }
  const { invoke } = await import("@tauri-apps/api/core");
  const baseUrl = await invoke<string>("get_backend_base_url");
  cachedBaseUrl = baseUrl && typeof baseUrl === "string" ? baseUrl : DEFAULT_BASE_URL;
  return cachedBaseUrl;
}

/**
 * Ensure base URL is resolved (for use by API client).
 */
export function ensureBackendBaseUrl(): Promise<string> {
  if (cachedBaseUrl) return Promise.resolve(cachedBaseUrl);
  return getBackendBaseUrl();
}

/**
 * Synchronous fallback. Returns cached URL or default.
 */
export function getBackendBaseUrlSync(): string {
  return cachedBaseUrl ?? DEFAULT_BASE_URL;
}
