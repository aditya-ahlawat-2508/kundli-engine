"""V2 phase 20: Lal Kitab layout (two editions), tables, debts and remedy selection."""
from datetime import date, time

import pytest
from fastapi.testclient import TestClient

from kundli.api import app
from kundli.chart import generate
from kundli.config import EngineConfig
from kundli.lalkitab import debts, houses_table, lalkitab, layout, planets_table, remedy_for
from kundli.lalkitab.layout import house_of
from kundli.lalkitab.tables import DEBILITATED_HOUSE, EXALTED_HOUSE, PAKKA_GHAR, PLANETS, karakas
from kundli.models import BirthInput, Place

PLACE = Place(name="Delhi", admin1="Delhi", country="IN", lat=28.6139, lon=77.2090, tz="Asia/Kolkata", source="manual")


def natal(cfg=None, t=time(10, 30)):
    return generate(BirthInput(name="T", date=date(1990, 5, 5), time=t, place=PLACE), cfg or EngineConfig())


@pytest.fixture(scope="module")
def k():
    return natal()


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDLI_DATA_DIR", str(tmp_path))


# ---- tables -------------------------------------------------------------------------------------------------
def test_exaltation_and_debilitation_houses_are_derived_from_signs():
    assert [EXALTED_HOUSE[p] for p in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")] == [1, 2, 10, 6, 4, 12, 7]
    assert [DEBILITATED_HOUSE[p] for p in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")] == [7, 8, 4, 12, 10, 6, 1]
    for p in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"):
        assert (DEBILITATED_HOUSE[p] - EXALTED_HOUSE[p]) % 12 == 6  # always opposite


def test_pakka_ghar_table_shape():
    assert set(PAKKA_GHAR) == set(PLANETS) and all(1 <= h <= 12 for hs in PAKKA_GHAR.values() for h in hs)
    assert karakas(1) == ["Sun"] and "Moon" in karakas(4) and karakas(11) == []
    assert all(PAKKA_GHAR[p][0] in range(1, 13) for p in PLANETS)


# ---- layout -------------------------------------------------------------------------------------------------
def test_both_editions_place_every_planet_once(k):
    for ed in ("lagna_houses", "fixed_aries"):
        c = layout(k, ed)
        assert c["edition"] == ed and [h["house"] for h in c["houses"]] == list(range(1, 13))
        placed = [p for h in c["houses"] for p in h["planets"]]
        assert sorted(placed) == sorted(PLANETS)
        for h in c["houses"]:
            assert all(c["planet_house"][p] == h["house"] for p in h["planets"])


def test_edition_semantics(k):
    lag = k.lagna["sign"]
    for p in k.planets:
        assert house_of(k, p.name, "fixed_aries") == p.sign + 1
        assert house_of(k, p.name, "lagna_houses") == (p.sign - lag) % 12 + 1 == p.rashi_house
    fixed = layout(k, "fixed_aries")
    assert [h["sign"] for h in fixed["houses"]] == list(range(12))
    lagna_based = layout(k, "lagna_houses")
    assert lagna_based["houses"][0]["sign"] == lag


def test_unknown_birth_time():
    kk = natal(t=None)
    assert layout(kk, "fixed_aries")["houses"][0]["sign"] == 0  # needs no lagna
    with pytest.raises(ValueError, match="birth time"):
        layout(kk, "lagna_houses")


# ---- debts --------------------------------------------------------------------------------------------------
def spread(**kw):
    base = {p: 1 for p in PLANETS}
    base.update(kw)
    return base


def test_debt_rules():
    d = {x["id"]: x for x in debts(spread(Venus=9))["debts"]}
    assert d["pitri_rin"]["present"] and d["pitri_rin"]["matched"] == [{"planet": "Venus", "house": 9}]
    assert not d["matri_rin"]["present"] and not d["stri_rin"]["present"]
    d = {x["id"]: x for x in debts(spread(Ketu=4, Moon=7))["debts"]}
    assert d["matri_rin"]["present"] and d["stri_rin"]["present"] and not d["pitri_rin"]["present"]
    none = debts(spread())
    assert none["any_present"] is False and none["tables_verified"] is False and none["not_implemented"]
    many = {x["id"]: x["matched"] for x in debts(spread(Venus=2, Mercury=5, Rahu=12))["debts"]}
    assert len(many["pitri_rin"]) == 3


def test_debt_file_is_validated(tmp_path, monkeypatch):
    import importlib
    debts_mod = importlib.import_module("kundli.lalkitab.debts")  # the package attribute `debts` is the function
    bad = tmp_path / "d.yaml"
    bad.write_text("- {id: x, name: X, planets: [Pluto], houses: [1], source: s, verify: true}\n")
    monkeypatch.setattr(debts_mod, "FILE", bad)
    debts_mod.rules.cache_clear()
    with pytest.raises(ValueError, match="malformed"):
        debts_mod.rules()
    monkeypatch.undo()
    debts_mod.rules.cache_clear()
    assert len(debts_mod.rules()) == 3


# ---- remedies / tables --------------------------------------------------------------------------------------
def test_remedy_selection_is_keys_not_text():
    r = remedy_for("saturn", spread(Saturn=1))
    assert r["planet"] == "Saturn" and r["house"] == 1 and r["remedy_keys"] == ["lalkitab.remedy.saturn.1"]
    assert r["in_debilitation_house"] is True and r["in_pakka_ghar"] is False  # Saturn debilitated in house 1
    assert "content" not in r and "not medical" in r["disclaimer"]  # text is attached by the adapter from the content store
    v = remedy_for("Venus", spread(Venus=9))
    assert v["related_debts"] == ["pitri_rin"] and v["remedy_keys"] == ["lalkitab.remedy.venus.9"]
    with pytest.raises(ValueError, match="unknown planet"):
        remedy_for("Pluto", spread())


def test_planets_and_houses_tables(k):
    full = lalkitab(k)
    assert set(full["planets"]) == set(PLANETS) and len(full["houses"]) == 12 and full["tables_verified"] is False
    for name, row in full["planets"].items():
        assert row["in_pakka_ghar"] == (row["house"] in PAKKA_GHAR[name])
        assert row["in_exaltation_house"] == (EXALTED_HOUSE.get(name) == row["house"])
    for h in full["houses"]:
        assert h["empty"] == (not h["planets"]) and h["karakas"] == karakas(h["house"])
    c = layout(k, "fixed_aries")
    assert planets_table(k, c["planet_house"]) == full["planets"] and houses_table(c) == full["houses"]


# ---- endpoints ----------------------------------------------------------------------------------------------
BODY = {"date": "1990-05-05", "time": "10:30", "lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"}


@pytest.mark.parametrize("ep", ["lalkitab_horoscope", "lalkitab_planets", "lalkitab_houses", "lalkitab_debts",
                                "lalkitab_remedies/saturn"])
def test_lalkitab_endpoints(ep):
    r = TestClient(app).post("/compat/" + ep, json=BODY)
    assert r.status_code == 200, r.text
    assert r.json()["data"] and r.json()["conventions_used"]["config"]["lalkitab_edition"] == "fixed_aries"


def test_edition_config_and_errors():
    c = TestClient(app)
    a = c.post("/compat/lalkitab_horoscope", json=BODY).json()["data"]
    b = c.post("/compat/lalkitab_horoscope", json={**BODY, "config": {"lalkitab_edition": "lagna_houses"}}).json()["data"]
    assert a["edition"] == "fixed_aries" and b["edition"] == "lagna_houses" and a["planet_house"] != b["planet_house"]
    assert c.post("/compat/lalkitab_horoscope", json={**BODY, "time": None, "config": {"lalkitab_edition": "lagna_houses"}}).status_code == 422
    assert c.post("/compat/lalkitab_horoscope", json={**BODY, "time": None}).status_code == 200
    assert c.post("/compat/lalkitab_remedies/pluto", json=BODY).status_code == 422
    assert c.post("/compat/lalkitab_horoscope", json={**BODY, "config": {"lalkitab_edition": "other"}}).status_code == 422
