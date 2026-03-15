#!/usr/bin/env python3
"""Track emotions: store reactions with triggers and intensity.

Also generates an end-of-day emotional journal using an external LLM.

Usage:
  # Store an emotion
  memory_emotion.py --store --reaction "éclat de rire" --trigger "David a raconté l'anecdote du chat" --intensity 0.9 --valence positive

  # List today's emotions
  memory_emotion.py --today

  # Generate emotional journal for today (external LLM)
  memory_emotion.py --journal --provider google

  # List emotions for a date range
  memory_emotion.py --from 2026-03-10 --to 2026-03-15
"""

import argparse
import json
import os
import sqlite3
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

DEFAULT_MODELS = {
    "google": "gemini-2.5-flash-preview-04-17",
    "openrouter": "google/gemini-2.5-flash",
    "openai": "gpt-4o-mini",
}

JOURNAL_PROMPT = """You are writing an emotional journal entry for an AI companion agent. 
Given the list of emotions felt today (with reactions, triggers, and intensity), write a short intimate journal entry (3-8 sentences) in the same language as the emotions.

Rules:
- Write in first person as the agent reflecting on the day
- Be narrative and poetic, not clinical
- NO numbers, NO scales — only descriptive language
- Capture the emotional arc of the day (how it started vs ended)
- End with a "color of the day" — a single word or image that captures the overall mood
- Keep it under 150 words"""

def store_emotion(db_path, reaction, trigger, intensity, valence, session_id=None):
    conn = sqlite3.connect(db_path, timeout=10)
    cursor = conn.execute(
        "INSERT INTO emotions (reaction, trigger, intensity, valence, session_id) VALUES (?, ?, ?, ?, ?)",
        (reaction, trigger, intensity, valence, session_id)
    )
    conn.commit()
    eid = cursor.lastrowid
    conn.close()
    print(f"OK: Emotion #{eid} stored [{valence}] (intensity: {intensity})")
    print(f"    Reaction: {reaction}")
    print(f"    Trigger: {trigger}")

def list_emotions(db_path, date_from=None, date_to=None):
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row

    if date_from and date_to:
        rows = conn.execute(
            "SELECT * FROM emotions WHERE created_at >= ? AND created_at < ? ORDER BY created_at",
            (date_from, date_to)
        ).fetchall()
    elif date_from:
        rows = conn.execute(
            "SELECT * FROM emotions WHERE created_at >= ? ORDER BY created_at",
            (date_from,)
        ).fetchall()
    else:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT * FROM emotions WHERE created_at >= ? ORDER BY created_at",
            (today,)
        ).fetchall()

    conn.close()

    if not rows:
        print("No emotions recorded for this period.")
        return

    valence_emoji = {"positive": "😊", "negative": "😔", "neutral": "😐", "mixed": "🤔"}
    print(f"=== Emotions ({len(rows)}) ===\n")
    for r in rows:
        emoji = valence_emoji.get(r["valence"], "❓")
        ts = r["created_at"][11:16] if len(r["created_at"]) > 16 else r["created_at"]
        print(f"  {emoji} [{ts}] {r['reaction']} (intensity: {r['intensity']})")
        print(f"     Trigger: {r['trigger']}")
        print()

