# Promise Tracker — Surviving Restarts

## The Problem

Agents promise "I'll get back to you" but after a restart, they forget. The human waits forever.

## The Solution: Persistent Promises

Every outbound promise is logged to a file BEFORE the action. On boot, the agent checks for unfulfilled promises.

### Promise File

Location: `~/.openclaw/workspace/.agent_promises.jsonl`

Format:
```jsonl
{"id":"p1","agent":"debug","target":"nova","action":"sessions_send","promise":"Je check avec Nova et je te reviens","status":"pending","created":"2026-03-16T23:00:00Z","timeout_minutes":10}
{"id":"p2","agent":"debug","target":"human","action":"restart","promise":"Je fais un restart et je reviens","status":"pending","created":"2026-03-16T23:05:00Z","timeout_minutes":5}
```

### Lifecycle

```
1. Agent promises something to the human
   → WRITE to .agent_promises.jsonl BEFORE acting
   
2. Action completes (sessions_send response, restart done, etc.)
   → UPDATE status to "fulfilled"
   → Send completion report to human

3. Agent restarts / reboots
   → On boot: READ .agent_promises.jsonl
   → Find status="pending" entries
   → For each: either retry or report to human

4. Promise times out (timeout_minutes exceeded)
   → Alert the human: "⚠️ J'avais promis X mais c'est resté sans réponse"
```

### Boot Check Protocol

At every agent startup (gateway:startup hook or first message):

```
1. Read .agent_promises.jsonl
2. For each pending promise:
   a. If age < timeout → retry the action
   b. If age > timeout → report to human:
      "⚠️ Avant le restart, j'avais promis: [promise]. 
       Statut: non résolu. Je relance ?"
3. Clean fulfilled promises older than 24h
```

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
