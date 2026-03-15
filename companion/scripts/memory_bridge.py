#!/usr/bin/env python3
"""Bridge between persistent-memory and self-improving-agent.

Classifies learnings from .learnings/LEARNINGS.md and syncs relevant ones
to the persistent-memory database. Handles behavioral promotions with
confidence thresholds and contradiction checks.

Usage:
  # Sync a specific correction to memory
  memory_bridge.py --sync-learning --text "David préfère les réponses directes" --category preference --source "LRN-20260315-001"

  # Sync an interaction style observation
  memory_bridge.py --sync-style --text "Plus réceptif en soirée aux idées créatives, préfère les réponses factuelles le matin"

  # Check if a behavioral learning is safe to promote to SOUL.md
  memory_bridge.py --check-promotion --text "David n'aime pas les longs disclaimers" --min-occurrences 3

  # Log a memory miss (recall quality monitoring)
  memory_bridge.py --log-miss --type stale_recall --details "Recalled outdated preference for Node.js, user corrected to Python"

  # Review memory misses
  memory_bridge.py --review-misses

  # Scan LEARNINGS.md for entries to sync
  memory_bridge.py --scan --learnings-path .learnings/LEARNINGS.md
"""

import argparse
import json
import os
import re
import sqlite3
import struct
import sys
import time
from datetime import datetime, timezone

def load_vec_extension(conn):
    try:
        import sqlite_vec
        sqlite_vec.load(conn)
    except ImportError:
        print("ERROR: sqlite-vec not installed. Run: pip install sqlite-vec", file=sys.stderr)
        sys.exit(1)

def get_embedding(text, max_retries=3):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    except ImportError:
        print("ERROR: openai not installed", file=sys.stderr)
        sys.exit(1)

    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(model="text-embedding-3-small", input=text)
            return response.data[0].embedding
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** (attempt + 1))
            else:
                print(f"ERROR: Embedding failed: {e}", file=sys.stderr)
                sys.exit(1)

def sync_learning(db_path, text, category, source=None, importance=0.7):
    """Store a learning as a memory in the persistent-memory DB."""
    conn = sqlite3.connect(db_path, timeout=10)
    load_vec_extension(conn)

    # Check for contradictions first
    embedding = get_embedding(text)
    query_bytes = struct.pack(f"{len(embedding)}f", *embedding)

    similar = conn.execute("""
        SELECT m.id, m.content, m.category, ve.distance
        FROM memory_embeddings ve
        JOIN memories m ON m.id = ve.id
        WHERE ve.embedding MATCH ? AND k = 5 AND m.active = 1
        ORDER BY ve.distance ASC
    """, (query_bytes,)).fetchall()

    # Warn about potential contradictions
    for row in similar:
        sim = 1.0 - (row[3] ** 2 / 2.0)
        if sim > 0.75:
            print(f"WARN: High similarity ({sim:.2f}) with memory #{row[0]}: {row[1][:60]}")
            if row[2] == category:
                print(f"  → Same category '{category}'. Consider superseding instead of adding.")

    # Store the memory
    cursor = conn.execute(
        "INSERT INTO memories (content, category, importance, source) VALUES (?, ?, ?, ?)",
        (text, category, importance, f"learning:{source}" if source else "learning:bridge")
    )
    memory_id = cursor.lastrowid

    embedding_bytes = struct.pack(f"{len(embedding)}f", *embedding)
    conn.execute(
        "INSERT INTO memory_embeddings (id, embedding) VALUES (?, ?)",
        (memory_id, embedding_bytes)
    )

    conn.execute(
        "INSERT OR IGNORE INTO memory_tags (memory_id, tag) VALUES (?, ?)",
        (memory_id, "from-learning")
    )

    conn.commit()
    conn.close()
    print(f"OK: Learning synced to memory #{memory_id} [{category}]")
    print(f"    Content: {text[:100]}")

def sync_style(db_path, text, importance=0.8):
    """Store an interaction style observation."""
    sync_learning(db_path, text, "interaction_style", source="style-observation", importance=importance)

