# DnD Offline Pro

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey)]()
[![GitHub Sponsors](https://img.shields.io/github/sponsors/gokulrajanpillai?label=Sponsors&logo=github)](https://github.com/sponsors/gokulrajanpillai)

> **Fully offline AI dungeon master. No internet. No subscription. Runs on any CPU.**

DnD Offline Pro is a local, privacy-first tabletop RPG narrator powered by small language models.
Every word of your adventure is generated on your machine — nothing leaves your device.

<!-- TODO: Replace this block with a demo.gif once recorded
![Demo](assets/demo.gif)
-->

**[Try the web demo →](https://huggingface.co/spaces/gokulrajanpillai/DnDOfflinePro-Demo)**
_(runs in browser — no install, no download)_

---

## Features

- **100% offline** — no network calls after the initial one-time model download
- **No GPU required** — runs on any modern CPU
- **Multiple starting scenarios** — dungeon, tavern, wilderness, or bring your own
- **Session save & resume** — save your story to JSON and continue later
- **Swappable models** — point `--model` at any Hugging Face causal LM on disk
- **Privacy-first** — your story never touches a server

---

## Quick Start

```bash
# 1. Clone and install dependencies
git clone https://github.com/gokulrajanpillai/DnDOfflinePro.git
cd DnDOfflinePro
pip install -r requirements.txt

# 2. Download the default model (one-time, ~1 GB)
python tools_fetch_model.py

# 3. Play
python src/dnd_offline.py
```

---

## Scenarios

Choose a starting scenario with `--scenario`:

```bash
python src/dnd_offline.py --scenario dungeon     # default — cold hall, creaking door
python src/dnd_offline.py --scenario tavern      # a hooded stranger with a note
python src/dnd_offline.py --scenario wilderness  # lost in fog, a wolf nearby
```

Community scenario templates live in [scenarios/](scenarios/). Drop a `.json` file there
and pass its path with `--scenario path/to/my_scenario.json`.

---

## Save & Resume

```bash
# Save session as you play
python src/dnd_offline.py --save saves/my_session.json

# Resume a saved session
python src/dnd_offline.py --load saves/my_session.json
```

---

## Swapping Models

Any Hugging Face causal LM downloaded locally works:

```bash
python src/dnd_offline.py --model models/qwen_2_5_1_5b_instruct
```

| Model | Size | Quality | RAM needed |
|---|---|---|---|
| Qwen2.5-0.5B-Instruct (default) | ~1 GB | Good | 2 GB |
| Qwen2.5-1.5B-Instruct | ~3 GB | Better | 4 GB |
| TinyLlama-Chat | ~700 MB | Baseline | 2 GB |

---

## Desktop GUI (PyQt6)

A full windowed app with a two-panel layout — story on the left, live character sheet on the right.

```bash
pip install -r requirements-desktop.txt
python src/dnd_desktop.py
# Optional flags:
#   --model models/qwen2_5_1_5b_instruct
#   --scenario tavern
```

---

## Web Demo (local)

Run the browser UI against your already-downloaded model — no extra download needed:

```bash
pip install gradio
LOCAL_MODEL_PATH=models/qwen2_5_0_5b_instruct python spaces/app.py
# Open http://localhost:7860
```

Or let it pull the model from HF Hub on first run (requires internet, ~1 GB):

```bash
pip install gradio
python spaces/app.py
```

---

## Project Structure

```
DnDOfflinePro/
├── src/dnd_offline.py      # Core CLI engine (Apache 2.0)
├── src/dnd_desktop.py      # PyQt6 desktop GUI
├── spaces/app.py           # Gradio web UI (HF Spaces / local)
├── scenarios/              # Community scenario templates
├── docs/                   # Setup guides
├── tools_fetch_model.py    # One-time model downloader
├── requirements.txt        # CLI dependencies
├── requirements-desktop.txt  # Desktop GUI (adds PyQt6)
└── models/                 # Local model files (git-ignored)
```

---

## Contributing

Contributions are welcome — bug fixes, new scenarios, model compatibility improvements,
and UI ideas. See [CONTRIBUTING.md](CONTRIBUTING.md) to get started.

---

## Support the Project

If DnD Offline Pro saved you money on AI subscriptions or gave you a good adventure,
consider sponsoring development:

- [GitHub Sponsors](https://github.com/sponsors/gokulrajanpillai)

Companies using DnD Offline Pro in demos or education: reach out about a sponsorship
tier to have your logo here.

---

## License

Apache 2.0 — free to use, modify, and distribute. See [LICENSE](./LICENSE).

> **Premium content** (campaign packs, structured multi-session storylines) will be
> released separately under commercial terms. The core engine stays open source, always.
