"""V2 phase 12: exact element spans, rise/set conventions, hora, choghadiya, inauspicious periods, Tamil calendar,
festivals and the Panchang compat endpoints."""
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from kundli.api import app
from kundli.config import EngineConfig
from kundli.panchang.choghadiya import choghadiya_table
from kundli.panchang.day import day_panchang, sunrise_jd
from kundli.panchang.festivals import festival_dates, festivals_on, load_rules
from kundli.panchang.hora import hora_table
from kundli.panchang.inauspicious import inauspicious_periods
from kundli.panchang.spans import ELEMENTS, _index, element_spans, sun_moon
from kundli.panchang.sun_moon_times import day_times, rise_args, sun_day
from kundli.panchang.tamil import tamil_calendar
from kundli.timeutil import julian_day

DELHI = (28.6139, 77.2090, "Asia/Kolkata")
CFG = EngineConfig()
JD = julian_day(datetime(2025, 10, 20, 6, 30, tzinfo=UTC))[1]  # 2025-10-20 12:00 IST


@pytest.fixture(scope="module")
def sun():
    return sun_day(date(2025, 10, 20), *DELHI, **rise_args(CFG))


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDLI_DATA_DIR", str(tmp_path))


@pytest.mark.parametrize("element", list(ELEMENTS))
def test_span_boundaries_are_exact(element):
    spans = element_spans(JD, DELHI[2])
    sp = spans[element]
    assert sp["start_jd"] < JD < sp["end_jd"]
    angle, unit, n = ELEMENTS[element]
    eps = 1e-6  # ~0.09 s
    assert _index(element, sp["end_jd"] - eps, "lahiri", 4) != _index(element, sp["end_jd"] + eps, "lahiri", 4)
    assert _index(element, sp["start_jd"] - eps, "lahiri", 4) != _index(element, sp["start_jd"] + eps, "lahiri", 4)
    a = angle(*sun_moon(sp["end_jd"], "lahiri", 4))
    r = a % unit
    assert min(r, unit - r) < 1e-5  # the angle sits on a unit boundary at the end instant


def test_next_element_starts_at_end():
    sp = element_spans(JD, DELHI[2])["tithi"]
    nxt = element_spans(sp["end_jd"] + 1e-4, DELHI[2])["tithi"]
    assert nxt["name"] == sp["next"]["name"] and abs(nxt["start_jd"] - sp["end_jd"]) < 1e-6


def test_known_tithi_end_delhi_2025_10_20():
    sp = element_spans(JD, DELHI[2])["tithi"]
    assert sp["name"] == "Chaturdashi" and sp["next"]["name"] == "Amavasya"
    end = datetime.fromisoformat(sp["end_local"])
    assert (end.hour, end.minute) in {(15, 44), (15, 45), (15, 46)}  # published almanacs: 15:44


def test_rise_set_definition_is_a_convention():
    upper = day_times(date(2025, 10, 20), *DELHI, CFG)
    centre = day_times(date(2025, 10, 20), *DELHI, EngineConfig(sunrise_definition="center_no_refraction"))
    assert centre["sunrise"] > upper["sunrise"] and centre["sunset"] < upper["sunset"]
    assert 1 < (datetime.fromisoformat(centre["sunrise"]) - datetime.fromisoformat(upper["sunrise"])) / timedelta(minutes=1) < 8
    assert upper["moonrise"] and upper["moonset"]
    high = day_times(date(2025, 10, 20), *DELHI, EngineConfig(observer_altitude_m=2000.0))
    # swisseph uses the altitude only to estimate refraction (no horizon dip), so the effect is small
    assert high["sunset"] != upper["sunset"]
    assert abs((datetime.fromisoformat(high["sunset"]) - datetime.fromisoformat(upper["sunset"])).total_seconds()) < 120


def test_hora_table(sun):
    rows = hora_table(sun, 1, DELHI[2])  # Monday
    assert len(rows) == 24 and rows[0]["lord"] == "Moon" and rows[12]["period"] == "night"
    assert all(abs(a["end_jd"] - b["start_jd"]) < 1e-9 for a, b in zip(rows, rows[1:], strict=False))
    assert rows[-1]["end_jd"] == pytest.approx(sun["next_sunrise"])
    assert [r["lord"] for r in rows[:7]] == ["Moon", "Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury"]


def test_choghadiya_tables(sun):
    t = choghadiya_table(sun, 1, DELHI[2])
    assert [len(t["day"]), len(t["night"])] == [8, 8]
    assert t["day"][0]["name"] == "Amrit"
    sunday_night = choghadiya_table(sun, 0, DELHI[2])["night"]
    assert [r["name"] for r in sunday_night][:8] == ["Shubh", "Amrit", "Chal", "Rog", "Kaal", "Labh", "Udveg", "Shubh"]
    assert t["night"][-1]["end_jd"] == pytest.approx(sun["next_sunrise"])


