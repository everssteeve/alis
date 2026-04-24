"""Phase 4 — Validation du cycle post-décision Guardian.

Attend un fichier DECISIONS-YYYY-MM-DD.json avec le format :
{
  "cycle": "2026-05-01",
  "decisions": [
    {"id": "HYP-2026-04-28-001", "decision": "GO", "comment": "..."},
    {"id": "HYP-2026-04-28-002", "decision": "NO GO", "comment": "..."},
    {"id": "HYP-2026-04-28-003", "decision": "DEFER", "comment": "..."}
  ]
}
"""

import json
import re
import shutil
from datetime import date
from pathlib import Path

from rich.console import Console

from ..config import (
    HYPOTHESES_PENDING,
    HYPOTHESES_DEFERRED,
    HYPOTHESES_GO,
    HYPOTHESES_NOGO,
    SIGNALS_SCORED,
    SIGNALS_ARCHIVED,
    RELEASES,
)
from ..models import Decision
from ..parser import parse_hypothesis

console = Console()


def _apply_decision_to_file(path: Path, decision: Decision, comment: str, cycle: str) -> str:
    """Met à jour le fichier hypothèse avec la décision du Gardien."""
    content = path.read_text(encoding="utf-8")

    # Cocher la bonne case
    if decision == Decision.GO:
        content = re.sub(r"\[ \] GO", "[x] GO", content)
    elif decision == Decision.NOGO:
        content = re.sub(r"\[ \] NO GO", "[x] NO GO", content)
    elif decision == Decision.DEFER:
        content = re.sub(r"\[ \] DEFER", "[x] DEFER", content)

    # Remplir la section Décision
    content = re.sub(
        r"## Décision du Gardien\n\*\*Date\*\* :\n\*\*Commentaire\*\* :",
        f"## Décision du Gardien\n**Date** : {cycle}\n**Commentaire** : {comment}",
        content,
    )

    return content


def _bump_defer_score(path: Path) -> None:
    """Augmente le score d'une hypothèse DEFER de +2."""
    content = path.read_text(encoding="utf-8")
    m = re.search(r"\*\*Total\*\*\s*:\s*(\d+)/20", content)
    if m:
        old_score = int(m.group(1))
        new_score = min(old_score + 2, 20)
        content = content.replace(
            f"**Total** : {old_score}/20", f"**Total** : {new_score}/20"
        )
        path.write_text(content, encoding="utf-8")


def _generate_implementation_plan(
    go_hyps: list, cycle: str, output_path: Path
) -> None:
    """Génère le plan d'implémentation pour les GO."""
    today = date.today().strftime("%Y-%m-%d")
    lines = [
        f"# Plan d'Implémentation — Cycle {cycle}",
        f"**Généré par ALIS** — {today}",
        "",
        f"## Hypothèses à implémenter ({len(go_hyps)} GO)",
        "",
    ]

    for i, hyp in enumerate(go_hyps, 1):
        lines += [
            f"### T{i} — {hyp.id} : {hyp.title}",
            f"**Composante** : {hyp.component}",
            f"**Score** : {hyp.score}/20",
            "",
            "**Modification proposée** :",
            hyp.proposed_modification,
            "",
            "**Tâches** :",
            "- [ ] Identifier les fichiers à modifier",
            "- [ ] Rédiger les modifications (agent)",
            "- [ ] Validation Gardien",
            "- [ ] Anti-drift check (terminologie cohérente)",
            "- [ ] Commit + changelog",
            "",
            "---",
            "",
        ]

    lines += [
        "## Anti-Drift Checklist",
        "- [ ] Terminologie cohérente dans tous les artefacts modifiés",
        "- [ ] Liens croisés entre documents vérifiés",
        "- [ ] Version AIAD bumped si nécessaire",
        "",
        "## Communication (J+2)",
        "- [ ] Release notes générées (`alis release`)",
        "- [ ] LinkedIn validé par Gardien",
        "- [ ] Discord annoncé",
        "- [ ] Thread X posté",
    ]

    output_path.write_text("\n".join(lines), encoding="utf-8")


