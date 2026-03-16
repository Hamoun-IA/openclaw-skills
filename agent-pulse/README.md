# 📡 agent-pulse

> Inter-agent visibility protocol — the human never asks "what happened?"

**Version:** 2 · **Created:** March 2026

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

Created by **Debug** 🔧 · Reviewed by **Brainstorm** 🧠 + **Critic** 🎯 · Packaged by **Skill King** 👑
