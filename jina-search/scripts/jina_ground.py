#!/usr/bin/env python3
"""Fact-check a statement via Jina Grounding API.

Usage:
  jina_ground.py --statement "The Eiffel Tower is 330 meters tall"
  jina_ground.py --statement "Python was created in 1995" --sites "wikipedia.org"

# Get your Jina AI API key for free: https://jina.ai/?sui=apikey
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

def ground(statement, sites=None, no_cache=False):
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

    payload = {"statement": statement}
    if sites:
        payload["sites"] = sites.split(",")

    req = urllib.request.Request(
        "https://g.jina.ai/",
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            data = result.get("data", {})

            factuality = data.get("factuality", None)
            result_text = data.get("result", "")
            references = data.get("references", [])

            emoji = "✅" if factuality else "❌" if factuality is False else "🤔"
            print(f"{emoji} **{statement}**\n")
            print(f"Factuality: {factuality}")
            if result_text:
                print(f"Analysis: {result_text}")

            if references:
                print(f"\nSources ({len(references)}):")
                for ref in references[:5]:
                    url = ref.get("url", "")
                    key = ref.get("keyQuote", "")
                    support = ref.get("isSupportive", None)
                    icon = "👍" if support else "👎" if support is False else "➡️"
                    print(f"  {icon} {url}")
                    if key:
                        print(f"     \"{key[:150]}\"")

            usage = result.get("usage", {})
            if usage:
                print(f"\n---\n_Tokens: {usage.get('tokens', '?')}_")

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: Jina Grounding {e.code}: {body[:300]}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Fact-check via Jina Grounding API")
    parser.add_argument("--statement", required=True, help="Statement to fact-check")
    parser.add_argument("--sites", help="Comma-separated sites to check against (e.g., wikipedia.org,reuters.com)")
    parser.add_argument("--no-cache", action="store_true", help="Bypass cache")
    args = parser.parse_args()

    ground(args.statement, args.sites, args.no_cache)

if __name__ == "__main__":
    main()
