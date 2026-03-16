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

    # 0. Rip Van Winkle detection — silence > 7 days
    latest_interaction = conn.execute("""
        SELECT MAX(created_at) as last FROM memories WHERE active = 1
    """).fetchone()

    if latest_interaction and latest_interaction["last"]:
        try:
            last_dt = datetime.fromisoformat(latest_interaction["last"].replace("Z", "+00:00"))
            silence_days = (datetime.now(timezone.utc) - last_dt).days

            if silence_days >= 30:
                sections.append(f"## 🔄 New Chapter ({silence_days} days absence)")
                sections.append("Treat as a new chapter. Full boot context. Warm reunion message.")
                sections.append("Reference the last conversation briefly but don't dwell. *'Ça fait un moment ! Content de te revoir.'*")
                sections.append("Enter `listen` mode regardless of reliability ratio.")
                sections.append("")
            elif silence_days >= 7:
                sections.append(f"## ⚠️ Long Silence ({silence_days} days)")
                sections.append("Acknowledge once, naturally, no guilt-trip. *'Ça fait un moment !'*")
                sections.append("Enter `listen` mode. Do not bombard with old context.")
                sections.append("")
            elif silence_days >= 3:
                sections.append(f"## 💬 Absence Noted ({silence_days} days)")
                sections.append("Warmer than usual, but don't reference the absence explicitly.")
                sections.append("Just be present and attentive.")
                sections.append("")
        except (ValueError, TypeError):
            pass

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

    # 6. Recent learnings (from bridge)
    bridge_memories = conn.execute("""
        SELECT id, content, category FROM memories
        WHERE active = 1 AND source LIKE 'learning:%'
        ORDER BY created_at DESC LIMIT 5
    """).fetchall()

    if bridge_memories:
        sections.append("## 📚 Recent Learnings")
        for m in bridge_memories:
            sections.append(f"- #{m['id']} [{m['category']}] {m['content'][:80]}")
        sections.append("")

    # 7. Memory miss summary
    try:
        misses = conn.execute("""
            SELECT type, COUNT(*) as count FROM memory_misses
            WHERE created_at >= date('now', '-7 days')
            GROUP BY type ORDER BY count DESC
        """).fetchall()

        if misses:
            sections.append("## ⚠️ Memory Misses (7 days)")
            for m in misses:
                sections.append(f"- {m['type']}: {m['count']}x")
            sections.append("")
    except sqlite3.OperationalError:
        pass

    # 8. Observer minimum threshold check
    try:
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        session_count = conn.execute("""
            SELECT COUNT(DISTINCT date(created_at)) as days FROM memories
            WHERE category = 'session_weather' AND active = 1 AND created_at >= ?
        """, (week_ago,)).fetchone()

        if session_count and session_count["days"] < 3:
            sections.append(f"## 📊 Observer Note")
            sections.append(f"Only {session_count['days']} active sessions this week (minimum 3 for weekly report).")
            sections.append("")
    except Exception:
        pass

    # 9. Pending followups
    try:
        followups = conn.execute("""
            SELECT id, context, trigger_context FROM pending_followups
            WHERE status = 'pending' ORDER BY created_at DESC LIMIT 5
        """).fetchall()
        if followups:
            sections.append("## 📌 Pending Followups")
            for f in followups:
                sections.append(f"- #{f['id']}: {f['context']} (trigger: {f['trigger_context']})")
            sections.append("")
    except sqlite3.OperationalError:
        pass

    # 10. Active aspirations
    try:
        aspirations = conn.execute("""
            SELECT id, content FROM aspirations WHERE status = 'active'
            ORDER BY last_mentioned DESC LIMIT 5
        """).fetchall()
        if aspirations:
            sections.append("## ✨ Active Aspirations")
            for a in aspirations:
                sections.append(f"- #{a['id']}: {a['content']}")
            sections.append("")
    except sqlite3.OperationalError:
        pass

    # 11. Reliability indicator
    try:
        verbatim = conn.execute("""
            SELECT COUNT(DISTINCT m.id) FROM memories m
            JOIN memory_tags t ON t.memory_id = m.id
            WHERE m.active = 1 AND (t.tag = 'founding' OR t.tag = 'user_corrected'
                  OR m.category IN ('verbatim', 'milestone'))
        """).fetchone()[0]

        inferred = conn.execute("""
            SELECT COUNT(DISTINCT m.id) FROM memories m
            JOIN memory_tags t ON t.memory_id = m.id
            WHERE m.active = 1 AND t.tag = 'inferred'
        """).fetchone()[0]

        if verbatim + inferred > 0:
            ratio = verbatim / (verbatim + inferred)
            if ratio < 0.4:
                sections.append("## 🔴 Reliability: LOW")
                sections.append(f"Only {verbatim} verbatim vs {inferred} inferred memories. LISTEN MODE: ask questions, don't assume.")
                sections.append("")
            elif ratio < 0.7:
                sections.append("## 🟡 Reliability: MEDIUM")
                sections.append(f"{verbatim} verbatim vs {inferred} inferred. Verify assumptions with open questions.")
                sections.append("")
    except Exception:
        pass

    # 10. Stats
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
