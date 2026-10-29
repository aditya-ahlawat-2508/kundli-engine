"""V2 phase 18: muhurta rulesets, rule evaluation, scoring, scan output and the 18 endpoints."""
from datetime import date, time, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from kundli.api import app
from kundli.chart import generate
from kundli.config import EngineConfig
from kundli.data.tables import NAKSHATRAS, YOGA_NAMES
from kundli.models import BirthInput, Place
from kundli.muhurta import MAX_DAYS, activities, load, scan
from kundli.muhurta.engine import Natal, _score, evaluate_rule
from kundli.muhurta.rules import WEEKDAYS, Rule, tables

DELHI = (28.6139, 77.2090, "Asia/Kolkata")
CFG = EngineConfig()
PLACE = Place(name="Delhi", admin1="Delhi", country="IN", lat=DELHI[0], lon=DELHI[1], tz=DELHI[2], source="manual")
ACTIVITIES = ["account_opening", "agreement_signing", "annaprashan", "bhumi_pujan", "business_start", "gold_purchase",
              "griha_pravesh", "job_joining", "loan_give", "loan_take", "marriage", "mundan", "namkaran",
              "property_purchase", "travel", "upanayana", "vehicle_purchase", "vidyarambh"]


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDLI_DATA_DIR", str(tmp_path))


def ctx(**kw):
    base = {"weekday": "Monday", "tithi": 2, "paksha": "shukla", "nak_index": 3, "nakshatra": "Rohini",
            "nakshatra_class": "dhruva", "yoga": "Priti", "karana": "Bava", "month": "Magha", "adhika": False,
            "sun_sign": "Capricorn", "moon_sign_index": 1, "windows": set(), "combust": {"Venus": False, "Jupiter": False}}
    return {**base, **kw}


# ---- data ---------------------------------------------------------------------------------------------------
def test_eighteen_rulesets_load_with_sources_and_flags():
    assert activities() == ACTIVITIES
    for a in ACTIVITIES:
        rs = load(a)
        assert rs.activity == a and rs.version == "v1" and rs.verify is True and len(rs.sources) >= 2
        assert {"avoid_rahu_kaal", "avoid_yamaganda", "avoid_gulika", "avoid_riktha_tithi", "tarabala"} <= {r.id for r in rs.rules}
        assert all(r.veto != (r.weight > 0) for r in rs.rules)
        assert any(r.weight > 0 for r in rs.rules)


def test_nakshatra_classes_partition_the_27():
    names = [n for ns in tables()["nakshatra_class"].values() for n in ns]
    assert sorted(names) == sorted(NAKSHATRAS)
    assert set(tables()["inauspicious_yogas"]) <= set(YOGA_NAMES) and len(tables()["inauspicious_yogas"]) == 9
    assert sorted(w for ws in tables()["dishashoola"].values() for w in ws) == sorted(WEEKDAYS)  # each weekday once


def test_marriage_uses_the_marriage_nakshatras():
    r = next(x for x in load("marriage").rules if x.id == "marriage_nakshatra")
    assert len(r.values) == 11 and set(r.values) <= set(NAKSHATRAS)


def test_unknown_activity_and_bad_rules():
    with pytest.raises(ValueError, match="unknown muhurta activity"):
        load("nonsense")
    with pytest.raises(ValueError, match="unknown muhurta activity"):
        load("_common")
    with pytest.raises(ValidationError):
        Rule(id="x", kind="weekday_in", values=("Monday",))  # neither weight nor veto
    with pytest.raises(ValidationError):
        Rule(id="x", kind="weekday_in", values=("Monday",), weight=1, veto=True)
    with pytest.raises(ValidationError):
        Rule(id="x", kind="nonsense", weight=1)


