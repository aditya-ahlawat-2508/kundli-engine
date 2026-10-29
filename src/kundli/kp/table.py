"""The KP 249-division table, generated (not typed in).

Each of the 27 nakshatras (13deg20') is cut into 9 sub-lords proportional to Vimshottari years starting from the
nakshatra lord; 27 x 9 = 243 pieces. Pieces that straddle a 30-degree sign boundary are cut in two, which adds 6,
giving the classical 249 divisions. The count is a self-check of the arithmetic (asserted in tests).
"""
from functools import lru_cache
from typing import Any

from ..data.tables import NAK_SPAN, NAKSHATRAS, SIGN_LORDS, SIGNS, VIM_ORDER, VIM_YEARS
from ..nakshatra import nakshatra_lord


@lru_cache(maxsize=1)
def kp_table() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for n in range(27):
        star = nakshatra_lord(n)
        i0 = VIM_ORDER.index(star)
        t = n * NAK_SPAN
        for k in range(9):
            sub = VIM_ORDER[(i0 + k) % 9]
            end = t + NAK_SPAN * VIM_YEARS[sub] / 120.0
            a = t
            while a < end - 1e-12:
                sign = int(a // 30.0 + 1e-12)
                b = min(end, (sign + 1) * 30.0)
                rows.append({"number": len(rows) + 1, "start": a, "end": b, "sign": SIGNS[sign % 12],
                             "sign_lord": SIGN_LORDS[sign % 12], "nakshatra": NAKSHATRAS[n], "star_lord": star,
                             "sub_lord": sub})
                a = b
            t = end
    return tuple(rows)


__all__ = ["kp_table"]
