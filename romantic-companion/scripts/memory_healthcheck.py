#!/usr/bin/env python3
"""Health check for the companion memory system.

Verifies: database integrity, sqlite-vec, cron agent outputs,
entity resolution backlog, and reliability status.

Run periodically or at boot to detect silent failures.

Usage:
  # Full health check
  memory_healthcheck.py --db memory.db

  # Check only cron outputs (are agents running?)
  memory_healthcheck.py --crons --db memory.db

  # Check sqlite-vec
  memory_healthcheck.py --vec --db memory.db

  # Prepare for agent consumption
  memory_healthcheck.py --prepare --db memory.db
"""

import argparse
import json
import os
import sqlite3
import struct
import sys
from datetime import datetime, timezone, timedelta

def check_database(db_path):
    """Verify database exists and has correct tables."""
    issues = []

    if not os.path.exists(db_path):
        return [{"severity": "critical", "component": "database", "issue": f"Database not found: {db_path}"}]

    conn = sqlite3.connect(db_path, timeout=10)

    required_tables = ["memories", "memory_tags", "memory_embeddings", "entities", "entity_relations"]
    existing = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

    for table in required_tables:
        if table not in existing:
            issues.append({"severity": "critical", "component": "database", "issue": f"Missing table: {table}"})

    # Check row counts
    try:
        mem_count = conn.execute("SELECT COUNT(*) FROM memories WHERE active = 1").fetchone()[0]
        if mem_count == 0:
            issues.append({"severity": "warning", "component": "database", "issue": "No active memories — database is empty"})
    except Exception as e:
        issues.append({"severity": "critical", "component": "database", "issue": f"Query failed: {e}"})

    conn.close()
    return issues

def check_vec(db_path):
    """Verify sqlite-vec is working."""
    issues = []

    try:
        import sqlite_vec
        conn = sqlite3.connect(db_path, timeout=10)
        sqlite_vec.load(conn)

        # Test query
        test_vec = struct.pack("1536f", *([0.1] * 1536))
        try:
            conn.execute("""
                SELECT id FROM memory_embeddings
                WHERE embedding MATCH ? AND k = 1
            """, (test_vec,)).fetchone()
        except Exception as e:
            issues.append({"severity": "warning", "component": "sqlite-vec", "issue": f"Vec query failed: {e}"})

        conn.close()
    except ImportError:
        issues.append({"severity": "critical", "component": "sqlite-vec", "issue": "sqlite-vec not installed. Run: pip install sqlite-vec"})
    except Exception as e:
        issues.append({"severity": "critical", "component": "sqlite-vec", "issue": f"sqlite-vec load failed: {e}"})

    return issues

def check_crons(db_path):
    """Check if cron agents have produced recent output."""
    issues = []
    now = datetime.now(timezone.utc)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row

    # Check consciousness stream
    if os.path.exists("consciousness-stream.md"):
        mtime = datetime.fromtimestamp(os.path.getmtime("consciousness-stream.md"), tz=timezone.utc)
        age_hours = (now - mtime).total_seconds() / 3600
        if age_hours > 48:
            issues.append({"severity": "warning", "component": "consciousness-cron",
                          "issue": f"Consciousness stream is {age_hours:.0f}h old (expected <24h)"})
    else:
        issues.append({"severity": "info", "component": "consciousness-cron",
                      "issue": "No consciousness-stream.md found (cron may not be set up)"})

    # Check emotional journal
    today = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    journal_today = f"emotional-journal-{today}.md"
    journal_yesterday = f"emotional-journal-{yesterday}.md"

    if not os.path.exists(journal_today) and not os.path.exists(journal_yesterday):
        issues.append({"severity": "info", "component": "emotional-cron",
                      "issue": "No recent emotional journal found"})

    # Check session weather freshness
    latest_weather = conn.execute("""
        SELECT created_at FROM memories
        WHERE category = 'session_weather' AND active = 1
        ORDER BY created_at DESC LIMIT 1
    """).fetchone()

    if latest_weather:
        weather_age = (now - datetime.fromisoformat(
            latest_weather["created_at"].replace("Z", "+00:00")
        )).total_seconds() / 3600
        if weather_age > 72:
            issues.append({"severity": "warning", "component": "session-weather",
                          "issue": f"Last session weather is {weather_age:.0f}h old"})

    # Check observer report (weekly)
    observer_files = [f for f in os.listdir(".") if f.startswith("observer-report-") and f.endswith(".md")]
    if observer_files:
        latest_report = sorted(observer_files)[-1]
        report_date = latest_report.replace("observer-report-", "").replace(".md", "")
        try:
            report_dt = datetime.strptime(report_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            age_days = (now - report_dt).days
            if age_days > 14:
                issues.append({"severity": "warning", "component": "observer-cron",
                              "issue": f"Last observer report is {age_days} days old (expected weekly)"})
        except ValueError:
            pass

    # Check entity resolution backlog
    try:
        ambiguous = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE active = 1 AND metadata LIKE '%ambiguous%'"
        ).fetchone()[0]
        if ambiguous > 5:
            issues.append({"severity": "warning", "component": "entity-resolution",
                          "issue": f"{ambiguous} ambiguous entities need resolution (backlog > 2 weeks?)"})
    except Exception:
        pass

    conn.close()
    return issues

def run_healthcheck(db_path, check_type="all"):
    """Run health checks and report."""
    all_issues = []

    if check_type in ("all", "db"):
        all_issues.extend(check_database(db_path))

    if check_type in ("all", "vec"):
        all_issues.extend(check_vec(db_path))

    if check_type in ("all", "crons"):
        all_issues.extend(check_crons(db_path))

    return all_issues

def print_report(issues):
    """Print health check report."""
    severity_emoji = {"critical": "🔴", "warning": "🟡", "info": "ℹ️"}

    critical = [i for i in issues if i["severity"] == "critical"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    info = [i for i in issues if i["severity"] == "info"]

    if not issues:
        print("✅ All systems healthy!")
        return

    print("=== Memory Health Check ===\n")

    if critical:
        print("🔴 CRITICAL:")
        for i in critical:
            print(f"  [{i['component']}] {i['issue']}")
        print()

    if warnings:
        print("🟡 WARNINGS:")
        for i in warnings:
            print(f"  [{i['component']}] {i['issue']}")
        print()

    if info:
        print("ℹ️  INFO:")
        for i in info:
            print(f"  [{i['component']}] {i['issue']}")
        print()

    print(f"Summary: {len(critical)} critical, {len(warnings)} warnings, {len(info)} info")

    if critical:
        print("\n⚠️  Critical issues must be resolved before the companion can function properly.")

def main():
    parser = argparse.ArgumentParser(description="Memory system health check")
    parser.add_argument("--db", default="memory.db", help="Database path")
    parser.add_argument("--crons", action="store_true", help="Check cron outputs only")
    parser.add_argument("--vec", action="store_true", help="Check sqlite-vec only")
    parser.add_argument("--prepare", action="store_true", help="Output for agent")
    args = parser.parse_args()

    check_type = "all"
    if args.crons:
        check_type = "crons"
    elif args.vec:
        check_type = "vec"

    issues = run_healthcheck(args.db, check_type)

    if args.prepare:
        print(json.dumps(issues, indent=2))
    else:
        print_report(issues)

if __name__ == "__main__":
    main()
