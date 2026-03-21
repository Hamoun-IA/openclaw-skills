#!/usr/bin/env python3
"""Archive old files to .archive/ directory.

Moves files by age — never deletes. Everything is recoverable.

Usage:
  # Dry run
  gardener_archive.py --workspace . --dry-run

  # Archive daily files > 30 days
  gardener_archive.py --workspace . --daily-days 30

  # Archive everything archivable
  gardener_archive.py --workspace . --all

  # From scan report
  gardener_archive.py --from-report scan-report.json --workspace .
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

SACRED_FILES = {
    "SOUL.md", "USER.md", "IDENTITY.md", "AGENTS.md", "TOOLS.md",
    "CURRENT.md", "consciousness-stream.md", "relationship.md",
    "MEMORY.md", "HEARTBEAT.md", "BOOTSTRAP.md",
}

def archive_file(workspace, filepath, archive_subdir="misc"):
    """Move a file to .archive/"""
    src = os.path.join(workspace, filepath)
    if not os.path.exists(src):
        return False

    # Determine archive path
    archive_dir = os.path.join(workspace, ".archive", archive_subdir)
    os.makedirs(archive_dir, exist_ok=True)

    dest = os.path.join(archive_dir, os.path.basename(filepath))

    # Handle duplicates
    if os.path.exists(dest):
        name, ext = os.path.splitext(os.path.basename(filepath))
        ts = datetime.now(timezone.utc).strftime("%H%M%S")
        dest = os.path.join(archive_dir, f"{name}_{ts}{ext}")

    shutil.move(src, dest)
    return True

def archive_workspace(workspace, daily_days=30, journal_days=60, report_days=90, dry_run=False, from_report=None):
    """Archive old files."""
    now = datetime.now(timezone.utc)
    archived = 0
    actions = []

    # From report if provided
    if from_report:
        with open(from_report) as f:
            report = json.load(f)
        for item in report.get("archivable_files", []):
            path = item["path"]
            basename = os.path.basename(path)
            if basename in SACRED_FILES:
                continue

            if dry_run:
                print(f"  [DRY RUN] Would archive: {path} ({item.get('age_days', '?')} days old)")
            else:
                subdir = "memory" if path.startswith("memory/") else "journals" if "journal" in path else "reports"
                if archive_file(workspace, path, subdir):
                    print(f"  ✅ Archived: {path}")
                    archived += 1
        if not dry_run:
            print(f"\nArchived {archived} files")
        return

    # Daily memory files
    memory_dir = os.path.join(workspace, "memory")
    if os.path.isdir(memory_dir):
        for f in sorted(os.listdir(memory_dir)):
            if not f.endswith(".md") or len(f) != 13:
                continue
            date_str = f.replace(".md", "")
            try:
                fdate = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                age = (now - fdate).days
                if age > daily_days:
                    month_dir = fdate.strftime("%Y-%m")
                    if dry_run:
                        print(f"  [DRY RUN] memory/{f} → .archive/memory/{month_dir}/")
                    else:
                        archive_dir = os.path.join(workspace, ".archive", "memory", month_dir)
                        os.makedirs(archive_dir, exist_ok=True)
                        shutil.move(os.path.join(memory_dir, f), os.path.join(archive_dir, f))
                        archived += 1
            except ValueError:
                pass

    # Emotional journals
    for f in os.listdir(workspace):
        if not f.startswith("emotional-journal-") or not f.endswith(".md"):
            continue
        date_str = f.replace("emotional-journal-", "").replace(".md", "")
        try:
            jdate = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if (now - jdate).days > journal_days:
                if dry_run:
                    print(f"  [DRY RUN] {f} → .archive/journals/")
                else:
                    if archive_file(workspace, f, "journals"):
                        archived += 1
        except ValueError:
            pass

    # Observer reports
    for f in os.listdir(workspace):
        if not f.startswith("observer-report-") or not f.endswith(".md"):
            continue
        date_str = f.replace("observer-report-", "").replace(".md", "")
        try:
            rdate = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if (now - rdate).days > report_days:
                if dry_run:
                    print(f"  [DRY RUN] {f} → .archive/reports/")
                else:
                    if archive_file(workspace, f, "reports"):
                        archived += 1
        except ValueError:
            pass

    prefix = "[DRY RUN] " if dry_run else ""
    print(f"\n{prefix}Archived {archived} files to .archive/")

def main():
    parser = argparse.ArgumentParser(description="Archive old workspace files")
    parser.add_argument("--workspace", default=".", help="Workspace path")
    parser.add_argument("--daily-days", type=int, default=30, help="Archive daily files older than N days (default: 30)")
    parser.add_argument("--journal-days", type=int, default=60, help="Archive journals older than N days (default: 60)")
    parser.add_argument("--report-days", type=int, default=90, help="Archive reports older than N days (default: 90)")
    parser.add_argument("--from-report", help="Archive files listed in scan report")
    parser.add_argument("--all", action="store_true", help="Archive everything archivable")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    args = parser.parse_args()

    archive_workspace(args.workspace, args.daily_days, args.journal_days, args.report_days,
                     args.dry_run, args.from_report)

if __name__ == "__main__":
    main()
