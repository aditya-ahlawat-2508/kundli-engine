"""KP significators with the standard four-level ordering.

House `H` is signified by, strongest first:
  A. planets in the nakshatra of an occupant of H
  B. occupants of H
  C. planets in the nakshatra of the owner of H
  D. the owner of H (the sign lord of H's cusp)
Planet `P` signifies, strongest first:
  1. houses occupied by P's nakshatra lord
  2. the house P occupies
  3. houses owned by P's nakshatra lord
  4. houses owned by P
Houses are the Placidus houses of the KP cusps; the owner of a house is the sign lord of its cusp. Rahu and Ketu own
no house in this implementation (a school-dependent point, listed in docs/open_questions.md). Pure functions of the
planet/cusp tables, no ephemeris access.
"""
from ..data.tables import PLANETS


def house_of(lon: float, cusp_lons: list[float]) -> int:
    """1..12: the house whose cusp interval [cusp i, cusp i+1) contains `lon` (all sidereal degrees)."""
    for i in range(12):
        a, b = cusp_lons[i], cusp_lons[(i + 1) % 12]
        if (lon - a) % 360.0 < (b - a) % 360.0:
            return i + 1
    return 12  # numerically on the last cusp boundary


def _owned(cusp_lords: list[str]) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {p: [] for p in PLANETS}
    for h, lord in enumerate(cusp_lords, 1):
        out[lord].append(h)
    return out


def significators(planet_lons: dict[str, float], star_lords: dict[str, str], cusp_lons: list[float],
                  cusp_lords: list[str]) -> dict[str, dict]:
    """{'planet': {P: {...}}, 'house': {H: {...}}} from planet longitudes, their nakshatra lords and the 12 cusps."""
    placed = {p: house_of(lon, cusp_lons) for p, lon in planet_lons.items()}
    owned = _owned(cusp_lords)
    occupants: dict[int, list[str]] = {h: [] for h in range(1, 13)}
    for p, h in placed.items():
        occupants[h].append(p)

    planet_out: dict[str, dict] = {}
    for p in planet_lons:
        star = star_lords[p]
        lv = [[placed[star]], [placed[p]], list(owned[star]), list(owned[p])]
        seen: list[int] = []
        for level in lv:
            seen += [h for h in level if h not in seen]
        planet_out[p] = {"house": placed[p], "star_lord": star, "levels": {"1_star_lord_occupies": lv[0],
                         "2_occupies": lv[1], "3_star_lord_owns": lv[2], "4_owns": lv[3]}, "houses": seen, "houses_sorted": sorted(seen)}

    house_out: dict[int, dict] = {}
    for h in range(1, 13):
        owner = cusp_lords[h - 1]
        a = [p for p in planet_lons if star_lords[p] in occupants[h]]
        c = [p for p in planet_lons if star_lords[p] == owner]
        ordered: list[str] = []
        for group in (a, occupants[h], c, [owner]):
            ordered += [p for p in group if p not in ordered]
        house_out[h] = {"owner": owner, "occupants": occupants[h], "levels": {
            "A_in_star_of_occupants": a, "B_occupants": occupants[h], "C_in_star_of_owner": c, "D_owner": [owner]},
            "planets": ordered}
    return {"planet": planet_out, "house": house_out}


__all__ = ["house_of", "significators"]
