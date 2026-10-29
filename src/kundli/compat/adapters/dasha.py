"""Dasha-group adapters (V2 phase 14). Engine-neutral bodies. Every `sub_*` endpoint lists the sub-periods of the
period named by its path (lords for Vimshottari, yogini or lord names for Yogini, sign names for Chara)."""
from datetime import datetime
from typing import Any

from ...chart import current_dasha
from ...dasha import chara, vimshottari, yogini
from ...models import Kundli
from ..normalize import BirthRequest, as_of_dt

Adapter = Any


def _par(k: Kundli) -> tuple[float, datetime, float, str]:
    p = k.dashas["params"]
    return p["moon_lon"], datetime.fromisoformat(p["birth_utc"]), p["year_days"], p["tz"]


def _chara_params(k: Kundli) -> dict:
    cp = k.dashas.get("chara", {}).get("params")
    if cp is None:
        raise ValueError("Chara dasha needs a known birth time")
    return cp


def _vim_sub(*names: str) -> Adapter:
    def run(k: Kundli, _r: BirthRequest, a: dict[str, str]) -> Any:
        moon, birth, yd, tz = _par(k)
        return vimshottari.descend(moon, birth, yd, [a[n] for n in names], tz, 1)
    return run


def _chara_sub(names: tuple[str, ...]) -> Adapter:
    def run(k: Kundli, r: BirthRequest, a: dict[str, str]) -> Any:
        cp = _chara_params(k)
        _m, birth, yd, tz = _par(k)
        path = [a[n] for n in names if n in a]
        if not path:  # route without path params: take the period running at as_of, one level up from the answer
            stack = current_dasha(k, as_of_dt(r), "chara", 2)
            path = [s["lord"] for s in stack]
        return chara.descend(cp["lagna_sign"], cp["signs"], cp["degs"], birth, yd, path, tz, 1)
    return run


def _yogini_sub(k: Kundli, r: BirthRequest, a: dict[str, str]) -> Any:
    moon, birth, yd, tz = _par(k)
    cycle = int(a["dashaCycle"]) if "dashaCycle" in a else None
    if cycle is not None and cycle < 1:
        raise ValueError("dashaCycle must be 1 or more")
    if "dashaName" in a:
        name = a["dashaName"]
    else:  # no path params: the yogini maha running at as_of, in the cycle running at as_of
        as_of = as_of_dt(r)
        name = current_dasha(k, as_of, "yogini", 1)[0]["lord"]
        cycle = yogini.cycle_at(moon, birth, yd, as_of)
    cycle = cycle or 1
    return yogini.descend(moon, birth, yd, [name], tz, 1, cycle)


def _stack(system: str, levels: int | None = None) -> Adapter:
    def run(k: Kundli, r: BirthRequest, _a: dict[str, str]) -> Any:
        return current_dasha(k, as_of_dt(r), system, levels or r.levels)
    return run


DASHA_ADAPTERS: dict[str, Adapter] = {
    "sub_vdasha/{md}": _vim_sub("md"),
    "sub_sub_vdasha/{md}/{ad}": _vim_sub("md", "ad"),
    "sub_sub_sub_vdasha/{md}/{ad}/{pd}": _vim_sub("md", "ad", "pd"),
    "sub_sub_sub_sub_vdasha/{md}/{ad}/{pd}/{sd}": _vim_sub("md", "ad", "pd", "sd"),
    "current_chardasha": _stack("chara"),
    "sub_chardasha/{md}": _chara_sub(("md",)),
    "sub_sub_chardasha": _chara_sub(()),
    "sub_yogini_dasha/{dashaCycle}/{dashaName}": _yogini_sub,
    "sub_yogini_dasha": _yogini_sub,
}
