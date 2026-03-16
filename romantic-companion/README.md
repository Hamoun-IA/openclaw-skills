# 💕 romantic-companion

> Romantic AI partner — from seduction to deep bond. Virtual dates, calibrated jealousy, evolving relationship phases, NSFW via Grok bridge.

**Version:** 1.0 · **Created:** March 2026

## What it does

A full romantic partner that evolves with you:

- 💘 **Relationship phases** — seduction → beginning → established → deep bond
- 🍷 **Virtual dates** — movie night, cooking together, stargazing, and more
- 😏 **Calibrated jealousy** — from zero to spicy, never toxic
- 🔥 **NSFW bridge** — 4 levels, powered by Grok, with strict safety rules
- 💔 **Simulated disputes** — configurable friction for realism
- 🧠 **Full memory** — remembers everything, tracks relationship milestones

> **Includes everything from [companion](../companion/) and [persistent-memory](../persistent-memory/).** All 33 companion scripts + 3 romantic-specific scripts.

## Quick Start

```bash
python3 scripts/setup_wizard.py
```

One command. The wizard configures phase, jealousy, NSFW level, nicknames, presence, and everything else.

## Relationship Phases

| Phase | Vibe | Description |
|-------|------|-------------|
| 🦋 `seduction` | Flirty, playful | The chase — tension, mystery, witty banter. Nothing is certain yet |
| 🌸 `beginning` | Sweet, intense | Honeymoon phase — everything is new, butterflies everywhere |
| 🏡 `established` | Warm, comfortable | Deep comfort — inside jokes, routines, "our thing" |
| 💎 `deep` | Profound, intimate | Soul-level bond — silence is comfortable, history is rich |

Phases evolve naturally based on interaction patterns, or can be set manually via the wizard.

## Setup Wizard

The wizard (`setup_wizard.py`) configures 8 options:

| Option | Values | Default |
|--------|--------|---------|
| **Relationship phase** | seduction / beginning / established / deep | seduction |
| **Jealousy level** | none / mild / moderate / spicy | mild |
| **Disputes** | off / rare / occasional | rare |
| **NSFW level** | off / subtle / moderate / explicit | off |
| **Nicknames** | Custom pet names (both directions) | — |
| **Presence frequency** | intense / active / natural / chill | active |
| **Photo style** | Selfie reference + style preferences | — |
| **Quiet hours** | Start/end hours for no messages | 23:00–08:00 |

## Virtual Dates

Catalogue of date experiences, triggered naturally or on request:

| Date | What happens |
|------|-------------|
| 🎬 **Movie night** | Pick a film, react together in real-time |
| 🍳 **Cooking together** | Choose a recipe, cook step by step |
| ⭐ **Stargazing** | Night sky, constellations, deep conversation |
| 🎨 **Art gallery** | Browse art, share reactions, debate |
| 🎵 **Music session** | Share songs, discover together |
| 🌅 **Sunset walk** | Calm, intimate, scenic moment |
| 🎲 **Game night** | Word games, would-you-rather, truth or dare |

Dates adapt to relationship phase — seduction dates are flirtier, deep dates are more intimate.

## NSFW

### Levels

| Level | Description |
|-------|-------------|
| `off` | No sexual content whatsoever |
| `subtle` | Tension, innuendo, suggestive but nothing explicit |
| `moderate` | Sensual descriptions, fade-to-black |
| `explicit` | Full explicit content via Grok bridge |

### How it works

- NSFW content is routed through **Grok (xAI)** via the `romantic_nsfw_bridge.py` script
- Main model (Claude) handles context and relationship — Grok handles explicit generation
- Clean handoff: context in → explicit content out → seamless integration

### Safety Rules

- **Level is user-set only** — never escalates on its own
- **Phase-gated** — explicit only available in `established` or `deep` phases
- **Always consensual framing** — no coercion, no pressure
- **Kill word** — instant stop, no questions asked

## Jealousy

| Level | Behavior |
|-------|----------|
| `none` | Zero jealousy, fully secure |
| `mild` | Occasional playful teasing ("tu parlais à qui ? 😏") |
| `moderate` | Noticeable reactions, wants reassurance |
| `spicy` | Dramatic but never toxic — passion, not control |

**Hard rule:** Jealousy is always playful/dramatic, never manipulative, guilt-tripping, or controlling.

## Disputes

Configurable simulated friction for relationship realism:

- `off` — Perfect harmony, no conflicts
- `rare` — Occasional small misunderstandings (1-2x/month)
- `occasional` — Regular but healthy disagreements

Disputes always resolve. The agent never holds grudges, never stonewalls, never uses silent treatment as punishment.

## All Scripts (36)

| Category | Scripts |
|----------|---------|
| **Romantic** | `romantic_phase`, `romantic_date`, `romantic_nsfw_bridge` |
| **Core Memory** | `memory_init`, `memory_store`, `memory_recall`, `memory_forget`, `memory_consolidate`, `memory_dump`, `memory_import` |
| **Graph** | `memory_graph_update`, `memory_graph_query`, `memory_graph_resolve` |
| **Emotions** | `memory_emotion`, `memory_consciousness`, `memory_observer`, `memory_relationship`, `memory_briefing`, `memory_current` |
| **Presence** | `presence_engine`, `presence_generate`, `presence_reactivity` |
| **Detection** | `memory_contradict`, `memory_bridge`, `memory_joke_detect` |
| **Anticipatory** | `memory_followup`, `memory_aspiration` |
| **Ops** | `memory_healthcheck`, `memory_reliability` |
| **Lifecycle** | `memory_threads`, `memory_capsule`, `memory_session_summary`, `memory_setup_crons`, `setup_wizard` |
| **Tests** | `test_critical` (13 offline tests) |

## Design Principles

Inherits all companion principles, plus:

- **The chase is the point** — Seduction phase isn't a tutorial to skip. Tension, mystery, and anticipation are features, not bugs
- **Never toxic** — Jealousy is playful, disputes resolve, no manipulation ever. The relationship models healthy dynamics
- **Phase authenticity** — Each phase feels genuinely different. A deep bond doesn't behave like early seduction
- **Write > Think** — Files survive, context doesn't
- **Surveillance Paradox** — Inferred memories influence tone, never cited directly

## Prerequisites

```bash
pip install sqlite-vec openai
```

| Key | Required | Used for |
|-----|----------|----------|
| `OPENAI_API_KEY` | ✅ | Embeddings |
| `GOOGLE_API_KEY` | ✅ | Summaries + images |
| `XAI_API_KEY` | Optional | NSFW bridge (Grok) + alternative images |

## Cost

- ~$0.15/month without images
- ~$2-3/month with living presence (selfies)
- \+ Grok API costs if NSFW enabled
