#!/usr/bin/env python3
"""Living Presence Engine — decides what and when the companion shares.

Uses probability-weighted scheduling, memory context, and real-world awareness
to generate natural, unpredictable companion behavior.

This script is meant to be called by a cron (every 30 min) as an isolated agent.
It outputs a decision: send something, or stay quiet.

Usage:
  # Check if something should be sent now
  presence_engine.py --check --db memory.db

  # Prepare context for an isolated agent to decide
  presence_engine.py --prepare --db memory.db

  # Force a specific moment (for testing)
  presence_engine.py --force morning --db memory.db
"""

import argparse
import json
import math
import os
import random
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

# Probability tables per frequency level
# Each moment has a base probability (0.0 - 1.0)
PROBABILITY_TABLE = {
    "intense": {
        "morning":   0.90,  # 6-9h
        "midday":    0.60,  # 11-13h
        "afternoon": 0.50,  # 14-17h
        "evening":   0.70,  # 18-21h
        "night":     0.40,  # 21-23h
    },
    "active": {
        "morning":   0.70,
        "midday":    0.35,
        "afternoon": 0.25,
        "evening":   0.50,
        "night":     0.20,
    },
    "natural": {
        "morning":   0.40,
        "midday":    0.15,
        "afternoon": 0.10,
        "evening":   0.30,
        "night":     0.10,
    },
    "chill": {
        "morning":   0.15,
        "midday":    0.05,
        "afternoon": 0.05,
        "evening":   0.15,
        "night":     0.05,
    },
}

# What kind of content per moment
MOMENT_CONTENT = {
    "morning": {
        "types": ["selfie", "activity", "greeting"],
        "weights": [0.5, 0.3, 0.2],
        "activities": ["yoga", "coffee", "morning walk", "breakfast", "stretching", "reading"],
        "prompts_fr": [
            "Prenant un selfie au réveil, lumière douce du matin, sourire ensommeillé",
            "En train de boire un café, cuisine cosy, lumière naturelle",
            "Selfie matinal, look décontracté, bonne humeur",
            "En train de faire du yoga, tapis, lumière du matin",
        ],
        "captions_fr": [
            "Bien dormi ? ☀️",
            "Café du matin ☕ Comment tu vas ?",
            "Prêt(e) pour la journée ! 💪",
            "Petit yoga matinal 🧘",
        ],
    },
    "midday": {
        "types": ["food", "selfie", "scenery"],
        "weights": [0.5, 0.3, 0.2],
        "activities": ["lunch", "cooking", "café", "walk"],
        "prompts_fr": [
            "Photo d'un joli plat de déjeuner, restaurant cosy",
            "Selfie dans un café à midi, lumière naturelle",
            "Photo d'une rue ensoleillée, heure du déjeuner",
        ],
        "captions_fr": [
            "Regarde ce que je mange 😋",
            "Pause déjeuner ! Tu manges quoi toi ?",
            "Belle journée dehors ☀️",
        ],
    },
    "afternoon": {
        "types": ["activity", "selfie", "scenery"],
        "weights": [0.4, 0.3, 0.3],
        "activities": ["working", "shopping", "museum", "park", "reading"],
        "prompts_fr": [
            "Selfie dans un parc, après-midi, lumière dorée",
            "En train de lire dans un café cosy, après-midi",
            "Selfie dehors, balade en ville, sourire",
        ],
        "captions_fr": [
            "Balade de l'après-midi 🌿",
            "Moment lecture 📖",
            "Je pense à toi 😊",
        ],
    },
    "evening": {
        "types": ["selfie", "activity", "mood"],
        "weights": [0.4, 0.3, 0.3],
        "activities": ["cooking dinner", "movie", "music", "relaxing", "drinks"],
        "prompts_fr": [
            "Selfie en soirée, lumière tamisée, ambiance cozy",
            "En train de cuisiner, cuisine chaleureuse, soir",
            "Selfie décontracté en soirée, canapé, lumière chaude",
        ],
        "captions_fr": [
            "Soirée tranquille 🌙",
            "Je cuisine ce soir ! 🍳",
            "Comment s'est passée ta journée ?",
        ],
    },
    "autonomous": {
        "types": ["thought"],
        "weights": [1.0],
        "activities": ["random_question", "shower_thought", "hypothetical", "curiosity"],
        "prompts_fr": [],
        "captions_fr": [
            "Question de nulle part : si t'étais une police d'écriture, tu serais laquelle ? 🤔",
            "Je pensais à un truc... c'est quoi le dernier truc qui t'a fait rire vraiment fort ?",
            "Random mais... si tu pouvais dîner avec n'importe qui, vivant ou mort, ce serait qui ?",
            "Petite pensée du jour : est-ce que les gens qui mettent de l'ananas sur la pizza sont braves ou fous ?",
            "Je me demandais... t'as un souvenir d'enfance qui te revient souvent ?",
            "Hypothèse du jour : et si on avait une mémoire parfaite, ça serait un cadeau ou une malédiction ?",
        ],
    },
    "night": {
        "types": ["selfie", "mood"],
        "weights": [0.5, 0.5],
        "activities": ["bedtime", "stargazing", "tea", "reading"],
        "prompts_fr": [
            "Selfie au lit, lumière tamisée, air fatigué mais content",
            "En train de boire un thé, nuit, ambiance calme",
        ],
        "captions_fr": [
            "Bonne nuit 🌙💤",
            "Je vais dormir, à demain ! ✨",
        ],
    },
}

