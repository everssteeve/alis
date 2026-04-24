"""Phase 2 — Scoring des signaux inbox et génération des hypothèses."""

from datetime import date
from pathlib import Path
import re

import anthropic
from rich.console import Console

from ..config import (
    ANTHROPIC_API_KEY,
    ALIS_MODEL,
    SCORE_THRESHOLD,
    SIGNALS_INBOX,
    SIGNALS_SCORED,
    HYPOTHESES_PENDING,
    TEMPLATES,
)
from ..models import Signal, SignalScore
from ..parser import parse_signal

console = Console()

SCORING_SYSTEM = """Tu es l'agent de scoring ALIS. Tu analyses les signaux bruts et :
1. Tu leur attribues un score sur 4 dimensions (1-5 chacune) = total /20
2. Si le score ≥ {threshold}, tu génères une hypothèse d'évolution structurée

## Dimensions de scoring
- **Fréquence** (1-5) : Ce signal est-il isolé (1) ou répété dans plusieurs sources (5) ?
- **Impact** (1-5) : Impact potentiel sur la valeur du framework AIAD (1=marginal, 5=fondamental)
- **Urgence** (1-5) : L'inaction est-elle coûteuse maintenant (1=peut attendre, 5=urgent)
- **Complexité inversée** (1-5) : Effort d'implémentation (1=très complexe, 5=simple)

## Format de réponse attendu (JSON strict)
{{
  "score": {{
    "frequence": X,
    "impact": X,
    "urgence": X,
    "complexite": X,
    "total": X,
    "justification": "phrase courte"
  }},
  "generate_hypothesis": true/false,
  "hypothesis": {{
    "title": "...",
    "component": "framework|sdd-mode|alis|constitution",
    "proposed_modification": "...",
    "terrain_justification": "...",
    "benefit": "...",
    "risk": "...",
    "effort": "faible|moyen|élevé"
  }}
}}
"""


def _score_signal_with_claude(client: anthropic.Anthropic, signal: Signal) -> dict:
    """Appelle Claude pour scorer un signal et éventuellement générer une hypothèse."""
    import json

    system = SCORING_SYSTEM.format(threshold=SCORE_THRESHOLD)

    user = f"""Signal à analyser :

**ID** : {signal.id}
**Source** : {signal.source_type} / {signal.origin}
**Catégorie** : {signal.category}
**Résumé** : {signal.summary}
**Détail** : {signal.detail}
**URL** : {signal.url}

Réponds UNIQUEMENT avec le JSON demandé, sans markdown ni explication."""

    message = client.messages.create(
        model=ALIS_MODEL,
        max_tokens=1024,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )

    raw = message.content[0].text.strip()
    # Extraire le JSON si enveloppé dans des backticks
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if m:
        raw = m.group(1)
    return json.loads(raw)


def _write_scored_signal(signal: Signal, score_data: dict) -> Path:
    """Met à jour le fichier signal avec les scores et le déplace dans scored/."""
    SIGNALS_SCORED.mkdir(parents=True, exist_ok=True)
    dest = SIGNALS_SCORED / signal.path.name

    sc = score_data["score"]
    score_block = f"""## Scoring (rempli automatiquement en Couche 2)
| Dimension | Score (1-5) | Justification |
|-----------|-------------|---------------|
| Fréquence | {sc['frequence']} | |
| Impact | {sc['impact']} | |
| Urgence | {sc['urgence']} | |
| Complexité (inversé) | {sc['complexite']} | |
| **Score total** | **{sc['total']}/20** | {sc.get('justification', '')} |

## Seuil de passage en hypothèse : ≥ {SCORE_THRESHOLD}/20
"""

    content = signal.raw_content
    # Remplace ou ajoute le bloc scoring
    if "## Scoring" in content:
        content = re.sub(
            r"## Scoring.*?(?=\n## |\Z)", score_block, content, flags=re.DOTALL
        )
    else:
        content = content.rstrip() + "\n\n" + score_block

    dest.write_text(content, encoding="utf-8")
    # Supprimer de l'inbox
    signal.path.unlink(missing_ok=True)
    return dest


