import json

import pytest

from alis.commands.decide import HOLD, build_decisions, decide_one, load_overrides
from alis.commands.validate import _apply_decision_to_file, _bump_defer_score
from alis.models import Decision, Hypothesis
from alis.parser import format_score, parse_hypothesis, parse_score

TEMPLATE = """# Hypothèse d'Évolution ALIS

## Identifiant
{id}

## Titre
{title}

## Signaux source
- SIG-2026-11-09-001 (16/20) : un signal

## Composante impactée
{component}

## Description de la modification proposée
Modifier quelque chose.

## Score agrégé des signaux
**Total** : {score}/20{note}

## Statut (rempli lors de la review)
- [ ] GO — Intégré dans ce cycle
- [ ] NO GO — Rejeté (justification : )
- [ ] DEFER — Reporté (score augmenté de +2 au prochain cycle)

## Décision du Gardien
**Date** :
**Commentaire** :
"""


def hyp(score, component="framework", hyp_id="HYP-2026-11-11-001"):
    return Hypothesis(id=hyp_id, title="Titre", component=component, score=score)


def write(tmp_path, score="15", component="framework", note="", hyp_id="HYP-2026-11-11-001"):
    path = tmp_path / f"{hyp_id}.md"
    path.write_text(
        TEMPLATE.format(id=hyp_id, title="Titre", component=component, score=score, note=note),
        encoding="utf-8",
    )
    return path


# ── Score ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text,expected",
    [
        ("**Total** : 15/20", 15),
        ("**Total** : 14,5/20 (moyenne de 15 et 14)", 14.5),
        ("**Total** : 12.3/20", 12.3),
        ("**Total** : /20", 0),
        ("aucun score", 0),
    ],
)
def test_parse_score(text, expected):
    assert parse_score(text) == expected


def test_parse_score_ignores_signal_scores_listed_before_the_total(tmp_path):
    assert (
        parse_hypothesis(write(tmp_path, score="14,5", note=" (moyenne de 15 et 14)")).score == 14.5
    )


def test_format_score_round_trips_french_decimals():
    assert format_score(15) == "15"
    assert format_score(14.5) == "14,5"
    assert format_score(16.0) == "16"


# ── Règle de décision ────────────────────────────────────────────────────────


def test_score_strictly_above_threshold_is_go():
    assert decide_one(hyp(14.5), already_deferred=False).decision == "GO"
    assert decide_one(hyp(15), already_deferred=False).decision == "GO"


def test_score_equal_to_threshold_is_not_go():
    assert decide_one(hyp(14), already_deferred=False).decision == "DEFER"


def test_low_score_already_deferred_is_closed():
    d = decide_one(hyp(13), already_deferred=True)
    assert d.decision == "NO GO"
    assert "péremption" in d.comment


def test_deferred_hypothesis_above_threshold_is_go():
    assert decide_one(hyp(16), already_deferred=True).decision == "GO"


def test_constitution_is_never_decided_automatically():
    d = decide_one(
        hyp(19, component="constitution (Human Authorship) | framework"), already_deferred=False
    )
    assert d.decision == HOLD


def test_unreadable_score_is_held():
    assert decide_one(hyp(0), already_deferred=False).decision == HOLD


def test_guardian_override_wins_over_the_rule_in_both_directions():
    veto = decide_one(
        hyp(18), already_deferred=False, override={"decision": "NO GO", "comment": "Non."}
    )
    assert (veto.decision, veto.source, veto.comment) == ("NO GO", "gardien", "Non.")
    forced = decide_one(hyp(12), already_deferred=False, override={"decision": "GO"})
    assert (forced.decision, forced.source) == ("GO", "gardien")


def test_guardian_can_decide_a_constitutional_hypothesis():
    d = decide_one(
        hyp(13, component="constitution"), already_deferred=False, override={"decision": "GO"}
    )
    assert d.decision == "GO"


