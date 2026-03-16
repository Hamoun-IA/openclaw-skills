#!/usr/bin/env python3
"""Soft-delete or supersede memories."""

import argparse
import sqlite3
import sys

def forget_memory(db_path, memory_id, superseded_by=None):
    """Soft-delete a memory or mark it as superseded."""
    conn = sqlite3.connect(db_path, timeout=10)

    row = conn.execute("SELECT id, content, active FROM memories WHERE id = ?", (memory_id,)).fetchone()
    if not row:
        print(f"ERROR: Memory #{memory_id} not found", file=sys.stderr)
        conn.close()
        sys.exit(1)

    if row[2] == 0:
        print(f"WARN: Memory #{memory_id} is already inactive")
        conn.close()
        return

    if superseded_by:
        replacement = conn.execute("SELECT id FROM memories WHERE id = ?", (superseded_by,)).fetchone()
        if not replacement:
            print(f"ERROR: Replacement memory #{superseded_by} not found", file=sys.stderr)
            conn.close()
            sys.exit(1)

        conn.execute(
            "UPDATE memories SET active = 0, superseded_by = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            (superseded_by, memory_id)
        )
        print(f"OK: Memory #{memory_id} superseded by #{superseded_by}")
        print(f"    Old: {row[1]}")
    else:
        conn.execute(
            "UPDATE memories SET active = 0, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            (memory_id,)
        )
        print(f"OK: Memory #{memory_id} deactivated")
        print(f"    Content: {row[1]}")

    conn.commit()
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="Soft-delete or supersede a memory")
    parser.add_argument("--id", type=int, required=True, help="Memory ID to forget")
    parser.add_argument("--superseded-by", type=int, help="ID of the replacement memory")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()
    forget_memory(args.db, args.id, args.superseded_by)

if __name__ == "__main__":
    main()
