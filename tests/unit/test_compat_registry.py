"""Endpoint registry, generated routes and the rule that no request path can reach offline content drafting."""
import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kundli.api import app
from kundli.compat import registry
from kundli.compat.adapters.engine_neutral import ADAPTERS

BODY = {"name": "x", "date": "1985-02-23", "time": "05:45", "lat": 20.8833, "lon": 76.2, "tz": "Asia/Kolkata",
        "config": {"node_type": "mean"}, "as_of": "2026-10-14"}
ROOT = Path(__file__).resolve().parents[2]


def test_registry_is_complete_and_consistent():
    rows = registry.load()
    assert len(rows) == 131 and len({r.name for r in rows}) == 131 and len({r.group for r in rows}) == 20
    assert registry.by_name("general_house_report/:planet_name").path == "general_house_report/{planet_name}"
    assert all(r.status != "done" for r in rows)  # nothing is oracle-verified yet


def test_gap_analysis_document_is_up_to_date():
    assert (ROOT / "docs" / "gap_analysis.md").read_text(encoding="utf-8") == registry.gap_markdown()


def test_every_adapter_matches_a_registry_endpoint():
    paths = {r.path for r in registry.load()}
    assert set(ADAPTERS) <= paths


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_built_endpoint_returns_data_and_conventions(client):
    r = client.post("/compat/planets", json=BODY)
    assert r.status_code == 200
    j = r.json()
    assert j["data"][0]["name"] == "Sun" and j["conventions_used"]["config"]["node_type"] == "mean"
    assert j["conventions_used"]["response_shape"] == "engine_neutral"


def test_path_params_and_dasha_as_of(client):
    assert client.post("/compat/planet_ashtak/Sun", json=BODY).json()["data"]["total"] == 48
    assert client.post("/compat/horo_chart/D9", json=BODY).status_code == 200
    r = client.post("/compat/current_vdasha_date", json=BODY)
    assert [x["level"] for x in r.json()["data"]][:2] == ["maha", "antar"]


def test_same_input_gives_identical_bytes(client):
    assert client.post("/compat/planets", json=BODY).content == client.post("/compat/planets", json=BODY).content


def test_unbuilt_endpoint_is_501_with_registry_info(client):
    r = client.post("/compat/moon_biorhythm", json=BODY)  # deliberately unimplemented (definition unconfirmed)
    assert r.status_code == 501 and r.json()["phase"] == "19" and r.json()["status"] == "missing"


def test_bad_requests_are_4xx_not_500(client):
    assert client.post("/compat/planets", json={**BODY, "config": {"ephemeris_path": "/etc"}}).status_code == 422
    assert client.post("/compat/planets", json={**BODY, "config": {"ephemeris": "swiss_files"}}).status_code == 422
    assert client.post("/compat/planets", json={**BODY, "date": "nonsense"}).status_code == 422
    assert client.post("/compat/current_vdasha", json={**BODY, "as_of": None}).status_code == 422
    assert client.post("/compat/horo_chart/D99", json=BODY).status_code == 422


def test_gem_endpoint_carries_disclaimer(client):
    assert "not medical" in client.post("/compat/basic_gem_suggestion", json=BODY).json()["data"]["disclaimer"]


def _imports(path: Path) -> set[str]:
    out: set[str] = set()
    for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            out.add(("." * n.level) + (n.module or ""))
            out |= {(n.module or "") + "." + a.name for a in n.names}
    return out


def test_request_paths_never_import_offline_content_drafting():
    files = [ROOT / "src/kundli/api.py", *(ROOT / "src/kundli/compat").rglob("*.py"),
             *(ROOT / "src/kundli/predict").rglob("*.py")]
    for f in files:
        assert not any("content.draft" in i or i.endswith("content.draft") for i in _imports(f)), f
