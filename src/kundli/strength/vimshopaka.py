"""Vimshopaka bala (Shodashavarga scheme, 20 points)."""
from ..core import Core
from ..data.tables import SHODASHAVARGA_WEIGHTS, VIMSHOPAKA_SCORE
from ..dignity import dignity


def vimshopaka(core: Core) -> dict:
    """For each graha: sum over the 16 vargas of weight x score(dignity in that varga)/20. The dignity in each
    varga uses sign-level rules (own/exalted/debilitated/compound relation with the varga-sign lord, temporal
    friendship taken from that varga's own sign positions)."""
    out: dict = {}
    names = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
    for p in names:
        total, detail = 0.0, {}
        for v, w in SHODASHAVARGA_WEIGHTS.items():
            signs = {n: core.varga[v][n] for n in names}
            d = dignity(p, signs[p], -1.0, signs)  # deg=-1 disables the moolatrikona degree window
            detail[v] = d
            total += w * VIMSHOPAKA_SCORE[d] / 20.0
        out[p] = {"score": total, "of": 20.0, "dignities": detail}
    return out
