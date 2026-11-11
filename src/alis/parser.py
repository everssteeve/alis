"""Parsers pour les fichiers markdown ALIS (signaux, hypothèses)."""

import re
from pathlib import Path
from datetime import date

from .models import Signal, SignalScore, Hypothesis, Decision


def _extract_field(content: str, field: str) -> str:
    """Extrait la valeur d'un champ markdown, avec ou sans gras."""
    # Pattern bold : **Champ** : Valeur
    m = re.search(rf"\*\*{re.escape(field)}\*\*\s*:\s*(.+)", content)
    if m:
        return m.group(1).strip()
    # Pattern liste non-bold : - Champ : Valeur
    m = re.search(rf"[-*]\s*{re.escape(field)}\s*:\s*(.+)", content)
    if m:
        return m.group(1).strip()
    # Pattern texte libre : Champ : Valeur (en début de ligne)
    m = re.search(rf"^{re.escape(field)}\s*:\s*(.+)", content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    # Pattern : section markdown (prend tout jusqu'à la prochaine section)
    m = re.search(rf"## {re.escape(field)}\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""


def _extract_score_value(content: str, dimension: str) -> int:
    """Extrait le score numérique d'une ligne de tableau."""
    m = re.search(rf"\|\s*{re.escape(dimension)}\s*\|\s*(\d+)", content)
    return int(m.group(1)) if m else 0


def parse_signal(path: Path) -> Signal:
    content = path.read_text(encoding="utf-8")

    sig_id_m = re.search(r"SIG-\d{4}-\d{2}-\d{2}-\d{3}", content)
    sig_id = sig_id_m.group(0) if sig_id_m else path.stem

    # Date depuis l'identifiant
    date_m = re.search(r"SIG-(\d{4})-(\d{2})-(\d{2})-\d{3}", sig_id)
    sig_date = (
        date(int(date_m.group(1)), int(date_m.group(2)), int(date_m.group(3)))
        if date_m
        else date.today()
    )

    # URL
    url_m = re.search(r"\*\*URL\s*/\s*Référence\*\*\s*:\s*(.+)", content)
    url = url_m.group(1).strip() if url_m else ""

    # Résumé — supporte "**Résumé** :" et "Résumé :"
    summary_m = re.search(r"\*\*Résumé\*\*\s*:\s*(.+)", content) or re.search(
        r"^Résumé\s*:\s*(.+)", content, re.MULTILINE
    )
    summary = summary_m.group(1).strip() if summary_m else ""

    # Score total
    total_m = re.search(r"\*\*Score total\*\*\s*\|\s*\*\*(\d+)/20\*\*", content)
    score_total = int(total_m.group(1)) if total_m else 0

    score = SignalScore(
        frequence=_extract_score_value(content, "Fréquence"),
        impact=_extract_score_value(content, "Impact"),
        urgence=_extract_score_value(content, "Urgence"),
        complexite=_extract_score_value(content, "Complexité (inversé)"),
    )
    # Si les dimensions ne sont pas parsées mais qu'on a le total, on l'approche
    if score.total == 0 and score_total > 0:
        score = SignalScore(
            frequence=score_total // 4,
            impact=score_total // 4,
            urgence=score_total // 4,
            complexite=score_total - 3 * (score_total // 4),
        )

    return Signal(
        id=sig_id,
        source_type=_extract_field(content, "Type"),
        origin=_extract_field(content, "Origine"),
        url=url,
        summary=summary,
        detail=_extract_field(content, "Détail"),
        category=_extract_field(content, "Catégorie"),
        date=sig_date,
        score=score,
        path=path,
        raw_content=content,
    )


SCORE_RE = re.compile(r"\*\*Total\*\*\s*:\s*(\d+(?:[.,]\d+)?)\s*/\s*20")


def parse_score(content: str) -> float:
    """Extrait le score agrégé `**Total** : X/20` (0 si absent)."""
    m = SCORE_RE.search(content)
    if not m:
        return 0
    value = float(m.group(1).replace(",", "."))
    return int(value) if value.is_integer() else value


def format_score(score: float) -> str:
    """Formate un score comme dans les fichiers ALIS : 15 → "15", 14.5 → "14,5"."""
    if float(score).is_integer():
        return str(int(score))
    return f"{score:g}".replace(".", ",")


def parse_hypothesis(path: Path) -> Hypothesis:
    content = path.read_text(encoding="utf-8")

    hyp_id_m = re.search(r"HYP-\d{4}-\d{2}-\d{2}-\d{3}", content)
    hyp_id = hyp_id_m.group(0) if hyp_id_m else path.stem

    # Titre
    title_m = re.search(r"## Titre\n(.+)", content)
    title = title_m.group(1).strip() if title_m else ""

    # Score — accepte les décimales à la française ("14,5/20") ou à l'anglaise
    score = parse_score(content)

    # Composante
    comp_m = re.search(r"## Composante impactée\n(.+)", content)
    component = comp_m.group(1).strip() if comp_m else ""

    # Signaux référencés
    signal_ids = re.findall(r"SIG-\d{4}-\d{2}-\d{2}-\d{3}", content)

    # Décision
    decision = Decision.PENDING
    if re.search(r"\[x\] GO", content, re.IGNORECASE):
        decision = Decision.GO
    elif re.search(r"\[x\] NO GO", content, re.IGNORECASE):
        decision = Decision.NOGO
    elif re.search(r"\[x\] DEFER", content, re.IGNORECASE):
        decision = Decision.DEFER

    # Impact
    benefit_m = re.search(r"\*\*Bénéfice\*\*\s*:\s*(.+)", content)
    risk_m = re.search(r"\*\*Risque\*\*\s*:\s*(.+)", content)
    effort_m = re.search(r"\*\*Effort\*\*\s*:\s*(.+)", content)

    # Justification terrain
    justif_m = re.search(
        r"## Justification terrain\n(.*?)(?=\n##|\Z)", content, re.DOTALL
    )

    # Modification proposée
    modif_m = re.search(
        r"## Description de la modification proposée\n(.*?)(?=\n##|\Z)",
        content,
        re.DOTALL,
    )

    # Cycle de report
    deferred_m = re.search(r"cycle\s+(\d{4}-\d{2}-\d{2})", content, re.IGNORECASE)

    # Date de décision Guardian (écrite par validate.py : **Date** : YYYY-MM-DD)
    decision_date_m = re.search(
        r"## Décision du Gardien\n\*\*Date\*\*\s*:\s*(\d{4}-\d{2}-\d{2})", content
    )
    decision_date = decision_date_m.group(1) if decision_date_m else ""

    # Commentaire de décision
    decision_comment_m = re.search(r"\*\*Commentaire\*\*\s*:\s*(.+)", content)
    decision_comment = decision_comment_m.group(1).strip() if decision_comment_m else ""

    return Hypothesis(
        id=hyp_id,
        title=title,
        component=component,
        proposed_modification=modif_m.group(1).strip() if modif_m else "",
        terrain_justification=justif_m.group(1).strip() if justif_m else "",
        benefit=benefit_m.group(1).strip() if benefit_m else "",
        risk=risk_m.group(1).strip() if risk_m else "",
        effort=effort_m.group(1).strip() if effort_m else "",
        score=score,
        signal_ids=list(dict.fromkeys(signal_ids)),  # déduplique
        decision=decision,
        decision_date=decision_date,
        decision_comment=decision_comment,
        deferred_from=deferred_m.group(1) if deferred_m else "",
        path=path,
        raw_content=content,
    )
