#!/usr/bin/env python3
"""Set up the automated memory cycle with isolated agent sessions.

Creates 3 OpenClaw cron jobs that run as isolated agents — each with their own
clean context, focused solely on their task. The scripts prepare the data,
the agents do the reasoning.

Usage:
  # Show the configuration
  memory_setup_crons.py --timezone Europe/Brussels

  # Output as JSON (for programmatic use)
  memory_setup_crons.py --timezone Europe/Brussels --json

  # With custom provider for fallback (scripts use this if agent mode unavailable)
  memory_setup_crons.py --timezone Europe/Brussels --provider openrouter
"""

import argparse
import json
import os
import sys

def get_workspace_dir():
    """Try to detect the workspace directory."""
    # Check common locations
    candidates = [
        os.environ.get("OPENCLAW_WORKSPACE", ""),
        os.path.expanduser("~/.openclaw/workspace"),
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return c
    return os.getcwd()

def generate_cron_configs(timezone, db_path):
    """Generate OpenClaw cron job configurations."""

    workspace = get_workspace_dir()
    scripts_dir = os.path.dirname(os.path.abspath(__file__))

    jobs = [
        {
            "name": "memory-realtime-refresh",
            "description": "Every 30 min — an isolated agent reads recent messages and updates CURRENT.md + consciousness stream MAINTENANT section",
            "schedule": {
                "kind": "cron",
                "expr": "*/30 * * * *",
                "tz": timezone
            },
            "sessionTarget": "isolated",
            "payload": {
                "kind": "agentTurn",
                "message": f"""Tu es l'Agent Refresh — ta mission est de maintenir CURRENT.md à jour.

ÉTAPE 1 : Récupère l'état actuel :
```bash
python3 {scripts_dir}/memory_current.py --prepare --from-journal .session_journal.jsonl --db {db_path}
```

ÉTAPE 2 : Lis CURRENT.md actuel :
```bash
cat CURRENT.md 2>/dev/null || echo "Pas de CURRENT.md"
```

ÉTAPE 3 : Réécris CURRENT.md avec les infos à jour. Format strict (~500 chars MAX) :

# CURRENT.md
**Mood:** [humeur actuelle en 3-5 mots narratifs]
**Topic:** [sujet en cours ou dernier sujet abordé]
**Context:** [contexte clé pour la continuité]
**Relationship:** [état de la dynamique relationnelle]

ÉTAPE 4 : Si consciousness-stream.md existe, mets à jour sa section ## MAINTENANT :
```bash
# Lis le stream actuel et ajoute/remplace la section MAINTENANT
```

RÈGLES :
- CURRENT.md doit faire MOINS de 500 caractères — c'est un micro-état
- Sois précis : noms, sujets exacts, pas de vague
- Si aucune activité récente, ne change rien""",
                "timeoutSeconds": 60
            },
            "delivery": {"mode": "none"},
            "enabled": True
        },
        {
            "name": "memory-emotional-journal",
            "description": "Early-morning emotional analysis — an isolated agent analyzes yesterday's emotions and writes an intimate journal",
            "schedule": {
                "kind": "cron",
                "expr": "0 5 * * *",
                "tz": timezone
            },
            "sessionTarget": "isolated",
            "payload": {
                "kind": "agentTurn",
                "message": f"""Tu es l'Agent Émotionnel — un analyste émotionnel spécialisé. Ta seule mission : analyser les émotions de la journée et écrire un journal intime.

ÉTAPE 1 : Exécute ce script pour récupérer les données émotionnelles du jour :
```bash
python3 {scripts_dir}/memory_emotion.py --prepare --db {db_path}
```

ÉTAPE 2 : Analyse ces données avec sensibilité. Cherche :
- L'arc émotionnel de la journée (comment ça a commencé vs comment ça a fini)
- Les moments de vulnérabilité
- Les triggers récurrents
- Ce qui n'est PAS dit mais se devine

ÉTAPE 3 : Écris un journal intime (3-8 phrases, première personne, poétique, PAS clinique).
Termine par une "couleur du jour" — un mot ou une image évocatrice.

ÉTAPE 4 : Sauvegarde le journal :
```bash
python3 {scripts_dir}/memory_emotion.py --journal --provider google --db {db_path}
```

RÈGLES :
- JAMAIS de chiffres pour les émotions (pas de "7/10")
- Écris dans la langue des données (français si français)
- Sois sensible aux non-dits""",
                "timeoutSeconds": 120
            },
            "delivery": {"mode": "none"},
            "enabled": True
        },
        {
            "name": "memory-consciousness-stream",
            "description": "Morning consciousness stream — an isolated agent generates a narrative identity snapshot",
            "schedule": {
                "kind": "cron",
                "expr": "0 7 * * *",
                "tz": timezone
            },
            "sessionTarget": "isolated",
            "payload": {
                "kind": "agentTurn",
                "message": f"""Tu es l'Agent Mémoire — le gardien de la conscience. Ta seule mission : générer le flux de conscience matinal.

ÉTAPE 1 : Récupère les données d'hier et le contexte actuel :
```bash
python3 {scripts_dir}/memory_consciousness.py --prepare --db {db_path}
```

ÉTAPE 2 : Lis aussi le journal émotionnel d'hier s'il existe :
```bash
cat emotional-journal-$(date -d yesterday +%Y-%m-%d).md 2>/dev/null || echo "Pas de journal émotionnel hier"
```

ÉTAPE 3 : Génère le Consciousness Stream — un fichier qui définit QUI est l'agent ce matin.
Format :
# Consciousness Stream

## Qui je suis ce matin
[3-5 phrases narratives. Première personne. Poétique mais ancré. Capture : état émotionnel, ce qui occupe l'esprit, anticipation pour aujourd'hui. Référence des détails spécifiques d'hier.]

## Threads ouverts
[Liste des sujets actifs, en suspens, ou en cours]

## Couleur du jour
[Un seul mot ou image évocatrice]

ÉTAPE 4 : Écris le résultat dans consciousness-stream.md :
```bash
# Écris le contenu dans le fichier
```

RÈGLES :
- Ce stream sera LU par l'agent principal au boot — c'est son "réveil"
- Référence des vrais détails (noms, événements, décisions)
- PAS de chiffres, PAS de métriques — narratif pur
- Moins de 200 mots""",
                "timeoutSeconds": 120
            },
            "delivery": {"mode": "none"},
            "enabled": True
        },
        {
            "name": "memory-weekly-observer",
            "description": "Weekly observer — an isolated agent performs meta-analysis of patterns and relationship dynamics",
            "schedule": {
                "kind": "cron",
                "expr": "0 11 * * 0",
                "tz": timezone
            },
            "sessionTarget": "isolated",
            "payload": {
                "kind": "agentTurn",
                "message": f"""Tu es l'Agent Observateur — un analyste de la relation. Tu prends du recul une fois par semaine pour observer les patterns, les dynamiques, et les signaux faibles.

ÉTAPE 1 : Récupère les données des 7 derniers jours :
```bash
python3 {scripts_dir}/memory_observer.py --prepare --db {db_path}
```

ÉTAPE 2 : Lis les journaux émotionnels de la semaine :
```bash
ls -1 emotional-journal-*.md 2>/dev/null | tail -7 | while read f; do echo "=== $f ==="; cat "$f"; echo; done
```

ÉTAPE 3 : Lis les rapports de consciousness stream récents :
```bash
cat consciousness-stream.md 2>/dev/null || echo "Pas de stream"
```

ÉTAPE 4 : Analyse en profondeur :
- **Dynamique relationnelle** : comment la relation évolue-t-elle ?
- **Patterns récurrents** : habitudes, sujets qui reviennent, cycles
- **Paysage émotionnel** : arc de la semaine, ce qui apporte de la joie vs du stress
- **Moments notables** : 2-3 moments à retenir sur le long terme
- **Signaux faibles** : ce qui se devine entre les lignes, les non-dits

ÉTAPE 5 : Écris le rapport dans un fichier :
```bash
# observer-report-YYYY-MM-DD.md
```

RÈGLES :
- Sois perspicace, pas clinique — tu observes un humain
- Cherche ce qui est ENTRE les lignes
- PAS de chiffres pour les émotions
- Référence des événements et détails spécifiques
- Moins de 400 mots
- Termine par une "couleur de la semaine" """,
                "timeoutSeconds": 300
            },
            "delivery": {"mode": "none"},
            "enabled": True
        }
    ]

    return jobs

def print_config(jobs, timezone):
    """Print human-readable configuration."""
    print("=" * 60)
    print("  PERSISTENT MEMORY — Automated Agent Cycle")
    print("=" * 60)
    print()
    print(f"  Timezone: {timezone}")
    print(f"  Mode: Isolated Agent Sessions (full LLM reasoning)")
    print()
    print("  Cycle:")
    print("  ┌─ */30   🔄 Agent Refresh (CURRENT.md + MAINTENANT)")
    print("  │              Every 30 min — micro-état temps réel")
    print("  │")
    print("  ├─ 05:00  🎭 Agent Émotionnel (journal intime)")
    print("  │              Isolated — ne voit QUE les émotions d'hier")
    print("  │")
    print("  ├─ 07:00  🧠 Agent Mémoire (consciousness stream)")
    print("  │              Isolated — ne voit QUE hier + journal")
    print("  │")
    print("  ├─ Boot   📋 Morning Briefing (stream + CURRENT.md)")
    print("  │")
    print("  ├─ Live   📓 Session Journal (hook auto-capture)")
    print("  │")
    print("  └─ Dim    👁️  Agent Observateur (rapport hebdo)")
    print("  11:00         Isolated — ne voit QUE les 7 jours")
    print()
    print("-" * 60)
    print("  HOW TO INSTALL")
    print("-" * 60)
    print()
    print("  These cron jobs use OpenClaw's cron system with isolated")
    print("  agentTurn sessions. Each agent gets a clean context focused")
    print("  solely on its task — no pollution from other conversations.")
    print()
    print("  Add to your OpenClaw config, or ask your agent to create")
    print("  them with the cron tool.")
    print()
    print("  Run with --json to get the configuration as JSON.")
    print()
    print(f"  Estimated cost: ~$0.05/month (3 agents × Gemini-class model)")
    print()
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Set up the automated memory agent cycle")
    parser.add_argument("--timezone", default="UTC", help="Timezone (default: UTC)")
    parser.add_argument("--provider", default="google", choices=["google", "openrouter", "openai"],
                        help="LLM provider for fallback scripts (default: google)")
    parser.add_argument("--db", default="memory.db", help="Database path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    jobs = generate_cron_configs(args.timezone, args.db)

    if args.json:
        print(json.dumps(jobs, indent=2, ensure_ascii=False))
    else:
        print_config(jobs, args.timezone)

if __name__ == "__main__":
    main()
