"""Chart views: what to draw for a given varga/chart, independent of the drawing style."""
from dataclasses import dataclass, field

from ..data.tables import PLANETS, SIGNS
from ..models import Kundli

ABBR = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me", "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa",
        "Rahu": "Ra", "Ketu": "Ke"}
DIGNITY_MARK = {"exalted": "E", "debilitated": "D", "own": "O", "moolatrikona": "O"}
LEGEND = "R retrograde, c combust, E exalted, D debilitated, O own/moolatrikona, V vargottama"


@dataclass
class Mark:
    planet: str
    degree: float
    retro: bool = False
    combust: bool = False
    dignity: str = ""
    vargottama: bool = False

    def label(self) -> str:
        m = ""
        if self.retro:
            m += "R"
        if self.combust:
            m += "c"
        m += DIGNITY_MARK.get(self.dignity, "")
        if self.vargottama:
            m += "V"
        return f"{ABBR[self.planet]} {int(self.degree)}°{m}"


@dataclass
class ChartView:
    title: str
    lagna_sign: int | None
    by_sign: dict[int, list[Mark]] = field(default_factory=dict)
    lagna_label: str = "Asc"

    def house_of_sign(self, sign: int) -> int:
        assert self.lagna_sign is not None
        return (sign - self.lagna_sign) % 12 + 1


def view_for(k: Kundli, chart: str) -> ChartView:
    """chart: 'D1'..'D60' | 'Chandra' | 'Surya' | 'Bhava' (bhava chalit)."""
    pl = {p.name: p for p in k.planets}
    by_sign: dict[int, list[Mark]] = {}

    def add(sign: int, p: str, deg: float) -> None:
        d = pl[p]
        by_sign.setdefault(sign, []).append(Mark(p, deg, d.retrograde, d.combust, d.dignity, d.vargottama))

    if chart in ("Chandra", "Surya"):
        ref = "Moon" if chart == "Chandra" else "Sun"
        for p in PLANETS:
            add(pl[p].sign, p, pl[p].degree_in_sign)
        return ChartView(f"{chart} chart ({ref} as lagna)", pl[ref].sign, by_sign, ref)
    if chart == "Bhava":
        if k.lagna is None:
            raise ValueError("Bhava chalit needs the lagna")
        ls = k.lagna["sign"]
        for p in PLANETS:
            add((ls + (pl[p].bhava_chalit_house or 1) - 1) % 12, p, pl[p].degree_in_sign)
        return ChartView("Bhava Chalit", ls, by_sign)
    vg = k.vargas[chart]
    for p in PLANETS:
        v = vg["planets"][p]
        add(v["sign"], p, v["degree_in_varga"] if chart != "D1" else pl[p].degree_in_sign)
    lagna = vg.get("lagna", {}).get("sign")
    name = vg["name"]
    return ChartView(f"{chart} {name}", lagna, by_sign)


__all__ = ["LEGEND", "SIGNS", "ChartView", "Mark", "view_for"]
