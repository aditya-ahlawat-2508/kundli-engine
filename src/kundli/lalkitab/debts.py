"""Lal Kitab debts (rin) from debts.yaml: a rule matches the listed grahas standing in the listed houses."""
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .tables import PLANETS

FILE = Path(__file__).with_name("debts.yaml")


@lru_cache(maxsize=1)
def rules() -> tuple[dict[str, Any], ...]:
    rows = yaml.safe_load(FILE.read_text(encoding="utf-8"))
    for r in rows:
        if not r.get("source") or "verify" not in r or set(r["planets"]) - set(PLANETS) or not all(1 <= h <= 12 for h in r["houses"]):
            raise ValueError(f"debt rule {r.get('id')!r} is malformed")
    return tuple(rows)


def debts(planet_house: dict[str, int]) -> dict[str, Any]:
    found = []
    for r in rules():
        hits = [{"planet": p, "house": planet_house[p]} for p in r["planets"] if planet_house[p] in r["houses"]]
        found.append({"id": r["id"], "name": r["name"], "present": bool(hits), "matched": hits, "verify": r["verify"]})
    return {"debts": found, "any_present": any(d["present"] for d in found), "tables_verified": False,
            "not_implemented": ["bhratri_rin", "bahan_rin", "putra_rin", "guru_rin", "other classical debts"]}


__all__ = ["debts", "rules"]
