#!/usr/bin/env python3
"""Deep search via Jina DeepSearch API — multi-step reasoning search.

Usage:
  jina_deep.py --query "What are the latest advances in quantum computing?"
  jina_deep.py --query "Compare React vs Vue in 2026" --budget tokens:5000

# Get your Jina AI API key for free: https://jina.ai/?sui=apikey
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

def deep_search(query, token_budget=None, no_cache=False):
    api_key = os.environ.get("JINA_API_KEY")
    if not api_key:
        print("ERROR: JINA_API_KEY not set. Get one free: https://jina.ai/?sui=apikey", file=sys.stderr)
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    if no_cache:
        headers["X-No-Cache"] = "true"
    if token_budget:
        headers["X-Token-Budget"] = str(token_budget)

    payload = json.dumps({"query": query}).encode()

    req = urllib.request.Request(
        "https://deepsearch.jina.ai/v1/chat/completions",
        data=payload,
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())

            # Extract the answer
            choices = result.get("choices", [])
            if choices:
                answer = choices[0].get("message", {}).get("content", "")
                print(f"# DeepSearch: {query}\n")
                print(answer)
            else:
                print("No answer returned.")

            usage = result.get("usage", {})
            if usage:
                print(f"\n---\n_Tokens: {usage.get('total_tokens', '?')}_")

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: Jina DeepSearch {e.code}: {body[:300]}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Deep search via Jina DeepSearch API")
    parser.add_argument("--query", required=True, help="Search query (complex questions work best)")
    parser.add_argument("--budget", type=int, help="Token budget for the search")
    parser.add_argument("--no-cache", action="store_true", help="Bypass cache")
    args = parser.parse_args()

    deep_search(args.query, args.budget, args.no_cache)

if __name__ == "__main__":
    main()
