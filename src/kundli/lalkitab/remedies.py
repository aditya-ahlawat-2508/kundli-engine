"""Lal Kitab remedy SELECTION (no remedy text is written here). For a graha in a house the engine reports the facts that
make a remedy relevant and the content-store key under which the remedy text lives:
`lalkitab.remedy.<planet>.<house>` (the adapter attaches the stored block, or `content_missing`)."""
from typing import Any

from .debts import debts
from .tables import DEBILITATED_HOUSE, PAKKA_GHAR, PLANETS

DISCLAIMER = "Traditional belief only; not medical, legal or financial advice."


def remedy_for(planet: str, planet_house: dict[str, int]) -> dict[str, Any]:
    name = planet.strip().capitalize()
    if name not in PLANETS:
        raise ValueError(f"unknown planet {planet!r}; use one of {list(PLANETS)}")
    h = planet_house[name]
    related = [d["id"] for d in debts(planet_house)["debts"] if any(m["planet"] == name for m in d["matched"])]
    return {"planet": name, "house": h, "in_pakka_ghar": h in PAKKA_GHAR[name],
            "in_debilitation_house": DEBILITATED_HOUSE.get(name) == h, "related_debts": related,
            "remedy_keys": [f"lalkitab.remedy.{name.lower()}.{h}"],
            "disclaimer": DISCLAIMER}


__all__ = ["DISCLAIMER", "remedy_for"]
