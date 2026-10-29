"""V2 phase 16: match making (Ashtakoota, Dashakoota, obstructions, percentage) and the doshas package."""
from datetime import UTC, date, datetime, time
from itertools import product

import pytest
from fastapi.testclient import TestClient

from kundli.api import app
from kundli.chart import generate
from kundli.config import EngineConfig
from kundli.data.tables import GANA_BY_NAK, NADI_CYCLE, NAKSHATRAS, SIGN_LORDS, VARNA_BY_SIGN, YONI_BY_NAK
from kundli.doshas import (
    kaal_sarpa,
    manglik,
    pitra_dosha,
    sadhesati_events,
    sadhesati_periods,
    sadhesati_status,
    simple_manglik,
)
from kundli.match import ashtakoota, dashakoota, match, obstructions, percentage, verdict
from kundli.match.ashtakoota import MAX, count_from
from kundli.match.dashakoota import rajju_of, vedha_pair
from kundli.match.obstructions import bhakoot_dosha, nadi_dosha
from kundli.match.person import Person
from kundli.match.tables import load
from kundli.models import BirthInput, Place
from kundli.transits import sid_lon

PLACE = Place(name="Delhi", admin1="Delhi", country="IN", lat=28.6139, lon=77.2090, tz="Asia/Kolkata", source="manual")
MUMBAI = Place(name="Mumbai", admin1="MH", country="IN", lat=19.076, lon=72.8777, tz="Asia/Kolkata", source="manual")


def person(sign: int, nak: int, pada: int = 1, vashya: str = "Manav", name: str = "P") -> Person:
    return Person(name=name, sign=sign, nakshatra=nak, pada=pada, sign_lord=SIGN_LORDS[sign], varna=VARNA_BY_SIGN[sign],
                  vashya=vashya, yoni=YONI_BY_NAK[nak], gana=GANA_BY_NAK[nak], nadi=NADI_CYCLE[nak % 6])


@pytest.fixture(scope="module")
def boy():
    return generate(BirthInput(name="B", date=date(1990, 5, 5), time=time(10, 30), place=PLACE), EngineConfig())


@pytest.fixture(scope="module")
def girl():
    return generate(BirthInput(name="G", date=date(1992, 11, 20), time=time(6, 15), place=MUMBAI), EngineConfig())


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDLI_DATA_DIR", str(tmp_path))


# ---- tables -------------------------------------------------------------------------------------------------
def test_tables_are_flagged_and_structurally_sound():
    t = load()
    assert t["verify"] is True and t["source"]
    assert sorted(n for ns in t["rajju"].values() for n in ns) == sorted(NAKSHATRAS)
    assert sorted(n for g in t["vedha"] for n in g) == sorted(NAKSHATRAS)


def test_yoni_matrix_is_symmetric_with_exactly_the_seven_enemy_pairs():
    m = load()["yoni_matrix"]
    o = m["order"]
    at = lambda a, b: m["rows"][a][o.index(b)]
    assert all(at(a, b) == at(b, a) for a in o for b in o)
    assert all(at(a, a) == 4 for a in o)
    zeros = {frozenset((a, b)) for a in o for b in o if a != b and at(a, b) == 0}
    assert zeros == {frozenset(p) for p in [("Ashwa", "Mahisha"), ("Gaja", "Simha"), ("Mesha", "Vanar"),
                                            ("Sarpa", "Nakul"), ("Shwan", "Mriga"), ("Marjar", "Mushak"),
                                            ("Gau", "Vyaghra")]}


# ---- Ashtakoota --------------------------------------------------------------------------------------------
def test_count_from_is_inclusive_and_cyclic():
    assert count_from(0, 0, 27) == 1 and count_from(26, 0, 27) == 2 and count_from(0, 26, 27) == 27


def test_identical_partners_score_28():
    p = person(1, 3)  # same sign, same nakshatra
    r = ashtakoota(p, p)["kootas"]
    assert [r[k]["points"] for k in MAX] == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 0.0]  # nadi is the only loss
    assert ashtakoota(p, p)["total"] == 28.0


