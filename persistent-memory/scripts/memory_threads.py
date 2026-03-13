#!/usr/bin/env python3
"""Manage open threads — unresolved topics the agent should follow up on.

Usage:
  # Open a new thread
  memory_threads.py --open "David cherche un nouveau job" --memory-id 42

  # List open threads
  memory_threads.py --list

  # List all (including resolved)
  memory_threads.py --list --all

  # Resolve a thread
  memory_threads.py --resolve 1

  # Mark as stale (no update in a while)
  memory_threads.py --stale 1

  # Touch a thread (update last_mentioned)
  memory_threads.py --touch 1
"""

import argparse
import sqlite3
import sys

def open_thread(conn, topic, memory_id=None):
    """Create a new open thread."""
    # Check for duplicate
    existing = conn.execute(
        "SELECT id FROM open_threads WHERE topic = ? AND status = 'open'",
        (topic,)
    ).fetchone()

    if existing:
        print(f"WARN: Similar open thread already exists (#{existing[0]})")
        return existing[0]

    cursor = conn.execute(
        "INSERT INTO open_threads (topic, memory_id, last_mentioned) VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))",
        (topic, memory_id)
    )
    conn.commit()
    tid = cursor.lastrowid
    print(f"OK: Opened thread #{tid}: \"{topic}\"")
    return tid

def list_threads(conn, show_all=False):
    """List threads."""
    where = "" if show_all else "WHERE status = 'open'"
    threads = conn.execute(f"""
        SELECT t.*, m.content as memory_content
        FROM open_threads t
        LEFT JOIN memories m ON m.id = t.memory_id
        {where}
        ORDER BY
            CASE t.status WHEN 'open' THEN 0 WHEN 'stale' THEN 1 ELSE 2 END,
            t.opened_at DESC
    """).fetchall()

    if not threads:
        print("No open threads.")
        return

    status_emoji = {"open": "🔵", "stale": "🟡", "resolved": "✅"}

    print(f"=== Threads ({len(threads)}) ===\n")
    for t in threads:
        emoji = status_emoji.get(t["status"], "⚪")
        mem_ref = f" (memory #{t['memory_id']})" if t["memory_id"] else ""
        print(f"{emoji} #{t['id']} [{t['status']}] {t['topic']}{mem_ref}")
        print(f"   Opened: {t['opened_at']} | Last mentioned: {t['last_mentioned']}")
        if t["resolved_at"]:
            print(f"   Resolved: {t['resolved_at']}")
        print()

def resolve_thread(conn, thread_id):
    """Mark a thread as resolved."""
    row = conn.execute("SELECT id, topic, status FROM open_threads WHERE id = ?", (thread_id,)).fetchone()
    if not row:
        print(f"ERROR: Thread #{thread_id} not found", file=sys.stderr)
        sys.exit(1)

    if row["status"] == "resolved":
        print(f"WARN: Thread #{thread_id} already resolved")
        return

    conn.execute(
        "UPDATE open_threads SET status = 'resolved', resolved_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
        (thread_id,)
    )
    conn.commit()
    print(f"OK: Thread #{thread_id} resolved: \"{row['topic']}\"")

def stale_thread(conn, thread_id):
    """Mark a thread as stale."""
    row = conn.execute("SELECT id, topic FROM open_threads WHERE id = ?", (thread_id,)).fetchone()
    if not row:
        print(f"ERROR: Thread #{thread_id} not found", file=sys.stderr)
        sys.exit(1)

    conn.execute("UPDATE open_threads SET status = 'stale' WHERE id = ?", (thread_id,))
    conn.commit()
    print(f"OK: Thread #{thread_id} marked stale: \"{row['topic']}\"")

def touch_thread(conn, thread_id):
    """Update last_mentioned timestamp."""
    row = conn.execute("SELECT id, topic FROM open_threads WHERE id = ?", (thread_id,)).fetchone()
    if not row:
        print(f"ERROR: Thread #{thread_id} not found", file=sys.stderr)
        sys.exit(1)

    conn.execute(
        "UPDATE open_threads SET last_mentioned = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), status = 'open' WHERE id = ?",
        (thread_id,)
    )
    conn.commit()
    print(f"OK: Thread #{thread_id} touched: \"{row['topic']}\"")

def main():
    parser = argparse.ArgumentParser(description="Manage open threads")
    parser.add_argument("--open", help="Open a new thread with this topic")
    parser.add_argument("--memory-id", type=int, help="Associated memory ID (with --open)")
    parser.add_argument("--list", action="store_true", help="List threads")
    parser.add_argument("--all", action="store_true", help="Include resolved threads (with --list)")
    parser.add_argument("--resolve", type=int, help="Resolve a thread by ID")
    parser.add_argument("--stale", type=int, help="Mark a thread as stale")
    parser.add_argument("--touch", type=int, help="Update last_mentioned for a thread")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    if args.open:
        open_thread(conn, args.open, args.memory_id)
    elif args.list:
        list_threads(conn, args.all)
    elif args.resolve is not None:
        resolve_thread(conn, args.resolve)
    elif args.stale is not None:
        stale_thread(conn, args.stale)
    elif args.touch is not None:
        touch_thread(conn, args.touch)
    else:
        print("ERROR: Provide --open, --list, --resolve, --stale, or --touch", file=sys.stderr)
        sys.exit(1)

    conn.close()

if __name__ == "__main__":
    main()
