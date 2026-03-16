#!/usr/bin/env python3
"""Generate and maintain CURRENT.md — an ultra-light state file (~500 chars max).

This file is the agent's "I wake up and know where I am" snapshot.
It should be injected into the boot context and survives everything.

Usage:
  # Update from the session journal (reads last N messages)
  memory_current.py --from-journal .session_journal.jsonl --db memory.db

  # Update with explicit values
  memory_current.py --mood "taquin" --topic "planification weekend" --relationship "complicité forte" --db memory.db

  # Prepare data for an isolated agent to generate CURRENT.md
  memory_current.py --prepare --db memory.db

  # Read current state
  memory_current.py --read
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

CURRENT_TEMPLATE = """# CURRENT.md
<!-- Updated: {timestamp} -->

**Mood:** {mood}
**Topic:** {topic}
**Context:** {context}
**Relationship:** {relationship}
"""

def read_current(output_path="CURRENT.md"):
    """Read and display current state."""
    if not os.path.exists(output_path):
        print("No CURRENT.md found. Run with --from-journal or --mood to create one.")
        return
    with open(output_path, "r", encoding="utf-8") as f:
        print(f.read())

def update_explicit(output_path, mood, topic, context, relationship):
    """Update CURRENT.md with explicit values."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    content = CURRENT_TEMPLATE.format(
        timestamp=now,
        mood=mood or "neutral",
        topic=topic or "no active topic",
        context=context or "",
        relationship=relationship or ""
    ).strip()

    # Enforce ~500 char limit
    if len(content) > 600:
        content = content[:597] + "..."

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content + "\n")

    print(f"OK: CURRENT.md updated ({len(content)} chars)")
    print(content)

def prepare_context(db_path, journal_path=None):
    """Output raw data for an agent to generate CURRENT.md."""
    parts = []

    # Latest session weather
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row

    weather = conn.execute("""
        SELECT content, created_at FROM memories
        WHERE category = 'session_weather' AND active = 1
        ORDER BY created_at DESC LIMIT 1
    """).fetchone()

    if weather:
        parts.append(f"Latest session weather: {weather['content']}")
        parts.append("")

    # Open threads
    try:
        threads = conn.execute(
            "SELECT topic FROM open_threads WHERE status = 'open' ORDER BY last_mentioned DESC LIMIT 5"
        ).fetchall()
        if threads:
            parts.append("Open threads:")
            for t in threads:
                parts.append(f"  - {t['topic']}")
            parts.append("")
    except sqlite3.OperationalError:
        pass

    # Latest emotions
    try:
        emotions = conn.execute(
            "SELECT reaction, trigger, valence FROM emotions ORDER BY created_at DESC LIMIT 3"
        ).fetchall()
        if emotions:
            parts.append("Recent emotions:")
            for e in emotions:
                parts.append(f"  - {e['reaction']} ({e['valence']})")
            parts.append("")
    except sqlite3.OperationalError:
        pass

    conn.close()

    # Recent journal messages
    if journal_path and os.path.exists(journal_path):
        messages = []
        with open(journal_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        messages.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

        recent = messages[-10:] if len(messages) > 10 else messages
        if recent:
            parts.append("Last messages:")
            for m in recent:
                role = "User" if m.get("role") == "user" else "Agent"
                content = m.get("content", "")[:150]
                parts.append(f"  [{role}] {content}")
            parts.append("")

    if parts:
        print("\n".join(parts))
    else:
        print("No data available for CURRENT.md generation.")

def from_journal(journal_path, db_path, output_path):
    """Quick extraction from journal — deterministic, no LLM needed."""
    messages = []
    if os.path.exists(journal_path):
        with open(journal_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        messages.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    # Get latest weather
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    weather = conn.execute("""
        SELECT content FROM memories WHERE category = 'session_weather' AND active = 1
        ORDER BY created_at DESC LIMIT 1
    """).fetchone()
    conn.close()

    # Extract topic from last user messages
    user_msgs = [m for m in messages if m.get("role") == "user"]
    topic = user_msgs[-1]["content"][:100] if user_msgs else "no active topic"

    # Mood from weather or default
    mood = "neutral"
    if weather:
        mood = weather["content"][:80]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    content = f"""# CURRENT.md
<!-- Updated: {now} -->

**Mood:** {mood}
**Topic:** {topic}
**Messages:** {len(messages)} in current session"""

    if len(content) > 600:
        content = content[:597] + "..."

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

    print(f"OK: CURRENT.md updated ({len(content)} chars)")

def main():
    parser = argparse.ArgumentParser(description="Manage CURRENT.md state file")
    parser.add_argument("--read", action="store_true", help="Read current state")
    parser.add_argument("--prepare", action="store_true", help="Output raw data for agent")
    parser.add_argument("--from-journal", help="Update from journal file")
    parser.add_argument("--mood", help="Explicit mood")
    parser.add_argument("--topic", help="Explicit topic")
    parser.add_argument("--context", help="Explicit context")
    parser.add_argument("--relationship", help="Explicit relationship state")
    parser.add_argument("--output", default="CURRENT.md", help="Output file")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()

    if args.read:
        read_current(args.output)
    elif args.prepare:
        prepare_context(args.db, args.from_journal)
    elif args.from_journal:
        from_journal(args.from_journal, args.db, args.output)
    elif args.mood or args.topic:
        update_explicit(args.output, args.mood, args.topic, args.context, args.relationship)
    else:
        read_current(args.output)

if __name__ == "__main__":
    main()
