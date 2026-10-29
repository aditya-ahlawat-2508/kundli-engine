"""Solar return (Varsha Pravesha) and the monthly progression (Masa Pravesha), by root-finding on the Sun.

* Year chart: the instant in `year` when the Sun returns to its natal longitude. `solar_return_zodiac` decides which
  longitude must return: `sidereal` (default, the configured ayanamsa) or `tropical` (the Sun's natal tropical
  longitude; the instants differ by about 20 minutes per year). The chart itself is always cast in the configured
  sidereal zodiac.
* Month chart n (1..12): the instant after the year chart when the Sun has advanced (n-1) x 30 degrees from its natal
  longitude (month 1 is the year chart).
Bisection runs to ~1 ms; the engine never reads the clock.
"""
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import swisseph as swe

from ..chart import generate
from ..config import EngineConfig
from ..ephemeris import base_flags
from ..models import BirthInput, Kundli
from ..timeutil import jd_to_utc
from ..transits import _cfg, jd_of, sid_lon


def _sun(jd: float, cfg: EngineConfig) -> float:
    if cfg.solar_return_zodiac == "tropical":
        return swe.calc_ut(jd, swe.SUN, base_flags(cfg))[0][0] % 360.0
    return sid_lon("Sun", jd, cfg)


def _natal_sun(k: Kundli, cfg: EngineConfig) -> float:
    sun = next(p for p in k.planets if p.name == "Sun")
    return sun.tropical_lon if cfg.solar_return_zodiac == "tropical" else sun.sidereal_lon


def _find(target: float, guess: float, cfg: EngineConfig, half_window: float = 3.0) -> float:
    def f(jd: float) -> float:
        return (_sun(jd, cfg) - target + 180.0) % 360.0 - 180.0

    lo, hi = guess - half_window, guess + half_window
    if f(lo) > 0 or f(hi) < 0:
        raise RuntimeError("Sun crossing not bracketed")
    for _ in range(50):
        mid = (lo + hi) / 2.0
        lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
    return (lo + hi) / 2.0


def _anniversary_guess(k: Kundli, year: int) -> float:
    birth = datetime.fromisoformat(k.birth["utc"])
    day = 28 if (birth.month == 2 and birth.day == 29) else birth.day
    return jd_of(birth.replace(year=year, day=day))


def return_jd(k: Kundli, year: int, month: int = 1) -> float:
    """JD (UT) of the year chart (month 1) or of month chart `month` (1..12) of the year starting in `year`."""
    if not 1 <= month <= 12:
        raise ValueError("month must be 1..12")
    cfg = _cfg(k)
    jd0 = _find(_natal_sun(k, cfg), _anniversary_guess(k, year), cfg)
    if month == 1:
        return jd0
    target = (_natal_sun(k, cfg) + 30.0 * (month - 1)) % 360.0
    return _find(target, jd0 + 30.4368 * (month - 1), cfg, 4.0)


def kundli_at(k: Kundli, jd: float) -> Kundli:
    """The chart for instant `jd` at the birth place (same configuration), time rounded to the second."""
    cfg = _cfg(k)
    p = k.birth["place"]
    utc = jd_to_utc(jd)
    local = utc.astimezone(ZoneInfo(p["tz"]))
    local = local.replace(microsecond=0)
    birth = BirthInput(name=k.birth["name"], date=local.date(), time=local.time(), place=p, fold=local.fold)
    return generate(birth, cfg)


def annual_chart(k: Kundli, year: int, month: int = 1) -> tuple[Kundli, float]:
    """(Kundli for the year or month chart, its JD). Needs a known birth time (the natal lagna drives Muntha)."""
    if k.birth.get("time_unknown"):
        raise ValueError("Varshaphal needs a known birth time")
    jd = return_jd(k, year, month)
    return kundli_at(k, jd), jd


def solar_return(k: Kundli, year: int) -> dict[str, Any]:
    """Summary of the year chart: moment, age, annual lagna, planet longitudes and Muntha."""
    from .muntha import muntha

    a, jd = annual_chart(k, year)
    birth = datetime.fromisoformat(k.birth["utc"])
    age = year - birth.year
    return {"year": year, "age": age, "planets": {p.name: {"sign": p.sign, "longitude": p.sidereal_lon} for p in a.planets},
            "muntha": muntha(k, a, age), "jd_ut": jd, "utc": jd_to_utc(jd).isoformat(timespec="seconds"),
            "local": a.birth["local"], "lagna_sign": a.lagna["sign"] if a.lagna else None,
            "lagna_sign_name": a.lagna["sign_name"] if a.lagna else None,
            "lagna_longitude": a.lagna["longitude"] if a.lagna else None, "zodiac_returned": _cfg(k).solar_return_zodiac}


__all__ = ["annual_chart", "kundli_at", "return_jd", "solar_return"]
