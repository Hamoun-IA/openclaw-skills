#!/usr/bin/env python3
"""Read a URL and convert to clean LLM-friendly markdown via Jina Reader API.

Usage:
  jina_read.py --url "https://example.com"
  jina_read.py --url "https://example.com" --selector "article" --format markdown
  jina_read.py --url "https://example.com" --links --images
  jina_read.py --url "https://example.com" --engine browser --timeout 30

# Get your Jina AI API key for free: https://jina.ai/?sui=apikey
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

def read_url(url, engine=None, format="markdown", selector=None, remove=None,
             links=False, images=False, timeout=None, no_cache=False, token_budget=None):
    api_key = os.environ.get("JINA_API_KEY")
    if not api_key:
        print("ERROR: JINA_API_KEY not set. Get one free: https://jina.ai/?sui=apikey", file=sys.stderr)
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    if engine:
        headers["X-Engine"] = engine
    if format:
        headers["X-Return-Format"] = format
    if selector:
        headers["X-Target-Selector"] = selector
    if remove:
        headers["X-Remove-Selector"] = remove
    if links:
        headers["X-With-Links-Summary"] = "true"
    if images:
        headers["X-With-Images-Summary"] = "true"
    if timeout:
        headers["X-Timeout"] = str(timeout)
    if no_cache:
        headers["X-No-Cache"] = "true"
    if token_budget:
        headers["X-Token-Budget"] = str(token_budget)

    payload = json.dumps({"url": url}).encode()

    req = urllib.request.Request("https://r.jina.ai/", data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            data = result.get("data", {})

            title = data.get("title", "")
            content = data.get("content", "")
            description = data.get("description", "")

            if title:
                print(f"# {title}\n")
            if description:
                print(f"> {description}\n")
            print(content)

            # Stats
            usage = result.get("usage", {})
            if usage:
                print(f"\n---\n_Tokens: {usage.get('tokens', '?')}_")

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: Jina Reader {e.code}: {body[:300]}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Read a URL via Jina Reader API")
    parser.add_argument("--url", required=True, help="URL to read")
    parser.add_argument("--engine", choices=["browser", "direct", "cf-browser-rendering"],
                        help="Rendering engine (browser for best quality, direct for speed)")
    parser.add_argument("--format", default="markdown", choices=["markdown", "html", "text", "screenshot"],
                        help="Output format (default: markdown)")
    parser.add_argument("--selector", help="CSS selector to focus on specific elements")
    parser.add_argument("--remove", help="CSS selector to remove elements (headers, footers)")
    parser.add_argument("--links", action="store_true", help="Include links summary")
    parser.add_argument("--images", action="store_true", help="Include images summary")
    parser.add_argument("--timeout", type=int, help="Max wait time in seconds")
    parser.add_argument("--no-cache", action="store_true", help="Bypass cache")
    parser.add_argument("--token-budget", type=int, help="Max tokens for response")
    args = parser.parse_args()

    read_url(args.url, args.engine, args.format, args.selector, args.remove,
             args.links, args.images, args.timeout, args.no_cache, args.token_budget)

if __name__ == "__main__":
    main()
