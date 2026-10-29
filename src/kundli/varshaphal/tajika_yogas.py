"""Tajika yogas between the seven grahas of the annual chart: Ithasala (applying) and Ishrafa (separating).

Tajika aspects are by sign distance d = (sign_b - sign_a) % 12 + 1: conjunction d=1; friendly aspects d in {3, 5, 9, 11}
(sextile/trine); inimical aspects d in {4, 7, 10} (square/opposition); d in {2, 6, 8, 12} = no aspect.
For an aspecting pair the faster graha (`SPEED_ORDER`) is F and the slower S; delta = degree of S in its sign minus
degree of F in its sign. With 0 <= delta <= mutual orb the pair is in Ithasala (F is behind S and applying); with
-orb <= delta < 0 it is in Ishrafa (F has passed S and is separating). The mutual orb is half the sum of the
deeptamsas. `purna` marks delta < 1 degree. Retrograde motion (which reverses applying/separating for the retrograde
graha) is reported but NOT used to flip the result. Nakta, Yamaya, Kambool and the other Tajika yogas are not
implemented (docs/open_questions.md). Orbs and speed order are `# VERIFY`.
"""
from itertools import combinations
from typing import Any

from ..data.tables import SEVEN
from ..models import Kundli
from .tables import DEEPTAMSA, SPEED_ORDER

FRIENDLY, INIMICAL = {3, 5, 9, 11}, {4, 7, 10}


def aspect_kind(sign_a: int, sign_b: int) -> str | None:
    d = (sign_b - sign_a) % 12 + 1
    if d == 1:
        return "conjunction"
    if d in FRIENDLY:
        return "friendly"
    if d in INIMICAL:
        return "inimical"
    return None


def tajika_yogas(annual: Kundli) -> dict[str, Any]:
    pl = {p.name: p for p in annual.planets if p.name in SEVEN}
    yogas: list[dict[str, Any]] = []
    for a, b in combinations(SEVEN, 2):
        f, s = sorted((a, b), key=SPEED_ORDER.index)
        kind = aspect_kind(pl[f].sign, pl[s].sign) or aspect_kind(pl[s].sign, pl[f].sign)
        if kind is None:
            continue
        orb = (DEEPTAMSA[f] + DEEPTAMSA[s]) / 2.0
        delta = pl[s].degree_in_sign - pl[f].degree_in_sign
        if 0.0 <= delta <= orb:
            name = "ithasala"
        elif -orb <= delta < 0.0:
            name = "ishrafa"
        else:
            continue
        yogas.append({"yoga": name, "faster": f, "slower": s, "aspect": kind, "delta_degrees": delta, "orb": orb,
                      "purna": abs(delta) < 1.0, "faster_retrograde": pl[f].retrograde,
                      "slower_retrograde": pl[s].retrograde})
    return {"yogas": yogas, "implemented": ["ithasala", "ishrafa"], "tables_verified": False}


__all__ = ["aspect_kind", "tajika_yogas"]
