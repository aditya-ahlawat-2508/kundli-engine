"""Monthly panchang yogas: Sarvartha Siddhi, Amrit Siddhi, Ravi, Ravi Pushya, Guru Pushya, Dwipushkar, Tripushkar.

For every Vedic day (sunrise to next sunrise) of a calendar month the day is cut at each nakshatra and tithi boundary
(exact instants from `spans`), each piece is tested against the rule, and consecutive qualifying pieces are merged
into one window. Rules are data (`rules/monthly_yogas.yaml`). Ravi Yoga samples the Sun's nakshatra at the middle
of each piece (the Sun changes nakshatra only every ~13 days, so a piece never straddles two Sun nakshatras in
practice).
"""
from calendar import monthrange
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from ..config import EngineConfig
from ..data.tables import NAK_SPAN, NAKSHATRAS
from ..ephemeris import base_flags
from ..timeutil import jd_to_utc
from .spans import span, sun_moon
from .sun_moon_times import rise_args, sun_day

RULES_FILE = Path(__file__).parent / "rules" / "monthly_yogas.yaml"
WEEKDAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
EPS = 1e-7


@lru_cache(maxsize=1)
def load_rules() -> dict[str, dict[str, Any]]:
    rules = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))
    for key, r in rules.items():
        if not r.get("source") or "verify" not in r:
            raise ValueError(f"yoga rule {key}: source and verify are required")
        names = [n for ns in r.get("table", {}).values() for n in ns] + r.get("nakshatras", [])
        bad = sorted(set(names) - set(NAKSHATRAS))
        if bad:
            raise ValueError(f"yoga rule {key}: unknown nakshatra names {bad}")
    return rules


def _pieces(t0: float, t1: float, ayanamsa: str, eph: int) -> list[dict]:
    """Cut [t0, t1) at every nakshatra and tithi boundary."""
    out, t = [], t0
    while t < t1 - EPS:
        n_end = span("nakshatra", t + EPS, ayanamsa, eph)[1]
        h_end = span("tithi", t + EPS, ayanamsa, eph)[1]
        end = min(n_end, h_end, t1)
        if end - t < 1e-5:  # ~1 second: a boundary coincides with the day start, not a real piece
            t = end + EPS
            continue
        mid = (t + end) / 2.0
        sun, moon = sun_moon(mid, ayanamsa, eph)
        out.append({"start": t, "end": end, "nak": int(moon // NAK_SPAN), "sun_nak": int(sun // NAK_SPAN),
                    "tithi": int(((moon - sun) % 360.0) // 12.0) + 1})
        t = end
    return out


def _qualifies(rule: dict, weekday: str, p: dict) -> bool:
    kind = rule["kind"]
    if kind == "weekday_nakshatra":
        return NAKSHATRAS[p["nak"]] in rule["table"].get(weekday, [])
    if kind == "moon_from_sun":
        return ((p["nak"] - p["sun_nak"]) % 27) + 1 in rule["offsets"]
    if kind == "weekday_tithi_nakshatra":
        return (weekday in rule["weekdays"] and p["tithi"] in rule["tithis"]
                and NAKSHATRAS[p["nak"]] in rule["nakshatras"])
    raise ValueError(f"unknown yoga kind {kind!r}")


def monthly_yogas(year: int, month: int, lat: float, lon: float, tz: str, cfg: EngineConfig,
                  which: set[str] | None = None) -> dict[str, list[dict]]:
    """{yoga id: [windows]} for the calendar month. A window is {date, weekday, start_local, end_local, nakshatra,
    tithi}; `date` is the civil date of the sunrise that starts the Vedic day."""
    rules = {k: v for k, v in load_rules().items() if which is None or k in which}
    eph, ra, zi = base_flags(cfg), rise_args(cfg), ZoneInfo(tz)
    out: dict[str, list[dict]] = {k: [] for k in rules}
    for day_n in range(monthrange(year, month)[1]):
        d = date(year, month, 1) + timedelta(days=day_n)
        sd = sun_day(d, lat, lon, tz, **ra)
        if sd is None:
            continue
        wk = WEEKDAY_NAMES[(d.weekday() + 1) % 7]  # Vedic weekday of the sunrise that starts the day
        pieces = _pieces(sd["sunrise"], sd["next_sunrise"], cfg.ayanamsa, eph)
        for key, rule in rules.items():
            run: list[dict] = []
            for p in [*pieces, None]:
                if p is not None and _qualifies(rule, wk, p):
                    run.append(p)
                    continue
                if run:
                    a, b = run[0]["start"], run[-1]["end"]
                    out[key].append({
                        "date": d.isoformat(), "weekday": wk,
                        "start_local": jd_to_utc(a).astimezone(zi).isoformat(timespec="seconds"),
                        "end_local": jd_to_utc(b).astimezone(zi).isoformat(timespec="seconds"),
                        "start_jd": a, "end_jd": b,
                        "nakshatra": sorted({NAKSHATRAS[x["nak"]] for x in run}),
                        "tithi": sorted({x["tithi"] for x in run})})
                    run = []
    return out


__all__ = ["WEEKDAY_NAMES", "load_rules", "monthly_yogas"]
