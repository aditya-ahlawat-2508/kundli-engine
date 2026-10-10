"""Deterministic rule-based reading: works with no LLM. Templates are keyed on yoga effects_key and house/planet
combinations (templates.yaml). Output shape equals the LLM response so the same validator applies."""
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..timeline import load_weights
from .facts import Fact
from .retrieval import detect_topics

TPL = Path(__file__).parent / "templates.yaml"


@lru_cache(maxsize=1)
def templates() -> dict[str, Any]:
    return yaml.safe_load(TPL.read_text(encoding="utf-8"))


def _ord(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _placement(h: int | None) -> str:
    if h in (1, 4, 5, 7, 9, 10):
        return "good"
    if h in (6, 8, 12):
        return "hard"
    return "mid"


def rule_based_reading(question: str, facts: list[Fact], language: str = "en") -> dict[str, Any]:
    """Claims built from the selected facts only. `language`: en | hi (hinglish falls back to en)."""
    t = templates()["hi" if language == "hi" else "en"]
    topics = detect_topics(question)
    area = load_weights()["areas"]
    houses = {h for tp in topics if tp in area for h in area[tp]["houses"]} or {1, 5, 9, 10}
    claims: list[dict[str, Any]] = []
    by_planet = {f.planets[0]: f for f in facts if f.kind == "planet"}

    def hn(h: int) -> str:
        return str(h) if language == "hi" else _ord(h)

    for f in facts:
        if f.kind == "house" and f.houses[0] in houses:
            h, lord = f.houses[0], f.data["lord"]
            text = t["house_line"].format(h=hn(h), theme=t["house_theme"][h], sign=f.data["sign"], lord=lord,
                                          placement=t["placement"][_placement(f.data["lord_house"])])
            ids = [f.id] + ([by_planet[lord].id] if lord in by_planet else [])
            claims.append({"text": text, "fact_ids": ids})
            if lord in by_planet:
                d = by_planet[lord].data["dignity"]
                key = "strong" if d in ("exalted", "own", "moolatrikona") else "weak" if d == "debilitated" else "plain"
                claims.append({"text": t["dignity"][key].format(planet=lord, dignity=d), "fact_ids": [by_planet[lord].id]})
    for f in facts:
        if f.kind == "yoga" and (set(f.planets) & {p for g in facts if g.kind == "planet" for p in g.planets}):
            key = f.data["effects_key"]
            name = f.text.split(" is present")[0]
            if f.data["effective"] is False:
                claims.append({"text": t["yoga_cancelled"].format(name=name, cancel=f.text.split("cancelled by ")[-1].split(";")[0].rstrip(").")),
                               "fact_ids": [f.id]})
            elif key in t["yoga_effect"]:
                claims.append({"text": t["yoga_line"].format(name=name, effect=t["yoga_effect"][key]), "fact_ids": [f.id]})
    for f in facts:
        if f.kind == "dasha":
            rel = sorted(set(f.houses) & houses)
            if rel:
                text = t["dasha_line"].format(level=f.data["level"], lord=f.data["lord"], start=f.data["start"],
                                              end=f.data["end"], rel=", ".join(map(str, rel)))
            else:
                text = t["dasha_neutral"].format(level=f.data["level"], lord=f.data["lord"], start=f.data["start"],
                                                 end=f.data["end"])
            claims.append({"text": text, "fact_ids": [f.id]})
        elif f.kind == "window":
            claims.append({"text": t["window_line"].format(kind=f.data["kind"], start=f.data["start"], end=f.data["end"]),
                           "fact_ids": [f.id]})
    if not claims:
        return {"summary": t["no_facts"], "claims": [], "confidence": "low", "language": language, "mode": "rules"}
    return {"summary": t["summary"].format(topics=", ".join(x.replace("_", " ") for x in topics)), "claims": claims,
            "confidence": "medium" if len(claims) > 4 else "low", "language": language, "mode": "rules"}


def disclaimer(language: str = "en") -> str:
    return templates()["hi" if language == "hi" else "en"]["disclaimer"]
