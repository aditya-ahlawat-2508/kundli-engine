"""Ashtakavarga: Bhinnashtakavarga (BAV), Sarvashtakavarga (SAV), prastara, shodhana, shodhya pinda."""
from ..core import Core
from ..data.tables import (
    BAV_CONTRIB,
    EKADHIPATYA,
    GRAHA_GUNAKARA,
    LAGNA_BAV_CONTRIB,
    LAGNA_BAV_TOTAL,
    RASI_GUNAKARA,
    SAV_TOTAL,
    SEVEN,
)

REFS = [*SEVEN, "Lagna"]


def prastara(core: Core, target: str) -> dict[str, list[int]]:
    """8 rows (contributors: 7 grahas + Lagna) x 12 signs of 0/1 bindus for `target`'s BAV."""
    assert core.lagna_sign is not None
    rows: dict[str, list[int]] = {}
    for c in REFS:
        csign = core.lagna_sign if c == "Lagna" else core.sign[c]
        row = [0] * 12
        for h in BAV_CONTRIB[target][c]:
            row[(csign + h - 1) % 12] = 1
        rows[c] = row
    return rows


def lagna_bav(core: Core) -> dict:
    """Bhinnashtakavarga of the Lagna as target: 8 contributor rows x 12 signs, column sums, grand total (49)."""
    assert core.lagna_sign is not None
    rows: dict[str, list[int]] = {}
    for c in REFS:
        csign = core.lagna_sign if c == "Lagna" else core.sign[c]
        row = [0] * 12
        for h in LAGNA_BAV_CONTRIB[c]:
            row[(csign + h - 1) % 12] = 1
        rows[c] = row
    bindus = [sum(rows[c][s] for c in REFS) for s in range(12)]
    return {"prastara": rows, "bav": bindus, "total": sum(bindus), "expected_total": LAGNA_BAV_TOTAL}


def bav(core: Core, target: str) -> list[int]:
    rows = prastara(core, target)
    return [sum(rows[c][s] for c in REFS) for s in range(12)]


def trikona_shodhana(v: list[int]) -> list[int]:
    """For each trikona (signs i, i+4, i+8): if none is zero, subtract the smallest from all three."""
    out = list(v)
    for i in range(4):
        g = [i, i + 4, i + 8]
        vals = [out[s] for s in g]
        if all(x > 0 for x in vals):
            m = min(vals)
            for s in g:
                out[s] -= m
    return out


def ekadhipatya_shodhana(v: list[int], occupied: set[int], planet_pairs=EKADHIPATYA) -> list[int]:
    """Signs owned by the same planet. Both empty: subtract the smaller from both (equal => both zero).
    One occupied: the empty sign is capped at the occupied sign's value. Both occupied: unchanged. (VERIFY)"""
    out = list(v)
    for a, b in planet_pairs.values():
        oa, ob = a in occupied, b in occupied
        if not oa and not ob:
            m = min(out[a], out[b])
            out[a] -= m
            out[b] -= m
        elif oa != ob:
            occ, emp = (a, b) if oa else (b, a)
            out[emp] = min(out[emp], out[occ])
    return out


def shodhya_pinda(reduced: list[int], planet: str, occupants: dict[int, list[str]]) -> dict:
    """Rasi pinda = sum(reduced x sign multiplier); Graha pinda = sum over occupying grahas of
    (reduced bindus in their sign x graha multiplier); Shodhya pinda = rasi + graha pinda."""
    rasi = sum(reduced[s] * RASI_GUNAKARA[s] for s in range(12))
    graha = sum(reduced[s] * GRAHA_GUNAKARA[g] for s in range(12) for g in occupants.get(s, []) if g in GRAHA_GUNAKARA)
    return {"rasi_pinda": rasi, "graha_pinda": graha, "shodhya_pinda": rasi + graha}


def ashtakavarga(core: Core) -> dict:
    if core.lagna_sign is None:
        raise ValueError("Ashtakavarga needs the lagna (birth time)")
    bavs = {p: bav(core, p) for p in SEVEN}
    sav = [sum(bavs[p][s] for p in SEVEN) for s in range(12)]
    occupants: dict[int, list[str]] = {}
    for p in SEVEN:
        occupants.setdefault(core.sign[p], []).append(p)
    occupied = set(occupants)
    reductions, pinda = {}, {}
    for p in SEVEN:
        t = trikona_shodhana(bavs[p])
        e = ekadhipatya_shodhana(t, occupied)
        reductions[p] = {"trikona": t, "ekadhipatya": e}
        pinda[p] = shodhya_pinda(e, p, occupants)
    lagna = core.lagna_sign
    return {
        "bav": bavs,
        "bav_totals": {p: sum(v) for p, v in bavs.items()},
        "sav": sav,
        "sav_total": sum(sav),
        "sav_by_house": {str(h): sav[(lagna + h - 1) % 12] for h in range(1, 13)},
        "bav_by_house": {p: {str(h): bavs[p][(lagna + h - 1) % 12] for h in range(1, 13)} for p in SEVEN},
        "prastara": {p: prastara(core, p) for p in SEVEN},
        "shodhana": reductions,
        "shodhya_pinda": pinda,
        "expected_sav_total": SAV_TOTAL,
        "lagna_bav": lagna_bav(core),
    }
