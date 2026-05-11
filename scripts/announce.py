#!/usr/bin/env python3
"""
Post release announcements across all distribution channels.

CI usage (called by announce.yml):
    VERSION=0.2.0 HF_URL=https://... ITCH_URL=https://... \\
    REDDIT_CLIENT_ID=xxx REDDIT_CLIENT_SECRET=xxx \\
    REDDIT_USERNAME=xxx REDDIT_PASSWORD=xxx \\
    python scripts/announce.py

Local dry-run (no credentials needed):
    VERSION=0.2.0 HF_URL=https://... ITCH_URL=https://... \\
    python scripts/announce.py --dry-run
"""

import argparse
import os
import sys
import time
import urllib.parse

GITHUB_URL = "https://github.com/gokulrajanpillai/DnDOfflinePro"


# ── Reddit posts (one unique angle per subreddit) ─────────────────────────────

REDDIT_POSTS = {
    "LocalLLaMA": {
        "title": (
            "I built an offline D&D dungeon master using Qwen2.5 — "
            "v{version} now on itch.io [GitHub]"
        ),
        "body": """\
After seeing what AI Dungeon charges for a subscription, I built a text-based \
D&D narrator that runs 100% locally.

**Stack:** Python + Hugging Face Transformers + Qwen2.5-0.5B-Instruct
**Inference:** CPU only, `device=-1`. ~15–30s per turn on a modern CPU.
**No network calls** after the initial model download.

The prompt engineering is minimal: one system rule ("write one vivid paragraph, \
second person, fantasy tone, end with a hook") plus the last 3 narrator turns \
in chat history. Tried including all turns but it degraded coherence — the model \
would start echoing player actions.

**What's new in v{version}:**
- `--scenario` flag: dungeon / tavern / wilderness or custom JSON files
- `--save` / `--load`: persist and resume sessions
- `--model`: swap any local Hugging Face causal LM
- HP tracking + difficulty selector in the web UI

Web demo (runs in browser): {hf_url}
Download (offline, no API key): {itch_url}
Source (Apache 2.0): {github_url}

Has anyone tried Phi-3.5-mini-instruct for creative writing tasks like this? \
Curious how the instruction-following holds up at the fantasy narrator persona \
compared to Qwen2.5-0.5B.
""",
    },

    "DnD": {
        "title": (
            "I made a free AI Dungeon Master that runs 100% offline — "
            "no subscription, no API key [v{version}]"
        ),
        "body": """\
Tired of paying subscriptions for AI dungeon-mastering apps, I built my own that \
runs entirely on your machine after a one-time model download (~1 GB).

**What it does:**
- Acts as a text-based D&D narrator: you type your action, it responds with \
one vivid paragraph of second-person fantasy
- Tracks HP and adapts tone when your character is hurt
- Easy/Normal/Hard difficulty that changes how often actions succeed or backfire
- Three starting scenarios: dungeon, tavern, wilderness — or write your own \
scenario file

**What it needs:**
- Python 3.10+ and ~2 GB RAM (no GPU required)
- One-time internet connection to download the model; fully offline after that

Web preview (cloud, no install): {hf_url}
Download / itch.io page: {itch_url}
Source on GitHub (Apache 2.0 — free forever): {github_url}

Happy to answer questions about the prompting setup or how it handles combat!
""",
    },

    "rpg": {
        "title": (
            "DnD Offline Pro v{version} — free, open-source AI narrator "
            "that runs on your CPU with no internet"
        ),
        "body": """\
Built a text-based RPG narrator powered by a small local language model. \
No subscription, no cloud, no data sent anywhere — everything runs on your \
machine after a one-time model download.

**Gameplay loop:**
1. Choose a scenario (dungeon, tavern, wilderness, or custom)
2. Pick your class (Fighter, Rogue, Wizard, Cleric, Ranger, Bard, Paladin, Druid)
3. Type your action — the narrator responds with a vivid paragraph
4. Your HP and difficulty level shape how the story unfolds

**v{version} highlights:**
- Web UI (Gradio) for browser-based play
- CLI mode with a two-panel Rich layout
- HP bar updates live, difficulty affects outcomes
- Save/load sessions to JSON

Try in browser (no install): {hf_url}
Download for offline use: {itch_url}
Code: {github_url}

Works best with Qwen2.5-0.5B-Instruct (default, ~1 GB). \
You can swap in any local Hugging Face causal LM.
""",
    },

    "SideProject": {
        "title": (
            "I shipped an open-source offline AI dungeon master — "
            "v{version} on itch.io + HF Spaces [Show and Tell]"
        ),
        "body": """\
**What:** A text-based D&D narrator that runs entirely on your CPU — \
no API key, no subscription, no data sent anywhere.

**Stack:** Python · Hugging Face Transformers · Qwen2.5-0.5B-Instruct · \
Gradio (web UI) · PyQt6 (desktop GUI) · Rich (CLI)

**Business model:** Open core — Apache 2.0 engine, premium campaign packs \
planned as paid add-ons on itch.io. The core stays free.

**Distribution:**
- Web demo on HF Spaces: {hf_url}
- Source download on itch.io: {itch_url}
- GitHub (releases, issues): {github_url}

**CI/CD:** GitHub Actions auto-deploys to both HF Spaces and itch.io on every \
push to main. Release tags create a GitHub Release draft and trigger \
announcement scripts (Reddit, HN link, Product Hunt template).

**What I learned:** Keeping only the last 3 *narrator* turns (not player actions) \
in context window dramatically improved narrative coherence at 0.5B parameters. \
Rolling context > full context for creative writing at small model sizes.

Happy to talk architecture, prompt engineering, or the open-core monetisation plan.
""",
    },
}


