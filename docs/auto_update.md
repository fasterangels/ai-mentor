# Tauri Auto-Update (Desktop)

This document describes how to set up and release updates for the AI Mentor desktop app (Tauri) so that the client can auto-update silently.

## Required secrets (do not commit)

- **`TAURI_SIGNING_PRIVATE_KEY`** — The private key used to sign update artifacts. Set this in **GitHub Actions → Settings → Secrets and variables → Actions**. Without it, the release workflow cannot sign installers and `latest.json` will be invalid for the updater.
- **`TAURI_SIGNING_PRIVATE_KEY_PASSWORD`** — (Optional) If you protected the private key with a password when generating it, set this secret as well.

## Generating signing keys

1. From the repo root (or `app/frontend`), generate a key pair:

   ```bash
   cd app/frontend
   pnpm exec tauri signer generate --write-keys ~/.tauri/ai-mentor.key
   ```

   This creates:
   - `~/.tauri/ai-mentor.key` — **private key** (keep secret, never commit).
   - `~/.tauri/ai-mentor.key.pub` — **public key** (safe to commit). Paste its contents into `app/frontend/src-tauri/tauri.conf.json` → `plugins.updater.pubkey`, replacing the placeholder.

2. **Where to set GitHub Secrets**
   - Repo → **Settings** → **Secrets and variables** → **Actions**.
   - Add **New repository secret**:
     - Name: `TAURI_SIGNING_PRIVATE_KEY`
     - Value: paste the **entire contents** of `ai-mentor.key` (or the path to the key file if your workflow reads from a file).
   - If you used a password: add `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` with that password.

3. The **public key** is committed in `app/frontend/src-tauri/tauri.conf.json` under `plugins.updater.pubkey`. The client uses it to verify update signatures; only the private key stays in GitHub Secrets.

## Creating a release that produces latest.json and signed artifacts

1. **Tag a version** (e.g. `v0.3.10`):
   ```bash
   git tag v0.3.10
   git push origin v0.3.10
   ```

2. The **Release Tauri** workflow (`.github/workflows/release-tauri.yml`) runs on:
   - Push of tags matching `v*`
   - Or manual **workflow_dispatch** from the Actions tab.

3. The workflow will:
   - Check out the repo, set up Node (frontend), Rust, and optionally Python/backend.
   - Build the Tauri app with `TAURI_SIGNING_PRIVATE_KEY` (and optional password) set so that installers and `.sig` files are produced.
   - Generate `latest.json` pointing at the release assets and include the signature from the `.sig` file.
   - Create (or update) the GitHub Release for that tag and upload:
     - Installer artifacts (e.g. NSIS `.exe`, MSI).
     - `latest.json` (so that `https://github.com/fasterangels/ai-mentor/releases/latest/download/latest.json` serves it for the latest release).

4. The desktop client is configured to check:
   `https://github.com/fasterangels/ai-mentor/releases/latest/download/latest.json`
   on startup (silent, no dialog). If an update is available, it downloads, installs, and restarts.

## Generating latest.json locally (validation)

To produce `latest.json` from built artifacts (e.g. for testing or local validation):

```bash
cd app/frontend
node scripts/generate-latest-json.js --version 0.3.9 --tag v0.3.9 --nsis-sig path/to/AI-Mentor-0.3.9-x64-setup.exe.sig --out latest.json
```

See `app/frontend/scripts/generate-latest-json.js` for the exact arguments (`--version`, `--tag`, `--nsis-sig`, `--out`). The script is deterministic given the same inputs.
