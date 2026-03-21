---
name: context-gardener
description: "Intelligent workspace maintenance — archives old files, consolidates contradictory memories, trims context bloat. Use when the agent has accumulated months of memory files, daily logs, transcripts, and stale memories. Use for 'clean up my workspace', 'my agent is slow', 'too much old context', 'archive old memories', 'find contradictions in memory'. Never deletes — archives to .archive/ for recovery. Works with or without persistent-memory skill."
---

# Context Gardener 🌿

Intelligent workspace maintenance. Archives old files, consolidates contradictory memories, trims context bloat. **Never deletes — archives.**

## Prerequisites

- Python 3.10+
- `GOOGLE_API_KEY` (for consolidation — uses Gemini 2.5 Flash)
- Works with or without persistent-memory/companion skills

## How It Works

```
Monthly cron → gardener_scan.py (analyzes everything)
           → gardener_report.py (human-readable report)
           → Send to user on Telegram
           → User reviews and approves
           → gardener_execute.py (applies approved changes)
```

**Nothing happens without user approval.**

## Scripts

### 1. Scan (`gardener_scan.py`)

Analyzes the entire workspace and produces a JSON report:

```bash
scripts/gardener_scan.py --workspace ~/.openclaw/workspace --output scan-report.json
```

**What it scans:**
- memory.db: stale memories, contradictions, duplicates, orphan entities
- Workspace files: old daily files, journals, observer reports
- Transcripts: count, size, age
- MEMORY.md: size

### 2. Report (`gardener_report.py`)

Converts the JSON scan into a readable markdown report:

```bash
scripts/gardener_report.py --scan-report scan-report.json --output report.md
```

### 3. Execute (`gardener_execute.py`)

Applies approved actions from the scan:

```bash
# Dry run first
scripts/gardener_execute.py --scan-report scan-report.json --workspace . --dry-run

# Execute all
scripts/gardener_execute.py --scan-report scan-report.json --workspace . --db memory.db

# Only archive files (no memory consolidation)
scripts/gardener_execute.py --scan-report scan-report.json --only archive

# Exclude specific memories from consolidation
scripts/gardener_execute.py --scan-report scan-report.json --exclude-ids 12,45
```

### 4. Consolidate (`gardener_consolidate.py`)

Merges contradictory memories into evolution narratives:

```bash
# Dry run
scripts/gardener_consolidate.py --pairs '[[12,45]]' --db memory.db --dry-run

# Execute
scripts/gardener_consolidate.py --pairs '[[12,45]]' --db memory.db --provider google
```

**Example:**
```
#12 "Utilise React" (January) + #45 "Passe à Vue" (February)
→ NEW: "A utilisé React (jan-fév), puis migré vers Vue. Raison: fatigue de l'écosystème."
→ #12 and #45 archived, NEW is active
```

### 5. Archive (`gardener_archive.py`)

Moves old files to `.archive/`:

```bash
scripts/gardener_archive.py --workspace . --daily-days 30 --dry-run
scripts/gardener_archive.py --workspace . --all
```

**What gets archived:**
- `memory/*.md` > 30 days → `.archive/memory/YYYY-MM/`
- `emotional-journal-*.md` > 60 days → `.archive/journals/`
- `observer-report-*.md` > 90 days → `.archive/reports/`

**What is NEVER archived:**
- SOUL.md, USER.md, IDENTITY.md, AGENTS.md
- CURRENT.md, consciousness-stream.md, relationship.md
- Founding, milestone, inside_joke memories

### 6. Rollback (`gardener_rollback.py`)

Undo any gardening operation:

```bash
# List available snapshots
scripts/gardener_rollback.py --list --workspace .

# Restore database
scripts/gardener_rollback.py --restore-db --snapshot .archive/db-snapshots/memory_20260321.db

# Restore a specific file
scripts/gardener_rollback.py --restore-file .archive/memory/2026-01/2026-01-15.md --to memory/2026-01-15.md
```

## Tri Intelligent (3 passes)

### Passe 1 — Contradictions temporelles
Two memories about the same topic with different conclusions → merge into evolution narrative.

### Passe 2 — Obsolescence confirmée
A memory whose replacement exists (moved, changed job, etc.) → merge with timeline.

### Passe 3 — Bruit
Low-importance memories, never recalled, > 60 days → archive (not merge, just move).

## Safety

1. **Snapshot before every modification** — always recoverable
2. **Dry-run by default** — shows without doing
3. **User validates** — never automatic
4. **Archive, never delete** — everything in `.archive/`
5. **Sacred files protected** — founding/milestone/inside_joke untouchable
6. **Full log** — `.gardener_log.jsonl` traces every action
7. **Rollback available** — restore any snapshot
