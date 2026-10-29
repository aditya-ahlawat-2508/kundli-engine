"""V2 phase 17: solar/month returns, Muntha, Panchavargeeya, Harsha, sahams, Tajika yogas, Mudda dasha."""
from datetime import date, datetime, time

import pytest
from fastapi.testclient import TestClient

from kundli.api import app
from kundli.chart import generate
from kundli.config import EngineConfig
from kundli.data.tables import SEVEN
from kundli.models import BirthInput, Place
from kundli.transits import sid_lon
from kundli.varshaphal import (
    annual_chart,
    harsha_bala,
    mudda_dasha,
    muntha,
    panchavargeeya,
    return_jd,
    sahams,
    tajika_yogas,
)
from kundli.varshaphal.harsha import is_day_chart
from kundli.varshaphal.panchavargeeya import uccha_virupas
from kundli.varshaphal.tables import DEEPTAMSA, HADDA, PANCHAVARGEEYA_MAX, hadda_lord
from kundli.varshaphal.tajika_yogas import aspect_kind

PLACE = Place(name="Delhi", admin1="Delhi", country="IN", lat=28.6139, lon=77.2090, tz="Asia/Kolkata", source="manual")


def natal(cfg: EngineConfig | None = None):
    return generate(BirthInput(name="T", date=date(1990, 5, 5), time=time(10, 30), place=PLACE), cfg or EngineConfig())


@pytest.fixture(scope="module")
def k():
    return natal()


@pytest.fixture(scope="module")
def year(k):
    annual, jd = annual_chart(k, 2026)
    return annual, jd


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDLI_DATA_DIR", str(tmp_path))


# ---- returns ------------------------------------------------------------------------------------------------
def test_solar_return_sun_equals_natal_sun(k):
    natal_sun = next(p.sidereal_lon for p in k.planets if p.name == "Sun")
    cfg = EngineConfig()
    for y in (1991, 2026, 2060):
        assert abs((sid_lon("Sun", return_jd(k, y), cfg) - natal_sun + 180) % 360 - 180) < 1e-7


def test_age_zero_return_is_the_birth_moment(k):
    assert abs(return_jd(k, 1990) - k.birth["jd_ut"]) < 1e-5  # < 1 second


def test_tropical_return_comes_earlier_by_precession(k):
    t = natal(EngineConfig(solar_return_zodiac="tropical"))
    d = return_jd(k, 2026) - return_jd(t, 2026)
    assert 0.3 < d < 0.8  # ~20.4 min per year x 36 years ~ 0.51 day


def test_month_charts_advance_30_degrees(k):
    cfg = EngineConfig()
    natal_sun = next(p.sidereal_lon for p in k.planets if p.name == "Sun")
    jds = [return_jd(k, 2026, m) for m in range(1, 13)]
    assert all(28.5 < b - a < 32.0 for a, b in zip(jds, jds[1:], strict=False))
    for m, jd in enumerate(jds, 1):
        assert abs((sid_lon("Sun", jd, cfg) - (natal_sun + 30 * (m - 1)) + 180) % 360 - 180) < 1e-6
    assert 360 < (return_jd(k, 2027) - jds[0]) < 366 and (return_jd(k, 2027) - jds[11]) > 28
    with pytest.raises(ValueError):
        return_jd(k, 2026, 13)


def test_unknown_birth_time_is_rejected():
    kk = generate(BirthInput(name="T", date=date(1990, 5, 5), time=None, place=PLACE), EngineConfig())
    with pytest.raises(ValueError, match="birth time"):
        annual_chart(kk, 2026)


# ---- muntha -------------------------------------------------------------------------------------------------
def test_muntha(k, year):
    annual, _ = year
    m = muntha(k, annual, 36)
    assert m["sign"] == (k.lagna["sign"] + 36) % 12
    assert m["house_in_annual_chart"] == (m["sign"] - annual.lagna["sign"]) % 12 + 1
    assert m["traditionally_unfavourable"] == (m["house_in_annual_chart"] in (6, 8, 12))
    assert m["lord_house_in_annual_chart"] in range(1, 13)


# ---- tables -------------------------------------------------------------------------------------------------
def test_hadda_table_invariants():
    totals = {p: 0.0 for p in ("Jupiter", "Venus", "Mercury", "Mars", "Saturn")}
    for sign, rows in enumerate(HADDA):
        assert len(rows) == 5 and rows[-1][0] == 30 and [u for u, _ in rows] == sorted(u for u, _ in rows)
        assert {lord for _, lord in rows} == set(totals)  # each of the five exactly once per sign
        prev = 0.0
        for upper, lord in rows:
            totals[lord] += upper - prev
            prev = upper
    assert totals == {"Jupiter": 79, "Venus": 82, "Mercury": 76, "Mars": 66, "Saturn": 57}
    assert sum(totals.values()) == 360
    assert hadda_lord(0, 0.0) == "Jupiter" and hadda_lord(0, 5.99) == "Jupiter" and hadda_lord(0, 6.0) == "Venus"
    assert hadda_lord(11, 29.9) == "Saturn"


