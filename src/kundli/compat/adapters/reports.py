"""Life-report and daily-prediction adapters (V2 phase 21). Each endpoint computes facts, builds a content key and returns
the stored block (or a `content_missing` marker) next to the facts. Text is never generated here."""
from datetime import timedelta
from typing import Any

from ...content import keys
from ...models import Kundli
from ...panchang.tarabala import daily_facts
from ..normalize import BirthRequest, as_of_dt
from ._content import block

Adapter = Any


def _planet(k: Kundli, name: str) -> Any:
    n = name.strip().lower()
    if n not in keys.PLANETS:
        raise ValueError(f"unknown planet {name!r}; use one of {keys.PLANETS}")
    return next(p for p in k.planets if p.name.lower() == n)


def _house_report(k: Kundli, _r: BirthRequest, a: dict[str, str]) -> Any:
    p = _planet(k, a["planet_name"])
    if p.rashi_house is None:
        raise ValueError("the house report needs a known birth time")
    key = keys.house_report(p.name, p.rashi_house)
    return {"facts": {"planet": p.name, "house": p.rashi_house, "sign": p.sign_name}, "content": block(k, key)}


def _rashi_report(k: Kundli, _r: BirthRequest, a: dict[str, str]) -> Any:
    p = _planet(k, a["planet_name"])
    return {"facts": {"planet": p.name, "sign": p.sign_name, "degree_in_sign": p.degree_in_sign},
            "content": block(k, keys.rashi_report(p.name, p.sign))}


def _ascendant_report(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    if k.lagna is None:
        raise ValueError("the ascendant report needs a known birth time")
    return {"facts": {"ascendant": k.lagna["sign_name"], "degree_in_sign": k.lagna["degree_in_sign"]},
            "content": block(k, keys.ascendant_report(k.lagna["sign"]))}


def _nakshatra_report(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    moon = next(p for p in k.planets if p.name == "Moon")
    return {"facts": {"nakshatra": moon.nakshatra_name, "pada": moon.pada, "lord": moon.nakshatra_lord},
            "content": block(k, keys.nakshatra_report(moon.nakshatra_name))}


def _daily(shift_days: int) -> Adapter:
    def run(k: Kundli, r: BirthRequest, _a: dict[str, str]) -> Any:
        p = k.birth["place"]
        from ...config import EngineConfig

        cfg = EngineConfig(**k.header["config"])
        d = as_of_dt(r).date() + timedelta(days=shift_days)
        facts = daily_facts(k, d, p["lat"], p["lon"], p["tz"], cfg)
        prim = facts["primary"]
        return {"facts": facts, "content": block(k, keys.daily(prim["tara"], prim["nakshatra"]))}
    return run


def _consolidated(k: Kundli, r: BirthRequest, _a: dict[str, str]) -> Any:
    from ...config import EngineConfig

    p = k.birth["place"]
    facts = daily_facts(k, as_of_dt(r).date(), p["lat"], p["lon"], p["tz"], EngineConfig(**k.header["config"]))
    segments = [{**s, "content": block(k, keys.daily(s["tara"], s["nakshatra"]))} for s in facts["segments"]]
    return {"facts": {x: v for x, v in facts.items() if x != "segments"}, "segments": segments}


REPORT_ADAPTERS: dict[str, Adapter] = {
    "general_house_report/{planet_name}": _house_report,
    "general_rashi_report/{planet_name}": _rashi_report,
    "general_ascendant_report": _ascendant_report,
    "general_nakshatra_report": _nakshatra_report,
    "daily_nakshatra_prediction": _daily(0),
    "daily_nakshatra_prediction/next": _daily(1),
    "daily_nakshatra_prediction/previous": _daily(-1),
    "daily_nakshatra_consolidated": _consolidated,
}
