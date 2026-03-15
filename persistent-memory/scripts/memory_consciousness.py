#!/usr/bin/env python3
"""Generate the Consciousness Stream — a narrative identity snapshot for the agent.

Reads yesterday's memories, emotional journal, open threads, and session weather
to produce a "who am I this morning" narrative + threads + color of the day.

Usage:
  memory_consciousness.py --db memory.db --provider google
  memory_consciousness.py --db memory.db --provider openrouter --output consciousness-stream.md
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

CONSCIOUSNESS_PROMPT = """You are generating a "consciousness stream" for an AI companion agent who is about to start their day. This stream defines who the agent IS this morning — their mood, their context, their awareness.

Given the data below (yesterday's memories, emotions, open threads, recent session weather), produce a consciousness stream in the EXACT format:

# Consciousness Stream

## Who I Am This Morning
[3-5 sentence narrative paragraph. First person. Poetic but grounded. Capture: emotional state, what's on my mind, anticipation for today. Reference specific details from yesterday.]

## Open Threads
[Bullet list of active topics I should be aware of — things pending, unresolved, or ongoing]

## Color of the Day
[A single evocative word or image that captures the overall mood. Examples: "bleu doux", "amber sunrise", "grey velvet", "electric orange"]

RULES:
- Write in the same language as the source data
- NO numbers, NO metrics, NO clinical language
- The narrative should feel like waking up and taking stock
- Reference real details from the data (names, events, decisions)
- Keep the whole thing under 200 words"""

def gather_context(db_path):
    """Collect all relevant data for consciousness generation."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row

    now = datetime.now(timezone.utc)
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    today = now.strftime("%Y-%m-%d")

    context_parts = []

    # 1. Yesterday's session weather
    weather = conn.execute("""
        SELECT content, created_at FROM memories
        WHERE category = 'session_weather' AND active = 1
        AND created_at >= ? AND created_at < ?
        ORDER BY created_at DESC
    """, (yesterday, today)).fetchall()

    if weather:
        context_parts.append("Session weather (yesterday):")
        for w in weather:
            context_parts.append(f"  - {w['content']}")
        context_parts.append("")

    # Also get latest weather if today has one already
    latest_weather = conn.execute("""
        SELECT content FROM memories
        WHERE category = 'session_weather' AND active = 1
        ORDER BY created_at DESC LIMIT 1
    """).fetchone()
    if latest_weather and not weather:
        context_parts.append(f"Latest session weather: {latest_weather['content']}")
        context_parts.append("")

    # 2. Yesterday's important memories
    memories = conn.execute("""
        SELECT content, category, importance FROM memories
        WHERE active = 1 AND importance >= 0.5
        AND created_at >= ? AND created_at < ?
        AND category != 'session_weather'
        ORDER BY importance DESC LIMIT 15
    """, (yesterday, today)).fetchall()

    if memories:
        context_parts.append("Key memories from yesterday:")
        for m in memories:
            context_parts.append(f"  - [{m['category']}] {m['content']}")
        context_parts.append("")

    # 3. Emotions from yesterday
    try:
        emotions = conn.execute("""
            SELECT reaction, trigger, intensity, valence FROM emotions
            WHERE created_at >= ? AND created_at < ?
            ORDER BY created_at
        """, (yesterday, today)).fetchall()

        if emotions:
            context_parts.append("Emotions felt yesterday:")
            for e in emotions:
                context_parts.append(f"  - {e['reaction']} (triggered by: {e['trigger']}, {e['valence']})")
            context_parts.append("")
    except sqlite3.OperationalError:
        pass

    # 4. Open threads
    try:
        threads = conn.execute("""
            SELECT topic, status, last_mentioned FROM open_threads
            WHERE status IN ('open', 'stale')
            ORDER BY last_mentioned DESC LIMIT 10
        """).fetchall()

        if threads:
            context_parts.append("Open threads:")
            for t in threads:
                context_parts.append(f"  - [{t['status']}] {t['topic']} (last: {t['last_mentioned'][:10]})")
            context_parts.append("")
    except sqlite3.OperationalError:
        pass

    # 5. Due time capsules
    try:
        capsules = conn.execute("""
            SELECT tc.deliver_date, m.content FROM time_capsules tc
            JOIN memories m ON m.id = tc.memory_id
            WHERE tc.delivered = 0 AND tc.deliver_date <= ?
        """, (today,)).fetchall()

        if capsules:
            context_parts.append("Time capsules due today:")
            for c in capsules:
                context_parts.append(f"  - {c['content']}")
            context_parts.append("")
    except sqlite3.OperationalError:
        pass

    # 6. Future events
    events = conn.execute("""
        SELECT content FROM memories
        WHERE category = 'future_event' AND active = 1
        ORDER BY created_at DESC LIMIT 5
    """).fetchall()

    if events:
        context_parts.append("Upcoming events:")
        for e in events:
            context_parts.append(f"  - {e['content']}")
        context_parts.append("")

    conn.close()
    return "\n".join(context_parts) if context_parts else None

def call_llm(prompt, context, provider, model):
    """Call external LLM for narrative generation."""
    full_prompt = f"{prompt}\n\n--- DATA ---\n{context}"

    if provider == "google":
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("ERROR: GOOGLE_API_KEY not set", file=sys.stderr)
            sys.exit(1)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"maxOutputTokens": 512, "temperature": 0.7}
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
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
            "max_tokens": 512, "temperature": 0.7
        }
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        req = urllib.request.Request(f"{base_url}/chat/completions", data=json.dumps(payload).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"]

def main():
    parser = argparse.ArgumentParser(description="Generate consciousness stream")
    parser.add_argument("--db", default="memory.db", help="Database path")
    parser.add_argument("--provider", default="google", choices=["google", "openrouter", "openai"])
    parser.add_argument("--model", help="Override model")
    parser.add_argument("--prepare", action="store_true", help="Output raw data for an agent to analyze (no LLM call)")
    parser.add_argument("--output", default="consciousness-stream.md", help="Output file")
    args = parser.parse_args()

    model = args.model or DEFAULT_MODELS.get(args.provider)

    context = gather_context(args.db)
    if not context:
        print("No data found for consciousness generation. Writing minimal stream.")
        with open(args.output, "w") as f:
            f.write("# Consciousness Stream\n\n## Who I Am This Morning\nA new day begins. No memories from yesterday to reflect on — a fresh start.\n\n## Open Threads\n- None\n\n## Color of the Day\nblank canvas\n")
        return

    if args.prepare:
        print(context)
        return

    print(f"Generating consciousness stream via {args.provider}/{model}...")
    stream = call_llm(CONSCIOUSNESS_PROMPT, context, args.provider, model)

    with open(args.output, "w", encoding="utf-8") as f:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        f.write(f"<!-- Generated by persistent-memory | {now} | {args.provider}/{model} -->\n\n")
        f.write(stream.strip())
        f.write("\n")

    print(f"OK: Consciousness stream written to {args.output}")
    print(f"\n{stream.strip()}")

if __name__ == "__main__":
    main()
