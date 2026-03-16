#!/usr/bin/env python3
"""Query the knowledge graph: find entities, relations, paths, and summaries.

Usage examples:
  # Everything about an entity (neighbors + related memories)
  memory_graph_query.py --entity "David"

  # Specific relation type
  memory_graph_query.py --entity "David" --relation "friend_of"

  # All entities of a type
  memory_graph_query.py --type person

  # Path between two entities (up to depth N)
  memory_graph_query.py --from "Alex" --to "Bruxelles" --depth 3

  # Full graph dump
  memory_graph_query.py --dump
"""

import argparse
import sqlite3
import sys
from collections import deque

def query_entity(conn, name, relation_filter=None, depth=1):
    """Get an entity and its neighborhood."""
    entity = conn.execute(
        "SELECT * FROM entities WHERE name = ? COLLATE NOCASE AND active = 1",
        (name,)
    ).fetchone()

    if not entity:
        print(f"Entity '{name}' not found.")
        return

    print(f"=== {entity['name']} [{entity['type']}] ===")
    if entity['aliases']:
        print(f"Aliases: {entity['aliases']}")
    if entity['metadata']:
        print(f"Metadata: {entity['metadata']}")
    print()

    # Outgoing relations
    rel_filter = "AND r.relation = ?" if relation_filter else ""
    params_out = [entity['id']] + ([relation_filter] if relation_filter else [])
    params_in = [entity['id']] + ([relation_filter] if relation_filter else [])

    outgoing = conn.execute(f"""
        SELECT r.relation, e.name, e.type, r.memory_id
        FROM entity_relations r
        JOIN entities e ON e.id = r.target_id
        WHERE r.source_id = ? AND r.active = 1 {rel_filter}
        ORDER BY r.relation
    """, params_out).fetchall()

    incoming = conn.execute(f"""
        SELECT r.relation, e.name, e.type, r.memory_id
        FROM entity_relations r
        JOIN entities e ON e.id = r.source_id
        WHERE r.target_id = ? AND r.active = 1 {rel_filter}
        ORDER BY r.relation
    """, params_in).fetchall()

    if outgoing:
        print("Outgoing relations:")
        for r in outgoing:
            mem_ref = f" (memory #{r['memory_id']})" if r['memory_id'] else ""
            print(f"  --{r['relation']}--> {r['name']} [{r['type']}]{mem_ref}")
        print()

    if incoming:
        print("Incoming relations:")
        for r in incoming:
            mem_ref = f" (memory #{r['memory_id']})" if r['memory_id'] else ""
            print(f"  <--{r['relation']}-- {r['name']} [{r['type']}]{mem_ref}")
        print()

    # Related memories
    memory_ids = set()
    for r in outgoing + incoming:
        if r['memory_id']:
            memory_ids.add(r['memory_id'])

    if memory_ids:
        print("Related memories:")
        for mid in sorted(memory_ids):
            mem = conn.execute("SELECT content, category FROM memories WHERE id = ?", (mid,)).fetchone()
            if mem:
                print(f"  #{mid} [{mem['category']}] {mem['content'][:80]}")
        print()

    total = len(outgoing) + len(incoming)
    print(f"Total: {total} relations ({len(outgoing)} outgoing, {len(incoming)} incoming)")

def query_type(conn, entity_type):
    """List all entities of a given type."""
    entities = conn.execute(
        "SELECT * FROM entities WHERE type = ? AND active = 1 ORDER BY name",
        (entity_type,)
    ).fetchall()

    if not entities:
        print(f"No entities of type '{entity_type}' found.")
        return

    print(f"=== Entities of type '{entity_type}' ({len(entities)}) ===\n")
    for e in entities:
        rel_count = conn.execute(
            "SELECT COUNT(*) FROM entity_relations WHERE (source_id = ? OR target_id = ?) AND active = 1",
            (e['id'], e['id'])
        ).fetchone()[0]
        aliases = f" (aka {e['aliases']})" if e['aliases'] else ""
        print(f"  {e['name']}{aliases} — {rel_count} relations")

