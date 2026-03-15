#!/usr/bin/env python3
"""Consolidate memories: merge duplicates, deactivate stale entries."""

import argparse
import math
import sqlite3
import struct
import sys

def load_vec_extension(conn):
    try:
        import sqlite_vec
        sqlite_vec.load(conn)
    except ImportError:
        print("ERROR: sqlite-vec not installed. Run: pip install sqlite-vec", file=sys.stderr)
        sys.exit(1)

def cosine_similarity(vec_a, vec_b):
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

def consolidate(db_path, similarity_threshold=0.92, dry_run=False):
    """Merge near-duplicates and clean up past future_events."""
    conn = sqlite3.connect(db_path, timeout=10)
    load_vec_extension(conn)
    conn.execute("PRAGMA foreign_keys = ON")

    merged = 0
    cleaned = 0

    # --- Phase 1: Merge near-duplicates ---
    active_memories = conn.execute(
        "SELECT id, content, importance FROM memories WHERE active = 1 ORDER BY id"
    ).fetchall()

    embeddings = {}
    for mem in active_memories:
        row = conn.execute("SELECT embedding FROM memory_embeddings WHERE id = ?", (mem[0],)).fetchone()
        if row:
            vec = struct.unpack(f"{1536}f", row[0])
            embeddings[mem[0]] = vec

    already_merged = set()
    for i, mem_a in enumerate(active_memories):
        if mem_a[0] in already_merged:
            continue
        for mem_b in active_memories[i + 1:]:
            if mem_b[0] in already_merged:
                continue
            if mem_a[0] not in embeddings or mem_b[0] not in embeddings:
                continue

            sim = cosine_similarity(embeddings[mem_a[0]], embeddings[mem_b[0]])
            if sim >= similarity_threshold:
                if mem_a[2] > mem_b[2] or (mem_a[2] == mem_b[2] and len(mem_a[1]) >= len(mem_b[1])):
                    keep, discard = mem_a, mem_b
                else:
                    keep, discard = mem_b, mem_a

                if not dry_run:
                    conn.execute(
                        "UPDATE memories SET active = 0, superseded_by = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
                        (keep[0], discard[0])
                    )
                    conn.execute(
                        "INSERT OR IGNORE INTO memory_tags (memory_id, tag) SELECT ?, tag FROM memory_tags WHERE memory_id = ?",
                        (keep[0], discard[0])
                    )

                already_merged.add(discard[0])
                merged += 1
                print(f"MERGE: #{discard[0]} → #{keep[0]} (similarity: {sim:.3f})")
                print(f"  Kept:    {keep[1][:80]}")
                print(f"  Removed: {discard[1][:80]}")

    # --- Phase 2: Clean past future_events ---
    past_events = conn.execute("""
        SELECT id, content FROM memories
        WHERE active = 1 AND category = 'future_event'
        AND created_at < strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-7 days')
    """).fetchall()

    for ev in past_events:
        if not dry_run:
            conn.execute(
                "UPDATE memories SET active = 0, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
                (ev[0],)
            )
        cleaned += 1
        print(f"CLEAN: #{ev[0]} past future_event — {ev[1][:80]}")

    # --- Phase 3: Graph orphan cleanup ---
    orphaned = 0
    try:
        orphan_edges = conn.execute("""
            SELECT r.id FROM entity_relations r
            LEFT JOIN entities s ON s.id = r.source_id AND s.active = 1
            LEFT JOIN entities t ON t.id = r.target_id AND t.active = 1
            WHERE s.id IS NULL OR t.id IS NULL
        """).fetchall()

        for edge in orphan_edges:
            if not dry_run:
                conn.execute("DELETE FROM entity_relations WHERE id = ?", (edge[0],))
            orphaned += 1
            print(f"ORPHAN: Removed edge #{edge[0]} (missing entity)")
    except sqlite3.OperationalError:
        pass  # Graph tables may not exist

    if not dry_run:
        conn.commit()
    conn.close()

    prefix = "[DRY RUN] " if dry_run else ""
    print(f"\n{prefix}Consolidation complete: {merged} merged, {cleaned} cleaned, {orphaned} orphan edges removed")

def main():
    parser = argparse.ArgumentParser(description="Consolidate and clean up memories")
    parser.add_argument("--similarity", type=float, default=0.92, help="Merge threshold (default: 0.92)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()
    consolidate(args.db, args.similarity, args.dry_run)

if __name__ == "__main__":
    main()
