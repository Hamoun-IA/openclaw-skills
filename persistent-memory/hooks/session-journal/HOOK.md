---
name: session-journal
description: "Complete anti-compaction system. Captures all messages, summarizes periodically, updates CURRENT.md, and forces full save before compaction. No external plugin needed."
metadata:
  {
    "openclaw":
      {
        "emoji": "📓",
        "events": ["message:received", "message:sent", "session:compact:before"],
        "requires": { "bins": ["python3"], "config": ["workspace.dir"] },
      },
  }
---

# Session Journal Hook

Complete anti-compaction system for persistent-memory. **No Lossless Claw needed.**

Three-layer protection:
1. **Message capture** — every message logged to `.session_journal.jsonl`
2. **Periodic summarization** — every 10 messages, external LLM summarizes → `.session_snapshot.md`
3. **Compact:before save** — forced full save (summary + CURRENT.md) right before compaction

Also updates CURRENT.md every 5 messages (lightweight, no LLM).

## What It Does

1. **Captures** every inbound and outbound message to `.session_journal.jsonl`
2. **Counts** messages per session
3. **Triggers summarization** every N messages (default: 10) using a cheap external LLM
4. **Writes** a compact `.session_snapshot.md` that the agent can read after compaction

## Configuration

Set via hook config or environment variables:

```json
{
  "hooks": {
    "internal": {
      "entries": {
        "session-journal": {
          "enabled": true,
          "env": {
            "SUMMARY_INTERVAL": "10",
            "SUMMARY_PROVIDER": "google",
            "SUMMARY_MODEL": "gemini-2.5-flash-preview-04-17",
            "GOOGLE_API_KEY": "your-key"
          }
        }
      }
    }
  }
}
```

**Providers:** `google` (default), `openrouter`, `openai`

## Requirements

- Python 3.10+
- `GOOGLE_API_KEY` or `OPENROUTER_API_KEY` or `OPENAI_API_KEY`
- The `memory_session_summary.py` script from persistent-memory skill
