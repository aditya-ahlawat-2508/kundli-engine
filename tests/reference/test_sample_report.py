"""External cross-check: values read from a third-party Vedic horoscope report (AstrologyAPI/VedicRishi sample PDF,
23/2/1985 05:45, Malkapur 20 N 53 / 76 E 12, Lahiri, MEAN node). Only numeric facts are used, no vendor text.

Findings recorded here:
* Positions agree to ~1 arcsecond; the vendor uses the mean node (true node differs by ~1 degree for Rahu/Ketu).
* The vendor's lat/lon are rounded to whole arcminutes, so the ascendant/cusps agree only to ~1 arcminute.
* The vendor's "KP house cusps" table is in tropical degrees (cusp 1 = 313:45:51 vs sidereal Asc 290:06:53); not used.
"""
from datetime import date, datetime, time

import pytest

from kundli.chart import generate
from kundli.config import EngineConfig
from kundli.models import BirthInput, Place

ARCMIN = 1 / 60
PLACE = Place(name="Malkapur", admin1="Maharashtra", country="India", lat=20 + 53 / 60, lon=76 + 12 / 60,
              tz="Asia/Kolkata", source="manual")

# name: (sign, degrees, minutes, seconds, nakshatra)
PLANETS = {
    "Sun": ("Aquarius", 10, 41, 5, "Shatabhisha"), "Moon": ("Pisces", 16, 33, 50, "Uttara Bhadrapada"),
    "Mars": ("Pisces", 21, 31, 10, "Revati"), "Mercury": ("Aquarius", 13, 47, 22, "Shatabhisha"),
    "Jupiter": ("Capricorn", 10, 1, 21, "Shravana"), "Venus": ("Pisces", 22, 29, 17, "Revati"),
    "Saturn": ("Scorpio", 4, 20, 46, "Anuradha"), "Rahu": ("Aries", 28, 41, 42, "Krittika"),
    "Ketu": ("Libra", 28, 41, 42, "Vishakha"),
}
SAV = [29, 24, 31, 25, 27, 25, 28, 37, 33, 36, 20, 22]
SUN_BAV = [3, 4, 5, 2, 4, 5, 4, 6, 6, 3, 3, 3]
VIMSHOTTARI = [("Saturn", "1966-04-17"), ("Mercury", "1985-04-17"), ("Ketu", "2002-04-17"), ("Venus", "2009-04-17"),
               ("Sun", "2029-04-17")]
YOGINI = [("Mercury", "1980-03-09"), ("Saturn", "1985-03-09"), ("Venus", "1991-03-09"), ("Rahu", "1998-03-09")]


@pytest.fixture(scope="module")
def k():
    b = BirthInput(name="ref", date=date(1985, 2, 23), time=time(5, 45), place=PLACE)
    return generate(b, EngineConfig(node_type="mean"))


@pytest.mark.parametrize("name", PLANETS)
def test_planet_matches_reference(k, name):
    sign, d, m, s, nak = PLANETS[name]
    p = next(x for x in k.planets if x.name == name)
    assert p.sign_name == sign and p.nakshatra_name == nak
    assert abs(p.degree_in_sign - (d + m / 60 + s / 3600)) < ARCMIN / 4  # 15 arcsec


def test_ascendant_matches_reference_within_rounding_of_coordinates(k):
    assert k.lagna["sign_name"] == "Capricorn"
    assert abs(k.lagna["degree_in_sign"] - (20 + 6 / 60 + 53 / 3600)) < ARCMIN * 1.5
    assert k.lagna["nakshatra"] == "Shravana"


def test_true_node_differs_from_reference():
    """Documents why the report defaults to the mean node: the vendor (and many Indian tools) use it."""
    b = BirthInput(name="ref", date=date(1985, 2, 23), time=time(5, 45), place=PLACE)
    rahu = next(p for p in generate(b, EngineConfig(node_type="true")).planets if p.name == "Rahu")
    assert abs(rahu.degree_in_sign - (28 + 41 / 60 + 42 / 3600)) > ARCMIN * 30


def test_panchang_matches_reference(k):
    pc = k.panchang
    assert (pc["tithi"]["name"], pc["tithi"]["paksha"]) == ("Tritiya", "shukla")
    assert pc["yoga"]["name"].startswith("Shubh") and pc["karana"]["name"] == "Gara"
    assert pc["vara"]["name"] == "Venus"  # born before sunrise on the 23rd: the Vedic day is Friday the 22nd


def test_ashtakavarga_matches_reference(k):
    assert k.ashtakavarga["sav"] == SAV
    assert k.ashtakavarga["bav"]["Sun"] == SUN_BAV


