# Consolidation & Maintenance Strategies

## When to Consolidate

Run `memory_consolidate.py` when:
- Memory count exceeds 100 and hasn't been consolidated in 7+ days
- Multiple contradictory memories detected during recall
- Agent detects repeated information across recent stores

## Merge Rules

1. **Duplicate detection**: Two memories with cosine similarity ≥ 0.92 → merge
   - Keep the more detailed version
   - Combine unique tags
   - Set importance = max of both
   - Mark the less detailed one as superseded

2. **Fact updates**: Newer memory contradicts older on same topic
   - Mark old `superseded_by = new.id`, set `active = 0`
   - New memory inherits old memory's tags + links

3. **Future events past due**: `future_event` memories whose date has passed
   - If event was discussed, promote to `fact`
   - If never referenced again, deactivate

## Importance Decay

Decay is applied at **recall time** (score multiplier), not by modifying stored data:
- `minor_detail`: TTL 7 days → decay_factor drops linearly
- `verbatim`: TTL 14 days → decay_factor drops linearly
- All other categories: no decay (factor = 1.0)
- A recalled memory resets its decay clock via `last_accessed`

## Memory Hygiene

- Recommended max active memories: ~500 per agent
- Beyond 500: run consolidation with similarity threshold 0.85
- `memory_dump.py` output should be reviewed periodically
- Never hard-delete; always soft-delete (`active = 0`)

## Contradiction Resolution

When recall returns contradictory memories:
1. Present both to the user for clarification
2. Supersede the incorrect one based on user response
3. If no clarification available, prefer the most recent memory
