/** HTTP client for backend (fetch). In Tauri desktop, base URL comes from backend_port.json.
 * No fetch allowed before backend_ready. */

import { getBackendBaseUrlSync, requireBackendReady } from "./backendBaseUrl";

function getBase(): string {
  requireBackendReady();
  return getBackendBaseUrlSync();
}

export async function getHealth(): Promise<{ status: string }> {
  const res = await fetch(`${getBase()}/health`, { method: "GET" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export function getBaseUrl(): string {
  return getBase();
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${getBase()}${path}`, { method: "GET" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Forbidden path: UI must not call deprecated analyze endpoint. */
const FORBIDDEN_ANALYZE_PATH = "/api/v1/analyze";

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  if (normalized.includes(FORBIDDEN_ANALYZE_PATH)) {
    throw new Error("Not supported: /api/v1/analyze. Use /pipeline/shadow/run.");
  }
  const res = await fetch(`${getBase()}${normalized}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
