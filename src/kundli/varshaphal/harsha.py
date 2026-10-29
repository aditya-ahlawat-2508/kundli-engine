"""Harsha bala (Tajika): four components of 5 virupas each (max 20) for the seven grahas in the annual chart.

1. Sthana: the graha stands in its "glad" house (Sun 9, Moon 3, Mars 6, Mercury 1, Jupiter 11, Venus 5, Saturn 12).
2. Stri-purusha: male grahas (Sun, Mars, Jupiter) in an odd (male) sign or female grahas (Moon, Venus) in an even
   (female) sign; Mercury and Saturn (neuter) score 0.
3. Uccha-adi: the graha is exalted, in its moolatrikona or in its own sign.
4. Dina-ratri: in a day chart (Sun above the horizon, houses 7-12) Sun, Jupiter, Saturn; in a night chart Moon, Venus,
   Mars; Mercury in both.
Components 2-4 are the least certain part of this implementation (`# VERIFY`, low confidence): the response always
carries `tables_verified: false`.
"""
from typing import Any

from ..data.tables import EXALTATION as EX
from ..data.tables import MOOLATRIKONA, OWN_SIGNS, SEVEN
from ..models import Kundli
from .tables import HARSHA_HOUSE

MALE, FEMALE = ("Sun", "Mars", "Jupiter"), ("Moon", "Venus")
DAY_PLANETS, NIGHT_PLANETS = ("Sun", "Jupiter", "Saturn"), ("Moon", "Venus", "Mars")


def is_day_chart(annual: Kundli) -> bool:
    sun = next(p for p in annual.planets if p.name == "Sun")
    return (sun.rashi_house or 1) >= 7


def harsha_bala(annual: Kundli) -> dict[str, Any]:
    if annual.lagna is None:
        raise ValueError("Harsha bala needs a known birth time")
    day = is_day_chart(annual)
    out: dict[str, Any] = {}
    for p in annual.planets:
        if p.name not in SEVEN:
            continue
        n, sign = p.name, p.sign
        sthana = 5.0 if p.rashi_house == HARSHA_HOUSE[n] else 0.0
        stri = 5.0 if (n in MALE and sign % 2 == 0) or (n in FEMALE and sign % 2 == 1) else 0.0
        mt = MOOLATRIKONA.get(n)
        strong = (sign == EX[n][0] or sign in OWN_SIGNS[n] or (mt is not None and sign == mt[0] and mt[1] <= p.degree_in_sign < mt[2]))
        uccha = 5.0 if strong else 0.0
        dr = 5.0 if (n == "Mercury" or n in (DAY_PLANETS if day else NIGHT_PLANETS)) else 0.0
        out[n] = {"sthana": sthana, "stri_purusha": stri, "uccha_adi": uccha, "dina_ratri": dr,
                  "total": sthana + stri + uccha + dr}
    return {"planets": out, "max": 20.0, "chart_is_day": day, "tables_verified": False}


__all__ = ["harsha_bala", "is_day_chart"]