def find_path(conn, from_name, to_name, max_depth=3):
    """BFS path finding between two entities."""
    start = conn.execute(
        "SELECT id, name FROM entities WHERE name = ? COLLATE NOCASE AND active = 1",
        (from_name,)
    ).fetchone()
    end = conn.execute(
        "SELECT id, name FROM entities WHERE name = ? COLLATE NOCASE AND active = 1",
        (to_name,)
    ).fetchone()

    if not start:
        print(f"Entity '{from_name}' not found.")
        return
    if not end:
        print(f"Entity '{to_name}' not found.")
        return

    # BFS
    queue = deque([(start['id'], [(start['name'], None)])])
    visited = {start['id']}

    while queue:
        current_id, path = queue.popleft()
        if len(path) - 1 >= max_depth:
            continue

        neighbors = conn.execute("""
            SELECT r.target_id as next_id, e.name, r.relation
            FROM entity_relations r
            JOIN entities e ON e.id = r.target_id
            WHERE r.source_id = ? AND r.active = 1
            UNION
            SELECT r.source_id as next_id, e.name, r.relation
            FROM entity_relations r
            JOIN entities e ON e.id = r.source_id
            WHERE r.target_id = ? AND r.active = 1
        """, (current_id, current_id)).fetchall()

        for n in neighbors:
            if n['next_id'] == end['id']:
                full_path = path + [(n['name'], n['relation'])]
                print(f"Path found ({len(full_path) - 1} hops):\n")
                for i, (name, rel) in enumerate(full_path):
                    if i == 0:
                        print(f"  [{name}]")
                    else:
                        print(f"    --{rel}-->")
                        print(f"  [{name}]")
                return

            if n['next_id'] not in visited:
                visited.add(n['next_id'])
                queue.append((n['next_id'], path + [(n['name'], n['relation'])]))

    print(f"No path found between '{from_name}' and '{to_name}' within depth {max_depth}.")

def dump_graph(conn):
    """Dump the full graph."""
    entities = conn.execute("SELECT * FROM entities WHERE active = 1 ORDER BY type, name").fetchall()
    relations = conn.execute("""
        SELECT r.*, s.name as source_name, t.name as target_name
        FROM entity_relations r
        JOIN entities s ON s.id = r.source_id
        JOIN entities t ON t.id = r.target_id
        WHERE r.active = 1
        ORDER BY s.name
    """).fetchall()

    print(f"=== Knowledge Graph: {len(entities)} entities, {len(relations)} relations ===\n")

    # Group entities by type
    types = {}
    for e in entities:
        types.setdefault(e['type'], []).append(e)

    print("--- Entities ---")
    for t, ents in sorted(types.items()):
        print(f"\n  [{t}] ({len(ents)})")
        for e in ents:
            aliases = f" (aka {e['aliases']})" if e['aliases'] else ""
            print(f"    • {e['name']}{aliases}")

    print("\n--- Relations ---")
    for r in relations:
        print(f"  [{r['source_name']}] --{r['relation']}--> [{r['target_name']}]")

def main():
    parser = argparse.ArgumentParser(description="Query the knowledge graph")
    parser.add_argument("--entity", help="Query a specific entity")
    parser.add_argument("--relation", help="Filter by relation type (with --entity)")
    parser.add_argument("--type", help="List all entities of a type")
    parser.add_argument("--from-entity", help="Path start entity")
    parser.add_argument("--to-entity", help="Path end entity")
    parser.add_argument("--depth", type=int, default=3, help="Max path depth (default: 3)")
    parser.add_argument("--dump", action="store_true", help="Dump full graph")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db, timeout=10)
    conn.row_factory = sqlite3.Row

    if args.entity:
        query_entity(conn, args.entity, args.relation)
    elif args.type:
        query_type(conn, args.type)
    elif args.from_entity and args.to_entity:
        find_path(conn, args.from_entity, args.to_entity, args.depth)
    elif args.dump:
        dump_graph(conn)
    else:
        print("ERROR: Provide --entity, --type, --from-entity/--to-entity, or --dump", file=sys.stderr)
        sys.exit(1)

    conn.close()

if __name__ == "__main__":
    main()
