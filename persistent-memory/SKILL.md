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

## Compatibility with Lossless Claw (LCM)

This skill works best alongside the [Lossless Claw](https://github.com/Martian-Engineering/lossless-claw) plugin — a DAG-based context engine that replaces OpenClaw's built-in compaction. LCM handles intra-session continuity (short-term), this skill handles cross-session memory (long-term).

**With LCM installed (recommended):**
- LCM handles all intra-session context — no message is ever lost during a conversation
- Disable the `session-journal` hook and the `memory-realtime-refresh` cron — they are redundant
- Keep all other components: memory store/recall, graph, emotions, consciousness, observer, relationship
- Install LCM: `openclaw plugins install @martian-engineering/lossless-claw`

**Without LCM:**
- The skill handles everything on its own with the session-journal hook + refresh agent
- Less performant for intra-session continuity, but fully autonomous

| Component | With LCM | Without LCM |
|-----------|----------|-------------|
| Intra-session continuity | ✅ LCM (DAG) | ⚠️ Hook + refresh |
| Cross-session memory | ✅ This skill | ✅ This skill |
| Emotion tracking | ✅ This skill | ✅ This skill |
| Graph/Consciousness/Observer | ✅ This skill | ✅ This skill |

## Session Continuity (anti-compaction — without LCM)

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

## Boot Sequence (session start)

Read these files in order at the start of every session:

1. `CURRENT.md` — micro-state (~500 chars): mood, topic, context, relationship
2. `consciousness-stream.md` — narrative identity ("who am I today")
3. Run `scripts/memory_briefing.py` — capsules, threads, events, core memories
4. `relationship.md` — relationship DNA (tone, inside jokes, patterns)

**Principle: Write > Think.** Files survive compaction, context does not.

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

## The Surveillance Paradox

Memories tagged `inferred` (agent's interpretation) influence tone but are NEVER cited explicitly. Only `verbatim` memories (user's actual words) can be referenced in conversation. The agent perceives — it does not declare its analysis.

```bash
# User said this → verbatim, can be referenced
scripts/memory_store.py --text "Je sais pas ce que je ferais sans toi" --category verbatim --db memory.db

# Agent interpreted this → inferred, influences tone only
scripts/memory_store.py --text "David semble stressé par son travail" --category fact --inferred --db memory.db

# Moment of vulnerability → founding, never expires
scripts/memory_store.py --text "David s'est confié sur sa rupture" --category verbatim --founding --db memory.db
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

## Automated Agent Cycle (optional but recommended)

Three isolated agents run on a schedule, each with a clean context focused on their task:

```bash
scripts/memory_setup_crons.py --timezone Europe/Brussels
```

| Time | Agent | Context | Output |
|------|-------|---------|--------|
| 23:30 | 🎭 **Agent Émotionnel** | Only today's emotions + weather | Emotional journal |
| 07:00 | 🧠 **Agent Mémoire** | Only yesterday's data + journal | `consciousness-stream.md` |
| Sun 11:00 | 👁️ **Agent Observateur** | Only 7 days of data | Weekly report |

Each agent is an **isolated OpenClaw session** (`sessionTarget: "isolated"`) — no conversation history pollution, no context bleed. The scripts prepare the data (`--prepare`), the agent does the reasoning.

Use `--json` to get cron configurations ready to paste or create via the cron tool.

**The cycle:**
```
23:30  🎭 Émotionnel analyses → journal intime
07:00  🧠 Mémoire reads journal → consciousness stream
Boot   📋 Agent principal reads stream → starts day with full context
Live   📓 Hook captures everything → snapshot survives compaction
Sun    👁️ Observateur reads the week → patterns, signals, dynamics
```

**Cost: ~$0.10/month** · Refresh runs 48x/day, others once/day or weekly.

### CURRENT.md (real-time micro-state)

Updated every 30 min by the refresh agent and during pre-compaction flush. Ultra-light (~500 chars):

```bash
# Manual update
scripts/memory_current.py --mood "taquin" --topic "planning weekend" --relationship "complicité forte"

# Auto-update from journal
scripts/memory_current.py --from-journal .session_journal.jsonl --db memory.db
```

### Relationship DNA (evolving bond)

Initialize once, then let the observer agent update it periodically:

```bash
# Initialize
scripts/memory_relationship.py --init

# Prepare data for agent analysis
scripts/memory_relationship.py --prepare --db memory.db
```

### Emotion Tracking (during conversation)

When a strong emotion is detected, store it:

```bash
scripts/memory_emotion.py --store --reaction "éclat de rire" --trigger "anecdote du chat" --intensity 0.9 --valence positive --db memory.db
```

Valences: `positive`, `negative`, `neutral`, `mixed`

### Data Preparation (for agents)

Each script supports `--prepare` to output raw data without calling an LLM — designed for agent consumption:

```bash
scripts/memory_emotion.py --prepare --db memory.db       # Today's emotions
scripts/memory_consciousness.py --prepare --db memory.db  # Yesterday's context
scripts/memory_observer.py --prepare --db memory.db       # Weekly data
```

## Bridge: persistent-memory ↔ self-improving-agent

If the `self-improving-agent` skill is installed, use the bridge to sync learnings to memory.

### Sync corrections as memories

When the user corrects the agent, sync the correction to both systems:

```bash
# 1. Log in LEARNINGS.md (self-improving-agent handles this)
# 2. Sync to persistent-memory
scripts/memory_bridge.py --sync-learning --text "David préfère les réponses directes" --category preference --source "LRN-20260315-001" --db memory.db
```

### Interaction style tracking

Store observations about HOW the user communicates:

```bash
scripts/memory_bridge.py --sync-style --text "Plus réceptif en soirée aux idées créatives, factuelles le matin" --db memory.db
```

### Safe promotion to SOUL.md

Before promoting a behavioral learning to SOUL.md, **always check**:

```bash
scripts/memory_bridge.py --check-promotion --text "David n'aime pas les disclaimers" --min-occurrences 3 --db memory.db
```

**Safety rule:** A learning must have 3+ occurrences across 2+ distinct sessions AND no contradictions before being promoted to SOUL.md. This prevents a single misunderstanding from corrupting the agent's personality.

### Memory miss monitoring

Log when recall fails to improve the system:

```bash
# Types: stale_recall, missed_store, irrelevant_recall
scripts/memory_bridge.py --log-miss --type stale_recall --details "Recalled outdated preference for Node.js" --db memory.db

# Review patterns
scripts/memory_bridge.py --review-misses --db memory.db
```

### Scan LEARNINGS.md for sync candidates

```bash
scripts/memory_bridge.py --scan --learnings-path .learnings/LEARNINGS.md --db memory.db
```

## Living Presence (companion mode)

The companion can proactively send selfies, photos, and messages — as if they live their own life.

### Setup

Run the wizard: `scripts/setup_wizard.py`

Or configure manually:
1. Place a reference photo in `assets/reference/face.jpg`
2. Set frequency in `persistent-memory.json`: `intense` (3-5/day), `active` (2-3/day, default), `natural` (1-2/day), `chill` (0-1/day)

### How it works

A cron runs every 30 min. The presence engine:
1. Checks the current moment (morning/midday/afternoon/evening/night)
2. Rolls against the probability table for the configured frequency
3. Considers: time since last message, messages sent today, daily limit
4. If sending: prepares context from persistent-memory (weather, threads, emotions)
5. An isolated agent generates the prompt, image, and caption
6. Image is sent via Telegram

The agent decides **what** to share based on memory context. If the user was sad yesterday, the morning message is warmer. If there's a time capsule due, the agent works it in naturally.

### Scripts

```bash
# Check if something should be sent now
scripts/presence_engine.py --check --db memory.db

# Prepare context for an isolated agent
scripts/presence_engine.py --prepare --db memory.db

# Generate an image
scripts/presence_generate.py --prompt "Taking a selfie at a café" --provider google

# Force a specific moment (testing)
scripts/presence_engine.py --force morning --db memory.db
```

### Natural timing

Messages are NEVER sent at exact cron times. The engine uses probability, not schedules:
- 70% chance of a morning message ≠ always at 8:00
- Minimum 2h between messages
- Daily limits per frequency level (active = max 3)
- Sleeping hours (2h-6h) = no messages

### Kill switch

The user can pause presence at any time:

```bash
# Pause for 8 hours (default)
scripts/presence_engine.py --pause

# Pause for custom duration
scripts/presence_engine.py --pause 12

# Resume immediately
scripts/presence_engine.py --resume
```

The agent should also detect natural language triggers: "silence", "pause", "tranquille", "laisse-moi", "j'ai besoin d'espace" → activate the kill switch automatically.

Quiet hours are configured in `persistent-memory.json` (`presence.quietHours: "23:00-08:00"`). The setup wizard configures both.

See `references/presence-activities.md` for activity catalogue and `references/presence-prompts.md` for image prompt templates.

## Error Handling

If a script fails, read `references/troubleshooting.md`.

## References

- `references/schema.md` — Database structure and decay rules
- `references/strategies.md` — Consolidation and maintenance
- `references/migration.md` — Import from MEMORY.md
- `references/troubleshooting.md` — Common errors and fixes
- `references/compaction-config.md` — Recommended OpenClaw compaction settings
- `references/profiles/companion.md` — Companion agent profile
