#!/usr/bin/env python3
"""Add entities and relations to the knowledge graph.

Designed to be called by the agent after extracting entities from a memory.
The agent does the NLP extraction (via its own LLM capabilities),
this script handles the database operations.

Usage examples:
  # Add an entity
  memory_graph_update.py --add-entity "Alex" --type person

  # Add a relation (creates entities if they don't exist)
  memory_graph_update.py --source "David" --relation "friend_of" --target "Alex" --memory-id 4

  # Add multiple relations from JSON
  memory_graph_update.py --json '[{"source":"David","relation":"has_pet","target":"Pixel","target_type":"pet","memory_id":2}]'
"""

import argparse
import json
import sqlite3
import sys

def get_or_create_entity(conn, name, entity_type="unknown", aliases=None):
    """Get existing entity or create new one. Returns entity id.

    Entity Resolution: before creating, checks for similar entities
    to prevent fragmentation (Alex / mon ami Alex / Alexandre = same person).
    """
    # 1. Exact match (case-insensitive)
    row = conn.execute(
        "SELECT id FROM entities WHERE name = ? COLLATE NOCASE AND type = ?",
        (name, entity_type)
    ).fetchone()
    if row:
        return row[0]

    # 2. Check aliases
    row = conn.execute(
        "SELECT id, name FROM entities WHERE aliases LIKE ? COLLATE NOCASE AND type = ?",
        (f"%{name}%", entity_type)
    ).fetchone()
    if row:
        return row[0]

    # 3. Fuzzy match: check if name is contained in existing entity names or vice versa
    normalized = name.lower().strip()
    candidates = conn.execute(
        "SELECT id, name, aliases FROM entities WHERE type = ? AND active = 1",
        (entity_type,)
    ).fetchall()

    for candidate in candidates:
        cname = candidate[0 + 1].lower().strip()  # name column
        # "Alex" matches "Alexandre", "mon ami Alex" matches "Alex"
        if normalized in cname or cname in normalized:
            # Found a likely match — add as alias if not already
            cid = candidate[0]
            existing_aliases = candidate[2] or ""
            if name.lower() not in existing_aliases.lower():
                new_aliases = f"{existing_aliases}, {name}".strip(", ")
                conn.execute("UPDATE entities SET aliases = ? WHERE id = ?", (new_aliases, cid))
            return cid

    # 4. Partial match — ambiguous, flag it
    for candidate in candidates:
        cname = candidate[0 + 1].lower().strip()
        # Names that share a word but aren't contained (e.g., "Jean" vs "Jean-Pierre")
        name_words = set(normalized.split())
        cname_words = set(cname.split())
        overlap = name_words & cname_words
        if overlap and len(overlap) >= 1 and len(name_words) > 1:
            # Ambiguous — create but flag
            cursor = conn.execute(
                "INSERT INTO entities (name, type, aliases, metadata) VALUES (?, ?, ?, ?)",
                (name, entity_type, aliases, json.dumps({"ambiguous": True, "similar_to": candidate[0 + 1]}))
            )
            new_id = cursor.lastrowid
            print(f"WARN: Ambiguous entity '{name}' — similar to '{candidate[0 + 1]}'. Flagged for review.", file=sys.stderr)
            return new_id

    # 5. No match found — create new entity
    cursor = conn.execute(
        "INSERT INTO entities (name, type, aliases) VALUES (?, ?, ?)",
        (name, entity_type, aliases)
    )
    return cursor.lastrowid

def add_relation(conn, source_name, relation, target_name,
                 source_type="unknown", target_type="unknown", memory_id=None):
    """Add a relation between two entities. Creates entities if needed."""
    source_id = get_or_create_entity(conn, source_name, source_type)
    target_id = get_or_create_entity(conn, target_name, target_type)

    # Check for duplicate
    existing = conn.execute("""
        SELECT id FROM entity_relations
        WHERE source_id = ? AND target_id = ? AND relation = ? AND active = 1
    """, (source_id, target_id, relation)).fetchone()

    if existing:
        return existing[0], False  # Already exists

    cursor = conn.execute(
        "INSERT INTO entity_relations (source_id, target_id, relation, memory_id) VALUES (?, ?, ?, ?)",
        (source_id, target_id, relation, memory_id)
    )
    return cursor.lastrowid, True  # Newly created

def main():
    parser = argparse.ArgumentParser(description="Update the knowledge graph")
    parser.add_argument("--add-entity", help="Add a single entity by name")
    parser.add_argument("--type", default="unknown", help="Entity type (person, pet, place, event, organization, object, concept)")
    parser.add_argument("--aliases", help="Comma-separated aliases")
    parser.add_argument("--source", help="Source entity name for relation")
    parser.add_argument("--relation", help="Relation type")
    parser.add_argument("--target", help="Target entity name for relation")
    parser.add_argument("--source-type", default="unknown", help="Source entity type")
    parser.add_argument("--target-type", default="unknown", help="Target entity type")
    parser.add_argument("--memory-id", type=int, help="Associated memory ID")
    parser.add_argument("--json", help="JSON array of relations: [{source, relation, target, source_type?, target_type?, memory_id?}]")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db, timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")

    created_entities = 0
    created_relations = 0

    # Mode 1: Add single entity
    if args.add_entity:
        eid = get_or_create_entity(conn, args.add_entity, args.type, args.aliases)
        conn.commit()
        print(f"OK: Entity '{args.add_entity}' [{args.type}] → id #{eid}")
        conn.close()
        return

    # Mode 2: Add single relation
    if args.source and args.relation and args.target:
        rid, is_new = add_relation(
            conn, args.source, args.relation, args.target,
            args.source_type, args.target_type, args.memory_id
        )
        conn.commit()
        status = "created" if is_new else "already exists"
        print(f"OK: [{args.source}] --{args.relation}--> [{args.target}] ({status}, id #{rid})")
        conn.close()
        return

    # Mode 3: Batch from JSON
    if args.json:
        try:
            relations = json.loads(args.json)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)

        for rel in relations:
            if not all(k in rel for k in ("source", "relation", "target")):
                print(f"WARN: Skipping incomplete relation: {rel}", file=sys.stderr)
                continue

            rid, is_new = add_relation(
                conn,
                rel["source"], rel["relation"], rel["target"],
                rel.get("source_type", "unknown"),
                rel.get("target_type", "unknown"),
                rel.get("memory_id")
            )
            if is_new:
                created_relations += 1
            print(f"  [{rel['source']}] --{rel['relation']}--> [{rel['target']}] ({'new' if is_new else 'exists'})")

        conn.commit()
        print(f"\nOK: Processed {len(relations)} relations ({created_relations} new)")
        conn.close()
        return

    print("ERROR: Provide --add-entity, --source/--relation/--target, or --json", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()
