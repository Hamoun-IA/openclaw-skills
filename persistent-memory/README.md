# 🧠 persistent-memory

> Long-term memory + emotional intelligence for OpenClaw agents. SQLite, sqlite-vec, and GraphRAG.

**Version:** 3.9 · **Created:** March 2026

> **Want living presence (selfies, proactive messages, inside jokes)?** Use the [companion](../companion/) skill instead — it includes everything here PLUS presence features.

## What it does

Gives any OpenClaw agent a **real memory** that persists across sessions — facts, emotions, relationships, and identity.

| Problem | Solution |
|---------|----------|
| Agent forgets between sessions | Semantic memory + vector search |
| Agent loses context after compaction | Built-in 3-layer anti-compaction (session-journal hook) |
| Agent can't connect facts together | Knowledge graph (GraphRAG) |
| Agent has no emotional continuity | Consciousness stream + emotional boot |
| Agent doesn't learn from mistakes | Bridge to self-improving-agent |
| Agent doesn't know "us" | Relationship memory (milestones, dynamics) |

## Quick Start

### Option A — Universal Installer (recommended)

```bash
# From the repo root:
python3 install.py persistent-memory
```

Handles dependencies, skill copy, hook setup, and DB init automatically.

### Option B — Manual

```bash
# 1. Install the skill
cp -r persistent-memory ~/.openclaw/skills/

# 2. Install dependencies
pip install sqlite-vec openai

# 3. Initialize database
python3 scripts/memory_init.py --db memory.db

# 4. Set up automated crons (emotion, consciousness, observer, refresh)
python3 scripts/memory_setup_crons.py --timezone Europe/Brussels

# 5. Install anti-compaction hook
cp -r hooks/session-journal ~/.openclaw/hooks/
openclaw hooks enable session-journal
```

## Built-in Anti-Compaction

The `session-journal` hook provides complete anti-compaction protection — no external plugin needed.

| Layer | What it does |
|-------|-------------|
| **1. Message capture** | Every message logged to JSONL journal in real-time |
| **2. Periodic summaries** | Markdown snapshot every 10 messages + CURRENT.md refresh every 5 |
| **3. Compact hook** | `compact:before` triggers forced save just before compaction |

```bash
cp -r hooks/session-journal ~/.openclaw/hooks/
openclaw hooks enable session-journal
```

## Architecture

```
05:00  🎭 Agent Émotionnel (analyzes yesterday → emotional journal)
07:00  🧠 Agent Mémoire (reads journal → consciousness stream)
*/30   🔄 Agent Refresh (updates CURRENT.md + MAINTENANT section)
Boot   📋 Stream → CURRENT.md → Founding → Relationship → Briefing
Live   📓 Hook captures every message → external summary every 10 msgs
Live   🧠 Agent stores memories (double-pass: facts + trivial crucial)
Sun    👁️ Agent Observateur (weekly patterns, dynamics, insights)
```

## Memory Categories (12)

| Category | Decay | What it stores |
|----------|-------|---------------|
| `fact` | ∞ | Hard facts (age, location, job) |
| `preference` | ∞ | Likes, dislikes, choices |
| `relationship` | ∞ | Social dynamics |
| `entity` | ∞ | Named people, pets, places |
| `verbatim` | 14 days | Emotionally charged exact quotes |
| `future_event` | After date | Upcoming events |
| `minor_detail` | 7 days | Intimate passing details |
| `inside_joke` | ∞ | Shared references |
| `session_weather` | ∞ | Narrative emotional summary |
| `milestone` | ∞ | Founding relationship moments |
| `shared_moment` | 90 days | Shared experiences |
| `dynamic` | Mutable | Relationship dynamic observations |

Memories with decay lose relevance over time (anti-stalker). A recalled memory resets its decay — just like human memory. **Founding memories** (`--founding` flag) never expire.

## Scripts (25)

### Core Memory
| Script | What it does |
|--------|-------------|
| `memory_init.py` | Create the database |
| `memory_store.py` | Store a memory + embedding |
| `memory_recall.py` | Semantic search + boot mode |
| `memory_forget.py` | Soft-delete or supersede |
| `memory_consolidate.py` | Merge duplicates, cleanup, orphan edges |
| `memory_dump.py` | Export as readable markdown |
| `memory_import.py` | Import from MEMORY.md |

### Knowledge Graph
| Script | What it does |
|--------|-------------|
| `memory_graph_update.py` | Add entities & relations (with entity resolution) |
| `memory_graph_query.py` | Query: neighbors, paths, dump |
| `memory_graph_resolve.py` | Entity resolution (merge ambiguous/duplicate entities) |

### Emotional Intelligence
| Script | What it does |
|--------|-------------|
| `memory_emotion.py` | Track emotions (reaction + trigger + intensity) |
| `memory_consciousness.py` | Morning consciousness stream |
| `memory_observer.py` | Weekly meta-analysis report |
| `memory_relationship.py` | Evolving relationship DNA |
| `memory_briefing.py` | All-in-one morning briefing |
| `memory_current.py` | CURRENT.md micro-state (~500 chars) |
| `memory_reliability.py` | Verbatim/inferred ratio → feature gate mode |

### Bridges
| Script | What it does |
|--------|-------------|
| `memory_contradict.py` | Detect contradictions |
| `memory_bridge.py` | Bridge to self-improving-agent |

### Lifecycle
| Script | What it does |
|--------|-------------|
| `memory_threads.py` | Track unresolved topics |
| `memory_capsule.py` | Time-based memory delivery |
| `memory_session_summary.py` | External conversation summarizer |
| `memory_setup_crons.py` | Configure the automated agent cycle |

### Ops
| Script | What it does |
|--------|-------------|
| `memory_healthcheck.py` | Full system check (DB integrity, sqlite-vec, crons, entity backlog) |
| `test_critical.py` | 13 offline tests — run before any deployment |

## Feature Gates

Behavior adapts based on memory reliability (verbatim vs. inferred ratio):

| Mode | Trigger | Behavior |
|------|---------|----------|
| 🟢 `normal` | High reliability | Full features — references, followups |
| 🟡 `exploratory` | Medium reliability | Softer references ("il me semble que..."), no assertions |
| 🔴 `listen` | Low reliability / new user | Listen-only — no memory references |

## Key Design Principles

### Write > Think
Files survive compaction, context does not. When in doubt, write to disk.

### Resume, Don't Restart
After compaction, the agent continues where it was emotionally — not from neutral.

### The Surveillance Paradox
`[inferred]` memories influence tone but are NEVER cited explicitly. Only `[verbatim]` memories can be referenced in conversation. The agent perceives — it does not declare its analysis.

## Prerequisites

```bash
pip install sqlite-vec openai
```

| Key | Required | Used for |
|-----|----------|----------|
| `OPENAI_API_KEY` | ✅ Yes | Embeddings |
| `GOOGLE_API_KEY` | ✅ Yes | Summaries (Gemini) |
| `OPENROUTER_API_KEY` | Optional | Fallback for summaries |

## Cost

| Component | Frequency | Cost/month |
|-----------|-----------|-----------|
| Embeddings (OpenAI) | ~500 store/recall | ~$0.02 |
| 4 agent crons (Gemini 2.5 Flash) | Daily + weekly | ~$0.10 |
| Session summaries (hook) | Every 10 messages | ~$0.03 |
| **Total** | | **~$0.15/month** |

## Roadmap

- [ ] Contextual calibration (auto-detect work/night/vulnerable modes)
- [ ] Cold storage for very old memories
- [ ] TTL on occurrence counters
- [ ] Additional profiles: technical, creative, research
