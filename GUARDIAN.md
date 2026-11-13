# ALIS — Guide Opérationnel du Gardien

*Ce qui est automatisé, ce qui te reste, et quoi faire quand quelque chose bloque.*
*Mis à jour le 11 novembre 2026 : cycle entièrement automatisé, cadence fixe de 28 jours.*

---

## Vue d'ensemble

Depuis le 11 novembre 2026, le cycle tourne sans toi de bout en bout. Tu as fixé la règle ; l'outillage l'applique.

```
AUTOMATIQUE                                     TOI (facultatif)
────────────────────────────────────────────────────────────────────────
Lundi (hebdo)     collecte des signaux
Mercredi (hebdo)  scoring + hypothèses
Samedi J-2        briefing de préavis          → infirmer / forcer une décision
Lundi du cycle    décision (règle > 14/20)       (decisions/OVERRIDES-<cycle>.json)
  08h30           implémentation du corpus
                  publication de la doctrine
                  brouillons de communication   → publier LinkedIn / Discord / X
                  site aiad.ovh mis à jour
                  aiad-sdd publié sur npm
                  rapport de cycle + notification
```

Le cycle revient **tous les 28 jours**, toujours un lundi : 23 novembre 2026, 21 décembre 2026, 18 janvier 2027…

---

## La règle de décision

Tu l'as adoptée le 11 novembre 2026. Elle est codée dans `src/alis/commands/decide.py` et testée dans `tests/test_decide.py`.

| Cas | Décision |
|-----|----------|
| Tu as déposé une décision explicite (`OVERRIDES`) | appliquée telle quelle, dans les deux sens |
| L'hypothèse touche la Constitution ou les valeurs fondatrices | **retenue** : jamais décidée automatiquement |
| Score **strictement supérieur à 14/20** | **GO** |
| Score ≤ 14/20, premier passage | DEFER (sans bonus de +2) |
| Score ≤ 14/20, déjà reportée | NO GO par péremption |

Le seuil se règle par `ALIS_AUTO_GO_ABOVE` dans `.env` (défaut : 14).

### Infirmer ou forcer une décision

Avant le jour du cycle, crée dans le Drive `06_AGENTS/alis/decisions/OVERRIDES-<date du cycle>.json` :

```json
{
  "decisions": [
    {"id": "HYP-2026-11-11-002", "decision": "NO GO", "comment": "Trop tôt."},
    {"id": "HYP-2026-10-14-002", "decision": "GO", "comment": "Je la veux dans ce cycle."}
  ]
}
```

Valeurs acceptées : `GO`, `NO GO`, `DEFER`. C'est aussi le seul moyen de faire avancer une hypothèse retenue.

Pour voir ce que la règle déciderait aujourd'hui, sans rien écrire :

```bash
cd ~/Dev/repos/alis && bin/alis-cycle --dry-run
```

---

## Ce qui tourne

Quatre agents macOS (`launchd`), via ton compte Claude Max.

| Agent | Quand | Ce qu'il fait |
|-------|-------|---------------|
| `ovh.aiad.alis-collect` | Lundi 07h00 | Collecte les signaux dans `signals/inbox/` |
| `ovh.aiad.alis-score` | Mercredi 07h00 | Score les signaux ; ≥ 12/20 → hypothèse dans `hypotheses/pending/` |
| `ovh.aiad.alis-briefing` | Samedi 07h00 | À 5 jours ou moins du cycle : briefing de préavis dans `briefings/` |
| `ovh.aiad.alis-cycle` | Tous les jours 08h30 | Ne fait rien tant que le cycle n'est pas dû ; le jour venu, déroule tout le cycle |

Le passage quotidien d'`alis-cycle` sert de rattrapage : si le Mac était éteint le lundi du cycle, le cycle part le lendemain, sans décaler les suivants.

### Les étapes du cycle (`bin/alis-cycle`)

| Étape | Nature | Ce qu'elle fait |
|-------|--------|-----------------|
| `preflight` | script | Outils, accès Google Drive, session Claude, GitHub, npm |
| `decide` | script | Applique la règle → `decisions/DECISIONS-<cycle>.json` |
| `validate` | script | Range les hypothèses (go / nogo / deferred), archive les signaux |
| `implement` | agent borné | Rédige les GO dans le corpus, vérifie les sources, publie la doctrine (`published/`) |
| `communication` | agent borné | Brouillons release notes / LinkedIn / Discord / X (non bloquant) |
| `sdd-prepare` | script | Clone propre de `sdd-mode`, `npm ci`, `sync-doctrine` depuis `published/md` |
| `site` | agent borné | Aligne `site/` (FR + EN) et les templates, committe en local |
| `release` | script | `release.js minor`, mêmes gates que la CI, puis **push de `main` et du tag** |
| `verify` | script | Attend les workflows `Release` et `site-deploy`, contrôle npm et le site |
| `close` | script | Rapport `releases/CYCLE-REPORT-<cycle>.md`, planifie le cycle suivant |

**Séparation des pouvoirs.** Les agents de rédaction tournent avec une liste blanche d'outils : ils éditent des fichiers et committent en local, mais `git push`, `git tag`, `npm publish` et `gh release` leur sont refusés. Seul le script publie, après les contrôles. Un agent en échec écrit `"status": "failed"` et rien n'est publié.

**Reprise.** Chaque étape pose un marqueur dans `state/runs/<cycle>/`. Après un échec, le passage du lendemain reprend à l'étape en échec. Après 3 tentatives, le cycle s'arrête et te notifie.

