#!/usr/bin/env python3
"""Detect contradictions when storing a new memory.

Run BEFORE or AFTER storing a memory to check if it contradicts existing knowledge.
Returns potential contradictions for the agent to address.

Usage:
  memory_contradict.py --text "David déteste le café" --db memory.db
  memory_contradict.py --text "David habite à Paris" --category fact --db memory.db
"""

import argparse
import os
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

def get_embedding(text, max_retries=3):
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
            response = client.embeddings.create(model="text-embedding-3-small", input=text)
            return response.data[0].embedding
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** (attempt + 1))
            else:
                print(f"ERROR: Embedding failed: {e}", file=sys.stderr)
                sys.exit(1)

# Contradiction keyword pairs (if new text has one side and old text has the other)
CONTRADICTION_SIGNALS = [
    (["aime", "adore", "love", "like", "préfère", "prefer"], ["déteste", "hate", "horreur", "supporte pas", "dislikes"]),
    (["habite", "lives", "vit à", "moved to", "déménagé"], ["habite", "lives", "vit à", "moved to", "déménagé"]),
    (["travaille", "works", "job", "boulot"], ["travaille", "works", "job", "boulot"]),
    (["célibataire", "single"], ["couple", "marié", "married", "partner", "copain", "copine"]),
]

def detect_contradictions(db_path, text, category=None, similarity_threshold=0.65, limit=5):
    """Find potentially contradictory memories."""
    conn = sqlite3.connect(db_path, timeout=10)
    load_vec_extension(conn)
    conn.row_factory = sqlite3.Row

    embedding = get_embedding(text)
    query_bytes = struct.pack(f"{len(embedding)}f", *embedding)

    # Find similar memories (high similarity = same topic)
    cat_filter = "AND m.category = ?" if category else ""
    params = [query_bytes, limit * 3, 1] + ([category] if category else [])

    rows = conn.execute(f"""
        SELECT m.id, m.content, m.category, m.importance, m.created_at, ve.distance
        FROM memory_embeddings ve
        JOIN memories m ON m.id = ve.id
        WHERE ve.embedding MATCH ?
            AND k = ?
            AND m.active >= ?
            {cat_filter}
        ORDER BY ve.distance ASC
    """, params).fetchall()

    contradictions = []
    for row in rows:
        similarity = 1.0 - (row["distance"] ** 2 / 2.0)
        if similarity < similarity_threshold:
            continue

        # Check for semantic opposition
        is_contradiction = _check_opposition(text.lower(), row["content"].lower())

        if is_contradiction:
            contradictions.append({
                "id": row["id"],
                "content": row["content"],
                "category": row["category"],
                "importance": row["importance"],
                "similarity": round(similarity, 3),
                "created_at": row["created_at"]
            })

        if len(contradictions) >= limit:
            break

    conn.close()

    if not contradictions:
        print("No contradictions detected.")
        return

    print(f"⚠️  Found {len(contradictions)} potential contradiction(s):\n")
    print(f"New statement: \"{text}\"\n")
    for i, c in enumerate(contradictions, 1):
        print(f"{i}. #{c['id']} [{c['category']}] (similarity: {c['similarity']}, importance: {c['importance']})")
        print(f"   Existing: \"{c['content']}\"")
        print(f"   Created: {c['created_at']}")
        print()
    print("Action needed: Confirm with user, then supersede the incorrect memory with memory_forget.py --superseded-by")

def _check_opposition(new_text, old_text):
    """Heuristic check for semantic opposition between two texts."""
    # Same-topic contradictions (e.g., "lives in X" vs "lives in Y" with different X/Y)
    for group_a, group_b in CONTRADICTION_SIGNALS:
        new_has_a = any(w in new_text for w in group_a)
        old_has_b = any(w in old_text for w in group_b)
        new_has_b = any(w in new_text for w in group_b)
        old_has_a = any(w in old_text for w in group_a)

        # Opposite sentiment on same topic
        if (new_has_a and old_has_b) or (new_has_b and old_has_a):
            # Check they're not saying the exact same thing
            if new_text.strip() != old_text.strip():
                return True

    # Negation patterns
    negation_pairs = [
        ("ne pas", ""), ("pas ", ""), ("plus ", ""), ("jamais ", ""),
        ("not ", ""), ("never ", ""), ("no longer", ""),
    ]
    for neg, _ in negation_pairs:
        if (neg in new_text and neg not in old_text) or (neg not in new_text and neg in old_text):
            # Only flag if texts are on same topic (already filtered by similarity)
            return True

    return False

def main():
    parser = argparse.ArgumentParser(description="Detect contradictions with existing memories")
    parser.add_argument("--text", required=True, help="New statement to check")
    parser.add_argument("--category", help="Filter by category")
    parser.add_argument("--threshold", type=float, default=0.65, help="Similarity threshold for same-topic (default: 0.65)")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()
    detect_contradictions(args.db, args.text, args.category, args.threshold)

if __name__ == "__main__":
    main()
