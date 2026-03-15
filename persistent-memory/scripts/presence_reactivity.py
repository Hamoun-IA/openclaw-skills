#!/usr/bin/env python3
"""Emotional Reactivity Scale — tracks user engagement and adapts behavior.

Monitors response patterns to calibrate the agent's tone and proactivity.
This is OPT-IN and configurable. Disabled during quiet hours.

Usage:
  # Log a user message (call from hook or agent)
  presence_reactivity.py --user-message --db memory.db

  # Log an agent message sent without reply
  presence_reactivity.py --agent-message --db memory.db

  # Get current reactivity state
  presence_reactivity.py --status --db memory.db

  # Prepare context for agent (engagement level + suggested tone)
  presence_reactivity.py --prepare --db memory.db
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

STATE_FILE = ".reactivity_state.json"

def load_state():
    """Load reactivity state."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "messages_sent_without_reply": 0,
        "last_user_message_at": None,
        "last_agent_message_at": None,
        "recent_response_times": [],
        "engagement_level": "medium",
    }

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def log_user_message(state):
    """User sent a message — reset counters, track response time."""
    now = datetime.now(timezone.utc).isoformat()

    # Calculate response time if we had sent a message
    if state["last_agent_message_at"]:
        try:
            agent_time = datetime.fromisoformat(state["last_agent_message_at"])
            response_seconds = (datetime.now(timezone.utc) - agent_time).total_seconds()
            state["recent_response_times"].append(response_seconds)
            # Keep last 20 response times
            state["recent_response_times"] = state["recent_response_times"][-20:]
        except (ValueError, TypeError):
            pass

    state["last_user_message_at"] = now
    state["messages_sent_without_reply"] = 0

    # Calculate engagement level
    state["engagement_level"] = calculate_engagement(state)

    save_state(state)
    print(f"OK: User message logged. Engagement: {state['engagement_level']}")

def log_agent_message(state):
    """Agent sent a proactive message — increment counter."""
    now = datetime.now(timezone.utc).isoformat()
    state["last_agent_message_at"] = now
    state["messages_sent_without_reply"] += 1
    save_state(state)
    print(f"OK: Agent message logged. Unreplied: {state['messages_sent_without_reply']}")

def calculate_engagement(state):
    """Calculate engagement level from response patterns."""
    times = state.get("recent_response_times", [])
    if not times:
        return "medium"

    avg = sum(times) / len(times)

    if avg < 120:  # < 2 min average
        return "high"
    elif avg < 600:  # < 10 min
        return "medium"
    else:
        return "low"

def get_silence_duration(state):
    """How long since last user message."""
    if not state["last_user_message_at"]:
        return None

    try:
        last = datetime.fromisoformat(state["last_user_message_at"])
        return (datetime.now(timezone.utc) - last).total_seconds()
    except (ValueError, TypeError):
        return None

def get_reactivity_suggestion(state):
    """Suggest tone adjustment based on silence and engagement."""
    silence = get_silence_duration(state)
    unreplied = state.get("messages_sent_without_reply", 0)
    engagement = state.get("engagement_level", "medium")

    if silence is None:
        return {"adjustment": "none", "reason": "No data yet"}

    minutes = silence / 60

    # Don't suggest anything if we've already sent too many unreplied
    if unreplied >= 3:
        return {
            "adjustment": "back_off",
            "reason": f"Sent {unreplied} messages without reply. Stop sending until user responds.",
            "tone": "wait patiently"
        }

    if minutes < 5:
        return {"adjustment": "none", "reason": "Normal response time"}
    elif minutes < 10:
        return {"adjustment": "slight_attention", "reason": "Slightly slow response", "tone": "a bit more attentive"}
    elif minutes < 20:
        return {"adjustment": "playful_nudge", "reason": "Getting quiet", "tone": "light playful nudge if relationship allows"}
    elif minutes < 30:
        return {"adjustment": "affectionate_passive", "reason": "Notable silence", "tone": "affectionate passive if relationship allows, otherwise neutral"}
    elif minutes < 60:
        return {"adjustment": "noticed", "reason": "Long silence", "tone": "show you noticed, keep it light"}
    else:
        return {"adjustment": "space", "reason": f"Very long silence ({minutes:.0f}min)", "tone": "give space, be available when they return"}

def status(state):
    """Print current reactivity state."""
    silence = get_silence_duration(state)
    suggestion = get_reactivity_suggestion(state)

    print("=== Reactivity State ===\n")
    print(f"  Engagement level: {state['engagement_level']}")
    print(f"  Unreplied messages: {state['messages_sent_without_reply']}")
    if silence:
        print(f"  Silence duration: {silence/60:.0f} min")
    if state["last_user_message_at"]:
        print(f"  Last user message: {state['last_user_message_at']}")
    print(f"\n  Suggestion: {suggestion['adjustment']} — {suggestion.get('reason', '')}")
    if suggestion.get("tone"):
        print(f"  Suggested tone: {suggestion['tone']}")

def prepare(state, db_path):
    """Output full context for an agent."""
    silence = get_silence_duration(state)
    suggestion = get_reactivity_suggestion(state)

    output = {
        "engagement_level": state["engagement_level"],
        "messages_sent_without_reply": state["messages_sent_without_reply"],
        "silence_minutes": round(silence / 60, 1) if silence else None,
        "avg_response_time_seconds": round(sum(state.get("recent_response_times", [])) / max(len(state.get("recent_response_times", [])), 1)),
        "suggestion": suggestion,
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(description="Emotional Reactivity Scale")
    parser.add_argument("--user-message", action="store_true", help="Log a user message")
    parser.add_argument("--agent-message", action="store_true", help="Log an agent proactive message")
    parser.add_argument("--status", action="store_true", help="Show current state")
    parser.add_argument("--prepare", action="store_true", help="Output context for agent")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()

    state = load_state()

    if args.user_message:
        log_user_message(state)
    elif args.agent_message:
        log_agent_message(state)
    elif args.status:
        status(state)
    elif args.prepare:
        prepare(state, args.db)
    else:
        status(state)

if __name__ == "__main__":
    main()