# ── Hacker News ───────────────────────────────────────────────────────────────

def build_hn_url(version: str, hf_url: str) -> str:
    title = f"Show HN: DnD Offline Pro v{version} – offline AI dungeon master, runs on CPU"
    return (
        f"https://news.ycombinator.com/submitlink"
        f"?u={urllib.parse.quote(hf_url)}"
        f"&t={urllib.parse.quote(title)}"
    )


def build_hn_body(version: str, hf_url: str, itch_url: str) -> str:
    return f"""\
I built an interactive D&D narrator that runs entirely on your machine — no API \
key, no subscription, no internet after the initial model download.

Demo: {hf_url}
Download: {itch_url}
Source: {GITHUB_URL}

It uses Qwen2.5-0.5B-Instruct via Hugging Face Transformers (~1 GB, CPU only). \
Generation takes 15–30 seconds per turn on a modern CPU.

Key prompt engineering decision: rolling 3-turn narrator history (narrator \
responses only, not player actions). This preserved narrative voice while \
staying within the model's effective context length at 0.5B parameters.

v{version} adds HP tracking, difficulty levels, a PyQt6 desktop GUI, and \
a Gradio web UI. The CLI uses Rich's Layout for a two-panel narrator/character-sheet view.

Apache 2.0. Core engine stays open source. Premium campaign packs planned as \
paid itch.io add-ons.
"""


# ── Product Hunt ──────────────────────────────────────────────────────────────

def build_ph_update(version: str, hf_url: str, itch_url: str) -> str:
    return f"""\
🎲 DnD Offline Pro v{version} is live!

What's new:
• HP tracking — your character's health affects the narrator's tone
• Difficulty selector (Easy / Normal / Hard) — controls how often actions fail
• Gradio web UI — play in a browser with no install
• PyQt6 desktop app — native windowed experience
• CLI two-panel layout — story on the left, character sheet on the right

Try the web demo (no download needed): {hf_url}
Download for 100% offline play: {itch_url}

Still fully local, no subscription, no API key. One ~1 GB model download and
you're playing forever offline on any modern CPU.
"""


# ── Reddit posting ────────────────────────────────────────────────────────────

def post_to_reddit(subreddit: str, title: str, body: str) -> str:
    try:
        import praw
    except ImportError:
        print("praw not installed. Run: pip install praw")
        sys.exit(1)

    reddit = praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        username=os.environ["REDDIT_USERNAME"],
        password=os.environ["REDDIT_PASSWORD"],
        user_agent=f"DnDOfflinePro/announce by u/{os.environ['REDDIT_USERNAME']}",
    )
    submission = reddit.subreddit(subreddit).submit(title=title, selftext=body)
    return f"https://reddit.com{submission.permalink}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print all posts without submitting anything")
    args = parser.parse_args()

    version  = os.environ.get("VERSION", "")
    hf_url   = os.environ.get("HF_URL", "")
    itch_url = os.environ.get("ITCH_URL", "")

    if not version:
        print("VERSION env var required (e.g. VERSION=0.2.0)")
        sys.exit(1)

    gha_summary = os.environ.get("GITHUB_STEP_SUMMARY")

    def out(text: str = ""):
        if gha_summary:
            with open(gha_summary, "a") as f:
                f.write(text + "\n")
        else:
            print(text)

    has_reddit = all(
        os.environ.get(k)
        for k in ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET",
                  "REDDIT_USERNAME", "REDDIT_PASSWORD"]
    )

    # ── Hacker News ──────────────────────────────────────────────────────────
    hn_url  = build_hn_url(version, hf_url)
    hn_body = build_hn_body(version, hf_url, itch_url)

    out("## Hacker News")
    out()
    out(f"**[Click to open pre-filled submission]({hn_url})**")
    out("_(URL + title pre-filled — paste the body below into the text field)_")
    out()
    out("```")
    out(hn_body)
    out("```")
    out()

    # ── Product Hunt ─────────────────────────────────────────────────────────
    ph_update = build_ph_update(version, hf_url, itch_url)

    out("## Product Hunt")
    out()
    out("Post a new update on your registered product page — copy/paste this:")
    out()
    out("```")
    out(ph_update)
    out("```")
    out()

    # ── Reddit ───────────────────────────────────────────────────────────────
    out("## Reddit")
    out()

    for sub, config in REDDIT_POSTS.items():
        title = config["title"].format(version=version)
        body  = config["body"].format(
            version=version, hf_url=hf_url,
            itch_url=itch_url, github_url=GITHUB_URL,
        )

        out(f"### r/{sub}")
        out()

        if args.dry_run or not has_reddit:
            out(f"**Title:** {title}")
            out()
            out("**Body:**")
            out("```")
            out(body)
            out("```")
            out()
        else:
            print(f"Posting to r/{sub}...")
            try:
                url = post_to_reddit(sub, title, body)
                out(f"✅ Posted: {url}")
                print(f"r/{sub} live: {url}")
                # Space posts to avoid rate limits
                time.sleep(10)
            except Exception as e:
                out(f"⚠️ r/{sub} failed: {e}")
                print(f"r/{sub} error: {e}", file=sys.stderr)
            out()


if __name__ == "__main__":
    main()
