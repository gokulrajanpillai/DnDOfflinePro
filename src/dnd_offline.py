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
from rich.table import Table

console = Console()

APP_DIR      = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL = os.path.join(APP_DIR, "..", "models", "qwen2_5_0_5b_instruct")
MEMORY_INTERVAL = 6   # generate a session summary every N turns

# Colour palette
GOLD   = "#c9a227"
CREAM  = "#e8d5b7"
DIM    = "dim"
BORDER = "#3d2f1a"
RED    = "#8b0000"
GREEN  = "#2d5a27"
AMBER  = "#8b6914"

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

DEFAULT_HP = {
    "Fighter": 14, "Paladin": 14,
    "Ranger": 12,  "Cleric": 12,
    "Bard": 10,    "Rogue": 10, "Druid": 10,
    "Wizard": 8,
}

DIFFICULTY_RULES = {
    "easy":   "Success usually comes to the brave. Setbacks are minor and rarely fatal.",
    "normal": ("Success is never guaranteed — sometimes the player fails, slips, or is "
               "surprised. Reference fortune in flavour only ('luck turns against you')."),
    "hard":   ("The world is unforgiving. Actions frequently fail or backfire. "
               "The player must be clever, cautious, and fortunate to survive."),
}

SCENARIOS = {
    "dungeon": "You stand in a cold hall. A door creaks. Something watches.",
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


# ── Utility helpers ───────────────────────────────────────────────────────────

def format_duration(seconds: float) -> str:
    s = int(seconds)
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def hp_bar(current: int, maximum: int, width: int = 16) -> Text:
    ratio  = current / maximum if maximum > 0 else 0
    filled = max(0, min(int(ratio * width), width))
    color  = GREEN if ratio > 0.5 else AMBER if ratio > 0.25 else RED
    bar = Text()
    bar.append("█" * filled, style=color)
    bar.append("░" * (width - filled), style=DIM)
    bar.append(f" {current}/{maximum}", style=CREAM)
    return bar


def normalize_character(c: dict) -> dict:
    cls = c.get("class", "Fighter")
    defaults = {
        "name":       "Adventurer",
        "class":      "Fighter",
        "hp_max":     DEFAULT_HP.get(cls, 12),
        "hp_current": DEFAULT_HP.get(cls, 12),
        "inventory":  [],
        "effects":    [],
        "difficulty": "normal",
        "memory":     "",
    }
    for k, v in defaults.items():
        if k not in c:
            c[k] = v
    c["hp_current"] = min(c["hp_current"], c["hp_max"])
    return c


# ── Prompt engineering ────────────────────────────────────────────────────────

def build_system_rule(character: dict) -> str:
    name = character.get("name", "Adventurer")
    cls  = character.get("class", "Fighter")
    desc = CHARACTER_CLASSES.get(cls, "a seasoned adventurer")
    diff = character.get("difficulty", "normal")

    # Memory preamble (injected when a summary exists)
    memory = character.get("memory", "").strip()
    memory_block = f"Session so far: {memory}\n\n" if memory else ""

    # Character state preamble
    state_parts = []
    hp_c = character.get("hp_current")
    hp_m = character.get("hp_max")
    if hp_c is not None and hp_m is not None:
        wound = ""
        if hp_c <= hp_m * 0.25: wound = " (critically wounded — narrate pain and frailty)"
        elif hp_c <= hp_m * 0.5: wound = " (injured — occasionally reference the hurt)"
        state_parts.append(f"HP {hp_c}/{hp_m}{wound}")

    inv = character.get("inventory", [])
    if inv:
        state_parts.append(f"carrying: {', '.join(inv)}")

    fx = character.get("effects", [])
    if fx:
        state_parts.append(f"status effects: {', '.join(fx)}")

    state_block = f"Character state: {'; '.join(state_parts)}.\n" if state_parts else ""

    return (
        f"{memory_block}"
        f"{state_block}"
        f"You are the Dungeon narrator for {name}, a {cls} — {desc}. "
        f"Write one vivid paragraph of up to 180 words. "
        "Second person, fantasy tone, rich sensory detail, light wit, no modern slang. "
        f"Acknowledge {name}'s class abilities when contextually fitting. "
        f"{DIFFICULTY_RULES.get(diff, DIFFICULTY_RULES['normal'])} "
        "End with a hook — a question, a sound, a dying breath, a door opening — "
        "and vary the form and phrasing every single time, never repeating yourself."
    )


def build_prompt(tokenizer, history: list, player_action: str, character: dict) -> str:
    rule = build_system_rule(character)
    msgs = [{"role": "system", "content": rule}]
    tail = [m for m in history if m.get("role") == "assistant"][-3:]
    msgs.extend(tail)
    msgs.append({"role": "user", "content": player_action})

    if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
        return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

    recent = " ".join(m["content"] for m in tail) if tail else ""
    return (
        f"<SYSTEM>\n{rule}\n</SYSTEM>\n"
        + (f"<ASSISTANT>\n{recent}\n</ASSISTANT>\n" if recent else "")
        + f"<USER>\n{player_action}\n</USER>\n<ASSISTANT>\n"
    )


def generate_memory(generator, history: list) -> str:
    """Run a second LLM pass to produce a 50-60 word session summary."""
    narrator_turns = [m["content"] for m in history if m.get("role") == "assistant"][-6:]
    if not narrator_turns:
        return ""
    context = "\n\n".join(narrator_turns)
    summary_prompt = [
        {"role": "system", "content": (
            "You are a scribe recording an adventure. "
            "Summarise the following events in 50-60 words. "
            "Focus on: locations, creatures, NPCs, items found, wounds taken. "
            "Past tense, third person, factual and specific."
        )},
        {"role": "user", "content": context},
    ]
    if hasattr(generator.tokenizer, "apply_chat_template") and generator.tokenizer.chat_template:
        prompt_text = generator.tokenizer.apply_chat_template(
            summary_prompt, tokenize=False, add_generation_prompt=True
        )
    else:
        prompt_text = f"<SYSTEM>Summarise in 50-60 words.</SYSTEM>\n<USER>{context}</USER>\n<ASSISTANT>"

    result = generator(
        prompt_text,
        max_new_tokens=90,
        do_sample=True,
        temperature=0.4,
        return_full_text=False,
    )[0]["generated_text"].strip()
    return result


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


# ── Rich UI helpers ───────────────────────────────────────────────────────────

def typewriter(text: str, delay: float = 0.013):
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


def separator():
    console.rule(style=f"dim {BORDER}")


def print_character_sheet(character: dict):
    table = Table.grid(padding=(0, 2))
    table.add_column(style=f"bold white", min_width=10)
    table.add_column(style=CREAM)

    table.add_row("Name",  character.get("name", "?"))
    table.add_row("Class", character.get("class", "?"))
    table.add_row("Diff.", character.get("difficulty", "normal").capitalize())

    hp_c = character.get("hp_current", "?")
    hp_m = character.get("hp_max", "?")
    if isinstance(hp_c, int) and isinstance(hp_m, int):
        bar_text = hp_bar(hp_c, hp_m)
        hp_row = Text("HP  ") + bar_text
        table.add_row("HP", hp_bar(hp_c, hp_m))
    else:
        table.add_row("HP", f"{hp_c}/{hp_m}")

    inv = character.get("inventory", [])
    table.add_row("Inventory", ", ".join(inv) if inv else f"[{DIM}]empty[/{DIM}]")

    fx = character.get("effects", [])
    table.add_row("Effects", ", ".join(fx) if fx else f"[{DIM}]none[/{DIM}]")

    memory = character.get("memory", "")
    if memory:
        table.add_row("Memory", f"[{DIM}]{memory[:80]}{'…' if len(memory) > 80 else ''}[/{DIM}]")

    console.print(Panel(table, title=f"[{GOLD}]Character Sheet[/{GOLD}]", border_style=GOLD))
    console.print()


# ── Slash commands ────────────────────────────────────────────────────────────

def handle_command(cmd: str, character: dict, history: list,
                   save_path: str | None) -> str:
    """
    Handle /commands. Returns:
      "continue"  — command handled, keep playing
      "quit"      — user wants to exit
    """
    parts = cmd.strip().split()
    key   = parts[0].lower()

    if key == "/help":
        lines = (
            f"[{GOLD}]/help[/{GOLD}]                    Show this message\n"
            f"[{GOLD}]/status[/{GOLD}]                  Full character sheet\n"
            f"[{GOLD}]/recap[/{GOLD}]                   Last three narrator moments\n"
            f"[{GOLD}]/undo[/{GOLD}]                    Roll back the last turn\n"
            f"[{GOLD}]/hp <n>[/{GOLD}]                  Set current HP (e.g. /hp 8)\n"
            f"[{GOLD}]/hp +<n> or -<n>[/{GOLD}]        Adjust HP (e.g. /hp -3, /hp +2)\n"
            f"[{GOLD}]/hp max <n>[/{GOLD}]              Set maximum HP\n"
            f"[{GOLD}]/inv add <item>[/{GOLD}]          Add item to inventory\n"
            f"[{GOLD}]/inv remove <item>[/{GOLD}]       Remove item from inventory\n"
            f"[{GOLD}]/effect add <name>[/{GOLD}]       Add a status effect\n"
            f"[{GOLD}]/effect remove <name>[/{GOLD}]    Remove a status effect\n"
            f"[{GOLD}]/difficulty easy|normal|hard[/{GOLD}]  Change difficulty\n"
            f"[{GOLD}]/save[/{GOLD}]                    Save session now\n"
            f"[{GOLD}]/quit[/{GOLD}]                    End the session"
        )
        console.print(Panel(lines, title=f"[{GOLD}]Commands[/{GOLD}]", border_style=GOLD))

    elif key == "/status":
        print_character_sheet(character)

    elif key == "/recap":
        turns = [m["content"] for m in history if m.get("role") == "assistant"][-3:]
        if turns:
            body = f"\n[{DIM}]─────[/{DIM}]\n".join(f"[{CREAM}]{t}[/{CREAM}]" for t in turns)
        else:
            body = f"[{DIM}]Nothing to recap yet.[/{DIM}]"
        console.print(Panel(body, title=f"[{GOLD}]Recent Events[/{GOLD}]", border_style=GOLD))

    elif key == "/hp":
        if len(parts) < 2:
            console.print(f"[{DIM}]Usage: /hp <n>  /hp +<n>  /hp -<n>  /hp max <n>[/{DIM}]")
        elif parts[1].lower() == "max" and len(parts) >= 3:
            try:
                character["hp_max"] = int(parts[2])
                character["hp_current"] = min(character["hp_current"], character["hp_max"])
                console.print(f"[{DIM}]Max HP set to {character['hp_max']}.[/{DIM}]")
            except ValueError:
                console.print(f"[red]Expected a number.[/red]")
        else:
            raw = parts[1]
            try:
                if raw.startswith(("+", "-")):
                    character["hp_current"] = max(0, character["hp_current"] + int(raw))
                else:
                    character["hp_current"] = max(0, int(raw))
                character["hp_current"] = min(character["hp_current"], character["hp_max"])
                hp_c = character["hp_current"]
                hp_m = character["hp_max"]
                bar  = hp_bar(hp_c, hp_m)
                line = Text(f"HP  ") + bar
                console.print(line)
                if hp_c == 0:
                    console.print(f"[bold {RED}]You have fallen.[/bold {RED}]")
            except ValueError:
                console.print(f"[red]Expected a number.[/red]")

    elif key == "/inv":
        if len(parts) < 3:
            console.print(f"[{DIM}]Usage: /inv add <item>  or  /inv remove <item>[/{DIM}]")
        else:
            action = parts[1].lower()
            item   = " ".join(parts[2:])
            inv    = character.setdefault("inventory", [])
            if action == "add":
                inv.append(item)
                console.print(f"[{DIM}]Added '{item}' to inventory.[/{DIM}]")
            elif action in ("remove", "rm", "drop"):
                matches = [i for i in inv if item.lower() in i.lower()]
                if matches:
                    inv.remove(matches[0])
                    console.print(f"[{DIM}]Removed '{matches[0]}' from inventory.[/{DIM}]")
                else:
                    console.print(f"[{DIM}]'{item}' not found in inventory.[/{DIM}]")
            else:
                console.print(f"[{DIM}]Unknown action '{action}'. Use 'add' or 'remove'.[/{DIM}]")

    elif key == "/effect":
        if len(parts) < 3:
            console.print(f"[{DIM}]Usage: /effect add <name>  or  /effect remove <name>[/{DIM}]")
        else:
            action = parts[1].lower()
            effect = " ".join(parts[2:])
            fx     = character.setdefault("effects", [])
            if action == "add":
                fx.append(effect)
                console.print(f"[{DIM}]Effect '{effect}' applied.[/{DIM}]")
            elif action in ("remove", "rm", "cure"):
                matches = [e for e in fx if effect.lower() in e.lower()]
                if matches:
                    fx.remove(matches[0])
                    console.print(f"[{DIM}]Effect '{matches[0]}' removed.[/{DIM}]")
                else:
                    console.print(f"[{DIM}]Effect '{effect}' not found.[/{DIM}]")
            else:
                console.print(f"[{DIM}]Unknown action '{action}'. Use 'add' or 'remove'.[/{DIM}]")

    elif key == "/difficulty":
        if len(parts) < 2 or parts[1].lower() not in DIFFICULTY_RULES:
            opts = " | ".join(DIFFICULTY_RULES.keys())
            console.print(f"[{DIM}]Usage: /difficulty {opts}[/{DIM}]")
        else:
            character["difficulty"] = parts[1].lower()
            console.print(f"[{DIM}]Difficulty set to {character['difficulty']}.[/{DIM}]")

    elif key == "/save":
        if save_path:
            save_session(save_path, character, history)
            console.print(f"[{DIM}]Session saved → {save_path}[/{DIM}]")
        else:
            console.print(f"[{DIM}]No save path set. Restart with --save <path>.[/{DIM}]")

    elif key in ("/quit", "/exit"):
        return "quit"

    else:
        console.print(f"[{DIM}]Unknown command. Type /help for a list.[/{DIM}]")

    console.print()
    return "continue"


# ── Character creation ────────────────────────────────────────────────────────

def character_creation() -> dict:
    console.print()
    console.rule(f"[bold {GOLD}]Character Creation[/bold {GOLD}]")
    console.print()

    # Name
    name = Prompt.ask(f"[bold white]Character name[/bold white]").strip() or "Adventurer"

    # Class
    console.print()
    console.print(f"[{GOLD}]Choose your class:[/{GOLD}]\n")
    classes = list(CHARACTER_CLASSES.keys())
    for i, (cls, desc) in enumerate(CHARACTER_CLASSES.items(), 1):
        hp = DEFAULT_HP.get(cls, 12)
        console.print(
            f"  [bold white]{i}.[/bold white] [{GOLD}]{cls:<10}[/{GOLD}]  "
            f"[{DIM}]{desc}  (HP {hp})[/{DIM}]"
        )
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
        console.print(f"[red]Enter a number from 1 to {len(classes)}.[/red]")

    # HP max (pre-filled from class default)
    default_hp = DEFAULT_HP.get(chosen_class, 12)
    console.print()
    while True:
        raw = Prompt.ask(
            f"[bold white]Starting HP[/bold white] [{DIM}](default {default_hp})[/{DIM}]",
            default=str(default_hp),
        )
        try:
            hp_max = max(1, int(raw))
            break
        except ValueError:
            console.print(f"[red]Enter a number.[/red]")

    # Difficulty
    console.print()
    console.print(f"[{GOLD}]Difficulty:[/{GOLD}]\n")
    diff_options = [
        ("easy",   "Success usually comes to the brave"),
        ("normal", "Success and failure are both possible  [dim](recommended)[/dim]"),
        ("hard",   "The world is unforgiving; tread carefully"),
    ]
    for i, (key, label) in enumerate(diff_options, 1):
        console.print(f"  [bold white]{i}.[/bold white] [{GOLD}]{key.capitalize():<8}[/{GOLD}]  {label}")
    console.print()
    while True:
        raw = Prompt.ask(f"[bold white]Difficulty[/bold white]", default="2")
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(diff_options):
                difficulty = diff_options[idx][0]
                break
        except ValueError:
            pass
        console.print(f"[red]Enter 1, 2, or 3.[/red]")

    console.print()
    console.print(Panel(
        Text(
            f"{name} the {chosen_class} steps forth into the dark…\n"
            f"HP {hp_max}/{hp_max}  ·  Difficulty: {difficulty.capitalize()}",
            style=f"italic {CREAM}",
        ),
        border_style=GOLD,
    ))
    console.print()

    return {
        "name":       name,
        "class":      chosen_class,
        "hp_max":     hp_max,
        "hp_current": hp_max,
        "inventory":  [],
        "effects":    [],
        "difficulty": difficulty,
        "memory":     "",
    }


# ── Model loading / scenario resolution ──────────────────────────────────────

def load_pipeline(model_dir: str):
    tok = AutoTokenizer.from_pretrained(model_dir)
    mdl = AutoModelForCausalLM.from_pretrained(model_dir)
    return pipeline("text-generation", model=mdl, tokenizer=tok, device=-1)


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
    p = argparse.ArgumentParser(description="DnD Offline Pro — AI dungeon master, fully offline")
    p.add_argument("--model",    default=None)
    p.add_argument("--scenario", default="dungeon",
                   help="dungeon (default), tavern, wilderness, or a JSON path")
    p.add_argument("--save",     default=None, help="Auto-save session JSON path")
    p.add_argument("--load",     default=None, help="Resume a saved session JSON")
    return p.parse_args()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    console.print()
    console.rule(f"[bold {GOLD}]DnD Offline Pro[/bold {GOLD}]")
    console.print(f"[{DIM}]Fully local · No network calls after install · /help for commands[/{DIM}]\n")

    # Character setup
    if args.load:
        raw_char, history = load_session(args.load)
        character = normalize_character(raw_char)
        if not raw_char:
            console.print(f"[{DIM}]No character in save — starting character creation.[/{DIM}]\n")
            character = character_creation()
        else:
            console.print(f"[{DIM}]Session resumed from {args.load}[/{DIM}]\n")
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
        console.print(f"[red]Could not load model from {model_dir}\n{e}[/red]")
        sys.exit(1)

    # Opening scene
    opening = resolve_opening(args.scenario)
    if args.load and history:
        last = next((m["content"] for m in reversed(history)
                     if m.get("role") == "assistant"), opening)
        typewriter(last)
    else:
        history.append({"role": "assistant", "content": opening})
        typewriter(opening)

    session_start = time.time()
    turn = 0

    try:
        while True:
            console.rule(style=f"dim {BORDER}")

            # HUD line
            hp_c    = character.get("hp_current", "?")
            hp_m    = character.get("hp_max", "?")
            elapsed = format_duration(time.time() - session_start)
            console.print(
                f"[bold {GOLD}]{character['name']}[/bold {GOLD}] "
                f"[{DIM}]({character['class']} · "
                f"HP {hp_c}/{hp_m} · "
                f"T{turn + 1} · {elapsed})[/{DIM}]"
            )

            action = Prompt.ask(f"[{CREAM}]>[/{CREAM}]")

            if action.lower() in ("exit", "quit"):
                console.print(f"\n[italic {DIM}]The dungeon sighs and releases you. Farewell.[/italic {DIM}]")
                break

            # /undo handled in the loop so it can modify turn
            if action.lower().strip() == "/undo":
                if len(history) >= 2:
                    history = history[:-2]
                    turn    = max(0, turn - 1)
                    console.print(f"[{DIM}]Last turn undone.[/{DIM}]\n")
                else:
                    console.print(f"[{DIM}]Nothing to undo.[/{DIM}]\n")
                continue

            if action.startswith("/"):
                result = handle_command(action, character, history, args.save)
                if result == "quit":
                    console.print(f"\n[italic {DIM}]The dungeon sighs and releases you. Farewell.[/italic {DIM}]")
                    break
                continue

            # Generate narrator response
            with console.status(
                f"[italic {DIM}]The narrator considers…[/italic {DIM}]",
                spinner="dots", spinner_style=GOLD,
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

            history.append({"role": "user",      "content": action})
            history.append({"role": "assistant",  "content": out})
            if len(history) > 8:
                del history[:-8]

            turn += 1

            # Session memory — summarise every MEMORY_INTERVAL turns
            if turn > 0 and turn % MEMORY_INTERVAL == 0:
                with console.status(
                    f"[{DIM}]Updating session memory…[/{DIM}]",
                    spinner="dots", spinner_style=GOLD,
                ):
                    character["memory"] = generate_memory(generator, history)
                console.print(f"[{DIM}]Session memory updated.[/{DIM}]\n")

            if args.save:
                save_session(args.save, character, history)

    except KeyboardInterrupt:
        console.print(f"\n[italic {DIM}]Session ended.[/italic {DIM}]")


if __name__ == "__main__":
    main()
