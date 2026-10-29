"""Remedy adapters (V2 phase 22). Selection comes from `remedies/` (facts + rules); wording is a content-store block per key."""
from datetime import datetime
from typing import Any

from ...models import Kundli
from ...remedies import gem_suggestion, puja_suggestion, rudraksha_suggestion, sadhesati_remedies
from ..normalize import BirthRequest, as_of_dt
from ._content import block

Adapter = Any


def _gems(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    out = gem_suggestion(k)
    for s in out["stones"]:
        s["content"] = {name: block(k, key) for name, key in s["content_keys"].items()}
    return out


def _pujas(k: Kundli, r: BirthRequest, _a: dict[str, str]) -> Any:
    as_of: datetime | None = as_of_dt(r) if r.as_of else None
    out = puja_suggestion(k, as_of)
    for p in out["pujas"]:
        p["content"] = block(k, p["content_key"])
    return out


def _rudraksha(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    out = rudraksha_suggestion(k)
    for p in out["rudraksha"]:
        p["content"] = block(k, p["content_key"])
    return out


def _sadhesati(k: Kundli, r: BirthRequest, _a: dict[str, str]) -> Any:
    out = sadhesati_remedies(k, as_of_dt(r))
    return {**out, "content": block(k, out["content_key"])}


REMEDY_ADAPTERS: dict[str, Adapter] = {
    "basic_gem_suggestion": _gems,
    "puja_suggestion": _pujas,
    "rudraksha_suggestion": _rudraksha,
    "sadhesati_remedies": _sadhesati,
}
