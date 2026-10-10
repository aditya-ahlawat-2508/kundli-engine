"""Kundli -> flat list of Fact(id, text, data). Pure and deterministic; the LLM sees only these."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..chart import current_dasha
from ..data.tables import PLANETS, SIGNS
from ..models import Kundli
from ..transits import snapshot


@dataclass
class Fact:
    id: str
    kind: str                     # lagna | planet | house | yoga | dasha | divisional | jaimini | transit | panchang | window
    text: str
    data: dict[str, Any] = field(default_factory=dict)
    houses: list[int] = field(default_factory=list)
    planets: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


def _ord(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _deg(x: float) -> str:
    d = int(x)
    return f"{d}°{int((x - d) * 60):02d}'"


def build_facts(k: Kundli, as_of: datetime | None = None) -> list[Fact]:
    """`as_of` (aware datetime) enables dasha-running and transit facts; it is never read from the clock."""
    out: list[Fact] = []

    def add(kind: str, text: str, **kw: Any) -> Fact:
        f = Fact(id=f"F{len(out) + 1:03d}", kind=kind, text=text, **kw)
        out.append(f)
        return f

    pl = {p.name: p for p in k.planets}
    sb = k.shadbala["planets"] if k.shadbala else {}
    if k.lagna:
        add("lagna", f"Lagna (ascendant) is {k.lagna['sign_name']} at {_deg(k.lagna['degree_in_sign'])}, nakshatra "
            f"{k.lagna['nakshatra']} pada {k.lagna['pada']}; lagna lord is {k.lagna['lord']}.",
            data={"sign": k.lagna["sign_name"], "lord": k.lagna["lord"]}, houses=[1], planets=[k.lagna["lord"]])
    else:
        add("lagna", "Birth time is unknown, so the lagna and house-based readings are unavailable.")
    for n in PLANETS:
        p = pl[n]
        parts = [f"{n} is in {p.sign_name} at {_deg(p.degree_in_sign)}"]
        if p.rashi_house:
            parts.append(f"in the {_ord(p.rashi_house)} house")
        parts.append(f"nakshatra {p.nakshatra_name} pada {p.pada} (lord {p.nakshatra_lord}); dignity {p.dignity}")
        if p.retrograde:
            parts.append("retrograde")
        if p.combust:
            parts.append("combust")
        if p.vargottama:
            parts.append("vargottama")
        if p.lord_of_houses:
            parts.append("rules house(s) " + ", ".join(str(h) for h in p.lord_of_houses))
        if n in sb:
            parts.append(f"Shadbala ratio {sb[n]['ratio']:.2f}")
        add("planet", "; ".join(parts) + ".", data={"dignity": p.dignity, "house": p.rashi_house, "sign": p.sign_name},
            houses=([p.rashi_house] if p.rashi_house else []) + p.lord_of_houses, planets=[n])
    if k.lagna:
        by_house: dict[int, list[str]] = {}
        for n in PLANETS:
            by_house.setdefault(pl[n].rashi_house or 0, []).append(n)
        for h in range(1, 13):
            sign = (k.lagna["sign"] + h - 1) % 12
            lord = next(p.name for p in k.planets if h in p.lord_of_houses)
            occ = by_house.get(h, [])
            asp = sorted(a for a, d in k.aspects.items() if d["aspects_houses"] and h in d["aspects_houses"])
            sav = k.ashtakavarga["sav_by_house"][str(h)] if k.ashtakavarga else None
            t = (f"The {_ord(h)} house is {SIGNS[sign]}, ruled by {lord} (placed in the {_ord(pl[lord].rashi_house or 0)} "
                 f"house); occupants: {', '.join(occ) or 'none'}; aspected by: {', '.join(asp) or 'none'}")
            if sav is not None:
                t += f"; Sarvashtakavarga bindus {sav}"
            add("house", t + ".", data={"sign": SIGNS[sign], "lord": lord, "sav": sav, "lord_house": pl[lord].rashi_house}, houses=[h],
                planets=[lord, *occ])
    for y in k.yogas:
        if y["present"]:
            c = f"; cancelled by {', '.join(y['cancelled_by'])}" if y["cancelled_by"] else ""
            add("yoga", f"{y['name']} is present involving {', '.join(y['planets_involved']) or 'the chart as a whole'} "
                f"(strength {y['strength']:.2f}{c}; source {y['source']}).", data={"effects_key": y["effects_key"],
                "effective": y["effective"], "category": y["category"]}, planets=y["planets_involved"],
                tags=[y["effects_key"], y["category"]])
    if as_of is not None:
        for lvl in current_dasha(k, as_of, levels=3):
            lord = lvl["lord"]
            p = pl[lord]
            add("dasha", f"Running {lvl['level']} dasha lord is {lord} from {lvl['start_local'][:10]} to "
                f"{lvl['end_local'][:10]}; {lord} is in the {_ord(p.rashi_house or 0)} house in {p.sign_name} and rules "
                f"house(s) {', '.join(map(str, p.lord_of_houses)) or 'none'}.",
                data={"level": lvl["level"], "lord": lord, "start": lvl["start_local"][:10], "end": lvl["end_local"][:10]},
                houses=([p.rashi_house] if p.rashi_house else []) + p.lord_of_houses, planets=[lord], tags=[lvl["level"]])
    for v in ("D9", "D10", "D7"):
        vg = k.vargas[v]
        txt = ", ".join(f"{n} in {vg['planets'][n]['sign_name']}" for n in PLANETS)
        lg = f"{v} lagna {vg['lagna']['sign_name']}; " if "lagna" in vg else ""
        add("divisional", f"{vg['name']} ({v}): {lg}{txt}.", data={"varga": v}, tags=[v], planets=list(PLANETS))
    if k.jaimini:
        j = k.jaimini
        ck = j["chara_karakas"]
        add("jaimini", f"Jaimini Atmakaraka is {ck['AK']['planet']}, Amatyakaraka {ck['AmK']['planet']}, Darakaraka "
            f"{ck['DK']['planet']}; Karakamsa is {j['karakamsa']['sign_name']}.", tags=["AK", "DK", "karakamsa"],
            planets=[ck["AK"]["planet"], ck["AmK"]["planet"], ck["DK"]["planet"]])
        add("jaimini", f"Arudha Lagna is {j['arudha_lagna']} and Upapada (UL) is {j['upapada']} "
            f"(the {_ord(j['arudha_padas']['A12']['house_from_lagna'])} house from lagna).", tags=["AL", "UL"],
            houses=[12, j["arudha_padas"]["A12"]["house_from_lagna"]])
    if as_of is not None:
        sn = snapshot(k, as_of)
        for n in ("Jupiter", "Saturn", "Rahu", "Ketu"):
            r = sn["planets"][n]
            h = r["house_from_lagna"]
            add("transit", f"Transiting {n} is in {r['sign_name']} ({_ord(r['house_from_moon'])} from natal Moon"
                + (f", {_ord(h)} house from lagna" if h else "") + (", retrograde" if r["retrograde"] else "") + ".",
                data={"planet": n, "sign": r["sign_name"]}, houses=[h] if h else [], planets=[n], tags=["transit"])
        ss = sn["sade_sati"]
        add("transit", "Sade Sati / Dhaiya status: " + (f"{ss['phase'].replace('_', ' ')}" if ss["active"] else "not active")
            + f" (Saturn is {_ord(ss['saturn_house_from_moon'])} from the natal Moon).", planets=["Saturn", "Moon"],
            tags=["sade_sati"])
    pc = k.panchang
    if pc:
        add("panchang", f"Birth tithi {pc['tithi']['name']} ({pc['tithi']['paksha']} paksha), birth nakshatra "
            f"{pc['nakshatra']['name']}, nitya yoga {pc['yoga']['name']}, karana {pc['karana']['name']}.", tags=["panchang"])
    return out


def add_window_facts(facts: list[Fact], timeline: dict[str, Any], limit: int = 4) -> list[Fact]:
    """Append timing windows computed by timeline.py as facts (the only source of dates for answers)."""
    for w in timeline["windows"][:limit]:
        facts.append(Fact(id=f"F{len(facts) + 1:03d}", kind="window",
                          text=f"Timeline ({timeline['area']}): {w['kind']} window from {w['start'][:10]} to "
                               f"{w['end'][:10]} (mean score {w['mean_score']:.0f}/100, running dasha lords "
                               f"{'/'.join(w['dasha_stack'])}).",
                          data={"start": w["start"][:10], "end": w["end"][:10], "kind": w["kind"]}, tags=["window"]))
    return facts
