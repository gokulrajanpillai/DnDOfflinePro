# Recording the Demo GIF

The animated GIF in the README is the single highest-value asset for GitHub stars.
This guide covers the fastest path on macOS.

## Option A — asciinema + agg (recommended, terminal-only)

Produces a clean, text-only GIF. Looks great in README. Tiny file size.

```bash
# Install tools
brew install asciinema
cargo install --git https://github.com/asciinema/agg   # requires Rust

# Record (Ctrl-D or 'exit' to stop)
asciinema rec demo.cast

# Play through your best 45-second session:
#   - Pick a vivid opening (tavern or dungeon)
#   - Type 3–4 actions with good narrative payoff
#   - Keep terminal at 100×30 for a clean aspect ratio

# Convert to GIF
agg demo.cast assets/demo.gif --font-size 14 --theme monokai
```

Upload `assets/demo.gif` and uncomment the image block in README.md.

---

## Option B — Screen recording + ffmpeg (shows actual terminal colours)

```bash
# 1. Open Terminal, resize window to ~100 columns × 30 rows
# 2. Cmd+Shift+5 → Record Selected Portion → select the terminal window
# 3. Play a session, then stop recording (Cmd+Shift+5 → Stop)
# 4. Convert the .mov to GIF:

brew install ffmpeg gifsicle

ffmpeg -i ~/Desktop/Screen\ Recording.mov \
  -vf "fps=8,scale=900:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" \
  -loop 0 assets/demo.gif

# Optimise file size
gifsicle -O3 assets/demo.gif -o assets/demo.gif
```

---

## Tips for a great demo

- **Duration:** 30–50 seconds. Long enough to show two narrator responses.
- **Scenario:** Tavern or wilderness — the openings are more visually interesting than the default dungeon.
- **Font:** Use a readable monospace (JetBrains Mono, Fira Code) at 14–16pt.
- **Terminal background:** Dark background (pure black or #1a1a2e) looks best in GitHub's light and dark modes.
- **Content:** Type a short action ("I reach for the note"), let the model respond, type one more action. That's enough to show the loop.
- **File size target:** Under 3 MB. GitHub embeds up to 10 MB but large GIFs hurt load time.

---

## Uncommenting the README embed

Once `assets/demo.gif` exists, open README.md and replace:

```markdown
<!-- TODO: Replace this block with a demo.gif once recorded
![Demo](assets/demo.gif)
-->
```

with:

```markdown
![Demo](assets/demo.gif)
```
