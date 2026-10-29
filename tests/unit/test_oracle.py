"""Oracle tooling: cases, tolerance-aware diff, convention fingerprinting and guarded collection."""
import json
from datetime import date, time
from pathlib import Path

import pytest

from kundli.chart import generate
from kundli.errors import KundliError
from kundli.models import BirthInput, Place
from kundli.oracle.cases import generate_cases
from kundli.oracle.collect import collect
from kundli.oracle.diff import FieldClass, diff, parse_dt, summarize
from kundli.oracle.fingerprint import fingerprint_dasha, fingerprint_positions
from kundli.service import make_birth

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads((ROOT / "tests/oracle/fixtures/reference_1985.json").read_text())


def test_cases_are_deterministic_and_cover_edge_cases():
    a, b = generate_cases(120, 1), generate_cases(120, 1)
    assert a == b and len(a) == 120 and a != generate_cases(120, 2)
    tags = {t for c in a for t in c["tags"]}
    assert {"midnight", "dst-overlap", "dst-gap", "polar", "pre-1950", "southern-hemisphere", "time-unknown"} <= tags
    assert (ROOT / "tests/oracle/cases.json").exists()


def test_engine_handles_the_special_and_a_sample_of_random_cases():
    cases = [c for c in generate_cases(120, 20260101) if c["id"].startswith("special")] + generate_cases(120)[14:24]
    for c in cases:
        try:
            k = generate(make_birth(c["name"], c["date"], c["time"], None, None, c["fold"], c["lat"], c["lon"], c["tz"]))
        except KundliError as e:
            assert type(e).__name__ == c["expect_error"] or c["expect_error"] is None and "DST" in str(e), c["id"]
            continue
        assert c["expect_error"] is None and k.planets, c["id"]


def test_diff_tolerances():
    exp = {"sunrise": "2026-10-14T06:00:00", "planet": {"longitude": 100.0, "name": "Sun"},
           "mahadasha": {"start": "2026-01-01T00:00:00"}, "text": "x"}
    ok = {"sunrise": "2026-10-14T06:00:50", "planet": {"longitude": 100.016, "name": "Sun"},
          "mahadasha": {"start": "2026-01-01T20:00:00"}, "text": "different words"}
    r = diff(exp, ok)
    assert not r.mismatches and r.match_rate == 1.0
    bad = {"sunrise": "2026-10-14T06:02:00", "planet": {"longitude": 100.1, "name": "Moon"},
           "mahadasha": {"start": "2026-01-03T00:00:00"}, "text": ""}
    kinds = {m.path: m.kind for m in diff(exp, bad).mismatches}
    assert kinds == {"sunrise": FieldClass.TIME, "planet.longitude": FieldClass.LONGITUDE, "planet.name": FieldClass.EXACT,
                     "mahadasha.start": FieldClass.DATE, "text": FieldClass.TEXT}


def test_diff_longitude_wraps_and_reports_missing():
    r = diff({"sidereal_longitude": 359.99, "gone": 1}, {"sidereal_longitude": 0.0})
    assert not r.mismatches and r.missing == ["gone"] and summarize(r)["missing"] == 1
    assert parse_dt("23-02-1985 05:45")[1] is True and parse_dt("23-02-1985")[1] is False and parse_dt("abc") is None


def _fixture_birth():
    b = FIXTURE["birth"]
    p = Place(name=b["place"], lat=b["lat"], lon=b["lon"], tz=b["tz"], source="manual")
    return BirthInput(name="f", date=date.fromisoformat(b["date"]), time=time.fromisoformat(b["time"]), place=p)


def test_fingerprint_identifies_reference_conventions():
    fits = fingerprint_positions(_fixture_birth(), FIXTURE["expected"]["sidereal_longitudes"])
    assert fits[0].variant.name == "lahiri/mean" and fits[0].max_error < 0.001 and fits[1].mean_error > 10 * fits[0].mean_error
    true_node = next(f for f in fits if f.variant.name == "lahiri/true")
    assert true_node.max_error > 1.0  # the node type is the discriminating convention
    d = fingerprint_dasha(_fixture_birth(), [tuple(x) for x in FIXTURE["expected"]["vimshottari_maha_starts"]])
    assert d[0].variant.name == "year=365.25" and d[0].max_error < 1.0


def test_collect_refuses_bulk_without_tos_check(tmp_path):
    cases = generate_cases(10)
    with pytest.raises(PermissionError):
        collect("planets", cases, lambda e, r: {}, out_dir=tmp_path)
    assert collect("planets", cases[:3], lambda e, r: {"ok": r["id"]}, out_dir=tmp_path)
    assert len(collect("horo_chart/:chart_id", cases, lambda e, r: {}, out_dir=tmp_path, tos_checked=True)) == 10
    assert (tmp_path / "horo_chart__chart_id" / "special-midnight.json").exists()
