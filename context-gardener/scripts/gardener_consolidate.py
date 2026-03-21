#!/usr/bin/env python3
"""Consolidate contradictory/evolved memories intelligently.

Reads pairs of contradictory memories, calls an LLM to create an evolution
narrative, archives the originals, stores the consolidated version.

Usage:
  # Dry run (show what would happen)
  gardener_consolidate.py --pairs '[[12,45],[8,67]]' --db memory.db --dry-run

  # Execute consolidation
  gardener_consolidate.py --pairs '[[12,45]]' --db memory.db --provider google

  # From a scan report
  gardener_consolidate.py --from-report scan-report.json --db memory.db --dry-run
"""

import argparse
import json
import os
import shutil
import sqlite3
import sys
import urllib.request
from datetime import datetime, timezone

DEFAULT_MODELS = {
    "google": "gemini-2.5-flash-preview-04-17",
    "openrouter": "google/gemini-2.5-flash",
    "openai": "gpt-4o-mini",
}

CONSOLIDATION_PROMPT = """You are consolidating two memories that represent an evolution or contradiction.

Memory A (older): "{mem_a}"
Created: {date_a}

Memory B (newer): "{mem_b}"
Created: {date_b}

Write ONE consolidated memory that:
1. Captures the evolution (what changed and when)
2. Preserves the current truth (Memory B is more recent)
3. Keeps relevant context from Memory A
4. Is concise (1-2 sentences max)
5. Write in the same language as the memories

Output ONLY the consolidated memory text, nothing else."""

def snapshot_db(db_path):
    """Create a backup before modification."""
    archive_dir = os.path.join(os.path.dirname(db_path) or ".", ".archive", "db-snapshots")
    os.makedirs(archive_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(archive_dir, f"memory_{ts}.db")
    shutil.copy2(db_path, dest)
    print(f"  Snapshot: {dest}")
    return dest

def call_llm(prompt, provider, model):
    if provider == "google":
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("ERROR: GOOGLE_API_KEY not set", file=sys.stderr)
            sys.exit(1)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 256, "temperature": 0.2}}
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result["candidates"][0]["content"]["parts"][0]["text"].strip()
    else:
        base_url = "https://openrouter.ai/api/v1" if provider == "openrouter" else "https://api.openai.com/v1"
        api_key = os.environ.get("OPENROUTER_API_KEY" if provider == "openrouter" else "OPENAI_API_KEY")
        if not api_key:
            print(f"ERROR: API key not set for {provider}", file=sys.stderr)
            sys.exit(1)
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 256, "temperature": 0.2}
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        req = urllib.request.Request(f"{base_url}/chat/completions", data=json.dumps(payload).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"].strip()

def consolidate_pair(conn, id_a, id_b, provider, model, dry_run=False):
    """Consolidate two memories into one evolution narrative."""
    mem_a = conn.execute("SELECT * FROM memories WHERE id = ?", (id_a,)).fetchone()
    mem_b = conn.execute("SELECT * FROM memories WHERE id = ?", (id_b,)).fetchone()

    if not mem_a or not mem_b:
        print(f"  SKIP: Memory #{id_a} or #{id_b} not found")
        return None

    prompt = CONSOLIDATION_PROMPT.format(
        mem_a=mem_a["content"], date_a=mem_a["created_at"][:10],
        mem_b=mem_b["content"], date_b=mem_b["created_at"][:10]
    )

    consolidated = call_llm(prompt, provider, model)

    print(f"\n  Consolidating #{id_a} + #{id_b}:")
    print(f"    OLD: {mem_a['content'][:80]}")
    print(f"    OLD: {mem_b['content'][:80]}")
    print(f"    NEW: {consolidated}")

    if dry_run:
        print(f"    [DRY RUN] Would create new memory and archive originals")
        return None

    # Create consolidated memory
    category = mem_b["category"]  # Use newer category
    importance = max(mem_a["importance"], mem_b["importance"])

    cursor = conn.execute(
        "INSERT INTO memories (content, category, importance, source) VALUES (?, ?, ?, 'consolidation')",
        (consolidated, category, importance)
    )
    new_id = cursor.lastrowid

    # Tag as consolidated
    conn.execute("INSERT OR IGNORE INTO memory_tags (memory_id, tag) VALUES (?, 'consolidated')", (new_id,))

    # Transfer important tags from originals
    for old_id in [id_a, id_b]:
        tags = conn.execute("SELECT tag FROM memory_tags WHERE memory_id = ?", (old_id,)).fetchall()
        for t in tags:
            if t["tag"] not in ("consolidated", "inferred"):
                conn.execute("INSERT OR IGNORE INTO memory_tags (memory_id, tag) VALUES (?, ?)", (new_id, t["tag"]))

    # Archive originals
    conn.execute("UPDATE memories SET active = 0, superseded_by = ? WHERE id = ?", (new_id, id_a))
    conn.execute("UPDATE memories SET active = 0, superseded_by = ? WHERE id = ?", (new_id, id_b))

    print(f"    ✅ Created #{new_id}, archived #{id_a} + #{id_b}")
    return new_id

def main():
    parser = argparse.ArgumentParser(description="Consolidate contradictory memories")
    parser.add_argument("--pairs", help="JSON array of [id_a, id_b] pairs")
    parser.add_argument("--from-report", help="Read pairs from scan report JSON")
    parser.add_argument("--db", default="memory.db")
    parser.add_argument("--provider", default="google", choices=["google", "openrouter", "openai"])
    parser.add_argument("--model", help="Override model")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without doing it")
    args = parser.parse_args()

    model = args.model or DEFAULT_MODELS.get(args.provider)

    # Get pairs
    pairs = []
    if args.pairs:
        pairs = json.loads(args.pairs)
    elif args.from_report:
        with open(args.from_report) as f:
            report = json.load(f)
        for action in report.get("proposed_actions", []):
            if action["type"] == "consolidate" and "memories" in action:
                pairs.append(action["memories"])

    if not pairs:
        print("No pairs to consolidate.")
        return

    conn = sqlite3.connect(args.db, timeout=10)
    conn.row_factory = sqlite3.Row

    if not args.dry_run:
        snapshot_db(args.db)

    consolidated = 0
    for pair in pairs:
        if len(pair) != 2:
            continue
        result = consolidate_pair(conn, pair[0], pair[1], args.provider, model, args.dry_run)
        if result:
            consolidated += 1

    if not args.dry_run:
        conn.commit()

    conn.close()
    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"\n{prefix}Consolidation complete: {consolidated} pairs merged")

if __name__ == "__main__":
    main()
