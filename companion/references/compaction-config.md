# Recommended Compaction Configuration

Optimal OpenClaw compaction settings for persistent-memory agents.

## Config

Add to your OpenClaw config (`openclaw.json` or via `openclaw config`):

```json
{
  "agents": {
    "defaults": {
      "compaction": {
        "keepRecentTokens": 20000,
        "recentTurnsPreserve": 6,
        "identifierPolicy": "strict",
        "memoryFlush": {
          "enabled": true,
          "softThresholdTokens": 15000,
          "forceFlushTranscriptBytes": "1mb",
          "prompt": "Before compaction, update CURRENT.md with the current mood, topic, and relationship state. Then store any important unsaved memories using persistent-memory scripts. End with a session_weather summary.",
          "systemPrompt": "Preserve: emotional register, current topic, relationship mode, accepted tasks, temporal context. Write to files — they survive, context does not."
        }
      }
    }
  }
}
```

## What each setting does

| Setting | Value | Purpose |
|---------|-------|---------|
| `keepRecentTokens` | 20000 | Keep ~30-40 recent messages verbatim after compaction |
| `recentTurnsPreserve` | 6 | Last 6 turns are NEVER compacted |
| `identifierPolicy` | "strict" | Preserve names, IDs, references during compaction |
| `memoryFlush.enabled` | true | Trigger a silent save turn before compaction |
| `softThresholdTokens` | 15000 | Start flush 15k tokens before the compaction threshold |
| `forceFlushTranscriptBytes` | "1mb" | Force flush if transcript exceeds 1MB |
| `prompt` | (custom) | Tell the agent WHAT to save during flush |
| `systemPrompt` | (custom) | Tell the compaction model WHAT to preserve |

## Why these values

- **20k recent tokens** = enough context for the agent to stay coherent immediately after compaction
- **6 turns preserved** = the active back-and-forth is never lost
- **15k soft threshold** = plenty of time to flush before compaction hits
- **1MB force flush** = safety net for very long sessions
- **Custom prompts** = the agent writes CURRENT.md and session_weather before compaction, and the compaction model preserves emotional/relational context

## Principle

> **Write > Think** — Files survive, context does not. When in doubt, write to disk.
