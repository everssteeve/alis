---
title: Cartographie de Veille ALIS
version: 1.0
status: draft
gardien: Steeve Evers
derniere_maj: 2026-04-24
ancrage_constitutionnel: Article VII — ALIS, Couche 1 (Collecte continue)
---

# Cartographie de Veille — Sources Externes d'ALIS

*Document opérationnel — alimente la Couche 1 du cycle lunaire ALIS*

---

## Intention

Cette cartographie recense les sources externes qui alimentent la Couche 1 (Collecte continue) d'ALIS. Elle obéit à trois principes ancrés dans la Constitution AIAD :

- **Sobriété intentionnelle** — le volume de sources est borné, la fréquence de consultation est phasée.
- **Empirisme sans concession** — chaque source est classée selon sa valeur de signal réelle, pas son prestige.
- **Transparence** — les critères de priorisation sont explicites et auditables.

Toutes les sources listées ici produisent des signaux qui peuvent être transformés en hypothèses d'évolution pour AIAD ou le SDD Mode. Aucune source ne décide à la place du Gardien.

---

## Principe de phasage

| Cercle | Durée cible | Rôle dans ALIS |
|---|---|---|
| Quotidien | 15 min max | Signaux faibles, détection d'événements |
| Hebdomadaire | 1 h max | Signaux tactiques, enrichissement hypothèses |
| Mensuel (pré-pleine lune) | 2-3 h | Signaux structurels, briefing de décision |

---

## A. Sources écrites

### Strate 1 — Rapports de fond (signal structurel)

- Anthropic — Agentic Coding Trends Report (annuel)
- Stanford HAI — AI Index Report (annuel, avril)
- Faros AI — AI Engineering Report (annuel)
- McKinsey — State of AI (annuel + notes trimestrielles adoption)
- GitHub Octoverse (annuel, octobre/novembre)
- Google Cloud — AI Agent Trends Report (annuel)
- IBM Think — Predictions annuelles (janvier)
- Gartner — Hype Cycle & Magic Quadrant (angle enterprise)

### Strate 2 — Newsletters hebdomadaires (signal tactique)

- The Pragmatic Engineer (Gergely Orosz) — prioritaire
- Latent Space (swyx + Alessio Fanelli)
- ByteByteGo (Alex Xu)
- Simon Willison's Weblog (quotidien mais filtrable)
- Import AI (Jack Clark)
- AI Engineering (Chip Huyen)
- The Rundown AI / TLDR AI (agrégateurs de balayage)

### Strate 3 — Médias techniques (signal éditorial)

- The New Stack — section AI Engineering
- InfoQ — tracks Architecture et AI/ML
- Ars Technica — section AI
- TechCrunch — signal business et levées

### Strate 4 — Sources primaires éditeurs (signal produit)

- Anthropic — blog, changelog Claude Code, documentation
- OpenAI — blog, Codex release notes
- GitHub — blog Copilot, Spec Kit repository
- AWS — annonces Kiro
- Cursor, Cline, Windsurf, Replit — changelogs et blogs
- Model Context Protocol (MCP) — spec officielle et ecosystem updates

### Strate 5 — Recherche et prépublication (signal avancé)

- arXiv — cs.AI, cs.SE (catégories Agents, Software Engineering)
- Papers With Code — section Code Generation / Agents
- Hugging Face Papers (feed quotidien curé)
- Google DeepMind, Meta AI, Anthropic Research — publications directes

### Strate 6 — Communautés et signaux faibles

- r/ClaudeAI, r/cursor, r/LocalLLaMA, r/ExperiencedDevs
- Hacker News — front page et commentaires
- X / LinkedIn — listes curées (Karpathy, Willison, Fowler, Beck, DHH, Yegge, Böckeler)
- GitHub Discussions des projets majeurs (Claude Code, Aider, OpenHands)
- Discord des outils (Cursor, Continue, Cline)

### Strate 7 — Écosystème francophone et européen (signal local)