def test_ruleset_validation_catches_unknown_names(tmp_path, monkeypatch):
    from kundli.muhurta import rules
    d = tmp_path / "rulesets"
    d.mkdir()
    (tmp_path / "tables.yaml").write_text((rules.DIR / "tables.yaml").read_text())
    (d / "_common.yaml").write_text("version: v1\nsources: [s]\nverify: true\nrules: []\n")
    (d / "bad.yaml").write_text("activity: bad\nversion: v1\nverify: true\nsources: [s]\nrules:\n"
                                "  - {id: w, kind: weekday_in, values: [Moonday], weight: 1}\n")
    monkeypatch.setattr(rules, "DIR", tmp_path)
    rules.load.cache_clear()
    with pytest.raises(ValueError, match="unknown names"):
        rules.load("bad")
    rules.load.cache_clear()


# ---- rule evaluation ----------------------------------------------------------------------------------------
def R(kind, **kw):
    return Rule(id="t", kind=kind, weight=1, **kw)


def test_every_rule_kind():
    c = ctx()
    assert evaluate_rule(R("weekday_in", values=("Monday",)), c, None, None) is True
    assert evaluate_rule(R("weekday_not_in", values=("Monday",)), c, None, None) is False
    assert evaluate_rule(R("tithi_in", values=(2, 3)), c, None, None) is True
    assert evaluate_rule(R("tithi_not_in", values=(2,)), c, None, None) is False
    assert evaluate_rule(R("nakshatra_in", values=("Rohini",)), c, None, None) is True
    assert evaluate_rule(R("nakshatra_not_in", values=("Rohini",)), c, None, None) is False
    assert evaluate_rule(R("nakshatra_class_in", classes=("dhruva",)), c, None, None) is True
    assert evaluate_rule(R("nakshatra_class_not_in", classes=("dhruva",)), c, None, None) is False
    assert evaluate_rule(R("yoga_not_in", values=("Vaidhriti",)), c, None, None) is True
    assert evaluate_rule(R("karana_not_in", values=("Bava",)), c, None, None) is False
    assert evaluate_rule(R("month_in", values=("Magha",)), c, None, None) is True
    assert evaluate_rule(R("month_not_in", values=("Magha",)), c, None, None) is False
    assert evaluate_rule(R("adhika_not"), c, None, None) is True
    assert evaluate_rule(R("sun_sign_not_in", values=("Capricorn",)), c, None, None) is False
    assert evaluate_rule(R("not_combust", planets=("Venus", "Jupiter")), c, None, None) is True
    assert evaluate_rule(R("not_combust", planets=("Venus",)), ctx(combust={"Venus": True, "Jupiter": False}), None, None) is False
    assert evaluate_rule(R("not_in_window", windows=("rahu_kaal",)), ctx(windows={"rahu_kaal"}), None, None) is False
    assert evaluate_rule(R("in_window", windows=("abhijit_muhurta",)), ctx(windows={"abhijit_muhurta"}), None, None) is True
    assert evaluate_rule(R("paksha_in", values=("krishna",)), c, None, None) is False


def test_personal_and_direction_rules():
    nat = Natal(nakshatra=0, moon_sign=0)
    good = ctx(nak_index=1, moon_sign_index=2)  # count 2 -> ok; Moon 3rd from natal Moon -> ok
    assert evaluate_rule(R("tarabala_ok"), good, nat, None) is True and evaluate_rule(R("chandrabala_ok"), good, nat, None) is True
    bad = ctx(nak_index=2, moon_sign_index=7)  # count 3 = Vipat; Moon 8th from natal Moon
    assert evaluate_rule(R("tarabala_ok"), bad, nat, None) is False and evaluate_rule(R("chandrabala_ok"), bad, nat, None) is False
    assert evaluate_rule(R("tarabala_ok"), bad, None, None) is None and evaluate_rule(R("chandrabala_ok"), bad, None, None) is None
    assert evaluate_rule(R("dishashoola_ok"), ctx(weekday="Monday"), None, "east") is False
    assert evaluate_rule(R("dishashoola_ok"), ctx(weekday="Monday"), None, "north") is True
    assert evaluate_rule(R("dishashoola_ok"), ctx(), None, None) is None
    with pytest.raises(ValueError):
        evaluate_rule(R("dishashoola_ok"), ctx(), None, "up")


