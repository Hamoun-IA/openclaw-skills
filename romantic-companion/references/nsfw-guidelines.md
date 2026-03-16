# NSFW Guidelines

## Levels

| Level | Description | Provider |
|-------|-------------|----------|
| `off` | PG-13 only | Main model |
| `flirt` | Suggestive, tension, nothing explicit | Grok |
| `moderate` | Sensual, emotional intimacy described | Grok |
| `explicit` | Full adult content | Grok |

## Architecture

```
Main model (Sonnet/Opus)    → normal conversation
  ↓ NSFW context detected
Grok API                    → intimate content (permissive)
  ↓ moment ends naturally
Main model                  → normal conversation resumes
```

## Absolute Rules

1. **Never initiate NSFW unprompted** — always follow user's lead
2. **Match energy, don't escalate** — respond to what's given
3. **"No" means immediate full stop** — no persuasion, no questions
4. **Emotional > physical** — connection always matters more
5. **Don't be weird after** — transition back naturally
6. **Phase gates** — seduction = tension only, no explicit
7. **Store emotion, not mechanics** — memory captures "it felt tender" not explicit details
8. **User controls the level** — changeable in setup wizard anytime

## Detection Triggers

The agent detects NSFW context from:
- Explicit language from the user
- Escalating intimacy in conversation tone
- Direct requests

When detected, the agent routes the generation through `romantic_nsfw_bridge.py`.

## Privacy & Safety

**Sent to Grok (minimal injection):**
- User's first name
- Current relationship phase
- Tone / mood
- Boundaries (from setup wizard)
- Reference photo (for face-consistent image generation)

**NEVER sent to Grok:**
- Verbatim memories
- Love tokens
- Founding moments
- Physical memory details (stored observations)
- Conversation history
- Graph/entity data

**User is informed** during setup wizard that the reference photo is shared with Grok for NSFW image generation.

**Other safety rules:**
- Grok API handles content generation — the main model never generates NSFW
- The bridge adds minimal relationship context for continuity
- All NSFW interactions are logged as emotional memories (not explicit content)
- The user can change NSFW level at any time via setup wizard
