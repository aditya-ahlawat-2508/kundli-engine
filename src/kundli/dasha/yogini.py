"""Yogini dasha (36-year cycle, 8 yoginis)."""
from datetime import datetime

from ..data.tables import YOGINI
from ..nakshatra import fraction_elapsed, nakshatra_index
from .engine import System, build_tree, maha_periods, stack_at

YOGINI_SYS = System("yogini", tuple((lord, float(y)) for _, lord, y in YOGINI))
YOGINI_NAMES = {lord: name for name, lord, _ in YOGINI}


def start_index(moon_lon: float) -> int:
    """(nakshatra number 1..27 + 3) mod 8, zero meaning the 8th (Sankata); returned as 0-based cycle index."""
    n = nakshatra_index(moon_lon) + 1
    r = (n + 3) % 8
    return (r or 8) - 1


def periods(moon_lon: float, birth_utc: datetime, year_days: float):
    return maha_periods(YOGINI_SYS, start_index(moon_lon), fraction_elapsed(moon_lon), birth_utc, year_days)


def tree(moon_lon: float, birth_utc: datetime, year_days: float, depth: int, tz: str) -> list[dict]:
    t = build_tree(YOGINI_SYS, periods(moon_lon, birth_utc, year_days), depth, tz)

    def label(nodes: list[dict]) -> None:
        for n in nodes:
            n["yogini"] = YOGINI_NAMES[n["lord"]]
            label(n.get("children", []))

    label(t)
    return t


def stack(moon_lon: float, birth_utc: datetime, year_days: float, as_of: datetime, levels: int, tz: str):
    s = stack_at(YOGINI_SYS, periods(moon_lon, birth_utc, year_days), as_of, levels, tz)
    for n in s:
        n["yogini"] = YOGINI_NAMES[n["lord"]]
    return s
