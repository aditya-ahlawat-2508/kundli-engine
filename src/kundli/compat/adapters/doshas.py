"""Dosha-group adapters (V2 phases 16, 21). Engine-neutral bodies; report text is a content-store block next to the facts."""
from typing import Any

from ...doshas import (
    kaal_sarpa,
    manglik,
    pitra_dosha,
    sadhesati_events,
    sadhesati_periods,
    sadhesati_status,
    simple_manglik,
)
from ...models import Kundli
from ..normalize import BirthRequest, as_of_dt
from ._content import block

Adapter = Any
NEEDS_TIME = "needs a known birth time"


def _need_time(k: Kundli, what: str) -> None:
    if k.lagna is None:
        raise ValueError(f"{what} {NEEDS_TIME}")


def manglik_state(m: dict[str, Any]) -> str:
    """Content-key suffix: absent | present | cancelled.<first cancellation id>."""
    if m["is_manglik"]:
        return "present"
    for ref in m["references"].values():
        if ref and ref["present"] and ref["cancelled_by"]:
            return "cancelled." + ref["cancelled_by"][0]
    return "absent"


def _manglik(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    _need_time(k, "Manglik")
    m = manglik(k)
    return {**m, "content": block(k, f"dosha.manglik.{manglik_state(m)}")}


def _simple(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    return simple_manglik(k)


def _kalsarpa(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    ks = kaal_sarpa(k)
    state = "absent" if not (ks["full"] or ks["partial"]) else ks["type"].lower() if ks["full"] and ks["type"] else "partial"
    return {**ks, "content": block(k, f"dosha.kaalsarpa.{state}")}


def _sadhesati_now(k: Kundli, r: BirthRequest, _a: dict[str, str]) -> Any:
    st = sadhesati_status(k, as_of_dt(r))
    return {**st, "content": block(k, f"dosha.sadhesati.{st['phase'] or 'none'}")}


def _sadhesati_life(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    return {"periods": sadhesati_periods(k), "events": sadhesati_events(k)}


def _pitra(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    _need_time(k, "Pitra dosha")
    p = pitra_dosha(k)
    return {**p, "content": block(k, f"dosha.pitra.{'present' if p['present'] else 'absent'}")}


DOSHA_ADAPTERS: dict[str, Adapter] = {
    "simple_manglik": _simple,
    "manglik": _manglik,
    "kalsarpa_details": _kalsarpa,
    "sadhesati_current_status": _sadhesati_now,
    "sadhesati_life_details": _sadhesati_life,
    "pitra_dosha_report": _pitra,
}
