"""Panchavargeeya bala (Tajika): strength of the seven grahas in the annual chart from five divisions.

| division | max | rule |
|----------|-----|------|
| Kshetra  | 30  | relation of the graha to the lord of the occupied sign |
| Uccha    | 20  | arc from the debilitation point / 9 (so 20 at the exaltation point) |
| Hadda    | 15  | relation to the hadda (Egyptian-term) lord of its degree |
| Drekkana | 10  | relation to the lord of its drekkana sign (D3) |
| Navamsa  | 5   | relation to the lord of its navamsa sign (D9) |

Relation to a lord = fraction of the maximum: own 1, great friend 3/4, friend 1/2, neutral 1/4, enemy 1/8, great enemy
1/16 (panchadha maitri of `dignity.compound_relation`, temporal friendship from the annual chart signs). The result is
the sum / 4 in virupas (max 20). Tables are `# VERIFY` (see `tables.py`).
"""
from typing import Any

from .. import vargas
from ..data.tables import EXALTATION, SEVEN, SIGN_LORDS
from ..dignity import compound_relation
from ..models import Kundli
from .tables import PANCHAVARGEEYA_MAX, RELATION_FRACTION, hadda_lord


def _fraction(planet: str, lord: str, signs: dict[str, int]) -> tuple[str, float]:
    if planet == lord:
        return "own", 1.0
    rel = compound_relation(planet, lord, signs[planet], signs[lord])
    return rel, RELATION_FRACTION[rel]


def uccha_virupas(planet: str, lon: float) -> float:
    ex_sign, ex_deg = EXALTATION[planet]
    debil = ((ex_sign + 6) % 12) * 30.0 + ex_deg
    arc = (lon - debil) % 360.0
    return min(arc, 360.0 - arc) / 9.0


def panchavargeeya(annual: Kundli) -> dict[str, Any]:
    pl = {p.name: p for p in annual.planets}
    signs = {n: pl[n].sign for n in SEVEN}
    out: dict[str, Any] = {}
    for n in SEVEN:
        p = pl[n]
        lon = p.sidereal_lon
        d3_sign, _ = vargas.VARGAS["D3"](lon)
        d9_sign, _ = vargas.VARGAS["D9"](lon)
        lords = {"kshetra": SIGN_LORDS[p.sign], "hadda": hadda_lord(p.sign, p.degree_in_sign),
                 "drekkana": SIGN_LORDS[d3_sign], "navamsa": SIGN_LORDS[d9_sign]}
        comps: dict[str, Any] = {}
        for key, lord in lords.items():
            rel, frac = _fraction(n, lord, signs)
            comps[key] = {"lord": lord, "relation": rel, "virupas": PANCHAVARGEEYA_MAX[key] * frac}
        comps["uccha"] = {"virupas": uccha_virupas(n, lon)}
        total = sum(c["virupas"] for c in comps.values())
        out[n] = {"components": comps, "total_virupas": total, "bala": total / 4.0}
    return {"planets": out, "max_bala": 20.0, "tables_verified": False}


__all__ = ["panchavargeeya", "uccha_virupas"]
