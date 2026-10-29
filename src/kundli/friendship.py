"""Planetary friendship matrices for the seven grahas: permanent (naisargika), temporal (tatkalika) and
five-fold (panchadha maitri). Temporal friendship depends on the sign positions in the chart."""
from .data.tables import SEVEN
from .dignity import compound_relation, natural_relation, temporal_relation


def friendship_tables(sign: dict[str, int]) -> dict[str, dict[str, dict[str, str]]]:
    """{'permanent'|'temporal'|'five_fold': {planet: {other: relation}}} (a planet has no row entry for itself)."""
    out: dict[str, dict[str, dict[str, str]]] = {"permanent": {}, "temporal": {}, "five_fold": {}}
    for a in SEVEN:
        out["permanent"][a], out["temporal"][a], out["five_fold"][a] = {}, {}, {}
        for b in SEVEN:
            if a == b:
                continue
            out["permanent"][a][b] = natural_relation(a, b)
            out["temporal"][a][b] = temporal_relation(sign[a], sign[b])
            out["five_fold"][a][b] = compound_relation(a, b, sign[a], sign[b])
    return out
