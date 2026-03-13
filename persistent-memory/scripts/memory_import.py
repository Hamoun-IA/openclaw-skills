#!/usr/bin/env python3
"""Import memories from a MEMORY.md markdown file into the database."""

import argparse
import os
import re
import sqlite3
import struct
import sys
import time

def load_vec_extension(conn):
    try:
        import sqlite_vec
        sqlite_vec.load(conn)
    except ImportError:
        print("ERROR: sqlite-vec not installed. Run: pip install sqlite-vec", file=sys.stderr)
        sys.exit(1)

def get_embeddings_batch(texts, max_retries=3):
    """Generate embeddings for multiple texts."""
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
                input=texts
            )
            return [d.embedding for d in response.data]
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"WARN: Batch embedding attempt {attempt + 1} failed: {e}. Retrying in {wait}s...", file=sys.stderr)
                time.sleep(wait)
            else:
                print(f"ERROR: Batch embedding failed: {e}", file=sys.stderr)
                sys.exit(1)

def guess_category(text, heading=""):
    """Guess memory category from content and heading context."""
    combined = (heading + " " + text).lower()

    if any(w in combined for w in ["préfère", "prefer", "aime", "love", "déteste", "hate", "favorite", "favori"]):
        return "preference"
    if any(w in combined for w in ["ami", "friend", "famille", "family", "frère", "sister", "chat", "cat", "dog", "partner"]):
        return "relationship"
    if any(w in combined for w in ["habitude", "habit", "routine", "toujours", "always", "every day", "chaque"]):
        return "preference"
    return "fact"

def parse_markdown(filepath):
    """Parse markdown file into memory entries."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    entries = []
    current_heading = ""

    for line in content.split("\n"):
        line = line.strip()

        heading_match = re.match(r"^#+\s+(.+)", line)
        if heading_match:
            current_heading = heading_match.group(1)
            continue

        bullet_match = re.match(r"^[-*]\s+(.+)", line)
        if bullet_match:
            text = bullet_match.group(1).strip()
            if len(text) < 10 or text.startswith("_") or text.startswith("("):
                continue
            entries.append({
                "content": text,
                "category": guess_category(text, current_heading),
                "heading": current_heading
            })
            continue

        if line and len(line) > 15 and not line.startswith("#") and not line.startswith("_"):
            entries.append({
                "content": line,
                "category": guess_category(line, current_heading),
                "heading": current_heading
            })

    return entries

def import_memories(source_path, db_path, batch_size=50, delay=1.0):
    """Parse markdown and import into database."""
    if not os.path.exists(source_path):
        print(f"ERROR: Source file not found: {source_path}", file=sys.stderr)
        sys.exit(1)

    entries = parse_markdown(source_path)
    if not entries:
        print("No memories found in source file.")
        return

    print(f"Parsed {len(entries)} memories from {source_path}")

    conn = sqlite3.connect(db_path, timeout=10)
    load_vec_extension(conn)
    conn.execute("PRAGMA foreign_keys = ON")

    imported = 0
    for i in range(0, len(entries), batch_size):
        batch = entries[i:i + batch_size]
        texts = [e["content"] for e in batch]

        embeddings = get_embeddings_batch(texts)

        for entry, embedding in zip(batch, embeddings):
            cursor = conn.execute(
                "INSERT INTO memories (content, category, importance, source) VALUES (?, ?, ?, ?)",
                (entry["content"], entry["category"], 0.5, "import")
            )
            memory_id = cursor.lastrowid

            embedding_bytes = struct.pack(f"{len(embedding)}f", *embedding)
            conn.execute(
                "INSERT INTO memory_embeddings (id, embedding) VALUES (?, ?)",
                (memory_id, embedding_bytes)
            )

            if entry["heading"]:
                conn.execute(
                    "INSERT OR IGNORE INTO memory_tags (memory_id, tag) VALUES (?, ?)",
                    (memory_id, entry["heading"].lower().replace(" ", "-"))
                )

            imported += 1

        conn.commit()
        print(f"  Imported batch {i // batch_size + 1}: {len(batch)} memories")

        if i + batch_size < len(entries):
            time.sleep(delay)

    conn.close()
    print(f"\nOK: Imported {imported} memories from {source_path}")

def main():
    parser = argparse.ArgumentParser(description="Import memories from MEMORY.md")
    parser.add_argument("--source", required=True, help="Path to markdown file")
    parser.add_argument("--batch-size", type=int, default=50, help="Embedding batch size (default: 50)")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between batches in seconds")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()
    import_memories(args.source, args.db, args.batch_size, args.delay)

if __name__ == "__main__":
    main()