@pytest.mark.parametrize("system,expected", [("vimshottari", VIMSHOTTARI), ("yogini", YOGINI)])
def test_dasha_starts_match_reference(k, system, expected):
    ms = k.dashas[system]["mahadashas"]
    for (lord, day), m in zip(expected, ms, strict=False):
        assert m["lord"] == lord
        got = datetime.fromisoformat(m["start_local"][:19])
        assert abs((got - datetime.fromisoformat(day)).total_seconds()) < 86400


# ---- sections added for the full report ---------------------------------------------------------------------
COLS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


def _matrix(rows: dict[str, str], names: dict[str, str]) -> dict[str, dict[str, str]]:
    return {p: {c: names[x] for c, x in zip(COLS, r.split(), strict=True) if x != "--"} for p, r in rows.items()}


PERMANENT = _matrix({
    "Sun": "-- F F N F E E", "Moon": "F -- N F N N N", "Mars": "F F -- E F N N", "Mercury": "F E N -- N F N",
    "Jupiter": "F F F E -- E N", "Venus": "E E N F N -- F", "Saturn": "E E E F N F --"},
    {"F": "friend", "E": "enemy", "N": "neutral"})
TEMPORAL = _matrix({
    "Sun": "-- F F E F F F", "Moon": "F -- E F F E E", "Mars": "F E -- F F E E", "Mercury": "E F F -- F F F",
    "Jupiter": "F F F F -- F F", "Venus": "F E E F F -- E", "Saturn": "F E E F F E --"},
    {"F": "friend", "E": "enemy"})
FIVE_FOLD = _matrix({
    "Sun": "-- I I E I N N", "Moon": "I -- E I F E E", "Mars": "I N -- N I E E", "Mercury": "N N F -- F I F",
    "Jupiter": "I I I N -- N F", "Venus": "N B E I F -- N", "Saturn": "N B B I F N --"},
    {"I": "great_friend", "F": "friend", "N": "neutral", "E": "enemy", "B": "great_enemy"})


def test_friendship_tables_match_reference(k):
    assert k.friendship["permanent"] == PERMANENT
    assert k.friendship["temporal"] == TEMPORAL
    assert k.friendship["five_fold"] == FIVE_FOLD


def test_avakahada_matches_reference(k):
    a = k.avakahada
    assert (a["varna"], a["vashya"], a["yoni"], a["gana"], a["nadi"], a["tatva"], a["paya"], a["name_alphabet"]) == (
        "Vipra", "Jalchar", "Gau", "Manushya", "Madhya", "Water", "Copper", "N")
    assert (a["sign"], a["sign_lord"], a["nakshatra"], a["charan"]) == ("Pisces", "Jupiter", "Uttara Bhadrapada", 4)


def test_hindu_month_matches_reference(k):
    assert k.panchang["hindu_month"]["name"] == "Phalguna" and not k.panchang["hindu_month"]["adhika"]


def test_functional_nature_matches_reference(k):
    assert k.functional_nature == {"Sun": "neutral", "Moon": "malefic", "Mars": "malefic", "Mercury": "benefic",
                                   "Jupiter": "malefic", "Venus": "yogakaraka", "Saturn": "benefic"}


def test_lagna_ashtakavarga_matches_reference(k):
    lb = k.ashtakavarga["lagna_bav"]
    assert lb["bav"] == [4, 6, 3, 4, 3, 3, 3, 6, 4, 5, 4, 4] and lb["total"] == 49
    assert lb["prastara"]["Venus"] == [1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1]


# planet: (nakshatra lord, sub lord, sub-sub lord)
KP_PLANETS = {"Sun": ("Rahu", "Saturn", "Saturn"), "Moon": ("Saturn", "Jupiter", "Rahu"),
              "Mars": ("Mercury", "Venus", "Ketu"), "Mercury": ("Rahu", "Mercury", "Rahu"),
              "Jupiter": ("Moon", "Moon", "Moon"), "Venus": ("Mercury", "Moon", "Rahu"),
              "Saturn": ("Saturn", "Saturn", "Venus"), "Rahu": ("Sun", "Mars", "Jupiter"),
              "Ketu": ("Jupiter", "Venus", "Ketu")}


def test_kp_lords_match_reference(k):
    from kundli.kp import kp_lords

    for p, exp in KP_PLANETS.items():
        r = k.kp["planets"][p]
        assert (r["nakshatra_lord"], r["sub_lord"], r["sub_sub_lord"]) == exp
    assert kp_lords(290 + 6 / 60 + 53 / 3600) == ("Moon", "Ketu", "Jupiter")  # reference ascendant