- Scrum.org blog
- InfoQ France
- Le Comptoir de l'IA, Génération IA (newsletters FR)
- Agile France, Agile Nantes, Agile Rennes, Agile Lille — retours communauté
- Duchess France, Paris.JS, BDX I/O, DevFest — talks enregistrés
- CNIL (RGPD/AI Act opérationnel), ANSSI (sécurité), ARCEP (numérique responsable)

### Strate 8 — Penseurs et voix longues (signal philosophique)

- Martin Fowler & Birgitta Böckeler (ThoughtWorks) — "Exploring generative AI"
- Kent Beck (substack, podcast Pragmatic Summit)
- Andrej Karpathy (X, blog, conférences)
- Cory Doctorow (Pluralistic) — contre-récit critique
- Ethan Mollick (One Useful Thing) — productivité et usage réel
- Margaret-Anne Storey — recherche cognitive debt

---

## B. Sources vidéo YouTube

### Strate V1 — Sources primaires éditeurs vidéo

| Chaîne | Angle | Fréquence | Priorité |
|---|---|---|---|
| @anthropic-ai | Claude, Claude Code, MCP, Agent SDK | Hebdo | Haute |
| @GitHub | Copilot, Spec Kit, GitHub Universe | Hebdo | Haute |
| @OpenAI | Codex, keynotes, DevDay | Variable | Moyenne |
| @GoogleDeepMind | Gemini, Jules, recherche agentique | Variable | Moyenne |
| @cursor_ai | Cursor releases, démos | Bimensuel | Moyenne |
| @Microsoft | MS Build, Ignite, Copilot | Épisodique | Basse |

### Strate V2 — Conférences et événements (signal REX)

| Chaîne | Angle | Priorité |
|---|---|---|
| @aiDotEngineer | Conf mondiale AI Engineering | Haute |
| @InfoQ | QCon, REX équipes ingé | Haute |
| @devoxxfr | Conf dev FR, tracks IA | Haute |
| @GOTO- | Archives conf soft eng | Moyenne |
| @AIProductDay | Conf produit IA | Moyenne |

### Strate V3 — Praticiens seniors et voix de fond

| Chaîne | Angle | Priorité |
|---|---|---|
| @LatentSpaceTV | Podcast AI Engineering (swyx) | Haute |
| @simonw | Démos et analyses lucides | Haute |
| @martinfowler / ThoughtWorks | Méthodo IA & génie logiciel | Haute |
| @ThoughtWorks | Technology Radar, REX consulting | Moyenne |
| @AndrejKarpathy | Pensée longue, vibe coding | Moyenne (haut signal) |

### Strate V4 — REX praticiens francophones

| Chaîne | Angle | Priorité |
|---|---|---|
| @naiersaidane | REX ingé FR, outils | Haute |
| @zeyneb-madi | REX ingé FR, outils | Haute |
| @maddyzhang | REX ingé FR, outils | Haute |
| @theproductcrew5084 | REX produit divers FR | Moyenne |

### Strate V5 — Vulgarisation et explainer

| Chaîne | Angle | Priorité |
|---|---|---|
| @IBMTechnology | Explainers RAG/MCP/agents | Moyenne |
| @StanfordHAI | Recherche académique, AI Index | Moyenne |
| @AILABS-393 | Tutoriels outils coding AI | Moyenne |

---

## Règles de priorisation

1. **Densité de signal** — ratio signal utile / volume produit.
2. **Originalité** — la source produit-elle du signal ou agrège-t-elle ?
3. **Fiabilité** — l'historique de la source est-il constant ?
4. **Ancrage AIAD** — la source nourrit-elle la dimension méthodologique, produit, ou constitutionnelle ?

---

## Gouvernance

- Toute proposition d'ajout ou de retrait passe par une hypothèse ALIS scorée.
- Les modifications sont tracées dans le changelog ci-dessous.
- Le Gardien valide chaque modification en session pré-pleine lune.

---

## Changelog

| Date | Version | Modification | Gardien |
|---|---|---|---|
| 2026-04-24 | 1.0 | Création initiale | Steeve Evers |

---

*Ce document est vivant. Il reflète un état de la veille à un instant donné, non une vérité immuable.*
