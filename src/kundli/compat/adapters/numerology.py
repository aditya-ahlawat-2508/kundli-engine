"""Numerology and biorhythm adapters (V2 phase 19). Lookups are returned for both the radical (birth day) and the destiny
number; report/prediction text comes from the content store in phase 21 (`content_missing` marker until then)."""
from datetime import date
from typing import Any

from ...biorhythm import biorhythm, biorhythm_series
from ...models import Kundli
from ...numerology import daily_number, fast_day, fav_lord, fav_place, fav_time, mantra, relation
from ..normalize import BirthRequest, as_of_dt
from ._content import block, blocks

Adapter = Any


def _both(fn) -> Adapter:  # type: ignore[no-untyped-def]
    def run(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
        n = k.numerology or {}
        return {"radical": fn(n["radical"]), "destiny": fn(n["destiny"]), "system": n.get("system")}
    return run


def _table(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    return k.numerology


def _report(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    n = k.numerology or {}
    return {**n, "radical_vs_destiny": relation(n["radical"], n["destiny"]),
            "content": blocks(k, radical=f"numerology.radical.{n['radical']}", destiny=f"numerology.destiny.{n['destiny']}",
                              name=f"numerology.name.{n['name']}" if n["name"] else "numerology.name.1")}


def _daily(k: Kundli, r: BirthRequest, _a: dict[str, str]) -> Any:
    n = k.numerology or {}
    d = daily_number(n["radical"], as_of_dt(r).date())
    return {**d, "content": block(k, f"numerology.daily.{d['daily_number']}")}


def _fasts(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    n = k.numerology or {}
    return {x: {**fast_day(n[x]), "content": block(k, f"numerology.fast.{n[x]}")} for x in ("radical", "destiny")}


def _biorhythm(k: Kundli, r: BirthRequest, _a: dict[str, str]) -> Any:
    birth = date.fromisoformat(r.date)
    start = as_of_dt(r).date()
    if r.end_date:
        return {"birth_date": birth.isoformat(), "series": biorhythm_series(birth, start, date.fromisoformat(r.end_date))}
    return {"birth_date": birth.isoformat(), **biorhythm(birth, start)}


NUMEROLOGY_ADAPTERS: dict[str, Adapter] = {
    "numero_table": _table,
    "numero_report": _report,
    "numero_fav_time": _both(fav_time),
    "numero_place_vastu": _both(fav_place),
    "numero_fasts_report": _fasts,
    "numero_fav_lord": _both(fav_lord),
    "numero_fav_mantra": _both(mantra),
    "numero_prediction/daily": _daily,
    "biorhythm": _biorhythm,
}
