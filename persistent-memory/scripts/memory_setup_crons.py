#!/usr/bin/env python3
"""Set up the automated memory cycle — emotional journal, consciousness stream, and weekly observer.

Creates 3 cron-like entries that the agent's SKILL.md references.
Outputs a configuration snippet ready to paste into the agent's config.

Usage:
  # Show the config to add (default timezone: UTC)
  memory_setup_crons.py

  # With custom timezone
  memory_setup_crons.py --timezone Europe/Brussels

  # With custom provider
  memory_setup_crons.py --timezone Europe/Brussels --provider openrouter

  # Show the shell commands for manual cron setup
  memory_setup_crons.py --mode shell --timezone Europe/Brussels
"""

import argparse
import json
import sys

def generate_config(timezone, provider, db_path):
    """Generate OpenClaw cron configuration."""

    config = {
        "description": "Persistent Memory — Automated Cycle",
        "note": "Add these cron jobs to your OpenClaw config or run them via system cron",
        "timezone": timezone,
        "provider": provider,
        "jobs": [
            {
                "name": "memory-emotional-journal",
                "description": "End-of-day emotional journal — analyzes today's emotions and writes an intimate journal entry",
                "schedule": f"30 23 * * * {timezone}",
                "command": f"python3 scripts/memory_emotion.py --journal --provider {provider} --db {db_path}",
                "recommended_model": "gemini-2.5-flash",
                "estimated_cost": "$0.0003/run"
            },
            {
                "name": "memory-consciousness-stream",
                "description": "Morning consciousness stream — generates a narrative identity snapshot for the agent's boot",
                "schedule": f"0 7 * * * {timezone}",
                "command": f"python3 scripts/memory_consciousness.py --provider {provider} --db {db_path}",
                "recommended_model": "gemini-2.5-flash",
                "estimated_cost": "$0.0005/run"
            },
            {
                "name": "memory-weekly-observer",
                "description": "Weekly observer report — meta-analysis of patterns, dynamics, and insights",
                "schedule": f"0 11 * * 0 {timezone}",
                "command": f"python3 scripts/memory_observer.py --provider {provider} --db {db_path}",
                "recommended_model": "gemini-2.5-flash",
                "estimated_cost": "$0.001/run"
            }
        ]
    }

    return config

def print_config(config):
    """Print the recommended configuration."""
    print("=" * 60)
    print("  PERSISTENT MEMORY — Automated Cycle Setup")
    print("=" * 60)
    print()
    print(f"  Timezone: {config['timezone']}")
    print(f"  Provider: {config['provider']}")
    print()
    print("  Daily cycle:")
    print("  ┌─ 23:30  🎭 Emotional Journal (analyzes the day)")
    print("  │")
    print("  ├─ 07:00  🧠 Consciousness Stream (morning narrative)")
    print("  │")
    print("  ├─ Boot   📋 Morning Briefing (agent reads stream)")
    print("  │")
    print("  ├─ Live   📓 Session Journal (auto-capture hook)")
    print("  │")
    print("  └─ Sun    👁️  Weekly Observer (meta-analysis)")
    print()
    print("-" * 60)
    print("  OPTION 1: OpenClaw Cron (recommended)")
    print("-" * 60)
    print()
    print("  Add to your agent's config or use 'openclaw cron add':")
    print()

    for job in config["jobs"]:
        print(f"  📌 {job['name']}")
        print(f"     Schedule: {job['schedule']}")
        print(f"     Command:  {job['command']}")
        print(f"     Cost:     ~{job['estimated_cost']}")
        print()

    print("-" * 60)
    print("  OPTION 2: System cron (alternative)")
    print("-" * 60)
    print()
    print("  Add to crontab (crontab -e):")
    print()
    for job in config["jobs"]:
        # Extract just the cron expression (without timezone)
        parts = job["schedule"].split()
        cron_expr = " ".join(parts[:5])
        print(f"  # {job['description']}")
        print(f"  {cron_expr} cd /path/to/workspace && {job['command']}")
        print()

    print("-" * 60)
    print("  ENVIRONMENT VARIABLES NEEDED")
    print("-" * 60)
    print()
    provider = config["provider"]
    if provider == "google":
        print("  export GOOGLE_API_KEY=your-key")
    elif provider == "openrouter":
        print("  export OPENROUTER_API_KEY=your-key")
    else:
        print("  export OPENAI_API_KEY=your-key")
    print("  export OPENAI_API_KEY=your-key  # always needed for embeddings")
    print()
    print(f"  Estimated total cost: ~$0.05/month")
    print()
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Set up the automated memory cycle")
    parser.add_argument("--timezone", default="UTC", help="Timezone (default: UTC)")
    parser.add_argument("--provider", default="google", choices=["google", "openrouter", "openai"],
                        help="LLM provider for generation (default: google)")
    parser.add_argument("--db", default="memory.db", help="Database path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    config = generate_config(args.timezone, args.provider, args.db)

    if args.json:
        print(json.dumps(config, indent=2))
    else:
        print_config(config)

if __name__ == "__main__":
    main()
