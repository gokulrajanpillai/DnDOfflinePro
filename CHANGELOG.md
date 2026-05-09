# Changelog

All notable changes to DnD Offline Pro are documented here.

## [Unreleased]

### Changed
- License changed from Personal Use to Apache 2.0 — core engine is now open source
- README completely rewritten with setup guide, scenario docs, and model table

### Added
- `--scenario` flag: choose from `dungeon`, `tavern`, `wilderness`, or a custom JSON file
- `--model` flag: point at any local Hugging Face causal LM
- `--save` / `--load` flags: persist and resume sessions as JSON
- Built-in scenario templates in `scenarios/`
- `CONTRIBUTING.md` and GitHub issue templates
- `.github/FUNDING.yml` to enable the Sponsor button

## [0.1.0] — 2025

### Added
- Initial release: offline AI dungeon narrator using Qwen2.5-0.5B-Instruct
- CPU-only inference via Hugging Face Transformers
- Rolling chat history for narrative continuity
- Nuitka-compiled standalone binary
