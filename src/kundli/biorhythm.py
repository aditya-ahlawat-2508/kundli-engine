"""Biorhythm: three sine cycles counted from the birth date: physical 23 days, emotional 28 days, intellectual 33 days.

value(t) = sin(2 pi t / period) with t = whole days from the birth date (local civil dates, birth date = day 0). A day is
`critical` when the value crosses zero between day t and t+1 (or is exactly 0). ENTERTAINMENT ONLY: biorhythm has no
scientific support. `moon_biorhythm` is NOT implemented: its definition could not be confirmed (docs/open_questions.md).
"""
import math
from datetime import date, timedelta
from typing import Any

PERIODS = {"physical": 23, "emotional": 28, "intellectual": 33}
DISCLAIMER = "Entertainment only: biorhythm has no scientific support."
MAX_SERIES_DAYS = 62


def value(days: int, period: int) -> float:
    return math.sin(2.0 * math.pi * days / period)


def biorhythm(birth: date, on: date) -> dict[str, Any]:
    t = (on - birth).days
    if t < 0:
        raise ValueError("the date is before birth")
    cycles = {}
    for name, p in PERIODS.items():
        v, nxt = value(t, p), value(t + 1, p)
        cycles[name] = {"period_days": p, "day_in_cycle": t % p, "value": v, "percent": 100.0 * v,
                        "phase": "rising" if nxt > v else "falling", "critical": v == 0.0 or v * nxt < 0.0}
    return {"date": on.isoformat(), "days_since_birth": t, "cycles": cycles, "disclaimer": DISCLAIMER}


def biorhythm_series(birth: date, start: date, end: date) -> list[dict[str, Any]]:
    if end < start:
        raise ValueError("end date is before start date")
    if (end - start).days + 1 > MAX_SERIES_DAYS:
        raise ValueError(f"at most {MAX_SERIES_DAYS} days per series")
    return [biorhythm(birth, start + timedelta(days=i)) for i in range((end - start).days + 1)]


__all__ = ["DISCLAIMER", "MAX_SERIES_DAYS", "PERIODS", "biorhythm", "biorhythm_series", "value"]