def test_inauspicious_periods(sun):
    p = inauspicious_periods(sun, 1, DELHI[2])  # Monday: rahu 2nd part, yamaganda 4th, gulika 6th
    eighth = (sun["sunset"] - sun["sunrise"]) / 8
    assert p["rahu_kaal"]["start_jd"] == pytest.approx(sun["sunrise"] + eighth)
    assert p["yamaganda"]["start_jd"] == pytest.approx(sun["sunrise"] + 3 * eighth)
    assert p["gulika_kaal"]["start_jd"] == pytest.approx(sun["sunrise"] + 5 * eighth)
    ab = p["abhijit_muhurta"]
    assert ab["end_jd"] - ab["start_jd"] == pytest.approx((sun["sunset"] - sun["sunrise"]) / 15)
    assert ab["start_jd"] < (sun["sunrise"] + sun["sunset"]) / 2 < ab["end_jd"]


def test_every_weekday_part_table_is_a_permutation():
    from kundli.panchang.inauspicious import GULIKA_KAAL_PART, RAHU_KAAL_PART, YAMAGANDA_PART
    for t in (RAHU_KAAL_PART, YAMAGANDA_PART, GULIKA_KAAL_PART):
        assert len(set(t)) == 7 and all(1 <= x <= 8 for x in t)


def test_tamil_calendar_counts_days():
    rows = [tamil_calendar(date(2025, 10, 1) + timedelta(days=i), *DELHI, CFG) for i in range(60)]
    for a, b in zip(rows, rows[1:], strict=False):
        assert b["day"] == a["day"] + 1 or b["day"] == 1
        if b["day"] == 1:
            assert b["month_number"] == a["month_number"] % 12 + 1
    assert {r["month"] for r in rows} >= {"Purattasi", "Aippasi", "Karthigai"}


@pytest.mark.parametrize("ds,name", [
    ("2025-02-26", "Maha Shivaratri"), ("2025-03-13", "Holika Dahan"), ("2025-03-14", "Holi"),
    ("2025-04-06", "Rama Navami"), ("2025-08-27", "Ganesh Chaturthi"), ("2025-10-02", "Vijayadashami"),
    ("2025-10-20", "Diwali"), ("2025-01-14", "Makar Sankranti")])
def test_major_festival_dates_2025(ds, name):
    names = [f["name"] for f in festivals_on(date.fromisoformat(ds), *DELHI, CFG)]
    assert any(name in n for n in names), names


def test_festival_not_on_neighbouring_day():
    assert not [f for f in festivals_on(date(2025, 10, 21), *DELHI, CFG) if "Diwali" in f["name"]]


def test_festival_reverse_lookup_and_counts():
    d = festival_dates("diwali", 2025, *DELHI, CFG)
    assert [x["date"] for x in d] == ["2025-10-20"]
    assert 22 <= len(festival_dates("ekadashi_shukla", 2025, *DELHI, CFG)) + len(
        festival_dates("ekadashi_krishna", 2025, *DELHI, CFG)) <= 26
    with pytest.raises(ValueError):
        festival_dates("nope", 2025, *DELHI, CFG)


def test_purnimanta_relabels_krishna_paksha_months():
    amanta = festivals_on(date(2025, 2, 26), *DELHI, CFG)[0]
    purni = festivals_on(date(2025, 2, 26), *DELHI, EngineConfig(festival_tradition="drik_purnimanta"))[0]
    assert (amanta["month"], purni["month"]) == ("Magha", "Phalguna")


def test_festival_rules_are_sourced_and_flagged():
    rules = load_rules()
    assert len(rules) >= 20 and all(r.source and r.verify for r in rules)


def test_day_panchang_deterministic_and_complete():
    a = day_panchang(JD, *DELHI, CFG)
    assert a == day_panchang(JD, *DELHI, CFG)
    assert {"elements", "rise_set", "hora", "choghadiya", "inauspicious", "hindu_month", "tamil", "festivals"} <= set(a)
    assert a["vara"]["name"] == "Moon" and a["hindu_month"]["name"] == "Ashwin"


def test_sunrise_jd_matches_day_times():
    jd = sunrise_jd(date(2025, 10, 20), *DELHI, CFG)
    assert jd == day_times(date(2025, 10, 20), *DELHI, CFG)["sunrise_jd"]


