"""POST /kundli input validation, config injection, and PDF markup escaping."""
import pytest
from fastapi.testclient import TestClient

from kundli.api import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDLI_DATA_DIR", str(tmp_path))
BASE = {"name": "T", "date": "1990-05-05", "time": "10:30", "lat": 28.6, "lon": 77.2, "tz": "Asia/Kolkata"}


@pytest.mark.parametrize("config", [{"ephemeris_path": "/etc"}, {"ephemeris": "swiss_files"}])
def test_client_cannot_set_server_side_config(config):
    r = client.post("/kundli", json={**BASE, "config": config})
    assert r.status_code == 422


@pytest.mark.parametrize("bad", [{"lat": 91}, {"lon": -181}, {"fold": 2}, {"name": "x" * 121}, {"place_choice": -1}])
def test_field_bounds_rejected(bad):
    assert client.post("/kundli", json={**BASE, **bad}).status_code == 422


def test_dasha_and_charts_validate_params():
    cid = client.post("/kundli", json=BASE).json()["id"]
    assert client.get(f"/kundli/{cid}/dasha", params={"date": "2025-01-01", "levels": 99}).status_code == 422
    assert client.get(f"/kundli/{cid}/dasha", params={"date": "2025-01-01", "system": "x"}).status_code == 422
    assert client.get(f"/kundli/{cid}/dasha", params={"date": "not-a-date"}).status_code == 422
    assert client.get(f"/kundli/{cid}/charts/D1.svg", params={"style": "round"}).status_code == 422
    assert client.post(f"/kundli/{cid}/ask", json={"question": "q", "as_of": "garbage"}).status_code == 422


def test_pdf_survives_markup_in_name():
    cid = client.post("/kundli", json={**BASE, "name": "A <b>&</b> <unclosed"}).json()["id"]
    r = client.get(f"/kundli/{cid}/report.pdf")
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
