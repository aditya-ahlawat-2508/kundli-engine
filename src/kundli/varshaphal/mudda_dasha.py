"""Mudda dasha: the Vimshottari cycle compressed so that one dasha year lasts 3 days (120 years = 360 days).

Basis (`EngineConfig.mudda_dasha_basis`, a convention, `# VERIFY`):
* `annual_moon` (default): the cycle starts at the year-chart instant, with the lord of the Moon's nakshatra in the
  year chart and the fraction of that nakshatra already elapsed.
* `natal_vimshottari`: the natal Vimshottari lord running at the year-chart instant and the fraction of its maha dasha
  elapsed then (the lord's first compressed period is the remainder).
The generic nested-period engine of dasha/engine.py supplies maha and antar levels.
"""
from datetime import UTC, datetime, timedelta
from typing import Any

from ..dasha import vimshottari
from ..dasha.engine import build_tree, maha_periods
from ..models import Kundli
from ..nakshatra import fraction_elapsed, nakshatra_index, nakshatra_lord
from ..timeutil import jd_to_utc

DAYS_PER_DASHA_YEAR = 3.0


def mudda_dasha(natal: Kundli, annual: Kundli, return_jd: float, basis: str, depth: int = 2) -> dict[str, Any]:
    start = jd_to_utc(return_jd).astimezone(UTC)
    tz = natal.birth["place"]["tz"]
    if basis == "annual_moon":
        moon = next(p for p in annual.planets if p.name == "Moon").sidereal_lon
        lord, elapsed = nakshatra_lord(nakshatra_index(moon)), fraction_elapsed(moon)
    elif basis == "natal_vimshottari":
        par = natal.dashas["params"]
        birth = datetime.fromisoformat(par["birth_utc"])
        running = next(m for m in vimshottari.tree(par["moon_lon"], birth, par["year_days"], 1, tz)
                       if datetime.fromisoformat(m["start_utc"]) <= start < datetime.fromisoformat(m["end_utc"]))
        lord = running["lord"]
        elapsed = (start - datetime.fromisoformat(running["start_utc"])).total_seconds() / (running["days"] * 86400.0)
    else:
        raise ValueError(f"unknown mudda_dasha_basis {basis!r}")
    periods = maha_periods(vimshottari.VIMSHOTTARI, vimshottari.VIMSHOTTARI.index(lord), elapsed, start, DAYS_PER_DASHA_YEAR)
    tree = build_tree(vimshottari.VIMSHOTTARI, periods, depth, tz)
    first_days = tree[0]["days"]
    # The first period began before the year chart: its active part is the balance. The 360-day year is closed by the
    # elapsed part of the first lord (the cycle is 360 days, the year-chart instant is inside the first period).
    tree[0]["active_from_utc"] = start.isoformat(timespec="seconds")
    tree[0]["balance_days"] = (1.0 - elapsed) * first_days
    closing_start = datetime.fromisoformat(tree[-1]["end_utc"])
    closing = {"lord": lord, "start_utc": closing_start.isoformat(timespec="seconds"),
               "end_utc": (closing_start + timedelta(days=elapsed * first_days)).isoformat(timespec="seconds"),
               "days": elapsed * first_days}
    return {"basis": basis, "start_lord": lord, "elapsed_fraction": elapsed, "days_per_dasha_year": DAYS_PER_DASHA_YEAR,
            "year_start_utc": start.isoformat(timespec="seconds"),
            "year_end_utc": (start + timedelta(days=360.0)).isoformat(timespec="seconds"),
            "periods": tree, "closing_remainder": closing, "tables_verified": False}


__all__ = ["DAYS_PER_DASHA_YEAR", "mudda_dasha"]