---

## Ce qui te reste

- **Publier la communication** : les brouillons sont dans `releases/` ; rien ne part sur LinkedIn, Discord ou X sans toi.
- **Les hypothèses retenues** (Constitution, valeurs fondatrices) : listées dans le briefing et le rapport de cycle.
- **Les évolutions logicielles** du package : le cycle ouvre une issue sur `sdd-mode` ; elles suivent Intent → SPEC → Gate.
- **Trois prérequis à tenir** :
  1. **Mac allumé** et session ouverte autour de 08h30 (sinon rattrapage au prochain passage).
  2. **Accès Google Drive pour « ALIS »** : accordé une fois (boîte de dialogue macOS, ou Réglages Système → Confidentialité et sécurité → Fichiers et dossiers → ALIS). À redonner si `launcher/build.sh` est relancé.
  3. **Session Claude valide** : une connexion `claude auth login` expire. Pour des jobs sans surveillance, préfère `claude setup-token` (jeton longue durée). `alis-cycle` te prévient dans la semaine qui précède si la session expire avant le cycle. Le jeton se range dans `~/.config/alis/claude-token` (mode 600, hors dépôt) : les quatre jobs le lisent s'il commence par `sk-ant-oat`, et l'ignorent sinon.
- Le secret GitHub **`NPM_TOKEN`** du dépôt `sdd-mode` doit rester valide (publication npm par `release.yml`).

---

## Commandes à connaître

```bash
cd ~/Dev/repos/alis

bin/alis-cycle --status      # date du prochain cycle, étapes faites, tentatives
bin/alis-cycle --dry-run     # décisions que la règle prendrait, sans rien écrire
uv run alis status           # signaux et hypothèses en stock

tail -f logs/cycle.log       # journal du cycle (étapes, gates, publication)
tail -f logs/cycle-implement.log logs/cycle-site.log   # journaux des agents de rédaction
```

### Lancer ou relancer le cycle à la main

Toujours via l'app, pour avoir l'accès Google Drive :

```bash
open -W -n -a ~/Dev/repos/alis/launcher/ALIS.app --args cycle            # comme launchd : rien si non dû
open -W -n -a ~/Dev/repos/alis/launcher/ALIS.app --args cycle --force    # force le cycle courant / relance après blocage
```

Depuis un terminal qui a déjà accès au Drive, `bin/alis-cycle --force` marche aussi.

### Changer la date du prochain cycle

```bash
uv run alis cycle-init --next 2026-12-21
```

### Suspendre l'automatisation

```bash
launchctl bootout gui/$(id -u)/ovh.aiad.alis-cycle        # suspendre
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ovh.aiad.alis-cycle.plist   # reprendre
```

### Vérifier l'accès Google Drive du lanceur

```bash
open -W -n -a ~/Dev/repos/alis/launcher/ALIS.app --args probe; cat ~/Dev/repos/alis/logs/probe.log   # DRIVE_READ=ok attendu
```

---

## En cas d'échec

Tu reçois une notification macOS « ALIS — cycle … en échec » avec l'étape. Ensuite :

1. `bin/alis-cycle --status` puis `tail -50 logs/cycle.log`.
2. Corrige la cause (accès Drive, session Claude, gate en échec, `NPM_TOKEN` expiré…).
3. Laisse le passage du lendemain reprendre, ou relance avec `--force`.

Cas particuliers :
- **Échec à `release` avant le push** : rien n'est publié ; le clone `work/sdd-mode` garde les commits locaux.
- **Échec à `verify`** : `main` et le tag sont déjà poussés. Regarde `gh run list --repo everssteeve/sdd-mode` ; une fois le workflow relancé avec succès, le passage suivant valide et clôt le cycle.
- **Revenir sur une doctrine publiée** : chaque fichier modifié a sa copie dans le dossier `archives/` voisin (`<nom>-<cycle>.md`).

---

## Fichiers importants

| Fichier | Rôle |
|---------|------|
| `bin/alis-cycle` | Orchestrateur du cycle |
| `routines/routine-implement.md`, `routine-site.md`, `routine-release.md` | Consignes des agents de rédaction |
| `routines/routine-collect.md`, `routine-score.md`, `routine-briefing.md` | Consignes des agents hebdomadaires |
| `src/alis/commands/decide.py`, `src/alis/cycle.py` | Règle de décision, cadence de 28 jours |
| `state/cycle.json` | Date du prochain cycle, historique (local, hors Drive) |
| `state/runs/<cycle>/` | Marqueurs d'étapes et résultats d'un cycle |
| `launcher/ALIS.app` | Lanceur natif : donne aux jobs launchd l'accès Google Drive |
| `launchd/ovh.aiad.alis-cycle.plist` | Copie de référence de l'agent quotidien |
| `work/sdd-mode/` | Clone dédié du dépôt `sdd-mode` (jamais ton clone de travail) |

---

## Ce qu'ALIS ne fait toujours pas sans toi

- Décider d'une hypothèse qui touche la Constitution ou les valeurs fondatrices
- Publier sur LinkedIn, Discord ou X
- Modifier la règle de décision ou le seuil
- Écrire du code dans `lib/` ou `bin/` du package sans passer par Intent → SPEC → Gate

*Tu fixes la règle. L'outillage l'applique. Tu peux la reprendre à tout moment.*

---

*Dépôt : `/Users/steeve/Dev/repos/alis`*
