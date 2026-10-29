"""V2 phase 19: numerology systems, lookups, daily number and biorhythm."""
import math
from datetime import date

import pytest
from fastapi.testclient import TestClient

from kundli.api import app
from kundli.biorhythm import MAX_SERIES_DAYS, PERIODS, biorhythm, biorhythm_series, value
from kundli.numerology import (
    CHALDEAN,
    PYTHAGOREAN,
    RULERS,
    daily_number,
    fast_day,
    fav_lord,
    fav_place,
    fav_time,
    mantra,
    name_number,
    numerology,
    reduce_digit,
)
from kundli.numerology.lookups import data, relation


@pytest.fixture(autouse=True)
def _data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("KUNDLI_DATA_DIR", str(tmp_path))


# ---- letter tables ------------------------------------------------------------------------------------------
def test_letter_tables_cover_the_alphabet():
    letters = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    assert set(CHALDEAN) == letters and set(PYTHAGOREAN) == letters
    assert set(CHALDEAN.values()) == set(range(1, 9))  # Chaldean never uses 9
    assert set(PYTHAGOREAN.values()) == set(range(1, 10))
    assert all(PYTHAGOREAN[c] == (ord(c) - 65) % 9 + 1 for c in letters)  # A=1 ... I=9, J=1 ...


def test_name_number_by_system():
    assert name_number("A", "chaldean") == 1 and name_number("A", "pythagorean") == 1
    assert name_number("ABC", "pythagorean") == 6 and name_number("ABC", "chaldean") == reduce_digit(1 + 2 + 3)
    assert name_number("Hello World!", "pythagorean") == reduce_digit(sum(PYTHAGOREAN[c] for c in "HELLOWORLD"))
    assert name_number("123 !!", "chaldean") == 0
    with pytest.raises(KeyError):
        name_number("A", "other")


def test_numerology_system_follows_config_and_is_echoed():
    c = TestClient(app)
    body = {"name": "Test Name", "date": "1990-05-05", "time": "10:30", "lat": 28.6, "lon": 77.2, "tz": "Asia/Kolkata"}
    a = c.post("/compat/numero_table", json=body).json()["data"]
    b = c.post("/compat/numero_table", json={**body, "config": {"numerology_system": "pythagorean"}}).json()["data"]
    assert a["system"] == "chaldean" and b["system"] == "pythagorean"
    assert a["name"] == name_number("Test Name", "chaldean") and b["name"] == name_number("Test Name", "pythagorean")
    assert (a["radical"], a["destiny"]) == (b["radical"], b["destiny"]) == (5, reduce_digit(5 + 5 + 1990))


def test_radical_and_destiny():
    n = numerology("X", date(1990, 5, 29))
    assert n["radical"] == reduce_digit(29) == 2 and n["destiny"] == reduce_digit(2 + 9 + 5 + 1 + 9 + 9 + 0)


