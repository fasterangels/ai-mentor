/**
 * Build-time info for UI and logs.
 * Version and display string come from version.ts (package.json + build channel).
 * buildInfoFormatted is the short UI string: "vX.Y.Z · dev" | "vX.Y.Z · release".
 */

import { appVersion, buildChannel, versionDisplay } from "./version";

export { appVersion, buildChannel } from "./version";

/** Single line for UI (footer, about): e.g. "v0.3.9 · dev" or "v0.3.9 · release". */
export const buildInfoFormatted = versionDisplay;

/** @deprecated Use buildChannel; kept for compatibility. */
export const build: string = buildChannel;

/** Commit hash when set at build time (e.g. by inject-build-env); not shown in UI. */
export const commit: string =
  typeof __COMMIT__ !== "undefined" ? __COMMIT__ : "";
