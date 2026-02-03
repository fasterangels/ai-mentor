#!/usr/bin/env node
/**
 * Sets VITE_COMMIT and VITE_BUILD then runs the frontend build.
 * Used by Tauri beforeBuildCommand. Works on Windows (PowerShell/cmd) and Unix.
 */
import { execSync, spawnSync } from "child_process";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
let commit = "unknown";
try {
  commit = execSync("git rev-parse --short HEAD", {
    encoding: "utf-8",
    cwd: root,
  }).trim();
} catch {
  // no git or not a repo
}

const build =
  process.env.GITHUB_RUN_NUMBER ||
  process.env.CI_BUILD_NUMBER ||
  process.env.BUILD_NUMBER ||
  new Date().toISOString();

process.env.VITE_COMMIT = commit;
process.env.VITE_BUILD = "release";
process.env.VITE_BUILD_ID = String(build);

const result = spawnSync("npm", ["run", "build"], {
  cwd: root,
  stdio: "inherit",
  env: process.env,
  shell: true,
});

process.exit(result.status ?? 1);
