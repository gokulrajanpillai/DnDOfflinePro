import os
import sys
import json
import time
import argparse
import warnings
from pathlib import Path

os.environ["TOKENIZERS_PARALLELISM"] = "false"
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass
try:
    import urllib3
    warnings.filterwarnings("ignore", category=urllib3.exceptions.NotOpenSSLWarning)
except Exception:
    pass

from transformers.utils import logging as hf_logging
hf_logging.set_verbosity_error()

from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich.prompt import Prompt
from rich.live import Live
from rich.columns import Columns

console = Console()

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL = os.path.join(APP_DIR, "..", "models", "qwen2_5_0_5b_instruct")

# Gold / parchment colour palette
GOLD   = "#c9a227"
CREAM  = "#e8d5b7"
DIM    = "dim"
BORDER = "#3d2f1a"

CHARACTER_CLASSES = {
    "Fighter":  "combat-hardened and resolute, skilled with any weapon, armoured and direct",
    "Rogue":    "nimble and cunning, expert in stealth, lockpicking, and deception",
    "Wizard":   "learned in arcane magic, quick to notice enchantments, physically frail",
    "Cleric":   "devoted to divine power, attuned to undead and evil, a healer under pressure",
    "Ranger":   "wilderness-hardened tracker, attuned to nature, at home in the dark",
    "Bard":     "silver-tongued and quick-witted, charming, skilled in lore and persuasion",
    "Paladin":  "righteous and strong, bound by oath, a beacon in the dark against evil",
    "Druid":    "attuned to nature's rhythms, perceptive of natural threats, ancient in outlook",
}

SCENARIOS = {
    "dungeon": (
        "You stand in a cold hall. A door creaks. Something watches."
    ),
    "tavern": (
        "You warm your hands at the crackling hearth of the Tarnished Flagon. "
        "The barkeep slides you a foaming ale without asking. A hooded stranger "
        "at the corner table catches your eye, then drops a folded note onto your lap."
    ),
    "wilderness": (
        "Pine needles crunch underfoot as the trail vanishes behind a curtain of fog. "
        "The moon is gone, your torch is nearly spent, and somewhere ahead a wolf "
        "howls — close enough that you can hear it breathe."
    ),
}


# ── Prompt engineering ────────────────────────────────────────────────────────

def build_system_rule(character: dict) -> str:
    if character.get("name") and character.get("class"):
        cls  = character["class"]
        desc = CHARACTER_CLASSES.get(cls, "a seasoned adventurer")
        char_ctx = (
            f"for {character['name']}, a {cls} — {desc}. "
            f"Acknowledge {character['name']}'s class abilities when contextually fitting. "
        )
    else:
        char_ctx = "for a lone adventurer. "

    return (
        f"You are the Dungeon narrator {char_ctx}"
        "Write one vivid paragraph of up to 180 words. "
        "Second person, fantasy tone, rich sensory detail, light wit, no modern slang. "
        "Success is never guaranteed — sometimes the player fails, slips, or is surprised. "
        "Reference fortune in flavour only ('luck turns against you', 'fortune smiles briefly'). "
        "End with a hook — a question, a sound, a dying breath, a door opening — "
        "and vary the form and phrasing every single time, never repeating yourself."
    )


def build_prompt(tokenizer, history: list, player_action: str, character: dict) -> str:
    system_rule = build_system_rule(character)
    msgs = [{"role": "system", "content": system_rule}]
    tail = [m for m in history if m.get("role") == "assistant"][-3:]
    msgs.extend(tail)
    msgs.append({"role": "user", "content": player_action})

    if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
        return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

    recent = " ".join(m["content"] for m in tail) if tail else ""
    return (
        f"<SYSTEM>\n{system_rule}\n</SYSTEM>\n"
        + (f"<ASSISTANT>\n{recent}\n</ASSISTANT>\n" if recent else "")
        + f"<USER>\n{player_action}\n</USER>\n<ASSISTANT>\n"
    )


# ── I/O helpers ───────────────────────────────────────────────────────────────

def typewriter(text: str, delay: float = 0.013):
    """Render narrator text with a typewriter effect inside a gold panel."""
    displayed = Text(style=CREAM)
    panel = Panel(displayed, border_style=GOLD, padding=(0, 1))
    with Live(panel, console=console, refresh_per_second=80):
        for char in text:
            displayed.append(char)
            try:
                time.sleep(delay)
            except KeyboardInterrupt:
                break
    console.print()


