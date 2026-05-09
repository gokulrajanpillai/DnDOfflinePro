import os
import textwrap
import warnings

import gradio as gr
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from transformers.utils import logging as hf_logging

os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore")
hf_logging.set_verbosity_error()

MODEL_SOURCE = os.environ.get("LOCAL_MODEL_PATH") or "Qwen/Qwen2.5-0.5B-Instruct"

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
    "Dungeon": (
        "You stand in a cold hall. A door creaks. Something watches."
    ),
    "Tavern": (
        "You warm your hands at the crackling hearth of the Tarnished Flagon. "
        "The barkeep slides you a foaming ale without asking. A hooded stranger "
        "at the corner table catches your eye, then drops a folded note onto your lap."
    ),
    "Wilderness": (
        "Pine needles crunch underfoot as the trail vanishes behind a curtain of fog. "
        "The moon is gone, your torch is nearly spent, and somewhere ahead a wolf "
        "howls — close enough that you can hear it breathe."
    ),
}

_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        tok = AutoTokenizer.from_pretrained(MODEL_SOURCE)
        mdl = AutoModelForCausalLM.from_pretrained(MODEL_SOURCE)
        _pipeline = pipeline("text-generation", model=mdl, tokenizer=tok, device=-1)
    return _pipeline


def build_system_rule(char_name: str, char_class: str) -> str:
    name = char_name.strip() or "Adventurer"
    cls  = char_class if char_class in CHARACTER_CLASSES else "Fighter"
    desc = CHARACTER_CLASSES[cls]
    return (
        f"You are the Dungeon narrator for {name}, a {cls} — {desc}. "
        f"Write one vivid paragraph of up to 180 words. "
        "Second person, fantasy tone, rich sensory detail, light wit, no modern slang. "
        f"Acknowledge {name}'s class abilities when contextually fitting. "
        "Success is never guaranteed — sometimes the player fails, slips, or is surprised. "
        "Reference fortune in flavour only ('luck turns against you', 'fortune smiles briefly'). "
        "End with a hook — a question, a sound, a dying breath, a door opening — "
        "and vary the form and phrasing every single time, never repeating yourself."
    )


def build_prompt(tokenizer, history: list, player_action: str,
                 char_name: str, char_class: str) -> str:
    system_rule = build_system_rule(char_name, char_class)
    msgs = [{"role": "system", "content": system_rule}]
    assistant_turns = [m for m in history if m.get("role") == "assistant"][-3:]
    msgs.extend(assistant_turns)
    msgs.append({"role": "user", "content": player_action})

    if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
        return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

    recent = " ".join(m["content"] for m in assistant_turns) if assistant_turns else ""
    return (
        f"<SYSTEM>\n{system_rule}\n</SYSTEM>\n"
        + (f"<ASSISTANT>\n{recent}\n</ASSISTANT>\n" if recent else "")
        + f"<USER>\n{player_action}\n</USER>\n<ASSISTANT>\n"
    )


def new_game(scenario_name: str, char_name: str, char_class: str):
    name    = char_name.strip() or "Adventurer"
    opening = SCENARIOS[scenario_name]
    intro   = f"*{name} the {char_class} enters the story…*\n\n{opening}"
    return [{"role": "assistant", "content": intro}], ""


def respond(message: str, history: list, scenario_name: str,
            char_name: str, char_class: str):
    if not message.strip():
        return history, ""

    if not history:
        opening = SCENARIOS[scenario_name]
        name    = char_name.strip() or "Adventurer"
        history = [{"role": "assistant", "content": f"*{name} the {char_class} enters the story…*\n\n{opening}"}]

    gen    = get_pipeline()
    prompt = build_prompt(gen.tokenizer, history, message, char_name, char_class)

    raw = gen(
        prompt,
        max_new_tokens=240,
        do_sample=True,
        temperature=0.85,
        top_p=0.92,
        repetition_penalty=1.05,
        eos_token_id=gen.tokenizer.eos_token_id,
        pad_token_id=gen.tokenizer.eos_token_id,
        num_return_sequences=1,
        return_full_text=False,
    )[0]["generated_text"]

    response = textwrap.fill(raw.strip(), width=90)

    history = history + [
        {"role": "user",      "content": message},
        {"role": "assistant", "content": response},
    ]
    if len(history) > 8:
        history = history[-8:]

    return history, ""


# ── Dark fantasy CSS ──────────────────────────────────────────────────────────

