"""Question -> topics -> relevant fact ids (deterministic keyword routing; no LLM)."""
import re

from ..timeline import load_weights
from .facts import Fact

KEYWORDS: dict[str, list[str]] = {
    "job_change": ["job change", "change job", "switch job", "new job", "naukri badal", "job badalna", "resign", "quit"],
    "career": ["career", "job", "profession", "work", "business", "promotion", "naukri", "kaam", "vyapar", "karobar",
               "नौकरी", "करियर", "व्यापार"],
    "marriage": ["marriage", "marry", "spouse", "wife", "husband", "relationship", "partner", "love", "shaadi", "shadi",
                 "vivah", "शादी", "विवाह"],
    "wealth": ["wealth", "money", "finance", "income", "rich", "savings", "paisa", "paise", "dhan", "धन",
               "पैसा"],
    "health": ["health", "illness", "disease", "sehat", "bimari", "fitness", "स्वास्थ्य"],
    "education": ["education", "study", "exam", "degree", "college", "padhai", "पढ़ाई", "शिक्षा"],
    "children": ["child", "children", "kids", "baby", "pregnan", "santan", "bachche", "संतान"],
    "property": ["property", "house", "land", "home", "flat", "vehicle", "ghar", "zameen", "घर"],
    "travel": ["travel", "abroad", "foreign", "settle", "immigrat", "videsh", "विदेश"],
    "spirituality": ["spiritual", "moksha", "meditation", "dharma", "guru", "adhyatm", "आध्यात्म"],
    "family": ["family", "mother", "father", "parents", "siblings", "mata", "pita", "परिवार"],
}
DIVISIONAL = {"career": ["D10"], "job_change": ["D10"], "marriage": ["D9"], "children": ["D7"], "wealth": ["D9", "D10"],
              "spirituality": ["D9"], "education": ["D9"], "health": ["D9"], "property": ["D9"], "travel": ["D9"],
              "family": ["D9"]}
JAIMINI_TAGS = {"marriage": {"UL", "DK", "karakamsa"}, "career": {"AL", "AK", "karakamsa"},
                "job_change": {"AL", "AK"}, "wealth": {"AL"}, "spirituality": {"AK", "karakamsa"}}


def detect_topics(question: str) -> list[str]:
    """Topics found in the question, most specific first (job_change before career). Empty => 'general'."""
    q = question.lower()
    found = [t for t, kws in KEYWORDS.items() if any(re.search(r"\b" + re.escape(w), q) if w.isascii() else w in q
                                                    for w in kws)]
    if "job_change" in found and "career" in found:
        found.remove("career")
    return found or ["general"]


def select_facts(question: str, facts: list[Fact], max_facts: int = 40) -> tuple[list[str], list[Fact]]:
    """Facts relevant to the question: area houses and their lords/occupants, karaka planets, relevant divisional charts,
    yogas touching these planets, running dashas, key transits. Always includes lagna and dasha facts."""
    topics = detect_topics(question)
    w = load_weights()["areas"]
    houses: set[int] = set()
    planets: set[str] = set()
    for t in topics:
        if t in w:
            houses |= set(w[t]["houses"])
            planets |= set(w[t]["karakas"])
    if "general" in topics:
        houses |= {1, 5, 9, 10}
        planets |= {"Moon", "Sun", "Jupiter", "Saturn"}
    for f in facts:
        if f.kind == "house" and f.houses[0] in houses:
            planets |= set(f.planets)
    chosen: list[Fact] = []
    divs = {v for t in topics for v in DIVISIONAL.get(t, [])}
    jtags = set().union(*(JAIMINI_TAGS.get(t, set()) for t in topics)) if topics else set()
    for f in facts:
        keep = (
            f.kind in ("lagna", "dasha", "window", "panchang")
            or (f.kind == "house" and f.houses[0] in houses)
            or (f.kind == "planet" and f.planets[0] in planets)
            or (f.kind == "yoga" and (set(f.planets) & planets or "dosha" in f.tags and "marriage" in topics))
            or (f.kind == "divisional" and f.data["varga"] in divs)
            or (f.kind == "jaimini" and set(f.tags) & jtags)
            or (f.kind == "transit" and (set(f.planets) & {"Jupiter", "Saturn"} or "sade_sati" in f.tags))
        )
        if keep:
            chosen.append(f)
    return topics, chosen[:max_facts]
