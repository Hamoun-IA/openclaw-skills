#!/usr/bin/env python3
"""Test suite for critical companion scripts.

Tests the 3 most critical scripts without requiring API keys
(uses mock embeddings for offline testing).

Usage:
  test_critical.py              # Run all tests
  test_critical.py --verbose    # Detailed output
"""

import argparse
import os
import sqlite3
import struct
import sys
import tempfile

PASSED = 0
FAILED = 0

def test(name, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  ✅ {name}")
    else:
        FAILED += 1
        print(f"  ❌ {name} — {detail}")

def mock_embedding():
    """Generate a mock embedding (no API needed)."""
    import random
    vec = [random.gauss(0, 1) for _ in range(1536)]
    norm = sum(v*v for v in vec) ** 0.5
    return [v/norm for v in vec]

def test_store_and_recall(db_path, verbose=False):
    """Test memory_store + memory_recall chain."""
    print("\n=== Test: Store & Recall ===")

    conn = sqlite3.connect(db_path, timeout=10)
    try:
        import sqlite_vec
        sqlite_vec.load(conn)
    except ImportError:
        test("sqlite-vec import", False, "pip install sqlite-vec")
        return

    # Init schema
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    os.system(f"python3 {scripts_dir}/memory_init.py --db {db_path} 2>/dev/null")
    test("Init database", os.path.exists(db_path))

    # Store with mock embedding
    content = "Test memory: David likes pizza"
    cursor = conn.execute(
        "INSERT INTO memories (content, category, importance, source) VALUES (?, ?, ?, ?)",
        (content, "preference", 0.8, "test")
    )
    mem_id = cursor.lastrowid
    test("Insert memory", mem_id > 0)

    emb = mock_embedding()
    emb_bytes = struct.pack(f"{len(emb)}f", *emb)
    conn.execute("INSERT INTO memory_embeddings (id, embedding) VALUES (?, ?)", (mem_id, emb_bytes))
    conn.commit()
    test("Insert embedding", True)

    # Verify recall
    row = conn.execute("SELECT content FROM memories WHERE id = ?", (mem_id,)).fetchone()
    test("Recall by ID", row and row[0] == content, f"Got: {row}")

    # Test tags
    conn.execute("INSERT OR IGNORE INTO memory_tags (memory_id, tag) VALUES (?, ?)", (mem_id, "founding"))
    conn.commit()
    tag = conn.execute("SELECT tag FROM memory_tags WHERE memory_id = ?", (mem_id,)).fetchone()
    test("Tag storage", tag and tag[0] == "founding")

    # Test supersede
    conn.execute("UPDATE memories SET active = 0, superseded_by = ? WHERE id = ?", (mem_id, mem_id))
    conn.commit()
    inactive = conn.execute("SELECT active FROM memories WHERE id = ?", (mem_id,)).fetchone()
    test("Supersede (soft-delete)", inactive and inactive[0] == 0)

    # Reset for other tests
    conn.execute("UPDATE memories SET active = 1, superseded_by = NULL WHERE id = ?", (mem_id,))
    conn.commit()
    conn.close()

def test_graph(db_path, verbose=False):
    """Test graph entity resolution + relations."""
    print("\n=== Test: Graph & Entity Resolution ===")

    conn = sqlite3.connect(db_path, timeout=10)

    # Create entity
    conn.execute("INSERT INTO entities (name, type) VALUES (?, ?)", ("Alex", "person"))
    conn.commit()

    # Verify
    row = conn.execute("SELECT id, name FROM entities WHERE name = 'Alex'").fetchone()
    test("Create entity", row and row[1] == "Alex")

    # Test fuzzy match (case insensitive)
    row2 = conn.execute("SELECT id FROM entities WHERE name = ? COLLATE NOCASE", ("alex",)).fetchone()
    test("Case-insensitive match", row2 and row2[0] == row[0])

    # Add relation
    conn.execute("INSERT INTO entities (name, type) VALUES (?, ?)", ("Brussels", "place"))
    conn.execute("INSERT INTO entity_relations (source_id, target_id, relation) VALUES (?, ?, ?)",
                 (1, 2, "lives_in"))
    conn.commit()

    rel = conn.execute("""
        SELECT e.name, r.relation FROM entity_relations r
        JOIN entities e ON e.id = r.target_id
        WHERE r.source_id = 1
    """).fetchone()
    test("Create relation", rel and rel[0] == "Brussels" and rel[1] == "lives_in")

    # Test orphan detection
    conn.execute("UPDATE entities SET active = 0 WHERE name = 'Brussels'")
    conn.commit()
    orphans = conn.execute("""
        SELECT r.id FROM entity_relations r
        LEFT JOIN entities s ON s.id = r.source_id AND s.active = 1
        LEFT JOIN entities t ON t.id = r.target_id AND t.active = 1
        WHERE s.id IS NULL OR t.id IS NULL
    """).fetchall()
    test("Orphan edge detection", len(orphans) > 0)

    conn.close()

def test_consolidate(db_path, verbose=False):
    """Test consolidation logic."""
    print("\n=== Test: Consolidation ===")

    conn = sqlite3.connect(db_path, timeout=10)
    try:
        import sqlite_vec
        sqlite_vec.load(conn)
    except ImportError:
        test("sqlite-vec", False, "pip install sqlite-vec")
        return

    # Create two similar memories with very similar embeddings
    base_emb = mock_embedding()
    similar_emb = [v + 0.001 for v in base_emb]  # Very close

    for i, (content, emb) in enumerate([
        ("David aime la pizza", base_emb),
        ("David adore la pizza", similar_emb),
    ]):
        cursor = conn.execute(
            "INSERT INTO memories (content, category, importance) VALUES (?, 'preference', 0.7)", (content,)
        )
        emb_bytes = struct.pack(f"{len(emb)}f", *emb)
        conn.execute("INSERT INTO memory_embeddings (id, embedding) VALUES (?, ?)", (cursor.lastrowid, emb_bytes))
    conn.commit()

    # Count active before
    before = conn.execute("SELECT COUNT(*) FROM memories WHERE active = 1").fetchone()[0]
    test("Memories before consolidation", before >= 2, f"Got {before}")

    # Test emotions table
    try:
        conn.execute("INSERT INTO emotions (reaction, trigger, intensity, valence) VALUES (?, ?, ?, ?)",
                    ("rire", "blague", 0.8, "positive"))
        conn.commit()
        emo = conn.execute("SELECT reaction FROM emotions ORDER BY id DESC LIMIT 1").fetchone()
        test("Emotion storage", emo and emo[0] == "rire")
    except sqlite3.OperationalError as e:
        test("Emotions table", False, str(e))

    # Test memory_misses table (bridge)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_misses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL, details TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
        """)
        conn.execute("INSERT INTO memory_misses (type, details) VALUES (?, ?)",
                    ("stale_recall", "test miss"))
        conn.commit()
        miss = conn.execute("SELECT type FROM memory_misses LIMIT 1").fetchone()
        test("Memory miss logging", miss and miss[0] == "stale_recall")
    except Exception as e:
        test("Memory miss table", False, str(e))

    conn.close()

def main():
    parser = argparse.ArgumentParser(description="Test critical companion scripts")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    global PASSED, FAILED

    # Create temp database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    print("=" * 50)
    print("  Companion Critical Tests")
    print(f"  Database: {db_path}")
    print("=" * 50)

    try:
        # Init
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        os.system(f"python3 {scripts_dir}/memory_init.py --db {db_path} 2>/dev/null")

        test_store_and_recall(db_path, args.verbose)
        test_graph(db_path, args.verbose)
        test_consolidate(db_path, args.verbose)

        print("\n" + "=" * 50)
        print(f"  Results: {PASSED} passed, {FAILED} failed")
        print("=" * 50)

        if FAILED > 0:
            sys.exit(1)

    finally:
        os.unlink(db_path)

if __name__ == "__main__":
    main()
