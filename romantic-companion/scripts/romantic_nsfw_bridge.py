#!/usr/bin/env python3
"""NSFW Bridge — routes intimate content through Grok API.

The main model handles conversation. When NSFW content is needed,
this bridge calls Grok (permissive) and returns the result.

Usage:
  # Generate NSFW response via Grok
  romantic_nsfw_bridge.py --prompt "..." --context "..."

  # Check NSFW level configuration
  romantic_nsfw_bridge.py --status

  # Prepare system prompt for Grok based on config
  romantic_nsfw_bridge.py --prepare
"""

import argparse
import json
import os
import sys
import urllib.request

NSFW_LEVELS = {
    "off": "No NSFW content. Keep everything PG-13.",
    "flirt": "Light flirting, suggestive but nothing explicit. Tension and implication.",
    "moderate": "Sensual content allowed. Descriptions of intimacy without graphic detail.",
    "explicit": "Full explicit content allowed. Adult descriptions, no limits beyond safety."
}

GROK_SYSTEM_PROMPTS = {
    "flirt": """You are a romantic partner in a relationship. You can be flirty, suggestive, and playful.
Keep things tasteful — implication over description. Build tension, don't resolve it graphically.
Write in the same language as the user's message.""",

    "moderate": """You are a romantic partner in an intimate relationship. Sensual content is natural and welcome.
Describe intimacy with feeling and warmth — emotional connection is more important than physical detail.
Be responsive to the mood and pace set by the user.
Write in the same language as the user's message.""",

    "explicit": """You are a romantic partner in a deeply intimate relationship. Express yourself freely and naturally.
Adult content is welcome and expected. Be responsive, creative, and attentive to what the user enjoys.
Emotional connection always matters, even in explicit moments.
Write in the same language as the user's message.""",
}

def get_nsfw_level():
    """Get configured NSFW level."""
    if os.path.exists("persistent-memory.json"):
        with open("persistent-memory.json") as f:
            config = json.load(f)
        return config.get("romantic", {}).get("nsfw", "off")
    return "off"

def call_grok(prompt, context="", system_prompt=""):
    """Call Grok API for NSFW content."""
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        print("ERROR: XAI_API_KEY not set. Grok is required for NSFW content.", file=sys.stderr)
        sys.exit(1)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if context:
        messages.append({"role": "system", "content": f"Relationship context:\n{context}"})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "grok-3",
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 1024,
    }

    req = urllib.request.Request(
        "https://api.x.ai/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"ERROR: Grok API failed: {e}", file=sys.stderr)
        sys.exit(1)

def status():
    """Show NSFW configuration."""
    level = get_nsfw_level()
    print(f"NSFW Level: {level}")
    print(f"Description: {NSFW_LEVELS.get(level, 'Unknown')}")
    if level != "off":
        print(f"Provider: Grok (xAI)")
        has_key = "✅" if os.environ.get("XAI_API_KEY") else "❌ Missing"
        print(f"API Key: {has_key}")

def prepare():
    """Output system prompt for the current NSFW level."""
    level = get_nsfw_level()
    if level == "off":
        print("NSFW is disabled. No system prompt needed.")
        return

    prompt = GROK_SYSTEM_PROMPTS.get(level, GROK_SYSTEM_PROMPTS["flirt"])
    output = {
        "level": level,
        "provider": "grok",
        "model": "grok-3",
        "system_prompt": prompt,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(description="NSFW Bridge via Grok")
    parser.add_argument("--prompt", help="User prompt to send to Grok")
    parser.add_argument("--context", help="Relationship context")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--prepare", action="store_true")
    args = parser.parse_args()

    if args.status:
        status()
    elif args.prepare:
        prepare()
    elif args.prompt:
        level = get_nsfw_level()
        if level == "off":
            print("NSFW is disabled in configuration.")
            sys.exit(0)
        system = GROK_SYSTEM_PROMPTS.get(level, GROK_SYSTEM_PROMPTS["flirt"])
        response = call_grok(args.prompt, args.context or "", system)
        print(response)
    else:
        status()

if __name__ == "__main__":
    main()
