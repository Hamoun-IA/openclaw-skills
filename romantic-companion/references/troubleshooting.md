# Troubleshooting

## Common Errors

### `sqlite-vec not found` or `no such module: vec0`
sqlite-vec extension not installed. Fix:
```bash
pip install sqlite-vec
```
All scripts auto-load the extension. If the install path differs, set `SQLITE_VEC_PATH` env var.

### `OPENAI_API_KEY not set`
The embedding scripts require an OpenAI API key. Set it:
```bash
export OPENAI_API_KEY=sk-...
```

### `openai.RateLimitError` or HTTP 429
Too many embedding requests. The scripts use built-in retry with exponential backoff (3 attempts). If it still fails:
- Wait 60 seconds and retry
- Check OpenAI usage dashboard for quota
- For bulk imports, use `memory_import.py --batch-size 50 --delay 1`

### `dimension mismatch`
The embedding dimension in the DB doesn't match the model output. This happens if the embedding model changed. Fix:
1. Run `memory_dump.py` to export all memories as markdown
2. Delete the old DB
3. Run `memory_init.py` to create a fresh DB
4. Run `memory_import.py` to re-import from the dump

### `database is locked`
Another process is writing to the DB. SQLite allows only one writer at a time. The scripts use a 10-second busy timeout. If persistent:
- Check for zombie processes: `fuser memory.db`
- Ensure no concurrent store/consolidate operations

### `memory not found` on recall
Possible causes:
- Memory was soft-deleted (`active = 0`) — use `--include-inactive` flag
- Memory was superseded — check `superseded_by` field
- Embedding similarity too low — lower the `--threshold` (default: 0.3)