def test_polar_summer_degrades_gracefully():
    jd = julian_day(datetime(2025, 6, 21, 10, 0, tzinfo=UTC))[1]
    out = day_panchang(jd, 69.65, 18.96, "Europe/Oslo", CFG)  # Tromso, midnight sun
    assert out["vara"].get("note") and "elements" in out and "hora" not in out


PANCHANG_ENDPOINTS = ["basic_panchang", "basic_panchang/sunrise", "advanced_panchang", "advanced_panchang/sunrise",
                      "planet_panchang", "planet_panchang/sunrise", "chaughadiya_muhurta", "hora_muhurta",
                      "hora_muhurta_dinman", "panchang_chart", "panchang_chart/sunrise", "tamil_panchang",
                      "tamil_month_panchang", "panchang_festival", "festival-by-date"]


@pytest.mark.parametrize("ep", PANCHANG_ENDPOINTS)
def test_compat_panchang_endpoints(ep):
    body = {"date": "2025-10-20", "time": "12:00", "lat": DELHI[0], "lon": DELHI[1], "tz": DELHI[2]}
    r = TestClient(app).post("/compat/" + ep, json=body)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["endpoint"] == ep and "conventions_used" in j and j["data"]


# ---- phase 13: monthly yogas, lookups -----------------------------------------------------------------------
def test_pushkar_nakshatra_sets_match_sign_geometry():
    """Tripushkar nakshatras split 3/1 over two signs, Dwipushkar 2/2: derive both sets from the zodiac."""
    from collections import Counter

    from kundli.data.tables import NAKSHATRAS
    from kundli.panchang.yogas_monthly import load_rules
    three_one, two_two = set(), set()
    for i, name in enumerate(NAKSHATRAS):
        signs = Counter(int((i * 4 + p) // 9) for p in range(4))  # 9 padas per sign
        if sorted(signs.values()) == [1, 3]:
            three_one.add(name)
        elif sorted(signs.values()) == [2, 2]:
            two_two.add(name)
    rules = load_rules()
    assert set(rules["tripushkar"]["nakshatras"]) == three_one
    assert set(rules["dwipushkar"]["nakshatras"]) == two_two


def test_monthly_yoga_rules_are_valid():
    from kundli.panchang.yogas_monthly import load_rules
    rules = load_rules()
    assert set(rules) == {"sarvartha_siddhi", "amrit_siddhi", "ravi_yoga", "ravi_pushya", "guru_pushya", "dwipushkar",
                          "tripushkar"}
    # every Amrit Siddhi weekday/nakshatra pair is also a Sarvartha Siddhi pair
    for wd, naks in rules["amrit_siddhi"]["table"].items():
        assert set(naks) <= set(rules["sarvartha_siddhi"]["table"][wd])


def test_guru_pushya_window_oct_2024():
    from kundli.panchang.yogas_monthly import monthly_yogas
    w = monthly_yogas(2024, 10, *DELHI, CFG, {"guru_pushya"})["guru_pushya"]
    assert [x["date"] for x in w] == ["2024-10-24"] and w[0]["weekday"] == "Thursday"


def test_monthly_yogas_windows_are_consistent():
    from kundli.panchang.yogas_monthly import WEEKDAY_NAMES, monthly_yogas
    res = monthly_yogas(2025, 10, *DELHI, CFG)
    for key, ws in res.items():
        for w in ws:
            assert w["start_jd"] < w["end_jd"] <= w["start_jd"] + 1.01  # a Vedic day is ~24 h
            if key in ("ravi_pushya", "guru_pushya"):
                assert w["nakshatra"] == ["Pushya"]
                assert w["weekday"] == ("Sunday" if key == "ravi_pushya" else "Thursday")
            if key in ("dwipushkar", "tripushkar"):
                assert w["weekday"] in ("Sunday", "Tuesday", "Saturday") and w["weekday"] in WEEKDAY_NAMES


def test_lookups_and_yoga_endpoints():
    c = TestClient(app)
    body = {"date": "2025-10-20", "time": "12:00", "lat": DELHI[0], "lon": DELHI[1], "tz": DELHI[2]}
    for ep in ("sarvartha_siddhi", "amrit_siddhi", "ravi_yoga", "ravi_pushya", "guru_pushya", "dwipushkar",
               "tripushkar", "astro_details", "planet_nature"):
        r = c.post("/compat/" + ep, json=body)
        assert r.status_code == 200, (ep, r.text)
    assert "ghat_chakra" in c.post("/compat/astro_details", json=body).json()["data"]["not_implemented"]
    assert c.post("/compat/ghat_chakra", json=body).status_code == 501
