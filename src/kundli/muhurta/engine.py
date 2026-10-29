"""Muhurta scan: score every slot of a date range against an activity's ruleset and explain the result.

Each Vedic day (sunrise to next sunrise) is cut at every tithi, nakshatra, yoga and karana boundary and at the edges of
the inauspicious windows (Rahu Kaal, Yamaganda, Gulika Kaal, Abhijit). Each piece is evaluated at its midpoint against
the rules; neighbouring pieces with the same verdict are merged into one window. The score of a window is the share of
soft-rule weight that passed (0-100); a failed `veto` rule makes the window `vetoed` (score null). Rules needing a
birth chart (Tarabala, Chandrabala) or a travel direction are `not_evaluated` when it is not supplied and then count
neither way. The month is taken at each day's sunrise. Nothing is tuned to a target outcome (docs/conventions.md).
"""
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from ..config import EngineConfig
from ..data.tables import COMBUST_ORBS, NAK_SPAN, NAKSHATRAS, SIGNS, YOGA_NAMES
from ..ephemeris import base_flags
from ..models import Kundli
from ..panchang.core import hindu_month, karana
from ..panchang.inauspicious import inauspicious_periods
from ..panchang.spans import ELEMENTS, span, sun_moon
from ..panchang.sun_moon_times import local_iso, rise_args, sun_day
from ..transits import sid_lon
from .rules import WEEKDAYS, Rule, RuleSet, load, tables

MAX_DAYS = 62
EPS = 1e-7
MIN_PIECE = 1e-5  # ~1 second
GOOD_SCORE = 60.0


@dataclass(frozen=True)
class Natal:
    nakshatra: int
    moon_sign: int


def natal_from(k: Kundli) -> Natal:
    moon = next(p for p in k.planets if p.name == "Moon")
    return Natal(moon.nakshatra, moon.sign)


