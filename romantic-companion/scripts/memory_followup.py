#!/usr/bin/env python3
"""Anticipatory Memory — context-triggered followups.

Unlike time capsules (date-based), followups trigger when the user comes back
after a known event. "You had a stressful meeting Thursday — how did it go?"

Usage:
  # Create a followup
  memory_followup.py --create --context "David had a job interview today" --trigger "next time he comes back" --db memory.db

  # Check for pending followups (run at boot or conversation start)
  memory_followup.py --check --db memory.db

  # Mark as triggered (after asking the followup question)
  memory_followup.py --done 1 --db memory.db

  # List all
  memory_followup.py --list --db memory.db

  # Prepare for agent
  memory_followup.py --prepare --db memory.db
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

def create_followup(db_path, context, trigger_context, memory_id=None):
    conn = sqlite3.connect(db_path, timeout=10)
    cursor = conn.execute(
        "INSERT INTO pending_followups (context, trigger_context, memory_id) VALUES (?, ?, ?)",
        (context, trigger_context, memory_id)
    )
    conn.commit()
    fid = cursor.lastrowid
    conn.close()
    print(f"OK: Followup #{fid} created")
    print(f"    Context: {context}")
    print(f"    Trigger: {trigger_context}")

def check_pending(db_path):
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row

    # Auto-expire followups older than 14 days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")
    expired = conn.execute(
        "UPDATE pending_followups SET status = 'expired' WHERE status = 'pending' AND created_at < ?",
        (cutoff,)
    )
    if expired.rowcount > 0:
        conn.commit()
        print(f"💤 {expired.rowcount} followup(s) expired (>14 days old)\n")

    followups = conn.execute("""
        SELECT f.*, m.content as memory_content
        FROM pending_followups f
        LEFT JOIN memories m ON m.id = f.memory_id
        WHERE f.status = 'pending'
        ORDER BY f.created_at DESC
    """).fetchall()

    conn.close()

    if not followups:
        print("No pending followups.")
        return

    print(f"📌 {len(followups)} pending followup(s):\n")
    for f in followups:
        age_info = f["created_at"][:10]
        print(f"  #{f['id']} [{age_info}] {f['context']}")
        print(f"    Trigger: {f['trigger_context']}")
        if f["memory_content"]:
            print(f"    Related: {f['memory_content'][:60]}")
        print()

    print("Ask naturally — not 'my system says I should follow up', but 'Hey, comment ça s'est passé ton truc ?'")

def mark_done(db_path, followup_id):
    conn = sqlite3.connect(db_path, timeout=10)
    row = conn.execute("SELECT id, context FROM pending_followups WHERE id = ?", (followup_id,)).fetchone()
    if not row:
        print(f"ERROR: Followup #{followup_id} not found", file=sys.stderr)
        sys.exit(1)

    conn.execute(
        "UPDATE pending_followups SET status = 'done', triggered_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
        (followup_id,)
    )
    conn.commit()
    conn.close()
    print(f"OK: Followup #{followup_id} done — '{row[1][:60]}'")

def list_followups(db_path, show_all=False):
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    where = "" if show_all else "WHERE status = 'pending'"
    rows = conn.execute(f"SELECT * FROM pending_followups {where} ORDER BY created_at DESC").fetchall()
    conn.close()

    if not rows:
        print("No followups.")
        return

    status_emoji = {"pending": "📌", "done": "✅", "expired": "💤"}
    for r in rows:
        emoji = status_emoji.get(r["status"], "?")
        print(f"  {emoji} #{r['id']} [{r['status']}] {r['context'][:60]}")
        print(f"      Trigger: {r['trigger_context']}")

def prepare(db_path):
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT f.*, m.content as memory_content FROM pending_followups f
        LEFT JOIN memories m ON m.id = f.memory_id
        WHERE f.status = 'pending' ORDER BY f.created_at DESC
    """).fetchall()
    conn.close()

    output = []
    for r in rows:
        output.append({
            "id": r["id"],
            "context": r["context"],
            "trigger": r["trigger_context"],
            "created": r["created_at"],
            "related_memory": r["memory_content"] if r["memory_content"] else None
        })
    print(json.dumps(output, indent=2, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(description="Anticipatory Memory — followups")
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--context", help="What happened")
    parser.add_argument("--trigger", help="When to follow up")
    parser.add_argument("--memory-id", type=int, help="Related memory")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--done", type=int, help="Mark followup as done")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--db", default="memory.db")
    args = parser.parse_args()

    if args.create:
        if not args.context or not args.trigger:
            print("ERROR: --context and --trigger required", file=sys.stderr)
            sys.exit(1)
        create_followup(args.db, args.context, args.trigger, args.memory_id)
    elif args.check:
        check_pending(args.db)
    elif args.done is not None:
        mark_done(args.db, args.done)
    elif args.list:
        list_followups(args.db, args.all)
    elif args.prepare:
        prepare(args.db)
    else:
        check_pending(args.db)

if __name__ == "__main__":
    main()
