"""Vimshottari dasha (120-year cycle) from the Moon's nakshatra."""
from datetime import datetime

from ..data.tables import VIM_ORDER, VIM_YEARS
from ..nakshatra import fraction_elapsed, nakshatra_index, nakshatra_lord
from .engine import System, build_tree, maha_periods, stack_at
from .engine import descend as descend_periods

VIMSHOTTARI = System("vimshottari", tuple((p, float(VIM_YEARS[p])) for p in VIM_ORDER))


def periods(moon_lon: float, birth_utc: datetime, year_days: float):
    lord = nakshatra_lord(nakshatra_index(moon_lon))
    return maha_periods(VIMSHOTTARI, VIMSHOTTARI.index(lord), fraction_elapsed(moon_lon), birth_utc, year_days)


def balance_at_birth(moon_lon: float, year_days: float) -> dict:
    """Balance of the first maha dasha = (1 - fraction elapsed) x lord's years."""
    lord = nakshatra_lord(nakshatra_index(moon_lon))
    years = (1 - fraction_elapsed(moon_lon)) * VIM_YEARS[lord]
    return {"lord": lord, "years": years, "days": years * year_days}


def tree(moon_lon: float, birth_utc: datetime, year_days: float, depth: int, tz: str) -> list[dict]:
    return build_tree(VIMSHOTTARI, periods(moon_lon, birth_utc, year_days), depth, tz)


def stack(moon_lon: float, birth_utc: datetime, year_days: float, as_of: datetime, levels: int, tz: str):
    return stack_at(VIMSHOTTARI, periods(moon_lon, birth_utc, year_days), as_of, levels, tz)


def descend(moon_lon: float, birth_utc: datetime, year_days: float, path: list[str], tz: str, depth: int = 1) -> dict:
    return descend_periods(VIMSHOTTARI, periods(moon_lon, birth_utc, year_days), path, tz, depth)
