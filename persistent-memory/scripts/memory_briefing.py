#!/usr/bin/env python3
"""Generate a morning briefing — consolidated boot context for the agent.

Combines: session weather + due time capsules + open threads + future events + core memories.
One call replaces multiple recall passes at session start.

Usage:
  memory_briefing.py --db memory.db
"""

import argparse
import sqlite3
import sys
from datetime import datetime, timezone

def load_vec_extension(conn):
    try:
        import sqlite_vec
        sqlite_vec.load(conn)
    except ImportError:
        pass  # Vec not needed for briefing, just structured queries

def generate_briefing(db_path):
    """Generate a comprehensive morning briefing."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sections = []

    # 1. Session Weather (last emotional state)
    weather = conn.execute("""
        SELECT content, created_at FROM memories
        WHERE category = 'session_weather' AND active = 1
        ORDER BY created_at DESC LIMIT 1
    """).fetchone()

    if weather:
        sections.append("## Last Session Weather")
        sections.append(f"{weather['content']}")
        sections.append(f"_(from {weather['created_at']})_")
        sections.append("")

    # 2. Time Capsules due
    try:
        capsules = conn.execute("""
            SELECT tc.id, tc.deliver_date, m.content, m.category
            FROM time_capsules tc
            JOIN memories m ON m.id = tc.memory_id
            WHERE tc.delivered = 0 AND tc.deliver_date <= ?
            ORDER BY tc.deliver_date ASC
        """, (today,)).fetchall()

        if capsules:
            sections.append("## 📬 Time Capsules Due")
            for c in capsules:
                sections.append(f"- Capsule #{c['id']}: {c['content']}")
            sections.append("")
    except sqlite3.OperationalError:
        pass  # Table doesn't exist yet

    # 3. Open Threads
    try:
        threads = conn.execute("""
            SELECT id, topic, status, last_mentioned FROM open_threads
            WHERE status IN ('open', 'stale')
            ORDER BY CASE status WHEN 'open' THEN 0 ELSE 1 END, last_mentioned DESC
            LIMIT 10
        """).fetchall()

        if threads:
            sections.append("## 🔵 Open Threads")
            for t in threads:
                emoji = "🔵" if t["status"] == "open" else "🟡"
                sections.append(f"- {emoji} #{t['id']}: {t['topic']} (last: {t['last_mentioned']})")
            sections.append("")
    except sqlite3.OperationalError:
        pass  # Table doesn't exist yet

    # 4. Future Events
    events = conn.execute("""
        SELECT id, content, created_at FROM memories
        WHERE category = 'future_event' AND active = 1
        ORDER BY created_at DESC LIMIT 5
    """).fetchall()

    if events:
        sections.append("## 📅 Upcoming Events")
        for e in events:
            sections.append(f"- #{e['id']}: {e['content']}")
        sections.append("")

    # 5. Core Memories (most important + most accessed)
    core = conn.execute("""
        SELECT id, content, category, importance FROM memories
        WHERE importance >= 0.8 AND active = 1
        AND category NOT IN ('session_weather', 'future_event')
        ORDER BY access_count DESC, importance DESC LIMIT 10
    """).fetchall()

    if core:
        sections.append("## 🧠 Core Memories")
        for c in core:
            sections.append(f"- #{c['id']} [{c['category']}] {c['content']}")
        sections.append("")

    # 6. Stats
    stats = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END) as active_count
        FROM memories
    """).fetchone()

    conn.close()

    if not sections:
        print("No memories found. Database is empty.")
        return

    print(f"# Morning Briefing — {today}")
    print(f"_{stats['active_count']} active memories ({stats['total']} total)_\n")
    print("\n".join(sections))

def main():
    parser = argparse.ArgumentParser(description="Generate morning briefing")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()
    generate_briefing(args.db)

if __name__ == "__main__":
    main()
