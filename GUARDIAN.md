# ALIS — Guide Opérationnel du Gardien

*Ce document décrit ce qui est automatisé, ce qui reste manuel, et exactement quoi faire à chaque étape du cycle lunaire.*

---

## Vue d'ensemble

ALIS automatise les tâches d'exécution du cycle. **Une seule chose reste ta responsabilité exclusive : la décision GO / NO GO / DEFER.**

```
AUTOMATIQUE                          MANUEL (toi)
──────────────────────────────────────────────────────────────
Lundi     → collecte des signaux
Mercredi  → scoring + hypothèses
Samedi    → briefing Guardian       → Session 45 min
                                    → Remplir DECISIONS-*.json
                                    → alis validate
                                    → Valider release notes
                                    → alis release
                                    → Publier (LinkedIn/Discord/X)
```

---

## Ce qui tourne automatiquement

Trois agents macOS (`launchd`) s'exécutent en arrière-plan via ton compte Claude Max — **aucun coût API**.

| Agent | Quand | Ce qu'il fait |
|-------|-------|---------------|
| `alis-collect` | Lundi 07h00 | Surveille Fowler, Anthropic, Tessl, Kiro, EU AI Act. Écrit les signaux pertinents dans `signals/inbox/` |
| `alis-score` | Mercredi 07h00 | Score chaque signal sur 4 dimensions (/20). Les signaux ≥ 12/20 deviennent des hypothèses dans `hypotheses/pending/` |
| `alis-briefing` | Samedi 07h00 | Si la pleine lune est dans ≤ 5 jours : génère `briefings/BRIEFING-*.md` et le dépose dans ton dossier ALIS |

> **Prérequis** : ton Mac doit être allumé aux horaires indiqués. Si la machine est éteinte, launchd ne rattrape pas les exécutions manquées — lance manuellement si besoin (voir section Commandes).

---

## Le cycle complet mois par mois

### Semaine 1–3 (continu)
Rien à faire. Les agents collectent et scorent en arrière-plan.
Tu peux consulter `alis status` à tout moment pour voir où en est le cycle.

### J-3 avant la pleine lune (samedi matin)
L'agent `alis-briefing` dépose automatiquement :
```
AIAD/06_AGENTS/alis/briefings/BRIEFING-YYYY-MM-DD.md
```
Tu reçois ce fichier dans ton Google Drive.

### Jour J — La pleine lune (session de 45 min)

**1. Lire le briefing**
Ouvre `briefings/BRIEFING-YYYY-MM-DD.md`. Il contient :
- Les hypothèses classées par score (priorité haute ≥ 16, moyenne 12–15)
- La justification terrain pour chacune
- La recommandation de l'agent (GO / DEFER)
- Les signaux sous le seuil (pour information)

**2. Prendre tes décisions**
Crée le fichier `DECISIONS-YYYY-MM-DD.json` (remplace la date par celle de la pleine lune) :

```json
{
  "cycle": "2026-05-01",
  "decisions": [
    {
      "id": "HYP-2026-04-28-001",
      "decision": "GO",
      "comment": "Validé — les signaux terrain sont convergents."
    },
    {
      "id": "HYP-2026-04-28-002",
      "decision": "NO GO",
      "comment": "Trop tôt — attendre la sortie finale de l'Omnibus VII."
    },
    {
      "id": "HYP-2026-04-28-003",
      "decision": "DEFER",
      "comment": "Pertinent mais pas urgent ce cycle."
    }
  ]
}
```

Les valeurs acceptées pour `decision` : `GO`, `NO GO`, `DEFER`.

**3. Valider le cycle**
```bash
cd ~/Dev/repos/alis
alis validate DECISIONS-2026-05-01.json
```

Ce que ça fait automatiquement :
- Déplace les hypothèses dans `go/`, `nogo/`, `deferred/`
- Archive les signaux de `scored/` vers `archived/`
- Génère `IMPLEMENTATION-CYCLE-*.md` pour les GO
- Augmente le score des DEFER de +2 pour le prochain cycle

### J+1 — Implémentation
Consulte `IMPLEMENTATION-CYCLE-YYYY-MM-DD.md` pour la liste des modifications à apporter aux artefacts AIAD. L'agent peut t'aider à les rédiger — **la validation finale reste la tienne avant tout commit**.

