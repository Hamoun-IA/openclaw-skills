# 🧠 persistent-memory

> Long-term memory + session continuity for OpenClaw agents — powered by SQLite, sqlite-vec, and GraphRAG.

**Version:** 2.0 · **Created:** March 2026

## What it does

Gives any OpenClaw agent a **real memory** that persists across sessions and survives context compaction.

| Problem | Solution |
|---------|----------|
| Agent forgets between sessions | Semantic memory store with vector search |
| Agent loses context after compaction | Auto-capture hook + external summarization |
| Agent can't connect facts together | Knowledge graph (GraphRAG) |
| Agent doesn't detect contradictions | Contradiction engine |
| Agent forgets to follow up | Open threads tracking |
| Agent misses important dates | Time capsules |

## How it works

```
📨 Message arrives
 ↓
📓 [Hook] Auto-logged to journal
 ↓
🤖 Agent responds (uses recall for context)
 ↓
📓 [Hook] Response logged
 ↓
📊 Every 10 messages → external LLM summarizes → snapshot on disk
 ↓
🧹 Compaction? No problem — snapshot survives
 ↓
📖 Agent reads snapshot → continues seamlessly
```

## Memory categories

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

Memories with decay lose relevance over time (anti-stalker). A recalled memory resets its decay — just like human memory.

## Scripts (18)

| Script | What it does |
|--------|-------------|
| `memory_init.py` | Create the database |
| `memory_store.py` | Store a memory + embedding |
| `memory_recall.py` | Semantic search + boot mode |
| `memory_forget.py` | Soft-delete or supersede |
| `memory_consolidate.py` | Merge duplicates, cleanup |
| `memory_dump.py` | Export as readable markdown |
| `memory_import.py` | Import from MEMORY.md |
| `memory_graph_update.py` | Add entities & relations |
| `memory_graph_query.py` | Query the knowledge graph |
| `memory_contradict.py` | Detect contradictions |
| `memory_threads.py` | Track unresolved topics |
| `memory_capsule.py` | Time-based memory delivery |
| `memory_briefing.py` | Morning briefing (all-in-one boot) |
| `memory_session_summary.py` | External conversation summarizer |
| `memory_emotion.py` | Track emotions (reaction + trigger + intensity) + daily journal |
| `memory_consciousness.py` | Morning consciousness stream (narrative identity) |
| `memory_observer.py` | Weekly meta-analysis report |
| `memory_setup_crons.py` | One-command automated cycle setup |

## Hook: session-journal

Companion hook that automatically captures all messages and triggers periodic summarization.

**Setup:**
```bash
cp -r hooks/session-journal ~/.openclaw/hooks/
openclaw hooks enable session-journal
```

**Supports:** Google Gemini API (default), OpenRouter, OpenAI

**Cost:** ~$0.001 per 3-hour conversation with Gemini 2.5 Flash

## Prerequisites

```bash
pip install sqlite-vec openai
```

- `OPENAI_API_KEY` — for embeddings (required)
- `GOOGLE_API_KEY` or `OPENROUTER_API_KEY` — for session summarization (optional, needed for the hook)

## Quick start

```bash
# 1. Copy to your agent's skills
cp -r persistent-memory ~/.openclaw/skills/

# 2. Initialize the database
python3 scripts/memory_init.py --db memory.db

# 3. (Optional) Install the anti-compaction hook
cp -r hooks/session-journal ~/.openclaw/hooks/
openclaw hooks enable session-journal

# 4. Done — the agent handles the rest via SKILL.md instructions
```

## Memory profile

The skill ships with a **companion** profile (`references/profiles/companion.md`) designed for conversational agents. It includes:

- **Double-pass extraction** — facts + "trivial crucial" details
- **No-enum rule** — emotions described narratively, never as numbers
- **Session weather** — emotional handoff between sessions
- **Boot sequence** — weather + capsules + threads + events + core memories

Custom profiles can be added to `references/profiles/` for different agent types.

## GraphRAG

The knowledge graph maps relationships between entities:

```
[David] --lives_in--> [Brussels]
[David] --has_pet--> [Pixel]
[David] --friend_of--> [Alex]
[Alex] --invited_to--> [Weekend March 15]
```

Query examples:
```bash
# Everything about a person
memory_graph_query.py --entity "Alex"

# Path between two entities
memory_graph_query.py --from-entity "Alex" --to-entity "Brussels" --depth 3
# Result: Alex → friend_of → David → lives_in → Brussels
```

## Automated Memory Cycle

Set up the complete lifecycle with one command:

```bash
python3 scripts/memory_setup_crons.py --timezone Europe/Brussels --provider google
```

```
23:30  🎭 Emotional Journal → analyzes today's emotions
07:00  🧠 Consciousness Stream → "who am I this morning"
Boot   📋 Morning Briefing → reads stream + capsules + threads
Live   📓 Session Journal → auto-capture + external summary
Sun    👁️  Weekly Observer → patterns, dynamics, insights
```

**Cost: ~$0.05/month** with Gemini 2.5 Flash.

## Roadmap

- [ ] Automatic inside joke promotion
- [ ] Personality traits tracking
- [ ] Batch graph linking (consolidation-based)
- [ ] Additional profiles: technical, creative, research
