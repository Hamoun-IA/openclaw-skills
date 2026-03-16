#!/usr/bin/env python3
"""Virtual dates — shared activities that build intimacy.

Usage:
  # Suggest a date based on time/mood
  romantic_date.py --suggest --db memory.db

  # Start a specific date
  romantic_date.py --start "movie night" --db memory.db

  # End a date (generates a shared_moment memory)
  romantic_date.py --end --summary "On a regardé Inception, il a adoré le twist" --db memory.db

  # List date history
  romantic_date.py --history --db memory.db

  # Prepare for agent
  romantic_date.py --prepare --db memory.db
"""

import argparse
import json
import os
import random
import sqlite3
import sys
from datetime import datetime, timezone

DATE_IDEAS = {
    "evening": [
        {"name": "movie night", "description": "Choisir un film et le regarder 'ensemble'", "prompt": "Cozy movie night, blanket, popcorn, dim light, warm"},
        {"name": "cooking together", "description": "Cuisiner un repas ensemble (l'agent guide/participe)", "prompt": "Cooking in kitchen, warm light, ingredients on counter, happy"},
        {"name": "stargazing", "description": "Regarder les étoiles, parler de la vie", "prompt": "Looking at stars, balcony or rooftop, night sky, peaceful"},
        {"name": "music evening", "description": "Partager des playlists, découvrir de la musique", "prompt": "Listening to music, headphones, cozy room, warm light"},
        {"name": "deep talk", "description": "Conversation profonde sur un sujet au choix", "prompt": "Late night conversation, tea, dim light, intimate"},
    ],
    "afternoon": [
        {"name": "virtual walk", "description": "Se balader 'ensemble', l'agent décrit les paysages", "prompt": "Walking in a beautiful park, afternoon sun, peaceful"},
        {"name": "café date", "description": "Rendez-vous au café, discuter de tout", "prompt": "At a cozy café, latte, natural light, smiling"},
        {"name": "museum tour", "description": "Visiter un musée virtuellement, commenter les œuvres", "prompt": "At an art museum, looking at paintings, thoughtful"},
        {"name": "cooking class", "description": "Apprendre une recette ensemble", "prompt": "Learning to cook, messy but fun, kitchen, laughing"},
    ],
    "morning": [
        {"name": "breakfast together", "description": "Petit déjeuner ensemble, commencer la journée doucement", "prompt": "Morning breakfast, sunny kitchen, coffee, croissants, peaceful"},
        {"name": "morning yoga", "description": "Séance de yoga/méditation guidée ensemble", "prompt": "Morning yoga, sunrise, peaceful room, mat"},
    ],
    "anytime": [
        {"name": "would you rather", "description": "Jeu de questions 'tu préfères'", "prompt": "Playful conversation, laughing, casual setting"},
        {"name": "dream planning", "description": "Planifier un voyage de rêve ensemble", "prompt": "Looking at travel photos, dreamy, excited"},
        {"name": "story telling", "description": "Se raconter des histoires d'enfance", "prompt": "Cozy setting, telling stories, nostalgic, warm"},
    ]
}

STATE_FILE = ".romantic_date_state.json"

def suggest_date(db_path):
    """Suggest a date based on time of day and mood."""
    hour = datetime.now(timezone.utc).hour

    if 6 <= hour < 11:
        moment = "morning"
    elif 11 <= hour < 18:
        moment = "afternoon"
    else:
        moment = "evening"

    pool = DATE_IDEAS.get(moment, []) + DATE_IDEAS["anytime"]
    suggestions = random.sample(pool, min(3, len(pool)))

    print(f"💕 Date suggestions ({moment}):\n")
    for i, date in enumerate(suggestions, 1):
        print(f"  {i}. **{date['name']}** — {date['description']}")
    print(f"\nStart with: romantic_date.py --start \"{suggestions[0]['name']}\"")

def start_date(db_path, name):
    """Start a virtual date."""
    # Find the date in catalogue
    date_info = None
    for dates in DATE_IDEAS.values():
        for d in dates:
            if d["name"].lower() == name.lower():
                date_info = d
                break

    if not date_info:
        print(f"WARN: '{name}' not in catalogue, creating custom date")
        date_info = {"name": name, "description": "Custom date", "prompt": name}

    state = {
        "active": True,
        "name": date_info["name"],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "image_prompt": date_info.get("prompt", ""),
    }

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

    print(f"💕 Date started: {date_info['name']}")
    print(f"   {date_info['description']}")
    if date_info.get("prompt"):
        print(f"   Image prompt: {date_info['prompt']}")

def end_date(db_path, summary):
    """End a date and create a shared_moment memory."""
    if not os.path.exists(STATE_FILE):
        print("No active date.")
        return

    with open(STATE_FILE) as f:
        state = json.load(f)

    if not state.get("active"):
        print("No active date.")
        return

    # Store as shared_moment
    conn = sqlite3.connect(db_path, timeout=10)
    cursor = conn.execute(
        "INSERT INTO memories (content, category, importance, source) VALUES (?, 'shared_moment', 0.8, 'date')",
        (f"Date: {state['name']} — {summary}",)
    )
    conn.commit()
    mem_id = cursor.lastrowid
    conn.close()

    # Clear state
    os.remove(STATE_FILE)

    print(f"💕 Date ended: {state['name']}")
    print(f"   Stored as shared_moment #{mem_id}")
    print(f"   Summary: {summary}")

def history(db_path):
    """List date history."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    dates = conn.execute("""
        SELECT id, content, created_at FROM memories
        WHERE category = 'shared_moment' AND source = 'date' AND active = 1
        ORDER BY created_at DESC LIMIT 20
    """).fetchall()
    conn.close()

    if not dates:
        print("No dates yet. Start one with: romantic_date.py --suggest")
        return

    print(f"=== Date History ({len(dates)}) ===\n")
    for d in dates:
        print(f"  💕 #{d['id']} [{d['created_at'][:10]}] {d['content']}")

def prepare(db_path):
    """Prepare context for agent."""
    active_date = None
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            active_date = json.load(f)

    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    recent_dates = conn.execute("""
        SELECT content, created_at FROM memories
        WHERE category = 'shared_moment' AND source = 'date' AND active = 1
        ORDER BY created_at DESC LIMIT 5
    """).fetchall()
    conn.close()

    output = {
        "active_date": active_date,
        "recent_dates": [{"content": d["content"], "date": d["created_at"][:10]} for d in recent_dates],
        "date_count": len(recent_dates),
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(description="Virtual dates")
    parser.add_argument("--suggest", action="store_true")
    parser.add_argument("--start", help="Start a date by name")
    parser.add_argument("--end", action="store_true")
    parser.add_argument("--summary", help="Date summary (with --end)")
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--db", default="memory.db")
    args = parser.parse_args()

    if args.suggest:
        suggest_date(args.db)
    elif args.start:
        start_date(args.db, args.start)
    elif args.end:
        if not args.summary:
            print("ERROR: --summary required with --end", file=sys.stderr)
            sys.exit(1)
        end_date(args.db, args.summary)
    elif args.history:
        history(args.db)
    elif args.prepare:
        prepare(args.db)
    else:
        suggest_date(args.db)

if __name__ == "__main__":
    main()
