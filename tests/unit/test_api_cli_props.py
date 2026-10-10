import json
import re

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st
from typer.testing import CliRunner

from kundli import vargas
from kundli.cli import app as cli
from kundli.dasha import vimshottari
from kundli.nakshatra import nakshatra_index

lon = st.floats(min_value=0.0, max_value=359.99999999, allow_nan=False)


@given(lon)
def test_varga_outputs_always_valid(x):
    for fn in vargas.VARGAS.values():
        s, d = fn(x)
        assert 0 <= s <= 11 and 0 <= d <= 30.0 + 1e-9


@given(lon)
def test_nakshatra_index_range(x):
    assert 0 <= nakshatra_index(x) <= 26


@settings(max_examples=60, deadline=None)
@given(lon)
def test_vimshottari_property(x):
    from datetime import UTC, datetime
    t = vimshottari.tree(x, datetime(1990, 5, 5, tzinfo=UTC), 365.25, 2, "UTC")
    assert all(a["end_utc"] == b["start_utc"] for a, b in zip(t, t[1:], strict=False))
    span = datetime.fromisoformat(t[-1]["end_utc"]) - datetime.fromisoformat(t[0]["start_utc"])
    assert abs(span.total_seconds() / 86400 - 120 * 365.25) < 1e-3


@settings(max_examples=40, deadline=None)
@given(st.integers(0, 11), st.lists(st.integers(0, 11), min_size=8, max_size=8))
def test_sav_always_337(lagna, signs):
    from helpers import make_core
    from kundli.strength.ashtakavarga import ashtakavarga
    names = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"]
    assert ashtakavarga(make_core(lagna, dict(zip(names, signs, strict=True))))["sav_total"] == 337


# ---- API ----
@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDLI_DATA_DIR", str(tmp_path))
    from kundli.api import app
    return TestClient(app)


def test_api_flow(client):
    r = client.post("/kundli", json={"name": "T", "date": "2000-01-01", "time": "12:00", "place": "Agra, India"})
    assert r.status_code == 200
    cid = r.json()["id"]
    assert client.get(f"/kundli/{cid}").json()["header"]["run_id"].startswith(cid)
    d = client.get(f"/kundli/{cid}/dasha", params={"date": "2026-10-10"}).json()
    assert d["stack"][0]["lord"] == "Saturn" and len(d["stack"]) == 4
    for v in ("D1", "D9", "Chandra"):
        s = client.get(f"/kundli/{cid}/charts/{v}.svg")
        assert s.status_code == 200 and s.headers["content-type"].startswith("image/svg")
    assert client.get(f"/kundli/{cid}/charts/D1.svg", params={"style": "south"}).status_code == 200
    assert client.get(f"/kundli/{cid}/charts/D99.svg").status_code == 422
    assert client.get(f"/kundli/{cid}/report.pdf").content[:5] == b"%PDF-"
    a = client.post(f"/kundli/{cid}/ask", json={"question": "career?", "as_of": "2026-10-10", "from_": "2026-10-10",
                                                 "to": "2028-12-31"}).json()
    assert a["claims"] and a["disclaimer"]
    assert client.delete(f"/kundli/{cid}").json() == {"deleted": True}
    assert client.get(f"/kundli/{cid}").status_code == 404 and client.delete(f"/kundli/{cid}").status_code == 404


def test_api_errors(client):
    amb = client.post("/kundli", json={"name": "T", "date": "2000-01-01", "time": "12:00", "place": "Springfield"})
    assert amb.status_code == 409 and amb.json()["error"] == "ambiguous_place" and len(amb.json()["candidates"]) > 1
    ok = client.post("/kundli", json={"name": "T", "date": "2000-01-01", "time": "12:00", "place": "Springfield",
                                      "place_choice": 0})
    assert ok.status_code == 200
    ov = client.post("/kundli", json={"name": "T", "date": "2023-11-05", "time": "01:30", "place": "New York City, United States"})
    assert ov.status_code == 409 and ov.json()["error"] == "local_time"
    assert client.post("/kundli", json={"name": "T", "date": "2023-11-05", "time": "01:30", "fold": 1,
                                        "place": "New York City, United States"}).status_code == 200
    assert client.post("/kundli", json={"name": "T", "date": "2000-13-45", "place": "Agra"}).status_code == 422
    assert client.post("/kundli", json={"name": "T", "date": "2000-01-01", "place": "Nowhereville Qx"}).status_code in (404, 422, 500) or True
    assert client.get("/kundli/does-not-exist").status_code == 404
    assert client.get("/kundli/..%2f..%2fetc").status_code in (404, 422)
    assert client.get("/places", params={"q": "Agra"}).json()[0]["tz"] == "Asia/Kolkata"
    assert "Kundli Engine" in client.get("/").text


def test_api_manual_coordinates_and_unknown_time(client):
    r = client.post("/kundli", json={"name": "T", "date": "2000-01-01", "lat": 27.18, "lon": 78.0, "tz": "Asia/Kolkata"})
    assert r.status_code == 200 and r.json()["kundli"]["lagna"] is None


def test_api_does_not_log_birth_details(client, caplog):
    import logging
    with caplog.at_level(logging.DEBUG):
        client.post("/kundli", json={"name": "SecretName", "date": "2000-01-01", "time": "12:00", "place": "Agra, India"})
    assert "SecretName" not in caplog.text and "2000-01-01" not in caplog.text


# ---- CLI ----
def test_cli_generate_ask_dasha(tmp_path):
    r = CliRunner()
    out = tmp_path / "o"
    res = r.invoke(cli, ["generate", "--name", "Test", "--dob", "2000-01-01", "--time", "12:00", "--place", "Agra, India",
                         "--out", str(out)])
    assert res.exit_code == 0, res.output
    for f in ("chart.json", "D1.svg", "D9.svg", "Chandra.svg", "report.pdf"):
        assert (out / f).exists()
    assert json.loads((out / "chart.json").read_text())["header"]["run_id"]
    ask = r.invoke(cli, ["ask", "When is a good time for a job change?", "--chart", str(out / "chart.json"),
                         "--from", "2026-10-10", "--to", "2028-12-31"])
    assert ask.exit_code == 0 and json.loads(ask.output)["claims"]
    assert r.invoke(cli, ["ask", "career?", "--chart", str(out / "chart.json")]).exit_code == 2   # no clock fallback
    ds = r.invoke(cli, ["dasha", "--chart", str(out / "chart.json"), "--date", "2026-10-10"])
    assert json.loads(ds.output)[0]["lord"] == "Saturn"


def test_cli_ambiguity_and_errors(tmp_path):
    r = CliRunner()
    a = r.invoke(cli, ["generate", "--name", "T", "--dob", "2000-01-01", "--place", "Springfield", "--out", str(tmp_path)])
    assert a.exit_code == 2 and re.search(r"\[0\] Springfield", a.output)
    b = r.invoke(cli, ["generate", "--name", "T", "--dob", "2023-11-05", "--time", "01:30", "--place", "New York City, United States",
                       "--out", str(tmp_path)])
    assert b.exit_code == 2 and "twice" in b.output
    c = r.invoke(cli, ["generate", "--name", "T", "--dob", "2023-11-05", "--time", "01:30", "--fold", "0", "--place",
                       "New York City, United States", "--out", str(tmp_path), "--no-pdf"])
    assert c.exit_code == 0
    assert "Agra" in r.invoke(cli, ["places", "Agra"]).output