def test_varna_is_directional():
    vipra, shudra = person(3, 8), person(2, 4)  # Cancer = Vipra, Gemini = Shudra
    assert ashtakoota(vipra, shudra)["kootas"]["varna"]["points"] == 1.0
    assert ashtakoota(shudra, vipra)["kootas"]["varna"]["points"] == 0.0


def test_tara_scores_per_direction():
    boy_, girl_ = person(0, 0), person(0, 3)  # Ashwini boy, Rohini girl
    r = ashtakoota(boy_, girl_)["kootas"]["tara"]
    # girl->boy count 25 (remainder 7 = Vadha, bad); boy->girl count 4 (remainder 4, good)
    assert (r["girl_to_boy_remainder"], r["boy_to_girl_remainder"], r["points"]) == (7, 4, 1.5)
    both_good = ashtakoota(person(0, 0), person(0, 1))["kootas"]["tara"]  # counts 2 and 27 -> remainders 0 and 2
    assert both_good["points"] == 3.0
    # the two inclusive counts always sum to 29, so both can never be 3/5/7 mod 9: Tara is always 1.5 or 3
    assert {ashtakoota(person(0, a), person(0, b))["kootas"]["tara"]["points"] for a in range(27) for b in range(27)} == {1.5, 3.0}


def test_bhakoot_distances():
    for d, expected in {1: 7, 2: 0, 3: 7, 4: 7, 5: 0, 6: 0, 7: 7, 8: 0, 9: 0, 10: 7, 11: 7, 12: 0}.items():
        r = ashtakoota(person(0, 0), person((d - 1) % 12, 5))["kootas"]["bhakoot"]
        assert r["points"] == expected and r["sign_distance"] == d


def test_nadi_all_or_nothing():
    same = ashtakoota(person(0, 0), person(1, 5))["kootas"]["nadi"]  # nakshatra 0 and 5: both Adi
    diff = ashtakoota(person(0, 0), person(1, 1))["kootas"]["nadi"]
    assert (same["points"], diff["points"]) == (0.0, 8.0)


def test_graha_maitri_table_and_same_lord():
    assert ashtakoota(person(0, 0), person(7, 5))["kootas"]["graha_maitri"]["points"] == 5.0  # Mars and Mars
    pts = {ashtakoota(person(a, 0), person(b, 5))["kootas"]["graha_maitri"]["points"] for a in range(12) for b in range(12)}
    assert pts <= {5.0, 4.0, 3.0, 1.0, 0.5, 0.0}


def test_every_koota_within_its_maximum_and_36_is_reachable():
    best = 0.0
    for sa, na, sb, nb in product(range(0, 12, 3), range(0, 27, 2), range(0, 12, 3), range(1, 27, 2)):
        ak = ashtakoota(person(sa, na), person(sb, nb))
        assert all(0 <= v["points"] <= v["max"] for v in ak["kootas"].values())
        assert ak["total"] == sum(v["points"] for v in ak["kootas"].values()) <= 36
        best = max(best, ak["total"])
    assert best >= 30


def test_verdict_bands_and_percentage():
    assert [verdict(x) for x in (36, 33, 32.5, 25, 18, 17.5, 0)] == [
        "excellent", "excellent", "good", "good", "average", "not_recommended", "not_recommended"]
    assert percentage(18) == 50.0 and percentage(36) == 100.0


# ---- Dashakoota --------------------------------------------------------------------------------------------
def test_rajju_and_vedha_rules():
    assert rajju_of("Ashwini") == "Pada" and rajju_of("Chitra") == "Siras" and rajju_of("Hasta") == "Kantha"
    assert vedha_pair("Ashwini", "Jyeshtha") and vedha_pair("Jyeshtha", "Ashwini")
    assert vedha_pair("Mrigashira", "Dhanishta") and vedha_pair("Chitra", "Dhanishta") and not vedha_pair("Ashwini", "Ashwini")
    d = dashakoota(person(0, 0), person(7, 17))  # Ashwini with Jyeshtha: vedha and the same rajju group (Pada)
    assert not d["poruthams"]["vedha"]["compatible"] and not d["poruthams"]["rajju"]["compatible"]