def test_invalid_override_is_rejected():
    with pytest.raises(ValueError):
        decide_one(hyp(15), already_deferred=False, override={"decision": "PEUT-ETRE"})
    with pytest.raises(ValueError):
        decide_one(hyp(15), already_deferred=False, override={"decision": "PENDING"})


def test_custom_threshold():
    assert decide_one(hyp(15), already_deferred=False, threshold=16).decision == "DEFER"


def test_build_decisions_separates_held_and_disables_defer_bonus():
    data = build_decisions(
        "2026-11-23",
        pending=[
            hyp(15, hyp_id="HYP-A"),
            hyp(13, hyp_id="HYP-B"),
            hyp(17, "constitution", "HYP-C"),
        ],
        deferred=[hyp(12, hyp_id="HYP-D")],
        overrides={"HYP-B": {"decision": "GO"}, "HYP-Z": {"decision": "GO"}},
    )
    assert {d["id"]: d["decision"] for d in data["decisions"]} == {
        "HYP-A": "GO",
        "HYP-B": "GO",
        "HYP-D": "NO GO",
    }
    assert [d["id"] for d in data["held"]] == ["HYP-C"]
    assert data["unknown_overrides"] == ["HYP-Z"]
    assert data["defer_bonus"] == 0
    json.dumps(data)  # sérialisable


def test_load_overrides(tmp_path):
    assert load_overrides(tmp_path / "absent.json") == {}
    path = tmp_path / "OVERRIDES-2026-11-23.json"
    path.write_text(
        json.dumps({"decisions": [{"id": "HYP-A", "decision": "NO GO", "comment": "x"}]})
    )
    assert load_overrides(path)["HYP-A"]["decision"] == "NO GO"


# ── Application des décisions (validate) ─────────────────────────────────────


def test_apply_decision_fills_blank_template(tmp_path):
    out = _apply_decision_to_file(write(tmp_path), Decision.GO, "GO automatique", "2026-11-23")
    assert "- [x] GO" in out and "- [ ] NO GO" in out and "- [ ] DEFER" in out
    assert "**Date** : 2026-11-23\n**Commentaire** : GO automatique" in out


def test_no_go_does_not_tick_go(tmp_path):
    out = _apply_decision_to_file(write(tmp_path), Decision.NOGO, "non", "2026-11-23")
    assert "- [ ] GO" in out and "- [x] NO GO" in out


def test_redeciding_a_deferred_hypothesis_keeps_the_previous_decision(tmp_path):
    path = write(tmp_path)
    path.write_text(
        _apply_decision_to_file(path, Decision.DEFER, "report", "2026-09-26"), encoding="utf-8"
    )
    out = _apply_decision_to_file(path, Decision.NOGO, "péremption", "2026-11-23")
    assert "- [x] NO GO" in out and "- [ ] DEFER" in out
    assert "**Date** : 2026-11-23\n**Commentaire** : péremption" in out
    assert "**Date** : 2026-09-26" in out  # trace conservée
    path.write_text(out, encoding="utf-8")
    parsed = parse_hypothesis(path)
    assert parsed.decision == Decision.NOGO
    assert parsed.decision_date == "2026-11-23"


def test_comment_with_backslash_is_written_verbatim(tmp_path):
    out = _apply_decision_to_file(write(tmp_path), Decision.GO, r"voir \1 et \g<0>", "2026-11-23")
    assert r"**Commentaire** : voir \1 et \g<0>" in out


def test_defer_bonus_handles_decimals_and_zero(tmp_path):
    path = write(tmp_path, score="14,5", note=" (moyenne de 15 et 14)")
    _bump_defer_score(path, 0)
    assert parse_hypothesis(path).score == 14.5
    _bump_defer_score(path, 2)
    assert "**Total** : 16,5/20 (moyenne de 15 et 14)" in path.read_text(encoding="utf-8")
    _bump_defer_score(path, 10)
    assert parse_hypothesis(path).score == 20