def _angdiff(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def evaluate_rule(r: Rule, ctx: dict[str, Any], natal: Natal | None, direction: str | None) -> bool | None:
    """True = pass, False = fail, None = not evaluable with the inputs given."""
    k = r.kind
    vals = {str(v) for v in r.values}
    if k == "weekday_in":
        return ctx["weekday"] in vals
    if k == "weekday_not_in":
        return ctx["weekday"] not in vals
    if k == "tithi_in":
        return str(ctx["tithi"]) in vals
    if k == "tithi_not_in":
        return str(ctx["tithi"]) not in vals
    if k == "nakshatra_in":
        return ctx["nakshatra"] in vals
    if k == "nakshatra_not_in":
        return ctx["nakshatra"] not in vals
    if k == "nakshatra_class_in":
        return ctx["nakshatra_class"] in r.classes
    if k == "nakshatra_class_not_in":
        return ctx["nakshatra_class"] not in r.classes
    if k == "yoga_not_in":
        return ctx["yoga"] not in vals
    if k == "karana_not_in":
        return ctx["karana"] not in vals
    if k == "month_in":
        return ctx["month"] in vals
    if k == "month_not_in":
        return ctx["month"] not in vals
    if k == "adhika_not":
        return not ctx["adhika"]
    if k == "sun_sign_not_in":
        return ctx["sun_sign"] not in vals
    if k == "not_combust":
        return not any(ctx["combust"][p] for p in r.planets)
    if k == "not_in_window":
        return not (set(r.windows) & ctx["windows"])
    if k == "in_window":
        return bool(set(r.windows) & ctx["windows"])
    if k == "paksha_in":
        return ctx["paksha"] in vals
    if k == "tarabala_ok":
        if natal is None:
            return None
        return ((ctx["nak_index"] - natal.nakshatra) % 27 + 1) % 9 not in (3, 5, 7)
    if k == "chandrabala_ok":
        if natal is None:
            return None
        return (ctx["moon_sign_index"] - natal.moon_sign) % 12 + 1 in (1, 3, 6, 7, 10, 11)
    if k == "dishashoola_ok":
        if direction is None:
            return None
        bad = tables()["dishashoola"].get(direction.lower())
        if bad is None:
            raise ValueError(f"direction must be one of {sorted(tables()['dishashoola'])}")
        return ctx["weekday"] not in bad
    raise ValueError(f"unknown rule kind {k!r}")


def _class_of(nak: str) -> str:
    return next(c for c, ns in tables()["nakshatra_class"].items() if nak in ns)


def _score(rs: RuleSet, ctx: dict[str, Any], natal: Natal | None, direction: str | None) -> dict[str, Any]:
    passed: list[str] = []
    failed: list[str] = []
    skipped: list[str] = []
    soft_total = soft_got = 0.0
    vetoed = False
    for r in rs.rules:
        res = evaluate_rule(r, ctx, natal, direction)
        if res is None:
            skipped.append(r.id)
            continue
        (passed if res else failed).append(r.id)
        if r.veto and not res:
            vetoed = True
        if r.weight > 0:
            soft_total += r.weight
            soft_got += r.weight if res else 0.0
    score = None if vetoed else round(100.0 * soft_got / soft_total, 1) if soft_total else 100.0
    return {"vetoed": vetoed, "score": score, "passed": passed, "failed": failed, "not_evaluated": skipped,
            "vetoed_by": [r.id for r in rs.rules if r.veto and r.id in failed]}


def _context(mid: float, weekday: str, day: dict[str, Any], windows: dict[str, tuple[float, float]], cfg: EngineConfig,
             eph: int, needs_combust: bool) -> dict[str, Any]:
    sun, moon = sun_moon(mid, cfg.ayanamsa, eph)
    nak = int(moon // NAK_SPAN)
    tithi = int(((moon - sun) % 360.0) // 12.0) + 1
    ctx: dict[str, Any] = {
        "weekday": weekday, "tithi": tithi, "paksha": "shukla" if tithi <= 15 else "krishna", "nak_index": nak,
        "nakshatra": NAKSHATRAS[nak], "nakshatra_class": _class_of(NAKSHATRAS[nak]),
        "yoga": YOGA_NAMES[int(((sun + moon) % 360.0) // NAK_SPAN)], "karana": karana(sun, moon)[1],
        "month": day["month"], "adhika": day["adhika"], "sun_sign": SIGNS[int(sun // 30)],
        "moon_sign_index": int(moon // 30),
        "windows": {name for name, (a, b) in windows.items() if a <= mid < b}, "combust": {}}
    if needs_combust:
        ctx["combust"] = {p: _angdiff(sid_lon(p, mid, cfg), sun) < COMBUST_ORBS[p] for p in ("Venus", "Jupiter")}
    return ctx


def _pieces(t0: float, t1: float, bounds: list[float], cfg: EngineConfig, eph: int) -> list[tuple[float, float]]:
    out, t = [], t0
    while t < t1 - EPS:
        ends = [span(el, t + EPS, cfg.ayanamsa, eph)[1] for el in ELEMENTS] + [b for b in bounds if b > t + EPS] + [t1]
        nxt = min(ends)
        if nxt - t >= MIN_PIECE:
            out.append((t, nxt))
        t = nxt
    return out


def scan(activity: str, start: date, end: date, lat: float, lon: float, tz: str, cfg: EngineConfig,
         natal: Kundli | None = None, direction: str | None = None) -> dict[str, Any]:
    """Score every window of [start, end] (inclusive civil dates, at most 62 days) for `activity`."""
    if end < start:
        raise ValueError("end date is before start date")
    if (end - start).days + 1 > MAX_DAYS:
        raise ValueError(f"at most {MAX_DAYS} days per scan")
    rs = load(activity)
    nat = natal_from(natal) if natal is not None else None
    eph, ra = base_flags(cfg), rise_args(cfg)
    needs_combust = any(r.kind == "not_combust" for r in rs.rules)
    days: list[dict[str, Any]] = []
    d = start
    while d <= end:
        sd = sun_day(d, lat, lon, tz, **ra)
        if sd is None:
            days.append({"date": d.isoformat(), "weekday": WEEKDAYS[(d.weekday() + 1) % 7], "windows": [], "best_score": None,
                         "note": "no sunrise/sunset at this latitude on this date"})
            d += timedelta(days=1)
            continue
        wd = (d.weekday() + 1) % 7
        weekday = WEEKDAYS[wd]
        ip = inauspicious_periods(sd, wd, tz)
        windows = {name: (w["start_jd"], w["end_jd"]) for name, w in ip.items()}
        hm = hindu_month(sd["sunrise"], cfg.ayanamsa, eph)
        day = {"month": hm["name"], "adhika": hm["adhika"]}
        bounds = sorted({x for a, b in windows.values() for x in (a, b)})
        merged: list[dict[str, Any]] = []
        for a, b in _pieces(sd["sunrise"], sd["next_sunrise"], bounds, cfg, eph):
            ctx = _context((a + b) / 2.0, weekday, day, windows, cfg, eph, needs_combust)
            res = _score(rs, ctx, nat, direction)
            sig = (res["vetoed"], res["score"], tuple(res["failed"]))
            if merged and merged[-1]["_sig"] == sig:
                merged[-1]["end_jd"] = b
                merged[-1]["end_local"] = local_iso(b, tz)
                merged[-1]["_ctx"].append(_brief(ctx))
                continue
            merged.append({"_sig": sig, "start_jd": a, "end_jd": b, "start_local": local_iso(a, tz), "end_local": local_iso(b, tz),
                           **res, "_ctx": [_brief(ctx)]})
        for w in merged:
            w.pop("_sig")
            ctxs = w.pop("_ctx")
            w["nakshatras"] = sorted({c["nakshatra"] for c in ctxs})
            w["tithis"] = sorted({c["tithi"] for c in ctxs})
        scores = [w["score"] for w in merged if not w["vetoed"] and w["score"] is not None]
        days.append({"date": d.isoformat(), "weekday": weekday, "month": day["month"], "adhika": day["adhika"],
                     "best_score": max(scores) if scores else None, "windows": merged})
        d += timedelta(days=1)
    good = [x["date"] for x in days if x["best_score"] is not None and x["best_score"] >= GOOD_SCORE]
    return {"activity": activity, "ruleset_version": rs.version, "rules_verified": not rs.verify, "sources": list(rs.sources),
            "range": [start.isoformat(), end.isoformat()], "good_score_threshold": GOOD_SCORE, "good_dates": good,
            "days": days, "personal_checks": nat is not None, "direction": direction}


def _brief(ctx: dict[str, Any]) -> dict[str, Any]:
    return {"nakshatra": ctx["nakshatra"], "tithi": ctx["tithi"]}


__all__ = ["GOOD_SCORE", "MAX_DAYS", "Natal", "evaluate_rule", "natal_from", "scan"]
