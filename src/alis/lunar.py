"""Calcul des dates de pleine lune pour le calendrier ALIS."""

from datetime import date, timedelta

import ephem


def next_full_moon(from_date: date | None = None) -> date:
    """Retourne la prochaine date de pleine lune après from_date."""
    if from_date is None:
        from_date = date.today()

    # ephem travaille avec des objets Date — on part du lendemain à minuit
    start = ephem.Date(from_date.strftime("%Y/%m/%d"))
    next_fm = ephem.next_full_moon(start)
    return ephem.Date(next_fm).datetime().date()


def briefing_date(full_moon: date) -> date:
    """J-3 avant la pleine lune."""
    return full_moon - timedelta(days=3)


def scoring_date(full_moon: date) -> date:
    """J-7 avant la pleine lune."""
    return full_moon - timedelta(days=7)


def cycle_label(full_moon: date) -> str:
    return full_moon.strftime("%Y-%m-%d")
