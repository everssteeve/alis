"""Phase 5 — Génération des artifacts de communication post-cycle."""

from datetime import date
from pathlib import Path

import anthropic
from rich.console import Console

from ..config import (
    ANTHROPIC_API_KEY,
    ALIS_MODEL,
    HYPOTHESES_GO,
    HYPOTHESES_NOGO,
    HYPOTHESES_DEFERRED,
    RELEASES,
    TEMPLATES,
)
from ..parser import parse_hypothesis

console = Console()

RELEASE_SYSTEM = """Tu es l'agent de communication ALIS. Tu génères les artifacts de communication
post-cycle pour le framework AIAD. Ton style est : direct, honnête, tourné praticiens.

Règles :
- Toujours inclure ce qui a changé, POURQUOI (signaux terrain), et ce qui a été rejeté
- La transparence sur les rejets est aussi importante que les intégrations
- Format LinkedIn : 800-1200 caractères, ton professionnel, pas de hashtags excessifs
- Format Discord : conversationnel, bullet points, 400-600 mots
- Thread X : 5-7 tweets de 280 caractères max chacun
- Release notes : markdown structuré, exhaustif
"""


def _build_release_prompt(
    cycle: str,
    go_hyps: list,
    nogo_hyps: list,
    defer_hyps: list,
    format_type: str,
) -> str:
    go_section = "\n".join(
        f"- {h.id} : {h.title} (composante: {h.component})\n"
        f"  Changement: {h.proposed_modification[:200]}\n"
        f"  Justification terrain: {h.terrain_justification[:200]}\n"
        f"  Décision: {h.decision_comment}"
        for h in go_hyps
    )

    nogo_section = "\n".join(
        f"- {h.id} : {h.title} — Rejeté : {h.decision_comment}"
        for h in nogo_hyps
    ) or "Aucun rejet ce cycle."

    defer_section = "\n".join(
        f"- {h.id} : {h.title} — Reporté : {h.decision_comment}"
        for h in defer_hyps
    ) or "Aucun report ce cycle."

    return f"""Génère le contenu de communication ALIS pour le cycle {cycle}.

## Hypothèses intégrées (GO — {len(go_hyps)})
{go_section or 'Aucune.'}

## Hypothèses rejetées (NO GO — {len(nogo_hyps)})
{nogo_section}

## Hypothèses reportées (DEFER — {len(defer_hyps)})
{defer_section}

**Format demandé** : {format_type}

Génère maintenant le contenu."""


def _call_claude(client: anthropic.Anthropic, cycle: str, go: list, nogo: list, defer: list, fmt: str) -> str:
    message = client.messages.create(
        model=ALIS_MODEL,
        max_tokens=2048,
        system=[{"type": "text", "text": RELEASE_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": _build_release_prompt(cycle, go, nogo, defer, fmt)}],
    )
    return message.content[0].text


def _load_hyps_from_dir(directory: Path) -> list:
    if not directory.exists():
        return []
    return [parse_hypothesis(f) for f in sorted(directory.glob("HYP-*.md"))]


def run_release(cycle: str | None = None, dry_run: bool = False) -> None:
    """Point d'entrée de la commande `alis release`."""
    if not ANTHROPIC_API_KEY:
        console.print("[red]✗ ANTHROPIC_API_KEY manquant dans .env[/red]")
        return

    if not cycle:
        cycle = date.today().strftime("%Y-%m-%d")

    console.print(f"[bold]ALIS Release[/bold] — cycle [cyan]{cycle}[/cyan]")

    # Charger les hypothèses du cycle depuis go/ nogo/ deferred/
    go_hyps = [h for h in _load_hyps_from_dir(HYPOTHESES_GO) if cycle in h.path.name or True]
    nogo_hyps = _load_hyps_from_dir(HYPOTHESES_NOGO)
    defer_hyps = _load_hyps_from_dir(HYPOTHESES_DEFERRED)

    # Filtrer par cycle si possible (date dans le nom de fichier)
    def filter_cycle(hyps: list, cycle: str) -> list:
        filtered = [h for h in hyps if cycle[:7] in h.id]
        return filtered if filtered else hyps

    go_hyps = filter_cycle(go_hyps, cycle)
    nogo_hyps = filter_cycle(nogo_hyps, cycle)
    defer_hyps = filter_cycle(defer_hyps, cycle)

    console.print(
        f"[dim]{len(go_hyps)} GO | {len(nogo_hyps)} NO GO | {len(defer_hyps)} DEFER[/dim]"
    )

    if dry_run:
        console.print("[dim]--dry-run : listing des hypothèses[/dim]")
        for h in go_hyps:
            console.print(f"  GO    {h.id} — {h.title}")
        for h in nogo_hyps:
            console.print(f"  NOGO  {h.id} — {h.title}")
        return

    if not ANTHROPIC_API_KEY:
        return

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    RELEASES.mkdir(parents=True, exist_ok=True)

    formats = {
        f"RELEASE-{cycle}.md": "release notes markdown exhaustives",
        f"LINKEDIN-{cycle}.md": "post LinkedIn (800-1200 caractères, professionnel)",
        f"DISCORD-{cycle}.md": "annonce Discord (conversationnel, bullet points)",
        f"THREAD-X-{cycle}.md": "thread X/Twitter (5-7 tweets de 280 caractères max)",
    }

    for filename, fmt in formats.items():
        output_path = RELEASES / filename
        if output_path.exists():
            console.print(f"[yellow]Existant : {filename}[/yellow]")
            continue

        console.print(f"[dim]Génération {filename}...[/dim]")
        content = _call_claude(client, cycle, go_hyps, nogo_hyps, defer_hyps, fmt)
        output_path.write_text(content, encoding="utf-8")
        console.print(f"[green]✓ {filename}[/green]")

    console.print(f"\n[green]✓ Communication générée dans {RELEASES}[/green]")
    console.print("[bold yellow]⚠ Validation Gardien requise avant toute publication.[/bold yellow]")
