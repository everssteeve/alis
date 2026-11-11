"""Phase 3 bis — Décision automatique par délégation permanente du Gardien.

Règle adoptée par le Gardien le 2026-11-11 : toute hypothèse dont le score
agrégé est strictement supérieur à `AUTO_GO_ABOVE` (14/20) est acceptée (GO)
sans review manuelle. Le reste suit la règle de péremption déjà en vigueur :

    décision explicite du Gardien (OVERRIDES-<cycle>.json)  → appliquée telle quelle
    composante « constitution »                              → RETENUE (jamais automatique)
    score illisible                                          → RETENUE
    score > seuil                                            → GO
    score ≤ seuil, premier passage                           → DEFER (sans bonus)
    score ≤ seuil, déjà reportée                             → NO GO (péremption)

Une hypothèse « retenue » reste dans son dossier : seule une décision explicite
du Gardien peut la faire avancer. Produit `decisions/DECISIONS-<cycle>.json`,
consommé ensuite par `alis validate`.
"""

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from rich.console import Console
from rich.table import Table

from ..config import AUTO_GO_ABOVE, DECISIONS, HYPOTHESES_DEFERRED, HYPOTHESES_PENDING
from ..models import Decision, Hypothesis
from ..parser import format_score, parse_hypothesis

console = Console()

HOLD = "HOLD"


@dataclass(frozen=True)
class AutoDecision:
    id: str
    title: str
    score: float
    decision: str  # "GO" | "NO GO" | "DEFER" | HOLD
    comment: str
    source: str  # "règle" | "gardien"


def decide_one(
    hyp: Hypothesis,
    *,
    already_deferred: bool,
    threshold: float = AUTO_GO_ABOVE,
    override: dict | None = None,
) -> AutoDecision:
    """Applique la règle à une hypothèse (fonction pure)."""
    seuil = format_score(threshold)
    score = format_score(hyp.score)

    def result(decision: str, comment: str, source: str = "règle") -> AutoDecision:
        return AutoDecision(hyp.id, hyp.title, hyp.score, decision, comment, source)

    if override is not None:
        decision = Decision(override["decision"]).value  # lève ValueError si invalide
        if decision == Decision.PENDING.value:
            raise ValueError(f"{hyp.id} : PENDING n'est pas une décision")
        comment = override.get("comment") or "Décision explicite du Gardien."
        return result(decision, comment, source="gardien")

    if "constitution" in hyp.component.lower():
        return result(
            HOLD,
            "Touche la Constitution ou les valeurs fondatrices : domaine réservé du Gardien, "
            "jamais décidé automatiquement.",
        )
    if hyp.score <= 0:
        return result(HOLD, "Score illisible dans le fichier : décision du Gardien requise.")
    if hyp.score > threshold:
        return result(
            Decision.GO.value,
            f"GO automatique — score {score}/20 > {seuil} "
            "(règle permanente du Gardien, 2026-11-11).",
        )
    if already_deferred:
        return result(
            Decision.NOGO.value,
            f"Close par péremption — score {score}/20 ≤ {seuil} après un report. "
            "Un nouveau signal peut la rouvrir.",
        )
    return result(
        Decision.DEFER.value,
        f"Report automatique — score {score}/20 ≤ {seuil}. Sans nouveau signal relevant "
        "le score, close par péremption au prochain cycle.",
    )


def load_overrides(path: Path) -> dict[str, dict]:
    """Charge les décisions explicites du Gardien pour ce cycle (optionnel)."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {d["id"]: d for d in data.get("decisions", [])}


def build_decisions(
    cycle: str,
    pending: list[Hypothesis],
    deferred: list[Hypothesis],
    overrides: dict[str, dict],
    threshold: float = AUTO_GO_ABOVE,
    today: date | None = None,
) -> dict:
    """Construit le contenu de DECISIONS-<cycle>.json (fonction pure)."""
    results = [
        decide_one(h, already_deferred=False, threshold=threshold, override=overrides.get(h.id))
        for h in pending
    ] + [
        decide_one(h, already_deferred=True, threshold=threshold, override=overrides.get(h.id))
        for h in deferred
    ]
    known = {r.id for r in results}
    unknown = sorted(set(overrides) - known)
    results.sort(key=lambda r: (-r.score, r.id))

    def as_dict(r: AutoDecision) -> dict:
        return {
            "id": r.id,
            "title": r.title,
            "score": r.score,
            "decision": r.decision,
            "comment": r.comment,
            "source": r.source,
        }

    return {
        "cycle": cycle,
        "generated": (today or date.today()).isoformat(),
        "mode": "auto",
        "rule": f"GO si score > {format_score(threshold)}/20 ; sinon DEFER puis péremption",
        "defer_bonus": 0,
        "decisions": [as_dict(r) for r in results if r.decision != HOLD],
        "held": [as_dict(r) for r in results if r.decision == HOLD],
        "unknown_overrides": unknown,
    }


def _load_dir(path: Path) -> list[Hypothesis]:
    if not path.exists():
        return []
    return [parse_hypothesis(f) for f in sorted(path.glob("HYP-*.md"))]


def run_decide(cycle: str, dry_run: bool = False, as_json: bool = False) -> Path | None:
    """Point d'entrée de `alis decide`. Retourne le chemin du fichier écrit."""
    overrides_path = DECISIONS / f"OVERRIDES-{cycle}.json"
    data = build_decisions(
        cycle,
        _load_dir(HYPOTHESES_PENDING),
        _load_dir(HYPOTHESES_DEFERRED),
        load_overrides(overrides_path),
    )

    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        table = Table(title=f"ALIS Decide — cycle {cycle} ({data['rule']})")
        for col in ("Hypothèse", "Score", "Décision", "Source", "Titre"):
            table.add_column(col)
        for d in data["decisions"] + data["held"]:
            table.add_row(
                d["id"],
                f"{format_score(d['score'])}/20",
                d["decision"],
                d["source"],
                d["title"][:70],
            )
        console.print(table)
        counts = {
            k: sum(1 for d in data["decisions"] if d["decision"] == k)
            for k in ("GO", "NO GO", "DEFER")
        }
        console.print(
            f"{counts['GO']} GO | {counts['NO GO']} NO GO | {counts['DEFER']} DEFER | "
            f"{len(data['held'])} retenue(s) pour le Gardien"
        )
        for hyp_id in data["unknown_overrides"]:
            console.print(f"[yellow]⚠ Override ignoré : {hyp_id} introuvable[/yellow]")

    if dry_run:
        return None

    DECISIONS.mkdir(parents=True, exist_ok=True)
    out = DECISIONS / f"DECISIONS-{cycle}.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not as_json:
        console.print(f"[green]✓ {out}[/green]")
    return out
