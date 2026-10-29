"""Pitra (Pitru) dosha indicators. School-dependent: the engine reports which indicator rules matched
(yogas/rules/doshas.yaml: Sun with a node; a node in the 9th or conjunct the 9th lord), never a verdict on effects."""
from typing import Any

from ..models import Kundli

RULE_IDS = ("pitru_sun_node", "pitru_ninth")


def pitra_dosha(k: Kundli) -> dict[str, Any]:
    by_id = {y["id"]: y for y in k.yogas}
    matched, evaluated = [], []
    for rid in RULE_IDS:
        y = by_id.get(rid)
        if y is None or not y["evaluated"]:
            continue
        evaluated.append(rid)
        if y["present"]:
            matched.append({"id": rid, "name": y["name"], "planets": y.get("planets_involved", [])})
    return {"present": bool(matched), "indicators": matched, "rules_evaluated": evaluated,
            "school_dependent": True,
            "note": "Indicator rules vary between traditions; this lists matched rules only."}


__all__ = ["RULE_IDS", "pitra_dosha"]
