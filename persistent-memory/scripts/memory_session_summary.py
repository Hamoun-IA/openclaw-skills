#!/usr/bin/env python3
"""Summarize the session journal into a compact snapshot.

Reads the raw message journal (JSONL), summarizes using a cheap LLM,
and writes a structured snapshot markdown file.

Supports: Google Gemini API, OpenRouter, OpenAI.

Usage:
  # Summarize with Google Gemini (default)
  memory_session_summary.py --journal .session_journal.jsonl --snapshot .session_snapshot.md

  # Use OpenRouter
  memory_session_summary.py --provider openrouter --journal .session_journal.jsonl

  # Use OpenAI
  memory_session_summary.py --provider openai --journal .session_journal.jsonl

  # Keep last N raw messages after summarizing
  memory_session_summary.py --keep-recent 10 --journal .session_journal.jsonl

Environment variables:
  GOOGLE_API_KEY      — for Google Gemini API (default provider)
  OPENROUTER_API_KEY  — for OpenRouter
  OPENAI_API_KEY      — for OpenAI
  SUMMARY_MODEL       — override model (default depends on provider)
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# Default models per provider
DEFAULT_MODELS = {
    "google": "gemini-2.5-flash-preview-04-17",
    "openrouter": "google/gemini-2.5-flash",
    "openai": "gpt-4o-mini",
}

SUMMARY_PROMPT = """You are a conversation summarizer. Given a sequence of messages between a user and an AI assistant, produce a structured summary in the EXACT format below. Write in the same language as the conversation.

# Session Snapshot

## Current Topic
[What is being discussed RIGHT NOW in the most recent messages]

## Key Decisions
[Bullet list of decisions made during this conversation]

## Important Context
[Facts, preferences, or information mentioned that matter for continuity]

## People Mentioned
[Names and their relation/role if mentioned]

## Conversation Tone
[Brief narrative description of the emotional tone — NO numbers or scales]

## Open Questions
[Anything unresolved or pending a response]

RULES:
- Be concise but complete — this summary replaces the full conversation after compaction
- Focus on what the AI agent NEEDS to continue the conversation coherently
- Preserve specific details (names, dates, numbers, decisions)
- The "Current Topic" section is THE MOST IMPORTANT — it must capture what's actively being discussed
- Write in the conversation's language (if French, write in French)"""

def read_journal(journal_path):
    """Read JSONL journal file."""
    if not os.path.exists(journal_path):
        return []

    messages = []
    with open(journal_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return messages

def format_messages_for_summary(messages):
    """Format messages into a readable conversation text."""
    lines = []
    for msg in messages:
        ts = msg.get("ts", "")
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if content:
            short_ts = ts[11:16] if len(ts) > 16 else ts  # HH:MM
            label = "User" if role == "user" else "Assistant"
            lines.append(f"[{short_ts}] {label}: {content[:500]}")
    return "\n".join(lines)

def summarize_google(conversation_text, model):
    """Call Google Gemini API directly."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": f"{SUMMARY_PROMPT}\n\n--- CONVERSATION ---\n{conversation_text}"}]}],
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.3}
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: Google API {e.code}: {body[:200]}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Google API failed: {e}", file=sys.stderr)
        sys.exit(1)

def summarize_openai_compatible(conversation_text, model, base_url, api_key, provider_name):
    """Call OpenAI-compatible API (OpenAI or OpenRouter)."""
    if not api_key:
        print(f"ERROR: API key not set for {provider_name}", file=sys.stderr)
        sys.exit(1)

    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": f"--- CONVERSATION ---\n{conversation_text}"}
        ],
        "max_tokens": 1024,
        "temperature": 0.3
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    if provider_name == "openrouter":
        headers["HTTP-Referer"] = "https://openclaw.ai"
        headers["X-Title"] = "persistent-memory"

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"ERROR: {provider_name} API {e.code}: {body[:200]}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {provider_name} API failed: {e}", file=sys.stderr)
        sys.exit(1)

def summarize(conversation_text, provider, model):
    """Route to the right provider."""
    if provider == "google":
        return summarize_google(conversation_text, model)
    elif provider == "openrouter":
        api_key = os.environ.get("OPENROUTER_API_KEY")
        return summarize_openai_compatible(
            conversation_text, model,
            "https://openrouter.ai/api/v1", api_key, "openrouter"
        )
    elif provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        return summarize_openai_compatible(
            conversation_text, model,
            "https://api.openai.com/v1", api_key, "openai"
        )
    else:
        print(f"ERROR: Unknown provider: {provider}", file=sys.stderr)
        sys.exit(1)

def run_summary(journal_path, snapshot_path, provider, model, keep_recent=5):
    """Main summarization flow."""
    messages = read_journal(journal_path)

    if len(messages) < 3:
        print("Not enough messages to summarize (need at least 3).")
        return

    # Format conversation for summarization
    conversation_text = format_messages_for_summary(messages)

    # Call LLM for summary
    print(f"Summarizing {len(messages)} messages via {provider}/{model}...")
    summary = summarize(conversation_text, provider, model)

    # Build snapshot with summary + recent raw messages
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    recent = messages[-keep_recent:] if keep_recent > 0 else []

    snapshot_lines = [
        f"<!-- Auto-generated by persistent-memory | {now} | {len(messages)} messages | {provider}/{model} -->",
        "",
        summary.strip(),
        "",
    ]

    if recent:
        snapshot_lines.append("## Recent Messages (raw)")
        for msg in recent:
            ts = msg.get("ts", "")[11:16] if len(msg.get("ts", "")) > 16 else ""
            role = "👤" if msg.get("role") == "user" else "🤖"
            content = msg.get("content", "")[:200]
            snapshot_lines.append(f"- `{ts}` {role} {content}")
        snapshot_lines.append("")

    with open(snapshot_path, "w", encoding="utf-8") as f:
        f.write("\n".join(snapshot_lines))

    # Trim journal: keep only recent messages
    if keep_recent > 0 and len(messages) > keep_recent:
        with open(journal_path, "w", encoding="utf-8") as f:
            for msg in recent:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    print(f"OK: Snapshot written to {snapshot_path}")
    print(f"    Journal trimmed to {len(recent)} recent messages")

def main():
    parser = argparse.ArgumentParser(description="Summarize session journal into snapshot")
    parser.add_argument("--journal", default=".session_journal.jsonl", help="Journal file path")
    parser.add_argument("--snapshot", default=".session_snapshot.md", help="Snapshot output path")
    parser.add_argument("--provider", default="google", choices=["google", "openrouter", "openai"],
                        help="LLM provider for summarization (default: google)")
    parser.add_argument("--model", help="Override model (default depends on provider)")
    parser.add_argument("--keep-recent", type=int, default=5, help="Keep N recent raw messages (default: 5)")
    args = parser.parse_args()

    model = args.model or os.environ.get("SUMMARY_MODEL") or DEFAULT_MODELS.get(args.provider)
    run_summary(args.journal, args.snapshot, args.provider, model, args.keep_recent)

if __name__ == "__main__":
    main()
