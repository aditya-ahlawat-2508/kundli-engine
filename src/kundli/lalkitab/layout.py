"""Lal Kitab chart layout. The edition is a convention (`EngineConfig.lalkitab_edition`):
* `lagna_houses`: houses are the whole-sign houses counted from the lagna (needs a birth time).
* `fixed_aries` (default): house n is zodiac sign n counted from Aries, whatever the lagna (the "Kaal Purush" layout).
Houses 1..12, each with the grahas standing in it."""
from typing import Any

from ..data.tables import SIGNS
from ..models import Kundli
from .tables import PLANETS


def house_of(k: Kundli, planet: str, edition: str) -> int:
    p = next(x for x in k.planets if x.name == planet)
    if edition == "fixed_aries":
        return p.sign + 1
    if k.lagna is None:
        raise ValueError("the lagna_houses layout needs a known birth time (or use lalkitab_edition=fixed_aries)")
    return (p.sign - k.lagna["sign"]) % 12 + 1


def layout(k: Kundli, edition: str) -> dict[str, Any]:
    placed = {p: house_of(k, p, edition) for p in PLANETS}
    lag = k.lagna["sign"] if k.lagna else None
    houses = []
    for h in range(1, 13):
        sign = h - 1 if edition == "fixed_aries" else (None if lag is None else (lag + h - 1) % 12)
        houses.append({"house": h, "sign": sign, "sign_name": None if sign is None else SIGNS[sign],
                       "planets": [p for p in PLANETS if placed[p] == h]})
    return {"edition": edition, "houses": houses, "planet_house": placed}


__all__ = ["house_of", "layout"]
