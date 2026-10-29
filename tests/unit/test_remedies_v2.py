"""V2 phase 22: remedy selection rules (gems, pujas, rudraksha, Sade Sati) and their endpoints."""
import importlib
from datetime import UTC, date, datetime, time

import pytest
from fastapi.testclient import TestClient

from kundli.api import app
from kundli.chart import generate
from kundli.config import EngineConfig
from kundli.content import ContentStore, keys, schema, set_default_store
from kundli.content.freeze import freeze, review
from kundli.content.lint import banned_claims
from kundli.data.tables import SEVEN
from kundli.doshas import kaal_sarpa, manglik, pitra_dosha, sadhesati_status
from kundli.models import BirthInput, Place
from kundli.remedies import (
    DISCLAIMER,
    gem_suggestion,
    gemstone_picks,
    holds,
    matched_rules,
    planet_facts,
    puja_suggestion,
    rudraksha_suggestion,
    rules,
    sadhesati_remedies,
)

selection = importlib.import_module("kundli.remedies.selection")
PLACE = Place(name="Delhi", admin1="Delhi", country="IN", lat=28.6139, lon=77.2090, tz="Asia/Kolkata", source="manual")
BODY = {"date": "1990-05-05", "time": "10:30", "lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata", "as_of": "2026-10-10"}
AS_OF = datetime(2026, 10, 10, tzinfo=UTC)


@pytest.fixture(scope="module")
def k():
    return generate(BirthInput(name="T", date=date(1990, 5, 5), time=time(10, 30), place=PLACE), EngineConfig())


@pytest.fixture(autouse=True)
def _isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDLI_DATA_DIR", str(tmp_path / "charts"))
    yield
    set_default_store(None)


def F(**kw):
    base = {"functional": "neutral", "dignity": "friend", "combust": False, "retrograde": False, "shadbala_ratio": 1.2,
            "house": 2, "lord_of": [3]}
    return {**base, **kw}


# ---- rules --------------------------------------------------------------------------------------------------
def test_rules_are_sourced_and_flagged():
    r = rules()
    assert {x["id"] for x in r["graha_shanti"]} == {"weak_benefic", "afflicted_malefic", "dusthana_lord_weak"}
    assert all(x["source"] and x["verify"] is True for x in r["graha_shanti"] + r["dosha_pujas"])
    assert sorted(r["rudraksha_mukhi"].values()) == list(range(1, 10)) and set(r["rudraksha_mukhi"]) == {*SEVEN, "Rahu", "Ketu"}
    assert [x["id"] for x in r["dosha_pujas"]] == ["kaalsarpa_shanti", "manglik_shanti", "pitra_shanti"]


def test_rule_file_is_validated(tmp_path, monkeypatch):
    bad = tmp_path / "r.yaml"
    bad.write_text("graha_shanti:\n  - {id: x, planets: [Sun], when: {nonsense: 1}, source: s, verify: true}\n"
                   "dosha_pujas: []\nrudraksha_mukhi: {Sun: 1, Moon: 2, Mars: 3, Mercury: 4, Jupiter: 5, Venus: 6, Saturn: 7, Rahu: 8, Ketu: 9}\n")
    monkeypatch.setattr(selection, "FILE", bad)
    selection.rules.cache_clear()
    with pytest.raises(ValueError, match="unknown predicates"):
        selection.rules()
    monkeypatch.undo()
    selection.rules.cache_clear()
    assert len(selection.rules()["graha_shanti"]) == 3


