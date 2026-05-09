import os
import textwrap
import warnings

import gradio as gr
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from transformers.utils import logging as hf_logging

os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore")
hf_logging.set_verbosity_error()

# LOCAL_MODEL_PATH env var lets you point at an already-downloaded model for local dev.
# Falls back to downloading from HF Hub when running in the cloud (HF Spaces).
MODEL_SOURCE = os.environ.get("LOCAL_MODEL_PATH") or "Qwen/Qwen2.5-0.5B-Instruct"

SHORT_RULE = (
    "You are the Dungeon narrator. Write one vivid paragraph under 110 words. "
    "Second person, fantasy tone, rich sensory detail, light wit, no modern slang. "
    "Always end with the question: What do you do next?"
)

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


def build_prompt(tokenizer, history, player_action):
    msgs = [{"role": "system", "content": SHORT_RULE}]
    assistant_turns = [m for m in history if m.get("role") == "assistant"][-3:]
    msgs.extend(assistant_turns)
    user_text = (
        f"The player attempts this: {player_action}. "
        "Describe the immediate result in one paragraph and then ask: What do you do next?"
    )
    msgs.append({"role": "user", "content": user_text})

    if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
        return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

    recent = " ".join(m["content"] for m in assistant_turns) if assistant_turns else ""
    return (
        f"<SYSTEM>\n{SHORT_RULE}\n</SYSTEM>\n"
        + (f"<ASSISTANT>\n{recent}\n</ASSISTANT>\n" if recent else "")
        + f"<USER>\n{user_text}\n</USER>\n<ASSISTANT>\n"
    )


def new_game(scenario_name):
    opening = SCENARIOS[scenario_name]
    return [{"role": "assistant", "content": opening}], ""


def respond(message, history, scenario_name):
    if not message.strip():
        return history, ""

    if not history:
        opening = SCENARIOS[scenario_name]
        history = [{"role": "assistant", "content": opening}]

    gen = get_pipeline()
    prompt = build_prompt(gen.tokenizer, history, message)

    raw = gen(
        prompt,
        max_new_tokens=140,
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
        {"role": "user", "content": message},
        {"role": "assistant", "content": response},
    ]
    if len(history) > 8:
        history = history[-8:]

    return history, ""


HEADER = """
# DnD Offline Pro
**Fully offline AI dungeon master.** No internet after install. No subscription. Runs on any CPU.

This is a cloud preview — [download the offline version](https://github.com/gokulrajanpillai/DnDOfflinePro)
to play with zero network calls on your own machine.
"""

FOOTER = """
---
*Model: Qwen2.5-0.5B-Instruct · CPU inference — allow 15–40 seconds per turn in this demo.*
*The downloaded version runs at the same speed on your hardware, fully offline.*
[GitHub](https://github.com/gokulrajanpillai/DnDOfflinePro) ·
[Support the project](https://github.com/sponsors/gokulrajanpillai)
"""

with gr.Blocks(theme=gr.themes.Base(), title="DnD Offline Pro") as demo:
    gr.Markdown(HEADER)

    with gr.Row():
        scenario_selector = gr.Radio(
            choices=list(SCENARIOS.keys()),
            value="Dungeon",
            label="Starting scenario",
            interactive=True,
        )
        new_game_btn = gr.Button("New Game", variant="primary", scale=0)

    chatbot = gr.Chatbot(
        value=[{"role": "assistant", "content": SCENARIOS["Dungeon"]}],
        type="messages",
        label="Your adventure",
        height=460,
        show_copy_button=True,
        bubble_full_width=False,
    )

    with gr.Row():
        action_input = gr.Textbox(
            placeholder="What do you do?  (e.g. 'I listen at the door')",
            label="Your action",
            scale=5,
            container=False,
        )
        submit_btn = gr.Button("Act", variant="primary", scale=0)

    gr.Markdown(FOOTER)

    submit_btn.click(respond, [action_input, chatbot, scenario_selector], [chatbot, action_input])
    action_input.submit(respond, [action_input, chatbot, scenario_selector], [chatbot, action_input])
    new_game_btn.click(new_game, [scenario_selector], [chatbot, action_input])


if __name__ == "__main__":
    demo.launch()
