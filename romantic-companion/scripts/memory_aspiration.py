#!/usr/bin/env python3
"""Aspirations Tracking — undated dreams and goals.

Not events (dated) or facts (current). Aspirations are what the user
WANTS but doesn't have yet. They form identity more deeply than preferences.

Usage:
  # Store an aspiration
  memory_aspiration.py --add "Veut vivre au Portugal un jour" --db memory.db

  # List active aspirations
  memory_aspiration.py --list --db memory.db

  # Mark as dormant (not mentioned in 60+ days)
  memory_aspiration.py --dormant 1 --db memory.db

  # Mark as achieved
  memory_aspiration.py --achieved 1 --db memory.db

  # Touch (mentioned again)
  memory_aspiration.py --touch 1 --db memory.db

  # Prepare for agent
  memory_aspiration.py --prepare --db memory.db
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

def add_aspiration(db_path, content):
    conn = sqlite3.connect(db_path, timeout=10)

    # Check duplicate
    existing = conn.execute(
        "SELECT id FROM aspirations WHERE content = ? COLLATE NOCASE AND status = 'active'",
        (content,)
    ).fetchone()
    if existing:
        print(f"WARN: Similar aspiration already exists (#{existing[0]})")
        conn.close()
        return

    cursor = conn.execute("INSERT INTO aspirations (content) VALUES (?)", (content,))
    conn.commit()
    aid = cursor.lastrowid
    conn.close()
    print(f"OK: Aspiration #{aid} — \"{content}\"")

def list_aspirations(db_path, show_all=False):
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    where = "" if show_all else "WHERE status IN ('active', 'dormant')"
    rows = conn.execute(f"SELECT * FROM aspirations {where} ORDER BY status, last_mentioned DESC").fetchall()
    conn.close()

    if not rows:
        print("No aspirations tracked.")
        return

    emoji = {"active": "✨", "in_progress": "🚀", "dormant": "💤", "achieved": "🎉"}
    print(f"=== Aspirations ({len(rows)}) ===\n")
    for r in rows:
        e = emoji.get(r["status"], "?")
        print(f"  {e} #{r['id']} [{r['status']}] {r['content']}")
        print(f"     Last mentioned: {r['last_mentioned'][:10]} | Created: {r['created_at'][:10]}")

def update_status(db_path, asp_id, status):
    conn = sqlite3.connect(db_path, timeout=10)
    row = conn.execute("SELECT id, content FROM aspirations WHERE id = ?", (asp_id,)).fetchone()
    if not row:
        print(f"ERROR: Aspiration #{asp_id} not found", file=sys.stderr)
        sys.exit(1)

    conn.execute("UPDATE aspirations SET status = ? WHERE id = ?", (status, asp_id))
    conn.commit()
    conn.close()
    print(f"OK: Aspiration #{asp_id} → {status}")

def touch(db_path, asp_id):
    conn = sqlite3.connect(db_path, timeout=10)
    row = conn.execute("SELECT id, content FROM aspirations WHERE id = ?", (asp_id,)).fetchone()
    if not row:
        print(f"ERROR: Aspiration #{asp_id} not found", file=sys.stderr)
        sys.exit(1)

    conn.execute(
        "UPDATE aspirations SET last_mentioned = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), status = 'active' WHERE id = ?",
        (asp_id,)
    )
    conn.commit()
    conn.close()
    print(f"OK: Aspiration #{asp_id} touched (reactivated if dormant)")

def prepare(db_path):
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row

    active = conn.execute("SELECT * FROM aspirations WHERE status = 'active' ORDER BY last_mentioned DESC").fetchall()
    dormant = conn.execute("SELECT * FROM aspirations WHERE status = 'dormant'").fetchall()

    # Auto-dormant: active but not mentioned in 60+ days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    stale = conn.execute(
        "SELECT id, content FROM aspirations WHERE status = 'active' AND last_mentioned < ?", (cutoff,)
    ).fetchall()

    for s in stale:
        conn.execute("UPDATE aspirations SET status = 'dormant' WHERE id = ?", (s["id"],))
    if stale:
        conn.commit()

    conn.close()

    output = {
        "active": [{"id": a["id"], "content": a["content"], "last_mentioned": a["last_mentioned"]} for a in active],
        "dormant": [{"id": d["id"], "content": d["content"]} for d in dormant],
        "auto_dormant": len(stale)
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(description="Aspirations Tracking")
    parser.add_argument("--add", help="Add an aspiration")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dormant", type=int, help="Mark as dormant")
    parser.add_argument("--in-progress", type=int, help="Mark as in progress (actively pursuing)")
    parser.add_argument("--achieved", type=int, help="Mark as achieved (requires user confirmation)")
    parser.add_argument("--touch", type=int, help="Touch (mentioned again)")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--db", default="memory.db")
    args = parser.parse_args()

    if args.add:
        add_aspiration(args.db, args.add)
    elif args.list:
        list_aspirations(args.db, args.all)
    elif args.dormant is not None:
        update_status(args.db, args.dormant, "dormant")
    elif args.in_progress is not None:
        update_status(args.db, args.in_progress, "in_progress")
    elif args.achieved is not None:
        print("⚠️  IMPORTANT: Only mark as achieved after USER CONFIRMS the dream is realized.")
        print("   The agent proposes, the user confirms. Never auto-achieve.")
        update_status(args.db, args.achieved, "achieved")
    elif args.touch is not None:
        touch(args.db, args.touch)
    elif args.prepare:
        prepare(args.db)
    else:
        list_aspirations(args.db)

if __name__ == "__main__":
    main()
