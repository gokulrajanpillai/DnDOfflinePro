import os
import sys
import json
import argparse
import textwrap
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

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL = os.path.join(APP_DIR, "..", "models", "qwen2_5_0_5b_instruct")

INTRO = (
    "Welcome to DnD Offline Pro\n"
    "Play an endless dungeon story. Fully local. No network calls after install.\n\n"
    "Type 'exit' to end the session."
)

SHORT_RULE = (
    "You are the Dungeon narrator. Write one vivid paragraph under 110 words. "
    "Second person, fantasy tone, rich sensory detail, light wit, no modern slang. "
    "Always end with the question: What do you do next?"
)

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


def parse_args():
    parser = argparse.ArgumentParser(
        description="DnD Offline Pro — AI dungeon master, fully offline"
    )
    parser.add_argument(
        "--model", default=None,
        help="Path to a local model directory (default: models/qwen2_5_0_5b_instruct)",
    )
    parser.add_argument(
        "--scenario", default="dungeon",
        help=(
            "Starting scenario: 'dungeon' (default), 'tavern', 'wilderness', "
            "or a path to a custom scenario JSON file."
        ),
    )
    parser.add_argument(
        "--save", default=None,
        help="Path to auto-save session history as JSON after each turn.",
    )
    parser.add_argument(
        "--load", default=None,
        help="Path to a previously saved session JSON to resume.",
    )
    return parser.parse_args()


def resolve_opening(scenario_arg):
    if scenario_arg in SCENARIOS:
        return SCENARIOS[scenario_arg]
    scenario_path = Path(scenario_arg)
    if scenario_path.exists():
        with open(scenario_path) as f:
            data = json.load(f)
        return data["opening"]
    print(f"Unknown scenario '{scenario_arg}'. Choose from: {', '.join(SCENARIOS)} or provide a JSON file path.")
    sys.exit(1)


def save_session(path, history):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(history, f, indent=2)


def load_session(path):
    with open(path) as f:
        return json.load(f)


def wrap(txt):
    return textwrap.fill(txt.strip(), width=90)


def load_pipeline(model_dir):
    print("Loading local model... ", end="", flush=True)
    tok = AutoTokenizer.from_pretrained(model_dir)
    mdl = AutoModelForCausalLM.from_pretrained(model_dir)
    gen = pipeline("text-generation", model=mdl, tokenizer=tok, device=-1)
    print("done.", flush=True)
    return gen


def build_prompt(tokenizer, history, player_action):
    msgs = [{"role": "system", "content": SHORT_RULE}]
    tail = [m for m in history if m.get("role") == "assistant"][-3:]
    msgs.extend(tail)
    user_text = (
        f"The player attempts this: {player_action}. "
        "Describe the immediate result in one paragraph and then ask: What do you do next?"
    )
    msgs.append({"role": "user", "content": user_text})

    if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
        return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

    recent = " ".join(m["content"] for m in tail) if tail else ""
    return (
        f"<SYSTEM>\n{SHORT_RULE}\n</SYSTEM>\n"
        + (f"<ASSISTANT>\n{recent}\n</ASSISTANT>\n" if recent else "")
        + f"<USER>\n{user_text}\n</USER>\n<ASSISTANT>\n"
    )


def main():
    args = parse_args()

    model_dir = args.model or DEFAULT_MODEL
    opening = resolve_opening(args.scenario)

    print(wrap(INTRO), flush=True)

    try:
        generator = load_pipeline(model_dir)
    except Exception as e:
        print("Could not load local model. Ensure the folder exists:", flush=True)
        print(model_dir, flush=True)
        print(e)
        sys.exit(1)

    if args.load:
        history = load_session(args.load)
        print(f"[Session resumed from {args.load}]", flush=True)
        last_narrator = next(
            (m["content"] for m in reversed(history) if m.get("role") == "assistant"), opening
        )
        print(wrap(last_narrator), flush=True)
    else:
        history = []
        print(wrap(opening), flush=True)
        history.append({"role": "assistant", "content": opening})

    try:
        while True:
            action = input("\nWhat do you do? > ").strip()
            if action.lower() in ["exit", "quit"]:
                print("The dungeon sighs and releases you. Farewell.", flush=True)
                break

            print("Thinking...", flush=True)
            prompt = build_prompt(generator.tokenizer, history, action)

            out = generator(
                prompt,
                max_new_tokens=140,
                do_sample=True,
                temperature=0.85,
                top_p=0.92,
                repetition_penalty=1.05,
                eos_token_id=generator.tokenizer.eos_token_id,
                pad_token_id=generator.tokenizer.eos_token_id,
                num_return_sequences=1,
                return_full_text=False,
            )[0]["generated_text"]

            print()
            print(wrap(out), flush=True)

            history.append({"role": "user", "content": f"The player attempts this: {action}."})
            history.append({"role": "assistant", "content": out})
            if len(history) > 8:
                del history[:-8]

            if args.save:
                save_session(args.save, history)

    except KeyboardInterrupt:
        print("\nSession ended.", flush=True)


if __name__ == "__main__":
    main()
