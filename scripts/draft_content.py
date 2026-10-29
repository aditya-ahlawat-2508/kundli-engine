"""Compose DRAFT content blocks from the vocabulary in scripts/content_data.py (no LLM, deterministic). Writes
`status: draft` blocks under src/kundli/content/blocks/<lang>/<topic>/; drafts are never served until a human reviews them
and `kundli content freeze` locks them (docs/content_rules.md).

    uv run python scripts/draft_content.py [--topics rashi_report,ascendant_report,...] [--langs en,hi] [--overwrite]

Topics covered: house_report, rashi_report, ascendant_report, numerology (radical/destiny/name), dosha (kaal sarp, manglik,
sade sati), remedy (gem texts and roles, Sade Sati practices). Others (nakshatra, daily, match, lalkitab) have no vocabulary yet; use `python -m kundli.content.draft`."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import content_data as cd

from kundli.content import keys, schema
from kundli.content.store import DEFAULT_DIR
from kundli.data.tables import ENEMIES, EXALTATION, FRIENDS, OWN_SIGNS, SIGN_LORDS

SRC = "template:scripts/content_data.py (original vocabulary, unreviewed draft)"
PLANET_NAMES = [p.title() for p in keys.PLANETS]  # Sun, Moon, ...


def _dignity(planet: str, sign: int) -> tuple[str, str]:
    """(dignity key for DIGNITY_TEXT, sign lord). Natural relation to the sign lord only (no chart-dependent temporal friendship)."""
    lord = SIGN_LORDS[sign]
    if planet in ("Rahu", "Ketu"):
        return "node", lord
    ex = EXALTATION[planet][0]
    if sign == ex:
        return "exalted", lord
    if sign == (ex + 6) % 12:
        return "debilitated", lord
    if sign in OWN_SIGNS[planet]:
        return "own", lord
    return ("friend" if lord in FRIENDS[planet] else "enemy" if lord in ENEMIES[planet] else "neutral"), lord


def rashi(lang: str) -> dict[str, str]:
    out = {}
    for pi, planet in enumerate(cd.PLANETS):
        for sign in range(12):
            dk, lord = _dignity(planet, sign)
            el, mod = cd.ELEMENTS[sign % 4], cd.MODALITIES[sign % 3]
            n = cd.NAMES[lang]
            text = cd.PIS_TEMPLATE[lang].format(
                P=n["planets"][planet], themes=cd.THEMES[lang][planet], S=n["signs"][sign], mod=n["modalities"][mod],
                el=n["elements"][el], L=n["planets"][lord], trait=cd.SIGN_TRAIT[lang][sign],
                phrase=cd.EXPRESSION[lang][planet][el], dignity=cd.DIGNITY_TEXT[lang][dk].format(P=n["planets"][planet], L=n["planets"][lord]))
            out[keys.rashi_report(planet, sign)] = text
    return out


def house(lang: str) -> dict[str, str]:
    out = {}
    n = cd.NAMES[lang]
    for planet in cd.PLANETS:
        for h in range(1, 13):
            if lang == "en":
                text = (f"{n['planets'][planet]} signifies {cd.THEMES['en'][planet]}. In the {cd.ORD_EN[h - 1]} house, which concerns "
                        f"{cd.HOUSE_THEME['en'][h - 1]}, these themes tend to show up through that area of life. {cd.PLANET_NOTE['en'][planet]}")
            else:
                text = (f"{n['planets'][planet]} {cd.THEMES['hi'][planet]} का कारक है। {h}वें भाव में, जो {cd.HOUSE_THEME['hi'][h - 1]} से "
                        f"जुड़ा है, ये विषय जीवन के उसी क्षेत्र में दिखाई देते हैं। {cd.PLANET_NOTE['hi'][planet]}")
            out[keys.house_report(planet, h)] = text
    return out


def ascendant(lang: str) -> dict[str, str]:
    return {keys.ascendant_report(s): f"{cd.LAGNA[lang][s][0]}: {cd.LAGNA[lang][s][1]}" for s in range(12)}


def numerology(lang: str) -> dict[str, str]:
    return {f"numerology.{kind}.{n}": cd.NUMEROLOGY[lang][n] for kind in ("radical", "destiny", "name") for n in range(1, 10)}


def dosha(lang: str) -> dict[str, str]:
    k, m, s = cd.KAAL_SARPA[lang], cd.MANGLIK[lang], cd.SADHESATI[lang]
    out = {"dosha.kaalsarpa.absent": k["absent"], "dosha.kaalsarpa.partial": f"{k['partial']} {k['intro']}"}
    for i, t in enumerate(keys.KAALSARPA_TYPES):
        n, other = i + 1, (i + 6) % 12 + 1
        body = k["type"].format(type=cd.KAAL_SARPA_TYPES[i] if hasattr(cd, "KAAL_SARPA_TYPES") else t.title(), n=n, m=other,
                                a=cd.HOUSE_THEME[lang][n - 1], b=cd.HOUSE_THEME[lang][other - 1])
        out[f"dosha.kaalsarpa.{t}"] = f"{k['intro']} {body} {k['remedies']}"
    refs = {"en": "the Lagna, the Moon or Venus", "hi": "लग्न, चंद्र या शुक्र"}[lang]
    out["dosha.manglik.absent"] = m["none"]
    out["dosha.manglik.present"] = f"{m['intro']} {m['effective'].format(refs=refs)} {m['remedies']}"
    for c in ("mars_own_or_exalted", "jupiter_conjunct_or_aspects_mars"):
        out[f"dosha.manglik.cancelled.{c}"] = f"{m['intro']} {m['cancelled'].format(refs=refs)}"
    for phase in keys.SADHESATI_PHASES:
        if phase == "none":
            out["dosha.sadhesati.none"] = s["inactive"]
        else:
            out[f"dosha.sadhesati.{phase}"] = f"{s['intro']} {s['active'].format(phase=s['phase_names'][phase])} {s['guidance']} {s['remedies']}"
    return out


def remedy(lang: str) -> dict[str, str]:
    s = cd.SADHESATI[lang]
    out = {f"remedy.gem.{p.lower()}": f"{cd.GEM_TEXT[lang][p]} {cd.GEM_CAUTION[lang]}" for p in cd.PLANETS}
    out.update({f"remedy.gem_role.{role}": f"{title}: {text}" for role, (title, text) in cd.GEM_ROLE[lang].items()})
    for phase in keys.SADHESATI_PHASES:
        out[f"remedy.sadhesati.{phase}"] = (s["inactive"] if phase == "none" else
                                            f"{s['active'].format(phase=s['phase_names'][phase])} {s['guidance']} {s['remedies']}")
    return out


TOPICS = {"rashi_report": rashi, "house_report": house, "ascendant_report": ascendant, "numerology": numerology, "dosha": dosha, "remedy": remedy}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topics", default=",".join(TOPICS))
    ap.add_argument("--langs", default="en,hi")
    ap.add_argument("--out", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()
    reachable = keys.all_keys()
    written = skipped = 0
    for lang in a.langs.split(","):
        for topic in a.topics.split(","):
            for key, text in TOPICS[topic](lang).items():
                if key not in reachable:
                    raise SystemExit(f"{key} is not a reachable content key")
                if schema.path_for(a.out, key, lang).exists() and not a.overwrite:
                    skipped += 1
                    continue
                schema.write(a.out, schema.Block(key=key, lang=lang, text=text, status="draft", sources=[SRC]))  # type: ignore[arg-type]
                written += 1
    print(f"wrote {written} draft block(s), skipped {skipped} existing (status=draft: never served until reviewed and frozen)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