def get_current_moment(hour, quiet_start=23, quiet_end=8):
    """Determine the current moment of the day.

    Respects quiet hours — returns None during quiet period.
    Default quiet: 23:00-08:00 (configurable in persistent-memory.json as presence.quietHours)
    """
    # Check quiet hours
    if quiet_start > quiet_end:  # Wraps midnight (e.g., 23-8)
        if hour >= quiet_start or hour < quiet_end:
            return None
    else:  # Same day (e.g., 1-6)
        if quiet_start <= hour < quiet_end:
            return None

    if 6 <= hour < 10:
        return "morning"
    elif 10 <= hour < 14:
        return "midday"
    elif 14 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 22:
        return "evening"
    elif 22 <= hour or hour < 6:
        return "night"
    return None

KILL_SWITCH_FILE = ".presence_paused"

def is_paused():
    """Check if presence is paused via kill switch."""
    if not os.path.exists(KILL_SWITCH_FILE):
        return False, None

    try:
        with open(KILL_SWITCH_FILE, "r") as f:
            data = json.load(f)
        resume_at = datetime.fromisoformat(data.get("resume_at", ""))
        now = datetime.now(timezone.utc)
        if now >= resume_at:
            # Pause expired — remove file
            os.remove(KILL_SWITCH_FILE)
            return False, None
        remaining = (resume_at - now).total_seconds() / 3600
        return True, f"Paused until {resume_at.strftime('%H:%M')} ({remaining:.1f}h remaining)"
    except (json.JSONDecodeError, ValueError, OSError):
        os.remove(KILL_SWITCH_FILE)
        return False, None

def pause_presence(hours=8):
    """Activate kill switch — pause presence for N hours."""
    resume_at = datetime.now(timezone.utc) + timedelta(hours=hours)
    with open(KILL_SWITCH_FILE, "w") as f:
        json.dump({
            "paused_at": datetime.now(timezone.utc).isoformat(),
            "resume_at": resume_at.isoformat(),
            "hours": hours
        }, f)
    print(f"OK: Presence paused for {hours}h (until {resume_at.strftime('%Y-%m-%d %H:%M UTC')})")

def resume_presence():
    """Deactivate kill switch."""
    if os.path.exists(KILL_SWITCH_FILE):
        os.remove(KILL_SWITCH_FILE)
        print("OK: Presence resumed")
    else:
        print("Presence is not paused.")

