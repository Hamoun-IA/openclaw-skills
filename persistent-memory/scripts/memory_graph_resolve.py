#!/usr/bin/env python3
"""Resolve ambiguous entities in the knowledge graph.

Finds entities flagged as ambiguous and presents them for resolution.
Can be run by the observer agent or manually.

Usage:
  # List ambiguous entities
  memory_graph_resolve.py --list --db memory.db

  # Merge two entities (keep first, merge second into it)
  memory_graph_resolve.py --merge --keep 1 --absorb 5 --db memory.db

  # Mark as distinct (clear ambiguous flag — they are different people)
  memory_graph_resolve.py --distinct 3 --db memory.db

  # Prepare context for an agent to resolve
  memory_graph_resolve.py --prepare --db memory.db
"""

import argparse
import json
import sqlite3
import sys

def list_ambiguous(db_path):
    """List all ambiguous entities."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row

    entities = conn.execute("""
        SELECT id, name, type, aliases, metadata FROM entities
        WHERE active = 1 AND metadata LIKE '%ambiguous%'
        ORDER BY name
    """).fetchall()

    conn.close()

    if not entities:
        print("No ambiguous entities found. Graph is clean.")
        return

    print(f"=== Ambiguous Entities ({len(entities)}) ===\n")
    for e in entities:
        meta = json.loads(e["metadata"]) if e["metadata"] else {}
        similar = meta.get("similar_to", "?")
        aliases = f" (aka {e['aliases']})" if e["aliases"] else ""
        print(f"  #{e['id']} {e['name']}{aliases} [{e['type']}]")
        print(f"    Similar to: {similar}")
        print(f"    Action: --merge --keep <id> --absorb {e['id']}  OR  --distinct {e['id']}")
        print()

def merge_entities(db_path, keep_id, absorb_id):
    """Merge two entities — keep one, absorb the other."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    keep = conn.execute("SELECT * FROM entities WHERE id = ?", (keep_id,)).fetchone()
    absorb = conn.execute("SELECT * FROM entities WHERE id = ?", (absorb_id,)).fetchone()

    if not keep:
        print(f"ERROR: Entity #{keep_id} not found", file=sys.stderr)
        sys.exit(1)
    if not absorb:
        print(f"ERROR: Entity #{absorb_id} not found", file=sys.stderr)
        sys.exit(1)

    # Merge aliases
    keep_aliases = keep["aliases"] or ""
    absorb_aliases = absorb["aliases"] or ""
    all_aliases = set(filter(None, [a.strip() for a in (keep_aliases + ", " + absorb_aliases + ", " + absorb["name"]).split(",")]))
    all_aliases.discard(keep["name"])
    new_aliases = ", ".join(sorted(all_aliases)) if all_aliases else None

    # Update keep entity
    conn.execute("UPDATE entities SET aliases = ?, metadata = NULL WHERE id = ?", (new_aliases, keep_id))

    # Redirect all relations from absorbed to kept
    conn.execute("UPDATE entity_relations SET source_id = ? WHERE source_id = ?", (keep_id, absorb_id))
    conn.execute("UPDATE entity_relations SET target_id = ? WHERE target_id = ?", (keep_id, absorb_id))

    # Remove duplicate relations
    conn.execute("""
        DELETE FROM entity_relations WHERE id NOT IN (
            SELECT MIN(id) FROM entity_relations GROUP BY source_id, target_id, relation
        )
    """)

    # Deactivate absorbed entity
    conn.execute("UPDATE entities SET active = 0 WHERE id = ?", (absorb_id,))

    conn.commit()
    conn.close()

    print(f"OK: Merged #{absorb_id} ({absorb['name']}) → #{keep_id} ({keep['name']})")
    if new_aliases:
        print(f"    Aliases: {new_aliases}")

def mark_distinct(db_path, entity_id):
    """Clear ambiguous flag — entity is confirmed distinct."""
    conn = sqlite3.connect(db_path, timeout=10)

    entity = conn.execute("SELECT name, metadata FROM entities WHERE id = ?", (entity_id,)).fetchone()
    if not entity:
        print(f"ERROR: Entity #{entity_id} not found", file=sys.stderr)
        sys.exit(1)

    conn.execute("UPDATE entities SET metadata = NULL WHERE id = ?", (entity_id,))
    conn.commit()
    conn.close()

    print(f"OK: Entity #{entity_id} ({entity[0]}) marked as distinct (ambiguous flag cleared)")

def prepare_context(db_path):
    """Output ambiguous entities for an agent to resolve."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row

    entities = conn.execute("""
        SELECT e.id, e.name, e.type, e.aliases, e.metadata,
               COUNT(r.id) as relation_count
        FROM entities e
        LEFT JOIN entity_relations r ON (r.source_id = e.id OR r.target_id = e.id)
        WHERE e.active = 1 AND e.metadata LIKE '%ambiguous%'
        GROUP BY e.id
        ORDER BY e.name
    """).fetchall()

    conn.close()

    if not entities:
        print("No ambiguous entities to resolve.")
        return

    print(f"# Ambiguous Entities for Resolution ({len(entities)})\n")
    for e in entities:
        meta = json.loads(e["metadata"]) if e["metadata"] else {}
        print(f"- #{e['id']} **{e['name']}** [{e['type']}] — {e['relation_count']} relations")
        print(f"  Similar to: {meta.get('similar_to', '?')}")
        print(f"  Aliases: {e['aliases'] or 'none'}")
        print()
    print("For each: decide if same person (--merge) or different people (--distinct)")

def main():
    parser = argparse.ArgumentParser(description="Resolve ambiguous entities")
    parser.add_argument("--list", action="store_true", help="List ambiguous entities")
    parser.add_argument("--merge", action="store_true", help="Merge two entities")
    parser.add_argument("--keep", type=int, help="Entity ID to keep (with --merge)")
    parser.add_argument("--absorb", type=int, help="Entity ID to absorb (with --merge)")
    parser.add_argument("--distinct", type=int, help="Mark entity as distinct (clear ambiguous)")
    parser.add_argument("--prepare", action="store_true", help="Prepare data for agent resolution")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()

    if args.list:
        list_ambiguous(args.db)
    elif args.merge:
        if not args.keep or not args.absorb:
            print("ERROR: --merge requires --keep and --absorb", file=sys.stderr)
            sys.exit(1)
        merge_entities(args.db, args.keep, args.absorb)
    elif args.distinct is not None:
        mark_distinct(args.db, args.distinct)
    elif args.prepare:
        prepare_context(args.db)
    else:
        list_ambiguous(args.db)

if __name__ == "__main__":
    main()