def test_dashakoota_counts_and_rasi_is_not_implemented():
    d = dashakoota(person(0, 0), person(0, 3))  # girl Ashwini -> boy... count_from(girl=3, boy=0) = 25
    assert d["poruthams"]["mahendra"]["compatible"] and d["poruthams"]["mahendra"]["count"] == 25
    assert d["poruthams"]["stree_deergha"]["compatible"]
    assert d["poruthams"]["rasi"]["status"] == "not_implemented" and d["max"] == 9
    assert d["total"] == sum(p["points"] for p in d["poruthams"].values()) <= 9


# ---- obstructions ------------------------------------------------------------------------------------------
def test_nadi_dosha_and_cancellations():
    assert nadi_dosha(person(0, 0), person(0, 1))["present"] is False
    plain = nadi_dosha(person(0, 0), person(5, 5))
    assert plain["present"] and plain["effective"]
    same_sign = nadi_dosha(person(0, 0), person(0, 5))  # same sign, different nakshatra, same nadi
    assert same_sign["present"] and same_sign["cancelled_by"] == ["same_sign_different_nakshatra"] and not same_sign["effective"]
    same_star = nadi_dosha(person(0, 0, pada=1), person(0, 0, pada=2))
    assert same_star["cancelled_by"] == ["same_nakshatra_different_pada"]


def test_bhakoot_dosha_cancellation_by_friendly_lords():
    r = bhakoot_dosha(person(0, 0), person(5, 5))  # Aries to Virgo: distance 6, lords Mars/Mercury (enemy) -> effective
    assert r["present"] and r["effective"]
    r2 = bhakoot_dosha(person(4, 0), person(0, 5))  # Leo(Sun) to Aries(Mars): distance 9, Sun and Mars are mutual friends
    assert r2["present"] and r2["cancelled_by"] and not r2["effective"]


# ---- full match + endpoints ---------------------------------------------------------------------------------
def test_full_match(boy, girl):
    m = match(boy, girl)
    assert set(m) >= {"ashtakoota", "dashakoota", "obstructions", "percentage", "verdict"}
    assert m["percentage"] == percentage(m["ashtakoota"]["total"])
    assert m["ashtakoota"]["tables_verified"] is False
    ob = obstructions(boy, girl, *[__import__("kundli.match", fromlist=["person_from"]).person_from(x) for x in (boy, girl)])
    assert ob["manglik"]["obstruction"] in (True, False)


def test_match_endpoints():
    c = TestClient(app)
    b = {"name": "B", "date": "1990-05-05", "time": "10:30", "lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata"}
    g = {"name": "G", "date": "1992-11-20", "time": "06:15", "lat": 19.076, "lon": 72.8777, "tz": "Asia/Kolkata"}
    names = ["match_birth_details", "match_astro_details", "match_planet_details", "match_ashtakoot_points",
             "match_ashtakoot_report", "match_dashakoot_points", "match_obstructions", "match_percentage",
             "match_manglik_report", "match_making_report", "match_making_detailed_report"]
    for ep in names:
        r = c.post("/compat/" + ep, json={"boy": b, "girl": g})
        assert r.status_code == 200, (ep, r.text)
        assert "conventions_used" in r.json()
    pts = c.post("/compat/match_ashtakoot_points", json={"boy": b, "girl": g}).json()["data"]
    pct = c.post("/compat/match_percentage", json={"boy": b, "girl": g}).json()["data"]
    assert pct["percentage"] == round(pts["total"] / 36 * 100, 2)
    full = c.post("/compat/match_making_report", json={"boy": b, "girl": g}).json()["data"]["content"]
    assert full["verdict"]["status"] == "content_missing" and set(full["kootas"]) == set(pts["kootas"])
    assert c.post("/compat/match_percentage", json={"boy": b, "girl": {**g, "date": "bad"}}).status_code == 422
    assert c.post("/compat/match_percentage", json={"boy": b, "girl": g, "config": {"ephemeris_path": "/x"}}).status_code == 422


