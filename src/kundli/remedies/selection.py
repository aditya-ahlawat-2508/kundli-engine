"""Facts and the rule evaluator behind the remedy endpoints. Nothing here writes remedy text."""
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..data.tables import SEVEN
from ..models import Kundli

FILE = Path(__file__).with_name("rules.yaml")
PREDICATES = {"functional", "dignity", "combust", "retrograde", "shadbala_ratio_below", "house", "lord_of_any", "any_of"}
DISCLAIMER = ("Traditional belief and cultural practice; not medical, legal or financial advice. No outcome is guaranteed.")


@lru_cache(maxsize=1)
def rules() -> dict[str, Any]:
    r = yaml.safe_load(FILE.read_text(encoding="utf-8"))

    def check(when: dict[str, Any], rid: str) -> None:
        bad = set(when) - PREDICATES
        if bad:
            raise ValueError(f"rule {rid}: unknown predicates {sorted(bad)}")
        for sub in when.get("any_of", []):
            check(sub, rid)

    for rule in r["graha_shanti"]:
        if not rule.get("source") or "verify" not in rule or set(rule["planets"]) - set(SEVEN):
            raise ValueError(f"rule {rule.get('id')!r} is malformed")
        check(rule["when"], rule["id"])
    for rule in r["dosha_pujas"]:
        if not rule.get("source") or "verify" not in rule:
            raise ValueError(f"rule {rule.get('id')!r} is malformed")
    if set(r["rudraksha_mukhi"].values()) != set(range(1, 10)):
        raise ValueError("rudraksha_mukhi must map the nine grahas to mukhi 1..9")
    return r


def planet_facts(k: Kundli) -> dict[str, dict[str, Any]]:
    """Facts for the seven grahas that selection rules read (needs a birth time: functional nature, houses, Shadbala)."""
    if k.lagna is None or k.functional_nature is None or k.shadbala is None:
        raise ValueError("remedy selection needs a known birth time")
    out: dict[str, dict[str, Any]] = {}
    for p in k.planets:
        if p.name in SEVEN:
            sb = k.shadbala["planets"][p.name]
            out[p.name] = {"functional": k.functional_nature[p.name], "dignity": p.dignity, "combust": p.combust,
                           "retrograde": p.retrograde, "shadbala_ratio": sb["ratio"], "house": p.rashi_house,
                           "lord_of": list(p.lord_of_houses)}
    return out


def holds(when: dict[str, Any], f: dict[str, Any]) -> bool:
    for name, arg in when.items():
        if name == "functional" and f["functional"] not in arg:
            return False
        if name == "dignity" and f["dignity"] not in arg:
            return False
        if name == "combust" and f["combust"] != arg:
            return False
        if name == "retrograde" and f["retrograde"] != arg:
            return False
        if name == "shadbala_ratio_below" and not f["shadbala_ratio"] < arg:
            return False
        if name == "house" and f["house"] not in arg:
            return False
        if name == "lord_of_any" and not set(f["lord_of"]) & set(arg):
            return False
        if name == "any_of" and not any(holds(sub, f) for sub in arg):
            return False
    return True


def matched_rules(planet: str, f: dict[str, Any]) -> list[str]:
    return [r["id"] for r in rules()["graha_shanti"] if planet in r["planets"] and holds(r["when"], f)]


__all__ = ["DISCLAIMER", "holds", "matched_rules", "planet_facts", "rules"]
