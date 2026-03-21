#!/usr/bin/env python3
"""Generate a human-readable gardening report from a scan.

Usage:
  gardener_report.py --scan-report scan-report.json
  gardener_report.py --scan-report scan-report.json --output report.md
"""

import argparse
import json
import os
import sys

def generate_report(scan_data, output=None):
    lines = []
    stats = scan_data.get("stats", {})

    lines.append(f"# 🌿 Context Gardener Report — {scan_data['scan_date'][:10]}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    if "active_memories" in stats:
        lines.append(f"- **{stats['active_memories']}** active memories ({stats.get('archived_memories', 0)} already archived)")
        lines.append(f"- **{stats.get('never_recalled', 0)}** never recalled (> 60 days)")
    lines.append(f"- **{stats.get('daily_files', 0)}** daily files ({stats.get('daily_files_archivable', 0)} archivable)")
    lines.append(f"- **{stats.get('emotional_journals', 0)}** emotional journals ({stats.get('journals_archivable', 0)} archivable)")
    lines.append(f"- **{stats.get('observer_reports', 0)}** observer reports ({stats.get('reports_archivable', 0)} archivable)")
    if "transcripts_mb" in stats:
        lines.append(f"- **{stats['transcripts_count']}** transcripts ({stats['transcripts_mb']} MB)")
    if "memory_md_kb" in stats:
        lines.append(f"- **MEMORY.md** size: {stats['memory_md_kb']} KB")
    if "orphan_entities" in stats:
        lines.append(f"- **{stats['orphan_entities']}** orphan entities in graph")
    lines.append("")

    # Contradictions
    contradictions = scan_data.get("contradictions", [])
    if contradictions:
        lines.append(f"## ⚠️ Contradictions ({len(contradictions)})")
        lines.append("")
        for c in contradictions:
            lines.append(f"- #{c.get('id_a', '?')} \"{c.get('content_a', '')[:60]}\"")
            lines.append(f"  ↔ #{c.get('id_b', '?')} \"{c.get('content_b', '')[:60]}\"")
            lines.append(f"  → Proposed: Consolidate into evolution narrative")
            lines.append("")

    # Stale memories
    stale = scan_data.get("stale_memories", [])
    if stale:
        lines.append(f"## 💤 Stale Memories ({len(stale)})")
        lines.append("")
        for s in stale[:20]:  # Show max 20
            lines.append(f"- #{s['id']} [{s['category']}] \"{s['content']}\"")
            lines.append(f"  Reason: {s['reason']}")
        if len(stale) > 20:
            lines.append(f"- ... and {len(stale) - 20} more")
        lines.append("")

    # Archivable files
    files = scan_data.get("archivable_files", [])
    if files:
        lines.append(f"## 📁 Files to Archive ({len(files)})")
        lines.append("")
        lines.append("| File | Age | Size |")
        lines.append("|------|-----|------|")
        for f in files[:30]:
            lines.append(f"| {f['path']} | {f['age_days']}d | {f.get('size_kb', '?')}KB |")
        if len(files) > 30:
            lines.append(f"| ... | {len(files) - 30} more | |")
        lines.append("")

    # Orphan entities
    orphans = scan_data.get("orphan_entities", [])
    if orphans:
        lines.append(f"## 🔗 Orphan Entities ({len(orphans)})")
        lines.append("")
        for o in orphans:
            lines.append(f"- {o['name']} [{o['type']}] — no relations")
        lines.append("")

    # Proposed actions summary
    actions = scan_data.get("proposed_actions", [])
    if actions:
        by_type = {}
        for a in actions:
            t = a["type"]
            by_type[t] = by_type.get(t, 0) + 1

        lines.append(f"## 🎯 Proposed Actions ({len(actions)})")
        lines.append("")
        for t, count in sorted(by_type.items()):
            lines.append(f"- **{t}**: {count} actions")
        lines.append("")

    lines.append("---")
    lines.append("⚠️ **None of these changes will be applied without your explicit approval.**")
    lines.append("Review and approve with: `gardener_execute.py --decision approve`")

    result = "\n".join(lines)

    if output:
        with open(output, "w") as f:
            f.write(result)
        print(f"OK: Report saved to {output}")
    else:
        print(result)

def main():
    parser = argparse.ArgumentParser(description="Generate gardening report")
    parser.add_argument("--scan-report", required=True, help="Path to scan JSON")
    parser.add_argument("--output", "-o", help="Output markdown file")
    args = parser.parse_args()

    with open(args.scan_report) as f:
        data = json.load(f)

    generate_report(data, args.output)

if __name__ == "__main__":
    main()
