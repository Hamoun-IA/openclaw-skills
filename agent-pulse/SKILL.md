---
name: agent-pulse
description: "Inter-agent visibility protocol — the human should never have to ask 'what happened?' Use when delegating tasks between agents, coordinating multi-agent work, or sending sessions_send/sessions_spawn. Covers departure signals, adaptive heartbeat, completion reports, abort/escalation, dead agent detection, and delegation patterns (fire-and-forget, wait-and-relay, chain, broadcast, relay)."
---

# Agent Pulse v2

Eliminate the #1 frustration in multi-agent setups: **silence**. The human should NEVER have to ask "so, what happened?"

## Core Rule

Every inter-agent interaction must be **visible to the human** at 4 levels:

### Level 1 — 🚀 Departure Signal (immediate)

Before any `sessions_send` or `sessions_spawn`:

1. Reply to the human IMMEDIATELY: "Transmis à [Agent] [emoji], il te revient" (adapt language)
2. For **fire-and-forget**: use `timeoutSeconds: 0` — don't wait at all
3. For **sync wait**: use a reasonable timeout (30-120s) based on expected task duration

```
# Fire-and-forget example
message: "🫡 Transmis à Nova ✨ pour validation, elle te revient."
sessions_send(sessionKey="agent:nova:main", message="...", timeoutSeconds=0)

# Sync wait example
message: "⚡ Je demande à Critic son avis..."
sessions_send(sessionKey="agent:critic:main", message="...", timeoutSeconds=60)
```

> ⚠️ Routing: Always use `sessionKey` (e.g. `agent:nova:main`). Labels may not be set. If the target agent has a Telegram bot, instruct it to reply directly to the human. If not (e.g. Critic), YOU must relay the response.

### Level 2 — ⏳ Heartbeat (adaptive)

Send progress updates to the human based on estimated task duration:

| Estimated Duration | Heartbeat Strategy |
|---|---|
| < 2 min | No heartbeat needed |
| 2–10 min | One heartbeat at ~halfway |
| 10+ min | Every 5 minutes |

```
message(action="send", message="⏳ Nova est encore dessus — elle analyse l'architecture...")
```

Limits:
- Max 5 heartbeats per delegation. After 5 without completion → escalate (see Level 4).
- Stop heartbeats immediately when you receive a completion or abort signal.

### Level 3 — ✅ Completion Report (always)

When work is done (yours or delegated), always close the loop:

```
message(action="send", message="✅ Migration terminée — 9 modules migrés, tests OK.")
```

Confidence signal — indicate how solid the result is:
- `✅` — High confidence, verified
- `⚠️✅` — Done but uncertain / needs validation
- `🔥` — Failed or critical problem

### Level 4 — 🛑 Abort / Escalation

Signals for when things go wrong:

| Signal | Meaning |
|--------|---------|
| 🛑 | Task aborted — can't complete (explain why) |
| ✋ | Blocked — waiting for external input, can't continue |
| 🔥 | Failed — something broke |

Escalation rules:
- No 👀 within 2 minutes of `sessions_send` → retry once, then alert the human
- 5 heartbeats without completion → alert the human
- Agent returns error → 🔥 report with cause

## Emoji Reactions Protocol

| Emoji | Meaning |
|-------|---------|
| 👀 | Message seen / acknowledged |
| ⚡ | Processing / working on it |
| 🎉 | Done / completed |
| 🤔 | Need info / question pending |
| 🫡 | Forwarded to another agent |
| 🔥 | Urgent / problem detected |
| 🛑 | Aborted / can't complete |

## Delegation Patterns

### Fire-and-forget
Target has its own channel to the human. Send and forget.
```
sessions_send(sessionKey="...", message="...", timeoutSeconds=0)
```

### Wait-and-relay
Target has NO channel. You wait and relay the response.
```
sessions_send(sessionKey="...", message="...", timeoutSeconds=120)
# Then relay the response to the human
```

### Chain
A → B → C. Designate ONE final reporter. Others stay silent to the human.

### Broadcast
Parallel requests to multiple agents. ONE agent synthesizes.

### Relay
Receive result from another agent, reformat for readability, send to human.
**Never dump raw** — reformat for readability.

## Anti-Patterns

❌ Sending to an agent and going silent (no departure signal)
❌ Waiting 120s with no heartbeat
❌ Multiple agents messaging the human about the same task
❌ Relaying raw technical output without reformatting
❌ Not escalating when an agent doesn't respond
❌ Sending heartbeats after the task is complete

## Dead Agent Detection

If `sessions_send` times out or returns no response:
1. Retry once with a shorter timeout
2. If still no response → alert the human with options:
   - "🛑 [Agent] ne répond pas. Options : (1) réessayer, (2) j'essaie moi-même, (3) on abandonne"
3. Never silently give up

## Promise Tracker (Restart Survival)

The #1 broken promise in multi-agent setups: "I'll get back to you" → restart → silence forever.

### How it works

Every promise is logged to `.agent_promises.jsonl` BEFORE acting. On boot, the agent checks for unfulfilled promises.

### The protocol

**Before any promise:**
```
1. Write to .agent_promises.jsonl: {promise, target, status: "pending", timeout_minutes}
2. Send departure signal to human
3. Execute the action (sessions_send, restart, etc.)
```

**On completion:**
```
4. Update promise status to "fulfilled"
5. Send completion report
```

**On boot (after restart):**
```
6. Read .agent_promises.jsonl
7. For each pending promise:
   - Age < timeout → retry the action
   - Age > timeout → report to human: "⚠️ Before restart, I promised X. Status: unresolved. Retry?"
8. Clean fulfilled promises older than 24h
```

### Restart announcement

When an agent is about to restart:
```
message: "⚡ Restart en cours. Tâches en vol: [list]. Je reprends après."
→ Log all in-flight delegations as promises
→ On return: check each one, report status
```

### The human ALWAYS gets closure

```
Before restart: "⚡ Restart, Nova bosse sur le rapport, je vérifie après"
After restart:  "✅ De retour ! Nova a fini : [summary]"
```

No silence. No forgotten promises. See `references/promise-tracker.md` for full specification.

## See Also

See `references/examples.md` for 8 complete real-world examples covering all patterns.
