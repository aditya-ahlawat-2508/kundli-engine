"""Match obstructions and their cancellations: Manglik match, Nadi dosha, Bhakoot dosha.

* Manglik: both manglik (effective after cancellations) or neither = no obstruction; exactly one = obstruction.
* Nadi dosha: same nadi. Cancelled when the Moon signs are the same but the nakshatras differ, or the nakshatras
  are the same but the padas differ (a commonly cited pair of exceptions; school-dependent, `# VERIFY`).
* Bhakoot dosha: sign distance 2/12, 5/9 or 6/8. Cancelled when the two Moon-sign lords are the same or mutual
  friends (`# VERIFY`).
"""
from typing import Any

from ..dignity import natural_relation
from ..models import Kundli
from .ashtakoota import BAD_SIGN_DISTANCES, sign_distance
from .person import Person


def manglik_match(boy: Kundli, girl: Kundli) -> dict[str, Any]:
    assert boy.doshas is not None and girl.doshas is not None
    b, g = boy.doshas["manglik"], girl.doshas["manglik"]
    bm, gm = bool(b["is_manglik"]), bool(g["is_manglik"])
    return {"boy_manglik": bm, "girl_manglik": gm, "boy_intensity_percent": b["intensity_percent"],
            "girl_intensity_percent": g["intensity_percent"], "obstruction": bm != gm,
            "note": "both manglik or neither: no obstruction" if bm == gm else "only one partner is manglik"}


def nadi_dosha(boy: Person, girl: Person) -> dict[str, Any]:
    present = boy.nadi == girl.nadi
    cancelled_by = []
    if present and boy.sign == girl.sign and boy.nakshatra != girl.nakshatra:
        cancelled_by.append("same_sign_different_nakshatra")
    if present and boy.nakshatra == girl.nakshatra and boy.pada != girl.pada:
        cancelled_by.append("same_nakshatra_different_pada")
    return {"present": present, "cancelled_by": cancelled_by, "effective": present and not cancelled_by,
            "boy_nadi": boy.nadi, "girl_nadi": girl.nadi}


def bhakoot_dosha(boy: Person, girl: Person) -> dict[str, Any]:
    d = sign_distance(boy, girl)
    present = d in BAD_SIGN_DISTANCES
    cancelled_by = []
    if present and (boy.sign_lord == girl.sign_lord or (natural_relation(boy.sign_lord, girl.sign_lord) == "friend"
                                                        and natural_relation(girl.sign_lord, boy.sign_lord) == "friend")):
        cancelled_by.append("sign_lords_same_or_mutual_friends")
    return {"present": present, "sign_distance": d, "cancelled_by": cancelled_by, "effective": present and not cancelled_by}


def obstructions(boy_k: Kundli, girl_k: Kundli, boy: Person, girl: Person) -> dict[str, Any]:
    out = {"nadi_dosha": nadi_dosha(boy, girl), "bhakoot_dosha": bhakoot_dosha(boy, girl)}
    if boy_k.doshas and girl_k.doshas and boy_k.lagna and girl_k.lagna:
        out["manglik"] = manglik_match(boy_k, girl_k)
    else:
        out["manglik"] = {"status": "needs_birth_time_for_both"}
    return out


__all__ = ["bhakoot_dosha", "manglik_match", "nadi_dosha", "obstructions"]
