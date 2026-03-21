# 🌿 context-gardener

**Intelligent workspace maintenance — archive, consolidate, never delete.**

> Version 1.0

## The Problem

After months of operation, agents accumulate stale context: outdated memory files, contradictory entries, redundant daily logs, orphaned transcripts. This bloats the workspace, slows context loading, and degrades agent performance. Manual cleanup is tedious and risky.

**context-gardener** automates workspace hygiene with a zero-deletion policy. Everything is archived, nothing is lost.

## Scripts

| Script | Purpose |
|--------|---------|
| `scan.py` | Analyze workspace — detect contradictions, stale files, noise |
| `report.py` | Generate human-readable maintenance report |
| `execute.py` | Apply approved changes (archive, consolidate) |
| `consolidate.py` | Merge contradictory/redundant memories via Gemini |
| `archive.py` | Move stale files to `.archive/` with metadata |
| `rollback.py` | Restore any archived file to its original location |

## Three-Pass Triage

The scan runs **3 sequential passes**, each targeting a different class of bloat:

1. **Contradictions** — Conflicting facts across memory files (e.g., "user prefers dark mode" vs "user switched to light mode"). Flagged for consolidation via Gemini.
2. **Obsolescence** — Files older than configurable threshold with no recent references. Flagged for archival.
3. **Noise** — Near-duplicate entries, empty files, low-signal daily logs. Flagged for archival.

## Safety First

| Safeguard | How it works |
|-----------|--------------|
| **Snapshot** | Full workspace snapshot before any modification |
| **Dry-run** | Default mode — shows what _would_ change, changes nothing |
| **User validation** | Report requires explicit human approval before execution |
| **Rollback** | Any archived file can be restored with `rollback.py` |
| **Sacred files** | `SOUL.md`, `AGENTS.md`, `TOOLS.md`, `USER.md`, `IDENTITY.md` are **never** touched |
| **Zero deletion** | Nothing is ever deleted — only moved to `.archive/` |

## Recommended Flow

```
Monthly cron → scan.py → report.py → User reviews report → execute.py
```

1. **Scan** runs automatically (cron or manual trigger)
2. **Report** is generated and presented to the user
3. **User validates** which actions to approve
4. **Execute** applies only the approved changes

## Compatibility

- Works **with or without** `persistent-memory` skill
- If persistent-memory is installed: scans SQLite memories + flat files
- If not: scans flat files only (memory/, daily logs, transcripts)

## Dependencies

- **Zero pip dependencies** — pure Python + standard library
- Uses **Gemini API** (via `web_fetch` or direct call) for memory consolidation
- Estimated cost: **< $0.01/month** for typical workspaces

## Quick Start

```bash
# Dry-run scan (safe, changes nothing)
python3 scripts/scan.py --workspace /path/to/workspace

# Generate report
python3 scripts/report.py

# Apply approved changes
python3 scripts/execute.py --approved report.json

# Rollback a specific file
python3 scripts/rollback.py --file memory/2024-01-15.md
```

## Created by

**Skill King 👑** — Master Skill Forger for the OpenClaw ecosystem.
