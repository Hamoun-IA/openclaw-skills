#!/usr/bin/env python3
"""Export all active memories as readable markdown."""

import argparse
import sqlite3
import sys

def dump_memories(db_path, include_inactive=False, output=None):
    """Export memories as markdown."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row

    where = "" if include_inactive else "WHERE m.active = 1"
    memories = conn.execute(f"""
        SELECT m.*, GROUP_CONCAT(t.tag, ', ') as tags
        FROM memories m
        LEFT JOIN memory_tags t ON t.memory_id = m.id
        {where}
        GROUP BY m.id
        ORDER BY m.category, m.importance DESC
    """).fetchall()

    if not memories:
        print("No memories found.")
        conn.close()
        return

    categories = {}
    for mem in memories:
        cat = mem["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(mem)

    stats = conn.execute(
        "SELECT COUNT(*) as total, SUM(CASE WHEN active = 1 THEN 1 ELSE 0 END) as active FROM memories"
    ).fetchone()

    lines = ["# Memory Dump", ""]
    lines.append(f"**Total:** {stats['total']} memories ({stats['active']} active)")
    lines.append("")

    for cat, mems in sorted(categories.items()):
        lines.append(f"## {cat.replace('_', ' ').title()} ({len(mems)})")
        lines.append("")
        for mem in mems:
            status = "" if mem["active"] else " ⛔"
            tags = f" `{mem['tags']}`" if mem["tags"] else ""
            session = f" 📍{mem['session_id'][:8]}" if mem["session_id"] else ""
            lines.append(f"- **#{mem['id']}** (importance: {mem['importance']}){status}{tags}{session}")
            lines.append(f"  {mem['content']}")
            lines.append(f"  _Created: {mem['created_at']} | Accessed: {mem['access_count']}x_")
            lines.append("")

    conn.close()

    result = "\n".join(lines)
    if output:
        with open(output, "w") as f:
            f.write(result)
        print(f"OK: Dumped {len(memories)} memories to {output}")
    else:
        print(result)

def main():
    parser = argparse.ArgumentParser(description="Export memories as markdown")
    parser.add_argument("--include-inactive", action="store_true", help="Include inactive memories")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()
    dump_memories(args.db, args.include_inactive, args.output)

if __name__ == "__main__":
    main()
