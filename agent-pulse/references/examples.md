# Examples — Agent Pulse v2

## Example 1: Simple fire-and-forget (Debug → Nova)

**Human:** "Demande à Nova de valider l'architecture"

**Debug (immediately):**
```
react 👀 on message  (Debug reacts)
message: "🫡 Transmis à Nova ✨ pour validation, elle te revient."
sessions_send(sessionKey="agent:nova:main", message="David demande ta validation sur l'architecture...", timeoutSeconds=0)
```

**Nova (receives task, signals human via her own bot):**
```
message: "👀 Reçu — j'analyse l'architecture."
# ... works ...
message: "✅ Architecture validée. 2 suggestions mineures : [details]"
```

> Debug's job is done after the departure signal. Nova has her own Telegram bot → she reports directly.

---

## Example 2: Wait-and-relay with heartbeat (Debug → Critic)

Critic has NO Telegram bot → Debug must relay.

**Human:** "Fais reviewer ce plan par Critic"

**Debug:**
```
react ⚡
message: "⚡ J'envoie à Critic 🔍 pour review — je te relaye sa réponse."
sessions_send(sessionKey="agent:critic:main", message="Review ce plan: ...", timeoutSeconds=120)
```

*If Critic takes > 2 min (adaptive heartbeat for ~5 min task = 1 heartbeat):*
```
message: "⏳ Critic analyse encore — il est sur la section sécurité..."
```

*On response from Critic:*
```
message: "✅ Review de Critic terminée:
🔴 Critique : pas de rate-limiting sur l'API
🟡 Important : ajouter des logs structurés
🟢 Nice-to-have : cache Redis pour les requêtes fréquentes
Confiance : ✅ haute"
```

> Key: Debug explicitly says "je te relaye" so David knows to expect it from Debug, not Critic.

---

## Example 3: Chain delegation with designated reporter

**Human:** "Prépare le rapport du soir"

**Debug (designates Nova as final reporter):**
```
react 👀
message: "🫡 Nova ✨ prépare le rapport — elle coordonne avec Jarvis. Elle te revient directement."
sessions_send(sessionKey="agent:nova:main",
  message="Rapport du soir demandé par David. Coordonne avec Jarvis pour les stats. Tu es désigné comme reporter final. Envoie le résultat directement à David sur Telegram. Debug ne relayera PAS.",
  timeoutSeconds=0)
```

**Nova (signals human, delegates to Jarvis):**
```
message: "⚡ Rapport en cours — je récupère les données de Jarvis..."
sessions_send(sessionKey="agent:jarvis:main", message="Stats du jour stp.", timeoutSeconds=30)
```

**Nova (final — she's the designated reporter):**
```
message: "✅ Rapport du soir prêt : [summary]"
```

> Only Nova sends the completion report. Debug doesn't double-report. Jarvis doesn't message David.

---

## Example 4: Broadcast — parallel perspectives

**Human:** "Je veux l'avis de Brainstorm et Critic sur ce plan"

**Debug (owns synthesis):**
```
react ⚡
message: "⚡ Je demande l'avis de Brainstorm 🧠 ET Critic 🔍 en parallèle — je te fais la synthèse."
sessions_send(sessionKey="agent:brainstorm:main", message="Analyse ce plan: ...", timeoutSeconds=0)
sessions_send(sessionKey="agent:critic:main", message="Review ce plan: ...", timeoutSeconds=120)
```

*Heartbeat after 3 min:*
```
message: "⏳ Brainstorm a répondu ✅ — j'attends encore Critic..."
```

*Both received → synthesize:*
```
message: "✅ Synthèse des deux reviews :

🧠 Brainstorm (créatif) :
- 3 angles d'amélioration proposés

🔍 Critic (technique) :
- 🔴 1 faille de sécurité
- 🟡 2 améliorations structurelles

Point commun : les deux recommandent de simplifier le module auth."
```

> Debug owns the synthesis. ONE message to David, not 3.

---

## Example 5: Dead agent detection

**Debug sends to Jarvis, no response after retry:**
```
message: "🛑 Jarvis ne répond pas (2 tentatives). Options :
1. 🔄 Réessayer dans 5 min
2. 🤖 Je fais la tâche moi-même
3. ❌ On abandonne pour l'instant"
```

> Never silently give up. Always present options.

---

## Example 6: Abort with context

**Debug is working on a migration but discovers a blocker:**
```
message: "🛑 Migration arrêtée — la base de données cible est en read-only.
Cause : maintenance planifiée jusqu'à 14h.
Suggestion : je programme un rappel pour 14h15 et je relance."
```

> Note: The cron tool is optional for retry automation.

---

## Example 7: Relay with reformatting

**Critic sends raw technical output. Debug reformats for David:**

❌ Wrong (raw dump):
```
message: "{\"score\":7.2,\"issues\":[{\"severity\":\"high\",\"desc\":\"missing auth middleware\"}]}"
```

✅ Right (reformatted):
```
message: "✅ Review de Critic :
Score : 7.2/10
🔴 Problème critique : middleware d'authentification manquant
Action recommandée : ajouter le middleware avant le déploiement"
```

> Never dump raw — reformat for readability.

---

## Example 8: Blocked — waiting for human input

**Debug is configuring a server but needs a password:**
```
message: "✋ Configuration en pause — j'ai besoin du mot de passe root du serveur.
Dès que tu me l'envoies, je reprends."
```

> Clear signal: I'm blocked, here's why, here's what I need.