def _next_hyp_id() -> str:
    """Génère l'identifiant suivant pour une hypothèse du jour."""
    today = date.today().strftime("%Y-%m-%d")
    HYPOTHESES_PENDING.mkdir(parents=True, exist_ok=True)
    existing = list(HYPOTHESES_PENDING.glob(f"HYP-{today}-*.md"))
    idx = len(existing) + 1
    return f"HYP-{today}-{idx:03d}"


def _write_hypothesis(hyp_id: str, signal: Signal, score_total: int, hyp_data: dict) -> Path:
    """Génère le fichier hypothèse depuis le template."""
    template_path = TEMPLATES / "hypothese.md"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = ""

    content = f"""# Hypothèse d'Évolution ALIS

## Identifiant
{hyp_id}

## Titre
{hyp_data['title']}

## Signaux source
- {signal.id} ({score_total}/20) : {signal.summary}

## Composante impactée
{hyp_data['component']}

## Description de la modification proposée
{hyp_data['proposed_modification']}

## Justification terrain
{hyp_data['terrain_justification']}

## Impact estimé
- **Bénéfice** : {hyp_data['benefit']}
- **Risque** : {hyp_data['risk']}
- **Effort** : {hyp_data['effort']}

## Score agrégé des signaux
**Total** : {score_total}/20

## Statut (rempli lors de la review)
- [ ] GO — Intégré dans ce cycle
- [ ] NO GO — Rejeté (justification : )
- [ ] DEFER — Reporté (score augmenté de +2 au prochain cycle)

## Décision du Gardien
**Date** :
**Commentaire** :
"""

    HYPOTHESES_PENDING.mkdir(parents=True, exist_ok=True)
    path = HYPOTHESES_PENDING / f"{hyp_id}.md"
    path.write_text(content, encoding="utf-8")
    return path


def run_score(dry_run: bool = False) -> None:
    """Point d'entrée de la commande `alis score`."""
    if not ANTHROPIC_API_KEY and not dry_run:
        console.print("[red]✗ ANTHROPIC_API_KEY manquant dans .env[/red]")
        return

    if not SIGNALS_INBOX.exists() or not any(SIGNALS_INBOX.glob("SIG-*.md")):
        console.print("[yellow]⚠ Aucun signal dans inbox/ — lance d'abord `alis collect`.[/yellow]")
        return

    inbox_files = sorted(SIGNALS_INBOX.glob("SIG-*.md"))
    console.print(
        f"[bold]ALIS Score[/bold] — {len(inbox_files)} signaux à analyser "
        f"(seuil : {SCORE_THRESHOLD}/20)"
    )

    if dry_run:
        console.print("[dim]--dry-run : lecture seule[/dim]")
        for f in inbox_files:
            sig = parse_signal(f)
            console.print(f"  {sig.id} — {sig.summary[:80]}")
        return

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    scored_count = 0
    hyp_count = 0

    for f in inbox_files:
        sig = parse_signal(f)
        console.print(f"[dim]Scoring {sig.id}...[/dim]", end=" ")

        try:
            result = _score_signal_with_claude(client, sig)
        except Exception as e:
            console.print(f"[red]erreur : {e}[/red]")
            continue

        score_total = result["score"]["total"]
        _write_scored_signal(sig, result)
        scored_count += 1

        status = f"[green]{score_total}/20[/green]"
        if score_total < SCORE_THRESHOLD:
            status += " [dim](sous seuil)[/dim]"
        console.print(status)

        if result.get("generate_hypothesis") and result.get("hypothesis"):
            hyp_id = _next_hyp_id()
            hyp_path = _write_hypothesis(hyp_id, sig, score_total, result["hypothesis"])
            hyp_count += 1
            console.print(f"  → Hypothèse générée : [cyan]{hyp_path.name}[/cyan]")

    console.print(
        f"\n[green]✓ {scored_count} signaux scorés, {hyp_count} hypothèses générées[/green]"
    )
    if hyp_count > 0:
        console.print("Lance [bold]alis briefing[/bold] pour générer le briefing Guardian.")
