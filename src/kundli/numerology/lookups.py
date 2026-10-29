"""Numerology lookups derived from a number's ruling graha: favourable lord/numbers (natural friendship), day of the week,
direction and mantra. Friendship comes from the existing natural-friendship table (`dignity`); Rahu (4) and Ketu (7)
have no friendship row, so relations involving them are reported as `not_defined` rather than invented."""
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..data.tables import WEEKDAY_LORDS
from ..dignity import natural_relation
from .table import RULERS

WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
SEVEN = set(WEEKDAY_LORDS)
FILE = Path(__file__).with_name("data.yaml")


@lru_cache(maxsize=1)
def data() -> dict[str, Any]:
    d = yaml.safe_load(FILE.read_text(encoding="utf-8"))
    if set(d["mantra"]) != set(RULERS.values()):
        raise ValueError("mantra table must cover every ruling graha")
    return d


def _check(n: int) -> int:
    if n not in RULERS:
        raise ValueError("number must be 1..9")
    return n


def relation(a: int, b: int) -> str:
    ra, rb = RULERS[_check(a)], RULERS[_check(b)]
    if ra == rb:
        return "same"
    if ra not in SEVEN or rb not in SEVEN:
        return "not_defined"
    return natural_relation(ra, rb)


def fav_lord(n: int) -> dict[str, Any]:
    """Ruling graha of number `n` and which numbers are friendly / neutral / inimical (by their rulers)."""
    out: dict[str, list[int]] = {"friend": [], "neutral": [], "enemy": [], "not_defined": []}
    for m in RULERS:
        if m != n:
            out[relation(n, m)].append(m)
    return {"number": n, "lord": RULERS[_check(n)], "friendly_numbers": out["friend"], "neutral_numbers": out["neutral"],
            "inimical_numbers": out["enemy"], "not_defined_numbers": out["not_defined"],
            "note": "Rahu (4) and Ketu (7) have no natural-friendship row; relations involving them are not defined."}


def fav_time(n: int) -> dict[str, Any]:
    lord = RULERS[_check(n)]
    day = WEEKDAYS[WEEKDAY_LORDS.index(lord)] if lord in SEVEN else None
    return {"number": n, "lord": lord, "weekday": day,
            "note": None if day else f"{lord} has no weekday of its own; no day is given"}


def fav_place(n: int) -> dict[str, Any]:
    lord = RULERS[_check(n)]
    return {"number": n, "lord": lord, "direction": data()["direction"].get(lord)}


def fast_day(n: int) -> dict[str, Any]:
    """Weekday associated with the number's lord, for the (text) fasts report; the text is a content-store block."""
    return fav_time(n)


def mantra(n: int) -> dict[str, Any]:
    lord = RULERS[_check(n)]
    return {"number": n, "lord": lord, "mantra": data()["mantra"][lord], "disclaimer": "Traditional belief; not medical, legal or financial advice."}


__all__ = ["data", "fast_day", "fav_lord", "fav_place", "fav_time", "mantra", "relation"]
