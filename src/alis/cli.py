"""CLI principal ALIS — AIAD Lunar Intelligence System."""

from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="alis")
def main() -> None:
    """ALIS — AIAD Lunar Intelligence System.

    Automatisation du cycle lunaire d'évolution du framework AIAD.
    """
    pass


# ── Phase 3 — Briefing ────────────────────────────────────────────────────────

@main.command()
@click.option("--dry-run", is_flag=True, help="Simule sans appel API ni écriture fichier")
@click.option("--force", is_flag=True, help="Regénère même si le briefing existe déjà")
def briefing(dry_run: bool, force: bool) -> None:
    """Génère le briefing J-3 pour la prochaine pleine lune.

    Lit les hypothèses pending/ et deferred/, appelle Claude,
    écrit briefings/BRIEFING-YYYY-MM-DD.md.
    """
    from .commands.briefing import run_briefing
    run_briefing(dry_run=dry_run, force=force)


# ── Phase 2 — Score ───────────────────────────────────────────────────────────

@main.command()
@click.option("--dry-run", is_flag=True, help="Liste les signaux sans les scorer")
def score(dry_run: bool) -> None:
    """Score les signaux de signals/inbox/ et génère les hypothèses.

    Chaque signal est analysé par Claude sur 4 dimensions (fréquence,
    impact, urgence, complexité). Les signaux ≥ 12/20 génèrent une
    hypothèse dans hypotheses/pending/.
    """
    from .commands.score import run_score
    run_score(dry_run=dry_run)


# ── Phase 4 — Validate ────────────────────────────────────────────────────────

@main.command()
@click.argument("decisions_file", type=click.Path(exists=True, path_type=Path))
@click.option("--dry-run", is_flag=True, help="Simule sans déplacer les fichiers")
def validate(decisions_file: Path, dry_run: bool) -> None:
    """Applique les décisions Guardian et clôture le cycle.

    DECISIONS_FILE : chemin vers DECISIONS-YYYY-MM-DD.json
    avec les décisions GO / NO GO / DEFER pour chaque hypothèse.

    Exemple :
        alis validate DECISIONS-2026-05-01.json
    """
    from .commands.validate import run_validate
    run_validate(decisions_file=decisions_file, dry_run=dry_run)


# ── Phase 1 — Collect ─────────────────────────────────────────────────────────

@main.command()
@click.option("--dry-run", is_flag=True, help="Liste les sources sans collecter")
@click.option(
    "--source",
    "sources",
    multiple=True,
    help="ID(s) de source à activer (répétable). Défaut : toutes.",
)
def collect(dry_run: bool, sources: tuple[str, ...]) -> None:
    """Collecte les signaux depuis la WATCHLIST et les sources RSS/web.

    Les signaux pertinents sont écrits dans signals/inbox/ au format
    SIG-YYYY-MM-NNN.md, prêts pour `alis score`.
    """
    from .commands.collect import run_collect
    run_collect(dry_run=dry_run, sources_override=list(sources) if sources else None)


# ── Phase 5 — Release ─────────────────────────────────────────────────────────

@main.command()
@click.option("--cycle", default=None, help="Date du cycle YYYY-MM-DD (défaut : aujourd'hui)")
@click.option("--dry-run", is_flag=True, help="Liste les hypothèses sans générer")
def release(cycle: str | None, dry_run: bool) -> None:
    """Génère les artifacts de communication post-cycle.

    Produit : RELEASE, LINKEDIN, DISCORD, THREAD-X dans releases/.
    Tous les contenus doivent être validés par le Gardien avant publication.
    """
    from .commands.release import run_release
    run_release(cycle=cycle, dry_run=dry_run)


# ── Commandes utilitaires ─────────────────────────────────────────────────────

@main.command()
def status() -> None:
    """Affiche l'état courant du cycle ALIS."""
    from .config import (
        ALIS_PATH, SIGNALS_INBOX, SIGNALS_SCORED, HYPOTHESES_PENDING,
        HYPOTHESES_DEFERRED, BRIEFINGS,
    )
    from .lunar import next_full_moon, briefing_date
    from datetime import date

    full_moon = next_full_moon()
    j3 = briefing_date(full_moon)
    today = date.today()
    days_to_fm = (full_moon - today).days
    days_to_briefing = (j3 - today).days

    console.print(f"\n[bold]ALIS Status[/bold]")
    console.print(f"Prochaine pleine lune : [cyan]{full_moon}[/cyan] (dans {days_to_fm} jours)")
    console.print(f"Date idéale briefing  : [cyan]{j3}[/cyan] ({'+' if days_to_briefing >= 0 else ''}{days_to_briefing} jours)")
    console.print()

    def count_files(path, pattern="*.md"):
        if not path.exists():
            return 0
        return len(list(path.glob(pattern)))

    console.print("[bold]Signaux[/bold]")
    console.print(f"  inbox/  : {count_files(SIGNALS_INBOX, 'SIG-*.md')}")
    console.print(f"  scored/ : {count_files(SIGNALS_SCORED, 'SIG-*.md')}")
    console.print()
    console.print("[bold]Hypothèses[/bold]")
    console.print(f"  pending/  : {count_files(HYPOTHESES_PENDING, 'HYP-*.md')}")
    console.print(f"  deferred/ : {count_files(HYPOTHESES_DEFERRED, 'HYP-*.md')}")
    console.print()
    console.print("[bold]Briefings[/bold]")
    console.print(f"  {count_files(BRIEFINGS, 'BRIEFING-*.md')} généré(s)")
    console.print()

    # Recommandation d'action
    inbox_count = count_files(SIGNALS_INBOX, 'SIG-*.md')
    scored_count = count_files(SIGNALS_SCORED, 'SIG-*.md')
    pending_count = count_files(HYPOTHESES_PENDING, 'HYP-*.md')

    if inbox_count > 0:
        console.print(f"[bold yellow]→ Action recommandée :[/bold yellow] alis score ({inbox_count} signaux à traiter)")
    elif scored_count > 0 and pending_count == 0:
        console.print("[bold yellow]→ Action recommandée :[/bold yellow] alis score (re-run pour générer hypothèses)")
    elif pending_count > 0:
        console.print(f"[bold yellow]→ Action recommandée :[/bold yellow] alis briefing ({pending_count} hypothèses prêtes)")
    elif days_to_fm <= 7:
        console.print("[bold yellow]→ Action recommandée :[/bold yellow] alis collect (pleine lune dans 7 jours)")
    else:
        console.print("[dim]Aucune action urgente.[/dim]")
