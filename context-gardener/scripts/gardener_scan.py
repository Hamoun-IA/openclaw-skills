#!/usr/bin/env python3
"""Scan the workspace for archivable/consolidable content.

Analyzes: memory.db (if exists), workspace files, transcripts, graph.
Produces a JSON report of proposed actions.

Usage:
  gardener_scan.py --workspace ~/.openclaw/workspace
  gardener_scan.py --workspace . --db memory.db
  gardener_scan.py --workspace . --output scan-report.json
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

def scan_workspace(workspace, db_path=None):
    """Full workspace scan."""
    report = {
        "scan_date": datetime.now(timezone.utc).isoformat(),
        "workspace": workspace,
        "stats": {},
        "contradictions": [],
        "stale_memories": [],
        "archivable_files": [],
        "orphan_entities": [],
        "proposed_actions": [],
    }

    now = datetime.now(timezone.utc)
    cutoff_30d = (now - timedelta(days=30)).isoformat()
    cutoff_60d = (now - timedelta(days=60)).isoformat()
    cutoff_90d = (now - timedelta(days=90)).isoformat()

    # --- Scan memory.db if exists ---
    effective_db = db_path or os.path.join(workspace, "memory.db")
    has_db = os.path.exists(effective_db)

    if has_db:
        conn = sqlite3.connect(effective_db, timeout=10)
        conn.row_factory = sqlite3.Row

        # Active memories count
        total_active = conn.execute("SELECT COUNT(*) as c FROM memories WHERE active = 1").fetchone()["c"]
        total_all = conn.execute("SELECT COUNT(*) as c FROM memories").fetchone()["c"]
        report["stats"]["active_memories"] = total_active
        report["stats"]["total_memories"] = total_all
        report["stats"]["archived_memories"] = total_all - total_active

        # Never recalled
        never_recalled = conn.execute("""
            SELECT id, content, category, importance, created_at FROM memories
            WHERE active = 1 AND access_count = 0 AND created_at < ?
            AND category NOT IN ('session_weather', 'milestone', 'inside_joke')
        """, (cutoff_60d,)).fetchall()
        report["stats"]["never_recalled"] = len(never_recalled)

        for m in never_recalled:
            # Check if it's a founding memory
            is_founding = conn.execute(
                "SELECT 1 FROM memory_tags WHERE memory_id = ? AND tag = 'founding'", (m["id"],)
            ).fetchone()
            if is_founding:
                continue

            report["stale_memories"].append({
                "id": m["id"],
                "content": m["content"][:100],
                "category": m["category"],
                "importance": m["importance"],
                "created_at": m["created_at"],
                "reason": f"Never recalled, {m['category']}, > 60 days old"
            })
            report["proposed_actions"].append({
                "type": "archive_memory",
                "id": m["id"],
                "reason": f"Never recalled, > 60 days, category: {m['category']}"
            })

        # Stale minor_details and session_weather
        stale_details = conn.execute("""
            SELECT id, content, category, created_at FROM memories
            WHERE active = 1 AND category IN ('minor_detail', 'verbatim')
            AND access_count = 0 AND created_at < ?
        """, (cutoff_30d,)).fetchall()

        for m in stale_details:
            is_founding = conn.execute(
                "SELECT 1 FROM memory_tags WHERE memory_id = ? AND tag = 'founding'", (m["id"],)
            ).fetchone()
            if is_founding:
                continue

            report["stale_memories"].append({
                "id": m["id"],
                "content": m["content"][:100],
                "category": m["category"],
                "created_at": m["created_at"],
                "reason": f"Stale {m['category']}, 0 access, > 30 days"
            })

        # Old session_weather (keep only last 10)
        old_weather = conn.execute("""
            SELECT id, content, created_at FROM memories
            WHERE active = 1 AND category = 'session_weather'
            ORDER BY created_at DESC
        """).fetchall()

        if len(old_weather) > 10:
            for w in old_weather[10:]:
                report["proposed_actions"].append({
                    "type": "archive_memory",
                    "id": w["id"],
                    "reason": "session_weather older than top 10"
                })

        # Orphan entities
        try:
            orphans = conn.execute("""
                SELECT e.id, e.name, e.type FROM entities e
                LEFT JOIN entity_relations r1 ON r1.source_id = e.id
                LEFT JOIN entity_relations r2 ON r2.target_id = e.id
                WHERE e.active = 1 AND r1.id IS NULL AND r2.id IS NULL
            """).fetchall()

            for o in orphans:
                report["orphan_entities"].append({
                    "id": o["id"], "name": o["name"], "type": o["type"]
                })
            report["stats"]["orphan_entities"] = len(orphans)
        except sqlite3.OperationalError:
            report["stats"]["orphan_entities"] = 0

        conn.close()

    # --- Scan workspace files ---
    # Daily memory files
    memory_dir = os.path.join(workspace, "memory")
    daily_files = []
    archivable_daily = []

    if os.path.isdir(memory_dir):
        for f in sorted(os.listdir(memory_dir)):
            if f.endswith(".md") and len(f) == 13:  # YYYY-MM-DD.md
                fpath = os.path.join(memory_dir, f)
                daily_files.append(f)
                date_str = f.replace(".md", "")
                try:
                    fdate = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    if (now - fdate).days > 30:
                        archivable_daily.append(f)
                        report["archivable_files"].append({
                            "path": f"memory/{f}",
                            "age_days": (now - fdate).days,
                            "size_kb": os.path.getsize(fpath) // 1024
                        })
                except ValueError:
                    pass

    report["stats"]["daily_files"] = len(daily_files)
    report["stats"]["daily_files_archivable"] = len(archivable_daily)

    # Emotional journals
    journals = [f for f in os.listdir(workspace) if f.startswith("emotional-journal-") and f.endswith(".md")]
    old_journals = []
    for j in journals:
        date_str = j.replace("emotional-journal-", "").replace(".md", "")
        try:
            jdate = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if (now - jdate).days > 60:
                old_journals.append(j)
                report["archivable_files"].append({
                    "path": j, "age_days": (now - jdate).days,
                    "size_kb": os.path.getsize(os.path.join(workspace, j)) // 1024
                })
        except ValueError:
            pass

    report["stats"]["emotional_journals"] = len(journals)
    report["stats"]["journals_archivable"] = len(old_journals)

    # Observer reports
    reports = [f for f in os.listdir(workspace) if f.startswith("observer-report-") and f.endswith(".md")]
    old_reports = []
    for r in reports:
        date_str = r.replace("observer-report-", "").replace(".md", "")
        try:
            rdate = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if (now - rdate).days > 90:
                old_reports.append(r)
                report["archivable_files"].append({
                    "path": r, "age_days": (now - rdate).days,
                    "size_kb": os.path.getsize(os.path.join(workspace, r)) // 1024
                })
        except ValueError:
            pass

    report["stats"]["observer_reports"] = len(reports)
    report["stats"]["reports_archivable"] = len(old_reports)

    # Transcripts
    sessions_dir = None
    for candidate in [os.path.join(workspace, "..", "sessions"), os.path.join(workspace, "sessions")]:
        if os.path.isdir(candidate):
            sessions_dir = candidate
            break

    if sessions_dir:
        transcripts = [f for f in os.listdir(sessions_dir) if f.endswith(".jsonl")]
        total_size = sum(os.path.getsize(os.path.join(sessions_dir, f)) for f in transcripts)
        report["stats"]["transcripts_count"] = len(transcripts)
        report["stats"]["transcripts_mb"] = round(total_size / (1024 * 1024), 1)

    # MEMORY.md size
    memory_md = os.path.join(workspace, "MEMORY.md")
    if os.path.exists(memory_md):
        report["stats"]["memory_md_kb"] = os.path.getsize(memory_md) // 1024

    return report

def main():
    parser = argparse.ArgumentParser(description="Scan workspace for gardening opportunities")
    parser.add_argument("--workspace", default=".", help="Workspace path")
    parser.add_argument("--db", help="Memory database path (auto-detected if not given)")
    parser.add_argument("--output", help="Output JSON report to file")
    args = parser.parse_args()

    report = scan_workspace(args.workspace, args.db)

    output = json.dumps(report, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"OK: Scan report saved to {args.output}")
        print(f"    Active memories: {report['stats'].get('active_memories', 'N/A')}")
        print(f"    Stale: {len(report['stale_memories'])}")
        print(f"    Archivable files: {len(report['archivable_files'])}")
        print(f"    Orphan entities: {len(report['orphan_entities'])}")
        print(f"    Proposed actions: {len(report['proposed_actions'])}")
    else:
        print(output)

if __name__ == "__main__":
    main()
