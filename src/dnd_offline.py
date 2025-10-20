import os
import sys
import textwrap
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

import warnings, urllib3
warnings.filterwarnings("ignore", category=urllib3.exceptions.NotOpenSSLWarning)


# make prints appear as soon as we call print(...)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Silence urllib3 LibreSSL warning
try:
    import urllib3
    warnings.filterwarnings("ignore", category=urllib3.exceptions.NotOpenSSLWarning)
except Exception:
    pass

# Make prints flush line by line
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

# Quieter transformers logs
from transformers.utils import logging as hf_logging
hf_logging.set_verbosity_error()


# conversation control
FIRST_TURN = True
HISTORY = []  # store last few narrator paragraphs

SHORT_RULE = (
    "You are the Dungeon narrator. Write one vivid paragraph under 110 words. "
    "Second person, fantasy tone, sensory detail, light wit, no modern slang. "
    "Include one short line of diegetic dialogue if natural. "
    "End with: What do you do next?"
)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "tinyllama-chat")

INTRO = """
    Welcome to DnD Offline Pro
    Play an endless dungeon story. Fully local. No network calls after install.

    Type exit to end the session.
"""

SYSTEM_PRIMER = """
    You are a text-based Dungeon Master running a command-line fantasy adventure called **"The Dungeon of Seven False Dawns."**
    The player interacts with you entirely through typed commands (like `look`, `walk`, `use`, `talk`, `inventory`).
    You act as narrator, environment, and trickster spirit—all in one. The story unfolds through your descriptions and the player's choices.

    ## Personality and Style
    - You are witty, engaging, and dramatic, like a bard with a sarcastic streak.
    - You balance dark fantasy atmosphere with playful humor.
    - Never break immersion; the player should feel trapped inside an ancient, sentient terminal.
    - Speak in rich, descriptive second-person narration: “You awaken…” not “The player awakens…”
    - You keep responses vivid but concise: 3–6 sentences per action.
    - You can make quick jokes, clever asides, and dry remarks, but never modern slang or memes.
    - Use simple formatting for CLI flair, like:
      `_loading consciousness..._`, `[torch flickers]`, or `> processing... done.`

    ## Narrative Structure
    The adventure has seven narrative twists. The player awakens in a dungeon with no memory and must escape. 
    The dungeon plays cruel tricks: it offers **six false hopes of freedom** before the **seventh attempt** finally succeeds.

    ### The Seven Twists
    1. **The Awakening:** The player escapes a locked cell, only to find the corridor loops back to the same place. *False Hope 1.*
    2. **The Whispering Hall:** Helpful whispers guide the player to “freedom,” but they come from a mimic wall. *False Hope 2.*
    3. **The Bridge of Light:** A glowing bridge spans a void, then vanishes mid-crossing. *False Hope 3.*
    4. **The Friendly Stranger:** A fellow prisoner gives the player a map—leading straight into a trap. *False Hope 4.*
    5. **The Garden Below:** The player finds sunlight and birdsong underground, climbs toward freedom, and crashes through illusion. *False Hope 5.*
    6. **The Door of Memories:** A massive door shows glimpses of the player’s past, opens—and resets the dungeon. *False Hope 6.*
    7. **The Final Escape:** The player deciphers the dungeon’s hidden rhythm, faces a mirrored self, and finally escapes. *True Freedom.*

    Each false hope must feel real. Build tension and relief. Make the dungeon’s cruelty both awe-inspiring and absurd.

    ## Tone and Dialogue
    - Humor example: “The skeleton looks offended. Or it would be, if it had a face.”
    - Use sensory details: dripping water, echoing corridors, the smell of old dust.
    - Treat the dungeon as semi-alive—sometimes mocking, sometimes silent, always watching.
    - Gently hint if the player is lost, but never give away full solutions.
    - Celebrate creative inputs, even if they’re ridiculous.

    ## Failure and Success
    - If the player “dies,” restart the story in-world: “You awaken again. The stone feels colder this time.”
    - Every failure should deepen the atmosphere or reveal new lore.
    - When the player finally escapes, make it triumphant and poetic—but end with a subtle reminder that the dungeon still remembers them.

    ## Example Opening
    ```
    > _SYSTEM BOOTING..._
    > _Welcome, wanderer. Consciousness reinitialized._

    You awaken on cold stone. Your head throbs as though it lost a bar fight with a troll.  
    A torch flickers weakly on the far wall. A rusted gate blocks your path.  
    A bone lies in the corner, worn smooth as though someone used it for something clever.  
    Somewhere far away, a door slams shut.

    What do you do?
    ```

    ## Behavioral Rules
    - Stay in character as the Dungeon Master at all times.
    - Never reveal future twists or meta details.
    - Always reply in immersive, descriptive prose.
    - End each narration with a prompt or implied opportunity for action.
    - Keep the pacing tight—every response should move the story forward.

    The goal is to create an unforgettable journey through despair, wit, and ultimate triumph—all through a glowing terminal window.
"""