def test_predicates():
    assert holds({"functional": ["malefic"]}, F(functional="malefic")) and not holds({"functional": ["malefic"]}, F())
    assert holds({"dignity": ["debilitated"]}, F(dignity="debilitated")) and holds({"combust": True}, F(combust=True))
    assert holds({"retrograde": False}, F()) and not holds({"retrograde": True}, F())
    assert holds({"shadbala_ratio_below": 1.0}, F(shadbala_ratio=0.9)) and not holds({"shadbala_ratio_below": 1.0}, F(shadbala_ratio=1.0))
    assert holds({"house": [1, 4]}, F(house=4)) and not holds({"house": [1, 4]}, F(house=5))
    assert holds({"lord_of_any": [6, 8]}, F(lord_of=[8, 9])) and not holds({"lord_of_any": [6, 8]}, F(lord_of=[9]))
    both = {"functional": ["benefic"], "any_of": [{"combust": True}, {"shadbala_ratio_below": 1.0}]}
    assert holds(both, F(functional="benefic", combust=True)) and not holds(both, F(functional="benefic"))
    assert not holds(both, F(functional="malefic", combust=True))


def test_matched_rules_semantics():
    assert matched_rules("Jupiter", F(functional="benefic", shadbala_ratio=0.8)) == ["weak_benefic"]
    assert matched_rules("Jupiter", F(functional="benefic")) == []
    assert matched_rules("Mars", F(functional="malefic", house=8)) == ["afflicted_malefic"]
    assert matched_rules("Saturn", F(functional="malefic", house=6, lord_of=[6], shadbala_ratio=0.5)) == ["dusthana_lord_weak"]
    assert matched_rules("Rahu", F(functional="malefic", house=8)) == []  # no rule for the nodes


def test_facts_need_a_birth_time():
    nt = generate(BirthInput(name="T", date=date(1990, 5, 5), time=None, place=PLACE), EngineConfig())
    for fn in (planet_facts, gem_suggestion, puja_suggestion, rudraksha_suggestion):
        with pytest.raises(ValueError, match="birth time"):
            fn(nt)


# ---- suggestions --------------------------------------------------------------------------------------------
def test_gem_suggestion(k):
    g = gem_suggestion(k)
    assert [s["role"] for s in g["stones"]] == ["life_stone", "benefic_stone", "lucky_stone"]
    assert g["disclaimer"] == DISCLAIMER and "not medical" in DISCLAIMER and g["tables_verified"] is False
    facts = planet_facts(k)
    for s, base in zip(g["stones"], gemstone_picks(k.lagna["sign"]), strict=True):
        assert s["gem"] == base["gem"] and s["planet"] == base["planet"]
        f = facts[s["planet"]]
        assert s["weak"] == (f["shadbala_ratio"] < 1.0 or f["dignity"] == "debilitated")
        assert s["examine_with_care"] == bool(s["reasons"]) and set(s["reasons"]) <= {
            "functional_malefic", "debilitated", "combust", "rules_6_8_12"}
        assert s["content_keys"] == {"gem": f"remedy.gem.{s['planet'].lower()}", "role": f"remedy.gem_role.{s['role']}"}


def test_puja_suggestion_is_consistent_with_rules_and_doshas(k):
    out = puja_suggestion(k, AS_OF)
    facts = planet_facts(k)
    by_id = {p["id"]: p for p in out["pujas"]}
    for planet in SEVEN:
        expected = matched_rules(planet, facts[planet])
        sade = sadhesati_status(k, AS_OF)["active"] and planet == "Saturn"
        assert (f"graha_shanti.{planet.lower()}" in by_id) == (bool(expected) or sade), planet
        if expected:
            assert by_id[f"graha_shanti.{planet.lower()}"]["rules"] == expected
    assert ("kaalsarpa_shanti" in by_id) == kaal_sarpa(k)["present"]
    assert ("manglik_shanti" in by_id) == manglik(k)["is_manglik"] and ("pitra_shanti" in by_id) == pitra_dosha(k)["present"]
    for p in out["pujas"]:
        assert p["content_key"] == f"remedy.puja.{p['id']}" and p["content_key"] in keys.all_keys()
    assert out["disclaimer"] == DISCLAIMER
    without = puja_suggestion(k)
    assert without["as_of"] is None and len(without["pujas"]) <= len(out["pujas"])