def test_tarabala_bad_counts_are_3_5_7():
    nat = Natal(nakshatra=10, moon_sign=0)
    bad = {n for n in range(27) if evaluate_rule(R("tarabala_ok"), ctx(nak_index=n), nat, None) is False}
    assert bad == {(10 + c - 1) % 27 for c in (3, 5, 7, 12, 14, 16, 21, 23, 25)}  # counts whose remainder mod 9 is 3, 5, 7


def test_chandrabala_good_houses():
    nat = Natal(nakshatra=0, moon_sign=4)
    ok = {h for h in range(1, 13)
          if evaluate_rule(R("chandrabala_ok"), ctx(moon_sign_index=(4 + h - 1) % 12), nat, None)}
    assert ok == {1, 3, 6, 7, 10, 11}


def test_score_arithmetic_and_vetoes():
    rs = load("vehicle_purchase")
    perfect = ctx(weekday="Monday", nakshatra="Ashwini", nak_index=0, nakshatra_class="kshipra",
                  windows={"abhijit_muhurta"})
    res = _score(rs, perfect, Natal(0, 1), None)
    assert res["score"] == 100.0 and not res["failed"] and not res["vetoed"]
    weekday_fail = _score(rs, ctx(weekday="Sunday", nakshatra_class="kshipra", windows={"abhijit_muhurta"}), Natal(0, 1), None)
    total = sum(r.weight for r in rs.rules if r.weight > 0)
    assert weekday_fail["score"] == pytest.approx(round(100 * (total - 3) / total, 1)) and weekday_fail["failed"] == ["weekday"]
    veto = _score(rs, ctx(windows={"rahu_kaal"}), None, None)
    assert veto["vetoed"] and veto["score"] is None and veto["vetoed_by"] == ["avoid_rahu_kaal"]
    noshow = _score(rs, ctx(), None, None)
    assert {"tarabala", "chandrabala"} <= set(noshow["not_evaluated"])


# ---- scan ---------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def week():
    natal = generate(BirthInput(name="N", date=date(1990, 5, 5), time=time(10, 30), place=PLACE), CFG)
    return scan("griha_pravesh", date(2025, 2, 3), date(2025, 2, 9), *DELHI, CFG, natal), natal


def test_scan_windows_cover_each_vedha_day_contiguously(week):
    out, _ = week
    assert [d["date"] for d in out["days"]] == [f"2025-02-0{n}" for n in range(3, 10)]
    for d in out["days"]:
        ws = d["windows"]
        assert ws and all(abs(a["end_jd"] - b["start_jd"]) < 1e-7 for a, b in zip(ws, ws[1:], strict=False))
        assert 0.99 < ws[-1]["end_jd"] - ws[0]["start_jd"] < 1.01  # sunrise to next sunrise


def test_scan_windows_are_explainable(week):
    out, _ = week
    rule_ids = {r.id for r in load("griha_pravesh").rules}
    for d in out["days"]:
        for w in d["windows"]:
            assert set(w["passed"]) | set(w["failed"]) | set(w["not_evaluated"]) == rule_ids
            assert w["vetoed"] == bool(w["vetoed_by"]) and (w["score"] is None) == w["vetoed"]
            assert w["score"] is None or 0 <= w["score"] <= 100
            assert not w["not_evaluated"]  # natal chart supplied: personal checks ran
    assert out["personal_checks"] and out["rules_verified"] is False and out["sources"]


def test_rahu_kaal_is_always_vetoed_and_good_dates_follow_the_threshold(week):
    out, _ = week
    for d in out["days"]:
        for w in d["windows"]:
            if "avoid_rahu_kaal" in w["failed"]:
                assert w["vetoed"] and "avoid_rahu_kaal" in w["vetoed_by"]
    assert out["good_dates"] == [d["date"] for d in out["days"] if d["best_score"] is not None and d["best_score"] >= 60]


