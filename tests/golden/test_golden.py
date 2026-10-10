"""Golden-chart tests. NOTE: the JSON files are engine-generated regression snapshots (see scripts/make_golden.py),
not JHora exports. They guard against unintended changes; swap `expected` for JHora data for cross-validation.
Tolerances follow the plan: longitude 1 arcminute, dasha 1 day, SAV exact."""
import json
from datetime import date, datetime, time
from pathlib import Path

import pytest

from kundli.chart import generate
from kundli.geo import resolve_place
from kundli.models import BirthInput

FILES = sorted(Path(__file__).parent.glob("*.json"))
ARCMIN = 1 / 60


def _chart(g):
    b = BirthInput(name=g["q"], date=date.fromisoformat(g["date"]), time=time.fromisoformat(g["time"]) if g["time"] else None,
                   place=resolve_place(g["q"], choice=0), fold=g["fold"])
    return generate(b)


def test_golden_set_covers_required_cases():
    whys = " ".join(json.loads(f.read_text())["why"] for f in FILES)
    assert len(FILES) >= 10
    for need in ("southern", "pre-1950", "DST overlap", "midnight", "high latitude", "ingress", "unknown"):
        assert need in whys


@pytest.mark.parametrize("f", FILES, ids=[f.stem for f in FILES])
def test_golden_matches(f):
    g = json.loads(f.read_text())
    k, e = _chart(g), g["expected"]
    if e["lagna"]:
        assert k.lagna["sign"] == e["lagna"]["sign"]
        assert abs(k.lagna["degree_in_sign"] - e["lagna"]["deg"]) < ARCMIN
    else:
        assert k.lagna is None
    for p in k.planets:
        x = e["planets"][p.name]
        assert (p.sign, p.nakshatra, p.pada) == (x["sign"], x["nak"], x["pada"]) or abs(p.degree_in_sign - x["deg"]) < ARCMIN
        assert abs(p.degree_in_sign - x["deg"]) < ARCMIN
        assert p.varga_signs["D9"] == x["d9"] and p.varga_signs["D10"] == x["d10"]
        assert p.retrograde == x["retro"]
    for m, (lord, start) in zip(k.dashas["vimshottari"]["mahadashas"], e["vimshottari"], strict=True):
        assert m["lord"] == lord
        assert abs((datetime.fromisoformat(m["start_utc"]) - datetime.fromisoformat(start)).total_seconds()) < 86400
    assert (k.ashtakavarga["sav"] if k.ashtakavarga else None) == e["sav"]
    assert k.notes == e["notes"]


@pytest.mark.parametrize("f", FILES, ids=[f.stem for f in FILES])
def test_golden_invariants(f):
    k = _chart(json.loads(f.read_text()))
    if k.ashtakavarga:
        assert sum(k.ashtakavarga["sav"]) == 337
    ms = k.dashas["vimshottari"]["mahadashas"]
    assert all(a["end_utc"] == b["start_utc"] for a, b in zip(ms, ms[1:], strict=False))
    total = (datetime.fromisoformat(ms[-1]["end_utc"]) - datetime.fromisoformat(ms[0]["start_utc"])).total_seconds()
    assert total / 86400 == pytest.approx(120 * 365.25, abs=1e-2)
    pl = {p.name: p for p in k.planets}
    assert (pl["Rahu"].sidereal_lon - pl["Ketu"].sidereal_lon) % 360 == pytest.approx(180)
    if k.shadbala:
        assert all(v["total_virupas"] > 0 for v in k.shadbala["planets"].values())


def test_special_golden_behaviours():
    by = {f.stem: json.loads(f.read_text()) for f in FILES}
    tr = _chart(by["tromso_midnight_sun"])
    assert tr.shadbala is None and any("sunrise" in n for n in tr.notes)       # polar day handled, no crash
    unk = _chart(by["agra_time_unknown"])
    assert unk.lagna is None and unk.shadbala is None and unk.birth["time_unknown"]
    assert unk.dashas["vimshottari"]["mahadashas"]                              # Moon-only outputs still present
    ny = _chart(by["new_york_dst_overlap"])
    assert ny.birth["utc_offset_seconds"] == -4 * 3600
    assert _chart({**by["delhi_1943"]})  .birth["utc_offset_seconds"] == int(6.5 * 3600)
    sb = _chart(by["agra_sign_boundary"])
    sun = next(p for p in sb.planets if p.name == "Sun")
    assert sun.sign == 11 and sun.degree_in_sign > 29.9                         # last minute of sidereal Pisces
