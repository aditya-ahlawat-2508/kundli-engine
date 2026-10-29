"""Sunrise, sunset, moonrise, moonset via swe.rise_trans.

The rise/set definition is a convention (`EngineConfig.sunrise_definition`), never hard-coded:
* ``upper_limb_refracted``: first visible edge of the disc, standard refraction (Indian panchang practice and
  the default of Swiss Ephemeris; flags = 0).
* ``center_no_refraction``: geometric centre of the disc on the horizon, no refraction
  (``BIT_DISC_CENTER | BIT_NO_REFRACTION``).
Atmospheric pressure/temperature are passed as 0, so swisseph uses its standard-atmosphere estimate. The observer
altitude (metres) is `EngineConfig.observer_altitude_m`; swisseph uses it only to estimate refraction (it applies
no horizon dip), so its effect is a few tens of seconds.
"""
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import swisseph as swe

from ..config import EngineConfig
from ..ephemeris import base_flags
from ..timeutil import jd_to_utc, julian_day

DEFINITION_BITS = {
    "upper_limb_refracted": 0,
    "center_no_refraction": swe.BIT_DISC_CENTER | swe.BIT_NO_REFRACTION,
}


def rise_args(cfg: EngineConfig) -> dict[str, Any]:
    """Keyword arguments (`eph`, `bits`, `alt`) shared by every rise/set consumer."""
    return {"eph": base_flags(cfg), "bits": DEFINITION_BITS[cfg.sunrise_definition], "alt": cfg.observer_altitude_m}


def rise_set(jd_start: float, lat: float, lon: float, which: int, eph: int = swe.FLG_MOSEPH, bits: int = 0,
             alt: float = 0.0, body: int = swe.SUN) -> float | None:
    """First rise (`which=swe.CALC_RISE`) or set (`swe.CALC_SET`) of `body` after `jd_start`; None if none occurs
    (polar day/night) or swisseph cannot compute it."""
    try:
        flag, tret = swe.rise_trans(jd_start, body, which | eph | bits, (lon, lat, alt), 0.0, 0.0)
    except swe.Error:
        return None
    return tret[0] if flag == 0 else None


def local_midnight_jd(d: date, tz: str) -> float:
    """JD (UT) of 00:00 local civil time on `d` (the first valid instant of the day if midnight is skipped)."""
    local = datetime.combine(d, time(0, 0)).replace(tzinfo=ZoneInfo(tz))
    return julian_day(local.astimezone(ZoneInfo("UTC")))[1]


def sun_day(d: date, lat: float, lon: float, tz: str, **ra: Any) -> dict | None:
    """Sunrise, sunset and next sunrise (JDs) of the civil date `d`: the first sunrise at or after local midnight.
    None at latitudes where the Sun does not rise or set that day."""
    from .core import sun_events

    start = local_midnight_jd(d, tz)
    rise = rise_set(start, lat, lon, swe.CALC_RISE, **ra)
    if rise is None or rise >= start + 1.0:
        return None
    return sun_events(rise + 1e-6, lat, lon, **ra)


def moon_day(d: date, lat: float, lon: float, tz: str, **ra: Any) -> dict[str, float | None]:
    """Moonrise and moonset falling on the civil date `d` (None when the Moon does not rise/set that date)."""
    start = local_midnight_jd(d, tz)
    out: dict[str, float | None] = {}
    for key, which in (("moonrise", swe.CALC_RISE), ("moonset", swe.CALC_SET)):
        t = rise_set(start, lat, lon, which, body=swe.MOON, **ra)
        out[key] = t if t is not None and t < start + 1.0 else None
    return out


def local_iso(jd: float | None, tz: str) -> str | None:
    return None if jd is None else jd_to_utc(jd).astimezone(ZoneInfo(tz)).isoformat(timespec="seconds")


def day_times(d: date, lat: float, lon: float, tz: str, cfg: EngineConfig) -> dict[str, Any]:
    """Sunrise/sunset/moonrise/moonset for a civil date with the definition used, local ISO strings plus JDs."""
    ra = rise_args(cfg)
    sun = sun_day(d, lat, lon, tz, **ra)
    moon = moon_day(d, lat, lon, tz, **ra)
    return {
        "date": d.isoformat(),
        "sunrise": local_iso(sun["sunrise"], tz) if sun else None,
        "sunset": local_iso(sun["sunset"], tz) if sun else None,
        "moonrise": local_iso(moon["moonrise"], tz),
        "moonset": local_iso(moon["moonset"], tz),
        "sunrise_jd": sun["sunrise"] if sun else None,
        "sunset_jd": sun["sunset"] if sun else None,
        "next_sunrise_jd": sun["next_sunrise"] if sun else None,
        "definition": cfg.sunrise_definition,
        "observer_altitude_m": cfg.observer_altitude_m,
        "note": None if sun else "no sunrise/sunset at this latitude on this date",
    }


__all__ = ["DEFINITION_BITS", "day_times", "local_iso", "local_midnight_jd", "moon_day", "rise_args", "rise_set",
           "sun_day"]
