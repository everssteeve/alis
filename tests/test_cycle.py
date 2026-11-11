from datetime import date

import pytest

from alis.cycle import (
    CycleState,
    CycleStateError,
    advance,
    load_state,
    next_cycle_after,
    save_state,
)


def test_next_cycle_is_scheduled_date_plus_cadence():
    assert next_cycle_after(date(2026, 11, 23), 28, today=date(2026, 11, 23)) == date(2026, 12, 21)


def test_late_run_does_not_shift_the_cadence():
    # Cycle du 23/11 exécuté le 26/11 : le suivant reste le 21/12.
    assert next_cycle_after(date(2026, 11, 23), 28, today=date(2026, 11, 26)) == date(2026, 12, 21)


def test_missed_cycles_are_skipped_not_replayed():
    # Machine éteinte deux mois : un seul cycle rattrape, le suivant est dans le futur.
    assert next_cycle_after(date(2026, 11, 23), 28, today=date(2027, 1, 20)) == date(2027, 2, 15)


def test_next_cycle_is_strictly_after_today():
    assert next_cycle_after(date(2026, 11, 23), 28, today=date(2026, 12, 21)) == date(2027, 1, 18)


def test_invalid_cadence_is_rejected():
    with pytest.raises(ValueError):
        next_cycle_after(date(2026, 11, 23), 0, today=date(2026, 11, 23))


def test_is_due():
    state = CycleState(next_cycle=date(2026, 11, 23))
    assert not state.is_due(date(2026, 11, 22))
    assert state.is_due(date(2026, 11, 23))
    assert state.is_due(date(2026, 11, 30))
    assert state.days_until(date(2026, 11, 11)) == 12


def test_advance_records_history_and_round_trips(tmp_path):
    path = tmp_path / "cycle.json"
    state = advance(
        CycleState(next_cycle=date(2026, 11, 23)), date(2026, 11, 23), "released", "v1.10"
    )
    save_state(state, path)
    loaded = load_state(path)
    assert loaded.last_cycle == date(2026, 11, 23)
    assert loaded.next_cycle == date(2026, 12, 21)
    assert loaded.history == [
        {"cycle": "2026-11-23", "ran_on": "2026-11-23", "outcome": "released", "detail": "v1.10"}
    ]


def test_missing_or_corrupt_state_raises(tmp_path):
    with pytest.raises(CycleStateError):
        load_state(tmp_path / "absent.json")
    bad = tmp_path / "bad.json"
    bad.write_text('{"next_cycle": "pas-une-date"}')
    with pytest.raises(CycleStateError):
        load_state(bad)