def print_panel(body: str, title: str = ""):
    console.print(Panel(
        Text(body, style=CREAM),
        title=f"[{GOLD}]{title}[/{GOLD}]" if title else "",
        border_style=GOLD,
        padding=(0, 1),
    ))
    console.print()


def separator():
    console.rule(style=f"dim {BORDER}")


# ── Session persistence ───────────────────────────────────────────────────────

def save_session(path: str, character: dict, history: list):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"character": character, "history": history}, f, indent=2)


def load_session(path: str) -> tuple[dict, list]:
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):          # backwards-compat with old plain-list saves
        return {}, data
    return data.get("character", {}), data.get("history", [])


# ── Character creation ────────────────────────────────────────────────────────

def character_creation() -> dict:
    console.print()
    console.rule(f"[bold {GOLD}]Character Creation[/bold {GOLD}]")
    console.print()

    name = Prompt.ask(f"[bold white]Your character's name[/bold white]").strip() or "Adventurer"

    console.print()
    console.print(f"[{GOLD}]Choose your class:[/{GOLD}]\n")
    classes = list(CHARACTER_CLASSES.keys())
    for i, (cls, desc) in enumerate(CHARACTER_CLASSES.items(), 1):
        console.print(f"  [bold white]{i}.[/bold white] [{GOLD}]{cls:<10}[/{GOLD}]  [{DIM}]{desc}[/{DIM}]")

    console.print()
    while True:
        raw = Prompt.ask(f"[bold white]Class[/bold white]", default="1")
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(classes):
                chosen_class = classes[idx]
                break
        except ValueError:
            pass
        console.print(f"[red]Enter a number from 1 to {len(classes)}[/red]")

    console.print()
    console.print(Panel(
        Text(f"{name} the {chosen_class} steps forth into the dark…", style=f"italic {CREAM}"),
        border_style=GOLD,
    ))
    console.print()

    return {"name": name, "class": chosen_class}


# ── Slash commands ────────────────────────────────────────────────────────────

def handle_command(cmd: str, character: dict, history: list, save_path: str | None) -> bool:
    """Handle /commands. Returns True if a known command was handled."""
    key = cmd.lower().strip()

    if key == "/help":
        lines = (
            f"[{GOLD}]/help[/{GOLD}]      Show this message\n"
            f"[{GOLD}]/status[/{GOLD}]    Show your character info\n"
            f"[{GOLD}]/recap[/{GOLD}]     Show the last three narrator moments\n"
            f"[{GOLD}]/save[/{GOLD}]      Save the session now\n"
            f"[{GOLD}]/quit[/{GOLD}]      End the session"
        )
        console.print(Panel(lines, title=f"[{GOLD}]Commands[/{GOLD}]", border_style=GOLD))

    elif key == "/status":
        body = (
            f"[bold white]Name :[/bold white]  [{CREAM}]{character.get('name', '?')}[/{CREAM}]\n"
            f"[bold white]Class:[/bold white]  [{CREAM}]{character.get('class', '?')}[/{CREAM}]"
        )
        console.print(Panel(body, title=f"[{GOLD}]Character[/{GOLD}]", border_style=GOLD))

    elif key == "/recap":
        narrator_turns = [m["content"] for m in history if m.get("role") == "assistant"][-3:]
        if narrator_turns:
            body = f"\n[{DIM}]─────[/{DIM}]\n".join(f"[{CREAM}]{t}[/{CREAM}]" for t in narrator_turns)
        else:
            body = f"[{DIM}]Nothing to recap yet.[/{DIM}]"
        console.print(Panel(body, title=f"[{GOLD}]Recent Events[/{GOLD}]", border_style=GOLD))

    elif key == "/save":
        if save_path:
            save_session(save_path, character, history)
            console.print(f"[{DIM}]Session saved → {save_path}[/{DIM}]")
        else:
            console.print(f"[{DIM}]No save path set. Restart with --save <path> to enable.[/{DIM}]")

    elif key in ("/quit", "/exit"):
        return False   # signal main loop to exit

    else:
        console.print(f"[{DIM}]Unknown command '{cmd}'. Type /help for a list.[/{DIM}]")

    console.print()
    return True