def test_rudraksha_and_sadhesati(k):
    r = rudraksha_suggestion(k)
    mukhi = rules()["rudraksha_mukhi"]
    assert [x["planet"] for x in r["rudraksha"]] == [g["planet"] for g in gemstone_picks(k.lagna["sign"])]
    assert all(x["mukhi"] == mukhi[x["planet"]] and x["content_key"] == f"remedy.rudraksha.{x['mukhi']}" for x in r["rudraksha"])
    s = sadhesati_remedies(k, AS_OF)
    assert s["content_key"] == "remedy.sadhesati.dhaiya_ashtama" and s["status"]["active"] is True and s["saturn_facts"]["house"]
    assert sadhesati_remedies(k, datetime(2012, 1, 1, tzinfo=UTC))["content_key"].startswith("remedy.sadhesati.")
    with pytest.raises(ValueError):
        sadhesati_remedies(k, datetime(2026, 10, 10))  # naive time


def test_every_remedy_key_is_in_the_reachable_space(k):
    allk = keys.all_keys()
    assert sum(1 for x in allk if x.startswith("remedy.")) == 37
    emitted = {s["content_keys"][n] for s in gem_suggestion(k)["stones"] for n in ("gem", "role")}
    emitted |= {p["content_key"] for p in puja_suggestion(k, AS_OF)["pujas"]} | {x["content_key"] for x in rudraksha_suggestion(k)["rudraksha"]}
    emitted.add(sadhesati_remedies(k, AS_OF)["content_key"])
    assert emitted <= allk
    assert all(f"remedy.sadhesati.{p}" in allk for p in keys.SADHESATI_PHASES)


# ---- endpoints ----------------------------------------------------------------------------------------------
def strings(x):
    if isinstance(x, dict):
        for k_, v in x.items():
            if k_ != "content":  # text blocks are checked by the content linter, not here
                yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)
    elif isinstance(x, str):
        yield x


@pytest.mark.parametrize("ep", ["basic_gem_suggestion", "puja_suggestion", "rudraksha_suggestion", "sadhesati_remedies"])
def test_remedy_endpoints_are_safe_and_labelled(ep):
    r = TestClient(app).post("/compat/" + ep, json=BODY)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["disclaimer"] == DISCLAIMER and data["tables_verified"] is False
    flagged = {s: banned_claims(s) for s in strings(data) if banned_claims(s)}
    assert not flagged, flagged  # no price, urgency, guarantee or medical language in the engine's own output
    assert not any(k_ in str(data).lower() for k_ in ("price", "cost", "must wear", "buy now"))


def test_remedy_text_comes_only_from_the_store(tmp_path, k):
    c = TestClient(app)
    first = gem_suggestion(k)["stones"][0]
    key = first["content_keys"]["gem"]
    before = c.post("/compat/basic_gem_suggestion", json=BODY).json()["data"]["stones"][0]["content"]["gem"]
    assert before["status"] == "content_missing"
    root, lock = tmp_path / "blocks", tmp_path / "content.lock"
    schema.write(root, schema.Block(key=key, lang="en", text="This gem is traditionally associated with calm. No outcome is guaranteed.", sources=["t"]))
    review(root, key, "en", "Reviewer")
    freeze(root, lock)
    set_default_store(ContentStore(root, lock))
    after = c.post("/compat/basic_gem_suggestion", json=BODY).json()["data"]["stones"][0]["content"]["gem"]
    assert after["status"] == "ok" and after["text"].startswith("This gem")
    pujas = c.post("/compat/puja_suggestion", json=BODY).json()["data"]["pujas"]
    assert pujas and all(p["content"]["status"] == "content_missing" for p in pujas)


def test_remedy_endpoint_errors():
    c = TestClient(app)
    for ep in ("basic_gem_suggestion", "puja_suggestion", "rudraksha_suggestion"):
        assert c.post("/compat/" + ep, json={**BODY, "time": None}).status_code == 422
    assert c.post("/compat/sadhesati_remedies", json={**BODY, "as_of": None}).status_code == 422
    assert c.post("/compat/puja_suggestion", json={**BODY, "as_of": None}).status_code == 200  # as_of optional here
