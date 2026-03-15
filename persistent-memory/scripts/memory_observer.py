#!/usr/bin/env python3
"""Generate a weekly observer report — meta-analysis of patterns, dynamics, and insights.

Reads the last 7 days of memories, emotions, threads, and graph data
to produce a structured weekly report.

Usage:
  memory_observer.py --db memory.db --provider google
  memory_observer.py --db memory.db --provider openrouter --output reports/
"""

import argparse
import json
import os
import sqlite3
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

DEFAULT_MODELS = {
    "google": "gemini-2.5-flash-preview-04-17",
    "openrouter": "google/gemini-2.5-flash",
    "openai": "gpt-4o-mini",
}

OBSERVER_PROMPT = """You are an observer agent performing a weekly meta-analysis of an AI companion's relationship with their user. Given 7 days of memories, emotions, and threads, produce a structured report in the EXACT format below. Write in the same language as the source data.

# Weekly Observer Report

## Relationship Dynamics
[How is the relationship evolving? Closer? Distant? New patterns?]

## Recurring Patterns
[Habits, topics, or behaviors that repeat across the week. Time-based patterns (morning person? night owl?)]

## Emotional Landscape
[Overall emotional arc of the week. What brought joy? What caused stress?]

## Notable Moments
[2-3 specific moments worth remembering long-term]

## Open Threads Status
[What progressed? What stalled? What's new?]

## Signals & Recommendations
[Subtle signals the companion agent should pay attention to. Recommendations for deeper engagement.]

## Color of the Week
[One evocative word or phrase]

RULES:
- Be insightful, not clinical — this is about understanding a human
- Look for what's BETWEEN the lines, not just what's stated
- NO numbers or scales for emotions
- Reference specific events and details
- Keep the whole report under 400 words"""

def gather_weekly_context(db_path):
    """Collect 7 days of data."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row

    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    today = now.strftime("%Y-%m-%d")
    parts = []

    # Memories
    memories = conn.execute("""
        SELECT content, category, importance, created_at FROM memories
        WHERE active = 1 AND created_at >= ? ORDER BY created_at
    """, (week_ago,)).fetchall()

    if memories:
        parts.append(f"Memories this week ({len(memories)}):")
        for m in memories:
            day = m["created_at"][:10]
            parts.append(f"  [{day}] [{m['category']}] {m['content'][:120]}")
        parts.append("")

    # Emotions
    try:
        emotions = conn.execute("""
            SELECT reaction, trigger, intensity, valence, created_at FROM emotions
            WHERE created_at >= ? ORDER BY created_at
        """, (week_ago,)).fetchall()

        if emotions:
            parts.append(f"Emotions this week ({len(emotions)}):")
            for e in emotions:
                day = e["created_at"][:10]
                parts.append(f"  [{day}] {e['reaction']} → {e['trigger']} ({e['valence']})")
            parts.append("")
    except sqlite3.OperationalError:
        pass

    # Threads
    try:
        threads = conn.execute("""
            SELECT topic, status, opened_at, resolved_at, last_mentioned FROM open_threads
            ORDER BY opened_at DESC LIMIT 15
        """).fetchall()

        if threads:
            parts.append("Threads:")
            for t in threads:
                parts.append(f"  [{t['status']}] {t['topic']} (opened: {t['opened_at'][:10]})")
            parts.append("")
    except sqlite3.OperationalError:
        pass

    # Entity graph summary
    try:
        entities = conn.execute("SELECT name, type FROM entities WHERE active = 1 LIMIT 20").fetchall()
        if entities:
            parts.append("Known entities:")
            for e in entities:
                parts.append(f"  {e['name']} [{e['type']}]")
            parts.append("")
    except sqlite3.OperationalError:
        pass

    # Stats
    stats = conn.execute("SELECT COUNT(*) as c FROM memories WHERE active = 1").fetchone()
    parts.append(f"Total active memories: {stats['c']}")

    conn.close()
    return "\n".join(parts) if parts else None

def call_llm(prompt, context, provider, model):
    full_prompt = f"{prompt}\n\n--- WEEKLY DATA ---\n{context}"

    if provider == "google":
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("ERROR: GOOGLE_API_KEY not set", file=sys.stderr)
            sys.exit(1)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.5}
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            return result["candidates"][0]["content"]["parts"][0]["text"]
    else:
        base_url = "https://openrouter.ai/api/v1" if provider == "openrouter" else "https://api.openai.com/v1"
        api_key = os.environ.get("OPENROUTER_API_KEY" if provider == "openrouter" else "OPENAI_API_KEY")
        if not api_key:
            print(f"ERROR: API key not set for {provider}", file=sys.stderr)
            sys.exit(1)
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": full_prompt}],
            "max_tokens": 1024, "temperature": 0.5
        }
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        req = urllib.request.Request(f"{base_url}/chat/completions", data=json.dumps(payload).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"]

def main():
    parser = argparse.ArgumentParser(description="Generate weekly observer report")
    parser.add_argument("--db", default="memory.db", help="Database path")
    parser.add_argument("--provider", default="google", choices=["google", "openrouter", "openai"])
    parser.add_argument("--model", help="Override model")
    parser.add_argument("--output", default=".", help="Output directory")
    args = parser.parse_args()

    model = args.model or DEFAULT_MODELS.get(args.provider)
    context = gather_weekly_context(args.db)

    if not context:
        print("No data found for the past 7 days.")
        return

    print(f"Generating weekly observer report via {args.provider}/{model}...")
    report = call_llm(OBSERVER_PROMPT, context, args.provider, model)

    os.makedirs(args.output, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_path = os.path.join(args.output, f"observer-report-{today}.md")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"<!-- Generated by persistent-memory | {today} | {args.provider}/{model} -->\n\n")
        f.write(report.strip())
        f.write("\n")

    print(f"OK: Report written to {report_path}")
    print(f"\n{report.strip()}")

if __name__ == "__main__":
    main()
