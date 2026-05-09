# Publishing Guide

How to set up DnD Offline Pro on Hugging Face Spaces and itch.io from scratch.
Assumes no existing accounts on either platform.

---

## Part 1 — Hugging Face Spaces (web demo)

This takes about 15 minutes. It gives you a live browser demo to link everywhere.

### Step 1 — Create a Hugging Face account

1. Open https://huggingface.co/join in your browser
2. Enter a **username** (this will appear in your Space URL — use `gokulrajanpillai` to match GitHub)
3. Enter your email and a password
4. Click **Create account**
5. Check your email and click the verification link

### Step 2 — Create an access token

1. Go to https://huggingface.co/settings/tokens
2. Click **New token**
3. Name it `dnd-deploy`, set Role to **Write**, click **Create**
4. **Copy the token** (starts with `hf_...`) — you only see it once

### Step 3 — Deploy the Space with the script

Open your terminal in the project root and run:

```bash
# Activate your virtualenv first
source .venv312/bin/activate

# Log in (paste your token when prompted)
huggingface-cli login

# Deploy
python scripts/deploy_hf_space.py
```

The script will:
- Confirm your username
- Create the Space `gokulrajanpillai/DnDOfflinePro-Demo`
- Upload `spaces/app.py`, `requirements.txt`, and `README.md`
- Print the live URL when done

### Step 4 — Verify the Space

1. Open the URL printed by the script (format: `https://huggingface.co/spaces/gokulrajanpillai/DnDOfflinePro-Demo`)
2. The Space will show **"Building"** for 3–5 minutes while it installs dependencies and downloads the model (~1 GB)
3. Once it shows the Gradio UI, type an action and confirm generation works
4. If it shows an error, click **Logs** (top right of the Space) to see what failed

### Step 5 — Add the Space URL to the README

Open `README.md` and replace:

```markdown
<!-- TODO: Replace this block with a demo.gif once recorded
![Demo](assets/demo.gif)
-->
```

with:

```markdown
**[Try the web demo →](https://huggingface.co/spaces/gokulrajanpillai/DnDOfflinePro-Demo)**
```

(You can swap this for the GIF later — see [demo-gif-guide.md](demo-gif-guide.md))

---

## Part 2 — itch.io (game distribution + monetisation)

This takes about 20 minutes. It gives you a public game page with pay-what-you-want pricing.

### Step 1 — Create an itch.io account

1. Open https://itch.io/register in your browser
2. Fill in:
   - **Username:** `gokulrajanpillai` (matches GitHub)
   - **Email:** your email
   - **Password:** strong password
3. Click **Create account**
4. Check your email and verify

### Step 2 — Create a new project

1. Go to https://itch.io/game/new
2. You land on the project editor. Fill in the fields **exactly** as below.

---

**Title:**
```
DnD Offline Pro
```

**Project URL** (auto-filled, adjust if taken):
```
dnd-offline-pro
```

**Short description / tagline:**
```
Fully offline AI dungeon master. No internet. No subscription. Runs on any CPU.
```

**Kind of project:** select **Downloadable**

**Classification:** select **Game**

**Genre:** select **Interactive Fiction**

---

**Description** (paste the full block below into the text editor — it supports plain text):

```
DnD Offline Pro is an AI-powered dungeon narrator that runs entirely on your machine.
No API key. No subscription. No data sent anywhere. Download it once and play forever,
completely offline.

You type what you do. The AI narrates what happens. It remembers the last few turns
so the story stays coherent. That's the whole thing.

── FEATURES ──

• 100% offline after the one-time model download (~1 GB)
• No GPU required — runs on any modern CPU
• Three starting scenarios: dungeon, tavern, wilderness
• Save your session and resume later
• Open source — Apache 2.0

── HOW TO PLAY ──

1. Download and extract the ZIP for your platform
2. Run DnDOfflinePro.bin (Linux) — or python src/dnd_offline.py from source
3. On first run: downloads the AI model (~1 GB, one-time only, needs internet)
4. After that: fully offline, play as long as you like

── WEB DEMO ──

Try it in your browser before downloading:
https://huggingface.co/spaces/gokulrajanpillai/DnDOfflinePro-Demo

── SOURCE ──

Core engine is open source at:
https://github.com/gokulrajanpillai/DnDOfflinePro
```

---

**Tags** (enter each one separately in the Tags field):
```
text-adventure
ai
dungeon
rpg
offline
privacy
fantasy
interactive-fiction
local-ai
```

---

**Pricing:** Select **No payments** for now, then change to **Paid** and set:
- Minimum price: **$0** (free)
- Suggested price: **$5**
- Check **Allow any amount above minimum**

This is "pay what you want" — anyone can download for free, but itch.io shows a
suggested price and many people pay it.

---

**Uploads:** (see Step 3 below before saving)

**Visibility:** Set to **Draft** for now — you'll publish after uploading the build

Click **Save & view page** at the bottom.

---

### Step 3 — Package and upload the build

Back in your terminal:

```bash
bash scripts/package_release.sh 0.2.0
```

This creates `release/DnDOfflinePro-v0.2.0-linux.zip`.

Back on the itch.io project editor:
1. Under **Uploads**, click **Upload files**
2. Select `release/DnDOfflinePro-v0.2.0-linux.zip`
3. After upload, tick the **Linux** checkbox under the file
4. Click **Save**

### Step 4 — Add a cover image

itch.io shows a 315×250 px cover image in search results. Without one, your page looks
unfinished and gets fewer clicks.

Quick option (no design skills needed):
1. Go to https://www.canva.com (free account)
2. Create a design at 315×250 px (File → Custom size)
3. Dark background, large text: "DnD Offline Pro", subtitle: "Offline AI Dungeon Master"
4. Export as PNG, upload to itch.io under **Cover image**

### Step 5 — Publish

1. Back on the project editor, change **Visibility** from Draft to **Public**
2. Click **Save & view page**
3. Your page is live at `https://gokulrajanpillai.itch.io/dnd-offline-pro`

### Step 6 — Add the itch.io link to your GitHub README

Open `README.md` and add under the Support section:

```markdown
- [Download on itch.io](https://gokulrajanpillai.itch.io/dnd-offline-pro)
```

---

## Part 3 — Future uploads (butler CLI)

After the first page is created, use itch.io's `butler` CLI for subsequent builds:

```bash
# Install butler (one-time)
brew install --cask butler         # macOS
# or download from https://itchio.itch.io/butler

# Push a new build
butler push release/DnDOfflinePro-v0.3.0-linux.zip \
  gokulrajanpillai/dnd-offline-pro:linux
```

This lets you update the download without touching the itch.io web UI.

---

## Checklist

- [ ] Hugging Face account created and verified
- [ ] Space deployed — URL working
- [ ] itch.io account created and verified
- [ ] itch.io game page created (all fields filled)
- [ ] Build ZIP uploaded and Linux checkbox ticked
- [ ] Cover image uploaded
- [ ] Page published (Visibility → Public)
- [ ] HF Spaces URL added to README.md
- [ ] itch.io URL added to README.md Support section
- [ ] Community posts ready to go (Show HN, r/LocalLLaMA) — see previous phase notes
