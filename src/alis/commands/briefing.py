"""Phase 3 — Génération du briefing J-3 avant la pleine lune."""

from datetime import date
from pathlib import Path

import anthropic
from rich.console import Console

from ..config import (
    ANTHROPIC_API_KEY,
    ALIS_MODEL,
    BRIEFINGS,
    HYPOTHESES_PENDING,
    HYPOTHESES_DEFERRED,
    SIGNALS_SCORED,
    SIGNALS_INBOX,
    TEMPLATES,
)
from ..lunar import next_full_moon, briefing_date, cycle_label
from ..models import Hypothesis, Signal
from ..parser import parse_hypothesis, parse_signal

console = Console()


def _load_hypotheses(directory: Path) -> list[Hypothesis]:
    if not directory.exists():
        return []
    files = sorted(directory.glob("HYP-*.md"))
    hypotheses = []
    for f in files:
        try:
            hypotheses.append(parse_hypothesis(f))
        except Exception as e:
            console.print(f"[yellow]⚠ Impossible de lire {f.name} : {e}[/yellow]")
    return hypotheses


def _load_signal(sig_id: str) -> Signal | None:
    for directory in [SIGNALS_SCORED, SIGNALS_INBOX]:
        if not directory.exists():
            continue
        # Cherche le fichier par ID dans le nom
        matches = list(directory.glob(f"*{sig_id}*.md"))
        if matches:
            try:
                return parse_signal(matches[0])
            except Exception:
                pass
    return None


def _load_signals_for_hypothesis(hyp: Hypothesis) -> list[Signal]:
    signals = []
    for sig_id in hyp.signal_ids:
        sig = _load_signal(sig_id)
        if sig:
            signals.append(sig)
    return signals


def _load_all_scored_signals() -> list[Signal]:
    if not SIGNALS_SCORED.exists():
        return []
    signals = []
    for f in sorted(SIGNALS_SCORED.glob("SIG-*.md")):
        try:
            signals.append(parse_signal(f))
        except Exception:
            pass
    return signals


def _build_system_prompt() -> str:
    """Charge le template briefing + constitution pour le cache Anthropic."""
    template_path = TEMPLATES / "briefing.md"
    template = template_path.read_text(encoding="utf-8") if template_path.exists() else ""

    return f"""Tu es l'agent ALIS (AIAD Lunar Intelligence System), responsable de générer les briefings pré-pleine lune pour le Gardien du framework AIAD (Steeve Evers).

## Rôle
Tu synthétises les hypothèses d'évolution et les signaux en un briefing structuré, précis et actionnable. Tu ne décides pas — tu prépares la décision humaine.

## Règles absolues
- Ne jamais décider à la place du Gardien
- Toujours fournir la chaîne de signaux justifiant chaque hypothèse
- Être honnête sur les risques, pas seulement les bénéfices
- Le briefing doit permettre une review de 45 minutes maximum
- Les hypothèses de priorité haute (≥16/20) en premier
- Les hypothèses reportées du cycle précédent ont leur score augmenté de +2

## Format de sortie attendu

{template}

## Contraintes de format
- Markdown pur, pas de HTML
- Dates au format YYYY-MM-DD
- IDs en format HYP-YYYY-MM-NNN et SIG-YYYY-MM-NNN
- Les cases à cocher décision restent vides (⬜)
- Conclure par : *Briefing généré par ALIS — AIAD Lunar Intelligence System*
"""