# ---- lookups ------------------------------------------------------------------------------------------------
def test_lookup_tables_are_complete_and_flagged():
    d = data()
    assert d["verify"] is True and d["source"]
    assert set(d["mantra"]) == set(RULERS.values())
    assert set(d["direction"]) == {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"}
    assert len(set(d["direction"].values())) == 8  # eight distinct directions


def test_fav_time_is_the_weekday_of_the_lord():
    assert [fav_time(n)["weekday"] for n in (1, 2, 3, 5, 6, 8, 9)] == [
        "Sunday", "Monday", "Thursday", "Wednesday", "Friday", "Saturday", "Tuesday"]
    assert fav_time(4)["weekday"] is None and fav_time(7)["weekday"] is None and "no weekday" in fav_time(4)["note"]


def test_fav_lord_relations_follow_the_friendship_table():
    f = fav_lord(1)  # Sun: friends Moon, Mars, Jupiter; enemies Venus, Saturn; neutral Mercury
    assert f["lord"] == "Sun" and f["friendly_numbers"] == [2, 3, 9] and sorted(f["inimical_numbers"]) == [6, 8]
    assert f["neutral_numbers"] == [5] and f["not_defined_numbers"] == [4, 7]
    for n in range(1, 10):
        f = fav_lord(n)
        assert sorted(f["friendly_numbers"] + f["neutral_numbers"] + f["inimical_numbers"] + f["not_defined_numbers"]) == [
            m for m in range(1, 10) if m != n]
    assert relation(3, 3) == "same" and relation(4, 5) == "not_defined"
    with pytest.raises(ValueError):
        fav_lord(10)


def test_place_mantra_fast():
    assert fav_place(1)["direction"] == "East" and fav_place(2)["direction"] == "North-West" and fav_place(7)["direction"] is None
    assert mantra(1)["mantra"].startswith("Om Hraam") and "disclaimer" in mantra(9)
    assert fast_day(5)["weekday"] == "Wednesday" and "content" not in fast_day(5)  # text comes from the content store


def test_daily_number_convention():
    d = daily_number(5, date(2026, 10, 10))
    assert d["date_root"] == reduce_digit(1 + 0 + 1 + 0 + 2 + 0 + 2 + 6) and d["daily_number"] == reduce_digit(5 + d["date_root"])
    assert d["relation_to_birth_number"] == relation(5, d["daily_number"]) and "content" not in d
    assert 1 <= daily_number(9, date(2000, 1, 1))["daily_number"] <= 9


# ---- biorhythm ----------------------------------------------------------------------------------------------
def test_biorhythm_values_and_cycle_positions():
    b = date(1990, 5, 5)
    r = biorhythm(b, b)
    assert r["days_since_birth"] == 0 and all(c["value"] == 0.0 and c["critical"] for c in r["cycles"].values())
    r = biorhythm(b, date(1990, 5, 5).replace(day=12))  # 7 days
    assert r["cycles"]["physical"]["value"] == pytest.approx(math.sin(2 * math.pi * 7 / 23))
    assert PERIODS == {"physical": 23, "emotional": 28, "intellectual": 33}
    # a full period later the cycle repeats; half a period is the other zero crossing; quarter period is the peak
    assert value(23, 23) == pytest.approx(0.0, abs=1e-12) and value(14, 28) == pytest.approx(0.0, abs=1e-12)
    assert value(7, 28) == pytest.approx(1.0) and value(21, 28) == pytest.approx(-1.0)
    p = biorhythm(b, date.fromordinal(b.toordinal() + 23))["cycles"]["physical"]
    assert p["day_in_cycle"] == 0 and abs(p["value"]) < 1e-12 and r["disclaimer"].startswith("Entertainment only")


def test_biorhythm_critical_days_and_phase():
    b = date(2000, 1, 1)
    crit = [t for t in range(70) if biorhythm(date.fromordinal(b.toordinal()), date.fromordinal(b.toordinal() + t))["cycles"]["physical"]["critical"]]
    # zero crossings of sin(2 pi t/23): at t = 0, 11.5 (between 11 and 12), 23, 34.5 ...
    assert crit == [0, 11, 23, 34, 46, 57, 69]
    assert biorhythm(b, date.fromordinal(b.toordinal() + 3))["cycles"]["physical"]["phase"] == "rising"
    assert biorhythm(b, date.fromordinal(b.toordinal() + 9))["cycles"]["physical"]["phase"] == "falling"


def test_biorhythm_errors_and_series():
    b = date(2000, 1, 1)
    with pytest.raises(ValueError, match="before birth"):
        biorhythm(b, date(1999, 12, 31))
    s = biorhythm_series(b, date(2000, 2, 1), date(2000, 2, 10))
    assert s[0]["date"] == "2000-02-01" and len(s) == 10
    with pytest.raises(ValueError):
        biorhythm_series(b, date(2000, 2, 10), date(2000, 2, 1))
    with pytest.raises(ValueError, match="at most"):
        biorhythm_series(b, date(2000, 2, 1), date.fromordinal(date(2000, 2, 1).toordinal() + MAX_SERIES_DAYS))


# ---- endpoints ----------------------------------------------------------------------------------------------
BODY = {"name": "Aditya", "date": "1990-05-05", "time": "10:30", "lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata",
        "as_of": "2026-10-10"}


@pytest.mark.parametrize("ep", ["numero_table", "numero_report", "numero_fav_time", "numero_place_vastu",
                                "numero_fasts_report", "numero_fav_lord", "numero_fav_mantra", "numero_prediction/daily",
                                "biorhythm"])
def test_numerology_endpoints(ep):
    r = TestClient(app).post("/compat/" + ep, json=BODY)
    assert r.status_code == 200, r.text
    assert r.json()["data"] and "conventions_used" in r.json()


def test_biorhythm_endpoint_options_and_moon_biorhythm_not_implemented():
    c = TestClient(app)
    one = c.post("/compat/biorhythm", json=BODY).json()["data"]
    assert one["days_since_birth"] == (date(2026, 10, 10) - date(1990, 5, 5)).days and "disclaimer" in one
    series = c.post("/compat/biorhythm", json={**BODY, "end_date": "2026-10-12"}).json()["data"]["series"]
    assert [s["date"] for s in series] == ["2026-10-10", "2026-10-11", "2026-10-12"]
    assert c.post("/compat/biorhythm", json={**BODY, "as_of": "1980-01-01"}).status_code == 422
    assert c.post("/compat/biorhythm", json={**BODY, "as_of": None}).status_code == 422
    r = c.post("/compat/moon_biorhythm", json=BODY)
    assert r.status_code == 501 and r.json()["phase"] == "19"
    lords = c.post("/compat/numero_fav_lord", json=BODY).json()["data"]
    assert lords["radical"]["number"] == 5 and lords["radical"]["lord"] == "Mercury"
