"""Sade Sati and Dhaiya from Saturn's sidereal sign relative to the natal Moon sign.

Saturn 12th / 1st / 2nd from the Moon sign = Sade Sati rising / peak / setting; 4th and 8th = Dhaiya (Kantaka,
Ashtama). `sadhesati_periods` lists every interval of those phases over a lifetime with exact (second-level)
ingress dates, including retrograde re-entries as separate intervals; `sadhesati_events` lists the phase-changing
ingresses; `sadhesati_status` gives the phase at an explicit `as_of` (the engine never reads the clock).
"""
from datetime import UTC, datetime, timedelta
from typing import Any

from ..config import EngineConfig
from ..models import Kundli
from ..timeutil import julian_day
from ..transits import ingresses, sade_sati_status, sid_lon

PHASES = {12: "sade_sati_rising", 1: "sade_sati_peak", 2: "sade_sati_setting", 4: "dhaiya_kantaka",
          8: "dhaiya_ashtama"}


def sadhesati_events(k: Kundli, years: int = 90) -> list[dict[str, Any]]:
    """Every Saturn sign change (direct or retrograde) over `years` from birth that changes the Sade Sati / Dhaiya
    phase, typed relative to the natal Moon sign: RISING_START (Saturn enters the 12th), RISING_END (retrograde back
    to the 11th), PEAK_START (enters the Moon sign), SETTING_START (enters the 2nd), SETTING_END (enters the 3rd)."""
    cfg = EngineConfig(**k.header["config"])
    moon = next(p.sign for p in k.planets if p.name == "Moon")
    start = datetime.fromisoformat(k.birth["utc"])
    out = []
    for e in ingresses("Saturn", start, start + timedelta(days=365.25 * years), cfg):
        rel_to, rel_from = (e["to_sign"] - moon) % 12 + 1, (e["from_sign"] - moon) % 12 + 1
        kind = {(12, 11): "RISING_START", (12, 1): "RISING_START", (11, 12): "RISING_END", (1, 12): "PEAK_START",
                (1, 2): "PEAK_START", (2, 1): "SETTING_START", (2, 3): "SETTING_START", (3, 2): "SETTING_END"}.get(
            (rel_to, rel_from))
        if kind:
            out.append({"type": kind, "date": e["utc"][:10], "utc": e["utc"], "retrograde": not e["direct"],
                        "saturn_from": e["from_sign"], "saturn_to": e["to_sign"], "moon_sign": moon})
    return out


def sadhesati_periods(k: Kundli, years: int = 90) -> list[dict[str, Any]]:
    """Intervals (birth to birth + `years`) in which Saturn is 12th/1st/2nd (Sade Sati) or 4th/8th (Dhaiya) from the
    natal Moon sign: {phase, saturn_sign, start_utc, end_utc, group}. `group` numbers the Sade Sati cycles (a
    cycle is the run of rising/peak/setting intervals around one Saturn transit of three signs)."""
    cfg = EngineConfig(**k.header["config"])
    moon = next(p.sign for p in k.planets if p.name == "Moon")
    start = datetime.fromisoformat(k.birth["utc"])
    end = start + timedelta(days=365.25 * years)
    sign0 = int(sid_lon("Saturn", julian_day(start)[1], cfg) // 30)
    cuts = [(start, sign0)] + [(datetime.fromisoformat(e["utc"]), e["to_sign"]) for e in ingresses("Saturn", start, end, cfg)]
    out: list[dict[str, Any]] = []
    for i, (t0, sign) in enumerate(cuts):
        t1 = cuts[i + 1][0] if i + 1 < len(cuts) else end
        phase = PHASES.get((sign - moon) % 12 + 1)
        if phase:
            out.append({"phase": phase, "saturn_sign": sign, "start_utc": t0.isoformat(timespec="seconds"),
                        "end_utc": t1.isoformat(timespec="seconds"), "retrograde_entry": i > 0 and (sign - cuts[i - 1][1]) % 12 != 1})
    group, prev_end = 0, None
    for p in out:
        if p["phase"].startswith("sade_sati"):
            # retrograde dips back out of the zone for under a year; cycles are ~29.5 years apart
            if prev_end is None or datetime.fromisoformat(p["start_utc"]) - datetime.fromisoformat(prev_end) > timedelta(days=730):
                group += 1
            prev_end = p["end_utc"]
            p["group"] = group
    return out


def sadhesati_status(k: Kundli, as_of: datetime) -> dict[str, Any]:
    """Phase at `as_of` plus the period containing it (None when no Sade Sati/Dhaiya is running)."""
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    cfg = EngineConfig(**k.header["config"])
    moon = next(p.sign for p in k.planets if p.name == "Moon")
    saturn = int(sid_lon("Saturn", julian_day(as_of.astimezone(UTC))[1], cfg) // 30)
    st = sade_sati_status(moon, saturn)
    birth = datetime.fromisoformat(k.birth["utc"])
    years = max(1, int((as_of - birth).days / 365.25) + 31)
    iso = as_of.astimezone(UTC).isoformat(timespec="seconds")
    period = next((p for p in sadhesati_periods(k, years) if p["start_utc"] <= iso < p["end_utc"]), None)
    return {**st, "as_of": iso, "moon_sign": moon, "saturn_sign": saturn, "period": period}


__all__ = ["sadhesati_events", "sadhesati_periods", "sadhesati_status"]
