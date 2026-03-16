#!/usr/bin/env python3
"""Inside Joke Emergence — detect recurring patterns and promote to inside jokes.

Tracks repeated phrases/situations and promotes them when they recur 3+ times
with positive reactions. Inside jokes are NEVER announced — they're used naturally.

Usage:
  # Log a potential joke pattern (agent calls this when a phrase/situation repeats)
  memory_joke_detect.py --log --text "File bosser !" --context "David traîne sur Telegram" --db memory.db

  # Check for promotable patterns (run periodically or by observer)
  memory_joke_detect.py --check --db memory.db

  # Promote a pattern to inside_joke
  memory_joke_detect.py --promote <pattern_id> --db memory.db

  # List tracked patterns
  memory_joke_detect.py --list --db memory.db
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

def ensure_table(conn):
    """Create joke patterns table if needed."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS joke_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            context TEXT,
            occurrences INTEGER NOT NULL DEFAULT 1,
            positive_reactions INTEGER NOT NULL DEFAULT 0,
            first_seen TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            last_seen TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            status TEXT NOT NULL DEFAULT 'tracking',
            promoted_memory_id INTEGER,
            FOREIGN KEY (promoted_memory_id) REFERENCES memories(id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_joke_status ON joke_patterns(status)")

def log_pattern(db_path, text, context=None, positive=False):
    """Log an occurrence of a potential joke pattern."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    ensure_table(conn)

    # Check if pattern already exists (fuzzy match)
    normalized = text.lower().strip()
    existing = conn.execute(
        "SELECT * FROM joke_patterns WHERE LOWER(text) = ? AND status != 'expired'",
        (normalized,)
    ).fetchone()

    if existing:
        new_occ = existing["occurrences"] + 1
        new_pos = existing["positive_reactions"] + (1 if positive else 0)
        conn.execute("""
            UPDATE joke_patterns
            SET occurrences = ?, positive_reactions = ?, last_seen = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'),
                context = COALESCE(?, context)
            WHERE id = ?
        """, (new_occ, new_pos, context, existing["id"]))
        conn.commit()
        conn.close()

        status = "🔥 READY TO PROMOTE" if new_occ >= 3 and new_pos >= 2 else f"tracking ({new_occ}x)"
        print(f"OK: Pattern updated — '{text}' ({status})")
        return existing["id"]
    else:
        cursor = conn.execute(
            "INSERT INTO joke_patterns (text, context, positive_reactions) VALUES (?, ?, ?)",
            (text, context, 1 if positive else 0)
        )
        conn.commit()
        pid = cursor.lastrowid
        conn.close()
        print(f"OK: New pattern tracked — '{text}' (#{pid}, 1st occurrence)")
        return pid

def check_promotable(db_path):
    """Check for patterns ready to promote."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    ensure_table(conn)

    candidates = conn.execute("""
        SELECT * FROM joke_patterns
        WHERE occurrences >= 3 AND positive_reactions >= 2 AND status = 'tracking'
        ORDER BY occurrences DESC
    """).fetchall()

    # Also expire old patterns (30 days without recurrence)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    expired = conn.execute("""
        UPDATE joke_patterns SET status = 'expired'
        WHERE status = 'tracking' AND occurrences < 3 AND last_seen < ?
    """, (cutoff,))
    expired_count = expired.rowcount

    conn.commit()
    conn.close()

    if expired_count:
        print(f"Expired {expired_count} stale pattern(s).\n")

    if not candidates:
        print("No patterns ready for promotion.")
        return

    print(f"🎯 {len(candidates)} pattern(s) ready for promotion:\n")
    for c in candidates:
        print(f"  #{c['id']} — \"{c['text']}\" ({c['occurrences']}x, {c['positive_reactions']} positive)")
        print(f"    Context: {c['context'] or 'N/A'}")
        print(f"    First: {c['first_seen'][:10]} | Last: {c['last_seen'][:10]}")
        print()

    print("Promote with: memory_joke_detect.py --promote <id>")
    print("Remember: inside jokes are NEVER announced. Use them naturally.")

def promote_pattern(db_path, pattern_id):
    """Promote a pattern to inside_joke memory."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    ensure_table(conn)

    pattern = conn.execute("SELECT * FROM joke_patterns WHERE id = ?", (pattern_id,)).fetchone()
    if not pattern:
        print(f"ERROR: Pattern #{pattern_id} not found", file=sys.stderr)
        conn.close()
        sys.exit(1)

    if pattern["status"] == "promoted":
        print(f"Pattern #{pattern_id} already promoted.")
        conn.close()
        return

    # Create inside_joke memory
    cursor = conn.execute(
        "INSERT INTO memories (content, category, importance, source) VALUES (?, 'inside_joke', 1.0, 'joke_detection')",
        (pattern["text"],)
    )
    memory_id = cursor.lastrowid

    conn.execute("INSERT OR IGNORE INTO memory_tags (memory_id, tag) VALUES (?, 'inside_joke')", (memory_id,))
    if pattern["context"]:
        conn.execute("INSERT OR IGNORE INTO memory_tags (memory_id, tag) VALUES (?, ?)", (memory_id, "context:" + pattern["context"][:50]))

    # Update pattern status
    conn.execute(
        "UPDATE joke_patterns SET status = 'promoted', promoted_memory_id = ? WHERE id = ?",
        (memory_id, pattern_id)
    )

    conn.commit()
    conn.close()
    print(f"OK: Pattern #{pattern_id} promoted to inside_joke memory #{memory_id}")
    print(f"    \"{pattern['text']}\"")
    print(f"    Rule: NEVER announce this as an inside joke. Use it naturally.")

def list_patterns(db_path, show_all=False):
    """List tracked patterns."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    ensure_table(conn)

    where = "" if show_all else "WHERE status IN ('tracking', 'promoted')"
    patterns = conn.execute(f"SELECT * FROM joke_patterns {where} ORDER BY occurrences DESC").fetchall()
    conn.close()

    if not patterns:
        print("No patterns tracked yet.")
        return

    status_emoji = {"tracking": "👀", "promoted": "🎯", "expired": "💤"}
    print(f"=== Joke Patterns ({len(patterns)}) ===\n")
    for p in patterns:
        emoji = status_emoji.get(p["status"], "?")
        print(f"  {emoji} #{p['id']} [{p['status']}] \"{p['text']}\" — {p['occurrences']}x ({p['positive_reactions']} positive)")

def main():
    parser = argparse.ArgumentParser(description="Inside Joke Emergence")
    parser.add_argument("--log", action="store_true", help="Log a pattern occurrence")
    parser.add_argument("--text", help="Pattern text")
    parser.add_argument("--context", help="Usage context")
    parser.add_argument("--positive", action="store_true", help="Mark as positive reaction")
    parser.add_argument("--check", action="store_true", help="Check for promotable patterns")
    parser.add_argument("--promote", type=int, help="Promote a pattern to inside_joke")
    parser.add_argument("--list", action="store_true", help="List tracked patterns")
    parser.add_argument("--all", action="store_true", help="Include expired (with --list)")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()

    if args.log:
        if not args.text:
            print("ERROR: --text required", file=sys.stderr)
            sys.exit(1)
        log_pattern(args.db, args.text, args.context, args.positive)
    elif args.check:
        check_promotable(args.db)
    elif args.promote is not None:
        promote_pattern(args.db, args.promote)
    elif args.list:
        list_patterns(args.db, args.all)
    else:
        list_patterns(args.db)

if __name__ == "__main__":
    main()