# ---- doshas ------------------------------------------------------------------------------------------------
def test_manglik_rule_variants_are_nested(boy, girl):
    for k in (boy, girl):
        res = {}
        for variant in ("lagna_only", "lagna_moon", "lagna_moon_venus"):
            kk = generate(BirthInput(name="x", date=date.fromisoformat(k.birth["local"][:10]), time=time.fromisoformat(k.birth["local"][11:19]),
                                     place=PLACE if k is boy else MUMBAI), EngineConfig(manglik_rules=variant))
            res[variant] = manglik(kk)
            assert 0 <= res[variant]["intensity_percent"] <= 100 and set(res[variant]["references"]) <= {"lagna", "moon", "venus"}
        assert set(res["lagna_only"]["references"]) == {"lagna"}
        assert set(res["lagna_moon"]["references"]) == {"lagna", "moon"}
        if res["lagna_only"]["is_manglik"]:
            assert res["lagna_moon_venus"]["is_manglik"]
    assert simple_manglik(boy)["is_manglik"] in (True, False)


def test_kalsarpa_and_pitra_shapes(boy):
    ks = kaal_sarpa(boy)
    assert {"present", "full", "partial", "direction", "type"} <= set(ks)
    p = pitra_dosha(boy)
    assert p["school_dependent"] is True and set(p["rules_evaluated"]) <= {"pitru_sun_node", "pitru_ninth"}
    assert p["present"] == bool(p["indicators"])


def test_sadhesati_periods_are_consistent(boy):
    periods = sadhesati_periods(boy, 90)
    moon = next(p.sign for p in boy.planets if p.name == "Moon")
    cfg = EngineConfig()
    iso = lambda s: datetime.fromisoformat(s)
    assert all(iso(a["end_utc"]) <= iso(b["start_utc"]) for a, b in zip(periods, periods[1:], strict=False))
    from kundli.timeutil import julian_day
    for p in periods:
        mid = iso(p["start_utc"]) + (iso(p["end_utc"]) - iso(p["start_utc"])) / 2
        rel = (int(sid_lon("Saturn", julian_day(mid)[1], cfg) // 30) - moon) % 12 + 1
        assert {12: "sade_sati_rising", 1: "sade_sati_peak", 2: "sade_sati_setting", 4: "dhaiya_kantaka",
                8: "dhaiya_ashtama"}[rel] == p["phase"]
    groups = {p["group"] for p in periods if "group" in p}
    assert 2 <= len(groups) <= 4  # one cycle every ~29.5 years over 90 years
    assert {e["type"] for e in sadhesati_events(boy)} >= {"PEAK_START"}


def test_sadhesati_status_matches_period_and_needs_aware_time(boy):
    when = datetime(2026, 10, 10, tzinfo=UTC)
    st = sadhesati_status(boy, when)
    assert st["phase"] == "dhaiya_ashtama" and st["period"]["phase"] == st["phase"]
    assert st["period"]["start_utc"] <= st["as_of"] < st["period"]["end_utc"]
    with pytest.raises(ValueError):
        sadhesati_status(boy, datetime(2026, 10, 10))
    quiet = sadhesati_status(boy, datetime(2012, 3, 1, tzinfo=UTC))
    assert quiet["active"] in (True, False) and (quiet["period"] is None) == (quiet["phase"] is None)


def test_dosha_endpoints():
    c = TestClient(app)
    b = {"date": "1990-05-05", "time": "10:30", "lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata",
         "as_of": "2026-10-10T00:00:00+00:00"}
    for ep in ("simple_manglik", "manglik", "kalsarpa_details", "sadhesati_current_status", "sadhesati_life_details",
               "pitra_dosha_report"):
        r = c.post("/compat/" + ep, json=b)
        assert r.status_code == 200, (ep, r.text)
    assert c.post("/compat/sadhesati_current_status", json={**b, "as_of": None}).status_code == 422
    unknown = c.post("/compat/manglik", json={**b, "time": None})
    assert unknown.status_code == 422
