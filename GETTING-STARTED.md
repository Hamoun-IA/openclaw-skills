# 🚀 Getting Started — OpenClaw Skills Installation Guide

> You just installed OpenClaw and want to add skills? This guide walks you through everything, step by step.

## Prerequisites

Before installing any skill, make sure you have:

1. **OpenClaw installed and running** — [Installation guide](https://docs.openclaw.ai)
2. **A Telegram bot** (or other channel) connected to your agent
3. **Python 3.10+** installed on your machine
4. **API keys** (we'll set them up below)

### Check your setup

```bash
# Is OpenClaw running?
openclaw status

# Is Python available?
python3 --version

# Where is your workspace?
# Usually: ~/.openclaw/workspace/
```

## Step 1 — Choose Your Skill

| I want... | Install this |
|-----------|-------------|
| An agent that **remembers** across sessions | [persistent-memory](./persistent-memory/) |
| A **virtual friend** that feels alive | [companion](./companion/) |
| A **romantic partner** (boyfriend/girlfriend) | [romantic-companion](./romantic-companion/) |
| Better **multi-agent coordination** | [agent-pulse](./agent-pulse/) |

> **Note:** `companion` includes everything in `persistent-memory`. `romantic-companion` includes everything in both. You only need ONE of the three memory skills.

## Step 2 — Get Your API Keys

### Required keys (for all memory skills)

| Key | Where to get it | Used for |
|-----|----------------|----------|
| `OPENAI_API_KEY` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | Memory embeddings (semantic search) |
| `GOOGLE_API_KEY` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Conversation summaries + image generation |

### Optional keys

| Key | Where to get it | Used for |
|-----|----------------|----------|
| `XAI_API_KEY` | [console.x.ai](https://console.x.ai) | Alternative images (Grok) + NSFW content (romantic only) |
| `OPENROUTER_API_KEY` | [openrouter.ai/keys](https://openrouter.ai/keys) | Fallback for summaries |

### Cost estimate

| Usage | Monthly cost |
|-------|-------------|
| Memory only (no images) | ~$0.15 |
| With living presence (selfies) | ~$2-3 |
| Romantic + NSFW | ~$3-5 |

## Step 3 — Install the Skill

### Download

```bash
# Clone the repo
git clone https://github.com/Hamoun-IA/openclaw-skills.git
cd openclaw-skills
```

### Copy to your agent

**For companion (recommended for most users):**
```bash
cp -r companion ~/.openclaw/skills/
```

**For romantic-companion (⚠️ requires a dedicated agent!):**
```bash
# Create a separate agent first — DO NOT install on your main agent
openclaw agents create romantic

# Install the skill in the new agent's workspace
cp -r romantic-companion ~/.openclaw/agents/romantic/workspace/skills/

# Run the wizard from the agent's workspace
cd ~/.openclaw/agents/romantic/workspace/
python3 skills/romantic-companion/scripts/setup_wizard.py
```
> **Why?** The romantic companion has its own personality, memory, and presence. Mixing it with your main agent would cause romantic behavior in work conversations.

**For persistent-memory only:**
```bash
cp -r persistent-memory ~/.openclaw/skills/
```

**For agent-pulse (multi-agent protocol):**
```bash
cp -r agent-pulse ~/.openclaw/skills/
```

### Install Python dependencies

```bash
pip install sqlite-vec openai
```

## Step 4 — Run the Setup Wizard

For **companion** or **romantic-companion**:

```bash
cd ~/.openclaw/skills/companion/scripts/
python3 setup_wizard.py
```

The wizard guides you through everything:
- 🔑 API keys
- 🌍 Timezone
- 📸 Reference photo (for selfies)
- 📊 Message frequency
- 🌙 Quiet hours
- 💕 Romantic settings (if romantic-companion)

For **persistent-memory** (manual setup):

```bash
cd ~/.openclaw/skills/persistent-memory/scripts/
python3 memory_init.py --db memory.db
```

## Step 5 — Set Up Automated Agents (Optional but Recommended)

These agents run in the background to maintain memory, emotions, and consciousness:

```bash
python3 memory_setup_crons.py --timezone Europe/Brussels
```

This shows you how to configure 4 automated agents:

| Agent | Schedule | What it does |
|-------|----------|-------------|
| 🔄 Refresh | Every 30 min | Updates CURRENT.md (state file) |
| 🎭 Emotional | 5:00 AM | Writes emotional journal |
| 🧠 Memory | 7:00 AM | Generates consciousness stream |
| 👁️ Observer | Sunday 11:00 | Weekly patterns analysis |

## Step 6 — Install Anti-Compaction Hook (Optional)

If you DON'T have [Lossless Claw](https://github.com/Martian-Engineering/lossless-claw) installed:

```bash
cp -r ~/.openclaw/skills/companion/hooks/session-journal ~/.openclaw/hooks/
openclaw hooks enable session-journal
```

If you DO have Lossless Claw → skip this step, it handles everything.

## Step 7 — Restart OpenClaw

```bash
openclaw gateway restart
```

That's it! Your agent now has memory, emotions, and presence. Talk to it on Telegram and watch it come alive. ✨

## Troubleshooting

### "sqlite-vec not found"
```bash
pip install sqlite-vec
```

### "OPENAI_API_KEY not set"
Make sure your keys are in the `.env.persistent-memory` file (created by the wizard) or exported in your shell:
```bash
export OPENAI_API_KEY=sk-...
export GOOGLE_API_KEY=AI...
```

### "No memories found"
The database needs to be initialized first:
```bash
python3 scripts/memory_init.py --db memory.db
```

### Agent doesn't detect the skill
Make sure the skill is in the right directory:
```bash
ls ~/.openclaw/skills/companion/SKILL.md
# Should exist
```
Then restart OpenClaw: `openclaw gateway restart`

### Images not generating
Check that `GOOGLE_API_KEY` is set and the reference photo exists:
```bash
ls ~/.openclaw/skills/companion/assets/reference/face.jpg
```

## Quick Reference

| Command | What it does |
|---------|-------------|
| `python3 setup_wizard.py` | Interactive setup |
| `python3 memory_init.py --db memory.db` | Initialize database |
| `python3 memory_briefing.py --db memory.db` | Morning briefing |
| `python3 memory_dump.py --db memory.db` | Export all memories |
| `python3 memory_healthcheck.py --db memory.db` | Health check |
| `python3 test_critical.py` | Run tests (no API needed) |
| `python3 presence_engine.py --check --db memory.db` | Check presence status |
| `python3 presence_engine.py --pause` | Pause presence (8h) |
| `python3 presence_engine.py --resume` | Resume presence |

## Need Help?

- 📖 Each skill has its own README with detailed documentation
- 🐛 Issues: [github.com/Hamoun-IA/openclaw-skills/issues](https://github.com/Hamoun-IA/openclaw-skills/issues)
- 💬 OpenClaw community: [discord.com/invite/clawd](https://discord.com/invite/clawd)
