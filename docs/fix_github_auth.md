# Fix GitHub auth (Git HTTPS + gh CLI)

Restore credentials so that:
1. **Git over HTTPS** works (no `SEC_E_NO_CREDENTIALS`).
2. **GitHub CLI (`gh`)** works for PR creation and checks.

---

## Step 1: Log in to GitHub via gh (do this first)

In a terminal (PowerShell or CMD) where you can interact with prompts:

```powershell
cd C:\ai-mentor-repo
gh auth login
```

When prompted:
- **What account do you want to log into?** → **GitHub.com**
- **What is your preferred protocol for Git operations?** → **HTTPS**
- **Authenticate Git with your GitHub credentials?** → **Yes**
- **How would you like to authenticate?** → **Login with a web browser** (recommended), or paste a token if you use one.

Complete the browser or token flow. When it says "Logged in as ...", continue.

---

## Step 2: Ensure gh is authenticated

```powershell
gh auth status
```

You should see: `Logged in to github.com as <username>`.

---

## Step 3: Configure Git to use gh as credential helper

```powershell
gh auth setup-git
```

This makes Git use `gh` for HTTPS credentials so `git push` / `git fetch` stop asking and stop failing with `SEC_E_NO_CREDENTIALS`.

---

## Step 4: Verify Git can talk to origin

```powershell
git remote get-url origin
git ls-remote --heads origin
```

- `git remote get-url origin` should show: `https://github.com/fasterangels/ai-mentor.git`
- `git ls-remote --heads origin` should list branches (no `SEC_E_NO_CREDENTIALS` error).

---

## Step 5: Verify PR operations

```powershell
gh repo view --json nameWithOwner,defaultBranchRef
gh pr list --state open --limit 5
```

Both should run without auth errors.

---

## Optional: End-to-end sanity check

Create a small test branch, push, and open a PR:

```powershell
git checkout -b auth-sanity-check
echo "auth sanity" >> docs/_auth_sanity_check.txt
git add -A
git commit -m "Chore: auth sanity check"
git push -u origin auth-sanity-check
gh pr create --title "Chore: auth sanity check" --body "Auth pipeline verification." --base main
gh pr checks --watch
```

---

## Using a token without browser (CI / script)

If you have a Personal Access Token (e.g. `GH_TOKEN`):

```powershell
$env:GH_TOKEN = "your_token_here"
echo $env:GH_TOKEN | gh auth login --with-token
gh auth setup-git
```

Then run Step 4 and 5 to verify.

---

## Definition of done

- `gh auth status` shows **logged in**.
- `git ls-remote origin` works (no **SEC_E_NO_CREDENTIALS**).
- `gh pr` commands work.
