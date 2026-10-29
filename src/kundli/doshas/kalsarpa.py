"""Kaal Sarp dosha: all grahas hemmed between Rahu and Ketu; type named by Rahu's house; full versus partial per config."""
from typing import Any

from ..data.tables import KAAL_SARPA_TYPES
from ..models import Kundli

SEVEN = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")


def _arc(a: float, b: float, x: float) -> bool:
    return (x - a) % 360.0 <= (b - a) % 360.0


def kaal_sarpa(k: Kundli) -> dict[str, Any]:
    """All seven grahas between Rahu and Ketu = full Kaal Sarp. `direction`: 'ascending' when they lie on the arc
    from Ketu to Rahu, 'descending' on the arc from Rahu to Ketu. `partial` = exactly one graha outside the arc.
    Type is named by Rahu's house (Anant ... Sheshnaag)."""
    pl = {p.name: p for p in k.planets}
    rahu, ketu = pl["Rahu"].sidereal_lon, pl["Ketu"].sidereal_lon
    lons = [pl[p].sidereal_lon for p in SEVEN]
    in_rk = sum(_arc(rahu, ketu, x) for x in lons)
    in_kr = sum(_arc(ketu, rahu, x) for x in lons)
    full = in_rk == 7 or in_kr == 7
    partial = not full and (in_rk == 6 or in_kr == 6)
    include_partial = k.header["config"].get("kalsarpa_variant") == "include_partial"
    direction = None if not (full or partial) else ("descending" if in_rk > in_kr else "ascending")
    house = pl["Rahu"].rashi_house
    return {"present": full or (partial and include_partial), "full": full, "partial": partial, "direction": direction,
            "type": KAAL_SARPA_TYPES[house - 1] if (full or partial) and house else None, "rahu_house": house}


__all__ = ["kaal_sarpa"]
