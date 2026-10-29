"""Saham points (Arabic parts) of the annual chart from `sahams.yaml`.

day: base + plus - minus; night: base + minus - plus, where base is the lagna longitude unless the formula names
another point. `plus`/`minus` may name a graha or an earlier saham (e.g. Yasha uses Punya). Results are
sidereal longitudes in [0, 360) with sign and degree in sign.
"""
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..data.tables import SEVEN, SIGNS
from ..models import Kundli
from .harsha import is_day_chart

FILE = Path(__file__).with_name("sahams.yaml")


@lru_cache(maxsize=1)
def load() -> tuple[dict[str, Any], ...]:
    rows = yaml.safe_load(FILE.read_text(encoding="utf-8"))
    ids: list[str] = []
    for r in rows:
        for key in ("plus", "minus", "base"):
            ref = r.get(key)
            if ref is not None and ref not in SEVEN and ref not in ids:
                raise ValueError(f"saham {r['id']}: {key}={ref!r} is neither a graha nor an earlier saham")
        ids.append(r["id"])
    return tuple(rows)


def sahams(annual: Kundli) -> dict[str, Any]:
    if annual.lagna is None:
        raise ValueError("Sahams need a known birth time")
    day = is_day_chart(annual)
    pos: dict[str, float] = {p.name: p.sidereal_lon for p in annual.planets}
    asc = annual.lagna["longitude"]
    out: dict[str, Any] = {}
    for r in load():
        base = pos[r["base"]] if r.get("base") in pos else asc
        plus, minus = pos[r["plus"]], pos[r["minus"]]
        lon = (base + plus - minus if day else base + minus - plus) % 360.0
        pos[r["id"]] = lon
        out[r["id"]] = {"name": r["name"], "longitude": lon, "sign": int(lon // 30), "sign_name": SIGNS[int(lon // 30)],
                        "degree_in_sign": lon % 30.0, "verify": r["verify"]}
    return {"chart_is_day": day, "sahams": out, "tables_verified": False}


__all__ = ["load", "sahams"]
