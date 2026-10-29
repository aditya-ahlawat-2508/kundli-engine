"""Match-making adapters (V2 phase 16). They receive both finished charts (boy first) and the match request."""
from collections.abc import Callable
from typing import Any

from ...content import keys
from ...match import ashtakoota, dashakoota, match, obstructions, percentage, person_from, verdict
from ...models import Kundli
from ._content import block

MatchAdapter = Callable[[Kundli, Kundli, dict[str, str]], Any]


def _dosha_state(d: dict[str, Any]) -> str:
    return "absent" if not d["present"] else "cancelled" if d["cancelled_by"] else "effective"


def _manglik_state(m: dict[str, Any]) -> str | None:
    if "obstruction" not in m:
        return None
    return {(False, False): "neither", (True, True): "both", (True, False): "boy_only", (False, True): "girl_only"}[
        (m["boy_manglik"], m["girl_manglik"])]


def _content(b: Kundli, ak: dict[str, Any] | None, ob: dict[str, Any] | None) -> dict[str, Any]:
    """Content blocks for the facts present: koota points, verdict, nadi/bhakoot dosha and manglik match."""
    out: dict[str, Any] = {}
    if ak is not None:
        out["kootas"] = {name: block(b, f"match.koota.{name}.{keys.num(k['points'])}") for name, k in ak["kootas"].items()}
        out["verdict"] = block(b, f"match.verdict.{verdict(ak['total'])}")
    if ob is not None:
        out["nadi_dosha"] = block(b, f"match.nadi_dosha.{_dosha_state(ob['nadi_dosha'])}")
        out["bhakoot_dosha"] = block(b, f"match.bhakoot_dosha.{_dosha_state(ob['bhakoot_dosha'])}")
        state = _manglik_state(ob["manglik"])
        if state:
            out["manglik"] = block(b, f"match.manglik.{state}")
    return out


def _both(fn: Callable[[Kundli], Any]) -> MatchAdapter:
    return lambda b, g, _a: {"boy": fn(b), "girl": fn(g)}


def _ashtakoota(b: Kundli, g: Kundli, _a: dict[str, str]) -> Any:
    ak = ashtakoota(person_from(b), person_from(g))
    return {**ak, "verdict": verdict(ak["total"])}


def _ashtakoota_report(b: Kundli, g: Kundli, a: dict[str, str]) -> Any:
    ak = ashtakoota(person_from(b), person_from(g))
    return {**_ashtakoota(b, g, a), "content": _content(b, ak, None)}


def _percentage(b: Kundli, g: Kundli, _a: dict[str, str]) -> Any:
    total = ashtakoota(person_from(b), person_from(g))["total"]
    return {"percentage": percentage(total), "ashtakoota_total": total, "formula": "total/36*100 (convention)"}


def _manglik_report(b: Kundli, g: Kundli, _a: dict[str, str]) -> Any:
    ob = obstructions(b, g, person_from(b), person_from(g))
    state = _manglik_state(ob["manglik"])
    return {**ob["manglik"], "content": block(b, f"match.manglik.{state}") if state else None}


def _full(b: Kundli, g: Kundli) -> dict[str, Any]:
    m = match(b, g)
    return {**m, "content": _content(b, m["ashtakoota"], m["obstructions"])}


MATCH_ADAPTERS: dict[str, MatchAdapter] = {
    "match_birth_details": _both(lambda k: {"birth": k.birth, "lagna": k.lagna}),
    "match_astro_details": _both(lambda k: k.avakahada),
    "match_planet_details": _both(lambda k: [p.model_dump() for p in k.planets]),
    "match_ashtakoot_points": _ashtakoota,
    "match_ashtakoot_report": _ashtakoota_report,
    "match_dashakoot_points": lambda b, g, _a: dashakoota(person_from(b), person_from(g)),
    "match_obstructions": lambda b, g, _a: obstructions(b, g, person_from(b), person_from(g)),
    "match_percentage": _percentage,
    "match_manglik_report": _manglik_report,
    "match_making_report": lambda b, g, _a: _full(b, g),
    "match_making_detailed_report": lambda b, g, _a: {**_full(b, g), "boy_astro": b.avakahada, "girl_astro": g.avakahada},
}
