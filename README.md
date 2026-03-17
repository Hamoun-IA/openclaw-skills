# 🧰 OpenClaw Skills

A collection of professional-grade skills for [OpenClaw](https://github.com/openclaw/openclaw) agents.

## Skills

| Skill | Version | Description |
|-------|---------|-------------|
| [**companion**](./companion/README.md) | 3.9 | Complete AI companion — memory, emotions, living presence, inside jokes, relationship continuity |
| [**persistent-memory**](./persistent-memory/README.md) | 3.4 | Long-term memory + emotional intelligence (standalone, without companion features) |
| [**romantic-companion**](./romantic-companion/README.md) | 1.5 | Romantic AI partner — seduction to deep bond, virtual dates, NSFW via Grok ⚠️ _dedicated agent required_ |
| [**agent-pulse**](./agent-pulse/README.md) | 2.2 | Inter-agent visibility protocol — departure signals, heartbeat, completion reports, escalation, promise tracker |

## 🚀 New here? → [Getting Started Guide](./GETTING-STARTED.md)

Step-by-step installation for beginners. From zero to a working companion in 10 minutes.

## What are Skills?

Skills are modular capabilities you can add to any OpenClaw agent. Each skill is a self-contained directory with:

- `SKILL.md` — Instructions for the agent (the "brain")
- `scripts/` — Executable Python/Bash CLIs
- `references/` — Supplementary docs loaded on demand
- `hooks/` — Optional automation hooks (if applicable)

## Installation

```bash
# Install a skill globally
cp -r persistent-memory ~/.openclaw/skills/

# Or per-agent
cp -r persistent-memory <workspace>/skills/
```

## Anti-Compaction

All memory skills include **built-in anti-compaction** via the `session-journal` hook. No external plugins required.

Three layers of protection:
1. **Message capture** — every message logged to JSONL journal
2. **Periodic summaries** — snapshot every 10 messages + CURRENT.md every 5
3. **Compact hook** — forced save just before compaction

## Created by

**Skill King 👑** — Master Skill Forger for the OpenClaw ecosystem.

## License

MIT
