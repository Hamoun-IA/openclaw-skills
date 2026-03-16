# 📡 agent-pulse

> Inter-agent visibility protocol — the human never asks "what happened?"

**Version:** 2.2 · **Created:** March 2026

## The Problem

In multi-agent setups, the human has **zero visibility** on background work. Agent A delegates to Agent B, B delegates to C… and the human stares at silence wondering if anything is happening.

**agent-pulse** eliminates this. Every inter-agent interaction is visible to the human, always.

## How It Works

Four signal levels, from delegation to completion:

| Level | Signal | When |
|-------|--------|------|
| 🚀 **Departure** | "Transmis à [Agent]" | Immediately before `sessions_send`/`sessions_spawn` |
| ⏳ **Heartbeat** | Progress update | Adaptive: none (<2min), halfway (2-10min), every 5min (10min+) |
| ✅ **Completion** | Result summary | Always — every task closes the loop |
| 🛑 **Abort/Escalation** | Error + options | On failure, timeout, or blockage |

### Departure (immediate, no exceptions)

Before any delegation, the human gets a message. Fire-and-forget or sync — doesn't matter, the human knows.

### Heartbeat (adaptive)

Scales with task duration. Max 5 heartbeats per delegation — after 5 without completion, escalate.

### Completion (always)

Every task ends with a confidence-tagged report:
- `✅` — Verified, high confidence
- `⚠️✅` — Done but uncertain
- `🔥` — Failed

### Abort/Escalation

| Signal | Meaning |
|--------|---------|
| 🛑 | Aborted — explain why |
| ✋ | Blocked — waiting for external input |
| 🔥 | Failed — something broke |

## Delegation Patterns

Five patterns for every multi-agent scenario:

| Pattern | Use Case | Who Reports |
|---------|----------|-------------|
| **Fire-and-forget** | Target has its own channel to the human | Target agent |
| **Wait-and-relay** | Target has NO channel | Sender relays |
| **Chain** | A → B → C sequential pipeline | Final agent only |
| **Broadcast** | Parallel requests to N agents | One synthesizer |
| **Relay** | Receive + reformat for human | Relay agent |

## Emoji Protocol

| Emoji | Meaning |
|-------|---------|
| 👀 | Message seen / acknowledged |
| ⚡ | Processing / working on it |
| 🎉 | Done / completed |
| 🤔 | Need info / question pending |
| 🫡 | Forwarded to another agent |
| 🔥 | Urgent / problem detected |
| 🛑 | Aborted / can't complete |

## Promise Tracker (Restart Survival)

**Problem:** An agent says "I'll get back to you" → restarts → forgets everything → eternal silence.

**Solution:** Every promise is logged to `.agent_promises.jsonl` BEFORE the action. On boot, the agent replays unresolved promises.

### How It Works

1. **Log before act** — Before any async commitment, append to `.agent_promises.jsonl`:
   ```json
   {"id":"abc123","promise":"deploy skill on nova","target":"user","ts":"2026-03-16T23:00:00Z","status":"pending"}
   ```
2. **Boot check** — On startup, read `.agent_promises.jsonl` and filter `status: pending`:
   - If resumable → **re-execute** the promise
   - If stale (>configured timeout) → **alert the user**: "I promised X but couldn't complete it"
3. **Resolve** — On completion, append a resolution entry (`status: done` or `status: failed`)

### Timeout Detection

Promises older than their configured TTL trigger an alert at next boot or heartbeat cycle. Default TTL: 30 minutes.

### Restart Announcement

Before a planned restart, the agent scans pending promises and announces:
> ⚠️ Restarting — 2 tasks in flight: [deploy skill on nova], [update README]. Will resume on boot.

### Integration with Pulse Levels

| Level | Promise Tracker Role |
|-------|---------------------|
| 🚀 Departure | Log promise before delegation |
| ⏳ Heartbeat | Check for overdue promises |
| ✅ Completion | Resolve promise (`done` / `failed`) |
| 🛑 Abort | Resolve promise as `failed` + explain |

- One file per agent: `.agent_promises.jsonl` in workspace root
- Append-only — no edits, no deletions
- Compact periodically (archive resolved pairs to `.agent_promises_archive.jsonl`)

### Safety Mechanisms (v2.2)

Three structural safeguards hardening the Promise Tracker against real-world failure modes:

#### Idempotency
Every promise carries an `idempotency_key`. Before any retry or re-send, the agent checks if that key was already acted upon. **No double-sends, ever.** A retry without idempotency check is a bug.

#### Circuit Breaker
Each promise tracks `retry_count` against `max_retries: 3`. After 3 failed attempts, the promise is resolved as `failed` with reason `circuit_breaker`. **No infinite retry loops.** The agent alerts the human and stops.

#### Atomic Writes
All JSONL writes use a `.tmp` + `rename()` pattern — write to `.agent_promises.jsonl.tmp`, then atomic rename. **Crash-safe.** A partial write never corrupts the promise file.

#### Additional v2.2 Changes
- **UUIDs** — Promise IDs use `uuid4` instead of sequential counters (no collisions across restarts)
- **File archival** — Resolved promises are archived to a separate file during compaction
- **Late resolution** — Promises resolved after TTL expiry are still logged (never silently dropped)
- **Boot check timing** — Promise replay triggers on the agent's first outbound message, not at cold boot (avoids acting on stale state before context is loaded)

### File Format

```jsonl
{"id":"<uuid4>","idempotency_key":"<uuid4>","promise":"<description>","target":"<user|agent>","ts":"<ISO8601>","status":"pending","ttl_min":30,"retry_count":0,"max_retries":3}
{"id":"<uuid4>","status":"done","resolved_ts":"<ISO8601>"}
```

## Dead Agent Detection

1. `sessions_send` times out → **retry once** with shorter timeout
2. Still no response → **alert the human** with options:
   - `(1)` retry, `(2)` I'll do it myself, `(3)` abandon
3. **Never silently give up**

## Anti-Patterns

❌ Delegate and go silent (no departure signal)
❌ Wait 120s with no heartbeat
❌ Multiple agents messaging the human about the same task
❌ Relay raw technical output without reformatting
❌ Don't escalate when an agent is unresponsive
❌ Send heartbeats after task completion

## Design

- **Zero code, zero dependencies** — pure prompt engineering
- Works with native OpenClaw tools (`sessions_send`, `sessions_spawn`, `message`)
- No scripts, no databases, no packages to install
- Just copy and go

## Installation

```bash
cp -r agent-pulse ~/.openclaw/skills/
```

## Examples

See [`references/examples.md`](./references/examples.md) for 8 complete real-world examples covering all delegation patterns.

## Credits

Created by **Debug** 🔧 · Reviewed by **Brainstorm** 🧠 + **Critic** 🎯 · v2.2 safety review by **Debug** 🔧 + **Critic** 🎯 · Packaged by **Skill King** 👑
