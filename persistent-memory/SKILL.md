---
name: persistent-memory
description: Persistent long-term and in-session memory using SQLite and sqlite-vec for semantic search. Stores, recalls, and consolidates memories across conversations and within long sessions. Use when the agent needs to remember user facts, preferences, habits, relationships, events, or emotional patterns. Use when the agent should learn about the user over time. Use for any "remember this", "what do you know about me", or "recall" request. Triggers automatically to extract information during meaningful exchanges and pre-compaction flush. Also maintains coherence during long sessions by storing key points that survive context compaction. Do not use for short-term within-conversation context that fits in the context window, or for file/document storage.
---

# Persistent Memory

Long-term and in-session memory with semantic search and decay weighting.

## Prerequisites

- Python 3.10+, `pip install sqlite-vec openai`, `OPENAI_API_KEY` set

## Setup

Run once per agent: `scripts/memory_init.py --db memory.db`

## Memory Profile

Load the appropriate profile from `references/profiles/` based on agent role. Default: `references/profiles/companion.md`. The profile defines extraction rules, categories, and recall strategies.

## Session Continuity (anti-compaction)

The companion hook `session-journal` automatically captures all messages and periodically summarizes them into `.session_snapshot.md`. This file survives compaction and keeps the agent coherent during long conversations.

### Setup (one-time)

Copy the hook to your hooks directory and enable it:
```bash
cp -r hooks/session-journal ~/.openclaw/hooks/
openclaw hooks enable session-journal
```

Configure the summarization provider in your agent config:
```json
{
  "hooks": {
    "internal": {
      "entries": {
        "session-journal": {
          "enabled": true,
          "env": {
            "SUMMARY_PROVIDER": "google",
            "GOOGLE_API_KEY": "your-key-here"
          }
        }
      }
    }
  }
}
```

Providers: `google` (Gemini 2.5 Flash, recommended), `openrouter`, `openai`

### How it works

1. Every message is automatically logged to `.session_journal.jsonl`
2. Every 10 messages, an external LLM summarizes the journal into `.session_snapshot.md`
3. The snapshot is always up-to-date and survives compaction
4. After compaction, read `.session_snapshot.md` to recover full context

### Manual summarization (without the hook)

If the hook is not installed, run manually:
```bash
scripts/memory_session_summary.py --journal .session_journal.jsonl --provider google
```

### Reading the snapshot (after compaction or context loss)

When the conversation context feels thin or after compaction, read the snapshot:
```bash
cat .session_snapshot.md
```

The snapshot contains: current topic, key decisions, people mentioned, tone, and recent raw messages.

## Core Flow

### 1. Morning Briefing (session start)

One call to get full boot context — session weather, time capsules, open threads, events, core memories:

```bash
scripts/memory_briefing.py --db memory.db
```

Alternatively, for lightweight boot or when only semantic recall is needed:
```bash
scripts/memory_recall.py --boot --db memory.db
```

### 2. In-Session Storage (during conversation)

Every ~5 meaningful exchanges, extract and store key information using the **Double-Pass** method:

**Pass 1 — Facts:** Explicit information (decisions, preferences, people, events).
**Pass 2 — Trivial Crucial:** Details in the margins (sensory details, exact phrasing during emotional moments, minor observations).

```bash
scripts/memory_store.py --text "<extracted fact>" --category <category> --importance <0.0-1.0> --session-id "<current_session_id>" --db memory.db
```

**Categories:** `fact`, `preference`, `relationship`, `entity`, `verbatim`, `future_event`, `minor_detail`, `inside_joke`, `session_weather`

Tag with `--session-id` to enable post-compaction recall within the same session.

### 3. Contextual Recall (mid-conversation)

When conversation touches a topic with potential stored context:

```bash
scripts/memory_recall.py --query "<topic>" --limit 5 --db memory.db
```

Filter options: `--category <cat>`, `--session-id <id>`, `--threshold <0.0-1.0>`

Decay weighting is automatic: `minor_detail` (7-day TTL) and `verbatim` (14-day TTL) scores decrease over time. Other categories have no decay.

### 4. Post-Compaction Recovery

After context compaction during a long session, recall session-specific memories:

```bash
scripts/memory_recall.py --query "conversation context" --session-id "<current_session_id>" --limit 15 --db memory.db
```

This recovers the thread that compaction summarized.

### 5. Pre-Compaction Flush

When receiving a memory flush prompt before compaction, extract all remaining unsaved information from the current conversation using the double-pass method. Store each memory, then generate a session_weather:

```bash
scripts/memory_store.py --text "<narrative emotional summary of the session so far>" --category session_weather --importance 0.9 --db memory.db
```

### 6. Session End

At natural conversation end, store final session_weather if not already done during flush. Run the double-pass one last time for any remaining information.

### 7. Forget (user request)

```bash
scripts/memory_forget.py --id <memory_id> --db memory.db
```

To supersede (correct a fact): store the new fact first, then:
```bash
scripts/memory_forget.py --id <old_id> --superseded-by <new_id> --db memory.db
```

### 8. Graph Update (after storing memories)

After storing memories that mention people, places, pets, or events, extract entities and their relationships into the knowledge graph.

**Single relation:**
```bash
scripts/memory_graph_update.py --source "David" --relation "friend_of" --target "Alex" --source-type person --target-type person --memory-id 4 --db memory.db
```