CUSTOM_CSS = """
/* Page background */
body, .gradio-container {
    background-color: #0a0a0f !important;
    font-family: 'IM Fell English SC', Georgia, serif !important;
}

/* Gold accent headings */
h1, h2, h3, .prose h1, .prose h2 {
    color: #c9a227 !important;
    letter-spacing: 0.05em;
}

/* Chatbot bubbles */
.message.svelte-1s78gho, [data-testid="bot"] .message-bubble-border,
.bot .bubble-wrap, .message-bubble {
    background-color: #14120c !important;
    border-color: #3d2f1a !important;
    color: #e8d5b7 !important;
    font-family: 'IM Fell English SC', Georgia, serif !important;
    font-size: 1rem !important;
    line-height: 1.7 !important;
}
[data-testid="user"] .message-bubble-border,
.user .bubble-wrap {
    background-color: #1a1a2e !important;
    border-color: #3d2f1a !important;
    color: #e8d5b7 !important;
}

/* Input box */
textarea, input[type="text"] {
    background-color: #14120c !important;
    border-color: #3d2f1a !important;
    color: #e8d5b7 !important;
    font-family: 'Fira Mono', monospace !important;
}
textarea::placeholder, input::placeholder {
    color: #6b5c3e !important;
}

/* Primary buttons (gold) */
button.primary, .primary {
    background-color: #c9a227 !important;
    color: #0a0a0f !important;
    border: none !important;
    font-family: 'Cinzel', serif !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em;
}
button.primary:hover { opacity: 0.85; }

/* Secondary buttons */
button.secondary {
    background-color: #1a1a2e !important;
    border-color: #3d2f1a !important;
    color: #c9a227 !important;
}

/* Radio buttons, labels */
.label-wrap span, label, .wrap span {
    color: #c9a227 !important;
    font-family: 'Cinzel', serif !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.06em;
}

/* Panel / block backgrounds */
.block, .panel, .form {
    background-color: #0f0d09 !important;
    border-color: #3d2f1a !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0a0a0f; }
::-webkit-scrollbar-thumb { background: #3d2f1a; border-radius: 3px; }
"""

GOOGLE_FONTS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IM+Fell+English+SC&family=Cinzel:wght@400;700&family=Fira+Mono&display=swap" rel="stylesheet">
"""

HEADER = """
# DnD Offline Pro
**Fully offline AI dungeon master.** No internet after install. No subscription. Runs on any CPU.

This is a cloud preview — [download the offline version](https://github.com/gokulrajanpillai/DnDOfflinePro) to play with zero network calls on your own machine.
"""

FOOTER = """
---
*Model: Qwen2.5-0.5B-Instruct · CPU inference — allow 15–40 seconds per turn.*
[GitHub](https://github.com/gokulrajanpillai/DnDOfflinePro) · [Support the project](https://github.com/sponsors/gokulrajanpillai)
"""

# ── Layout ────────────────────────────────────────────────────────────────────

with gr.Blocks(theme=gr.themes.Base(), css=CUSTOM_CSS,
               title="DnD Offline Pro") as demo:

    gr.HTML(GOOGLE_FONTS)
    gr.Markdown(HEADER)

    with gr.Row():
        char_name_input = gr.Textbox(
            label="Character name",
            placeholder="e.g. Sable",
            scale=2,
        )
        char_class_input = gr.Dropdown(
            choices=list(CHARACTER_CLASSES.keys()),
            value="Fighter",
            label="Class",
            scale=2,
        )

    with gr.Row():
        scenario_selector = gr.Radio(
            choices=list(SCENARIOS.keys()),
            value="Dungeon",
            label="Starting scenario",
            interactive=True,
        )
        new_game_btn = gr.Button("Begin Adventure", variant="primary", scale=0)

    chatbot = gr.Chatbot(
        value=[{"role": "assistant", "content": SCENARIOS["Dungeon"]}],
        type="messages",
        label="The Chronicle",
        height=480,
        show_copy_button=True,
        bubble_full_width=False,
    )

    with gr.Row():
        action_input = gr.Textbox(
            placeholder="Speak your intent…",
            label="Your action",
            scale=5,
            container=False,
        )
        submit_btn = gr.Button("Proceed", variant="primary", scale=0)

    gr.Markdown(FOOTER)

    # Wire events
    submit_btn.click(
        respond,
        [action_input, chatbot, scenario_selector, char_name_input, char_class_input],
        [chatbot, action_input],
    )
    action_input.submit(
        respond,
        [action_input, chatbot, scenario_selector, char_name_input, char_class_input],
        [chatbot, action_input],
    )
    new_game_btn.click(
        new_game,
        [scenario_selector, char_name_input, char_class_input],
        [chatbot, action_input],
    )


if __name__ == "__main__":
    demo.launch()
