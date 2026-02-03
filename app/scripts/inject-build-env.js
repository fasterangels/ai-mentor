import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Prefer the canonical script in app/frontend/scripts if it exists
const frontendScript = path.resolve(__dirname, "../frontend/scripts/inject-build-env.js");

if (existsSync(frontendScript)) {
  const r = spawnSync(process.execPath, [frontendScript], { stdio: "inherit" });
  process.exit(r.status ?? 1);
}

// Fallback: run frontend build with env injection (minimal)
function run(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { stdio: "inherit", ...opts });
  if (r.status !== 0) process.exit(r.status ?? 1);
}

let commit = "unknown";
try {
  const r = spawnSync("git", ["rev-parse", "--short", "HEAD"], { encoding: "utf8" });
  if (r.status === 0) commit = String(r.stdout).trim() || "unknown";
} catch {}

const build =
  process.env.GITHUB_RUN_NUMBER ||
  process.env.CI_BUILD_NUMBER ||
  process.env.BUILD_NUMBER ||
  new Date().toISOString();

// Run frontend build from app/frontend
const frontendDir = path.resolve(__dirname, "../frontend");
run("npm", ["run", "build"], {
  cwd: frontendDir,
  env: { ...process.env, VITE_COMMIT: commit, VITE_BUILD: String(build) },
});
