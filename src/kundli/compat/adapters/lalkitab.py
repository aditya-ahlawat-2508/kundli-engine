"""Lal Kitab adapters (V2 phase 20). The layout follows `EngineConfig.lalkitab_edition`; remedy text is a content-store key."""
from typing import Any

from ...lalkitab import debts, houses_table, lalkitab, layout, planets_table, remedy_for
from ...models import Kundli
from ...transits import _cfg
from ..normalize import BirthRequest
from ._content import block

Adapter = Any


def _chart(k: Kundli) -> dict[str, Any]:
    return layout(k, _cfg(k).lalkitab_edition)


def _horoscope(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    return lalkitab(k)["chart"]


def _planets(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    return planets_table(k, _chart(k)["planet_house"])


def _houses(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    return houses_table(_chart(k))


def _debts(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    return debts(_chart(k)["planet_house"])


def _remedies(k: Kundli, _r: BirthRequest, a: dict[str, str]) -> Any:
    r = remedy_for(a["planet_name"], _chart(k)["planet_house"])
    return {**r, "content": block(k, r["remedy_keys"][0])}


LALKITAB_ADAPTERS: dict[str, Adapter] = {
    "lalkitab_horoscope": _horoscope,
    "lalkitab_planets": _planets,
    "lalkitab_houses": _houses,
    "lalkitab_debts": _debts,
    "lalkitab_remedies/{planet_name}": _remedies,
}