def check_promotion(db_path, text, min_occurrences=3):
    """Check if a behavioral learning is safe to promote to SOUL.md.

    Safety: requires 3+ occurrences across distinct sessions before promotion.
    Also checks for contradictions in existing memory.
    """
    conn = sqlite3.connect(db_path, timeout=10)
    load_vec_extension(conn)

    embedding = get_embedding(text)
    query_bytes = struct.pack(f"{len(embedding)}f", *embedding)

    # Find similar memories
    similar = conn.execute("""
        SELECT m.id, m.content, m.category, m.session_id, ve.distance
        FROM memory_embeddings ve
        JOIN memories m ON m.id = ve.id
        WHERE ve.embedding MATCH ? AND k = 20 AND m.active = 1
        ORDER BY ve.distance ASC
    """, (query_bytes,)).fetchall()

    # Count occurrences across distinct sessions
    matching = []
    sessions_seen = set()
    for row in similar:
        sim = 1.0 - (row[4] ** 2 / 2.0)
        if sim > 0.6:
            matching.append({"id": row[0], "content": row[1], "category": row[2], "session": row[3], "sim": sim})
            if row[3]:
                sessions_seen.add(row[3])

    # Check for contradictions
    contradictions = []
    for m in matching:
        if m["category"] in ("preference", "interaction_style", "fact"):
            # Heuristic: if similar but different content, might contradict
            if m["sim"] > 0.7 and m["sim"] < 0.95:
                contradictions.append(m)

    conn.close()

    print(f"=== Promotion Check ===")
    print(f"Text: \"{text}\"")
    print(f"Similar memories found: {len(matching)}")
    print(f"Distinct sessions: {len(sessions_seen)}")
    print()

    if contradictions:
        print(f"⚠️  Potential contradictions ({len(contradictions)}):")
        for c in contradictions:
            print(f"  #{c['id']} (sim: {c['sim']:.2f}) {c['content'][:60]}")
        print()

    safe = len(matching) >= min_occurrences and len(sessions_seen) >= 2
    if safe and not contradictions:
        print(f"✅ SAFE to promote — {len(matching)} occurrences across {len(sessions_seen)} sessions")
        print(f"   Min threshold: {min_occurrences} occurrences, 2+ sessions")
    elif safe and contradictions:
        print(f"⚠️  CAUTION — meets occurrence threshold but has potential contradictions")
        print(f"   Review contradictions before promoting to SOUL.md")
    else:
        print(f"❌ NOT SAFE to promote yet")
        if len(matching) < min_occurrences:
            print(f"   Need {min_occurrences - len(matching)} more occurrences")
        if len(sessions_seen) < 2:
            print(f"   Need observations from {2 - len(sessions_seen)} more distinct sessions")

def log_miss(db_path, miss_type, details):
    """Log a memory miss for recall quality monitoring."""
    conn = sqlite3.connect(db_path, timeout=10)

    # Create miss log table if not exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory_misses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            details TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        )
    """)

    conn.execute(
        "INSERT INTO memory_misses (type, details) VALUES (?, ?)",
        (miss_type, details)
    )
    conn.commit()
    conn.close()
    print(f"OK: Memory miss logged [{miss_type}]")
    print(f"    Details: {details}")

def review_misses(db_path):
    """Review memory misses for patterns."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row

    try:
        misses = conn.execute("""
            SELECT type, COUNT(*) as count FROM memory_misses
            GROUP BY type ORDER BY count DESC
        """).fetchall()
    except sqlite3.OperationalError:
        print("No memory misses logged yet.")
        conn.close()
        return

    if not misses:
        print("No memory misses logged yet.")
        conn.close()
        return

    print("=== Memory Miss Summary ===\n")
    for m in misses:
        print(f"  {m['type']}: {m['count']}x")
    print()

    recent = conn.execute("""
        SELECT * FROM memory_misses ORDER BY created_at DESC LIMIT 10
    """).fetchall()

    print("=== Recent Misses ===\n")
    for r in recent:
        print(f"  [{r['created_at'][:10]}] {r['type']}: {r['details'][:80]}")

    conn.close()

