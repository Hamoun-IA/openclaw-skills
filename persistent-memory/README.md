# 🧠 persistent-memory

> Long-term memory + emotional intelligence for OpenClaw agents. SQLite, sqlite-vec, and GraphRAG.

**Version:** 3.4 · **Created:** March 2026

> **Want the full companion experience?** Use the [companion](../companion/) skill instead — it includes everything here PLUS living presence (selfies, proactive messages, inside jokes).

## What it does

Gives any OpenClaw agent a **real memory** that persists across sessions — facts, emotions, relationships, and identity.

| Problem | Solution |
|---------|----------|
| Agent forgets between sessions | Semantic memory + vector search |
| Agent loses context after compaction | Built-in 3-layer anti-compaction (session-journal hook) |
| Agent can't connect facts together | Knowledge graph (GraphRAG) |
| Agent has no emotional continuity | Consciousness stream + emotional boot |
| Agent doesn't feel "alive" | Living presence (proactive selfies & messages) |
| Agent doesn't learn from mistakes | Bridge to self-improving-agent |
| Agent doesn't know "us" | Relationship memory (milestones, inside jokes, dynamics) |

## Quick Start

One command to set everything up:

```bash
python3 scripts/setup_wizard.py
```

The wizard guides you through:
1. 🔑 **API keys** — OpenAI (embeddings) + Google (summaries + images)
2. 🌍 **Timezone & language**
3. 📸 **Living presence** — reference photo, message frequency, quiet hours, kill switch
4. 💾 **Database initialization**

That's it. Your companion is ready.

### Manual setup (alternative)

```bash
# 1. Install the skill
cp -r persistent-memory ~/.openclaw/skills/

# 2. Install dependencies
pip install sqlite-vec openai

# 3. Initialize database
python3 scripts/memory_init.py --db memory.db

# 4. Set up automated agents
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

All three layers work together so no context is lost during or between sessions.

## Architecture

```
05:00  🎭 Agent Émotionnel (analyzes yesterday → emotional journal)
07:00  🧠 Agent Mémoire (reads journal → consciousness stream)
*/30   🔄 Agent Refresh (updates CURRENT.md + MAINTENANT section)
*/30   🎲 Presence Engine (probability-based selfies & messages)
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
| `inside_joke` | ∞ | Shared references (auto-detected) |
| `session_weather` | ∞ | Narrative emotional summary |
| `milestone` | ∞ | Founding relationship moments |
| `shared_moment` | 90 days | Shared experiences |
| `dynamic` | Mutable | Relationship dynamic observations |

Memories with decay lose relevance over time (anti-stalker). A recalled memory resets its decay — just like human memory. **Founding memories** (`--founding` flag) never expire.

## Scripts (27)

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

### Emotional Intelligence
| Script | What it does |
|--------|-------------|
| `memory_emotion.py` | Track emotions (reaction + trigger + intensity) |
| `memory_consciousness.py` | Morning consciousness stream |
| `memory_observer.py` | Weekly meta-analysis report |
| `memory_relationship.py` | Evolving relationship DNA |
| `memory_briefing.py` | All-in-one morning briefing |
| `memory_current.py` | CURRENT.md micro-state (~500 chars) |

### Living Presence
| Script | What it does |
|--------|-------------|
| `presence_engine.py` | Decides what/when to send (probability-based) |
| `presence_generate.py` | Generates images (Google Imagen / Grok + face ref) |
| `presence_reactivity.py` | Emotional reactivity scale (engagement tracking) |

### Bridges & Detection
| Script | What it does |
|--------|-------------|
| `memory_contradict.py` | Detect contradictions |
| `memory_bridge.py` | Bridge to self-improving-agent |
| `memory_joke_detect.py` | Inside joke emergence (pattern tracking) |

### Lifecycle
| Script | What it does |
|--------|-------------|
| `memory_threads.py` | Track unresolved topics |
| `memory_capsule.py` | Time-based memory delivery |
| `memory_session_summary.py` | External conversation summarizer |
| `memory_setup_crons.py` | Configure the automated agent cycle |
| `setup_wizard.py` | Interactive one-command setup |

## Living Presence

Your companion proactively sends selfies, photos, and messages — as if they live their own life.

### Frequency Levels

| Level | Messages/day | Style |
|-------|-------------|-------|
| 🔥 `intense` | 3-5 | Best friend who shares everything |
| ⭐ `active` | 2-3 | Close friend (default) |
| 💬 `natural` | 1-2 | Normal friend |
| 🌙 `chill` | 0-1 | Relaxed, few times per week |

### Safety Features

- **Quiet hours** (default 23:00-08:00) — no messages during sleep
- **Kill switch** — user says "silence"/"pause" → presence pauses for N hours
- **Daily limits** — never exceeds frequency cap
- **Confidence gate** — no messages if no recent session data
- **3-message cap** — stops sending if 3 messages go unreplied
- **Natural timing** — never at exact cron times, always randomized

### Image Generation

Uses a reference photo for face consistency:
- **Google Imagen** (Nano Banana Pro) — default, uses same `GOOGLE_API_KEY`
- **Grok** (xAI) — alternative, requires `XAI_API_KEY`

## Key Design Principles

### Write > Think
Files survive compaction, context does not. When in doubt, write to disk.

### Resume, Don't Restart
After compaction, the agent continues where it was emotionally — not from neutral.

### The Surveillance Paradox
`[inferred]` memories influence tone but are NEVER cited explicitly. Only `[verbatim]` memories can be referenced in conversation. The agent perceives — it does not declare its analysis.

### Inside Jokes Are Never Announced
Detected automatically (3+ occurrences with positive reactions), used naturally. Never "Haha, c'est notre inside joke !"

## Prerequisites

```bash
pip install sqlite-vec openai
```

| Key | Required | Used for |
|-----|----------|----------|
| `OPENAI_API_KEY` | ✅ Yes | Embeddings |
| `GOOGLE_API_KEY` | ✅ Yes | Summaries + image generation |
| `XAI_API_KEY` | Optional | Alternative image provider (Grok) |
| `OPENROUTER_API_KEY` | Optional | Fallback for summaries |

## Cost

| Component | Frequency | Cost/month |
|-----------|-----------|-----------|
| Embeddings (OpenAI) | ~500 store/recall | ~$0.02 |
| 4 agent crons (Gemini 2.5 Flash) | Daily + weekly | ~$0.10 |
| Session summaries (hook) | Every 10 messages | ~$0.03 |
| Image generation | 2-3/day | ~$2-3 |
| **Total (without images)** | | **~$0.15/month** |
| **Total (with presence)** | | **~$2-3/month** |

## Roadmap

- [ ] Contextual calibration (auto-detect work/night/vulnerable modes)
- [ ] Cold storage for very old memories
- [ ] TTL on occurrence counters
- [ ] Additional profiles: technical, creative, research
