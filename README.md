# 🧰 OpenClaw Skills

A collection of professional-grade skills for [OpenClaw](https://github.com/openclaw/openclaw) agents.

## Skills

| Skill | Version | Description |
|-------|---------|-------------|
| [**companion**](./companion/README.md) | 3.8 | Complete AI companion — memory, emotions, living presence, inside jokes, relationship continuity |
| [**persistent-memory**](./persistent-memory/README.md) | 3.4 | Long-term memory + emotional intelligence (standalone, without companion features) |

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

## Recommended Companion

For complete memory (short + long term), pair our skills with:

- **[Lossless Claw](https://github.com/Martian-Engineering/lossless-claw)** — DAG-based context engine that replaces compaction. No message is ever lost during a conversation. By [Martian Engineering](https://github.com/Martian-Engineering) (MIT License).

## Created by

**Skill King 👑** — Master Skill Forger for the OpenClaw ecosystem.

## License

MIT
