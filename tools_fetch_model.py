# tools_fetch_model.py
import argparse
import os
import shutil
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

# Supported models
MODELS = {
    "qwen_0_5b": {
        "repo": "Qwen/Qwen2.5-0.5B-Instruct",
        "local": "models/qwen_2_5_0_5b_instruct",
        "note": "Small instruct model. Good on CPU.",
    },
    "qwen_1_5b": {
        "repo": "Qwen/Qwen2.5-1.5B-Instruct",
        "local": "models/qwen_2_5_1_5b_instruct",
        "note": "Larger instruct model. Nicer prose. Slower on CPU.",
    },
    "tinyllama_chat": {
        "repo": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "local": "models/tinyllama-chat",
        "note": "Tiny chat tuned model.",
    },
    "distilgpt2": {
        "repo": "distilgpt2",
        "local": "models/distilgpt2",
        "note": "Very small baseline causal model.",
    },
}

def human_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    x = float(n)
    while x >= 1024 and i < len(units) - 1:
        x /= 1024.0
        i += 1
    return f"{x:.1f} {units[i]}"

def dir_size(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except Exception:
                pass
    return total

def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

def fetch(model_key: str, force: bool = False) -> Path:
    if model_key not in MODELS:
        names = ", ".join(MODELS.keys())
        raise SystemExit(f"Unknown model {model_key}. Choose from: {names}")

    repo_id = MODELS[model_key]["repo"]
    local_dir = Path(MODELS[model_key]["local"])
    ensure_parent(local_dir)

    if local_dir.exists() and not force:
        print(f"Model already present at: {local_dir}")
        print(f"Size: {human_bytes(dir_size(local_dir))}")
        return local_dir

    if local_dir.exists() and force:
        print(f"Removing existing folder: {local_dir}")
        shutil.rmtree(local_dir)

    print(f"Downloading {repo_id}")
    print(f"Target: {local_dir}")
    snapshot_download(
        repo_id=repo_id,
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,
        resume_download=True,
        max_workers=4,
    )
    size = human_bytes(dir_size(local_dir))
    print(f"Done. Stored at: {local_dir}  Size: {size}")
    return local_dir

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Download a local model for DnD Offline Pro"
    )
    parser.add_argument(
        "--model",
        choices=list(MODELS.keys()),
        default="qwen_0_5b",
        help="Which model to fetch. Default is qwen_0_5b",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Redownload and overwrite the existing folder",
    )
    args = parser.parse_args(argv)

    choice = args.model
    info = MODELS[choice]
    print(f"Model: {choice}")
    print(f"Repo:  {info['repo']}")
    print(f"Path:  {info['local']}")
    print(f"Note:  {info['note']}\n")

    try:
        path = fetch(choice, force=args.force)
        # Print a helper line for setting MODEL_DIR
        print("\nSet MODEL_DIR in src/dnd_offline.py to:")
        print(f"MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', '{path.as_posix()}')")
        return 0
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130

if __name__ == "__main__":
    sys.exit(main())
