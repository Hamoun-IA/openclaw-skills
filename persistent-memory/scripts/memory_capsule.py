#!/usr/bin/env python3
"""Manage time capsules — memories that deliver at a specific date.

Usage:
  # Create a time capsule
  memory_capsule.py --create --memory-id 42 --date 2026-04-15

  # Check for capsules due today (used in morning briefing)
  memory_capsule.py --due

  # Mark a capsule as delivered
  memory_capsule.py --deliver 1

  # List all capsules
  memory_capsule.py --list
"""

import argparse
import sqlite3
import sys
from datetime import datetime, timezone

def create_capsule(conn, memory_id, deliver_date):
    """Create a time capsule for a memory."""
    # Verify memory exists
    mem = conn.execute("SELECT id, content FROM memories WHERE id = ?", (memory_id,)).fetchone()
    if not mem:
        print(f"ERROR: Memory #{memory_id} not found", file=sys.stderr)
        sys.exit(1)

    # Validate date
    try:
        datetime.strptime(deliver_date, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Invalid date format. Use YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    cursor = conn.execute(
        "INSERT INTO time_capsules (memory_id, deliver_date) VALUES (?, ?)",
        (memory_id, deliver_date)
    )
    conn.commit()
    print(f"OK: Time capsule #{cursor.lastrowid} created")
    print(f"    Memory: #{memory_id} — {mem['content'][:80]}")
    print(f"    Delivers: {deliver_date}")

def check_due(conn):
    """Check for capsules due today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    capsules = conn.execute("""
        SELECT tc.id, tc.deliver_date, tc.memory_id, m.content, m.category
        FROM time_capsules tc
        JOIN memories m ON m.id = tc.memory_id
        WHERE tc.delivered = 0 AND tc.deliver_date <= ?
        ORDER BY tc.deliver_date ASC
    """, (today,)).fetchall()

    if not capsules:
        print("No time capsules due today.")
        return

    print(f"📬 {len(capsules)} time capsule(s) due:\n")
    for c in capsules:
        overdue = " (OVERDUE)" if c["deliver_date"] < today else ""
        print(f"  Capsule #{c['id']} — deliver date: {c['deliver_date']}{overdue}")
        print(f"  Memory #{c['memory_id']} [{c['category']}]: {c['content']}")
        print()

    print("Mark as delivered after presenting to user: memory_capsule.py --deliver <id>")

def deliver_capsule(conn, capsule_id):
    """Mark a capsule as delivered."""
    row = conn.execute("SELECT id, memory_id FROM time_capsules WHERE id = ?", (capsule_id,)).fetchone()
    if not row:
        print(f"ERROR: Capsule #{capsule_id} not found", file=sys.stderr)
        sys.exit(1)

    if conn.execute("SELECT delivered FROM time_capsules WHERE id = ?", (capsule_id,)).fetchone()["delivered"]:
        print(f"WARN: Capsule #{capsule_id} already delivered")
        return

    conn.execute("UPDATE time_capsules SET delivered = 1 WHERE id = ?", (capsule_id,))
    conn.commit()
    print(f"OK: Capsule #{capsule_id} marked as delivered")

def list_capsules(conn, show_all=False):
    """List capsules."""
    where = "" if show_all else "WHERE tc.delivered = 0"
    capsules = conn.execute(f"""
        SELECT tc.*, m.content, m.category
        FROM time_capsules tc
        JOIN memories m ON m.id = tc.memory_id
        {where}
        ORDER BY tc.deliver_date ASC
    """).fetchall()

    if not capsules:
        print("No pending time capsules.")
        return

    print(f"=== Time Capsules ({len(capsules)}) ===\n")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for c in capsules:
        status = "📬 DUE" if c["deliver_date"] <= today and not c["delivered"] else ("✅ delivered" if c["delivered"] else "⏳ pending")
        print(f"  #{c['id']} [{status}] Deliver: {c['deliver_date']}")
        print(f"  Memory #{c['memory_id']} [{c['category']}]: {c['content'][:80]}")
        print()

def main():
    parser = argparse.ArgumentParser(description="Manage time capsules")
    parser.add_argument("--create", action="store_true", help="Create a time capsule")
    parser.add_argument("--memory-id", type=int, help="Memory ID (with --create)")
    parser.add_argument("--date", help="Delivery date YYYY-MM-DD (with --create)")
    parser.add_argument("--due", action="store_true", help="Check for capsules due today")
    parser.add_argument("--deliver", type=int, help="Mark capsule as delivered")
    parser.add_argument("--list", action="store_true", help="List pending capsules")
    parser.add_argument("--all", action="store_true", help="Include delivered (with --list)")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    if args.create:
        if not args.memory_id or not args.date:
            print("ERROR: --create requires --memory-id and --date", file=sys.stderr)
            sys.exit(1)
        create_capsule(conn, args.memory_id, args.date)
    elif args.due:
        check_due(conn)
    elif args.deliver is not None:
        deliver_capsule(conn, args.deliver)
    elif args.list:
        list_capsules(conn, args.all)
    else:
        print("ERROR: Provide --create, --due, --deliver, or --list", file=sys.stderr)
        sys.exit(1)

    conn.close()

if __name__ == "__main__":
    main()
