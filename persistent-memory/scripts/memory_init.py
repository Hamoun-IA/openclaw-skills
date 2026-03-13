#!/usr/bin/env python3
"""Initialize the persistent memory database with schema and sqlite-vec extension."""

import argparse
import sqlite3
import sys

def load_vec_extension(conn):
    """Load sqlite-vec extension."""
    try:
        import sqlite_vec
        sqlite_vec.load(conn)
    except ImportError:
        print("ERROR: sqlite-vec not installed. Run: pip install sqlite-vec", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to load sqlite-vec: {e}", file=sys.stderr)
        sys.exit(1)

def init_db(db_path):
    """Create database with full schema."""
    conn = sqlite3.connect(db_path)
    load_vec_extension(conn)

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'fact',
            importance REAL NOT NULL DEFAULT 0.5,
            source TEXT,
            session_id TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            access_count INTEGER NOT NULL DEFAULT 0,
            last_accessed TEXT,
            superseded_by INTEGER,
            active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS memory_tags (
            memory_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            PRIMARY KEY (memory_id, tag),
            FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
        CREATE INDEX IF NOT EXISTS idx_memories_active ON memories(active);
        CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC);
        CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id);

        -- Graph tables
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'unknown',
            aliases TEXT,
            first_seen TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            metadata TEXT,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_entities_name_type ON entities(name COLLATE NOCASE, type);

        CREATE TABLE IF NOT EXISTS entity_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            relation TEXT NOT NULL,
            memory_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (source_id) REFERENCES entities(id) ON DELETE CASCADE,
            FOREIGN KEY (target_id) REFERENCES entities(id) ON DELETE CASCADE,
            FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS idx_relations_source ON entity_relations(source_id);
        CREATE INDEX IF NOT EXISTS idx_relations_target ON entity_relations(target_id);
        CREATE INDEX IF NOT EXISTS idx_relations_relation ON entity_relations(relation);

        -- Time capsules
        CREATE TABLE IF NOT EXISTS time_capsules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_id INTEGER NOT NULL,
            deliver_date TEXT NOT NULL,
            delivered INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_capsules_date ON time_capsules(deliver_date);
        CREATE INDEX IF NOT EXISTS idx_capsules_delivered ON time_capsules(delivered);

        -- Open threads
        CREATE TABLE IF NOT EXISTS open_threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            memory_id INTEGER,
            opened_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            resolved_at TEXT,
            last_mentioned TEXT,
            FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS idx_threads_status ON open_threads(status);
    """)

    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memory_embeddings USING vec0(
            id INTEGER PRIMARY KEY,
            embedding FLOAT[1536]
        )
    """)

    conn.commit()
    conn.close()
    print(f"OK: Database initialized at {db_path}")

def main():
    parser = argparse.ArgumentParser(description="Initialize persistent memory database")
    parser.add_argument("--db", default="memory.db", help="Database path (default: memory.db)")
    args = parser.parse_args()
    init_db(args.db)

if __name__ == "__main__":
    main()
