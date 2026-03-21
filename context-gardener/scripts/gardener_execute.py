#!/usr/bin/env python3
"""Execute approved gardening actions from a validated decision.

Usage:
  # Execute all approved actions
  gardener_execute.py --scan-report scan-report.json --workspace . --db memory.db

  # Execute only specific types
  gardener_execute.py --scan-report scan-report.json --only archive

  # Exclude specific memory IDs
  gardener_execute.py --scan-report scan-report.json --exclude-ids 12,45
"""

import argparse
import json
import os
import sys

def main():
    parser = argparse.ArgumentParser(description="Execute approved gardening actions")
    parser.add_argument("--scan-report", required=True)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--db", default="memory.db")
    parser.add_argument("--only", choices=["archive", "consolidate", "all"], default="all")
    parser.add_argument("--exclude-ids", help="Comma-separated memory IDs to skip")
    parser.add_argument("--provider", default="google")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(args.scan_report) as f:
        report = json.load(f)

    excluded = set()
    if args.exclude_ids:
        excluded = {int(x) for x in args.exclude_ids.split(",")}

    actions = report.get("proposed_actions", [])
    if not actions:
        print("No actions to execute.")
        return

    print(f"=== Executing {len(actions)} actions ===\n")
    if excluded:
        print(f"Excluding IDs: {excluded}\n")

    # Archive actions
    if args.only in ("archive", "all"):
        archive_actions = [a for a in actions if a["type"].startswith("archive")]
        if archive_actions:
            print(f"--- Archiving ({len(archive_actions)} actions) ---")
            scripts_dir = os.path.dirname(os.path.abspath(__file__))
            cmd = f"python3 {scripts_dir}/gardener_archive.py --from-report {args.scan_report} --workspace {args.workspace}"
            if args.dry_run:
                cmd += " --dry-run"
            os.system(cmd)

    # Consolidate actions
    if args.only in ("consolidate", "all"):
        consolidate_actions = [a for a in actions if a["type"] == "consolidate"]
        pairs = [a["memories"] for a in consolidate_actions if "memories" in a
                 and not any(m in excluded for m in a["memories"])]

        if pairs:
            print(f"\n--- Consolidating ({len(pairs)} pairs) ---")
            scripts_dir = os.path.dirname(os.path.abspath(__file__))
            pairs_json = json.dumps(pairs)
            cmd = f"python3 {scripts_dir}/gardener_consolidate.py --pairs '{pairs_json}' --db {args.db} --provider {args.provider}"
            if args.dry_run:
                cmd += " --dry-run"
            os.system(cmd)

    # Log execution
    log = {
        "executed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "scan_report": args.scan_report,
        "actions_total": len(actions),
        "excluded_ids": list(excluded),
        "dry_run": args.dry_run,
    }
    log_path = os.path.join(args.workspace, ".gardener_log.jsonl")
    with open(log_path, "a") as f:
        f.write(json.dumps(log) + "\n")

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Execution complete. Log: {log_path}")

if __name__ == "__main__":
    main()