# House cusps as printed by the reference (tropical degrees, a vendor quirk): compare after adding the ayanamsa.
KP_CUSPS_TROPICAL = [313.76417, 351.19861, 25.98750, 55.15111, 80.51667, 105.41333, 133.76417, 171.19861, 205.98750,
                     235.15111, 260.51667, 285.41333]


def test_kp_cusps_match_reference_after_ayanamsa(k):
    ay = k.header["ayanamsa_degrees"]
    for i, ref in enumerate(KP_CUSPS_TROPICAL):
        mine = (k.kp["cusps"][i]["longitude"] + ay) % 360
        assert abs((mine - ref + 180) % 360 - 180) < ARCMIN * 2, (i + 1, mine, ref)


def test_kaal_sarpa_matches_reference(k):
    ks = k.doshas["kaal_sarpa"]
    assert (ks["present"], ks["type"], ks["direction"]) == (True, "Shankhpal", "ascending")


def test_numerology_matches_reference(k):
    n = k.numerology
    assert (n["radical"], n["radical_ruler"], n["destiny"]) == (5, "Mercury", 3)


def test_gemstones_match_reference(k):
    g = {x["role"]: x for x in k.gemstones}
    assert (g["life_stone"]["gem"], g["benefic_stone"]["gem"], g["lucky_stone"]["gem"]) == (
        "Blue Sapphire", "Diamond", "Emerald")
    assert (g["life_stone"]["day"], g["life_stone"]["finger"]) == ("Saturday", "Middle")
    assert (g["lucky_stone"]["day"], g["lucky_stone"]["finger"]) == ("Wednesday", "Little")


# (years) maha periods of Chara dasha and their end dates
CHARA_MAHA = [("Capricorn", 2, "1987-02-23"), ("Sagittarius", 1, "1988-02-23"), ("Scorpio", 11, "1999-02-23"),
              ("Libra", 5, "2004-02-23"), ("Virgo", 7, "2011-02-23"), ("Leo", 6, "2017-02-23"),
              ("Cancer", 4, "2021-02-23"), ("Gemini", 8, "2029-02-23"), ("Taurus", 10, "2039-02-23"),
              ("Aries", 11, "2050-02-23"), ("Pisces", 2, "2052-02-23"), ("Aquarius", 10, "2062-02-23")]


def test_chara_dasha_maha_matches_reference(k):
    ms = k.dashas["chara"]["mahadashas"]
    assert [(m["lord"], m["years"]) for m in ms] == [(s, y) for s, y, _ in CHARA_MAHA]
    for m, (_, _, end) in zip(ms, CHARA_MAHA, strict=True):
        assert abs((datetime.fromisoformat(m["end_local"][:19]) - datetime.fromisoformat(end)).total_seconds()) < 2 * 86400
    first = ms[0]["children"]  # only the first antardasha column of the reference is internally consistent
    assert [c["lord"] for c in first][:3] == ["Sagittarius", "Scorpio", "Libra"] and first[-1]["lord"] == "Capricorn"
    assert first[0]["end_local"].startswith("1985-04-2")


SADESATI = [("RISING_START", "1993-03-05"), ("RISING_END", "1993-10-15"), ("RISING_START", "1993-11-10"),
            ("PEAK_START", "1995-06-02"), ("RISING_START", "1995-08-10"), ("PEAK_START", "1996-02-16"),
            ("SETTING_START", "1998-04-17"), ("SETTING_END", "2000-06-07"), ("RISING_START", "2022-04-29"),
            ("RISING_END", "2022-07-12"), ("RISING_START", "2023-01-17"), ("PEAK_START", "2025-03-29"),
            ("SETTING_START", "2027-06-03"), ("PEAK_START", "2027-10-20"), ("SETTING_START", "2028-02-23"),
            ("SETTING_END", "2029-08-08"), ("SETTING_START", "2029-10-05"), ("SETTING_END", "2030-04-17"),
            ("RISING_START", "2052-02-25"), ("PEAK_START", "2054-05-14"), ("RISING_START", "2054-09-02"),
            ("PEAK_START", "2055-02-05"), ("SETTING_START", "2057-04-07"), ("SETTING_END", "2059-05-28")]


def test_sadhesati_events_match_reference(k):
    got = [(e["type"], e["date"]) for e in k.doshas["sadhesati_events"]][: len(SADESATI)]
    assert [t for t, _ in got] == [t for t, _ in SADESATI]
    for (_, a), (_, b) in zip(got, SADESATI, strict=True):
        assert abs((date.fromisoformat(a) - date.fromisoformat(b)).days) <= 1, (a, b)
