"""Ashtakoota (8 kootas, 36 points). Inputs are the Moon sign and nakshatra of the boy and the girl.

| koota        | max | rule |
|--------------|-----|------|
| Varna        | 1   | boy's varna rank >= girl's |
| Vashya       | 2   | vashya matrix (boy row, girl column) |
| Tara         | 3   | 1.5 per direction where (count from one nakshatra to the other) mod 9 is not 3, 5, 7; the two inclusive counts sum to 29, so the score is always 1.5 or 3 |
| Yoni         | 4   | yoni matrix |
| Graha Maitri | 5   | natural friendship of the two Moon-sign lords (both directions) |
| Gana         | 6   | gana matrix |
| Bhakoot      | 7   | 0 if the signs are 2/12, 5/9 or 6/8 from each other, else 7 |
| Nadi         | 8   | 0 if both nakshatras have the same nadi, else 8 |

All matrices live in tables.yaml (`verify: true`); the rules above are the standard scheme from memory.
"""
from typing import Any

from ..dignity import natural_relation
from .person import Person
from .tables import load, matrix_score

MAX = {"varna": 1, "vashya": 2, "tara": 3, "yoni": 4, "graha_maitri": 5, "gana": 6, "bhakoot": 7, "nadi": 8}
MAITRI = {("friend", "friend"): 5.0, ("friend", "neutral"): 4.0, ("neutral", "friend"): 4.0,
          ("neutral", "neutral"): 3.0, ("friend", "enemy"): 1.0, ("enemy", "friend"): 1.0,
          ("neutral", "enemy"): 0.5, ("enemy", "neutral"): 0.5, ("enemy", "enemy"): 0.0}
BAD_SIGN_DISTANCES = {2, 12, 5, 9, 6, 8}
BAD_TARA_REMAINDERS = {3, 5, 7}  # Vipat, Pratyari, Vadha


def count_from(a: int, b: int, modulus: int) -> int:
    """Inclusive count from index a to index b going forward (1..modulus)."""
    return (b - a) % modulus + 1


def tara_remainders(boy: Person, girl: Person) -> tuple[int, int]:
    return count_from(girl.nakshatra, boy.nakshatra, 27) % 9, count_from(boy.nakshatra, girl.nakshatra, 27) % 9


def sign_distance(boy: Person, girl: Person) -> int:
    return count_from(boy.sign, girl.sign, 12)


def maitri_relations(boy: Person, girl: Person) -> tuple[str, str]:
    if boy.sign_lord == girl.sign_lord:
        return "friend", "friend"
    return natural_relation(boy.sign_lord, girl.sign_lord), natural_relation(girl.sign_lord, boy.sign_lord)


def ashtakoota(boy: Person, girl: Person) -> dict[str, Any]:
    t = load()
    rank = t["varna_rank"]
    r1, r2 = tara_remainders(boy, girl)
    rel = maitri_relations(boy, girl)
    dist = sign_distance(boy, girl)
    rows: dict[str, tuple[float, dict[str, Any]]] = {
        "varna": (1.0 if rank[boy.varna] >= rank[girl.varna] else 0.0, {"boy": boy.varna, "girl": girl.varna}),
        "vashya": (float(matrix_score("vashya_matrix", boy.vashya, girl.vashya)), {"boy": boy.vashya, "girl": girl.vashya}),
        "tara": (1.5 * ((r1 not in BAD_TARA_REMAINDERS) + (r2 not in BAD_TARA_REMAINDERS)),
                 {"girl_to_boy_remainder": r1, "boy_to_girl_remainder": r2}),
        "yoni": (float(matrix_score("yoni_matrix", boy.yoni, girl.yoni)), {"boy": boy.yoni, "girl": girl.yoni}),
        "graha_maitri": (MAITRI[rel], {"boy_lord": boy.sign_lord, "girl_lord": girl.sign_lord,
                                       "boy_sees_girl": rel[0], "girl_sees_boy": rel[1]}),
        "gana": (float(matrix_score("gana_matrix", boy.gana, girl.gana)), {"boy": boy.gana, "girl": girl.gana}),
        "bhakoot": (0.0 if dist in BAD_SIGN_DISTANCES else 7.0, {"boy_sign": boy.sign_name, "girl_sign": girl.sign_name,
                                                                  "sign_distance": dist}),
        "nadi": (0.0 if boy.nadi == girl.nadi else 8.0, {"boy": boy.nadi, "girl": girl.nadi}),
    }
    kootas = {k: {"points": v[0], "max": MAX[k], **v[1]} for k, v in rows.items()}
    total = sum(v[0] for v in rows.values())
    return {"kootas": kootas, "total": total, "max": 36, "tables_verified": not t["verify"]}


def verdict(total: float) -> str:
    for band in load()["verdict_bands"]:
        if total >= band["min"]:
            return band["label"]
    return "not_recommended"


__all__ = ["MAX", "ashtakoota", "count_from", "sign_distance", "tara_remainders", "verdict"]
