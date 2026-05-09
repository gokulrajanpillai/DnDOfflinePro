# Contributing to DnD Offline Pro

Thanks for your interest in contributing. The project is small and the bar is low —
if you play the game and something bugs you, that's enough reason to open a PR.

## What we welcome

- **Bug fixes** — wrong output, crashes, model loading issues
- **New built-in scenarios** — add an opening scene to `src/dnd_offline.py`'s `SCENARIOS` dict
- **Scenario templates** — drop a `.json` file in `scenarios/` (see format below)
- **Model compatibility** — notes or patches for models that need special handling
- **Documentation** — clearer setup steps, model download guides, FAQ

## What we are not looking for (yet)

- Large architectural refactors without a prior discussion
- GUI implementations (tracked separately as a roadmap item)
- Anything that adds a network call at runtime

## Setup

```bash
git clone https://github.com/gokulrajanpillai/DnDOfflinePro.git
cd DnDOfflinePro
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python tools_fetch_model.py   # downloads the default model
python src/dnd_offline.py     # smoke-test your setup
```

## Scenario template format

A scenario JSON file has two fields:

```json
{
  "name": "shipwreck",
  "opening": "Salt water fills your lungs as you drag yourself onto black sand. The wreck of the Mara's Tooth burns fifty yards offshore. You have your knife. Everything else is gone."
}
```

Place it in `scenarios/` and test it with:

```bash
python src/dnd_offline.py --scenario scenarios/shipwreck.json
```

## Pull request checklist

- [ ] Tested locally with `python src/dnd_offline.py`
- [ ] No new dependencies added without discussion
- [ ] No runtime network calls introduced
- [ ] Commit message describes the *why*, not just the *what*

## Code style

Standard Python — `black` formatting is appreciated but not enforced.
Keep functions short. No unnecessary abstractions.

## License

By contributing you agree your changes are licensed under Apache 2.0,
the same as the rest of this project.
