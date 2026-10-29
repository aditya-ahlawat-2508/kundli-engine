"""The four remedy suggestions: gems, pujas, rudraksha and Sade Sati remedies. Each returns FACTS and content keys
(`remedy.*`), a `disclaimer`, and `tables_verified: false`; wording comes from the content store via the adapters."""
from datetime import datetime
from typing import Any

from ..data.tables import SEVEN
from ..doshas import kaal_sarpa, manglik, pitra_dosha, sadhesati_status
from ..models import Kundli
from .gems import gemstone_picks
from .selection import DISCLAIMER, matched_rules, planet_facts, rules

GEM_ROLES = ("life_stone", "benefic_stone", "lucky_stone")


def _flags(planet: str, f: dict[str, Any] | None) -> dict[str, Any]:
    if f is None:  # Rahu / Ketu have no functional-nature row
        return {"examine_with_care": False, "reasons": []}
    reasons = [x for x, on in (("functional_malefic", f["functional"] == "malefic"), ("debilitated", f["dignity"] == "debilitated"),
                               ("combust", f["combust"]), ("rules_6_8_12", bool(set(f["lord_of"]) & {6, 8, 12}))) if on]
    return {"examine_with_care": bool(reasons), "reasons": reasons}


def gem_suggestion(k: Kundli) -> dict[str, Any]:
    if k.lagna is None:
        raise ValueError("gem suggestions need a known birth time")
    facts = planet_facts(k)
    picks = []
    for g in gemstone_picks(k.lagna["sign"]):
        planet, role = str(g["planet"]), str(g["role"])
        f = facts.get(planet)
        picks.append({**g, "planet_facts": f, **_flags(planet, f), "weak": bool(f and (f["shadbala_ratio"] < 1.0 or f["dignity"] == "debilitated")),
                      "content_keys": {"gem": f"remedy.gem.{planet.lower()}", "role": f"remedy.gem_role.{role}"}})
    return {"stones": picks, "selection": "gems of the lords of the 1st, 5th and 9th houses; flags show where tradition advises care",
            "disclaimer": DISCLAIMER, "tables_verified": False}


def puja_suggestion(k: Kundli, as_of: datetime | None = None) -> dict[str, Any]:
    facts = planet_facts(k)
    out: list[dict[str, Any]] = []
    for p in SEVEN:
        why = matched_rules(p, facts[p])
        if why:
            out.append({"id": f"graha_shanti.{p.lower()}", "planet": p, "rules": why, "facts": facts[p],
                        "content_key": f"remedy.puja.graha_shanti.{p.lower()}"})
    present = {"kaal_sarpa": kaal_sarpa(k)["present"], "manglik": manglik(k)["is_manglik"], "pitra": pitra_dosha(k)["present"]}
    for r in rules()["dosha_pujas"]:
        if present[r["dosha"]]:
            out.append({"id": r["id"], "planet": None, "rules": [r["dosha"]], "facts": None, "content_key": f"remedy.puja.{r['id']}"})
    if as_of is not None and sadhesati_status(k, as_of)["active"] and not any(x["id"] == "graha_shanti.saturn" for x in out):
        out.append({"id": "graha_shanti.saturn", "planet": "Saturn", "rules": ["sade_sati_or_dhaiya_active"], "facts": facts["Saturn"],
                    "content_key": "remedy.puja.graha_shanti.saturn"})
    return {"pujas": out, "as_of": None if as_of is None else as_of.isoformat(), "disclaimer": DISCLAIMER, "tables_verified": False,
            "note": "Rahu and Ketu have no selection rule here (no consensus); Sade Sati is considered only when as_of is given"}


def rudraksha_suggestion(k: Kundli) -> dict[str, Any]:
    if k.lagna is None:
        raise ValueError("rudraksha suggestions need a known birth time")
    mukhi = rules()["rudraksha_mukhi"]
    picks = [{"role": g["role"], "planet": g["planet"], "mukhi": mukhi[str(g["planet"])],
              "content_key": f"remedy.rudraksha.{mukhi[str(g['planet'])]}"} for g in gemstone_picks(k.lagna["sign"])]
    return {"rudraksha": picks, "selection": "mukhi linked to the grahas of the gem candidates (rule unconfirmed)",
            "disclaimer": DISCLAIMER, "tables_verified": False}


def sadhesati_remedies(k: Kundli, as_of: datetime) -> dict[str, Any]:
    st = sadhesati_status(k, as_of)
    try:
        f = planet_facts(k)["Saturn"]
    except ValueError:
        f = None
    return {"status": {x: st[x] for x in ("active", "phase", "saturn_house_from_moon", "period", "as_of")}, "saturn_facts": f,
            "content_key": f"remedy.sadhesati.{st['phase'] or 'none'}", "disclaimer": DISCLAIMER, "tables_verified": False}


__all__ = ["GEM_ROLES", "gem_suggestion", "puja_suggestion", "rudraksha_suggestion", "sadhesati_remedies"]