### J+2 — Communication

**Générer les drafts :**
```bash
alis release --cycle 2026-05-01
```

Produit dans `releases/` :
- `RELEASE-2026-05-01.md` — release notes complètes
- `LINKEDIN-2026-05-01.md` — post LinkedIn (800–1200 caractères)
- `DISCORD-2026-05-01.md` — annonce Discord
- `THREAD-X-2026-05-01.md` — thread X (5–7 tweets)

> ⚠️ **Valide chaque contenu avant de publier.** L'agent rédige, toi tu autorises.

---

## Commandes à connaître

### Quotidien / Vérification
```bash
alis status          # État du cycle : signaux, hypothèses, prochaine pleine lune
```

### Lancer manuellement un agent (si Mac était éteint)
```bash
launchctl start ovh.aiad.alis-collect     # Collecte
launchctl start ovh.aiad.alis-score       # Scoring
launchctl start ovh.aiad.alis-briefing    # Briefing
```

### Voir ce qui se passe
```bash
tail -f ~/Dev/repos/alis/logs/collect-stdout.log
tail -f ~/Dev/repos/alis/logs/score-stdout.log
tail -f ~/Dev/repos/alis/logs/briefing-stdout.log
```

### Après la session Guardian
```bash
alis validate DECISIONS-YYYY-MM-DD.json  # Appliquer les décisions
alis release --cycle YYYY-MM-DD          # Générer la communication
```

### En cas de problème
```bash
launchctl list | grep aiad               # Voir l'état des 3 agents
launchctl list ovh.aiad.alis-collect     # Détail d'un agent (LastExitStatus)
```

---

## Structure des dossiers ALIS

```
AIAD/06_AGENTS/alis/
├── signals/
│   ├── inbox/        ← Signaux bruts (lundi → mercredi)
│   ├── scored/       ← Signaux analysés (mercredi → pleine lune)
│   └── archived/     ← Signaux traités (après validate)
├── hypotheses/
│   ├── pending/      ← En attente de ta décision
│   ├── go/           ← Approuvées
│   ├── nogo/         ← Rejetées (avec justification)
│   └── deferred/     ← Reportées (score +2 au prochain cycle)
├── briefings/        ← BRIEFING-*.md (généré J-3)
├── releases/         ← RELEASE, LINKEDIN, DISCORD, THREAD-X
└── templates/        ← Formats de référence (ne pas modifier)
```

---

## Dates de pleine lune 2026

| Date | J-3 (briefing) | Session Guardian |
|------|---------------|-----------------|
| 1er mai 2026 | 28 avril | 1er mai |
| 31 mai 2026 | 28 mai | 31 mai |
| 30 juin 2026 | 27 juin | 30 juin |
| 29 juillet 2026 | 26 juillet | 29 juillet |
| 28 août 2026 | 25 août | 28 août |
| 27 septembre 2026 | 24 septembre | 27 septembre |
| 26 octobre 2026 | 23 octobre | 26 octobre |
| 25 novembre 2026 | 22 novembre | 25 novembre |
| 25 décembre 2026 | 22 décembre | 25 décembre |

---

## Fichiers importants

| Fichier | Rôle |
|---------|------|
| `~/Dev/repos/alis/.env` | Clé API Anthropic (pour les commandes manuelles) |
| `~/Dev/repos/alis/routines/routine-collect.md` | Prompt de l'agent de collecte |
| `~/Dev/repos/alis/routines/routine-score.md` | Prompt de l'agent de scoring |
| `~/Dev/repos/alis/routines/routine-briefing.md` | Prompt de l'agent de briefing |
| `~/Library/LaunchAgents/ovh.aiad.alis-*.plist` | Configuration des agents macOS |

---

## Ce qu'ALIS ne fera jamais sans toi

- Modifier un artefact AIAD sans ta validation
- Décider GO / NO GO / DEFER à ta place
- Publier du contenu sur LinkedIn, Discord ou X
- Modifier les valeurs fondatrices ou la Constitution AIAD

*L'agent prépare. Le Gardien décide.*

---

*Généré le 24 avril 2026 — Projet ALIS v0.1.0*
*Dépôt : `/Users/steeve/Dev/repos/alis`*
