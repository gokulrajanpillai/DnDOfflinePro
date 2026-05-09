# Release Process

Everything that happens automatically and everything you need to do manually,
in order.

---

## One-time setup — GitHub secrets and variables

Go to **github.com/gokulrajanpillai/DnDOfflinePro → Settings → Secrets and variables → Actions**.

### Repository secrets (`Secrets` tab → `New repository secret`)

| Secret name | Where to get it | Required for |
|---|---|---|
| `HF_TOKEN` | huggingface.co/settings/tokens (Write token) | HF Spaces deploy |
| `BUTLER_API_KEY` | itch.io → Account → API keys (see below) | itch.io deploy |
| `REDDIT_CLIENT_ID` | reddit.com/prefs/apps → create app (see below) | Reddit announcements |
| `REDDIT_CLIENT_SECRET` | same Reddit app | Reddit announcements |
| `REDDIT_USERNAME` | your Reddit username | Reddit announcements |
| `REDDIT_PASSWORD` | your Reddit password | Reddit announcements |

### Repository variables (`Variables` tab → `New repository variable`)

| Variable name | Value |
|---|---|
| `HF_USERNAME` | `gokulrajanpillai` |
| `ITCH_USER` | `gokulrajanpillai` |
| `ITCH_GAME` | `dnd-offline-pro` |

---

## Getting the butler API key (itch.io)

1. Log in to itch.io
2. Go to **itch.io/user/settings/api-keys**
3. Click **Generate new API key**
4. Copy the key and save it as `BUTLER_API_KEY` in GitHub Secrets

---

## Getting Reddit API credentials

1. Log in to Reddit
2. Go to **reddit.com/prefs/apps**
3. Click **Create another app** at the bottom
4. Fill in:
   - **Name:** `DnDOfflinePro announce`
   - **Type:** select **script**
   - **Redirect URI:** `http://localhost:8080`
5. Click **Create app**
6. You'll see a box with two values:
   - Under the app name (looks like a random string) → `REDDIT_CLIENT_ID`
   - **secret** field → `REDDIT_CLIENT_SECRET`

> **Note:** Reddit posts are optional. If the four `REDDIT_*` secrets are not set,
> the announce workflow outputs the formatted post to the workflow summary instead
> of posting automatically. You can always add Reddit credentials later.

---

## Automations at a glance

| Trigger | What runs automatically |
|---|---|
| Push to `main` with changes in `spaces/` | `deploy-spaces.yml` — updates the HF Spaces demo |
| Push a tag `v*.*.*` | `release.yml` — creates draft GitHub Release + deploys HF Spaces |
| GitHub Release **published** | `deploy-itch.yml` — pushes binary ZIP to itch.io |
| GitHub Release **published** | `announce.yml` — posts to Reddit + generates HN URL in summary |

---

## How to cut a release

### Step 1 — Tag the release

```bash
git tag v0.2.0
git push origin v0.2.0
```

This immediately triggers `release.yml`, which:
- Creates a **draft** GitHub Release named "DnD Offline Pro v0.2.0"
- Deploys the latest `spaces/` to HF Spaces
- Prints the next steps in the workflow summary

### Step 2 — Build and package the binary

On your local machine:

```bash
# Build with Nuitka (if you have a new version)
python -m nuitka --onefile src/dnd_offline.py   # adjust flags as needed

# Package into a release ZIP
bash scripts/package_release.sh 0.2.0
# Output: release/DnDOfflinePro-v0.2.0-linux.zip
```

> If the code hasn't changed significantly and the existing binary is still valid,
> skip the Nuitka build and just re-run the packaging script.

### Step 3 — Attach the binary to the draft release

```bash
gh release upload v0.2.0 release/DnDOfflinePro-v0.2.0-linux.zip
```

### Step 4 — Publish the release

```bash
gh release edit v0.2.0 --draft=false
```

Publishing triggers both:
- `deploy-itch.yml` — downloads the ZIP from the release and pushes to itch.io via butler
- `announce.yml` — posts to Reddit (if credentials set) + generates HN link

### Step 5 — Open the HN submission

After the `announce` workflow completes:
1. Go to the workflow run in the Actions tab
2. Open the **Post announcements** step summary
3. Click the pre-filled HN link (URL + title are pre-filled)
4. Paste the HN body text from the summary into the "text" field
5. Submit

---

## Manual re-deploy (without a release)

**Re-deploy HF Spaces only:**

Go to Actions → "Deploy HF Spaces" → Run workflow → main branch

**Post announcements manually (e.g. for a different community):**

Go to Actions → "Announce Release" → Run workflow → fill in version, HF URL, itch URL

---

## Versioning convention

Tags follow `vMAJOR.MINOR.PATCH`:

| Change | Bump |
|---|---|
| New scenario, minor feature, bug fix | PATCH (`v0.2.0` → `v0.2.1`) |
| New flag, new built-in scenario set, UI change | MINOR (`v0.2.0` → `v0.3.0`) |
| Desktop GUI, major architecture change | MAJOR (`v0.x.x` → `v1.0.0`) |
