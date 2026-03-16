#!/usr/bin/env python3
"""Memory reliability indicator — measures verbatim vs inferred ratio.

Prevents feedback loop: if most knowledge about a user is inferred (agent
guesses) rather than verbatim (user said it), the agent should switch to
listening mode instead of acting on potentially biased assumptions.

Usage:
  # Get reliability score for a topic
  memory_reliability.py --topic "David's mood" --db memory.db

  # Get overall reliability
  memory_reliability.py --overall --db memory.db

  # Get agent behavior policy based on reliability
  memory_reliability.py --policy --db memory.db

  # Prepare context for agent
  memory_reliability.py --prepare --db memory.db
"""

import argparse
import sqlite3
import sys

def get_reliability(db_path, topic=None):
    """Calculate verbatim vs inferred ratio."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row

    if topic:
        # Topic-specific — would need vector search, simplified here
        total = conn.execute(
            "SELECT COUNT(*) as c FROM memories WHERE active = 1"
        ).fetchone()["c"]
    else:
        total = conn.execute(
            "SELECT COUNT(*) as c FROM memories WHERE active = 1"
        ).fetchone()["c"]

    if total == 0:
        conn.close()
        return {"total": 0, "verbatim": 0, "inferred": 0, "ratio": 0, "policy": "listen"}

    verbatim_count = conn.execute("""
        SELECT COUNT(DISTINCT m.id) as c FROM memories m
        JOIN memory_tags t ON t.memory_id = m.id
        WHERE m.active = 1 AND (t.tag = 'founding' OR t.tag = 'user_corrected'
              OR m.category IN ('verbatim', 'milestone'))
    """).fetchone()["c"]

    inferred_count = conn.execute("""
        SELECT COUNT(DISTINCT m.id) as c FROM memories m
        JOIN memory_tags t ON t.memory_id = m.id
        WHERE m.active = 1 AND t.tag = 'inferred'
    """).fetchone()["c"]

    # Memories without explicit tags are considered "observed" (neutral)
    observed = total - verbatim_count - inferred_count

    # Reliability ratio: verbatim / (verbatim + inferred)
    # Observed memories don't count against reliability
    tagged_total = verbatim_count + inferred_count
    if tagged_total == 0:
        ratio = 0.5  # No tagged data, assume neutral
    else:
        ratio = verbatim_count / tagged_total

    conn.close()

    return {
        "total": total,
        "verbatim": verbatim_count,
        "inferred": inferred_count,
        "observed": observed,
        "ratio": round(ratio, 2),
        "policy": get_policy(ratio)
    }

def get_policy(ratio):
    """Determine agent behavior policy based on reliability ratio."""
    if ratio >= 0.7:
        return "normal"      # >70% verbatim → full behavior
    elif ratio >= 0.4:
        return "exploratory"  # 40-70% → ask open questions, verify assumptions
    else:
        return "listen"       # <40% → listen mode, zero hypotheses

POLICY_DESCRIPTIONS = {
    "normal": "Reliability HIGH (>70% verbatim). Agent can act on stored knowledge confidently. Use memories to personalize, reference past conversations, adapt tone.",
    "exploratory": "Reliability MEDIUM (40-70%). Agent should verify assumptions with open questions. Don't state inferred facts as certainties. Ask 'Is that right?' more often.",
    "listen": "Reliability LOW (<40%). Most knowledge is inferred, not confirmed. Enter LISTENING MODE: ask questions, don't assume, don't reference unconfirmed patterns. Build verbatim foundation first."
}

def show_overall(db_path):
    """Show overall reliability."""
    r = get_reliability(db_path)

    print("=== Memory Reliability ===\n")
    print(f"  Total memories: {r['total']}")
    print(f"  Verbatim (user said): {r['verbatim']}")
    print(f"  Inferred (agent guessed): {r['inferred']}")
    print(f"  Observed (neutral): {r['observed']}")
    print(f"  Reliability ratio: {r['ratio']}")
    print(f"  Policy: {r['policy'].upper()}")
    print()
    print(f"  {POLICY_DESCRIPTIONS[r['policy']]}")

def show_policy(db_path):
    """Show just the policy."""
    r = get_reliability(db_path)
    print(f"Policy: {r['policy']}")
    print(f"Ratio: {r['ratio']} ({r['verbatim']} verbatim / {r['inferred']} inferred)")
    print()
    print(POLICY_DESCRIPTIONS[r['policy']])

def prepare(db_path):
    """Output for agent consumption."""
    import json
    r = get_reliability(db_path)
    r["policy_description"] = POLICY_DESCRIPTIONS[r["policy"]]
    print(json.dumps(r, indent=2))

def main():
    parser = argparse.ArgumentParser(description="Memory reliability indicator")
    parser.add_argument("--overall", action="store_true", help="Show overall reliability")
    parser.add_argument("--policy", action="store_true", help="Show behavior policy")
    parser.add_argument("--prepare", action="store_true", help="Output for agent")
    parser.add_argument("--topic", help="Topic-specific reliability (future)")
    parser.add_argument("--db", default="memory.db", help="Database path")
    args = parser.parse_args()

    if args.policy:
        show_policy(args.db)
    elif args.prepare:
        prepare(args.db)
    elif args.overall or args.topic:
        show_overall(args.db)
    else:
        show_overall(args.db)

if __name__ == "__main__":
    main()
