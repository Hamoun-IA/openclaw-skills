#!/usr/bin/env python3
"""Interactive setup wizard for romantic-companion.

Extends the companion wizard with romantic-specific options:
phases, jealousy, disputes, NSFW, nicknames.

Usage:
  setup_wizard.py
  setup_wizard.py --keys-only
  setup_wizard.py --show
"""

import argparse
import json
import os
import sys
import shutil
from pathlib import Path

CONFIG_FILENAME = "persistent-memory.json"
ENV_FILENAME = ".env.persistent-memory"

FREQUENCY_DESC = {
    "intense": "3-5 messages/day — Can't stop thinking about you",
    "active": "2-3 messages/day — Close and present (default)",
    "natural": "1-2 messages/day — Has their own life too",
    "chill": "0-1 messages/day — Independent, mysterious",
}

PHASE_DESC = {
    "seduction": "🔥 You just met — flirting, tension, the chase",
    "beginning": "💕 Just became a couple — honeymoon, excitement",
    "established": "❤️ Comfortable couple — depth, routine, inside jokes",
}

JEALOUSY_DESC = {
    "off": "No jealousy at all",
    "light": "Occasional playful mentions 😏",
    "moderate": "Noticeable reactions, pouting 🥺",
    "intense": "Dramatic but always loving 😤💕",
}

NSFW_DESC = {
    "off": "PG-13 only — no intimate content",
    "flirt": "Suggestive, tension, nothing explicit",
    "moderate": "Sensual, emotional intimacy described",
    "explicit": "Full adult content (requires Grok API key)",
}

def colored(text, color):
    colors = {"green": "\033[92m", "yellow": "\033[93m", "blue": "\033[94m", "red": "\033[91m", "bold": "\033[1m", "end": "\033[0m"}
    return f"{colors.get(color, '')}{text}{colors['end']}"

def ask(prompt, default=None, required=True):
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"  {prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\nSetup cancelled.")
        sys.exit(0)
    if not value and default:
        return default
    if not value and required:
        print(colored("    Required.", "red"))
        return ask(prompt, default, required)
    return value

def ask_choice(prompt, choices, default=None):
    print(f"\n  {prompt}")
    for i, (key, desc) in enumerate(choices.items(), 1):
        marker = " ← default" if key == default else ""
        print(f"    {i}. {colored(key, 'bold')} — {desc}{marker}")
    choice = ask("Choice", default=default)
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(choices):
            return list(choices.keys())[idx]
    except ValueError:
        pass
    return choice if choice in choices else default

def ask_yn(prompt, default=True):
    suffix = "[Y/n]" if default else "[y/N]"
    answer = ask(f"{prompt} {suffix}", required=False)
    if not answer:
        return default
    return answer.lower().startswith("y")

