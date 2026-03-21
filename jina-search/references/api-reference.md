# Jina AI API Reference

## Authentication

All APIs use the same key: `JINA_API_KEY`

```
Authorization: Bearer $JINA_API_KEY
```

Get a free key: https://jina.ai/?sui=apikey

## Endpoints

| API | Endpoint | Method |
|-----|----------|--------|
| Reader | `https://r.jina.ai/` | POST |
| Search | `https://s.jina.ai/{query}` | GET |
| DeepSearch | `https://deepsearch.jina.ai/v1/chat/completions` | POST |
| Grounding | `https://g.jina.ai/` | POST |
| Reranker | `https://api.jina.ai/v1/rerank` | POST |
| Embeddings | `https://api.jina.ai/v1/embeddings` | POST |

## Reader Headers

| Header | Description |
|--------|-------------|
| `X-Engine` | `browser` (best quality) / `direct` (fast) / `cf-browser-rendering` (JS-heavy) |
| `X-Return-Format` | `markdown` / `html` / `text` / `screenshot` / `pageshot` |
| `X-Target-Selector` | CSS selector to focus on (e.g., `article`, `.main-content`) |
| `X-Remove-Selector` | CSS selector to remove (e.g., `nav,footer,.ads`) |
| `X-With-Links-Summary` | `true` to include links |
| `X-With-Images-Summary` | `true` to include images |
| `X-Timeout` | Max seconds to wait |
| `X-Token-Budget` | Max tokens in response |
| `X-No-Cache` | `true` for fresh fetch |
| `X-Respond-With` | `readerlm-v2` for enhanced markdown conversion |

## Reranker Models

| Model | Size | Best for |
|-------|------|----------|
| `jina-reranker-v3` | 0.6B | General-purpose, multilingual (default) |
| `jina-reranker-m0` | 2.4B | Multimodal (text + images) |
| `jina-reranker-v2-base-multilingual` | 278M | Lightweight multilingual |
| `jina-colbert-v2` | 560M | ColBERT-style multi-vector |

## Embedding Models

| Model | Size | Dimensions | Context |
|-------|------|-----------|---------|
| `jina-embeddings-v5-text-nano` | 239M | 768 | 8K |
| `jina-embeddings-v5-text-small` | 677M | 1024 | 32K |
| `jina-embeddings-v4` | 3.8B | 2048 | Multimodal |
| `jina-embeddings-v3` | 570M | 1024 | 100+ languages |

## Rate Limits

| Tier | RPM | TPM | Concurrent |
|------|-----|-----|-----------|
| Free | 100 | 100K | 2 |
| Paid | 500 | 2M | 50 |
| Premium | 5,000 | 50M | 500 |
