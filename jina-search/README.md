# 🔍 jina-search

> Web search, reading, fact-checking & reranking via Jina AI APIs. One API key, zero pip dependencies.

**Version:** 1.0 · **Created:** March 2026

## What's inside

Five tools built on Jina AI's API suite — all accessible with a single `JINA_API_KEY`:

| Tool | What it does | Endpoint |
|------|-------------|----------|
| **Reader** | URL → clean markdown (better than raw fetch) | `r.jina.ai` |
| **Search** | Web search with LLM-ready results | `s.jina.ai` |
| **DeepSearch** | Multi-step research with reasoning | `deepsearch.jina.ai` |
| **Grounding** | Fact-check a statement against the web | `g.jina.ai` |
| **Reranker** | Sort results by relevance to a query | `api.jina.ai/v1/rerank` |

## Quick Start

```bash
# Install the skill
cp -r jina-search ~/.openclaw/skills/

# Set your API key (get one free at https://jina.ai)
# Add to agent's TOOLS.md:
#   JINA_API_KEY=jnai_xxxxxxxxxxxxx
```

That's it. No `pip install`, no dependencies — pure `urllib` under the hood.

## Usage Examples

### Reader — Clean page extraction

```
"Read this page: https://example.com/article"
"What does this page say about X?"
```

The agent calls `scripts/jina_reader.py <url>` → returns clean markdown, images stripped, main content only.

### Search — Web search

```
"Search for OpenClaw agent framework"
"Find information about Jina AI pricing"
```

Returns top results with title, URL, and content — already formatted for LLM consumption.

### DeepSearch — Multi-step research

```
"Research the current state of AI agent frameworks in 2026"
"Deep search: comparison of vector databases for RAG"
```

Performs iterative search with reasoning — follows leads, cross-references sources, synthesizes findings.

### Grounding — Fact-checking

```
"Is this true: Python 4.0 was released in 2025"
"Fact check: OpenAI acquired Anthropic"
```

Returns factuality score + supporting/contradicting evidence from the web.

### Reranker — Relevance sorting

```
"Rerank these results for relevance to my query"
```

Takes a query + list of documents, returns them sorted by semantic relevance. Used internally by other tools, also available standalone.

## When to use what

| Need | Use | Why |
|------|-----|-----|
| Read a webpage cleanly | **jina-search Reader** | Better extraction than `web_fetch`, handles JS-heavy pages |
| Quick web search | Built-in `web_search` | Faster, no API key needed |
| LLM-optimized search results | **jina-search Search** | Results pre-formatted for LLM context |
| Deep multi-step research | **jina-search DeepSearch** | Iterative reasoning, not just a single query |
| Fact-check a claim | **jina-search Grounding** | Purpose-built for verification |
| Re-order results by relevance | **jina-search Reranker** | Semantic relevance, not keyword matching |

## API & Pricing

| | Details |
|---|---------|
| **API Key** | Single `JINA_API_KEY` for all 5 tools |
| **Free tier** | 100 RPM, 100K TPM |
| **Cost** | ~$0.02 / 1M tokens |
| **Dependencies** | None — native `urllib` only |
| **Get a key** | [jina.ai](https://jina.ai) |

## Files

```
jina-search/
├── SKILL.md              # Agent instructions
├── scripts/
│   ├── jina_reader.py    # URL → markdown
│   ├── jina_search.py    # Web search
│   ├── jina_deepsearch.py # Multi-step research
│   ├── jina_grounding.py # Fact-checking
│   └── jina_reranker.py  # Relevance sorting
└── references/
    └── jina-api-ref.md   # Full API reference
```

## Created by

**Skill King 👑** — Master Skill Forger for the OpenClaw ecosystem.
