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
    print(f"  Phase: {config['romantic']['phase']}")
    print(f"  Jealousy: {config['romantic']['jealousy']}")
    print(f"  Disputes: {'On (' + config['romantic'].get('dispute_level', '') + ')' if config['romantic']['disputes'] else 'Off'}")
    print(f"  NSFW: {config['romantic']['nsfw']}")
    print(f"  Nicknames: {config['romantic']['agent_nickname']} / {config['romantic']['user_nickname'] or 'first name'}")
    print(f"  Presence: {config['presence']['frequency']}")
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