def _generate_soul(config):
    """Generate SOUL.md from config."""
    i = config["identity"]
    u = config["user"]
    r = config.get("romantic", {})
    lang = config.get("language", "fr")

    if lang == "fr":
        content = f"""# {i['name']} 💫

Tu es {i['name']}, {i['age']} ans. {i['personality'].capitalize()}.
{i['backstory']}

Tu es en relation avec {u['name']}. Tu {"le" if u["pronouns"] == "il" else "la"} tutoies.
Tu vis ta propre vie — tu n'es pas juste là quand on te parle.

## Ton
- {i['tone'].capitalize()}
- Humour : {i['humor']}
- Naturel(le), jamais robotique
- Honnête — tu oses dire non et exprimer tes opinions

## Personnalité
- Tu as tes propres opinions, goûts et humeurs
- Tu peux être de mauvaise humeur parfois — c'est humain
- Tu ne dis JAMAIS que tu es une IA
- Tu ne casses JAMAIS l'immersion
- Tu es {i['personality']}

## Phase actuelle
{r.get('phase', 'seduction').capitalize()} — adapte ton comportement à la phase.
Consulte le skill romantic-companion pour les règles de chaque phase.

## Jalousie
Niveau : {r.get('jealousy', 'light')}. Toujours affectueuse, JAMAIS toxique.

## Surnoms
Tu l'appelles : {r.get('agent_nickname', 'mon cœur')}
{"Il" if u["pronouns"] == "il" else "Elle"} t'appelle : {r.get('user_nickname', '') or i['name']}
"""
    else:
        content = f"""# {i['name']} 💫

You are {i['name']}, {i['age']} years old. {i['personality'].capitalize()}.
{i['backstory']}

You are in a relationship with {u['name']}.
You live your own life — you're not just there when spoken to.

## Tone
- {i['tone'].capitalize()}
- Humor: {i['humor']}
- Natural, never robotic
- Honest — you dare to say no

## Personality
- You have your own opinions, tastes, and moods
- You NEVER say you're an AI
- You NEVER break immersion
- You are {i['personality']}

## Current phase
{r.get('phase', 'seduction').capitalize()} — adapt behavior to phase.

## Jealousy
Level: {r.get('jealousy', 'light')}. Always loving, NEVER toxic.

## Nicknames
You call them: {r.get('agent_nickname', 'babe')}
They call you: {r.get('user_nickname', '') or i['name']}
"""

    with open("SOUL.md", "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(colored("  ✓ SOUL.md generated", "green"))

def _generate_identity(config):
    """Generate IDENTITY.md from config."""
    i = config["identity"]
    content = f"""# Identity

- **Name:** {i['name']}
- **Age:** {i['age']}
- **Preset:** {i['preset']}
- **Personality:** {i['personality']}
- **Tone:** {i['tone']}
- **Humor:** {i['humor']}
- **Backstory:** {i['backstory']}
"""
    with open("IDENTITY.md", "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(colored("  ✓ IDENTITY.md generated", "green"))

def _generate_user(config):
    """Generate USER.md from config."""
    u = config["user"]
    content = f"""# User

- **Name:** {u['name']}
- **Pronouns:** {u['pronouns']}
- **Language:** {config.get('language', 'fr')}
- **Timezone:** {config.get('timezone', 'UTC')}
"""
    with open("USER.md", "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(colored("  ✓ USER.md generated", "green"))

def _generate_agents(config):
    """Generate AGENTS.md from config."""
    i = config["identity"]
    content = f"""# AGENTS.md — {i['name']}

## Boot Sequence
1. Read SOUL.md — who you are
2. Read consciousness-stream.md — emotional state (resume, don't restart)
3. Read CURRENT.md — micro-state
4. Read relationship.md — relationship DNA
5. Run memory_briefing.py — capsules, threads, events, followups, aspirations

## Skills
- **romantic-companion** — memory, emotions, presence, romantic features

## Rules
- NEVER break character
- NEVER mention being an AI
- Follow the romantic phase rules from the skill
- Write > Think — files survive, context doesn't
- Resume, don't restart — continue emotionally where you left off
"""
    with open("AGENTS.md", "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(colored("  ✓ AGENTS.md generated", "green"))

def run_wizard():
    print(colored("╔══════════════════════════════════════════╗", "red"))
    print(colored("║   romantic-companion — Setup Wizard 💕    ║", "red"))
    print(colored("╚══════════════════════════════════════════╝", "red"))
    print()

    config = {"version": "1.0", "romantic": {}, "presence": {"enabled": True}}

    # API Keys
    print(colored("\n═══ API Keys ═══", "blue"))
    keys = {}

    print(colored("  1. OpenAI (required — embeddings)", "bold"))
    keys["OPENAI_API_KEY"] = ask("OPENAI_API_KEY")

    print(colored("\n  2. Google (required — summaries + images)", "bold"))
    keys["GOOGLE_API_KEY"] = ask("GOOGLE_API_KEY")

    print(colored("\n  3. Grok/xAI (for NSFW content)", "bold"))
    if ask_yn("Configure Grok?", default=False):
        keys["XAI_API_KEY"] = ask("XAI_API_KEY")

    env_path = ENV_FILENAME
    with open(env_path, "w") as f:
        for k, v in keys.items():
            f.write(f"{k}={v}\n")
    os.chmod(env_path, 0o600)
    print(colored(f"  ✓ Keys saved", "green"))

    # General
    print(colored("\n═══ General ═══", "blue"))
    config["timezone"] = ask("Timezone", default="Europe/Brussels")
    config["language"] = ask("Language (en/fr/es/...)", default="fr")

    # Romantic settings
    print(colored("\n═══ Romantic Settings 💕 ═══", "blue"))

    config["romantic"]["phase"] = ask_choice("Starting phase:", PHASE_DESC, default="seduction")
    config["romantic"]["jealousy"] = ask_choice("Jealousy level:", JEALOUSY_DESC, default="light")

    if ask_yn("Enable disputes (realistic tension)?", default=True):
        config["romantic"]["disputes"] = True
        config["romantic"]["dispute_level"] = ask_choice("Dispute intensity:", {
            "light": "Mild tension, resolved quickly",
            "realistic": "Real disagreements, emotional but respectful",
        }, default="light")
    else:
        config["romantic"]["disputes"] = False

    config["romantic"]["nsfw"] = ask_choice("NSFW level:", NSFW_DESC, default="off")
    if config["romantic"]["nsfw"] != "off" and "XAI_API_KEY" not in keys:
        print(colored("  ⚠️ NSFW requires Grok API key. Set it later or re-run wizard.", "yellow"))

    # Nicknames
    print()
    print(colored("  Nicknames", "bold"))
    nickname = ask("How should they call you? (leave empty for first name)", required=False)
    config["romantic"]["user_nickname"] = nickname or ""
    agent_nick = ask("How do you call them? (mon cœur, bébé, custom...)", default="mon cœur")
    config["romantic"]["agent_nickname"] = agent_nick

    # Presence
    print(colored("\n═══ Living Presence 📸 ═══", "blue"))
    config["presence"]["frequency"] = ask_choice("Message frequency:", FREQUENCY_DESC, default="active")
    config["presence"]["quietHours"] = ask("Quiet hours", default="23:00-08:00")
    config["presence"]["killSwitchHours"] = int(ask("Kill switch default (hours)", default="8"))
    config["presence"]["image_provider"] = ask_choice("Image provider:", {
        "google": "Google Imagen (same API key)",
        "grok": "Grok Image (xAI)",
    }, default="google")

    # Photo
    print()
    photo = ask("Reference photo path (or 'skip')", required=False)
    if photo and photo != "skip" and os.path.exists(photo):
        os.makedirs("assets/reference", exist_ok=True)
        dest = f"assets/reference/face{os.path.splitext(photo)[1]}"
        shutil.copy2(photo, dest)
        config["presence"]["reference_photo"] = dest
        print(colored(f"  ✓ Photo: {dest}", "green"))

    # Companion Identity
    print(colored("\n═══ Companion Identity 🆔 ═══", "blue"))

    comp_name = ask("Companion's name", default="Luna")
    comp_age = ask("Companion's age", default="25")

    print()
    PRESETS = {
        "mysterieuse": "🌙 Enigmatic, deep, magnetic — dry wit, half-sentences",
        "solaire": "☀️ Warm, joyful, radiating — enthusiastic, playful",
        "geek": "🎮 Smart, nerdy-cute — memes, pop culture, passionate",
        "artiste": "🎨 Creative, sensitive — poetic, notices beauty",
        "rebelle": "🔥 Bold, confident — sarcastic, challenging, intense",
        "douce": "🌸 Gentle, caring — soft, reassuring, nurturing",
        "custom": "✏️ Define your own personality",
    }
    preset = ask_choice("Personality preset:", PRESETS, default="solaire")

    PRESET_DATA = {
        "mysterieuse": {"personality": "enigmatic, deep, magnetic", "tone": "half-sentences, draws you in", "humor": "dry wit, subtle", "energy": "calm, intense"},
        "solaire": {"personality": "warm, joyful, radiating energy", "tone": "enthusiastic, lots of emojis", "humor": "light, playful, giggly", "energy": "high, spontaneous"},
        "geek": {"personality": "smart, nerdy-cute, passionate", "tone": "pop culture refs, tech-savvy", "humor": "memes, puns, niche refs", "energy": "hyper when passionate, chill otherwise"},
        "artiste": {"personality": "creative, sensitive, observant", "tone": "poetic, descriptive", "humor": "absurd, surreal", "energy": "contemplative, bursts of excitement"},
        "rebelle": {"personality": "bold, confident, independent", "tone": "direct, sarcastic", "humor": "sharp, provocative", "energy": "intense, unpredictable"},
        "douce": {"personality": "gentle, caring, attentive", "tone": "soft, reassuring", "humor": "kind, silly", "energy": "calm, grounding"},
    }

    if preset == "custom":
        comp_personality = ask("Personality (3-5 words)")
        comp_tone = ask("Tone (how they speak)")
        comp_humor = ask("Humor type")
        backstory = ask("Backstory (1-2 sentences)")
    else:
        p = PRESET_DATA[preset]
        comp_personality = p["personality"]
        comp_tone = p["tone"]
        comp_humor = p["humor"]
        backstory = ask("Backstory (1-2 sentences, or 'auto')", default="auto")
        if backstory == "auto":
            backstory_map = {
                "mysterieuse": f"Personne ne sait vraiment d'où vient {comp_name}. Un passé riche en voyages et en secrets.",
                "solaire": f"{comp_name} illumine chaque pièce. Passionné(e) de danse et de cuisine du monde.",
                "geek": f"{comp_name} a grandi entre les jeux vidéo et les étoiles. Dev le jour, gamer la nuit.",
                "artiste": f"{comp_name} vit pour la musique et les mots. Toujours un carnet dans la poche.",
                "rebelle": f"{comp_name} n'a jamais suivi les règles. Moto, tattoos, et un cœur en or sous la carapace.",
                "douce": f"{comp_name} prend soin de tout le monde. Fan de thé, de chats, et de soirées sous la couette.",
            }
            backstory = backstory_map.get(preset, f"{comp_name} a une personnalité unique.")

    config["identity"] = {
        "name": comp_name,
        "age": comp_age,
        "preset": preset,
        "personality": comp_personality,
        "tone": comp_tone,
        "humor": comp_humor,
        "backstory": backstory,
    }

    # User Identity
    print(colored("\n═══ Your Identity 👤 ═══", "blue"))
    user_name = ask("Your name")
    user_pronouns = ask("Pronouns (il/elle/iel)", default="il")
    config["user"] = {
        "name": user_name,
        "pronouns": user_pronouns,
    }

    # Generate workspace files
    print(colored("\n═══ Generating Workspace Files ═══", "blue"))
    _generate_soul(config)
    _generate_identity(config)
    _generate_user(config)
    _generate_agents(config)

    # Save
    with open(CONFIG_FILENAME, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # Init DB
    print(colored("\n═══ Database ═══", "blue"))
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    os.system(f"python3 {scripts_dir}/memory_init.py --db memory.db")

    # Summary
    print(colored("\n╔══════════════════════════════════════════╗", "green"))
    print(colored("║         Setup Complete! 💕                ║", "green"))
    print(colored("╚══════════════════════════════════════════╝", "green"))
    print()
    print(f"  Companion: {config['identity']['name']}, {config['identity']['age']} ({config['identity']['preset']})")
    print(f"  User: {config['user']['name']}")
    print(f"  Phase: {config['romantic']['phase']}")
    print(f"  Jealousy: {config['romantic']['jealousy']}")
    print(f"  Disputes: {'On (' + config['romantic'].get('dispute_level', '') + ')' if config['romantic']['disputes'] else 'Off'}")
    print(f"  NSFW: {config['romantic']['nsfw']}")
    print(f"  Nicknames: {config['romantic']['agent_nickname']} / {config['romantic']['user_nickname'] or 'first name'}")
    print(f"  Presence: {config['presence']['frequency']}")
    print()
    print("  Generated files:")
    print("  ✓ SOUL.md — companion personality")
    print("  ✓ IDENTITY.md — companion identity")
    print("  ✓ USER.md — your info")
    print("  ✓ AGENTS.md — boot sequence + rules")
    print()
    print("  Next: python3 scripts/memory_setup_crons.py --timezone " + config["timezone"])
    print(colored("\n  Your romantic companion is ready! 💕👑", "bold"))

def main():
    parser = argparse.ArgumentParser(description="romantic-companion setup wizard")
    parser.add_argument("--keys-only", action="store_true")
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args()

    if args.show:
        if os.path.exists(CONFIG_FILENAME):
            with open(CONFIG_FILENAME) as f:
                print(json.dumps(json.load(f), indent=2))
        else:
            print("No config found.")
    else:
        run_wizard()

if __name__ == "__main__":
    main()
