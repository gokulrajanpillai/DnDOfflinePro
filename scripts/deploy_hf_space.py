#!/usr/bin/env python3
"""
Deploy (or re-deploy) the DnD Offline Pro demo to a Hugging Face Space.

Local usage (interactive login):
    python scripts/deploy_hf_space.py

CI usage (env vars, no prompts):
    HF_TOKEN=hf_xxx HF_USERNAME=gokulrajanpillai python scripts/deploy_hf_space.py

Requires:
    pip install huggingface_hub>=0.24
"""

import os
import sys

try:
    from huggingface_hub import HfApi, login, whoami
except ImportError:
    print("huggingface_hub not found. Run: pip install huggingface_hub")
    sys.exit(1)

SPACE_NAME     = "DnDOfflinePro-Demo"
SPACES_DIR     = os.path.join(os.path.dirname(__file__), "..", "spaces")
REQUIRED_FILES = ["app.py", "requirements.txt", "README.md"]


def check_login():
    try:
        return whoami()["name"]
    except Exception:
        return None


def main():
    ci_token    = os.environ.get("HF_TOKEN")
    ci_username = os.environ.get("HF_USERNAME")

    if ci_token and ci_username:
        # Non-interactive CI path
        api      = HfApi(token=ci_token)
        username = ci_username
    else:
        # Interactive local path
        print("=== DnD Offline Pro — Hugging Face Space deployer ===\n")
        username = check_login()
        if not username:
            print("Not logged in. Paste a token from https://huggingface.co/settings/tokens\n")
            login()
            username = check_login()
            if not username:
                print("Login failed.")
                sys.exit(1)
        print(f"Logged in as: {username}\n")
        api = HfApi()

    repo_id = f"{username}/{SPACE_NAME}"

    missing = [f for f in REQUIRED_FILES if not os.path.exists(os.path.join(SPACES_DIR, f))]
    if missing:
        print(f"Missing files in spaces/: {missing}")
        sys.exit(1)

    print(f"Creating Space '{repo_id}' if it doesn't exist...")
    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="gradio",
        private=False,
        exist_ok=True,
    )

    print(f"Uploading spaces/ → {repo_id}...")
    api.upload_folder(
        folder_path=SPACES_DIR,
        repo_id=repo_id,
        repo_type="space",
        ignore_patterns=["*.pyc", "__pycache__"],
    )

    space_url = f"https://huggingface.co/spaces/{repo_id}"
    print(f"\nDone: {space_url}")


if __name__ == "__main__":
    main()
