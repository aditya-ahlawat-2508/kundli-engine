"""Lal Kitab (V2 phase 20): chart layout, planet and house tables, debts and remedy selection. Highest-ambiguity area:
edition-specific rules are data flagged `# VERIFY`, and nothing here writes remedy text."""
from typing import Any

from ..models import Kundli
from ..transits import _cfg
from .debts import debts
from .layout import layout
from .remedies import remedy_for
from .tables import DEBILITATED_HOUSE, EXALTED_HOUSE, PAKKA_GHAR, PLANETS, karakas


def planets_table(k: Kundli, planet_house: dict[str, int]) -> dict[str, Any]:
    pl = {p.name: p for p in k.planets}
    return {n: {"house": planet_house[n], "sign": pl[n].sign_name, "in_pakka_ghar": planet_house[n] in PAKKA_GHAR[n],
                "pakka_ghar": list(PAKKA_GHAR[n]), "in_exaltation_house": EXALTED_HOUSE.get(n) == planet_house[n],
                "in_debilitation_house": DEBILITATED_HOUSE.get(n) == planet_house[n], "retrograde": pl[n].retrograde}
            for n in PLANETS}


def houses_table(chart: dict[str, Any]) -> list[dict[str, Any]]:
    return [{**h, "karakas": karakas(h["house"]), "empty": not h["planets"],
             "occupants_in_pakka_ghar": [p for p in h["planets"] if h["house"] in PAKKA_GHAR[p]]} for h in chart["houses"]]


def lalkitab(k: Kundli) -> dict[str, Any]:
    chart = layout(k, _cfg(k).lalkitab_edition)
    return {"chart": chart, "planets": planets_table(k, chart["planet_house"]), "houses": houses_table(chart),
            "debts": debts(chart["planet_house"]), "tables_verified": False}


__all__ = ["DEBILITATED_HOUSE", "EXALTED_HOUSE", "PAKKA_GHAR", "PLANETS", "debts", "houses_table", "karakas", "lalkitab",
           "layout", "planets_table", "remedy_for"]
