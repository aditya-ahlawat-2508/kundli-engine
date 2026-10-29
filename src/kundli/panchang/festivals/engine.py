"""Evaluate festival rules for a civil date.

A `lunar`/`tithi` rule fires on civil date D when the tithi at the rule's anchor moment of D equals the rule's tithi
and (for `lunar`) the amanta month at that moment has the rule's name and is not an Adhika month. `sankranti`
fires on the Tamil-rule day 1 of a solar month; `after` fires on the day after another rule. This is a deliberate
single-anchor simplification (see docs/open_questions.md): classical tie-breaks for tithis spanning two days are not
applied, so every rule is `verify` until compared with a published almanac.
"""
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

from ...config import EngineConfig
from ...ephemeris import base_flags
from ..core import hindu_month
from ..spans import sun_moon
from ..sun_moon_times import local_iso, moon_day, rise_args, sun_day
from ..tamil import TAMIL_MONTHS, tamil_calendar

RULES_DIR = Path(__file__).parent / "rules"
Anchor = Literal["sunrise", "madhyahna", "aparahna", "pradosha", "nishita", "moonrise"]
SIGNS = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha",
         "Meena"]
MONTHS = ["Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada", "Ashwin", "Kartik", "Margashirsha",
          "Pausha", "Magha", "Phalguna"]
DEFAULT_SOURCE = ("Festival rule summarised from standard almanac practice (Drik-style single-anchor); "
                  "NOT yet checked against a published almanac")


class Rule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name: str
    kind: Literal["lunar", "tithi", "sankranti", "after"]
    month: str | None = None
    tithi: int | None = None
    anchor: Anchor | None = None
    after: str | None = None
    source: str = DEFAULT_SOURCE
    verify: bool = True


@lru_cache(maxsize=1)
def load_rules() -> tuple[Rule, ...]:
    rules: list[Rule] = []
    for f in sorted(RULES_DIR.glob("*.yaml")):
        rules += [Rule(**r) for r in yaml.safe_load(f.read_text(encoding="utf-8"))]
    ids = [r.id for r in rules]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate festival rule ids")
    for r in rules:
        if r.kind in ("lunar", "tithi") and (r.tithi is None or r.anchor is None):
            raise ValueError(f"rule {r.id}: tithi and anchor are required")
        if r.kind == "lunar" and r.month not in MONTHS:
            raise ValueError(f"rule {r.id}: unknown month {r.month!r}")
        if r.kind == "after" and r.after not in ids:
            raise ValueError(f"rule {r.id}: unknown rule {r.after!r}")
    return tuple(rules)


def _tithi_at(jd: float, ayanamsa: str, eph: int) -> int:
    s, m = sun_moon(jd, ayanamsa, eph)
    return int(((m - s) % 360.0) // 12.0) + 1


def _anchor_jd(anchor: str, sd: dict, moon: dict[str, float | None]) -> float | None:
    day = sd["sunset"] - sd["sunrise"]
    return {"sunrise": sd["sunrise"], "madhyahna": sd["sunrise"] + 0.5 * day,
            "aparahna": sd["sunrise"] + 0.7 * day, "pradosha": sd["sunset"] + 1.0 / 30.0,
            "nishita": (sd["sunset"] + sd["next_sunrise"]) / 2.0, "moonrise": moon["moonrise"]}[anchor]


def _month_label(name: str, tithi: int, tradition: str) -> str:
    """Amanta name, or the purnimanta name (krishna paksha belongs to the next month)."""
    if tradition == "drik_purnimanta" and tithi > 15:
        return MONTHS[(MONTHS.index(name) + 1) % 12]
    return name


def _fires(r: Rule, d: date, lat: float, lon: float, tz: str, cfg: EngineConfig, cache: dict) -> dict | None:
    ra = rise_args(cfg)
    eph = base_flags(cfg)
    if r.kind == "sankranti":
        try:
            tc = tamil_calendar(d, lat, lon, tz, cfg)
        except ValueError:
            return None
        if tc["day"] != 1:
            return None
        sign = tc["month_number"] - 1
        name = {9: "Makar Sankranti", 0: "Mesha Sankranti (Vaisakhi)"}.get(sign, f"{SIGNS[sign]} Sankranti")
        return {"id": r.id, "name": name, "date": d.isoformat(), "solar_month": TAMIL_MONTHS[sign],
                "sankranti_local": tc["sankranti_local"], "source": r.source, "verify": r.verify}
    if r.kind == "after":
        base = next(x for x in load_rules() if x.id == r.after)
        if _fires(base, d - timedelta(days=1), lat, lon, tz, cfg, cache) is None:
            return None
        return {"id": r.id, "name": r.name, "date": d.isoformat(), "source": r.source, "verify": r.verify}
    key = ("sun", d)
    if key not in cache:
        cache[key] = (sun_day(d, lat, lon, tz, **ra), moon_day(d, lat, lon, tz, **ra))
    sd, moon = cache[key]
    if sd is None:
        return None
    jd = _anchor_jd(r.anchor or "sunrise", sd, moon)
    if jd is None:
        return None
    t = _tithi_at(jd, cfg.ayanamsa, eph)
    if t != r.tithi:
        return None
    out = {"id": r.id, "name": r.name, "date": d.isoformat(), "tithi": t, "paksha": "shukla" if t <= 15 else "krishna",
           "anchor": r.anchor, "anchor_local": local_iso(jd, tz), "source": r.source, "verify": r.verify}
    if r.kind == "lunar":
        hm = hindu_month(jd, cfg.ayanamsa, eph)
        if hm["name"] != r.month or hm["adhika"]:
            return None
        out["month"] = _month_label(hm["name"], t, cfg.festival_tradition)
    return out


def festivals_on(d: date, lat: float, lon: float, tz: str, cfg: EngineConfig, ids: set[str] | None = None) -> list[dict]:
    """All rules firing on civil date `d`."""
    cache: dict = {}
    hits = (_fires(r, d, lat, lon, tz, cfg, cache) for r in load_rules() if ids is None or r.id in ids)
    return [h for h in hits if h is not None]


def festival_dates(rule_id: str, year: int, lat: float, lon: float, tz: str, cfg: EngineConfig) -> list[dict]:
    """Dates in calendar `year` on which rule `rule_id` fires (reverse lookup; scans every day)."""
    if rule_id not in {r.id for r in load_rules()}:
        raise ValueError(f"unknown festival rule {rule_id!r}")
    out: list[dict] = []
    d = date(year, 1, 1)
    while d.year == year:
        out += festivals_on(d, lat, lon, tz, cfg, {rule_id})
        d += timedelta(days=1)
    return out


__all__ = ["Rule", "festival_dates", "festivals_on", "load_rules"]
