"""Event-window scoring from dasha + transit + strength. Weights live in data/timeline_weights_v1.yaml."""
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from .aspects import aspected_signs
from .chart import current_dasha
from .data.tables import SEVEN
from .models import Kundli
from .transits import _cfg, jd_of, sade_sati_status, sid_lon

WEIGHTS_FILE = Path(__file__).parent / "data" / "timeline_weights_v1.yaml"


def load_weights(path: Path = WEIGHTS_FILE) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _lord_effects(k: Kundli) -> dict[str, dict[str, float]]:
    """Per planet: yoga bonus/malus counts from effective yogas."""
    eff: dict[str, dict[str, float]] = {p: {"good": 0, "bad": 0} for p in [x.name for x in k.planets]}
    for y in k.yogas:
        if not y.get("effective"):
            continue
        bucket = "good" if y["category"] == "benefic" else "bad" if y["category"] in ("malefic", "dosha") else None
        if bucket:
            for p in y["planets_involved"]:
                eff[p][bucket] += 1
    return eff


def significance(k: Kundli, lord: str, area: dict[str, Any], w: dict[str, Any], eff: dict) -> float:
    """How strongly a dasha lord signifies a life area (see weights file for each term)."""
    sw = w["significator"]
    pl = {p.name: p for p in k.planets}[lord]
    houses = area["houses"]
    s = 0.0
    if any(h in houses for h in pl.lord_of_houses):
        s += sw["rules_house"]
    if pl.rashi_house in houses:
        s += sw["occupies_house"]
    if lord in area["karakas"]:
        s += sw["karaka"]
    if any(h in (6, 8, 12) and h not in houses for h in pl.lord_of_houses):
        s += sw["rules_dusthana"]
    if k.shadbala and lord in k.shadbala["planets"]:
        ratio = min(k.shadbala["planets"][lord]["ratio"], 1.5)
        s *= 1 + sw["strength_scale"] * (ratio - 1)
    if eff[lord]["good"]:
        s += sw["yoga_bonus"]
    if eff[lord]["bad"]:
        s += sw["yoga_malus"]
    return s


def score_at(k: Kundli, when: datetime, area_name: str, w: dict[str, Any] | None = None) -> dict[str, Any]:
    """Score (0..100, 50 neutral) for one life area at one moment, with the components that produced it."""
    w = w or load_weights()
    if k.lagna is None:
        raise ValueError("timeline needs a known birth time")
    area = w["areas"][area_name]
    cfg, eff = _cfg(k), _lord_effects(k)
    lagna = k.lagna["sign"]
    stack = current_dasha(k, when, levels=3)
    dasha = 0.0
    parts: dict[str, Any] = {"dasha": {}}
    for lvl in stack:
        v = w["dasha_level_weights"][lvl["level"]] * significance(k, lvl["lord"], area, w, eff)
        parts["dasha"][lvl["level"]] = {"lord": lvl["lord"], "score": v}
        dasha += v
    jd = jd_of(when)
    tw = w["transit"]
    area_signs = {(lagna + h - 1) % 12 for h in area["houses"]}
    transit, tparts = 0.0, {}
    for pn in ("Jupiter", "Saturn", "Rahu", "Ketu"):
        lon = sid_lon(pn, jd, cfg)
        s = int(lon // 30)
        v = 0.0
        asp = set(aspected_signs(pn, s)) if pn in ("Jupiter", "Saturn") else set()
        if pn == "Jupiter":
            v += tw["jupiter_in_area_house"] * (s in area_signs) + tw["jupiter_aspect"] * len(asp & area_signs)
        elif pn == "Saturn":
            v += tw["saturn_in_area_house"] * (s in area_signs) + tw["saturn_aspect"] * len(asp & area_signs)
        else:
            v += tw["rahu_ketu_in_area_house"] * (s in area_signs)
        if k.ashtakavarga and pn in ("Jupiter", "Saturn"):
            v += tw["sav_scale"] * (k.ashtakavarga["sav"][s] - 28) / 28.0
        tparts[pn] = {"sign": s, "score": v}
        transit += v
    moon_sign = next(p.sign for p in k.planets if p.name == "Moon")
    saturn_sign = tparts["Saturn"]["sign"]
    if area_name in ("health", "wealth", "career", "marriage") and sade_sati_status(moon_sign, saturn_sign)["phase"] \
            and sade_sati_status(moon_sign, saturn_sign)["phase"].startswith("sade_sati"):
        transit += tw["sade_sati_malus"]
        tparts["sade_sati"] = tw["sade_sati_malus"]
    raw = dasha + transit
    score = 50.0 + 50.0 * math.tanh((raw - w["normalise"]["center"]) * w["normalise"]["tanh_scale"])
    return {"when": when.astimezone(UTC).isoformat(), "area": area_name, "score": score, "raw": raw,
            "dasha": parts["dasha"], "transit": tparts, "dasha_stack": [x["lord"] for x in stack]}


def build_timeline(k: Kundli, start: datetime, end: datetime, area: str, step_days: int = 30) -> dict[str, Any]:
    """Sample the score every `step_days`, then merge consecutive favourable/challenging samples into windows."""
    w = load_weights()
    pts = []
    t = start
    while t <= end:
        pts.append(score_at(k, t, area, w))
        t += timedelta(days=step_days)
    hi, lo = w["normalise"]["favourable_above"], w["normalise"]["challenging_below"]
    windows: list[dict[str, Any]] = []
    for kind, test in (("favourable", lambda s: s >= hi), ("challenging", lambda s: s <= lo)):
        cur: list[dict] = []
        for p in [*pts, None]:
            if p is not None and test(p["score"]):
                cur.append(p)
                continue
            if cur:
                scores = [c["score"] for c in cur]
                windows.append({"kind": kind, "start": cur[0]["when"], "end": cur[-1]["when"],
                                "mean_score": sum(scores) / len(scores), "peak_score": max(scores),
                                "dasha_stack": cur[0]["dasha_stack"]})
                cur = []
    windows.sort(key=lambda x: (x["kind"], -x["mean_score"], x["start"]))
    return {"area": area, "weights_version": w["version"], "step_days": step_days, "samples": pts,
            "windows": windows, "from": start.isoformat(), "to": end.isoformat()}


__all__ = ["SEVEN", "build_timeline", "load_weights", "score_at"]