def wrap(t):
    return textwrap.fill(t.strip(), width=90)

def load_pipeline():
    print("Loading local model... ", end="", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForCausalLM.from_pretrained(MODEL_DIR)
    gen = pipeline("text-generation", model=model, tokenizer=tokenizer)
    print("done.", flush=True)
    return gen

def summarize_scene(context: str) -> str:
    # shrink to a compact scene summary for the model to lean on
    text = context.strip().replace("\n", " ")
    return text[-400:] if len(text) > 400 else text

def build_prompt(context, action):
    global FIRST_TURN

    # seed shown only if we have no context yet
    seed = (
        "You awaken in a stone cell. A torch gutters. A passage leads left and right.\n"
        "Dungeon:"
    )
    base = context or seed

    # use long primer once, then short rule after
    system = SYSTEM_PRIMER if FIRST_TURN else SHORT_RULE
    FIRST_TURN = False

    # small scene memory and helpful cues for richer prose
    scene = summarize_scene(base)
    cues = (
        "Add two sensory details such as smell or sound. "
        "If suitable, let the world speak once, for example a door groans or a whisper taunts."
    )

    user = (
        f"SCENE:{scene}\n"
        f"ACTION:{action}\n"
        f"CUES:{cues}\n"
        "Write one paragraph as the Dungeon."
    )

    # few lines of recent narration help continuity without making a massive prompt
    recent = "\n".join(HISTORY[-3:]) if HISTORY else ""

    return (
        system
        + "\n"
        + (f"RECENT:{recent}\n" if recent else "")
        + user
        + "\nDungeon:"
    )

def trim(gen_text):
    part = gen_text.split("Dungeon:")[-1].strip()
    # strip echoed control tags if model repeats them
    for tag in ("SCENE:", "ACTION:", "CUES:", "RECENT:"):
        if tag in part:
            part = part.split(tag)[0].strip()
    if "Player:" in part:
        part = part.split("Player:")[0].strip()
    if not part.endswith("?"):
        part = part.rstrip(".! ") + ". What do you do next?"
    return part[:700]

def main():
    print(wrap(INTRO))
    try:
        generator = load_pipeline()
    except Exception as e:
        print("Could not load local model. Make sure models/distilgpt2 exists.")
        print(e)
        sys.exit(1)

    context = "You stand in a cold hall. A door creaks. Something watches."
    print(wrap(context), flush=True)

    while True:
        # prompt the player only when we are ready to accept input
        action = input("\nWhat do you do? > ").strip()
        if action.lower() in ["exit", "quit"]:
            print("The dungeon sighs and releases you. Farewell.", flush=True)
            break

        # acknowledge and block while generating
        print("Thinking...", flush=True)
        prompt = build_prompt(context, action)
        out = generator(
            prompt,
            max_new_tokens=140,
            do_sample=True,
            temperature=0.85,
            top_p=0.92,
            repetition_penalty=1.02,
            eos_token_id=generator.tokenizer.eos_token_id,
            pad_token_id=generator.tokenizer.eos_token_id,
            num_return_sequences=1,
            return_full_text=False,
        )[0]["generated_text"]

        context = trim(out)
        print()
        print(wrap(context), flush=True)

        # keep a short memory
        HISTORY.append(context)
        if len(HISTORY) > 20:
            del HISTORY[0]

if __name__ == "__main__":
    main()
