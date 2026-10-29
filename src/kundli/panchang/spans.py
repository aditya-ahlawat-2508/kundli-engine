"""Exact start/end instants of the running tithi, nakshatra, yoga and karana.

Each element is a monotonically increasing angle divided into equal units:

| element   | angle (sidereal Sun s, Moon m)      | unit      | count |
|-----------|-------------------------------------|-----------|-------|
| tithi     | (m - s) mod 360                     | 12 deg    | 30    |
| karana    | (m - s) mod 360                     | 6 deg     | 60    |
| nakshatra | m                                   | 13deg20'  | 27    |
| yoga      | (s + m) mod 360                     | 13deg20'  | 27    |

The boundary is found by scanning in hourly steps until the unit index changes, then bisecting to ~1e-8 day
(< 1 ms). No linear interpolation of speeds is used.
"""
from collections.abc import Callable

import swisseph as swe

from ..ayanamsa import ayanamsa_ut
from ..data.tables import NAK_SPAN, NAKSHATRAS, YOGA_NAMES
from ..timeutil import jd_to_utc
from .core import karana, tithi

STEP = 1.0 / 24.0
TOL = 1e-8
MAX_SCAN_DAYS = 3.0

Angle = Callable[[float, float], float]
ELEMENTS: dict[str, tuple[Angle, float, int]] = {
    "tithi": (lambda s, m: (m - s) % 360.0, 12.0, 30),
    "karana": (lambda s, m: (m - s) % 360.0, 6.0, 60),
    "nakshatra": (lambda s, m: m % 360.0, NAK_SPAN, 27),
    "yoga": (lambda s, m: (s + m) % 360.0, NAK_SPAN, 27),
}


def sun_moon(jd: float, ayanamsa: str, eph: int) -> tuple[float, float]:
    """Sidereal (Sun, Moon) longitudes at `jd` (UT)."""
    ay = ayanamsa_ut(jd, ayanamsa)
    return ((swe.calc_ut(jd, swe.SUN, eph)[0][0] - ay) % 360.0, (swe.calc_ut(jd, swe.MOON, eph)[0][0] - ay) % 360.0)


def _index(element: str, jd: float, ayanamsa: str, eph: int) -> int:
    angle, unit, n = ELEMENTS[element]
    return int(angle(*sun_moon(jd, ayanamsa, eph)) // unit) % n


def _boundary(element: str, jd: float, direction: int, ayanamsa: str, eph: int) -> float:
    """Instant where the unit index of `element` changes, searching forward (+1) or backward (-1) from `jd`."""
    i0 = _index(element, jd, ayanamsa, eph)
    lo, t = jd, jd
    for _ in range(int(MAX_SCAN_DAYS / STEP)):
        t = lo + direction * STEP
        if _index(element, t, ayanamsa, eph) != i0:
            break
        lo = t
    else:
        raise RuntimeError(f"no {element} boundary within {MAX_SCAN_DAYS} days of JD {jd}")
    a, b = (lo, t) if direction > 0 else (t, lo)  # a is inside the unit being searched from, b outside (or reverse)
    inside_is_a = direction > 0
    while b - a > TOL:
        mid = (a + b) / 2.0
        same = _index(element, mid, ayanamsa, eph) == i0
        if same == inside_is_a:
            a = mid
        else:
            b = mid
    return (a + b) / 2.0


def span(element: str, jd: float, ayanamsa: str, eph: int) -> tuple[float, float]:
    """(start_jd, end_jd) of the `element` unit running at `jd`."""
    return _boundary(element, jd, -1, ayanamsa, eph), _boundary(element, jd, +1, ayanamsa, eph)


def _describe(element: str, jd: float, ayanamsa: str, eph: int) -> dict:
    s, m = sun_moon(jd, ayanamsa, eph)
    if element == "tithi":
        n, name, paksha = tithi(s, m)
        return {"number": n, "name": name, "paksha": paksha}
    if element == "karana":
        n, name = karana(s, m)
        return {"number": n, "name": name}
    if element == "nakshatra":
        i = int(m // NAK_SPAN)
        return {"number": i + 1, "name": NAKSHATRAS[i], "pada": int((m % NAK_SPAN) // (NAK_SPAN / 4)) + 1}
    i = int(((s + m) % 360.0) // NAK_SPAN)
    return {"number": i + 1, "name": YOGA_NAMES[i]}


def element_spans(jd_ut: float, tz: str, ayanamsa: str = "lahiri", eph: int = swe.FLG_MOSEPH) -> dict[str, dict]:
    """Running tithi/nakshatra/yoga/karana at `jd_ut` with exact start and end, and the next element."""
    from zoneinfo import ZoneInfo

    zi = ZoneInfo(tz)

    def loc(j: float) -> str:
        return jd_to_utc(j).astimezone(zi).isoformat(timespec="seconds")

    out: dict[str, dict] = {}
    for el in ELEMENTS:
        a, b = span(el, jd_ut, ayanamsa, eph)
        out[el] = {**_describe(el, jd_ut, ayanamsa, eph), "start_jd": a, "end_jd": b, "start_local": loc(a),
                   "end_local": loc(b), "next": _describe(el, b + 1e-5, ayanamsa, eph)}
    return out


__all__ = ["ELEMENTS", "element_spans", "span", "sun_moon"]
