#!/usr/bin/env python3
"""Web search via Jina Search API — returns LLM-friendly results.

Usage:
  jina_search.py --query "best python frameworks 2026"
  jina_search.py --query "OpenClaw skills" --max-results 5
  jina_search.py --query "climate change" --include-content

# Get your Jina AI API key for free: https://jina.ai/?sui=apikey
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse

def search(query, max_results=5, include_content=False, no_cache=False, site=None):
    api_key = os.environ.get("JINA_API_KEY")
    if not api_key:
        print("ERROR: JINA_API_KEY not set. Get one free: https://jina.ai/?sui=apikey", file=sys.stderr)
        sys.exit(1)

    # Build search query
    search_query = query
    if site:
        search_query = f"site:{site} {query}"

    encoded_query = urllib.parse.quote(search_query)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    if no_cache:
        headers["X-No-Cache"] = "true"

    req = urllib.request.Request(
        f"https://s.jina.ai/{encoded_query}",
        headers=headers,
        method="GET"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            data = result.get("data", [])

            if not data:
                print(f"No results for '{query}'")
                return

            results = data[:max_results]
            print(f"=== Search: '{query}' ({len(results)} results) ===\n")

            for i, item in enumerate(results, 1):
                title = item.get("title", "No title")
                url = item.get("url", "")
                description = item.get("description", "")
                content = item.get("content", "")

                print(f"{i}. **{title}**")
                print(f"   {url}")
                if description:
                    print(f"   {description[:200]}")
                if include_content and content:
                    print(f"\n   {content[:500]}")
                print()

            usage = result.get("usage", {})
            if usage:
                print(f"---\n_Tokens: {usage.get('tokens', '?')}_")

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: Jina Search {e.code}: {body[:300]}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Web search via Jina Search API")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--max-results", type=int, default=5, help="Max results (default: 5)")
    parser.add_argument("--include-content", action="store_true", help="Include page content snippets")
    parser.add_argument("--site", help="Limit to a specific site (e.g., github.com)")
    parser.add_argument("--no-cache", action="store_true", help="Bypass cache")
    args = parser.parse_args()

    search(args.query, args.max_results, args.include_content, args.no_cache, args.site)

if __name__ == "__main__":
    main()
