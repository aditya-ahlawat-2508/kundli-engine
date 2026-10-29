"""Krishnamurti Paddhati lords: nakshatra lord, sub lord and sub-sub lord, and KP house cusps (sidereal)."""
from typing import Any

from ..config import EngineConfig
from ..data.tables import NAKSHATRAS, SIGN_LORDS, SIGNS, VIM_ORDER, VIM_YEARS
from ..houses import compute_houses
from ..models import Kundli
from ..nakshatra import fraction_elapsed, nakshatra_index, nakshatra_lord


def _split(start_lord: str, frac: float) -> tuple[str, float]:
    """Divide a span in proportion to Vimshottari years beginning with `start_lord`; return the part lord containing
    `frac` (0..1 of the span) and the fraction (0..1) elapsed inside that part."""
    i0 = VIM_ORDER.index(start_lord)
    pos, acc = frac * 120.0, 0.0
    for k in range(9):
        lord = VIM_ORDER[(i0 + k) % 9]
        y = float(VIM_YEARS[lord])
        if pos < acc + y or k == 8:
            return lord, min(max((pos - acc) / y, 0.0), 1.0)
        acc += y
    raise AssertionError("unreachable")


def kp_lords(lon: float) -> tuple[str, str, str]:
    """(nakshatra lord, sub lord, sub-sub lord) of a sidereal longitude."""
    star = nakshatra_lord(nakshatra_index(lon))
    sub, f = _split(star, fraction_elapsed(lon))
    subsub, _ = _split(sub, f)
    return star, sub, subsub


def kp_row(lon: float) -> dict[str, Any]:
    sign = int(lon % 360 // 30)
    star, sub, subsub = kp_lords(lon)
    return {"longitude": lon % 360, "sign": sign, "sign_name": SIGNS[sign], "sign_lord": SIGN_LORDS[sign],
            "nakshatra": NAKSHATRAS[nakshatra_index(lon)], "nakshatra_lord": star, "sub_lord": sub,
            "sub_sub_lord": subsub}


def kp_cusps(k: Kundli) -> list[dict[str, Any]]:
    """The 12 KP (Placidus) cusps in the sidereal zodiac of the chart's ayanamsa. Placidus is unavailable at polar
    latitudes; compute_houses then falls back to equal houses (flag in `fallback`)."""
    if k.lagna is None:
        raise ValueError("KP cusps need a known birth time")
    cfg = EngineConfig(**k.header["config"]).model_copy(update={"house_system": "placidus"})
    p = k.birth["place"]
    hs = compute_houses(k.birth["jd_ut"], p["lat"], p["lon"], cfg)
    rows = []
    for i, c in enumerate(hs.starts, 1):
        row = kp_row(c)
        row["house"] = i
        row["fallback"] = hs.fallback
        rows.append(row)
    return rows


__all__ = ["kp_cusps", "kp_lords", "kp_row"]