def test_orbs_cover_all_planets():
    assert set(DEEPTAMSA) == set(SEVEN)


# ---- panchavargeeya -----------------------------------------------------------------------------------------
def test_uccha_virupas():
    assert uccha_virupas("Sun", 10.0) == pytest.approx(20.0)  # exaltation point
    assert uccha_virupas("Sun", 190.0) == pytest.approx(0.0)  # debilitation point
    assert uccha_virupas("Moon", 3.0 + 30) == pytest.approx(20.0)
    assert uccha_virupas("Sun", 100.0) == pytest.approx(10.0)


def test_panchavargeeya_bounds(year):
    annual, _ = year
    r = panchavargeeya(annual)
    assert r["tables_verified"] is False and set(r["planets"]) == set(SEVEN)
    for row in r["planets"].values():
        c = row["components"]
        for key, mx in PANCHAVARGEEYA_MAX.items():
            assert 0 <= c[key]["virupas"] <= mx
        assert 0 <= c["uccha"]["virupas"] <= 20
        assert row["total_virupas"] == pytest.approx(sum(x["virupas"] for x in c.values()))
        assert row["bala"] == pytest.approx(row["total_virupas"] / 4) and 0 <= row["bala"] <= 20


# ---- harsha -------------------------------------------------------------------------------------------------
def test_harsha_components(year):
    annual, _ = year
    r = harsha_bala(annual)
    assert r["chart_is_day"] == is_day_chart(annual)
    for row in r["planets"].values():
        assert all(row[x] in (0.0, 5.0) for x in ("sthana", "stri_purusha", "uccha_adi", "dina_ratri"))
        assert row["total"] == sum(row[x] for x in ("sthana", "stri_purusha", "uccha_adi", "dina_ratri")) <= 20
    assert r["planets"]["Mercury"]["dina_ratri"] == 5.0
    assert r["planets"]["Moon"]["stri_purusha"] == (5.0 if next(p for p in annual.planets if p.name == "Moon").sign % 2 else 0.0)


