"""Manglik (Kuja) dosha. The reference points counted are a convention (`EngineConfig.manglik_rules`):
`lagna_only`, `lagna_moon`, `lagna_moon_venus`. Cancellations come from yogas/rules/doshas.yaml (`standard_v1`)."""
from typing import Any

from ..models import Kundli

MANGLIK_HOUSES = (1, 2, 4, 7, 8, 12)
WEIGHTS = {"lagna": 50, "moon": 25, "venus": 25}
REFERENCES = {"lagna_only": ("lagna",), "lagna_moon": ("lagna", "moon"), "lagna_moon_venus": ("lagna", "moon", "venus")}
YOGA_IDS = {"lagna": "mangal_lagna", "moon": "mangal_moon", "venus": "mangal_venus"}


def simple_manglik(k: Kundli) -> dict[str, Any]:
    """Mars in 1/2/4/7/8/12 from the lagna only (no cancellations)."""
    if k.lagna is None:
        raise ValueError("Manglik needs a known birth time")
    mars = next(p for p in k.planets if p.name == "Mars")
    return {"mars_house": mars.rashi_house, "manglik_houses": list(MANGLIK_HOUSES),
            "is_manglik": mars.rashi_house in MANGLIK_HOUSES}


def manglik(k: Kundli) -> dict[str, Any]:
    """Mars in 1/2/4/7/8/12 from the configured reference points, plus the other malefics in those houses from the
    lagna and the manglik houses Mars aspects. `intensity_percent` is a transparent heuristic (Lagna 50, Moon 25,
    Venus 25 points, normalised to the references in use; a cancelled reference counts a quarter), not a classical
    figure."""
    variant = k.header["config"].get("manglik_rules", "lagna_moon_venus")
    used = REFERENCES[variant]
    by_id = {y["id"]: y for y in k.yogas}
    refs: dict[str, dict[str, Any] | None] = {}
    score = 0.0
    for key in used:
        y = by_id.get(YOGA_IDS[key])
        if y is None or not y["evaluated"]:
            refs[key] = None
            continue
        refs[key] = {"present": y["present"], "cancelled_by": y["cancelled_by"], "effective": y["effective"]}
        if y["present"]:
            score += WEIGHTS[key] * (1.0 if y["effective"] else 0.25)
    pl = {p.name: p for p in k.planets}
    mars_house = pl["Mars"].rashi_house
    others = [n for n in ("Sun", "Saturn", "Rahu", "Ketu") if pl[n].rashi_house in MANGLIK_HOUSES]
    asp = (k.aspects.get("Mars", {}).get("aspects_houses") or []) if k.lagna else []
    return {"mars_house": mars_house, "rules": variant, "references": refs,
            "other_malefics_in_manglik_houses": others,
            "mars_aspects_manglik_houses": sorted(h for h in asp if h in MANGLIK_HOUSES),
            "is_manglik": any(r and r["effective"] for r in refs.values()),
            "intensity_percent": round(100 * score / sum(WEIGHTS[x] for x in used))}


__all__ = ["MANGLIK_HOUSES", "manglik", "simple_manglik"]
