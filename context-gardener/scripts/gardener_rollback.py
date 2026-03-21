#!/usr/bin/env python3
"""Rollback a gardening operation by restoring from snapshots.

Usage:
  # List available snapshots
  gardener_rollback.py --list --workspace .

  # Restore DB from snapshot
  gardener_rollback.py --restore-db --snapshot .archive/db-snapshots/memory_20260321_143000.db --db memory.db

  # Restore an archived file
  gardener_rollback.py --restore-file .archive/memory/2026-01/2026-01-15.md --to memory/2026-01-15.md --workspace .
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

def list_snapshots(workspace):
    archive_dir = os.path.join(workspace, ".archive")
    if not os.path.isdir(archive_dir):
        print("No .archive/ directory found. Nothing to rollback.")
        return

    print("=== Available Snapshots ===\n")

    # DB snapshots
    db_dir = os.path.join(archive_dir, "db-snapshots")
    if os.path.isdir(db_dir):
        snapshots = sorted(os.listdir(db_dir), reverse=True)
        print(f"Database snapshots ({len(snapshots)}):")
        for s in snapshots[:10]:
            size = os.path.getsize(os.path.join(db_dir, s)) // 1024
            print(f"  {s} ({size} KB)")
        print()

    # Archived files by category
    for subdir in ["memory", "journals", "reports", "memory-snapshots"]:
        sub_path = os.path.join(archive_dir, subdir)
        if os.path.isdir(sub_path):
            count = sum(1 for _ in Path(sub_path).rglob("*") if _.is_file())
            print(f"Archived {subdir}: {count} files")

    print(f"\nRestore with:")
    print(f"  --restore-db --snapshot <path>")
    print(f"  --restore-file <archive-path> --to <destination>")

def restore_db(snapshot_path, db_path):
    if not os.path.exists(snapshot_path):
        print(f"ERROR: Snapshot not found: {snapshot_path}", file=sys.stderr)
        sys.exit(1)

    # Backup current before restoring
    if os.path.exists(db_path):
        backup = db_path + ".pre-rollback"
        shutil.copy2(db_path, backup)
        print(f"  Backed up current DB to {backup}")

    shutil.copy2(snapshot_path, db_path)
    print(f"  ✅ Restored {db_path} from {snapshot_path}")

def restore_file(workspace, archive_path, dest_path):
    full_archive = os.path.join(workspace, archive_path)
    full_dest = os.path.join(workspace, dest_path)

    if not os.path.exists(full_archive):
        print(f"ERROR: Archived file not found: {full_archive}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(full_dest), exist_ok=True)
    shutil.copy2(full_archive, full_dest)
    print(f"  ✅ Restored {dest_path} from {archive_path}")

def main():
    parser = argparse.ArgumentParser(description="Rollback gardening operations")
    parser.add_argument("--list", action="store_true", help="List available snapshots")
    parser.add_argument("--restore-db", action="store_true", help="Restore database from snapshot")
    parser.add_argument("--restore-file", help="Restore an archived file")
    parser.add_argument("--snapshot", help="Snapshot path (for --restore-db)")
    parser.add_argument("--to", help="Destination path (for --restore-file)")
    parser.add_argument("--db", default="memory.db")
    parser.add_argument("--workspace", default=".")
    args = parser.parse_args()

    if args.list:
        list_snapshots(args.workspace)
    elif args.restore_db:
        if not args.snapshot:
            print("ERROR: --snapshot required", file=sys.stderr)
            sys.exit(1)
        restore_db(args.snapshot, args.db)
    elif args.restore_file:
        if not args.to:
            print("ERROR: --to required", file=sys.stderr)
            sys.exit(1)
        restore_file(args.workspace, args.restore_file, args.to)
    else:
        list_snapshots(args.workspace)

if __name__ == "__main__":
    main()
