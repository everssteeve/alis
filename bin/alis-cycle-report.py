#!/usr/bin/env python3
"""Rapport de cycle ALIS (Markdown sur stdout), à partir du dossier d'exécution.

Usage : alis-cycle-report.py <run_dir> <cycle> <next_cycle> <résultat>
"""

import json
import sys
from pathlib import Path


def load(run: Path, name: str) -> dict:
    path = run / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def fmt(score: float) -> str:
    return f"{score:g}".replace(".", ",")


def render(run: Path, cycle: str, next_cycle: str, outcome: str) -> str:
    dec, impl, site = (
        load(run, "decisions.json"),
        load(run, "implement.json"),
        load(run, "site.json"),
    )
    version_file = run / "version"
    version = version_file.read_text().strip() if version_file.exists() else None

    out = [
        f"# Rapport de cycle ALIS — {cycle}",
        "",
        "**Mode** : automatique (règle permanente du Gardien du 11 novembre 2026 : "
        f"{dec.get('rule', 'n/d')})",
        f"**Résultat** : {outcome}",
        f"**Prochain cycle** : {next_cycle}",
        "",
    ]
    if impl:
        out.append(
            f"- Doctrine : {impl.get('previous_framework_version')} → "
            f"**{impl.get('framework_version')}** (publiée)"
        )
    if version:
        out.append(f"- Package : **aiad-sdd@{version}** sur npm")
        out.append(f"- Site : aiad.ovh déployé en v{version}")

    out += [
        "",
        "## Décisions",
        "",
        "| Hypothèse | Score | Décision | Source | Titre |",
        "|---|---|---|---|---|",
    ]
    for d in dec.get("decisions", []):
        out.append(
            f"| {d['id']} | {fmt(d['score'])}/20 | {d['decision']} | {d['source']} | {d['title']} |"
        )

    if dec.get("held"):
        out += ["", "## Retenues pour le Gardien (jamais décidées automatiquement)", ""]
        out += [
            f"- **{d['id']}** ({fmt(d['score'])}/20) — {d['title']} : {d['comment']}"
            for d in dec["held"]
        ]

    sections = (
        ("Points réservés au Gardien pendant l'implémentation", impl.get("held_for_guardian")),
        ("Points écartés faute de source vérifiable", impl.get("dropped")),
        ("Évolutions logicielles demandées", impl.get("software_changes")),
        ("Issues ouvertes sur sdd-mode", site.get("issues_opened")),
    )
    for title, items in sections:
        if items:
            out += ["", f"## {title}", ""] + [f"- {item}" for item in items]

    if impl.get("summary"):
        out += ["", "## Synthèse", "", impl["summary"]]

    out += [
        "",
        "---",
        f"*Les brouillons de communication (`releases/*-{cycle}.md`) ne sont pas publiés "
        "automatiquement.*",
        "*Pour infirmer une décision automatique : déposer `decisions/OVERRIDES-<cycle>.json` "
        "avant le jour du cycle.*",
    ]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    sys.stdout.write(render(Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]))
