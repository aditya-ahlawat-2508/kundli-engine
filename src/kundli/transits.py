"""Transits (gochar), ingress dates, Sade Sati / Dhaiya, Ashtakavarga transit scoring.

All functions take explicit datetimes; nothing reads the clock.
"""
from datetime import UTC, datetime, timedelta
from typing import Any

import swisseph as swe

from .ayanamsa import sid_mode
from .config import EngineConfig
from .data.tables import NAK_SPAN, NAKSHATRAS, PLANETS, SEVEN, SIGNS
from .ephemeris import base_flags, planet_positions
from .models import Kundli
from .timeutil import jd_to_utc, julian_day

BODY = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER,
        "Venus": swe.VENUS, "Saturn": swe.SATURN}


def _cfg(k: Kundli) -> EngineConfig:
    return EngineConfig(**k.header["config"])


def jd_of(dt: datetime) -> float:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return julian_day(dt.astimezone(UTC))[1]


def sid_lon(planet: str, jd_ut: float, cfg: EngineConfig) -> float:
    """Sidereal longitude of one graha (Rahu/Ketu per cfg.node_type)."""
    swe.set_sid_mode(sid_mode(cfg.ayanamsa))
    fl = base_flags(cfg) | swe.FLG_SIDEREAL
    if planet in ("Rahu", "Ketu"):
        node = swe.TRUE_NODE if cfg.node_type == "true" else swe.MEAN_NODE
        lon = swe.calc_ut(jd_ut, node, fl)[0][0]
        return (lon + (180.0 if planet == "Ketu" else 0.0)) % 360.0
    return swe.calc_ut(jd_ut, BODY[planet], fl)[0][0] % 360.0


def positions_on(as_of: datetime, cfg: EngineConfig) -> dict[str, Any]:
    pos = planet_positions(jd_of(as_of), cfg)
    return {p.name: p for p in pos}


def sade_sati_status(moon_sign: int, saturn_sign: int) -> dict[str, Any]:
    """Saturn 12th/1st/2nd from natal Moon sign = Sade Sati (rising/peak/setting); 4th = Dhaiya (Kantaka),
    8th = Ashtama Shani."""
    rel = (saturn_sign - moon_sign) % 12 + 1
    name = {12: "sade_sati_rising", 1: "sade_sati_peak", 2: "sade_sati_setting",
            4: "dhaiya_kantaka", 8: "dhaiya_ashtama"}.get(rel)
    return {"active": name is not None, "phase": name, "saturn_house_from_moon": rel}


def snapshot(k: Kundli, as_of: datetime) -> dict[str, Any]:
    """Transit positions at `as_of` over the natal chart."""
    cfg = _cfg(k)
    pos = positions_on(as_of, cfg)
    moon_sign = next(p.sign for p in k.planets if p.name == "Moon")
    lagna_sign = k.lagna["sign"] if k.lagna else None
    natal = {p.name: p for p in k.planets}
    av = k.ashtakavarga
    out: dict[str, Any] = {"as_of": as_of.astimezone(UTC).isoformat(), "planets": {}}
    for n in PLANETS:
        p = pos[n]
        s = int(p.sidereal_lon // 30)
        nk = int(p.sidereal_lon // NAK_SPAN)
        row: dict[str, Any] = {
            "longitude": p.sidereal_lon, "sign": s, "sign_name": SIGNS[s], "degree_in_sign": p.sidereal_lon - s * 30,
            "nakshatra": NAKSHATRAS[nk], "retrograde": p.retrograde,
            "house_from_moon": (s - moon_sign) % 12 + 1,
            "house_from_lagna": None if lagna_sign is None else (s - lagna_sign) % 12 + 1,
            "natal_planets_in_sign": sorted(q for q in PLANETS if natal[q].sign == s),
        }
        if av and n in SEVEN:
            row["bav_bindus"] = av["bav"][n][s]
            row["sav_bindus"] = av["sav"][s]
        out["planets"][n] = row
    out["sade_sati"] = sade_sati_status(moon_sign, out["planets"]["Saturn"]["sign"])
    return out


# ---- ingress dates ----------------------------------------------------------------------------------
def ingresses(planet: str, start: datetime, end: datetime, cfg: EngineConfig) -> list[dict[str, Any]]:
    """All sign changes of `planet` in [start, end], found by stepping and bisecting to ~1 second.
    Retrograde re-entries are reported as separate events (`retrograde` flag)."""
    j0, j1 = jd_of(start), jd_of(end)
    step = 0.25 if planet == "Moon" else 1.0
    out: list[dict[str, Any]] = []
    j = j0
    prev = int(sid_lon(planet, j, cfg) // 30)
    while j < j1:
        nj = min(j + step, j1)
        cur = int(sid_lon(planet, nj, cfg) // 30)
        if cur != prev:
            lo, hi = j, nj
            for _ in range(40):
                mid = (lo + hi) / 2.0
                if int(sid_lon(planet, mid, cfg) // 30) == prev:
                    lo = mid
                else:
                    hi = mid
            t = hi
            fwd = (cur - prev) % 12 == 1
            out.append({"planet": planet, "from_sign": prev, "to_sign": cur, "to_sign_name": SIGNS[cur],
                        "utc": jd_to_utc(t).isoformat(timespec="seconds"), "direct": fwd, "jd_ut": t})
        prev, j = cur, nj
    return out


def sade_sati_periods(moon_sign: int, start: datetime, end: datetime, cfg: EngineConfig) -> list[dict[str, Any]]:
    """Contiguous Sade Sati / Dhaiya intervals in [start, end] with exact ingress dates (UTC)."""
    events = ingresses("Saturn", start, end, cfg)
    j0 = jd_of(start)
    cur_sign = int(sid_lon("Saturn", j0, cfg) // 30)
    segs: list[tuple[datetime, datetime, int]] = []
    t = start.astimezone(UTC)
    for e in events:
        te = datetime.fromisoformat(e["utc"])
        segs.append((t, te, cur_sign))
        t, cur_sign = te, e["to_sign"]
    segs.append((t, end.astimezone(UTC), cur_sign))
    out: list[dict[str, Any]] = []
    for a, b, s in segs:
        st = sade_sati_status(moon_sign, s)
        if not st["active"]:
            continue
        if out and out[-1]["phase"] == st["phase"] and out[-1]["end"] == a.isoformat():
            out[-1]["end"] = b.isoformat()
        else:
            out.append({"phase": st["phase"], "saturn_sign": SIGNS[s], "start": a.isoformat(), "end": b.isoformat()})
    return out


def next_return(k: Kundli, planet: str, after: datetime) -> datetime:
    """Next date `planet` transits its natal sidereal longitude (within 1 second), searching up to 40 years."""
    cfg = _cfg(k)
    target = next(p.sidereal_lon for p in k.planets if p.name == planet)
    j = jd_of(after)

    def f(jd: float) -> float:
        return (sid_lon(planet, jd, cfg) - target + 180.0) % 360.0 - 180.0

    step = 1.0
    for _ in range(int(40 * 366 / step)):
        a, b = f(j), f(j + step)
        if a < 0 <= b and abs(a) < 90 and abs(b) < 90:
            lo, hi = j, j + step
            for _ in range(40):
                mid = (lo + hi) / 2.0
                lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
            return jd_to_utc(hi)
        j += step
    raise ValueError("no return found")


__all__ = ["ingresses", "next_return", "sade_sati_periods", "sade_sati_status", "snapshot", "timedelta"]
