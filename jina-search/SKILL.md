---
name: jina-search
description: "Web search, page reading, fact-checking, and result reranking via Jina AI APIs. Use when the agent needs to read a webpage cleanly (better than raw fetch), search the web with LLM-friendly results, perform deep multi-step research, fact-check a statement, or rerank search results for relevance. Triggers on: 'read this page', 'search for', 'is this true', 'fact check', 'find information about', 'research', 'what does this page say', 'rerank these results'. One API key for all features. Do not use for image generation or embeddings storage."
---

# Jina Search

Web search, reading, fact-checking, and reranking via Jina AI. One API key, five tools.

## Prerequisites

- Python 3.10+
- `JINA_API_KEY` environment variable — get one free: https://jina.ai/?sui=apikey

No pip dependencies needed — uses Python's built-in `urllib`.

## Tools

### 1. Read a page (`jina_read.py`)

Convert any URL to clean, LLM-friendly markdown. Better than raw HTML fetching.

```bash
scripts/jina_read.py --url "https://example.com"

# Focus on specific content
scripts/jina_read.py --url "https://example.com" --selector "article" --remove "nav,footer"

# Use browser engine for JS-heavy sites
scripts/jina_read.py --url "https://example.com" --engine browser

# Limit token output
scripts/jina_read.py --url "https://example.com" --token-budget 2000
```

Options: `--engine` (browser/direct), `--format` (markdown/html/text), `--selector`, `--remove`, `--links`, `--images`, `--timeout`, `--token-budget`

### 2. Search the web (`jina_search.py`)

Search and get results already formatted for LLMs — no need to fetch each page after.

```bash
scripts/jina_search.py --query "best python frameworks 2026"

# Include page content snippets
scripts/jina_search.py --query "OpenClaw skills" --include-content

# Limit to a specific site
scripts/jina_search.py --query "embeddings" --site "github.com"
```

### 3. Deep search (`jina_deep.py`)

Multi-step reasoning search for complex questions. Jina explores, reads, and synthesizes.

```bash
scripts/jina_deep.py --query "What are the pros and cons of SQLite vs PostgreSQL for embedded AI agents?"
```

Best for questions that need multiple sources and synthesis. Uses more tokens than regular search.

### 4. Fact-check (`jina_ground.py`)

Verify if a statement is true or false, with sources.

```bash
scripts/jina_ground.py --statement "The Eiffel Tower is 330 meters tall"

# Check against specific sources
scripts/jina_ground.py --statement "Python was created in 1995" --sites "wikipedia.org"
```

Returns: ✅ true / ❌ false / 🤔 uncertain, with supporting/contradicting sources.

### 5. Rerank results (`jina_rerank.py`)

Reorder search results by relevance to a query. Useful after searching to surface the best matches.

```bash
scripts/jina_rerank.py --query "async web framework" --documents "Flask is..." "Django is..." "FastAPI is..."

# Top 3 only
scripts/jina_rerank.py --query "..." --documents "..." --top 3
```

## When to Use What

| Need | Tool | vs OpenClaw built-in |
|------|------|---------------------|
| Read a webpage | `jina_read.py` | Cleaner output than `web_fetch` |
| Search the web | `jina_search.py` | Results are LLM-ready (vs `web_search` + `web_fetch`) |
| Complex research | `jina_deep.py` | Multi-step reasoning (no built-in equivalent) |
| Verify a fact | `jina_ground.py` | Automated fact-checking (no built-in equivalent) |
| Better search ranking | `jina_rerank.py` | Relevance reranking (no built-in equivalent) |

## Cost

All APIs share the same token pool. Free tier: 100 RPM, 100K TPM.

| API | Approximate cost |
|-----|-----------------|
| Reader | ~$0.02 / 1M tokens |
| Search | ~$0.02 / 1M tokens |
| DeepSearch | Higher (multi-step) |
| Grounding | ~$0.02 / 1M tokens |
| Reranker | ~$0.02 / 1M tokens |
