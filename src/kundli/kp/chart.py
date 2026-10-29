"""One-call KP chart for a finished Kundli: planets and cusps with lord chains, plus all significators."""
from typing import Any

from ..data.tables import PLANETS
from ..models import Kundli
from .lords import kp_cusps, kp_row
from .significators import house_of, significators


def kp_chart(k: Kundli) -> dict[str, Any]:
    if k.lagna is None:
        raise ValueError("KP needs a known birth time")
    cusps = kp_cusps(k)
    cusp_lons = [c["longitude"] for c in cusps]
    cusp_lords = [c["sign_lord"] for c in cusps]
    lon = {p.name: p.sidereal_lon for p in k.planets if p.name in PLANETS}
    rows = {p: {**kp_row(lon[p]), "house": house_of(lon[p], cusp_lons)} for p in PLANETS}
    sig = significators(lon, {p: rows[p]["nakshatra_lord"] for p in PLANETS}, cusp_lons, cusp_lords)
    return {"ayanamsa": k.header["config"]["ayanamsa"], "house_system": "placidus", "planets": rows, "cusps": cusps,
            "significators": sig}


__all__ = ["kp_chart"]
