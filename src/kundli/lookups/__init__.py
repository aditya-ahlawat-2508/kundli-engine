"""Lookup groups of the Basic Astro endpoints (V2 phase 13): thin, tested compositions over `avakahada.py`,
`friendship.py` and `functional.py`. Ghat Chakra and Yunja are NOT implemented: no verified table (open_questions.md)."""
from ..models import Kundli


def astro_details(k: Kundli) -> dict:
    """Moon-based birth attributes plus the panchang elements at birth."""
    pc = k.panchang or {}
    return {"avakahada": k.avakahada,
            "panchang": {x: pc.get(x) for x in ("tithi", "nakshatra", "yoga", "karana", "vara", "hindu_month")},
            "not_implemented": ["ghat_chakra", "yunja"]}


def planet_nature(k: Kundli) -> dict:
    """Friendship matrices (permanent, temporal, five-fold) and the functional nature for the lagna."""
    return {"friendship": k.friendship, "functional_nature": k.functional_nature}


__all__ = ["astro_details", "planet_nature"]
