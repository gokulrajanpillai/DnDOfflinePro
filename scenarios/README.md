# Community Scenarios

This folder contains community-contributed scenario starting points for DnD Offline Pro.

## Using a scenario

```bash
python src/dnd_offline.py --scenario scenarios/shipwreck.json
```

## Creating your own

A scenario file is a plain JSON object with two fields:

```json
{
  "name": "your_scenario_name",
  "opening": "The opening paragraph the narrator reads aloud at the start of the session."
}
```

Tips for a good opening:
- Second person ("You stand..."), present tense
- 1–3 sentences — just enough to establish place, stakes, and tension
- End mid-situation: give the player something immediate to react to
- Avoid giving the player named abilities or inventory — let them define that

## Contributing a scenario

Add your `.json` file to this folder and open a PR. See [CONTRIBUTING.md](../CONTRIBUTING.md).