def test_without_a_natal_chart_personal_checks_are_not_evaluated():
    out = scan("business_start", date(2025, 2, 3), date(2025, 2, 4), *DELHI, CFG)
    assert not out["personal_checks"]
    assert all({"tarabala", "chandrabala"} <= set(w["not_evaluated"]) for d in out["days"] for w in d["windows"])


def test_scan_is_deterministic():
    a = scan("namkaran", date(2025, 2, 3), date(2025, 2, 5), *DELHI, CFG)
    assert a == scan("namkaran", date(2025, 2, 3), date(2025, 2, 5), *DELHI, CFG)


def test_travel_direction_vetoes_the_dishashoola_weekday():
    mon = scan("travel", date(2025, 2, 3), date(2025, 2, 3), *DELHI, CFG, direction="east")["days"][0]  # 2025-02-03 is a Monday
    assert mon["weekday"] == "Monday" and mon["best_score"] is None
    assert all("dishashoola" in w["vetoed_by"] for w in mon["windows"] if "dishashoola" in w["failed"])
    north = scan("travel", date(2025, 2, 3), date(2025, 2, 3), *DELHI, CFG, direction="north")["days"][0]
    assert not any("dishashoola" in w["failed"] for w in north["windows"])


def test_scan_range_checks():
    with pytest.raises(ValueError, match="before start"):
        scan("travel", date(2025, 2, 5), date(2025, 2, 4), *DELHI, CFG)
    with pytest.raises(ValueError, match="at most"):
        scan("travel", date(2025, 1, 1), date(2025, 1, 1) + timedelta(days=MAX_DAYS), *DELHI, CFG)
    with pytest.raises(ValueError):
        scan("nonsense", date(2025, 1, 1), date(2025, 1, 2), *DELHI, CFG)


def test_kharmas_and_combustion_rules_fire_in_season():
    # 2025-01-05: Sun in Sagittarius (Kharmas) -> every window of a Kharmas-sensitive activity is vetoed by it
    out = scan("mundan", date(2025, 1, 5), date(2025, 1, 5), *DELHI, CFG)
    assert all("avoid_kharmas" in w["failed"] for w in out["days"][0]["windows"])
    out2 = scan("mundan", date(2025, 2, 5), date(2025, 2, 5), *DELHI, CFG)  # Sun in Capricorn/Aquarius
    assert not any("avoid_kharmas" in w["failed"] for w in out2["days"][0]["windows"])


# ---- endpoints ----------------------------------------------------------------------------------------------
BODY = {"date": "2025-02-03", "end_date": "2025-02-05", "lat": DELHI[0], "lon": DELHI[1], "tz": DELHI[2]}


@pytest.mark.parametrize("ep", ACTIVITIES)
def test_muhurta_endpoints(ep):
    r = TestClient(app).post("/compat/" + ep, json=BODY)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["activity"] == ep and len(d["days"]) == 3 and "conventions_used" in r.json()


def test_muhurta_endpoint_options_and_errors():
    c = TestClient(app)
    natal = {"date": "1990-05-05", "time": "10:30", "lat": DELHI[0], "lon": DELHI[1], "tz": DELHI[2]}
    d = c.post("/compat/marriage", json={**BODY, "natal": natal}).json()["data"]
    assert d["personal_checks"] is True
    assert c.post("/compat/travel", json={**BODY, "direction": "east"}).json()["data"]["direction"] == "east"
    assert c.post("/compat/travel", json={**BODY, "direction": "up"}).status_code == 422
    assert c.post("/compat/marriage", json={**BODY, "end_date": "2025-01-01"}).status_code == 422
    assert c.post("/compat/marriage", json={**BODY, "end_date": "2025-12-31"}).status_code == 422
    assert c.post("/compat/marriage", json={**BODY, "natal": {**natal, "date": "bad"}}).status_code == 422
    default = c.post("/compat/marriage", json={k_: v for k_, v in BODY.items() if k_ != "end_date"}).json()["data"]
    assert len(default["days"]) == 30
