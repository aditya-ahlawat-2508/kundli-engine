"""Muntha: the natal lagna sign advanced one sign per completed year of age. Its lord and its house in the annual chart
are reported; houses 6, 8 and 12 are traditionally regarded as unfavourable for Muntha (`# VERIFY`)."""
from typing import Any

from ..data.tables import SIGN_LORDS, SIGNS
from ..models import Kundli

UNFAVOURABLE_HOUSES = (6, 8, 12)


def muntha(natal: Kundli, annual: Kundli, age: int) -> dict[str, Any]:
    if natal.lagna is None or annual.lagna is None:
        raise ValueError("Muntha needs a known birth time")
    sign = (natal.lagna["sign"] + age) % 12
    lord = SIGN_LORDS[sign]
    lord_p = next(p for p in annual.planets if p.name == lord)
    house = (sign - annual.lagna["sign"]) % 12 + 1
    return {"age": age, "sign": sign, "sign_name": SIGNS[sign], "house_in_annual_chart": house, "lord": lord,
            "lord_house_in_annual_chart": lord_p.rashi_house, "lord_retrograde": lord_p.retrograde,
            "occupants": sorted(p.name for p in annual.planets if p.sign == sign),
            "traditionally_unfavourable": house in UNFAVOURABLE_HOUSES}


__all__ = ["UNFAVOURABLE_HOUSES", "muntha"]
