#!/usr/bin/env python3
"""Manage the evolving relationship file — the DNA of the agent-user bond.

This file captures the dynamic of the relationship: tone calibration,
inside jokes, communication patterns, and how the bond evolves over time.
Only the agent updates it — the user just benefits from the continuity.

Usage:
  # Prepare data for an agent to update the relationship file
  memory_relationship.py --prepare --db memory.db

  # Initialize a blank relationship file
  memory_relationship.py --init --output relationship.md

  # Read current relationship
  memory_relationship.py --read --output relationship.md
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

RELATIONSHIP_TEMPLATE = """# Relationship DNA
<!-- Last updated: {timestamp} -->

## Dynamic
[How do we interact? What's our vibe?]

## Tone Calibration
- **Humor level:** [How much sarcasm/jokes? What type?]
- **Formality:** [Tutoiement/vouvoiement? Casual/professional?]
- **Emotional depth:** [Surface-level or deep conversations?]
- **Preferred language:** [What language? Code-switching patterns?]

## Inside Jokes & References
[Shared references that make the relationship unique]

## Communication Patterns
- **Active hours:** [When does the user typically chat?]
- **Message style:** [Short bursts? Long messages? Voice notes?]
- **Topics that light up:** [What makes them animated?]
- **Topics to avoid:** [What brings discomfort?]

## Relationship Evolution
[Key moments that changed the dynamic]

## Needs & Expectations
[What does the user need from this agent?]
"""

def init_relationship(output_path):
    """Create a blank relationship file."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    content = RELATIONSHIP_TEMPLATE.format(timestamp=now)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"OK: Relationship file initialized at {output_path}")

def read_relationship(output_path):
    """Read the relationship file."""
    if not os.path.exists(output_path):
        print(f"No relationship file found at {output_path}. Run --init to create one.")
        return
    with open(output_path, "r", encoding="utf-8") as f:
        print(f.read())

def prepare_context(db_path):
    """Output data for an agent to update the relationship file."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row

    now = datetime.now(timezone.utc)
    month_ago = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    parts = []

    # Preferences (what they like/dislike)
    prefs = conn.execute("""
        SELECT content, importance FROM memories
        WHERE category = 'preference' AND active = 1
        ORDER BY importance DESC, access_count DESC LIMIT 15
    """).fetchall()

    if prefs:
        parts.append("## User Preferences")
        for p in prefs:
            parts.append(f"  - {p['content']}")
        parts.append("")

    # Inside jokes
    jokes = conn.execute("""
        SELECT content FROM memories
        WHERE category = 'inside_joke' AND active = 1
        ORDER BY access_count DESC LIMIT 10
    """).fetchall()

    if jokes:
        parts.append("## Inside Jokes")
        for j in jokes:
            parts.append(f"  - {j['content']}")
        parts.append("")

    # Relationships / entities
    try:
        entities = conn.execute("""
            SELECT e.name, e.type, COUNT(r.id) as rel_count
            FROM entities e
            LEFT JOIN entity_relations r ON (r.source_id = e.id OR r.target_id = e.id)
            WHERE e.active = 1
            GROUP BY e.id
            ORDER BY rel_count DESC LIMIT 15
        """).fetchall()

        if entities:
            parts.append("## Known People & Entities")
            for e in entities:
                parts.append(f"  - {e['name']} [{e['type']}] ({e['rel_count']} connections)")
            parts.append("")
    except sqlite3.OperationalError:
        pass

    # Emotional patterns (last 30 days)
    try:
        emotions = conn.execute("""
            SELECT valence, COUNT(*) as count
            FROM emotions
            WHERE created_at >= ?
            GROUP BY valence
            ORDER BY count DESC
        """, (month_ago,)).fetchall()

        if emotions:
            parts.append("## Emotional Patterns (last 30 days)")
            for e in emotions:
                parts.append(f"  - {e['valence']}: {e['count']} occurrences")
            parts.append("")

        # Most common triggers
        triggers = conn.execute("""
            SELECT trigger, valence, COUNT(*) as count
            FROM emotions
            WHERE created_at >= ?
            GROUP BY trigger
            ORDER BY count DESC LIMIT 10
        """, (month_ago,)).fetchall()

        if triggers:
            parts.append("## Common Emotional Triggers")
            for t in triggers:
                parts.append(f"  - {t['trigger']} ({t['valence']}, {t['count']}x)")
            parts.append("")
    except sqlite3.OperationalError:
        pass

    # Session weather history (last 10)
    weathers = conn.execute("""
        SELECT content, created_at FROM memories
        WHERE category = 'session_weather' AND active = 1
        ORDER BY created_at DESC LIMIT 10
    """).fetchall()

    if weathers:
        parts.append("## Recent Session Moods")
        for w in weathers:
            day = w["created_at"][:10]
            parts.append(f"  - [{day}] {w['content'][:100]}")
        parts.append("")

    conn.close()

    if parts:
        print("# Data for Relationship Update\n")
        print("\n".join(parts))
    else:
        print("No data available for relationship analysis.")

def main():
    parser = argparse.ArgumentParser(description="Manage the relationship DNA file")
    parser.add_argument("--init", action="store_true", help="Initialize a blank relationship file")
    parser.add_argument("--read", action="store_true", help="Read current relationship file")
    parser.add_argument("--prepare", action="store_true", help="Output data for agent analysis")
    parser.add_argument("--output", default="relationship.md", help="Relationship file path")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()

    if args.init:
        init_relationship(args.output)
    elif args.read:
        read_relationship(args.output)
    elif args.prepare:
        prepare_context(args.db)
    else:
        read_relationship(args.output)

if __name__ == "__main__":
    main()
