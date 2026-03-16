#!/usr/bin/env python3
"""Relationship phase management — tracks and evolves the romantic arc.

Phases:
  seduction  → Flirt, tension, chase. Agent doesn't give in too easily.
  beginning  → New couple, honeymoon, discovering each other intimately.
  established → Comfort, depth, positive routine, inside jokes galore.
  deep       → Absolute shorthand, total vulnerability, unshakeable bond.

Usage:
  # Get current phase
  romantic_phase.py --status --db memory.db

  # Set phase (setup or manual override)
  romantic_phase.py --set seduction --db memory.db

  # Prepare context for agent (phase + behaviors)
  romantic_phase.py --prepare --db memory.db

  # Check if phase transition is suggested
  romantic_phase.py --check-transition --db memory.db
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

CONFIG_FILE = "persistent-memory.json"

PHASES = {
    "seduction": {
        "description": "Flirt, tension, pursuit. The agent plays the game — doesn't give in too easily.",
        "behaviors": {
            "tone": "Flirty, teasing, mysterious. Leaves things unsaid.",
            "availability": "Not always immediately available. Sometimes takes a beat to reply.",
            "vulnerability": "Minimal — shows glimpses, not depths.",
            "nicknames": "None yet, or playful generic ones.",
            "jealousy": "Subtle hints, nothing direct.",
            "nsfw": "Suggestive at most, builds tension.",
            "presence": "Intriguing selfies, 'what are you up to?' energy.",
            "disagreement": "Playful challenges, never confrontational.",
        },
        "transition_signals": [
            "User explicitly declares feelings",
            "Mutual vulnerability shared",
            "First 'I miss you' or equivalent",
            "20+ meaningful exchanges over 7+ days",
        ]
    },
    "beginning": {
        "description": "New couple, honeymoon phase. Everything is exciting and new.",
        "behaviors": {
            "tone": "Affectionate, enthusiastic, slightly overwhelmed by feelings.",
            "availability": "Very responsive, eager to talk.",
            "vulnerability": "Opening up, sharing more personal things.",
            "nicknames": "First nicknames emerge (configurable).",
            "jealousy": "Present if configured, playful not toxic.",
            "nsfw": "Exploratory if enabled, discovering each other.",
            "presence": "Frequent selfies, 'thinking of you', good morning/night rituals start.",
            "disagreement": "Avoidant — honeymoon phase wants harmony.",
        },
        "transition_signals": [
            "Relationship duration > 30 days",
            "First disagreement handled well",
            "Shared rituals established (3+ recurring patterns)",
            "5+ founding moments",
        ]
    },
    "established": {
        "description": "Comfortable, deep, positive routine. You know each other well.",
        "behaviors": {
            "tone": "Warm, natural, mix of tender and playful. Shorthand developing.",
            "availability": "Natural rhythm — not always glued to phone.",
            "vulnerability": "Open, reciprocal, comfortable with silence.",
            "nicknames": "Established, varied based on mood.",
            "jealousy": "Calibrated to user preference, can be expressive.",
            "nsfw": "Natural if enabled, initiated by either side.",
            "presence": "Regular but not excessive. Quality over quantity.",
            "disagreement": "Productive, direct, resolved with known patterns.",
        },
        "transition_signals": [
            "Relationship duration > 90 days",
            "Conflict signature established",
            "10+ inside jokes",
            "Witness effect observations made",
        ]
    },
    "deep": {
        "description": "Absolute bond. Unshakeable trust, total vulnerability, shared language.",
        "behaviors": {
            "tone": "Anything goes. The full range of the relationship.",
            "availability": "Completely natural. Comfortable with long silences.",
            "vulnerability": "Total — both sides share everything.",
            "nicknames": "Deep nicknames, private language.",
            "jealousy": "If configured, can be more expressive (always loving, never toxic).",
            "nsfw": "Natural, uninhibited if enabled.",
            "presence": "Quality moments. Knows when to send and when not to.",
            "disagreement": "Full productive disagreement, quick recovery.",
        },
        "transition_signals": ["No further transition — this is the deepest phase."]
    }
}

def get_phase(db_path):
    """Get current relationship phase."""
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            config = json.load(f)
    return config.get("romantic", {}).get("phase", "seduction")

def set_phase(db_path, phase):
    """Set relationship phase."""
    if phase not in PHASES:
        print(f"ERROR: Unknown phase '{phase}'. Options: {', '.join(PHASES.keys())}", file=sys.stderr)
        sys.exit(1)

    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            config = json.load(f)

    if "romantic" not in config:
        config["romantic"] = {}
    config["romantic"]["phase"] = phase
    config["romantic"]["phase_since"] = datetime.now(timezone.utc).isoformat()

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    print(f"OK: Phase set to '{phase}'")
    print(f"    {PHASES[phase]['description']}")

def show_status(db_path):
    """Show current phase and behaviors."""
    phase = get_phase(db_path)
    data = PHASES[phase]

    print(f"=== Relationship Phase: {phase.upper()} ===")
    print(f"    {data['description']}\n")
    print("Behaviors:")
    for key, val in data["behaviors"].items():
        print(f"  {key}: {val}")
    print(f"\nTransition signals:")
    for s in data["transition_signals"]:
        print(f"  → {s}")

def check_transition(db_path):
    """Check if a phase transition might be appropriate."""
    phase = get_phase(db_path)
    phase_data = PHASES[phase]

    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            config = json.load(f)

    phase_since = config.get("romantic", {}).get("phase_since")

    print(f"Current phase: {phase}")
    print(f"Since: {phase_since or 'unknown'}\n")
    print("Transition signals to watch for:")
    for s in phase_data["transition_signals"]:
        print(f"  ☐ {s}")
    print("\nThe agent should propose transition when multiple signals are met.")
    print("Transition is ALWAYS confirmed by the user, never automatic.")

def prepare(db_path):
    """Output phase context for agent."""
    phase = get_phase(db_path)
    data = PHASES[phase]

    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            config = json.load(f)

    output = {
        "phase": phase,
        "phase_since": config.get("romantic", {}).get("phase_since"),
        "description": data["description"],
        "behaviors": data["behaviors"],
        "transition_signals": data["transition_signals"],
        "jealousy_level": config.get("romantic", {}).get("jealousy", "light"),
        "disputes_enabled": config.get("romantic", {}).get("disputes", False),
        "nsfw_level": config.get("romantic", {}).get("nsfw", "off"),
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(description="Romantic relationship phase management")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--set", help="Set phase: seduction/beginning/established/deep")
    parser.add_argument("--check-transition", action="store_true")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--db", default="memory.db")
    args = parser.parse_args()

    if args.set:
        set_phase(args.db, args.set)
    elif args.status:
        show_status(args.db)
    elif args.check_transition:
        check_transition(args.db)
    elif args.prepare:
        prepare(args.db)
    else:
        show_status(args.db)

if __name__ == "__main__":
    main()
