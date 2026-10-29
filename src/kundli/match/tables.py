"""Loader for match/tables.yaml with structural validation (shape, names, coverage)."""
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..data.tables import NAKSHATRAS, YONI_BY_NAK

FILE = Path(__file__).with_name("tables.yaml")


@lru_cache(maxsize=1)
def load() -> dict[str, Any]:
    t = yaml.safe_load(FILE.read_text(encoding="utf-8"))
    for name in ("vashya_matrix", "yoni_matrix", "gana_matrix"):
        m = t[name]
        n = len(m["order"])
        if set(m["rows"]) != set(m["order"]) or any(len(r) != n for r in m["rows"].values()):
            raise ValueError(f"{name}: rows must match order and be square")
    if set(t["yoni_matrix"]["order"]) != set(YONI_BY_NAK):
        raise ValueError("yoni_matrix names must be exactly the yonis used by YONI_BY_NAK")
    r = [n for ns in t["rajju"].values() for n in ns]
    v = [n for grp in t["vedha"] for n in grp]
    for what, names in (("rajju", r), ("vedha", v)):
        if sorted(names) != sorted(NAKSHATRAS):
            raise ValueError(f"{what} must list every nakshatra exactly once")
    return t


def matrix_score(name: str, boy: str, girl: str) -> float:
    m = load()[name]
    return m["rows"][boy][m["order"].index(girl)]


__all__ = ["load", "matrix_score"]