# ── Model loading ─────────────────────────────────────────────────────────────

def load_pipeline(model_dir: str):
    tok = AutoTokenizer.from_pretrained(model_dir)
    mdl = AutoModelForCausalLM.from_pretrained(model_dir)
    return pipeline("text-generation", model=mdl, tokenizer=tok, device=-1)


# ── Scenario resolution ───────────────────────────────────────────────────────

def resolve_opening(scenario_arg: str) -> str:
    if scenario_arg in SCENARIOS:
        return SCENARIOS[scenario_arg]
    p = Path(scenario_arg)
    if p.exists():
        with open(p) as f:
            return json.load(f)["opening"]
    console.print(f"[red]Unknown scenario '{scenario_arg}'. "
                  f"Choose from: {', '.join(SCENARIOS)} or provide a JSON file.[/red]")
    sys.exit(1)


# ── CLI args ──────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="DnD Offline Pro — AI dungeon master, fully offline")
    parser.add_argument("--model",    default=None, help="Path to a local model directory")
    parser.add_argument("--scenario", default="dungeon",
                        help="Starting scenario: dungeon (default), tavern, wilderness, or a JSON path")
    parser.add_argument("--save",     default=None, help="Auto-save session to this JSON path each turn")
    parser.add_argument("--load",     default=None, help="Resume a previously saved session")
    return parser.parse_args()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    console.print()
    console.rule(f"[bold {GOLD}]DnD Offline Pro[/bold {GOLD}]")
    console.print(f"[{DIM}]Fully local · No network calls after install · Type /help for commands[/{DIM}]\n")

    # Character
    if args.load:
        character, history = load_session(args.load)
        if not character:
            console.print(f"[{DIM}]No character found in save — starting character creation.[/{DIM}]\n")
            character = character_creation()
    else:
        character = character_creation()
        history   = []

    # Model
    model_dir = args.model or DEFAULT_MODEL
    try:
        with console.status(f"[{DIM}]Loading local model…[/{DIM}]",
                            spinner="dots", spinner_style=GOLD):
            generator = load_pipeline(model_dir)
    except Exception as e:
        console.print(f"[red]Could not load model from {model_dir}[/red]\n[red]{e}[/red]")
        sys.exit(1)

    # Opening scene
    opening = resolve_opening(args.scenario)
    if args.load and history:
        last = next((m["content"] for m in reversed(history) if m.get("role") == "assistant"), opening)
        console.print(f"[{DIM}]Session resumed from {args.load}[/{DIM}]\n")
        typewriter(last)
    else:
        history.append({"role": "assistant", "content": opening})
        typewriter(opening)

    turn = 0
    try:
        while True:
            separator()
            action = Prompt.ask(
                f"[bold {GOLD}]{character['name']}[/bold {GOLD}]"
                f" [{DIM}]({character['class']} · Turn {turn + 1})[/{DIM}]"
            )

            if action.lower() in ("exit", "quit"):
                console.print(f"\n[italic {DIM}]The dungeon sighs and releases you. Farewell.[/italic {DIM}]")
                break

            if action.startswith("/"):
                should_continue = handle_command(action, character, history, args.save)
                if not should_continue:
                    console.print(f"\n[italic {DIM}]The dungeon sighs and releases you. Farewell.[/italic {DIM}]")
                    break
                continue

            with console.status(
                f"[italic {DIM}]The narrator considers…[/italic {DIM}]",
                spinner="dots", spinner_style=GOLD
            ):
                prompt = build_prompt(generator.tokenizer, history, action, character)
                out = generator(
                    prompt,
                    max_new_tokens=240,
                    do_sample=True,
                    temperature=0.85,
                    top_p=0.92,
                    repetition_penalty=1.05,
                    eos_token_id=generator.tokenizer.eos_token_id,
                    pad_token_id=generator.tokenizer.eos_token_id,
                    num_return_sequences=1,
                    return_full_text=False,
                )[0]["generated_text"].strip()

            console.print()
            typewriter(out)

            history.append({"role": "user", "content": action})
            history.append({"role": "assistant", "content": out})
            if len(history) > 8:
                del history[:-8]

            if args.save:
                save_session(args.save, character, history)

            turn += 1

    except KeyboardInterrupt:
        console.print(f"\n[italic {DIM}]Session ended.[/italic {DIM}]")


if __name__ == "__main__":
    main()
