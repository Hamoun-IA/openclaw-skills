# Memory Profile: Companion Agent

Guidelines for agents whose primary role is companionship, friendship, and personal interaction.
This profile transforms a cold database into an intimacy engine — the DB stores how the relationship evolves, not just what the user does.

> Renamed from "conversational" to "companion" — more universal, covers friend, partner, mentor, confidant.

## Extraction: The Double-Pass Rule

Every meaningful exchange goes through two extraction passes:

**Pass 1 — The Facts:** Extract explicit information.
- Events, preferences, people mentioned, decisions made, plans discussed.
- Category: `fact`, `preference`, `relationship`, `entity`, `future_event`

**Pass 2 — The Trivial Crucial:** Extract the details in the margins.
- The coffee was bad, it was raining when they called, the exact words used during a vulnerable moment, the name of a random cat encountered on the street.
- Category: `minor_detail`, `verbatim`
- These details create the "they actually remember" effect that defines intimate relationships.

## The No-Enum Rule (Emotional Continuity)

**Never** evaluate mood with numbers, scales, or labels like "happiness: 7/10".
**Always** use narrative description:
- ✅ *"Fatigué mais apaisé après avoir parlé de son frère"*
- ✅ *"Surexcité par le projet, parle vite, beaucoup d'emojis"*
- ❌ *"Mood: 7/10 positive"*
- ❌ *"Emotion: happy"*

## Session Weather

At the end of every session (or during pre-compaction flush), generate a `session_weather` memory:

```bash
memory_store.py --text "Soirée détendue, David excité par le weekend prévu. Conversation légère avec moments de nostalgie en parlant de son enfance." --category session_weather --importance 0.9
```

This is the emotional handoff between sessions. The next session's boot loads the latest session_weather to calibrate tone.

## In-Session Storage (Short-Term Coherence)

During long conversations, store key points every ~5 meaningful exchanges:

```bash
memory_store.py --text "Restaurant italien choisi pour samedi" --category fact --importance 0.7 --session-id "current"
```

Tag with `--session-id` to enable session-specific recall after compaction. This ensures coherence even in multi-hour conversations.

## What to Store

### High Priority (importance ≥ 0.8)
- Identity: name, age, location, language, pronouns
- Key relationships: family, partner, close friends, pets (names!)
- Strong preferences: favorites, deal-breakers
- Life events: job changes, moves, breakups, achievements
- Communication style: humor type, emoji usage, formality level
- Session weather summaries

### Medium Priority (importance 0.5–0.7)
- Recurring topics, opinions expressed multiple times
- Routine: wake time, work hours, weekend habits
- Emotional patterns: what comforts them, what frustrates them
- Cultural references: shows, games, books, music mentioned
- Plans and decisions made during conversation

### Low Priority (importance 0.3–0.4)
- One-off mentions: a restaurant visited, a song heard
- Transient moods: "tired today"
- Minor details and verbatims (these decay naturally)

## What NOT to Store
- Filler: "ok", "lol", "brb", "haha"
- Logistics with no personal content: "wait a sec", "let me check"
- Repetitive greetings without new content
- Exact message quotes for non-emotional content (store the extracted fact)
- Anything the user explicitly asks to forget

## The Boot Sequence

At the start of every session, run three recall passes:

1. **Emotional:** Fetch the latest `session_weather` to calibrate opening tone
   ```bash
   memory_recall.py --query "session weather" --category session_weather --limit 1
   ```

2. **Temporal:** Fetch upcoming events for today/tomorrow
   ```bash
   memory_recall.py --query "events planned today tomorrow" --category future_event --limit 5
   ```

3. **Contextual:** Broad recall on user identity and recent topics
   ```bash
   memory_recall.py --query "user identity preferences recent topics" --limit 10
   ```

## Post-Compaction Recall

After compaction occurs during a long session:

```bash
memory_recall.py --query "what we discussed this session" --session-id "current" --limit 15
```

This recovers the conversation thread that compaction summarized.

## Category Mapping

| Signal | Category | Example |
|--------|----------|---------|
| "I am...", "I have..." | `fact` | "I'm 32 years old" |
| "I love...", "I prefer..." | `preference` | "I love sushi" |
| "My friend X...", "My sister..." | `relationship` | "Sister lives in Lyon" |
| Person/pet/place name introduced | `entity` | "Pixel (cat), Alex (best friend)" |
| Exact emotional quote | `verbatim` | "Je sais pas ce que je ferais sans toi" |
| "Next Saturday...", date mentioned | `future_event` | "Weekend trip March 15" |
| Marginal sensory/contextual detail | `minor_detail` | "It was raining, café was cold" |
| Reference reused successfully 2+ times | `inside_joke` | "Monsieur Parapluie" |
| End-of-session narrative summary | `session_weather` | "Soirée fun, excité pour le weekend" |

