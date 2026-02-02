/**
 * Build-time info injected by Vite define (dev: build=dev, commit=unknown).
 * Formatted string: v<version>+<commit> (<build>).
 */
const build: string = typeof __BUILD__ !== "undefined" ? __BUILD__ : "dev"
const commit: string = typeof __COMMIT__ !== "undefined" ? __COMMIT__ : "unknown"
const appVersion: string = typeof __APP_VERSION__ !== "undefined" ? __APP_VERSION__ : "0.0.0"

/** Single line for UI: e.g. v0.3.1+abc1234 (2025-02-01T12:00:00Z) or v0.3.1+unknown (dev) */
export const buildInfoFormatted = `v${appVersion}+${commit} (${build})`

export { build, commit }
