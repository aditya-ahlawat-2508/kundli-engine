"""One-call panchang for a moment: elements with exact spans, rise/set, hora, choghadiya, inauspicious periods,
Hindu and Tamil calendar. This is the shared source for the compat Panchang endpoints."""
from datetime import date
from zoneinfo import ZoneInfo

from ..config import EngineConfig
from ..data.tables import WEEKDAY_LORDS
from ..ephemeris import base_flags
from ..timeutil import jd_to_utc
from .choghadiya import choghadiya_table
from .core import hindu_month, sun_events, vara_index
from .festivals import festivals_on
from .hora import hora_table
from .inauspicious import inauspicious_periods
from .spans import element_spans
from .sun_moon_times import day_times, local_iso, rise_args, sun_day
from .tamil import tamil_calendar


def sunrise_jd(d: date, lat: float, lon: float, tz: str, cfg: EngineConfig) -> float:
    """JD of the sunrise of civil date `d` (the `/sunrise` endpoint variants evaluate at this instant)."""
    sd = sun_day(d, lat, lon, tz, **rise_args(cfg))
    if sd is None:
        raise ValueError("no sunrise on this date at this latitude")
    return sd["sunrise"]


def day_panchang(jd_ut: float, lat: float, lon: float, tz: str, cfg: EngineConfig) -> dict:
    eph = base_flags(cfg)
    ra = rise_args(cfg)
    out: dict = {"moment_local": local_iso(jd_ut, tz), "conventions": {
        "sunrise_definition": cfg.sunrise_definition, "ayanamsa": cfg.ayanamsa, "observer_altitude_m": cfg.observer_altitude_m}}
    out["elements"] = element_spans(jd_ut, tz, cfg.ayanamsa, eph)
    ev = sun_events(jd_ut, lat, lon, **ra)
    civil = jd_to_utc(jd_ut).astimezone(ZoneInfo(tz)).date()
    if ev is None:
        out["vara"] = {"index": (civil.weekday() + 1) % 7, "name": WEEKDAY_LORDS[(civil.weekday() + 1) % 7],
                       "note": "no sunrise at this latitude; civil weekday used"}
        out["rise_set"] = day_times(civil, lat, lon, tz, cfg)
        return out
    d_idx = vara_index(ev["sunrise"], tz)
    day = jd_to_utc(ev["sunrise"]).astimezone(ZoneInfo(tz)).date()
    out["vara"] = {"index": d_idx, "name": WEEKDAY_LORDS[d_idx]}
    out["rise_set"] = day_times(day, lat, lon, tz, cfg)
    out["hora"] = hora_table(ev, d_idx, tz)
    out["choghadiya"] = choghadiya_table(ev, d_idx, tz)
    out["inauspicious"] = inauspicious_periods(ev, d_idx, tz)
    out["hindu_month"] = hindu_month(jd_ut, cfg.ayanamsa, eph)
    out["tamil"] = tamil_calendar(day, lat, lon, tz, cfg)
    out["festivals"] = festivals_on(day, lat, lon, tz, cfg)
    return out


__all__ = ["day_panchang", "sunrise_jd"]