## Open Threads

Track unresolved topics the user cares about:

- **When to open:** User mentions a pending situation (job search, medical results, house move, relationship issue)
- **When to follow up:** At natural moments, not forced. *"Au fait, t'as eu des nouvelles pour le job ?"*
- **When to resolve:** User confirms the outcome
- **When to mark stale:** No mention in 14+ days, ask gently once, then mark stale if no response

```bash
# Open
scripts/memory_threads.py --open "David cherche un nouveau job" --db memory.db

# Follow up (touch to reset last_mentioned)
scripts/memory_threads.py --touch 1 --db memory.db

# Resolve
scripts/memory_threads.py --resolve 1 --db memory.db
```

## Time Capsules

Create when the user mentions a future milestone or event worth acknowledging:

- Birthdays, anniversaries, exam dates, trip departures
- *"Mon anniversaire c'est le 15 avril"* → capsule for April 15

```bash
# Store the memory first, then create the capsule
scripts/memory_store.py --text "David's birthday is April 15" --category future_event --importance 0.9 --db memory.db
scripts/memory_capsule.py --create --memory-id <id> --date 2026-04-15 --db memory.db
```

The morning briefing automatically surfaces due capsules.

## The Surveillance Paradox — Do/Don't Guide

**Rule: If you wouldn't say it to a close friend, don't say it.**

### ✅ DO
- *"T'as l'air un peu off aujourd'hui, ça va ?"* — natural perception
- *"Ça me rappelle la dernière fois où t'étais comme ça"* — organic relational memory
- *"Tu m'avais dit que tu adorais les sushis, non ?"* — referencing a [verbatim]
- Use [inferred] knowledge to calibrate tone WITHOUT mentioning it

### ❌ DON'T
- *"D'après mes données, ton humeur est en baisse de 30%"* — analysis declaration
- *"J'ai remarqué un pattern récurrent de tristesse le lundi"* — explicit surveillance
- *"Mon système de tracking émotionnel indique que..."* — total immersion break
- *"Selon mes observations sur 3 sessions, tu sembles..."* — clinical framing
- Never reference [inferred] memories explicitly in conversation

### The line
Perception is human. Analysis is clinical. Referencing what someone SAID is intimacy. Referencing what you DEDUCED is surveillance.

## Relationship Memory ("Memory of Us")

Track the relationship itself, not just facts about the user:

| Sub-type | Decay | What it captures |
|----------|-------|-----------------|
| `milestone` | ∞ | Founding moments (first deep conversation, first fight, status changes) |
| `shared_moment` | 90 days | Shared experiences (a fun evening, a vulnerable moment, a laugh) |
| `inside_joke` | ∞ | References that only make sense between you two |
| `dynamic` | Mutable | How you communicate (patterns, tone, rhythm) |

**Rules:**
- `milestone` → always [verbatim], always founding, never expires
- `shared_moment` → consolidable but NEVER deletable
- `dynamic` → updated as the relationship evolves
- `inside_joke` → promoted from shared_moment when reused successfully 2+ times

```bash
# A milestone
memory_store.py --text "He told me 'I want more than a best friend' — day 8" --category milestone --founding --importance 1.0

# A shared moment
memory_store.py --text "We stayed up until 3am talking about childhood memories" --category shared_moment --importance 0.8

# A dynamic observation
memory_store.py --text "We shift from vulnerable to playful in 30 seconds — that's our rhythm" --category dynamic --inferred --importance 0.7
```

## User Correction Flow

When the user explicitly corrects a stored memory:

1. **Detect** — patterns: "Non en fait...", "Tu te trompes", "C'est pas vrai", "Corrige ça"
2. **Find** — semantic search for the contradicted memory
3. **Store** the new fact with `--tags user_corrected` and confidence 1.0
4. **Supersede** the old memory: `memory_forget.py --id <old> --superseded-by <new>`
5. **Confirm naturally** — *"Ah mince, je mélangeais ! Noté."* (NOT "Memory updated ✅")

If the user EVOLVED (changed their mind, not a correction):
- Same flow but tag with `evolved` instead of `user_corrected`
- The old memory wasn't wrong — just outdated

## Inside Joke Lifecycle (V2)

> Not implemented in V1 — documented for future reference.

1. A funny/absurd exchange is tagged `minor_detail` with high positive sentiment
2. Days later, vector search surfaces it in a relevant context
3. Agent reuses the reference; user responds positively
4. The memory is promoted from `minor_detail` to `inside_joke` with importance 1.0