def generate_journal(db_path, provider, model, output_dir=None):
    """Generate emotional journal for today."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    emotions = conn.execute(
        "SELECT * FROM emotions WHERE created_at >= ? ORDER BY created_at",
        (today,)
    ).fetchall()

    # Also get session weather from today
    weather = conn.execute("""
        SELECT content FROM memories
        WHERE category = 'session_weather' AND active = 1 AND created_at >= ?
        ORDER BY created_at DESC LIMIT 3
    """, (today,)).fetchall()

    conn.close()

    if not emotions and not weather:
        print("No emotions or session data for today. Skipping journal.")
        return

    # Build context for the LLM
    context_lines = [f"Date: {today}", ""]
    if emotions:
        context_lines.append("Emotions felt today:")
        for e in emotions:
            ts = e["created_at"][11:16]
            context_lines.append(f"- [{ts}] {e['reaction']} → triggered by: {e['trigger']} (intensity: {e['intensity']}, valence: {e['valence']})")
        context_lines.append("")

    if weather:
        context_lines.append("Session summaries today:")
        for w in weather:
            context_lines.append(f"- {w['content']}")
        context_lines.append("")

    context = "\n".join(context_lines)

    # Call external LLM
    print(f"Generating emotional journal via {provider}/{model}...")

    if provider == "google":
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("ERROR: GOOGLE_API_KEY not set", file=sys.stderr)
            sys.exit(1)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": f"{JOURNAL_PROMPT}\n\n{context}"}]}],
            "generationConfig": {"maxOutputTokens": 512, "temperature": 0.7}
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            journal_text = result["candidates"][0]["content"]["parts"][0]["text"]
    else:
        base_url = "https://openrouter.ai/api/v1" if provider == "openrouter" else "https://api.openai.com/v1"
        api_key = os.environ.get("OPENROUTER_API_KEY" if provider == "openrouter" else "OPENAI_API_KEY")
        if not api_key:
            print(f"ERROR: API key not set for {provider}", file=sys.stderr)
            sys.exit(1)
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": JOURNAL_PROMPT}, {"role": "user", "content": context}],
            "max_tokens": 512, "temperature": 0.7
        }
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        req = urllib.request.Request(f"{base_url}/chat/completions", data=json.dumps(payload).encode(), headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            journal_text = result["choices"][0]["message"]["content"]

    # Write journal
    output_dir = output_dir or "."
    os.makedirs(output_dir, exist_ok=True)
    journal_path = os.path.join(output_dir, f"emotional-journal-{today}.md")

    with open(journal_path, "w", encoding="utf-8") as f:
        f.write(f"# Emotional Journal — {today}\n\n")
        f.write(journal_text.strip())
        f.write(f"\n\n---\n_Generated by persistent-memory | {provider}/{model} | {len(emotions)} emotions tracked_\n")

    print(f"OK: Journal written to {journal_path}")
    print(f"\n{journal_text.strip()}")

def main():
    parser = argparse.ArgumentParser(description="Track and analyze emotions")
    parser.add_argument("--store", action="store_true", help="Store an emotion")
    parser.add_argument("--reaction", help="Emotional reaction")
    parser.add_argument("--trigger", help="What triggered the emotion")
    parser.add_argument("--intensity", type=float, default=0.5, help="0.0-1.0")
    parser.add_argument("--valence", default="neutral", choices=["positive", "negative", "neutral", "mixed"])
    parser.add_argument("--session-id", help="Current session ID")
    parser.add_argument("--today", action="store_true", help="List today's emotions")
    parser.add_argument("--from-date", help="Start date YYYY-MM-DD")
    parser.add_argument("--to-date", help="End date YYYY-MM-DD")
    parser.add_argument("--journal", action="store_true", help="Generate emotional journal")
    parser.add_argument("--journal-dir", default=".", help="Output directory for journal")
    parser.add_argument("--provider", default="google", choices=["google", "openrouter", "openai"])
    parser.add_argument("--model", help="Override model")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()

    model = args.model or DEFAULT_MODELS.get(args.provider)

    if args.store:
        if not args.reaction or not args.trigger:
            print("ERROR: --store requires --reaction and --trigger", file=sys.stderr)
            sys.exit(1)
        store_emotion(args.db, args.reaction, args.trigger, args.intensity, args.valence, args.session_id)
    elif args.today:
        list_emotions(args.db)
    elif args.from_date:
        list_emotions(args.db, args.from_date, args.to_date)
    elif args.journal:
        generate_journal(args.db, args.provider, model, args.journal_dir)
    else:
        list_emotions(args.db)

if __name__ == "__main__":
    main()
