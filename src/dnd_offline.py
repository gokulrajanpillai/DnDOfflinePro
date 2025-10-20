import os
import sys
import textwrap
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "distilgpt2")

INTRO = """
Welcome to DnD Offline Pro
Play an endless dungeon story. Fully local. No network calls after install.

Type exit to end the session.
"""

SYSTEM_PRIMER = """
You are the Dungeon. You write short vivid paragraphs.
Keep responses under 120 words. Avoid modern slang.
Describe sights sounds textures and risk.
End each response with a prompt for the player.
"""

def wrap(t):
    return textwrap.fill(t.strip(), width=90)

def load_pipeline():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForCausalLM.from_pretrained(MODEL_DIR)
    gen = pipeline("text-generation", model=model, tokenizer=tokenizer)
    return gen

def build_prompt(context, action):
    seed = (
        "You awaken in a stone cell. A torch gutters. A passage leads left and right.\n"
        "Dungeon:"
    )
    base = context or seed
    user = f"\nPlayer: {action}\nDungeon:"
    return SYSTEM_PRIMER + "\n" + base + user

def trim(gen_text):
    part = gen_text.split("Dungeon:")[-1].strip()
    return part[:700]

def main():
    print(wrap(INTRO))
    try:
        generator = load_pipeline()
    except Exception as e:
        print("Could not load local model. Make sure models/distilgpt2 exists.")
        print(e)
        sys.exit(1)

    context = ""
    while True:
        if not context:
            context = "You stand in a cold hall. A door creaks. Something watches."
            print(wrap(context))
        action = input("\nWhat do you do? > ").strip()
        if action.lower() in ["exit", "quit"]:
            print("The dungeon sighs and releases you. Farewell.")
            break

        prompt = build_prompt(context, action)
        out = generator(
            prompt,
            max_length=len(prompt.split()) + 90,
            do_sample=True,
            temperature=0.9,
            top_p=0.92,
            num_return_sequences=1,
            pad_token_id=generator.tokenizer.eos_token_id
        )[0]["generated_text"]

        context = trim(out)
        print()
        print(wrap(context))

if __name__ == "__main__":
    main()
