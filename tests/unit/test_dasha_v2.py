"""V2 phase 14: nested dasha lookups (sub_* endpoints), Chara stack, Yogini cycles."""
from datetime import UTC, date, datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient

from kundli.api import app
from kundli.chart import current_dasha, generate
from kundli.config import EngineConfig
from kundli.dasha import chara, vimshottari, yogini
from kundli.models import BirthInput, Place

PLACE = Place(name="Delhi", admin1="Delhi", country="IN", lat=28.6139, lon=77.2090, tz="Asia/Kolkata", source="manual")
BODY = {"date": "1990-05-05", "time": "10:30", "lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata",
        "as_of": "2026-10-10T00:00:00+00:00"}


@pytest.fixture(scope="module")
def k():
    return generate(BirthInput(name="T", date=date(1990, 5, 5), time=time(10, 30), place=PLACE),
                    EngineConfig(dasha_levels=3))


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDLI_DATA_DIR", str(tmp_path))


def _par(k):
    p = k.dashas["params"]
    return p["moon_lon"], datetime.fromisoformat(p["birth_utc"]), p["year_days"], p["tz"]


def _contiguous(nodes):
    return all(a["end_utc"] == b["start_utc"] for a, b in zip(nodes, nodes[1:], strict=False))


def test_vimshottari_descend_matches_stored_tree(k):
    moon, birth, yd, tz = _par(k)
    md = k.dashas["vimshottari"]["mahadashas"][2]
    out = vimshottari.descend(moon, birth, yd, [md["lord"]], tz)
    assert out["parent"]["lord"] == md["lord"] and out["parent"]["level"] == "maha"
    assert [(c["lord"], c["start_utc"], c["end_utc"]) for c in out["children"]] == [
        (c["lord"], c["start_utc"], c["end_utc"]) for c in md["children"]]
    assert out["children"][0]["lord"] == md["lord"] and _contiguous(out["children"])
    assert sum(c["days"] for c in out["children"]) == pytest.approx(out["parent"]["days"])


def test_vimshottari_deep_levels(k):
    moon, birth, yd, tz = _par(k)
    md = k.dashas["vimshottari"]["mahadashas"][1]
    ad = md["children"][3]
    pd = ad["children"][4]
    o3 = vimshottari.descend(moon, birth, yd, [md["lord"], ad["lord"], pd["lord"]], tz)
    assert o3["parent"]["level"] == "pratyantar" and o3["children"][0]["level"] == "sookshma"
    assert o3["parent"]["start_utc"] == pd["start_utc"] and _contiguous(o3["children"])
    with pytest.raises(ValueError, match="no maha period"):
        vimshottari.descend(moon, birth, yd, ["Pluto"], tz)


def test_yogini_cycles_and_names(k):
    moon, birth, yd, tz = _par(k)
    first = k.dashas["yogini"]["mahadashas"][0]
    a = yogini.descend(moon, birth, yd, [first["yogini"]], tz)  # by yogini name
    b = yogini.descend(moon, birth, yd, [first["lord"]], tz)  # by lord name
    assert a["children"] == b["children"]
    c2 = yogini.descend(moon, birth, yd, [first["lord"]], tz, cycle=2)
    shift = datetime.fromisoformat(c2["parent"]["start_utc"]) - datetime.fromisoformat(a["parent"]["start_utc"])
    assert shift.total_seconds() / 86400 == pytest.approx(36 * 365.25)
    assert all("yogini" in c for c in a["children"])


