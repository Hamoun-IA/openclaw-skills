# Migration from MEMORY.md

## Overview

Import existing MEMORY.md content into the persistent-memory database.

## Usage

```bash
scripts/memory_import.py --source MEMORY.md [--db memory.db]
```

## How It Works

1. Parse the markdown file section by section
2. Each heading becomes a context tag
3. Each bullet point or paragraph becomes a separate memory
4. Assign categories based on content analysis (keyword matching + heuristics)
5. Generate embeddings for all extracted memories
6. Store in the database with `source = 'import'`

## Supported Formats

- Standard markdown with `#` headings
- Bullet lists (`-` or `*`)
- Paragraphs under headings
- Nested lists (flattened with parent context)

## Post-Migration

After importing:
1. Run `memory_dump.py` to verify imported content
2. Run `memory_consolidate.py` to merge any duplicates
3. Optionally rename MEMORY.md to MEMORY.md.bak
4. Update agent config to remove `memory_search` / `memory_get` tool reliance
