"""Panchang: tithi, vara, nakshatra, yoga, karana, sunrise/sunset, hora, choghadiya, moon phase."""
import math
from zoneinfo import ZoneInfo

import swisseph as swe

from ..data.tables import (
    CHALDEAN,
    CHOGHADIYA_CYCLE,
    CHOGHADIYA_QUALITY,
    CHOGHADIYA_START,
    KARANA_FIXED,
    KARANA_MOVABLE,
    NAK_SPAN,
    NAKSHATRAS,
    TITHI_NAMES,
    WEEKDAY_LORDS,
    YOGA_NAMES,
)
from ..timeutil import jd_to_utc
from .sun_moon_times import rise_set


def tithi(sun: float, moon: float) -> tuple[int, str, str]:
    """(number 1..30, name, paksha). 12 degrees of Moon-Sun elongation each."""
    n = int(((moon - sun) % 360.0) // 12.0) + 1
    paksha = "shukla" if n <= 15 else "krishna"
    k = (n - 1) % 15
    name = "Purnima" if n == 15 else "Amavasya" if n == 30 else TITHI_NAMES[k]
    return n, name, paksha


def yoga(sun_sid: float, moon_sid: float) -> tuple[int, str]:
    """Nitya yoga: (sidereal Sun + Moon) / 13deg20'."""
    n = int(((sun_sid + moon_sid) % 360.0) // NAK_SPAN)
    return n + 1, YOGA_NAMES[n]


def karana(sun: float, moon: float) -> tuple[int, str]:
    """60 karanas per lunar month (6 degrees each): Kimstughna, 7 movable x8, Shakuni, Chatushpada, Naga."""
    i = int(((moon - sun) % 360.0) // 6.0)
    return i + 1, KARANA_FIXED.get(i, KARANA_MOVABLE[(i - 1) % 7])


def moon_illumination(sun: float, moon: float) -> float:
    return (1 - math.cos(math.radians((moon - sun) % 360.0))) / 2


def sun_events(jd_ut: float, lat: float, lon: float, eph: int = swe.FLG_MOSEPH, bits: int = 0,
               alt: float = 0.0) -> dict | None:
    """Sunrise at/before jd_ut, the following sunset and next sunrise (JDs); None if the Sun does not
    rise/set (polar). Upper limb with standard refraction (the Indian panchang convention)."""
    rise = rise_set(jd_ut - 1.0, lat, lon, swe.CALC_RISE, eph, bits, alt)
    if rise is None:
        return None
    nxt: float | None = None
    for _ in range(3):
        nxt = rise_set(rise + 0.01, lat, lon, swe.CALC_RISE, eph, bits, alt)
        if nxt is None:
            return None
        if nxt > jd_ut:
            break
        rise = nxt
    sset = rise_set(rise, lat, lon, swe.CALC_SET, eph, bits, alt)
    if nxt is None:
        return None
    if sset is None or not (rise < jd_ut or abs(rise - jd_ut) < 1e-9):
        return None
    # Polar day/night: swisseph can return a degenerate pair instead of "no event". Require a sane day.
    if not (rise + 0.02 < sset < nxt - 0.02) or not (0.9 < nxt - rise < 1.1) or not (0.02 < sset - rise < 0.98):
        return None
    return {"sunrise": rise, "sunset": sset, "next_sunrise": nxt}


def vara_index(sunrise_jd: float, tz: str) -> int:
    """Vedic weekday (0=Sunday) of the day beginning at this sunrise, by local civil date."""
    local = jd_to_utc(sunrise_jd).astimezone(ZoneInfo(tz))
    return (local.weekday() + 1) % 7


def hora_lord(jd_ut: float, ev: dict, day_idx: int) -> tuple[str, int]:
    """Hora lord and hora number (1..24). Day and night are each divided into 12 equal horas; lords run in
    Chaldean order starting from the weekday lord."""
    if jd_ut < ev["sunset"]:
        n = int((jd_ut - ev["sunrise"]) / ((ev["sunset"] - ev["sunrise"]) / 12.0))
    else:
        n = 12 + int((jd_ut - ev["sunset"]) / ((ev["next_sunrise"] - ev["sunset"]) / 12.0))
    n = min(n, 23)
    start = CHALDEAN.index(WEEKDAY_LORDS[day_idx])
    return CHALDEAN[(start + n) % 7], n + 1


def choghadiya(jd_ut: float, ev: dict, day_idx: int) -> dict | None:
    """Daytime choghadiya (8 parts of sunrise-sunset). Night parts not provided (None)."""
    if not (ev["sunrise"] <= jd_ut < ev["sunset"]):
        return None
    k = int((jd_ut - ev["sunrise"]) / ((ev["sunset"] - ev["sunrise"]) / 8.0))
    name = CHOGHADIYA_CYCLE[(CHOGHADIYA_START[day_idx] + min(k, 7)) % 7]
    return {"name": name, "quality": CHOGHADIYA_QUALITY[name], "part": min(k, 7) + 1}


def panchang(jd_ut: float, sun_sid: float, moon_sid: float, lat: float, lon: float, tz: str,
             eph: int = swe.FLG_MOSEPH, bits: int = 0, alt: float = 0.0) -> dict:
    t_n, t_name, paksha = tithi(sun_sid, moon_sid)
    y_n, y_name = yoga(sun_sid, moon_sid)
    k_n, k_name = karana(sun_sid, moon_sid)
    nak = int(moon_sid // NAK_SPAN)
    out: dict = {
        "tithi": {"number": t_n, "name": t_name, "paksha": paksha},
        "nakshatra": {"index": nak, "name": NAKSHATRAS[nak]},
        "yoga": {"number": y_n, "name": y_name},
        "karana": {"number": k_n, "name": k_name},
        "moon_illumination": moon_illumination(sun_sid, moon_sid),
        "sun_events": None,
    }
    ev = sun_events(jd_ut, lat, lon, eph, bits, alt)
    if ev is None:
        local = jd_to_utc(jd_ut).astimezone(ZoneInfo(tz))
        out["vara"] = {"index": (local.weekday() + 1) % 7, "name": WEEKDAY_LORDS[(local.weekday() + 1) % 7],
                       "note": "no sunrise at this latitude; civil weekday used"}
        return out
    d = vara_index(ev["sunrise"], tz)
    hl, hn = hora_lord(jd_ut, ev, d)
    zi = ZoneInfo(tz)

    def loc(j: float) -> str:
        return jd_to_utc(j).astimezone(zi).isoformat(timespec="seconds")

    out["vara"] = {"index": d, "name": WEEKDAY_LORDS[d]}
    out["sun_events"] = {"sunrise_jd": ev["sunrise"], "sunset_jd": ev["sunset"],
                         "next_sunrise_jd": ev["next_sunrise"], "sunrise_local": loc(ev["sunrise"]),
                         "sunset_local": loc(ev["sunset"])}
    out["hora"] = {"lord": hl, "number": hn}
    out["choghadiya"] = choghadiya(jd_ut, ev, d)
    return out




# ---- Hindu lunar month (amanta) ----------------------------------------------------------------------
MONTH_BY_SUN_SIGN = ["Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada", "Ashwin", "Kartik",
                     "Margashirsha", "Pausha", "Magha", "Phalguna", "Chaitra"]  # Sun's sidereal sign at the new moon
_MOON_DAILY = 12.1908  # mean elongation gain, degrees/day


def _elong(jd: float, eph: int = swe.FLG_MOSEPH) -> float:
    s = swe.calc_ut(jd, swe.SUN, eph)[0][0]
    m = swe.calc_ut(jd, swe.MOON, eph)[0][0]
    return (m - s) % 360.0


def _new_moon_near(guess: float, eph: int = swe.FLG_MOSEPH) -> float:
    def f(j: float) -> float:
        return (_elong(j, eph) + 180.0) % 360.0 - 180.0

    lo, hi = guess - 3.0, guess + 3.0
    for _ in range(50):
        mid = (lo + hi) / 2.0
        lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
    return (lo + hi) / 2.0


def hindu_month(jd_ut: float, ayanamsa: str = "lahiri", eph: int = swe.FLG_MOSEPH) -> dict:
    """Amanta lunar month: named by the Sun's sidereal sign at the preceding new moon. If the Sun is in the same
    sign at the preceding and the following new moon (no sankranti in between) the month is Adhika."""
    from ..ayanamsa import to_sidereal

    e = _elong(jd_ut, eph)
    prev = _new_moon_near(jd_ut - e / _MOON_DAILY, eph)
    nxt = _new_moon_near(prev + 29.53, eph)

    def sun_sign(j: float) -> int:
        return int(to_sidereal(swe.calc_ut(j, swe.SUN, eph)[0][0], j, ayanamsa) // 30)

    s0, s1 = sun_sign(prev), sun_sign(nxt)
    return {"name": MONTH_BY_SUN_SIGN[s0], "adhika": s0 == s1, "new_moon_jd": prev, "next_new_moon_jd": nxt}
