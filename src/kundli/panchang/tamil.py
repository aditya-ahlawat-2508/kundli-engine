"""Tamil solar calendar: month = the Sun's sidereal sign, day 1 = the civil day of the sankranti (ingress).

Sunset rule (`sankranti_before_sunset`, the only rule implemented; regional variants exist and are listed in
docs/open_questions.md): if the Sun enters a new sign at or before sunset on civil date C, C is day 1 of the new
month; if after sunset, the next civil date is day 1. The Tamil year name (60-year cycle) is not implemented.
"""
from datetime import date, timedelta
from zoneinfo import ZoneInfo

import swisseph as swe

from ..config import EngineConfig
from ..ephemeris import base_flags
from ..timeutil import jd_to_utc
from .spans import sun_moon
from .sun_moon_times import local_iso, rise_args, sun_day

TAMIL_MONTHS = ["Chithirai", "Vaikasi", "Aani", "Aadi", "Aavani", "Purattasi", "Aippasi", "Karthigai", "Margazhi",
                "Thai", "Maasi", "Panguni"]  # Mesha..Meena
RULE = "sankranti_before_sunset"


def sun_sign(jd: float, ayanamsa: str, eph: int) -> int:
    return int(sun_moon(jd, ayanamsa, eph)[0] // 30)


def last_ingress(jd: float, ayanamsa: str = "lahiri", eph: int = swe.FLG_MOSEPH) -> tuple[float, int]:
    """(JD of the latest sign ingress at or before `jd`, the sign index entered)."""
    sign = sun_sign(jd, ayanamsa, eph)
    hi, lo = jd, jd
    for _ in range(40):  # the Sun stays in a sign at most ~32 days
        lo = hi - 1.0
        if sun_sign(lo, ayanamsa, eph) != sign:
            break
        hi = lo
    else:
        raise RuntimeError("no ingress found")
    a, b = lo, hi  # sign differs at a, equals `sign` at b
    while b - a > 1e-8:
        mid = (a + b) / 2.0
        a, b = (mid, b) if sun_sign(mid, ayanamsa, eph) != sign else (a, mid)
    return (a + b) / 2.0, sign


def tamil_calendar(d: date, lat: float, lon: float, tz: str, cfg: EngineConfig) -> dict:
    ra = rise_args(cfg)
    ev = sun_day(d, lat, lon, tz, **ra)
    if ev is None:
        raise ValueError("no sunset on this date at this latitude; the Tamil civil day is undefined")
    eph = base_flags(cfg)
    ing, sign = last_ingress(ev["sunset"], cfg.ayanamsa, eph)
    zi = ZoneInfo(tz)
    c = jd_to_utc(ing).astimezone(zi).date()
    ev_c = sun_day(c, lat, lon, tz, **ra)
    if ev_c is None:
        raise ValueError("no sunset on the ingress date; the Tamil civil day is undefined")
    first = c if ing <= ev_c["sunset"] else c + timedelta(days=1)
    return {"month": TAMIL_MONTHS[sign], "month_number": sign + 1, "day": (d - first).days + 1,
            "month_start_date": first.isoformat(), "sankranti_local": local_iso(ing, tz), "sankranti_jd": ing,
            "rule": RULE}


__all__ = ["TAMIL_MONTHS", "last_ingress", "tamil_calendar"]
