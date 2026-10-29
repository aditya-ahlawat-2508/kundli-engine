"""Varshaphal-group adapters (V2 phase 17). `year` defaults to the year of `as_of`; `month` (1..12) selects a month chart."""
from datetime import datetime
from typing import Any

from ...models import Kundli
from ...transits import _cfg
from ...varshaphal import (
    annual_chart,
    harsha_bala,
    mudda_dasha,
    muntha,
    panchavargeeya,
    sahams,
    tajika_yogas,
)
from ..normalize import BirthRequest, as_of_dt

Adapter = Any


def _year(r: BirthRequest) -> int:
    return r.year if r.year is not None else as_of_dt(r).year


def _chart(k: Kundli, r: BirthRequest, month: int):  # type: ignore[no-untyped-def]
    year = _year(r)
    annual, jd = annual_chart(k, year, month)
    return annual, jd, year - datetime.fromisoformat(k.birth["utc"]).year, year


def _wrap(fn) -> Adapter:  # type: ignore[no-untyped-def]
    """Adapter that computes the year chart then applies fn(natal, annual, jd, age)."""
    def run(k: Kundli, r: BirthRequest, _a: dict[str, str]) -> Any:
        annual, jd, age, year = _chart(k, r, 1)
        return {"year": year, "age": age, **fn(k, annual, jd, age)}
    return run


def _year_chart(k: Kundli, annual: Kundli, jd: float, age: int) -> dict[str, Any]:
    return {"jd_ut": jd, "local": annual.birth["local"], "lagna": annual.lagna, "planets": annual.planets,
            "d1": annual.vargas.get("D1"), "houses": annual.houses}


def _month_chart(k: Kundli, r: BirthRequest, _a: dict[str, str]) -> Any:
    if r.month is None:
        raise ValueError("month (1..12) is required for the month chart")
    annual, jd, age, year = _chart(k, r, r.month)
    return {"year": year, "month": r.month, "age": age, **_year_chart(k, annual, jd, age)}


def _details(k: Kundli, annual: Kundli, jd: float, age: int) -> dict[str, Any]:
    return {"jd_ut": jd, "local": annual.birth["local"], "lagna": annual.lagna, "muntha": muntha(k, annual, age),
            "zodiac_returned": _cfg(k).solar_return_zodiac}


ADAPTERS_VARSHAPHAL: dict[str, Adapter] = {
    "varshaphal_year_chart": _wrap(_year_chart),
    "varshaphal_month_chart": _month_chart,
    "varshaphal_details": _wrap(_details),
    "varshaphal_planets": _wrap(lambda k, a, jd, age: {"planets": a.planets}),
    "varshaphal_muntha": _wrap(lambda k, a, jd, age: {"muntha": muntha(k, a, age)}),
    "varshaphal_mudda_dasha": _wrap(lambda k, a, jd, age: {"mudda_dasha": mudda_dasha(k, a, jd, _cfg(k).mudda_dasha_basis)}),
    "varshaphal_panchavargeeya_bala": _wrap(lambda k, a, jd, age: panchavargeeya(a)),
    "varshaphal_harsha_bala": _wrap(lambda k, a, jd, age: harsha_bala(a)),
    "varshaphal_saham_points": _wrap(lambda k, a, jd, age: sahams(a)),
    "varshaphal_yoga": _wrap(lambda k, a, jd, age: tajika_yogas(a)),
}
