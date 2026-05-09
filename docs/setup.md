# Setup Guide

## Requirements

- Python 3.10 or higher (3.12 recommended)
- ~2 GB RAM (for the default 0.5B model)
- ~1 GB disk space for the model

No GPU required. No internet connection required after the initial model download.

---

## Step 1 — Clone the repository

```bash
git clone https://github.com/gokulrajanpillai/DnDOfflinePro.git
cd DnDOfflinePro
```

## Step 2 — Create a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate       # macOS / Linux
.venv\Scripts\activate.bat      # Windows
```

## Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs PyTorch, Hugging Face Transformers, and huggingface_hub.
PyTorch is large (~500 MB); allow a few minutes on a slow connection.

## Step 4 — Download the model (one-time)

```bash
python tools_fetch_model.py
```

This downloads Qwen2.5-0.5B-Instruct into `models/qwen2_5_0_5b_instruct/`.
The download is approximately 1 GB. After this, the game runs with no network access.

## Step 5 — Play

```bash
python src/dnd_offline.py
```

---

## Troubleshooting

### `Could not load local model`

The model folder is missing or incomplete. Re-run `python tools_fetch_model.py`
and check that `models/qwen2_5_0_5b_instruct/` contains `config.json` and `.safetensors` files.

### Slow generation

This is expected on CPU with a 0.5B model — expect 5–30 seconds per turn depending on
your hardware. Switching to a smaller model will not help much; this is the smallest
recommended size for coherent narration. A faster CPU or more RAM helps more than model size.

### `TOKENIZERS_PARALLELISM` warning

Suppressed automatically. No action needed.

### Windows `UnicodeDecodeError`

Run `chcp 65001` in your terminal before launching, or set `PYTHONIOENCODING=utf-8`.

---

## Using a different model

Any Hugging Face causal LM downloaded locally works:

```bash
# Download a larger model for better quality
python -c "
from huggingface_hub import snapshot_download
snapshot_download('Qwen/Qwen2.5-1.5B-Instruct', local_dir='models/qwen_2_5_1_5b_instruct')
"

# Use it
python src/dnd_offline.py --model models/qwen_2_5_1_5b_instruct
```
