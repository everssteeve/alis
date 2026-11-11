"""Cadence fixe du cycle ALIS (28 jours) et état local du cycle.

Depuis le 2026-11-11, le cycle n'est plus calé sur la pleine lune mais sur une
cadence fixe (`CYCLE_CADENCE_DAYS`). L'état vit hors du Drive (`state/cycle.json`)
pour rester lisible par un job launchd sans autorisation d'accès aux fichiers.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path

from .config import CYCLE_CADENCE_DAYS, CYCLE_STATE_FILE


class CycleStateError(Exception):
    """État du cycle absent ou illisible."""


@dataclass
class CycleState:
    next_cycle: date
    cadence_days: int = CYCLE_CADENCE_DAYS
    last_cycle: date | None = None
    history: list[dict] = field(default_factory=list)

    def is_due(self, today: date) -> bool:
        return today >= self.next_cycle

    def days_until(self, today: date) -> int:
        return (self.next_cycle - today).days


def next_cycle_after(scheduled: date, cadence_days: int, today: date) -> date:
    """Prochaine date de cycle après `scheduled`, strictement postérieure à `today`.

    La cadence part de la date *planifiée*, pas de la date d'exécution réelle :
    un cycle exécuté en retard ne décale pas les suivants. Si plusieurs échéances
    ont été manquées, elles sont sautées (un seul cycle rattrape tout).
    """
    if cadence_days <= 0:
        raise ValueError("cadence_days doit être strictement positif")
    nxt = scheduled + timedelta(days=cadence_days)
    while nxt <= today:
        nxt += timedelta(days=cadence_days)
    return nxt


def load_state(path: Path = CYCLE_STATE_FILE) -> CycleState:
    if not path.exists():
        raise CycleStateError(
            f"État du cycle absent : {path}. Initialiser avec `alis cycle-init --next YYYY-MM-DD`."
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return CycleState(
            next_cycle=date.fromisoformat(raw["next_cycle"]),
            cadence_days=int(raw.get("cadence_days", CYCLE_CADENCE_DAYS)),
            last_cycle=date.fromisoformat(raw["last_cycle"]) if raw.get("last_cycle") else None,
            history=list(raw.get("history", [])),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise CycleStateError(f"État du cycle illisible ({path}) : {exc}") from exc


def save_state(state: CycleState, path: Path = CYCLE_STATE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = asdict(state)
    raw["next_cycle"] = state.next_cycle.isoformat()
    raw["last_cycle"] = state.last_cycle.isoformat() if state.last_cycle else None
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def advance(state: CycleState, today: date, outcome: str, detail: str = "") -> CycleState:
    """Clôt le cycle courant et planifie le suivant."""
    done = state.next_cycle
    state.history.append(
        {
            "cycle": done.isoformat(),
            "ran_on": today.isoformat(),
            "outcome": outcome,
            "detail": detail,
        }
    )
    state.last_cycle = done
    state.next_cycle = next_cycle_after(done, state.cadence_days, today)
    return state
