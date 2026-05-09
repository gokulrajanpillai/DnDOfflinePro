#!/usr/bin/env python3
"""
Post release announcements to Reddit (r/LocalLLaMA) and generate a
pre-filled Hacker News submission URL.

CI usage (called by announce.yml):
    VERSION=0.2.0 HF_URL=https://... ITCH_URL=https://... \\
    REDDIT_CLIENT_ID=xxx REDDIT_CLIENT_SECRET=xxx \\
    REDDIT_USERNAME=xxx REDDIT_PASSWORD=xxx \\
    python scripts/announce.py

Local usage (dry-run, no credentials needed):
    VERSION=0.2.0 HF_URL=https://... ITCH_URL=https://... \\
    python scripts/announce.py --dry-run
"""

import argparse
import os
import sys
import urllib.parse


def build_reddit_post(version: str, hf_url: str, itch_url: str) -> tuple[str, str]:
    title = (
        f"I built an offline D&D dungeon master using Qwen2.5 — "
        f"v{version} now on itch.io [GitHub]"
    )
    body = f"""\
After seeing what AI Dungeon charges for a subscription, I built a text-based \
D&D narrator that runs 100% locally.

**Stack:** Python + Hugging Face Transformers + Qwen2.5-0.5B-Instruct
**Inference:** CPU only, `device=-1`. ~15–30s per turn on a modern CPU.
**No network calls** after the initial model download.

The prompt engineering is minimal: one system rule ("write one vivid paragraph, \
second person, fantasy tone, end with 'What do you do next?'") plus the last 3 \
narrator turns in chat history. Tried including all turns but it degraded coherence \
— the model would start echoing player actions.

**What's new in v{version}:**
- `--scenario` flag: dungeon / tavern / wilderness or custom JSON files
- `--save` / `--load`: persist and resume sessions
- `--model`: swap any local Hugging Face causal LM

Web demo (runs in browser): {hf_url}
Download (offline, no API key): {itch_url}
Source (Apache 2.0): https://github.com/gokulrajanpillai/DnDOfflinePro

**Question for the community:** has anyone tried Phi-3.5-mini-instruct for \
creative writing tasks like this? Curious if the instruction-following holds \
up at the fantasy narrator persona compared to Qwen2.5-0.5B.
"""
    return title, body


def build_hn_url(version: str, hf_url: str) -> str:
    title = f"Show HN: DnD Offline Pro v{version} – offline AI dungeon master, runs on CPU"
    return f"https://news.ycombinator.com/submitlink?u={urllib.parse.quote(hf_url)}&t={urllib.parse.quote(title)}"


def build_hn_body(version: str, hf_url: str, itch_url: str) -> str:
    return f"""\
I built an interactive D&D narrator that runs entirely on your machine — no API \
key, no subscription, no internet after the initial model download.

Demo: {hf_url}
Download: {itch_url}
Source: https://github.com/gokulrajanpillai/DnDOfflinePro

It uses Qwen2.5-0.5B-Instruct via Hugging Face Transformers. Generation takes \
15–30 seconds per turn on a modern CPU. The whole game loop is ~160 lines of Python.

The key prompt engineering decision: rolling 3-turn narrator history (not full \
turn history). Keeping only narrator responses — not player actions — in the \
context window preserved narrative voice while staying within the model's \
effective context length.

v{version} adds --scenario (dungeon/tavern/wilderness or custom JSON), \
session save/load, and a --model flag to swap any local causal LM.

Apache 2.0. Planning a PyQt6 desktop GUI next. Core engine stays open.
"""


def post_to_reddit(title: str, body: str) -> str:
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
    sub = reddit.subreddit("LocalLLaMA")
    submission = sub.submit(title=title, selftext=body)
    return f"https://reddit.com{submission.permalink}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print posts without submitting")
    args = parser.parse_args()

    version   = os.environ.get("VERSION", "")
    hf_url    = os.environ.get("HF_URL", "")
    itch_url  = os.environ.get("ITCH_URL", "")

    if not version:
        print("VERSION env var required (e.g. VERSION=0.2.0)")
        sys.exit(1)

    reddit_title, reddit_body = build_reddit_post(version, hf_url, itch_url)
    hn_url  = build_hn_url(version, hf_url)
    hn_body = build_hn_body(version, hf_url, itch_url)

    # --- GitHub Actions summary output ---
    gha_summary = os.environ.get("GITHUB_STEP_SUMMARY")

    def to_summary(text: str):
        if gha_summary:
            with open(gha_summary, "a") as f:
                f.write(text + "\n")
        else:
            print(text)

    # HN section (always output — no API, user clicks the link)
    to_summary("## Hacker News")
    to_summary("")
    to_summary(f"**[Click to open pre-filled submission]({hn_url})**")
    to_summary("(URL + title are pre-filled; paste the body below into the text field)")
    to_summary("")
    to_summary("```")
    to_summary(hn_body)
    to_summary("```")
    to_summary("")

    # Reddit section
    to_summary("## Reddit — r/LocalLLaMA")
    to_summary("")

    has_reddit_creds = all(
        os.environ.get(k)
        for k in ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET",
                  "REDDIT_USERNAME", "REDDIT_PASSWORD"]
    )

    if args.dry_run or not has_reddit_creds:
        to_summary("_Reddit credentials not set — post manually:_")
        to_summary("")
        to_summary(f"**Title:** {reddit_title}")
        to_summary("")
        to_summary("**Body:**")
        to_summary("```")
        to_summary(reddit_body)
        to_summary("```")
    else:
        print("Posting to r/LocalLLaMA...")
        url = post_to_reddit(reddit_title, reddit_body)
        to_summary(f"Posted: {url}")
        print(f"Reddit post live: {url}")


if __name__ == "__main__":
    main()