# ---- sahams -------------------------------------------------------------------------------------------------
def test_sahams_day_night_formulae(year):
    annual, _ = year
    s = sahams(annual)
    pos = {p.name: p.sidereal_lon for p in annual.planets}
    asc = annual.lagna["longitude"]
    day = is_day_chart(annual)
    punya = (asc + pos["Moon"] - pos["Sun"]) % 360 if day else (asc + pos["Sun"] - pos["Moon"]) % 360
    assert s["sahams"]["punya"]["longitude"] == pytest.approx(punya)
    vidya = (asc + pos["Sun"] - pos["Moon"]) % 360 if day else (asc + pos["Moon"] - pos["Sun"]) % 360
    assert s["sahams"]["vidya"]["longitude"] == pytest.approx(vidya)
    yasha = (asc + pos["Jupiter"] - punya) % 360 if day else (asc + punya - pos["Jupiter"]) % 360
    assert s["sahams"]["yasha"]["longitude"] == pytest.approx(yasha)
    for v in s["sahams"].values():
        assert 0 <= v["longitude"] < 360 and v["sign"] == int(v["longitude"] // 30)


def test_saham_file_rejects_forward_references(tmp_path, monkeypatch):
    from kundli.varshaphal import saham
    bad = tmp_path / "s.yaml"
    bad.write_text("- {id: a, name: A, plus: Moon, minus: later, verify: true}\n- {id: later, name: L, plus: Sun, minus: Moon, verify: true}\n")
    monkeypatch.setattr(saham, "FILE", bad)
    saham.load.cache_clear()
    with pytest.raises(ValueError, match="neither a graha nor an earlier saham"):
        saham.load()
    saham.load.cache_clear()


# ---- tajika yogas -------------------------------------------------------------------------------------------
def test_aspect_kinds():
    assert aspect_kind(0, 0) == "conjunction" and aspect_kind(0, 2) == "friendly" and aspect_kind(0, 4) == "friendly"
    assert aspect_kind(0, 3) == "inimical" and aspect_kind(0, 6) == "inimical" and aspect_kind(0, 1) is None
    assert aspect_kind(0, 5) is None and aspect_kind(0, 7) is None and aspect_kind(0, 11) is None


def test_tajika_yogas_match_an_independent_recomputation(year):
    annual, _ = year
    got = {frozenset((y["faster"], y["slower"])): y for y in tajika_yogas(annual)["yogas"]}
    pl = {p.name: p for p in annual.planets if p.name in SEVEN}
    from itertools import combinations

    from kundli.varshaphal.tables import SPEED_ORDER
    expected = {}
    for a, b in combinations(SEVEN, 2):
        f, s = sorted((a, b), key=SPEED_ORDER.index)
        if aspect_kind(pl[f].sign, pl[s].sign) is None and aspect_kind(pl[s].sign, pl[f].sign) is None:
            continue
        orb = (DEEPTAMSA[f] + DEEPTAMSA[s]) / 2
        delta = pl[s].degree_in_sign - pl[f].degree_in_sign
        if 0 <= delta <= orb:
            expected[frozenset((a, b))] = "ithasala"
        elif -orb <= delta < 0:
            expected[frozenset((a, b))] = "ishrafa"
    assert {k_: v["yoga"] for k_, v in got.items()} == expected
    assert all(abs(y["delta_degrees"]) <= y["orb"] for y in got.values())
    assert tajika_yogas(annual)["implemented"] == ["ithasala", "ishrafa"]


# ---- mudda dasha --------------------------------------------------------------------------------------------
def test_mudda_dasha_compresses_the_cycle(k, year):
    annual, jd = year
    m = mudda_dasha(k, annual, jd, "annual_moon", depth=2)
    assert len(m["periods"]) == 9 and sum(p["days"] for p in m["periods"]) == pytest.approx(360.0)
    assert {p["lord"]: p["days"] for p in m["periods"]} == {"Sun": 18, "Moon": 30, "Mars": 21, "Rahu": 54, "Jupiter": 48,
                                                              "Saturn": 57, "Mercury": 51, "Ketu": 21, "Venus": 60}
    first = m["periods"][0]
    assert first["lord"] == m["start_lord"] and first["balance_days"] + m["closing_remainder"]["days"] == pytest.approx(first["days"])
    assert first["active_from_utc"] == m["year_start_utc"]
    assert all(c["level"] == "antar" for p in m["periods"] for c in p["children"])
    other = mudda_dasha(k, annual, jd, "natal_vimshottari", depth=1)
    assert sum(p["days"] for p in other["periods"]) == pytest.approx(360.0)
    with pytest.raises(ValueError):
        mudda_dasha(k, annual, jd, "nonsense")


# ---- endpoints ----------------------------------------------------------------------------------------------
BODY = {"date": "1990-05-05", "time": "10:30", "lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata", "year": 2026, "month": 3}


@pytest.mark.parametrize("ep", ["varshaphal_year_chart", "varshaphal_month_chart", "varshaphal_details",
                                "varshaphal_planets", "varshaphal_muntha", "varshaphal_mudda_dasha",
                                "varshaphal_panchavargeeya_bala", "varshaphal_harsha_bala", "varshaphal_saham_points",
                                "varshaphal_yoga"])
def test_varshaphal_endpoints(ep):
    r = TestClient(app).post("/compat/" + ep, json=BODY)
    assert r.status_code == 200, r.text
    assert r.json()["data"]


def test_varshaphal_endpoint_edge_cases():
    c = TestClient(app)
    assert c.post("/compat/varshaphal_month_chart", json={**BODY, "month": None}).status_code == 422
    assert c.post("/compat/varshaphal_month_chart", json={**BODY, "month": 13}).status_code == 422
    assert c.post("/compat/varshaphal_muntha", json={**BODY, "year": None}).status_code == 422  # no year, no as_of
    ok = c.post("/compat/varshaphal_muntha", json={**BODY, "year": None, "as_of": "2027-01-01"})
    assert ok.status_code == 200 and ok.json()["data"]["year"] == 2027
    assert c.post("/compat/varshaphal_muntha", json={**BODY, "time": None}).status_code == 422
    a = c.post("/compat/varshaphal_details", json=BODY).json()["data"]["jd_ut"]
    t = c.post("/compat/varshaphal_details", json={**BODY, "config": {"solar_return_zodiac": "tropical"}}).json()["data"]["jd_ut"]
    assert a > t


def test_year_chart_moment_matches_return(k):
    c = TestClient(app)
    d = c.post("/compat/varshaphal_year_chart", json=BODY).json()["data"]
    assert abs(d["jd_ut"] - return_jd(k, 2026)) < 1e-6  # response rounding
    local = datetime.fromisoformat(d["local"])
    assert local.year == 2026 and local.month == 5