def run_validate(decisions_file: Path, dry_run: bool = False) -> None:
    """Point d'entrée de la commande `alis validate`."""
    if not decisions_file.exists():
        console.print(f"[red]✗ Fichier de décisions introuvable : {decisions_file}[/red]")
        console.print(
            "Crée un fichier DECISIONS-YYYY-MM-DD.json avec les décisions GO/NO GO/DEFER."
        )
        return

    data = json.loads(decisions_file.read_text(encoding="utf-8"))
    cycle = data["cycle"]
    decisions_raw = data["decisions"]

    console.print(f"[bold]ALIS Validate[/bold] — cycle [cyan]{cycle}[/cyan]")
    console.print(f"{len(decisions_raw)} décisions à appliquer")

    if dry_run:
        console.print("[dim]--dry-run : simulation[/dim]")
        for d in decisions_raw:
            console.print(f"  {d['id']} → [cyan]{d['decision']}[/cyan]")
        return

    # Créer les dossiers de destination
    for d in [HYPOTHESES_GO, HYPOTHESES_NOGO, HYPOTHESES_DEFERRED, SIGNALS_ARCHIVED]:
        d.mkdir(parents=True, exist_ok=True)

    go_hyps = []

    for dec in decisions_raw:
        hyp_id = dec["id"]
        decision_str = dec["decision"].upper().replace(" ", "_")
        comment = dec.get("comment", "")

        # Trouver le fichier dans pending/
        matches = list(HYPOTHESES_PENDING.glob(f"{hyp_id}.md"))
        if not matches:
            # Peut aussi être dans deferred/
            matches = list(HYPOTHESES_DEFERRED.glob(f"{hyp_id}.md"))
        if not matches:
            console.print(f"[yellow]⚠ {hyp_id} introuvable dans pending/ ou deferred/[/yellow]")
            continue

        src = matches[0]
        hyp = parse_hypothesis(src)

        try:
            decision = Decision(dec["decision"])
        except ValueError:
            console.print(f"[red]✗ Décision invalide pour {hyp_id} : {dec['decision']}[/red]")
            continue

        # Mettre à jour le contenu
        updated = _apply_decision_to_file(src, decision, comment, cycle)
        src.write_text(updated, encoding="utf-8")

        # Déplacer vers le bon dossier
        if decision == Decision.GO:
            dest = HYPOTHESES_GO / src.name
            go_hyps.append(hyp)
            label = "[green]GO →go/[/green]"
        elif decision == Decision.NOGO:
            dest = HYPOTHESES_NOGO / src.name
            label = "[red]NO GO →nogo/[/red]"
        else:  # DEFER
            dest = HYPOTHESES_DEFERRED / src.name
            _bump_defer_score(src)
            label = "[yellow]DEFER →deferred/ (+2)[/yellow]"

        shutil.move(str(src), str(dest))
        console.print(f"  {hyp_id} → {label}")

    # Archiver les signaux scored
    scored_files = list(SIGNALS_SCORED.glob("SIG-*.md"))
    for f in scored_files:
        shutil.move(str(f), str(SIGNALS_ARCHIVED / f.name))
    console.print(f"[dim]{len(scored_files)} signaux archivés[/dim]")

    # Générer le plan d'implémentation
    if go_hyps:
        plan_path = RELEASES.parent / f"IMPLEMENTATION-CYCLE-{cycle}.md"
        RELEASES.mkdir(parents=True, exist_ok=True)
        # Plan dans le dossier alis/ racine
        plan_path = HYPOTHESES_GO.parent.parent / f"IMPLEMENTATION-CYCLE-{cycle}.md"
        _generate_implementation_plan(go_hyps, cycle, plan_path)
        console.print(f"[green]✓ Plan d'implémentation : {plan_path.name}[/green]")

    console.print(
        f"\n[green]✓ Cycle {cycle} validé — "
        f"{len(go_hyps)} GO | "
        f"{len([d for d in decisions_raw if d['decision'] == 'NO GO'])} NO GO | "
        f"{len([d for d in decisions_raw if d['decision'] == 'DEFER'])} DEFER[/green]"
    )
    console.print("Lance [bold]alis release[/bold] pour générer la communication.")
