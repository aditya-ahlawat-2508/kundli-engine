"""V2 phase 15: KP 249-division table, significators, KP chart and endpoints."""
from datetime import date, time

import pytest
from fastapi.testclient import TestClient

from kundli.api import app
from kundli.chart import generate
from kundli.config import EngineConfig
from kundli.kp import house_of, kp_chart, kp_lords, kp_table, significators
from kundli.models import BirthInput, Place

PLACE = Place(name="Delhi", admin1="Delhi", country="IN", lat=28.6139, lon=77.2090, tz="Asia/Kolkata", source="manual")
BODY = {"date": "1990-05-05", "time": "10:30", "lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"}


@pytest.fixture(scope="module")
def k():
    return generate(BirthInput(name="T", date=date(1990, 5, 5), time=time(10, 30), place=PLACE), EngineConfig())


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDLI_DATA_DIR", str(tmp_path))


def test_table_has_the_classical_249_divisions():
    t = kp_table()
    assert len(t) == 249
    assert t[0]["start"] == 0.0 and t[-1]["end"] == pytest.approx(360.0)
    assert all(a["end"] == pytest.approx(b["start"]) for a, b in zip(t, t[1:], strict=False))
    assert all(int(r["start"] // 30) == int((r["end"] - 1e-9) // 30) for r in t)  # none crosses a sign boundary
    first = t[0]
    assert (first["star_lord"], first["sub_lord"]) == ("Ketu", "Ketu") and first["end"] == pytest.approx(7 / 9)  # 0deg46'40"


def test_table_agrees_with_the_lord_function():
    for r in kp_table():
        mid = (r["start"] + r["end"]) / 2
        star, sub, _ = kp_lords(mid)
        assert (star, sub) == (r["star_lord"], r["sub_lord"])


def test_house_of_handles_wraparound():
    cusps = [(350.0 + 30 * i) % 360 for i in range(12)]  # cusp 1 at 350 deg, houses of 30 deg
    assert house_of(355.0, cusps) == 1 and house_of(10.0, cusps) == 1 and house_of(20.0, cusps) == 2
    assert house_of(349.9, cusps) == 12


def test_significator_ordering_on_a_hand_built_chart():
    cusp_lons = [i * 30.0 for i in range(12)]  # house n = sign n
    cusp_lords = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Saturn",
                  "Jupiter"]
    lon = {"Sun": 5.0, "Moon": 35.0, "Mars": 65.0, "Mercury": 95.0, "Jupiter": 125.0, "Venus": 155.0, "Saturn": 185.0,
           "Rahu": 215.0, "Ketu": 245.0}
    star = {p: "Sun" for p in lon}
    star.update({"Moon": "Mars", "Mars": "Moon"})
    s = significators(lon, star, cusp_lons, cusp_lords)
    h1 = s["house"][1]  # occupied by Sun (house 1), owner Mars
    assert h1["occupants"] == ["Sun"] and h1["owner"] == "Mars"
    assert h1["levels"]["A_in_star_of_occupants"] == [p for p in lon if star[p] == "Sun"]
    assert h1["levels"]["C_in_star_of_owner"] == ["Moon"]  # Moon is the only planet in Mars's star
    assert h1["planets"][-1] == "Mars"  # owner comes last unless already listed; here Mars is not in A, B, C
    p = s["planet"]["Moon"]  # Moon in house 2, star lord Mars in house 3, Mars owns 1 and 8, Moon owns 4
    assert p["house"] == 2 and p["levels"]["1_star_lord_occupies"] == [3]
    assert p["levels"]["3_star_lord_owns"] == [1, 8] and p["levels"]["4_owns"] == [4]
    assert p["houses"] == [3, 2, 1, 8, 4]  # strongest first
    assert p["houses_sorted"] == [1, 2, 3, 4, 8]


def test_kp_chart_is_consistent(k):
    c = kp_chart(k)
    assert len(c["cusps"]) == 12 and set(c["planets"]) == {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                                                           "Saturn", "Rahu", "Ketu"}
    lons = [x["longitude"] for x in c["cusps"]]
    for p, row in c["planets"].items():
        assert row["house"] == house_of(row["longitude"], lons) and 1 <= row["house"] <= 12
        assert c["significators"]["planet"][p]["house"] == row["house"]
    for h, s in c["significators"]["house"].items():
        assert s["owner"] == c["cusps"][h - 1]["sign_lord"] and s["owner"] in s["planets"]
    assert k.kp["significators"] == c["significators"] and k.kp["cusps"] == c["cusps"]


def test_kp_requires_birth_time():
    kk = generate(BirthInput(name="T", date=date(1990, 5, 5), time=None, place=PLACE), EngineConfig())
    assert "cusps" not in (kk.kp or {})
    with pytest.raises(ValueError):
        kp_chart(kk)


@pytest.mark.parametrize("ep", ["kp_planets", "kp_house_cusps", "kp_birth_chart", "kp_house_significator",
                                "kp_planet_significator"])
def test_kp_endpoints(ep):
    r = TestClient(app).post("/compat/" + ep, json=BODY)
    assert r.status_code == 200, r.text
    assert r.json()["data"]


def test_kp_ayanamsa_convention_changes_longitudes():
    c = TestClient(app)
    a = c.post("/compat/kp_planets", json=BODY).json()["data"]["Sun"]["longitude"]
    b = c.post("/compat/kp_planets", json={**BODY, "config": {"kp_ayanamsa": "kp"}}).json()["data"]["Sun"]["longitude"]
    assert 0.0 < abs(a - b) < 0.5  # Lahiri vs Krishnamurti differ by a few arcminutes
