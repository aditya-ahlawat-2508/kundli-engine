"""Yogini dasha (36-year cycle, 8 yoginis)."""
from datetime import datetime, timedelta

from ..data.tables import YOGINI
from ..nakshatra import fraction_elapsed, nakshatra_index
from .engine import System, build_tree, maha_periods, stack_at
from .engine import descend as descend_periods

YOGINI_SYS = System("yogini", tuple((lord, float(y)) for _, lord, y in YOGINI))
YOGINI_NAMES = {lord: name for name, lord, _ in YOGINI}


def start_index(moon_lon: float) -> int:
    """(nakshatra number 1..27 + 3) mod 8, zero meaning the 8th (Sankata); returned as 0-based cycle index."""
    n = nakshatra_index(moon_lon) + 1
    r = (n + 3) % 8
    return (r or 8) - 1


def periods(moon_lon: float, birth_utc: datetime, year_days: float, cycle: int = 1):
    """Maha periods of the 36-year cycle number `cycle` (1 = the cycle containing birth). Later cycles repeat the
    same eight yoginis in the same order."""
    base = maha_periods(YOGINI_SYS, start_index(moon_lon), fraction_elapsed(moon_lon), birth_utc, year_days)
    shift = timedelta(days=(cycle - 1) * YOGINI_SYS.total * year_days)
    return [(i, t + shift, d) for i, t, d in base]


def tree(moon_lon: float, birth_utc: datetime, year_days: float, depth: int, tz: str) -> list[dict]:
    t = build_tree(YOGINI_SYS, periods(moon_lon, birth_utc, year_days), depth, tz)

    def label(nodes: list[dict]) -> None:
        for n in nodes:
            n["yogini"] = YOGINI_NAMES[n["lord"]]
            label(n.get("children", []))

    label(t)
    return t


def cycle_at(moon_lon: float, birth_utc: datetime, year_days: float, as_of: datetime) -> int:
    """Number (1-based) of the 36-year cycle running at `as_of`; the cycles repeat for life."""
    start = periods(moon_lon, birth_utc, year_days)[0][1]
    return max(1, int((as_of - start) / timedelta(days=YOGINI_SYS.total * year_days)) + 1)


def stack(moon_lon: float, birth_utc: datetime, year_days: float, as_of: datetime, levels: int, tz: str):
    cycle = cycle_at(moon_lon, birth_utc, year_days, as_of)
    s = stack_at(YOGINI_SYS, periods(moon_lon, birth_utc, year_days, cycle), as_of, levels, tz)
    for n in s:
        n["yogini"] = YOGINI_NAMES[n["lord"]]
    return s


def descend(moon_lon: float, birth_utc: datetime, year_days: float, path: list[str], tz: str, depth: int = 1,
            cycle: int = 1) -> dict:
    """Sub-periods under the yogini `path` (names such as 'Mangala' or lord names such as 'Moon')."""
    by_name = {name.lower(): lord for lord, name in YOGINI_NAMES.items()}
    lords = [by_name.get(p.strip().lower(), p) for p in path]
    out = descend_periods(YOGINI_SYS, periods(moon_lon, birth_utc, year_days, cycle), lords, tz, depth)

    def label(nodes: list[dict]) -> None:
        for n in nodes:
            n["yogini"] = YOGINI_NAMES[n["lord"]]
            label(n.get("children", []))

    label([out["parent"], *out["children"]])
    return out
