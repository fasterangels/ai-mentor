/**
 * App version and build channel for UI (footer, about, logs).
 * Version from package.json via Vite __APP_VERSION__; build channel from __BUILD__.
 * Deterministic: no "unknown (dev)" — fallback version "0.0.0" with console warning if missing.
 */

const rawVersion =
  typeof __APP_VERSION__ !== "undefined" && __APP_VERSION__ !== ""
    ? __APP_VERSION__
    : null;

if (rawVersion == null || rawVersion === "") {
  if (typeof console !== "undefined" && console.warn) {
    console.warn("[version] __APP_VERSION__ missing or empty; using 0.0.0");
  }
}

/** Semantic version string (from package.json or tauri.conf.json at build time). */
export const appVersion: string = rawVersion ?? "0.0.0";

/** Build channel: "release" for Tauri production build, "dev" for Vite dev or standalone build. */
export const buildChannel: "dev" | "release" =
  typeof __BUILD__ !== "undefined" && String(__BUILD__).toLowerCase() === "release"
    ? "release"
    : "dev";

/** Short label for UI: "vX.Y.Z · dev" or "vX.Y.Z · release". */
export const versionDisplay: string = `v${appVersion} · ${buildChannel}`;
