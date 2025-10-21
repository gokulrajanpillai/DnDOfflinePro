# src/dnd_offline.py

import os
import sys
import textwrap
import warnings

# Quiet common noise and make prints appear immediately
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

# Point to your downloaded instruct model (recommended for CPU)
# Download once using your fetch script:
#   Qwen/Qwen2.5-0.5B-Instruct  -> models/qwen2_5_0_5b_instruct
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "qwen2_5_0_5b_instruct")

INTRO = (
    "Welcome to DnD Offline Pro\n"
    "Play an endless dungeon story. Fully local. No network calls after install.\n\n"
    "Type exit to end the session."
)

# A single clear rule the model follows every turn
SHORT_RULE = (
    "You are the Dungeon narrator. Write one vivid paragraph under 110 words. "
    "Second person, fantasy tone, rich sensory detail, light wit, no modern slang. "
    "Always end with the question: What do you do next?"
)

# Keep a tiny rolling chat history of narrator turns for continuity
HISTORY = []  # list of dicts like {"role": "assistant", "content": "..."}

def wrap(txt: str) -> str:
    return textwrap.fill(txt.strip(), width=90)

def load_pipeline():
    print("Loading local model... ", end="", flush=True)
    tok = AutoTokenizer.from_pretrained(MODEL_DIR)
    mdl = AutoModelForCausalLM.from_pretrained(MODEL_DIR)
    gen = pipeline("text-generation", model=mdl, tokenizer=tok, device=-1)
    print("done.", flush=True)
    return gen

def build_prompt(tokenizer, history, player_action: str) -> str:
    """
    Use a proper chat template so the model sees roles.
    We send a system rule, a few recent assistant paragraphs, and the new user action.
    """
    msgs = [{"role": "system", "content": SHORT_RULE}]
    # include the last three narrator paragraphs for continuity
    tail = [m for m in history if m.get("role") == "assistant"][-3:]
    msgs.extend(tail)
    user_text = (
        f"The player attempts this: {player_action}. "
        "Describe the immediate result in one paragraph and then ask: What do you do next?"
    )
    msgs.append({"role": "user", "content": user_text})

    # Build a chat-formatted prompt. The model will generate only the assistant turn.
    if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
        return tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)

    # Fallback if the tokenizer lacks a chat template
    recent = " ".join(m["content"] for m in tail) if tail else ""
    return (
        f"<SYSTEM>\n{SHORT_RULE}\n</SYSTEM>\n"
        + (f"<ASSISTANT>\n{recent}\n</ASSISTANT>\n" if recent else "")
        + f"<USER>\n{user_text}\n</USER>\n<ASSISTANT>\n"
    )

def main():
    print(wrap(INTRO), flush=True)

    try:
        generator = load_pipeline()
    except Exception as e:
        print("Could not load local model. Ensure the folder exists:", flush=True)
        print(MODEL_DIR, flush=True)
        print(e)
        sys.exit(1)

    # Opening scene
    opening = "You stand in a cold hall. A door creaks. Something watches."
    print(wrap(opening), flush=True)
    HISTORY.append({"role": "assistant", "content": opening})

    try:
        while True:
            action = input("\nWhat do you do? > ").strip()
            if action.lower() in ["exit", "quit"]:
                print("The dungeon sighs and releases you. Farewell.", flush=True)
                break

            print("Thinking...", flush=True)
            prompt = build_prompt(generator.tokenizer, HISTORY, action)

            # Ask only for the assistant completion to avoid echoing the prompt
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
                return_full_text=False,   # only the completion
            )[0]["generated_text"]

            print()
            print(wrap(out), flush=True)

            # Update short chat history for continuity
            HISTORY.append({"role": "user", "content": f"The player attempts this: {action}."})
            HISTORY.append({"role": "assistant", "content": out})
            if len(HISTORY) > 8:
                del HISTORY[:-8]

    except KeyboardInterrupt:
        print("\nSession ended.", flush=True)

if __name__ == "__main__":
    main()
