"""Chara (Jaimini) dasha: sign-based periods starting from the lagna sign.

Sequence direction: lagna in Aries, Taurus, Gemini, Libra, Scorpio or Sagittarius runs forward through the zodiac,
other lagnas run backward. Years of a sign = signs counted from it to its lord (forward for those six signs, backward
for the rest), minus one; zero becomes 12. Scorpio (Mars/Ketu) and Aquarius (Saturn/Rahu) use the co-lord with
the greater degrees in its sign. Each maha dasha is split into 12 equal antardashas that start from the sign after
the maha sign and end with the maha sign itself. VERIFY: schools differ on co-lord choice and antardasha order;
only maha dasha dates were cross-checked against an external reference (tests/reference).
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ..data.tables import SIGN_LORDS, SIGNS
from .engine import LEVEL_NAMES

SAVYA = {0, 1, 2, 6, 7, 8}
CO_LORDS = {7: ("Mars", "Ketu"), 10: ("Saturn", "Rahu")}


def lord_of(sign: int, signs: dict[str, int], degs: dict[str, float]) -> str:
    if sign in CO_LORDS:
        a, b = CO_LORDS[sign]
        return a if degs[a] > degs[b] else b
    return SIGN_LORDS[sign]


def sign_years(sign: int, signs: dict[str, int], degs: dict[str, float]) -> int:
    lord_sign = signs[lord_of(sign, signs, degs)]
    n = (lord_sign - sign) % 12 if sign in SAVYA else (sign - lord_sign) % 12
    return n or 12


def sequence(lagna_sign: int) -> list[int]:
    step = 1 if lagna_sign in SAVYA else -1
    return [(lagna_sign + step * i) % 12 for i in range(12)]


def _fmt(dt: datetime, tz: ZoneInfo) -> tuple[str, str]:
    return dt.isoformat(timespec="seconds"), dt.astimezone(tz).isoformat(timespec="seconds")


def _node(level: int, sign: int, start: datetime, days: float, z: ZoneInfo, extra: dict | None = None) -> dict:
    end = start + timedelta(days=days)
    return {"level": LEVEL_NAMES[level], "sign": sign, "lord": SIGNS[sign], "days": days, "start_utc": _fmt(start, z)[0],
            "end_utc": _fmt(end, z)[0], "start_local": _fmt(start, z)[1], "end_local": _fmt(end, z)[1], **(extra or {})}


def children(sign: int, start: datetime, days: float) -> list[tuple[int, datetime, float]]:
    """12 equal sub-periods of a period of `sign`, in the direction of that sign, starting from the next sign and
    ending with the sign itself. VERIFY: the same rule is applied at every level below maha (only maha dates were
    cross-checked against a reference)."""
    step = 1 if sign in SAVYA else -1
    return [((sign + step * i) % 12, start + timedelta(days=days / 12.0 * (i - 1)), days / 12.0) for i in range(1, 13)]


def _build(sign: int, start: datetime, days: float, level: int, depth: int, z: ZoneInfo, extra: dict | None = None) -> dict:
    node = _node(level, sign, start, days, z, extra)
    if level + 1 < depth:
        node["children"] = [_build(cs, ct, cd, level + 1, depth, z) for cs, ct, cd in children(sign, start, days)]
    return node


def maha_periods(lagna_sign: int, signs: dict[str, int], degs: dict[str, float], birth_utc: datetime,
                 year_days: float) -> list[tuple[int, datetime, float, int]]:
    """(sign, start, days, years) for the 12 maha dashas from birth."""
    out, t = [], birth_utc
    for s in sequence(lagna_sign):
        yrs = sign_years(s, signs, degs)
        out.append((s, t, yrs * year_days, yrs))
        t = t + timedelta(days=yrs * year_days)
    return out


def tree(lagna_sign: int, signs: dict[str, int], degs: dict[str, float], birth_utc: datetime, year_days: float,
         tz: str, depth: int = 2) -> list[dict]:
    z = ZoneInfo(tz)
    return [_build(s, t, d, 0, depth, z, {"years": y})
            for s, t, d, y in maha_periods(lagna_sign, signs, degs, birth_utc, year_days)]


def stack(lagna_sign: int, signs: dict[str, int], degs: dict[str, float], birth_utc: datetime, year_days: float,
          as_of: datetime, levels: int, tz: str) -> list[dict]:
    """Running maha/antar/pratyantar... at `as_of` (aware; never read from the clock). Empty before birth or
    after the 12 maha dashas end."""
    z = ZoneInfo(tz)
    out: list[dict] = []
    cur = [(s, t, d) for s, t, d, _ in maha_periods(lagna_sign, signs, degs, birth_utc, year_days)]
    for lvl in range(levels):
        hit = next(((s, t, d) for s, t, d in cur if t <= as_of < t + timedelta(days=d)), None)
        if hit is None:
            break
        out.append(_node(lvl, *hit, z))
        cur = children(*hit)
    return out


def descend(lagna_sign: int, signs: dict[str, int], degs: dict[str, float], birth_utc: datetime, year_days: float,
            path: list[str], tz: str, depth: int = 1) -> dict:
    """The sub-periods of the period reached by following `path` (sign names: maha, then antar, ...)."""
    z = ZoneInfo(tz)
    cur = [(s, t, d) for s, t, d, _ in maha_periods(lagna_sign, signs, degs, birth_utc, year_days)]
    hit = None
    for lvl, name in enumerate(path):
        key = name.strip().lower()
        hit = next(((s, t, d) for s, t, d in cur if SIGNS[s].lower() == key), None)
        if hit is None:
            raise ValueError(f"no {LEVEL_NAMES[lvl]} period for sign {name!r} here; "
                             f"available: {[SIGNS[s] for s, _, _ in cur]}")
        cur = children(*hit)
    parent = _node(len(path) - 1, *hit, z) if hit else None
    return {"parent": parent, "children": [_build(s, t, d, len(path), len(path) + depth, z) for s, t, d in cur]}