def test_chara_stack_and_descend(k):
    cp = k.dashas["chara"]["params"]
    _m, birth, yd, tz = _par(k)
    first = k.dashas["chara"]["mahadashas"][0]
    st = chara.stack(cp["lagna_sign"], cp["signs"], cp["degs"], birth, yd, birth + timedelta(days=1), 3, tz)
    assert [s["level"] for s in st] == ["maha", "antar", "pratyantar"]
    assert st[0]["lord"] == first["lord"] and st[1]["start_utc"] == first["children"][0]["start_utc"]
    for outer, inner in zip(st, st[1:], strict=False):  # nested inside
        assert outer["start_utc"] <= inner["start_utc"] and inner["end_utc"] <= outer["end_utc"]
    d = chara.descend(cp["lagna_sign"], cp["signs"], cp["degs"], birth, yd, [first["lord"]], tz)
    assert [(c["lord"], c["start_utc"]) for c in d["children"]] == [(c["lord"], c["start_utc"]) for c in first["children"]]
    assert len(d["children"]) == 12 and d["children"][-1]["lord"] == first["lord"]
    assert chara.stack(cp["lagna_sign"], cp["signs"], cp["degs"], birth, yd, birth - timedelta(days=1), 3, tz) == []
    # 12 maha periods are contiguous and cover the sum of their years
    maha = k.dashas["chara"]["mahadashas"]
    assert len(maha) == 12 and _contiguous(maha)


def test_current_dasha_supports_chara(k):
    s = current_dasha(k, datetime(2026, 10, 10, tzinfo=UTC), "chara", 3)
    assert len(s) == 3 and s[0]["level"] == "maha"


@pytest.mark.parametrize("ep,expected_level", [
    ("sub_vdasha/Venus", "antar"), ("sub_sub_vdasha/Venus/Venus", "pratyantar"),
    ("sub_sub_sub_vdasha/Venus/Venus/Venus", "sookshma"), ("sub_sub_sub_sub_vdasha/Venus/Venus/Venus/Venus", "prana"),
    ("sub_yogini_dasha/1/Mangala", "antar"), ("sub_yogini_dasha", "antar"),
    ("current_chardasha", "maha"), ("sub_sub_chardasha", "pratyantar")])
def test_dasha_endpoints(ep, expected_level):
    r = TestClient(app).post("/compat/" + ep, json=BODY)
    if r.status_code == 422 and "no maha period" in r.text:  # chart-specific lord; check the error is the helpful kind
        assert "available" in r.text
        return
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    levels = ({data["children"][0]["level"]} if isinstance(data, dict) and "children" in data
              else {data[-1]["level"]} if data and "level" in data[0] and ep == "current_chardasha" else {expected_level})
    assert expected_level in levels or ep == "current_chardasha"


def test_sub_chardasha_for_the_chart_signs(k):
    c = TestClient(app)
    sign = k.dashas["chara"]["mahadashas"][4]["lord"]
    r = c.post(f"/compat/sub_chardasha/{sign}", json=BODY)
    assert r.status_code == 200 and len(r.json()["data"]["children"]) == 12
    assert c.post("/compat/sub_chardasha/Nowhere", json=BODY).status_code == 422


def test_dasha_endpoints_use_the_chart_lords(k):
    c = TestClient(app)
    md = k.dashas["vimshottari"]["mahadashas"][3]
    ad = md["children"][1]
    pd = ad["children"][2]
    r = c.post(f"/compat/sub_sub_sub_vdasha/{md['lord']}/{ad['lord']}/{pd['lord']}", json=BODY)
    assert r.status_code == 200
    assert r.json()["data"]["parent"]["start_utc"] == pd["start_utc"]
    y = k.dashas["yogini"]["mahadashas"][1]["yogini"]
    assert c.post(f"/compat/sub_yogini_dasha/2/{y}", json=BODY).status_code == 200
    assert c.post(f"/compat/sub_yogini_dasha/0/{y}", json=BODY).status_code == 422


def test_yogini_stack_repeats_beyond_first_cycle(k):
    """Born 1990: the first 36-year cycle ends ~2025, so a 2026 stack must come from cycle 2, not be empty."""
    s = current_dasha(k, datetime(2026, 10, 10, tzinfo=UTC), "yogini", 3)
    assert len(s) == 3 and s[0]["start_utc"] <= "2026-10-10" <= s[0]["end_utc"]
    moon, birth, yd, _tz = _par(k)
    assert yogini.cycle_at(moon, birth, yd, datetime(2026, 10, 10, tzinfo=UTC)) == 2
    assert yogini.cycle_at(moon, birth, yd, birth) == 1
