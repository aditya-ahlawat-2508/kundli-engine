"""Bhava bala (simplified, documented): house lord strength + aspects received on the house."""
from ..core import Core
from ..data.tables import SEVEN
from .shadbala import aspect_value, is_benefic


def bhavabala(core: Core, sb: dict) -> dict:
    """Per house (whole sign): Adhipati bala = lord's Shadbala total (virupas); Drishti bala = (benefic - malefic
    aspect values on the house mid-point)/4; Total = sum. Bhava-dig bala and the occupant terms of BPHS ch.28 are
    NOT included (VERIFY / open_questions)."""
    out = {}
    for h in range(1, 13):
        sign = core.sign_of_house(h)
        mid = sign * 30.0 + 15.0
        lord = core.lord_of_house(h)
        drishti = 0.0
        for q in SEVEN:
            d = (mid - core.lon[q]) % 360.0
            fake = _value_at(core, q, d, sign)
            drishti += fake if is_benefic(core, q) else -fake
        drishti /= 4.0
        adhipati = sb["planets"][lord]["total_virupas"]
        out[str(h)] = {"sign": sign, "lord": lord, "adhipati_bala": adhipati, "drishti_bala": drishti,
                       "total": adhipati + drishti}
    return {"houses": out, "unit": "virupas", "note": "simplified; see docs/open_questions.md"}


def _value_at(core: Core, q: str, d: float, target_sign: int) -> float:
    """aspect_value for a point at angular distance d from q (re-implemented on a synthetic target)."""
    from copy import copy
    c = copy(core)
    c.lon = {**core.lon, "_pt": (core.lon[q] + d) % 360.0}
    c.sign = {**core.sign, "_pt": target_sign}
    return aspect_value(c, q, "_pt")
