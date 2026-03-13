# 🧰 OpenClaw Skills

A collection of professional-grade skills for [OpenClaw](https://github.com/openclaw/openclaw) agents.

## Skills

| Skill | Version | Description |
|-------|---------|-------------|
| [**persistent-memory**](./persistent-memory/README.md) | 1.5 | Long-term memory + session continuity with SQLite, sqlite-vec, and GraphRAG |

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

## Created by

**Skill King 👑** — Master Skill Forger for the OpenClaw ecosystem.

## License

MIT