**Batch (preferred — fewer calls):**
```bash
scripts/memory_graph_update.py --json '[
  {"source":"David","relation":"has_pet","target":"Pixel","source_type":"person","target_type":"pet","memory_id":2},
  {"source":"David","relation":"friend_of","target":"Alex","source_type":"person","target_type":"person","memory_id":4}
]' --db memory.db
```

**Entity types:** `person`, `pet`, `place`, `event`, `organization`, `object`, `concept`

Extract entities during the double-pass: after storing the memory, identify any named entities and relationships, then batch-update the graph.

### 9. Graph Query (enriched recall)

Use the graph to answer relationship questions or enrich vector search results:

```bash
# Everything about a person
scripts/memory_graph_query.py --entity "Alex" --db memory.db

# All people known
scripts/memory_graph_query.py --type person --db memory.db

# How are two entities connected?
scripts/memory_graph_query.py --from-entity "Alex" --to-entity "Bruxelles" --depth 3 --db memory.db

# Full graph overview
scripts/memory_graph_query.py --dump --db memory.db
```

**When to use graph vs vector search:**
- *"Who is Alex?"* → Graph query (`--entity "Alex"`)
- *"What do I know about cooking?"* → Vector search (`--query "cooking"`)
- *"What's planned with Alex?"* → Graph (Alex's events) + Vector (context)

### 10. Contradiction Check (before storing corrections)

When a new fact seems to contradict existing knowledge, check before storing:

```bash
scripts/memory_contradict.py --text "David déteste le café" --db memory.db
```

If contradictions found: confirm with user, store the new fact, then supersede the old one.

### 11. Open Threads (track unresolved topics)

```bash
# Open a thread when user mentions a pending situation
scripts/memory_threads.py --open "David attend ses résultats médicaux" --db memory.db

# List open threads
scripts/memory_threads.py --list --db memory.db

# Resolve when outcome is known
scripts/memory_threads.py --resolve <id> --db memory.db

# Touch when topic is mentioned again
scripts/memory_threads.py --touch <id> --db memory.db
```

Follow up on open threads naturally, not forcefully. Mark stale after 14+ days without mention.

### 12. Time Capsules (deliver at a future date)

```bash
# Store a memory, then create a capsule
scripts/memory_store.py --text "David's birthday April 15" --category future_event --importance 0.9 --db memory.db
scripts/memory_capsule.py --create --memory-id <id> --date 2026-04-15 --db memory.db

# Check for due capsules (included in morning briefing automatically)
scripts/memory_capsule.py --due --db memory.db

# Mark delivered after presenting to user
scripts/memory_capsule.py --deliver <id> --db memory.db
```

### 13. Consolidation (periodic)

Preview: `scripts/memory_consolidate.py --dry-run --db memory.db`
Apply: `scripts/memory_consolidate.py --db memory.db`

See `references/strategies.md` for tuning.

### 14. Export (human review)

```bash
scripts/memory_dump.py --db memory.db
scripts/memory_dump.py --db memory.db -o memories_export.md
```

## Deciding What to Store

1. Personal information? → Store (`fact`, `preference`, `relationship`)
2. Pattern observed 2+ times? → Store (`preference` or `fact`)
3. Emotionally significant? → Store (`verbatim` or `minor_detail`)
4. Upcoming event with date? → Store (`future_event`)
5. One-time logistical message? → Skip
6. Filler/small talk? → Skip

When uncertain, do not store. A clean memory is more valuable than a complete one.

## The No-Enum Rule

Never describe emotions with numbers or scales. Always use narrative:
- ✅ *"Tired but relieved after resolving the server issue"*
- ❌ *"Mood: 6/10"*

## Automated Cycle (optional but recommended)

Set up the full memory lifecycle with one command:

```bash
scripts/memory_setup_crons.py --timezone Europe/Brussels --provider google
```

This shows you how to configure 3 automated jobs:

| Time | Job | What it does |
|------|-----|-------------|
| 23:30 | 🎭 **Emotional Journal** | Analyzes today's emotions → writes intimate journal |
| 07:00 | 🧠 **Consciousness Stream** | Generates narrative identity snapshot → `consciousness-stream.md` |
| Sunday 11:00 | 👁️ **Weekly Observer** | Meta-analysis of patterns, dynamics → weekly report |

The consciousness stream is read during the morning briefing. The emotional journal feeds into the next morning's consciousness. The observer catches what daily analysis misses.

**Estimated cost: ~$0.05/month** with Gemini 2.5 Flash.

### Emotion Tracking (during conversation)

When a strong emotion is detected, store it:

```bash
scripts/memory_emotion.py --store --reaction "éclat de rire" --trigger "anecdote du chat" --intensity 0.9 --valence positive --db memory.db
```

Valences: `positive`, `negative`, `neutral`, `mixed`

The emotional journal (`--journal`) uses these to write the end-of-day entry.

## Error Handling

If a script fails, read `references/troubleshooting.md`.

## References

- `references/schema.md` — Database structure and decay rules
- `references/strategies.md` — Consolidation and maintenance
- `references/migration.md` — Import from MEMORY.md
- `references/troubleshooting.md` — Common errors and fixes
- `references/profiles/companion.md` — Companion agent profile