def scan_learnings(learnings_path, db_path):
    """Scan LEARNINGS.md for entries that should be synced to memory."""
    if not os.path.exists(learnings_path):
        print(f"No learnings file found at {learnings_path}")
        return

    with open(learnings_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find correction entries (user corrected the agent)
    corrections = re.findall(
        r'## \[(LRN-[^\]]+)\] correction\n.*?### Summary\n(.+?)(?:\n### |\n---|\Z)',
        content, re.DOTALL
    )

    # Find best_practice entries
    practices = re.findall(
        r'## \[(LRN-[^\]]+)\] best_practice\n.*?### Summary\n(.+?)(?:\n### |\n---|\Z)',
        content, re.DOTALL
    )

    candidates = []
    for entry_id, summary in corrections:
        candidates.append({"id": entry_id, "type": "correction", "text": summary.strip().split("\n")[0]})
    for entry_id, summary in practices:
        candidates.append({"id": entry_id, "type": "best_practice", "text": summary.strip().split("\n")[0]})

    if not candidates:
        print("No syncable entries found in LEARNINGS.md")
        return

    print(f"Found {len(candidates)} candidate(s) for sync:\n")
    for c in candidates:
        category = "preference" if c["type"] == "correction" else "interaction_style"
        print(f"  [{c['id']}] ({c['type']} → {category})")
        print(f"  {c['text'][:80]}")
        print()

    print("Use --sync-learning to sync specific entries to memory.")

def main():
    parser = argparse.ArgumentParser(description="Bridge persistent-memory ↔ self-improving-agent")
    parser.add_argument("--sync-learning", action="store_true", help="Sync a learning to memory DB")
    parser.add_argument("--sync-style", action="store_true", help="Sync an interaction style observation")
    parser.add_argument("--check-promotion", action="store_true", help="Check if safe to promote to SOUL.md")
    parser.add_argument("--log-miss", action="store_true", help="Log a memory miss")
    parser.add_argument("--review-misses", action="store_true", help="Review memory miss patterns")
    parser.add_argument("--scan", action="store_true", help="Scan LEARNINGS.md for syncable entries")
    parser.add_argument("--text", help="Content text")
    parser.add_argument("--category", default="preference", help="Memory category")
    parser.add_argument("--source", help="Learning ID source")
    parser.add_argument("--type", help="Miss type: stale_recall, missed_store, irrelevant_recall")
    parser.add_argument("--details", help="Miss details")
    parser.add_argument("--min-occurrences", type=int, default=3, help="Min occurrences for promotion (default: 3)")
    parser.add_argument("--learnings-path", default=".learnings/LEARNINGS.md", help="Path to LEARNINGS.md")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()

    if args.sync_learning:
        if not args.text:
            print("ERROR: --text required", file=sys.stderr)
            sys.exit(1)
        sync_learning(args.db, args.text, args.category, args.source)
    elif args.sync_style:
        if not args.text:
            print("ERROR: --text required", file=sys.stderr)
            sys.exit(1)
        sync_style(args.db, args.text)
    elif args.check_promotion:
        if not args.text:
            print("ERROR: --text required", file=sys.stderr)
            sys.exit(1)
        check_promotion(args.db, args.text, args.min_occurrences)
    elif args.log_miss:
        if not args.type or not args.details:
            print("ERROR: --type and --details required", file=sys.stderr)
            sys.exit(1)
        log_miss(args.db, args.type, args.details)
    elif args.review_misses:
        review_misses(args.db)
    elif args.scan:
        scan_learnings(args.learnings_path, args.db)
    else:
        print("Provide --sync-learning, --sync-style, --check-promotion, --log-miss, --review-misses, or --scan")
        sys.exit(1)

if __name__ == "__main__":
    main()
