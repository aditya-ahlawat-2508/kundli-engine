"""Dashakoota / Porutham (South Indian): nine of the ten poruthams. Each is pass/fail.

Implemented: Dina, Gana, Mahendra, Stree Deergha, Yoni, Rasyadhipati, Vasya, Rajju, Vedha.
NOT implemented: Rasi porutham (the accepted sign-count rule could not be confirmed; docs/open_questions.md), so
the maximum here is 9 and `rasi` is reported as `not_implemented`.

Counts run from the girl's nakshatra to the boy's (inclusive, 1..27). Dina: count mod 9 in {2,4,6,8,0}.
Mahendra: count in {4,7,10,13,16,19,22,25}. Stree Deergha: count > 13. Gana: same gana, or Deva with Manushya.
Yoni: matrix score >= 2. Rasyadhipati: the two Moon-sign lords are the same or mutual non-enemies. Vasya: vashya
matrix score >= 1. Rajju: the two nakshatras are in different rajju groups. Vedha: the nakshatras are not a vedha pair.
All rules and tables are from memory (`# VERIFY`).
"""
from typing import Any

from ..dignity import natural_relation
from .ashtakoota import count_from
from .person import Person
from .tables import load, matrix_score

MAHENDRA = {4, 7, 10, 13, 16, 19, 22, 25}


def rajju_of(nakshatra: str) -> str:
    return next(g for g, ns in load()["rajju"].items() if nakshatra in ns)


def vedha_pair(a: str, b: str) -> bool:
    return a != b and any(a in grp and b in grp for grp in load()["vedha"])


def dashakoota(boy: Person, girl: Person) -> dict[str, Any]:
    n = count_from(girl.nakshatra, boy.nakshatra, 27)
    lords = {boy.sign_lord, girl.sign_lord}
    same_or_friends = (len(lords) == 1 or (natural_relation(boy.sign_lord, girl.sign_lord) != "enemy"
                                           and natural_relation(girl.sign_lord, boy.sign_lord) != "enemy"))
    gana_ok = boy.gana == girl.gana or {boy.gana, girl.gana} == {"Deva", "Manushya"}
    r_boy, r_girl = rajju_of(boy.nakshatra_name), rajju_of(girl.nakshatra_name)
    rows: dict[str, tuple[bool, dict[str, Any]]] = {
        "dina": (n % 9 in (2, 4, 6, 8, 0), {"count": n}),
        "gana": (gana_ok, {"boy": boy.gana, "girl": girl.gana}),
        "mahendra": (n in MAHENDRA, {"count": n}),
        "stree_deergha": (n > 13, {"count": n}),
        "yoni": (matrix_score("yoni_matrix", boy.yoni, girl.yoni) >= 2, {"boy": boy.yoni, "girl": girl.yoni}),
        "rasyadhipati": (same_or_friends, {"boy_lord": boy.sign_lord, "girl_lord": girl.sign_lord}),
        "vasya": (matrix_score("vashya_matrix", boy.vashya, girl.vashya) >= 1, {"boy": boy.vashya, "girl": girl.vashya}),
        "rajju": (r_boy != r_girl, {"boy": r_boy, "girl": r_girl}),
        "vedha": (not vedha_pair(boy.nakshatra_name, girl.nakshatra_name), {"boy": boy.nakshatra_name,
                                                                          "girl": girl.nakshatra_name}),
    }
    poruthams: dict[str, dict[str, Any]] = {k: {"compatible": bool(v[0]), "points": 1 if v[0] else 0, **v[1]} for k, v in rows.items()}
    poruthams["rasi"] = {"compatible": None, "points": 0, "status": "not_implemented"}
    return {"poruthams": poruthams, "total": sum(p["points"] for p in poruthams.values()), "max": 9,
            "tables_verified": not load()["verify"]}


__all__ = ["dashakoota", "rajju_of", "vedha_pair"]
