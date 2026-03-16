# Promise Tracker — Surviving Restarts

## The Problem

Agents promise "I'll get back to you" but after a restart, they forget. The human waits forever.

## The Solution: Persistent Promises

Every outbound promise is logged to a file BEFORE the action. On boot, the agent checks for unfulfilled promises.

### Promise File

Location: `~/.openclaw/workspace/.agent_promises.jsonl`

Format:
```jsonl
{"id":"550e8400-e29b-41d4-a716-446655440000","agent":"debug","target":"nova","action":"sessions_send","promise":"Je check avec Nova et je te reviens","status":"pending","created":"2026-03-16T23:00:00Z","timeout_minutes":10,"action_started_at":null,"retry_count":0,"max_retries":3,"idempotency_key":"debug-nova-report-20260316"}
```

### Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | UUID (not sequential — avoids collision between agents) |
| `agent` | Yes | Agent that made the promise |
| `target` | Yes | Who the action is directed at |
| `action` | Yes | What type (sessions_send, restart, etc.) |
| `promise` | Yes | Human-readable description |
| `status` | Yes | pending / fulfilled / failed / expired |
| `created` | Yes | ISO timestamp |
| `timeout_minutes` | Yes | Max time before alerting human |
| `action_started_at` | No | Set when action begins (for idempotency) |
| `retry_count` | Yes | Number of retries attempted (default: 0) |
| `max_retries` | Yes | Max retries before giving up (default: 3) |
| `idempotency_key` | No | Unique key to prevent duplicate actions |

### Lifecycle

```
1. Agent promises something to the human
   → Generate UUID + idempotency_key
   → ATOMIC WRITE to .agent_promises.jsonl (write to .tmp, then rename)
   → This guarantees the promise exists even if the agent crashes mid-action

2. Action begins
   → SET action_started_at = now
   → Execute the action (sessions_send, restart, etc.)

3. Action completes
   → UPDATE status to "fulfilled"
   → Send completion report to human

4. Agent restarts / reboots
   → On boot: READ .agent_promises.jsonl
   → Find status="pending" entries
   → For each:
      a. Check idempotency_key — if target already received the action, mark fulfilled
      b. If retry_count >= max_retries → mark "failed", alert human
      c. If action_started_at is set (was mid-action) → check target status before retry
      d. Otherwise → retry, increment retry_count

5. Promise times out (timeout_minutes exceeded)
   → Alert the human: "⚠️ J'avais promis X mais c'est resté sans réponse"
   → If action completed AFTER timeout alert → send "✅ Finalement résolu: X"
```

### Safety Mechanisms

**🔴 Fix 1 — Idempotency (no double actions):**
Before retrying, check if the action already happened:
- Query the target agent: "Did you already receive [idempotency_key]?"
- If `action_started_at` is set, the action WAS sent — verify target received it before resending
- Never blindly retry a sessions_send

**🔴 Fix 2 — Circuit Breaker (no infinite loops):**
- `max_retries: 3` (default) — after 3 failed retries, mark as "failed" and alert human
- `retry_count` incremented at each attempt
- After max_retries: "🛑 Promise failed after 3 retries: [promise]. Manual action needed."
- A promise can NEVER be retried after reaching max_retries

**🔴 Fix 3 — Atomic Writes (no lost promises):**
- Write to `.agent_promises.jsonl.tmp` first
- Then `rename()` to `.agent_promises.jsonl` (atomic on all filesystems)
- If crash during write → old file intact, promise from before crash preserved
- On boot: if `.tmp` exists, it was a partial write → discard it

**🟡 Fix 4 — File Hygiene:**
- Fulfilled/failed promises older than 24h → archived to `.agent_promises_archive.jsonl`
- Archive compacted weekly (keep last 100 entries)
- Max file size check: if > 1MB → force archive

**🟡 Fix 5 — Timeout Resolution:**
- If action completes AFTER timeout alert was sent → send follow-up: "✅ Finalement résolu"
- Agent tracks `timeout_alerted: true` to know if it needs the follow-up

### Boot Check Protocol

Triggered on: first message received after restart (since gateway:startup is not available in skills).

```
1. Check for .agent_promises.jsonl.tmp → discard if exists (partial write)
2. Read .agent_promises.jsonl
3. For each pending promise:
   a. If retry_count >= max_retries → mark "failed", alert human
   b. If age > timeout AND action_started_at set → check target, then:
      - Target received → mark fulfilled
      - Target didn't receive → retry (if under max_retries)
   c. If age > timeout AND action NOT started → alert human with options
   d. If age < timeout → retry with idempotency check
4. Archive fulfilled/failed promises older than 24h
5. Report summary to human if any promises were found
```

**⚠️ Note (Debug insight):** The boot check depends on the first message — if nobody talks to the agent, promises stay pending. For critical promises, the agent should set a cron heartbeat that triggers the check every 30 min.

### Integration with Agent Pulse Levels

| Level | Promise Tracker action |
|-------|----------------------|
| 🚀 Departure | WRITE promise before sessions_send |
| ⏳ Heartbeat | Check promise age, heartbeat if approaching timeout |
| ✅ Completion | UPDATE promise to fulfilled |
| 🛑 Abort | UPDATE promise to failed, report to human |

### Restart-Specific Protocol

When an agent announces a restart:

```
1. Log promise: "restart + return"
2. List any in-flight delegations
3. Send to human: "⚡ Restart en cours. Tâches en vol: [list]. Je reprends après."
4. After restart boot:
   - Read promises
   - For each in-flight delegation: check if the target agent responded
   - Report status to human
```

### Example: Debug restarts while Nova is working

**Before restart:**
```
Debug: "⚡ Je fais un restart. Nova est en train de bosser sur le rapport — 
        je vérifie son statut dès que je reviens."
→ Write: {promise: "check nova report status", target: "nova", status: "pending"}
→ Restart
```

**After restart (boot):**
```
Debug reads .agent_promises.jsonl
→ Found: "check nova report status" (pending, 3 min old)
→ Action: sessions_send to nova: "Status du rapport ?"
→ If nova responds: relay to human
→ If nova timeout: "⚠️ Nova n'a pas répondu au rapport. Options: ..."
```

**The human sees:**
```
Before: "⚡ Restart, Nova bosse, je vérifie après"
After:  "✅ De retour ! Nova a fini le rapport : [summary]"
```

No silence. No forgotten promises.