def _build_user_prompt(
    pending: list[Hypothesis],
    deferred: list[Hypothesis],
    all_signals: list[Signal],
    full_moon: date,
    gen_date: date,
) -> str:
    parts: list[str] = []

    parts.append(f"## Date de génération : {gen_date.strftime('%d %B %Y')}")
    parts.append(f"## Pleine lune cible : {full_moon.strftime('%d %B %Y')} ({cycle_label(full_moon)})")
    parts.append("")

    # --- Hypothèses pending ---
    if pending:
        parts.append(f"## Hypothèses en attente de review ({len(pending)})")
        for hyp in sorted(pending, key=lambda h: h.score, reverse=True):
            sigs = _load_signals_for_hypothesis(hyp)
            sig_summaries = "\n".join(
                f"  - {s.id} ({s.score_total}/20) : {s.summary}" for s in sigs
            ) or "  (signaux non retrouvés dans scored/)"
            parts.append(f"""
### {hyp.id} — {hyp.title}
**Score** : {hyp.score}/20 | **Composante** : {hyp.component} | **Priorité** : {hyp.priority}

**Modification proposée** :
{hyp.proposed_modification}

**Justification terrain** :
{hyp.terrain_justification}

**Impact** : Bénéfice — {hyp.benefit} / Risque — {hyp.risk} / Effort — {hyp.effort}

**Signaux source** :
{sig_summaries}
""")
    else:
        parts.append("## Hypothèses en attente de review : aucune")

    # --- Hypothèses reportées ---
    if deferred:
        parts.append(f"\n## Hypothèses reportées du cycle précédent ({len(deferred)})")
        for hyp in sorted(deferred, key=lambda h: h.score, reverse=True):
            parts.append(f"""
### {hyp.id} — {hyp.title} *(reportée, score +2)*
**Score ajusté** : {hyp.score}/20 | **Composante** : {hyp.component}
{hyp.terrain_justification[:300]}...
""")

    # --- Signaux non transformés en hypothèse ---
    under_threshold = [s for s in all_signals if s.score_total < 12]
    if under_threshold:
        parts.append(f"\n## Signaux sous le seuil ({len(under_threshold)} signaux, pour information)")
        for sig in sorted(under_threshold, key=lambda s: s.score_total, reverse=True)[:10]:
            parts.append(f"- {sig.id} ({sig.score_total}/20) : {sig.summary}")

    # Métriques brutes
    total_signals = len(all_signals)
    above_threshold = len([s for s in all_signals if s.score_total >= 12])
    parts.append(f"""
## Métriques brutes du cycle
- Signaux scored/ disponibles : {total_signals}
- Signaux ≥ {12} : {above_threshold}
- Hypothèses pending : {len(pending)}
- Hypothèses deferred : {len(deferred)}
""")

    parts.append(
        "Génère maintenant le briefing complet en suivant exactement le format du template."
    )

    return "\n".join(parts)


def run_briefing(dry_run: bool = False, force: bool = False) -> Path | None:
    """Point d'entrée de la commande `alis briefing`."""
    if not ANTHROPIC_API_KEY and not dry_run:
        console.print("[red]✗ ANTHROPIC_API_KEY manquant dans .env[/red]")
        return None

    today = date.today()
    full_moon = next_full_moon(today)
    j3 = briefing_date(full_moon)
    label = cycle_label(full_moon)
    output_path = BRIEFINGS / f"BRIEFING-{label}.md"

    console.print(f"[bold]ALIS Briefing[/bold] — cycle [cyan]{label}[/cyan]")
    console.print(f"Pleine lune : [cyan]{full_moon}[/cyan]  •  J-3 (date idéale) : [cyan]{j3}[/cyan]")

    if output_path.exists() and not force:
        console.print(f"[yellow]Briefing existant : {output_path.name}[/yellow]")
        console.print("Utilise [bold]--force[/bold] pour le regénérer.")
        return output_path

    # Chargement des hypothèses
    pending = _load_hypotheses(HYPOTHESES_PENDING)
    deferred = _load_hypotheses(HYPOTHESES_DEFERRED)
    all_signals = _load_all_scored_signals()

    console.print(
        f"[dim]Hypothèses pending : {len(pending)} | deferred : {len(deferred)} | "
        f"signaux scored : {len(all_signals)}[/dim]"
    )

    if not pending and not deferred:
        console.print(
            "[yellow]⚠ Aucune hypothèse en attente. Lance d'abord `alis score`.[/yellow]"
        )

    if dry_run:
        console.print("[dim]--dry-run : pas d'appel API, pas d'écriture fichier[/dim]")
        prompt = _build_user_prompt(pending, deferred, all_signals, full_moon, today)
        console.print("\n[bold]Prompt user (extrait) :[/bold]")
        console.print(prompt[:2000])
        return None

    # Appel Claude avec prompt caching sur le system prompt
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(pending, deferred, all_signals, full_moon, today)

    console.print("[dim]Appel Claude API...[/dim]")

    message = client.messages.create(
        model=ALIS_MODEL,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )

    briefing_content = message.content[0].text

    # Écriture
    BRIEFINGS.mkdir(parents=True, exist_ok=True)
    output_path.write_text(briefing_content, encoding="utf-8")

    usage = message.usage
    console.print(f"[green]✓ Briefing écrit : {output_path}[/green]")
    console.print(
        f"[dim]Tokens : {usage.input_tokens} in / {usage.output_tokens} out"
        + (
            f" / {usage.cache_read_input_tokens} cache_read"
            if hasattr(usage, "cache_read_input_tokens")
            else ""
        )
        + "[/dim]"
    )

    return output_path
