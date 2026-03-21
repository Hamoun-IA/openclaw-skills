#!/usr/bin/env python3
"""Rerank search results for better relevance via Jina Reranker API.

Usage:
  # From stdin (pipe search results)
  echo '{"query":"python web framework","documents":["Flask is...","Django is...","FastAPI is..."]}' | jina_rerank.py

  # From arguments
  jina_rerank.py --query "python web framework" --documents "Flask is lightweight" "Django is batteries-included" "FastAPI is modern"

  # Top N results only
  jina_rerank.py --query "..." --documents "..." --top 3

# Get your Jina AI API key for free: https://jina.ai/?sui=apikey
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

def rerank(query, documents, top_n=None, model="jina-reranker-v3"):
    api_key = os.environ.get("JINA_API_KEY")
    if not api_key:
        print("ERROR: JINA_API_KEY not set. Get one free: https://jina.ai/?sui=apikey", file=sys.stderr)
        sys.exit(1)

    payload = {
        "model": model,
        "query": query,
        "documents": documents,
        "return_documents": True,
    }
    if top_n:
        payload["top_n"] = top_n

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    req = urllib.request.Request(
        "https://api.jina.ai/v1/rerank",
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            results = result.get("results", [])

            if not results:
                print("No reranking results.")
                return

            print(f"=== Reranked for: '{query}' ===\n")
            for r in results:
                idx = r.get("index", "?")
                score = r.get("relevance_score", 0)
                doc = r.get("document", {})
                text = doc.get("text", "")[:200]
                bar = "█" * int(score * 20)
                print(f"  {score:.3f} {bar}")
                print(f"  [{idx}] {text}")
                print()

            usage = result.get("usage", {})
            if usage:
                print(f"---\n_Tokens: {usage.get('total_tokens', '?')}_")

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: Jina Reranker {e.code}: {body[:300]}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Rerank results via Jina Reranker API")
    parser.add_argument("--query", help="The search query")
    parser.add_argument("--documents", nargs="+", help="Documents to rerank")
    parser.add_argument("--top", type=int, help="Return top N results only")
    parser.add_argument("--model", default="jina-reranker-v3",
                        choices=["jina-reranker-v3", "jina-reranker-v2-base-multilingual", "jina-colbert-v2"],
                        help="Reranker model")
    args = parser.parse_args()

    # Try stdin if no arguments
    if not args.query and not sys.stdin.isatty():
        data = json.loads(sys.stdin.read())
        args.query = data["query"]
        args.documents = data["documents"]

    if not args.query or not args.documents:
        print("ERROR: --query and --documents required (or pipe JSON via stdin)", file=sys.stderr)
        sys.exit(1)

    rerank(args.query, args.documents, args.top, args.model)

if __name__ == "__main__":
    main()
