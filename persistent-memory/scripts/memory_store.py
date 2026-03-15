#!/usr/bin/env python3
"""Store a memory with its embedding in the persistent memory database."""

import argparse
import os
import sqlite3
import struct
import sys
import time

CATEGORIES = [
    "fact", "preference", "relationship", "entity",
    "verbatim", "future_event", "minor_detail", "inside_joke",
    "session_weather", "milestone", "shared_moment", "dynamic",
    "interaction_style"
]

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

def store_memory(db_path, content, category="fact", importance=0.5, source=None, session_id=None, tags=None):
    """Store a memory and its embedding."""
    conn = sqlite3.connect(db_path, timeout=10)
    load_vec_extension(conn)
    conn.execute("PRAGMA foreign_keys = ON")

    cursor = conn.execute(
        "INSERT INTO memories (content, category, importance, source, session_id) VALUES (?, ?, ?, ?, ?)",
        (content, category, importance, source, session_id)
    )
    memory_id = cursor.lastrowid

    embedding = get_embedding(content)
    embedding_bytes = struct.pack(f"{len(embedding)}f", *embedding)
    conn.execute(
        "INSERT INTO memory_embeddings (id, embedding) VALUES (?, ?)",
        (memory_id, embedding_bytes)
    )

    if tags:
        for tag in tags:
            conn.execute(
                "INSERT OR IGNORE INTO memory_tags (memory_id, tag) VALUES (?, ?)",
                (memory_id, tag.strip())
            )

    conn.commit()
    conn.close()

    print(f"OK: Stored memory #{memory_id} [category: {category}, importance: {importance}]")
    print(f"    Content: {content[:100]}")
    if session_id:
        print(f"    Session: {session_id}")
    if tags:
        print(f"    Tags: {', '.join(tags)}")

def main():
    parser = argparse.ArgumentParser(description="Store a memory with embedding")
    parser.add_argument("--text", required=True, help="Memory content to store")
    parser.add_argument("--category", default="fact", choices=CATEGORIES, help="Memory category")
    parser.add_argument("--importance", type=float, default=0.5, help="Importance score 0.0-1.0")
    parser.add_argument("--source", help="Source identifier")
    parser.add_argument("--session-id", help="Current session ID for in-session recall")
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument("--founding", action="store_true", help="Mark as founding memory (never expires)")
    parser.add_argument("--inferred", action="store_true", help="Mark as inferred (agent interpretation, not user's words)")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()

    if not 0.0 <= args.importance <= 1.0:
        print("ERROR: importance must be between 0.0 and 1.0", file=sys.stderr)
        sys.exit(1)

    tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
    if args.founding:
        tags.append("founding")
    if args.inferred:
        tags.append("inferred")
    tags = tags if tags else None
    store_memory(args.db, args.text, args.category, args.importance, args.source, args.session_id, tags)

if __name__ == "__main__":
    main()
