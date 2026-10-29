"""Engine-neutral response bodies for endpoints the engine can already answer. Each function takes a finished
Kundli plus the request and returns plain JSON-able data. No provider field names are assumed."""
from collections.abc import Callable
from typing import Any

from ... import lookups
from ...chart import current_dasha
from ...models import Kundli
from ..normalize import BirthRequest, as_of_dt
from .dasha import DASHA_ADAPTERS
from .doshas import DOSHA_ADAPTERS
from .kp import KP_ADAPTERS
from .lalkitab import LALKITAB_ADAPTERS
from .muhurta import MUHURTA_ADAPTERS
from .numerology import NUMEROLOGY_ADAPTERS
from .panchang import PANCHANG_ADAPTERS
from .remedies import REMEDY_ADAPTERS
from .reports import REPORT_ADAPTERS
from .varshaphal import ADAPTERS_VARSHAPHAL

Adapter = Callable[[Kundli, BirthRequest, dict[str, str]], Any]


def _planets(k: Kundli, *_: Any) -> Any:
    return [p.model_dump() for p in k.planets]


def _chart(k: Kundli, _r: BirthRequest, a: dict[str, str]) -> Any:
    cid = a["chart_id"]
    if cid in k.vargas:
        return k.vargas[cid]
    mapping = {"chandra": k.chandra_chart, "moon": k.chandra_chart, "surya": k.surya_chart, "sun": k.surya_chart}
    if cid.lower() in mapping and mapping[cid.lower()] is not None:
        return mapping[cid.lower()]
    raise ValueError(f"unknown chart {cid!r}; use one of {sorted(k.vargas)} or chandra/surya")


def _bav(k: Kundli, _r: BirthRequest, a: dict[str, str]) -> Any:
    if k.ashtakavarga is None:
        raise ValueError("Ashtakavarga needs a known birth time")
    p = a["planet_name"].capitalize()
    if p not in k.ashtakavarga["bav"]:
        raise ValueError(f"unknown planet {p!r}")
    return {"planet": p, "bav": k.ashtakavarga["bav"][p], "total": k.ashtakavarga["bav_totals"][p],
            "prastara": k.ashtakavarga["prastara"][p]}


def _stack(levels: int | None, system: str = "vimshottari") -> Adapter:
    def run(k: Kundli, r: BirthRequest, _a: dict[str, str]) -> Any:
        return current_dasha(k, as_of_dt(r), system, levels or r.levels)
    return run


def _need(k: Kundli, field: str) -> Any:
    v = getattr(k, field)
    if v is None:
        raise ValueError(f"{field} needs a known birth time")
    return v


ADAPTERS: dict[str, Adapter] = {
    "birth_details": lambda k, r, a: {"birth": k.birth, "lagna": k.lagna, "header": k.header},
    "planets": _planets,
    "bhav_madhya": lambda k, r, a: _need(k, "houses"),
    "ayanamsha": lambda k, r, a: {"name": k.header["config"]["ayanamsa"], "degrees": k.header["ayanamsa_degrees"]},
    "planet_nature": lambda k, r, a: lookups.planet_nature(k),
    "astro_details": lambda k, r, a: lookups.astro_details(k),
    "horo_chart/{chart_id}": _chart,
    "planet_ashtak/{planet_name}": _bav,
    "sarvashtak": lambda k, r, a: {"sav": _need(k, "ashtakavarga")["sav"], "total": k.ashtakavarga["sav_total"]},  # type: ignore[index]
    "major_vdasha": lambda k, r, a: k.dashas["vimshottari"]["mahadashas"],
    "current_vdasha_all": _stack(5),
    "current_vdasha": _stack(3),
    "current_vdasha_date": _stack(None),
    "major_yogini_dasha": lambda k, r, a: k.dashas["yogini"]["mahadashas"],
    "current_yogini_dasha": _stack(None, "yogini"),
    "major_chardasha": lambda k, r, a: _need(k, "dashas").get("chara", {}).get("mahadashas") or _need(k, "lagna"),
}

ADAPTERS.update(PANCHANG_ADAPTERS)
ADAPTERS.update(DASHA_ADAPTERS)
ADAPTERS.update(KP_ADAPTERS)
ADAPTERS.update(DOSHA_ADAPTERS)
ADAPTERS.update(ADAPTERS_VARSHAPHAL)
ADAPTERS.update(MUHURTA_ADAPTERS)
ADAPTERS.update(NUMEROLOGY_ADAPTERS)
ADAPTERS.update(LALKITAB_ADAPTERS)
ADAPTERS.update(REPORT_ADAPTERS)
ADAPTERS.update(REMEDY_ADAPTERS)
