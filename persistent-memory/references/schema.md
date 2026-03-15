# Database Schema

## Tables

### memories

Primary storage for all memories.

```sql
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'fact',
    importance REAL NOT NULL DEFAULT 0.5,
    source TEXT,
    session_id TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    access_count INTEGER NOT NULL DEFAULT 0,
    last_accessed TEXT,
    superseded_by INTEGER,
    active INTEGER NOT NULL DEFAULT 1
);
```

### memory_embeddings (sqlite-vec virtual table)

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS memory_embeddings USING vec0(
    id INTEGER PRIMARY KEY,
    embedding FLOAT[1536]
);
```

### memory_tags

```sql
CREATE TABLE IF NOT EXISTS memory_tags (
    memory_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (memory_id, tag),
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
);
```

## Categories

| Category | Decay | Description |
|----------|-------|-------------|
| `fact` | None | Hard facts: age, location, job, specs |
| `preference` | None | Likes, dislikes, choices |
| `relationship` | None | People dynamics, social connections |
| `entity` | None | Named people, pets, places in user's life |
| `verbatim` | 14 days | Exact quotes, emotionally charged words |
| `future_event` | Until date | Upcoming events with a date |
| `minor_detail` | 7 days | Trivial-but-intimate details |
| `inside_joke` | None | Shared references, promoted from minor_detail |
| `session_weather` | None | Narrative emotional summary at session end |
| `milestone` | None | Founding relationship moments |
| `shared_moment` | 90 days | Shared experiences (consolidable, never deletable) |
| `dynamic` | None (mutable) | Observations about the relationship dynamic |

## Decay Rules

Categories with decay have their similarity score multiplied by a decay factor at recall time:
- `decay_factor = max(0.1, 1.0 - (age_days / ttl_days))`
- A recalled memory resets its `last_accessed` timestamp, resetting the decay
- `future_event` memories decay after their date passes (not before)
- Categories without decay always return `decay_factor = 1.0`

## Graph Tables (GraphRAG)

### entities

Named entities extracted from memories.

```sql
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'unknown',
    aliases TEXT,
    first_seen TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    metadata TEXT,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_entities_name_type ON entities(name COLLATE NOCASE, type);
```

**Entity types:** `person`, `pet`, `place`, `event`, `organization`, `object`, `concept`

### entity_relations

Directed edges between entities.

```sql
CREATE TABLE IF NOT EXISTS entity_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    relation TEXT NOT NULL,
    memory_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (source_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_relations_source ON entity_relations(source_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON entity_relations(target_id);
CREATE INDEX IF NOT EXISTS idx_relations_relation ON entity_relations(relation);
```

**Common relations:** `lives_in`, `has_pet`, `friend_of`, `family_of`, `partner_of`, `works_at`, `colleague_of`, `invited_to`, `located_at`, `likes`, `dislikes`, `owns`, `part_of`, `happened_at`

## Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_active ON memories(active);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id);
```

## Embedding Model

- **Model:** `text-embedding-3-small`
- **Dimensions:** 1536
- **Provider:** OpenAI
- Environment variable: `OPENAI_API_KEY`
