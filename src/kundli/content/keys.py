"""The space of content keys that can be reached from computed facts. Each endpoint computes facts, builds a key here and asks
the store for the block; `reachable()` enumerates every key so the linter can demand coverage.

Keys: lowercase dotted parts; planets and signs by lowercase name; nakshatras by lowercase name with `_` for spaces.
Half points use `_` (`0_5`)."""
from ..data.tables import NAKSHATRAS, SIGNS

PLANETS = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu"]
SIGN_SLUGS = [s.lower() for s in SIGNS]
NAK_SLUGS = [n.lower().replace(" ", "_") for n in NAKSHATRAS]
from ..panchang.tarabala import TARAS  # nine taras counted from the birth nakshatra

KAALSARPA_TYPES = ["anant", "kulik", "vasuki", "shankhpal", "padma", "mahapadma", "takshak", "karkotak", "shankhchoor", "ghatak",
                   "vishdhar", "sheshnaag"]
SADHESATI_PHASES = ["sade_sati_rising", "sade_sati_peak", "sade_sati_setting", "dhaiya_kantaka", "dhaiya_ashtama", "none"]
MANGLIK_STATES = ["absent", "present", "cancelled.mars_own_or_exalted", "cancelled.jupiter_conjunct_or_aspects_mars"]
KOOTA_POINTS: dict[str, list[float]] = {"varna": [0, 1], "vashya": [0, 0.5, 1, 2], "tara": [1.5, 3], "yoni": [0, 1, 2, 3, 4],
                "graha_maitri": [0, 0.5, 1, 3, 4, 5], "gana": [0, 1, 5, 6], "bhakoot": [0, 7], "nadi": [0, 8]}
MATCH_VERDICTS = ["excellent", "good", "average", "not_recommended"]
MANGLIK_MATCH = ["neither", "both", "boy_only", "girl_only"]
DOSHA_STATES = ["absent", "effective", "cancelled"]
GEM_ROLES = ["life_stone", "benefic_stone", "lucky_stone"]
DOSHA_PUJAS = ["kaalsarpa_shanti", "manglik_shanti", "pitra_shanti"]


def num(x: float) -> str:
    return str(x).replace(".", "_").removesuffix("_0")


def slug(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def house_report(planet: str, house: int) -> str:
    return f"house_report.{slug(planet)}.{house}"


def rashi_report(planet: str, sign: int) -> str:
    return f"rashi_report.{slug(planet)}.{SIGN_SLUGS[sign]}"


def ascendant_report(sign: int) -> str:
    return f"ascendant_report.{SIGN_SLUGS[sign]}"


def nakshatra_report(nakshatra: str) -> str:
    return f"nakshatra_report.{slug(nakshatra)}"


def daily(tara: str, nakshatra: str) -> str:
    return f"daily.tara.{tara}.nakshatra.{slug(nakshatra)}"


def reachable() -> dict[str, list[str]]:
    """topic -> every key reachable from the engine's facts."""
    out: dict[str, list[str]] = {
        "house_report": [f"house_report.{p}.{h}" for p in PLANETS for h in range(1, 13)],
        "rashi_report": [f"rashi_report.{p}.{s}" for p in PLANETS for s in SIGN_SLUGS],
        "ascendant_report": [f"ascendant_report.{s}" for s in SIGN_SLUGS],
        "nakshatra_report": [f"nakshatra_report.{n}" for n in NAK_SLUGS],
        "daily": [f"daily.tara.{t}.nakshatra.{n}" for t in TARAS for n in NAK_SLUGS],
        "numerology": [f"numerology.{kind}.{n}" for kind in ("radical", "destiny", "name", "daily", "fast") for n in range(1, 10)],
        "dosha": ([f"dosha.manglik.{s}" for s in MANGLIK_STATES] + [f"dosha.kaalsarpa.{t}" for t in KAALSARPA_TYPES]
                  + ["dosha.kaalsarpa.absent", "dosha.kaalsarpa.partial"] + [f"dosha.sadhesati.{p}" for p in SADHESATI_PHASES]
                  + [f"dosha.pitra.{s}" for s in ("present", "absent")]),
        "match": ([f"match.koota.{k}.{num(p)}" for k, ps in KOOTA_POINTS.items() for p in ps]
                  + [f"match.verdict.{v}" for v in MATCH_VERDICTS] + [f"match.manglik.{m}" for m in MANGLIK_MATCH]
                  + [f"match.nadi_dosha.{s}" for s in DOSHA_STATES] + [f"match.bhakoot_dosha.{s}" for s in DOSHA_STATES]),
        "lalkitab": [f"lalkitab.remedy.{p}.{h}" for p in PLANETS for h in range(1, 13)],
        "remedy": ([f"remedy.gem.{p}" for p in PLANETS] + [f"remedy.gem_role.{r}" for r in GEM_ROLES]
                   + [f"remedy.puja.graha_shanti.{p}" for p in PLANETS[:7]] + [f"remedy.puja.{d}" for d in DOSHA_PUJAS]
                   + [f"remedy.rudraksha.{n}" for n in range(1, 10)] + [f"remedy.sadhesati.{s}" for s in SADHESATI_PHASES]),
    }
    return out


def all_keys() -> set[str]:
    return {k for ks in reachable().values() for k in ks}


__all__ = ["KAALSARPA_TYPES", "KOOTA_POINTS", "NAK_SLUGS", "PLANETS", "SADHESATI_PHASES", "SIGN_SLUGS", "TARAS", "all_keys",
           "ascendant_report", "daily", "house_report", "nakshatra_report", "num", "rashi_report", "reachable", "slug"]