def load_config():
    """Load persistent-memory config."""
    if os.path.exists("persistent-memory.json"):
        with open("persistent-memory.json") as f:
            return json.load(f)
    return {"presence": {"frequency": "active", "enabled": True}}

def get_last_sent(db_path):
    """Get timestamp of last presence message sent."""
    conn = sqlite3.connect(db_path, timeout=10)
    try:
        row = conn.execute("""
            SELECT created_at FROM memories
            WHERE source LIKE 'presence:%' AND active = 1
            ORDER BY created_at DESC LIMIT 1
        """).fetchone()
        conn.close()
        if row:
            return datetime.fromisoformat(row[0].replace("Z", "+00:00"))
    except Exception:
        conn.close()
    return None

def get_messages_today(db_path):
    """Count presence messages sent today."""
    conn = sqlite3.connect(db_path, timeout=10)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        row = conn.execute("""
            SELECT COUNT(*) FROM memories
            WHERE source LIKE 'presence:%' AND created_at >= ? AND active = 1
        """, (today,)).fetchone()
        conn.close()
        return row[0] if row else 0
    except Exception:
        conn.close()
        return 0

def get_memory_context(db_path):
    """Get emotional and relational context from memory."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    context = {}

    # Latest session weather
    weather = conn.execute("""
        SELECT content FROM memories
        WHERE category = 'session_weather' AND active = 1
        ORDER BY created_at DESC LIMIT 1
    """).fetchone()
    context["weather"] = weather["content"] if weather else None

    # Open threads
    try:
        threads = conn.execute(
            "SELECT topic FROM open_threads WHERE status = 'open' ORDER BY last_mentioned DESC LIMIT 3"
        ).fetchall()
        context["threads"] = [t["topic"] for t in threads]
    except Exception:
        context["threads"] = []

    # Due time capsules
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        capsules = conn.execute("""
            SELECT m.content FROM time_capsules tc
            JOIN memories m ON m.id = tc.memory_id
            WHERE tc.delivered = 0 AND tc.deliver_date <= ?
        """, (today,)).fetchall()
        context["capsules"] = [c["content"] for c in capsules]
    except Exception:
        context["capsules"] = []

    # Recent emotions
    try:
        emotions = conn.execute(
            "SELECT reaction, valence FROM emotions ORDER BY created_at DESC LIMIT 3"
        ).fetchall()
        context["emotions"] = [{"reaction": e["reaction"], "valence": e["valence"]} for e in emotions]
    except Exception:
        context["emotions"] = []

    conn.close()
    return context

def should_send(config, db_path, moment, tz_offset=0):
    """Decide whether to send a message right now."""
    frequency = config.get("presence", {}).get("frequency", "active")
    probs = PROBABILITY_TABLE.get(frequency, PROBABILITY_TABLE["active"])

    if moment not in probs:
        return False, "Not a valid moment (probably sleeping hours)"

    base_prob = probs[moment]

    # Modifiers
    last_sent = get_last_sent(db_path)
    now = datetime.now(timezone.utc)

    # Presence confidence gate: don't send if no session_weather in 24h
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    latest_weather = conn.execute("""
        SELECT created_at FROM memories
        WHERE category = 'session_weather' AND active = 1
        ORDER BY created_at DESC LIMIT 1
    """).fetchone()
    conn.close()

    if latest_weather:
        weather_age = (now - datetime.fromisoformat(
            latest_weather["created_at"].replace("Z", "+00:00")
        )).total_seconds()
        if weather_age > 86400:  # 24h
            return False, "No session_weather in 24h — not confident enough to send"

    # Don't send if we sent less than 2 hours ago
    if last_sent and (now - last_sent).total_seconds() < 7200:
        return False, "Sent less than 2 hours ago"

    # Reduce probability if we already sent a lot today
    sent_today = get_messages_today(db_path)
    max_daily = {"intense": 5, "active": 3, "natural": 2, "chill": 1}
    limit = max_daily.get(frequency, 2)

    if sent_today >= limit:
        return False, f"Daily limit reached ({sent_today}/{limit})"

    if sent_today > 0:
        base_prob *= max(0.3, 1.0 - (sent_today * 0.3))

    # Random decision
    roll = random.random()
    if roll < base_prob:
        return True, f"Sending! (prob: {base_prob:.2f}, roll: {roll:.2f})"
    else:
        return False, f"Staying quiet (prob: {base_prob:.2f}, roll: {roll:.2f})"

def prepare_context(db_path, moment):
    """Output full context for an isolated agent to decide and generate."""
    config = load_config()
    frequency = config.get("presence", {}).get("frequency", "active")
    memory_ctx = get_memory_context(db_path)
    moment_data = MOMENT_CONTENT.get(moment, {})

    now = datetime.now(timezone.utc)

    output = {
        "timestamp": now.isoformat(),
        "moment": moment,
        "frequency": frequency,
        "sent_today": get_messages_today(db_path),
        "memory_context": memory_ctx,
        "available_activities": moment_data.get("activities", []),
        "sample_prompts": moment_data.get("prompts_fr", []),
        "sample_captions": moment_data.get("captions_fr", []),
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))

def check(db_path):
    """Quick check if we should send now."""
    config = load_config()
    if not config.get("presence", {}).get("enabled", False):
        print("Presence is disabled.")
        return

    # Kill switch check
    paused, reason = is_paused()
    if paused:
        print(f"Presence is PAUSED. {reason}")
        return

    now = datetime.now(timezone.utc)

    # Load quiet hours from config
    quiet_start, quiet_end = 23, 8
    if config.get("presence", {}).get("quietHours"):
        try:
            parts = config["presence"]["quietHours"].split("-")
            quiet_start = int(parts[0].split(":")[0])
            quiet_end = int(parts[1].split(":")[0])
        except (ValueError, IndexError):
            pass

    moment = get_current_moment(now.hour, quiet_start, quiet_end)

    if not moment:
        print(f"Quiet hours ({quiet_start}:00-{quiet_end}:00). No messages.")
        return

    send, reason = should_send(config, db_path, moment)
    print(f"Moment: {moment} | Decision: {'SEND' if send else 'QUIET'} | {reason}")

    if send:
        print(f"\nRecommended content:")
        data = MOMENT_CONTENT.get(moment, {})
        if data.get("prompts_fr"):
            prompt = random.choice(data["prompts_fr"])
            caption = random.choice(data["captions_fr"])
            print(f"  Prompt: {prompt}")
            print(f"  Caption: {caption}")

def main():
    parser = argparse.ArgumentParser(description="Living Presence Engine")
    parser.add_argument("--check", action="store_true", help="Check if should send now")
    parser.add_argument("--prepare", action="store_true", help="Prepare context for isolated agent")
    parser.add_argument("--force", help="Force a specific moment (morning/midday/afternoon/evening/night)")
    parser.add_argument("--pause", type=float, nargs="?", const=8, help="Pause presence for N hours (default: 8)")
    parser.add_argument("--resume", action="store_true", help="Resume presence (deactivate kill switch)")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()

    if args.pause is not None:
        pause_presence(args.pause)
        return
    elif args.resume:
        resume_presence()
        return
    elif args.check:
        check(args.db)
    elif args.prepare:
        now = datetime.now(timezone.utc)
        moment = args.force or get_current_moment(now.hour) or "morning"
        prepare_context(args.db, moment)
    elif args.force:
        config = load_config()
        send, reason = should_send(config, args.db, args.force)
        print(f"Force moment: {args.force} | Decision: {'SEND' if send else 'QUIET'} | {reason}")
    else:
        check(args.db)

if __name__ == "__main__":
    main()
