"""Regenerate tests/golden/*.json. These are ENGINE-GENERATED regression snapshots (tool: kundli-engine, defaults:
Lahiri/true node/whole sign/Moshier). They are NOT JHora/Parashara's Light exports; replace `expected` with
exports from those tools (noting settings) to get real cross-validation. See docs/open_questions.md."""
import json
from datetime import date, time
from pathlib import Path

from kundli.chart import generate
from kundli.geo import resolve_place
from kundli.models import BirthInput

OUT = Path(__file__).resolve().parents[1] / "tests" / "golden"


CASES = [
    ("agra_2000", "Agra, India", date(2000, 1, 1), time(12, 0), None, "reference"),
    ("mumbai_1985", "Mumbai", date(1985, 6, 15), time(5, 45), None, "morning"),
    ("sydney_1990", "Sydney, Australia", date(1990, 12, 25), time(23, 10), None, "southern hemisphere"),
    ("buenos_aires_1988", "Buenos Aires, Argentina", date(1988, 8, 8), time(8, 8), None, "southern hemisphere"),
    ("delhi_1943", "Delhi, India", date(1943, 3, 3), time(8, 15), None, "pre-1950 India (war time)"),
    ("new_york_dst_overlap", "New York City, United States", date(2023, 11, 5), time(1, 30), 0, "DST overlap fold=0"),
    ("tromso_midnight_sun", "Tromso, Norway", date(1995, 6, 21), time(14, 0), None, "high latitude, no sunset"),
    ("kolkata_midnight", "Kolkata, India", date(1990, 3, 15), time(0, 0), None, "midnight birth"),
    ("agra_sign_boundary", "Agra, India", date(2000, 4, 13), time(17, 21), None, "Sun near sidereal Aries ingress"),
    ("london_1970", "London, United Kingdom", date(1970, 11, 2), time(17, 25), None, "UK"),
    ("agra_time_unknown", "Agra, India", date(2004, 5, 5), None, None, "unknown time"),
]


def snapshot(k) -> dict:
    d = {"lagna": None if k.lagna is None else {"sign": k.lagna["sign"], "deg": round(k.lagna["degree_in_sign"], 4)},
         "planets": {p.name: {"sign": p.sign, "deg": round(p.degree_in_sign, 4), "nak": p.nakshatra, "pada": p.pada,
                              "d9": p.varga_signs["D9"], "d10": p.varga_signs["D10"], "retro": p.retrograde}
                     for p in k.planets},
         "vimshottari": [[m["lord"], m["start_utc"]] for m in k.dashas["vimshottari"]["mahadashas"]],
         "sav": None if k.ashtakavarga is None else k.ashtakavarga["sav"],
         "notes": k.notes}
    return d


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, q, d, t, fold, why in CASES:
        b = BirthInput(name=name, date=d, time=t, place=resolve_place(q, choice=0), fold=fold)
        k = generate(b)
        (OUT / f"{name}.json").write_text(json.dumps({
            "source": "kundli-engine regression snapshot (NOT JHora)", "why": why, "q": q, "date": d.isoformat(),
            "time": t.isoformat() if t else None, "fold": fold, "expected": snapshot(k)}, indent=1, sort_keys=True))
        print(name, k.lagna and k.lagna["sign_name"], k.notes[:1])
