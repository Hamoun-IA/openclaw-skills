#!/usr/bin/env python3
"""Recall memories using semantic search with decay weighting."""

import argparse
import math
import os
import sqlite3
import struct
import sys
import time
from datetime import datetime, timezone

# Decay TTL in days per category (None = no decay)
DECAY_TTL = {
    "minor_detail": 7,
    "verbatim": 14,
    "shared_moment": 90,
}

def load_vec_extension(conn):
    try:
        import sqlite_vec
        sqlite_vec.load(conn)
    except ImportError:
        print("ERROR: sqlite-vec not installed. Run: pip install sqlite-vec", file=sys.stderr)
        sys.exit(1)

def get_embedding(text, max_retries=3):
    """Generate embedding via OpenAI API."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    except ImportError:
        print("ERROR: openai package not installed. Run: pip install openai", file=sys.stderr)
        sys.exit(1)

    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"WARN: Embedding attempt {attempt + 1} failed: {e}. Retrying in {wait}s...", file=sys.stderr)
                time.sleep(wait)
            else:
                print(f"ERROR: Embedding failed after {max_retries} attempts: {e}", file=sys.stderr)
                sys.exit(1)

def compute_decay(category, created_at, last_accessed):
    """Compute decay factor for a memory based on its category and age."""
    ttl = DECAY_TTL.get(category)
    if ttl is None:
        return 1.0

    # Use last_accessed if available, otherwise created_at
    ref_date = last_accessed or created_at
    try:
        ref = datetime.fromisoformat(ref_date.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return 1.0

    age_days = (datetime.now(timezone.utc) - ref).total_seconds() / 86400
    decay = max(0.1, 1.0 - (age_days / ttl))
    return round(decay, 3)

def recall_memories(db_path, query, limit=5, threshold=0.3, category=None,
                    session_id=None, boot=False, include_inactive=False):
    """Search memories by semantic similarity with decay weighting."""
    conn = sqlite3.connect(db_path, timeout=10)
    load_vec_extension(conn)
    conn.row_factory = sqlite3.Row

    results = []

    # --- Boot mode: chronological queries (no embedding needed) ---
    if boot:
        # 1. Latest session weather
        weather = conn.execute("""
            SELECT id, content, category, importance, created_at, access_count
            FROM memories WHERE category = 'session_weather' AND active = 1
            ORDER BY created_at DESC LIMIT 1
        """).fetchone()
        if weather:
            results.append(dict(weather) | {"similarity": 1.0, "tags": [], "decay": 1.0, "section": "Session Weather"})

        # 2. Upcoming future events
        events = conn.execute("""
            SELECT id, content, category, importance, created_at, access_count
            FROM memories WHERE category = 'future_event' AND active = 1
            ORDER BY created_at DESC LIMIT 5
        """).fetchall()
        for e in events:
            results.append(dict(e) | {"similarity": 1.0, "tags": [], "decay": 1.0, "section": "Upcoming Events"})

        # 3. Founding memories (hard cap 20 at boot)
        founding = conn.execute("""
            SELECT DISTINCT m.id, m.content, m.category, m.importance, m.created_at, m.access_count
            FROM memories m
            JOIN memory_tags t ON t.memory_id = m.id
            WHERE t.tag = 'founding' AND m.active = 1
            ORDER BY m.importance DESC, m.created_at ASC LIMIT 20
        """).fetchall()
        for f in founding:
            results.append(dict(f) | {"similarity": 1.0, "tags": ["founding"], "decay": 1.0, "section": "Founding Memories"})

        # 4. High-importance core memories (non-founding)
        founding_ids = {f["id"] for f in founding}
        core = conn.execute("""
            SELECT id, content, category, importance, created_at, access_count
            FROM memories WHERE importance >= 0.8 AND active = 1
            AND category NOT IN ('session_weather', 'future_event')
            ORDER BY access_count DESC, importance DESC LIMIT 10
        """).fetchall()
        core = [c for c in core if c["id"] not in founding_ids]
        for c in core:
            results.append(dict(c) | {"similarity": 1.0, "tags": [], "decay": 1.0, "section": "Core Memories"})

        # Update access counts
        for r in results:
            conn.execute(
                "UPDATE memories SET access_count = access_count + 1, last_accessed = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
                (r["id"],)
            )
        conn.commit()

        # Fetch tags
        for r in results:
            tags = conn.execute("SELECT tag FROM memory_tags WHERE memory_id = ?", (r["id"],)).fetchall()
            r["tags"] = [t["tag"] for t in tags]

        conn.close()
        _print_boot_results(results)
        return

    # --- Semantic search mode ---
    query_embedding = get_embedding(query)
    query_bytes = struct.pack(f"{len(query_embedding)}f", *query_embedding)

    # Build filter
    active_filter = 0 if include_inactive else 1

    rows = conn.execute("""
        SELECT
            m.id, m.content, m.category, m.importance,
            m.created_at, m.last_accessed, m.access_count,
            m.session_id, ve.distance
        FROM memory_embeddings ve
        JOIN memories m ON m.id = ve.id
        WHERE ve.embedding MATCH ?
            AND k = ?
            AND m.active >= ?
        ORDER BY ve.distance ASC
    """, (query_bytes, limit * 4, active_filter)).fetchall()

    # Pre-fetch founding tags to skip decay
    founding_ids = set()
    try:
        founding_rows = conn.execute(
            "SELECT memory_id FROM memory_tags WHERE tag = 'founding'"
        ).fetchall()
        founding_ids = {r["memory_id"] for r in founding_rows}
    except Exception:
        pass

    for row in rows:
        # sqlite-vec returns L2 distance; convert to cosine similarity
        raw_similarity = 1.0 - (row["distance"] ** 2 / 2.0)
        # Founding memories never decay
        if row["id"] in founding_ids:
            decay = 1.0
        else:
            decay = compute_decay(row["category"], row["created_at"], row["last_accessed"])
        weighted_similarity = round(raw_similarity * decay, 3)

        if weighted_similarity < threshold:
            continue
        if category and row["category"] != category:
            continue
        if session_id and row["session_id"] != session_id:
            continue

        results.append(dict(row) | {"similarity": weighted_similarity, "raw_similarity": raw_similarity, "decay": decay})
        if len(results) >= limit:
            break

    # Update access counts
    for r in results:
        conn.execute(
            "UPDATE memories SET access_count = access_count + 1, last_accessed = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            (r["id"],)
        )
    conn.commit()

    # Fetch tags
    for r in results:
        tags = conn.execute("SELECT tag FROM memory_tags WHERE memory_id = ?", (r["id"],)).fetchall()
        r["tags"] = [t["tag"] for t in tags]
        if "distance" in r:
            del r["distance"]

    conn.close()
    _print_search_results(results, query, threshold)

def _print_boot_results(results):
    """Format boot recall output."""
    if not results:
        print("No memories found for boot sequence.")
        return

    current_section = None
    print("=== Boot Recall ===\n")
    for r in results:
        if r.get("section") != current_section:
            current_section = r["section"]
            print(f"--- {current_section} ---")
        tags_str = f" [{', '.join(r['tags'])}]" if r["tags"] else ""
        print(f"  #{r['id']} [{r['category']}] (importance: {r['importance']}){tags_str}")
        print(f"  {r['content']}")
        print()

def _print_search_results(results, query, threshold):
    """Format semantic search output."""
    if not results:
        print(f"No memories found matching '{query}' (threshold: {threshold})")
        return

    print(f"Found {len(results)} relevant memories:\n")
    for i, r in enumerate(results, 1):
        tags_str = f" [{', '.join(r['tags'])}]" if r["tags"] else ""
        decay_str = f" decay:{r['decay']}" if r['decay'] < 1.0 else ""
        session_str = f" session:{r['session_id']}" if r.get("session_id") else ""
        print(f"{i}. [{r['category']}] (score: {r['similarity']}{decay_str}, importance: {r['importance']}) #{r['id']}{session_str}")
        print(f"   {r['content']}")
        if tags_str:
            print(f"   Tags:{tags_str}")
        print(f"   Created: {r['created_at']} | Accessed: {r['access_count']}x")
        print()

def main():
    parser = argparse.ArgumentParser(description="Recall memories by semantic search")
    parser.add_argument("--query", help="Search query (not needed for --boot)")
    parser.add_argument("--limit", type=int, default=5, help="Max results (default: 5)")
    parser.add_argument("--threshold", type=float, default=0.3, help="Min similarity 0.0-1.0 (default: 0.3)")
    parser.add_argument("--category", help="Filter by category")
    parser.add_argument("--session-id", help="Filter by session ID (for in-session recall)")
    parser.add_argument("--boot", action="store_true", help="Boot mode: fetch session_weather + future events + core memories")
    parser.add_argument("--include-inactive", action="store_true", help="Include superseded/deleted memories")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()

    if not args.boot and not args.query:
        print("ERROR: --query is required unless using --boot mode", file=sys.stderr)
        sys.exit(1)

    recall_memories(args.db, args.query, args.limit, args.threshold,
                    args.category, args.session_id, args.boot, args.include_inactive)

if __name__ == "__main__":
    main()
