import pytest

from kundli import vargas as V
from kundli.aspects import aspected_signs, rashi_drishti
from kundli.data.tables import BAV_CONTRIB, BAV_TOTALS, SAV_TOTAL, VIM_YEARS
from kundli.dignity import compound_relation, dignity, natural_relation, temporal_relation
from kundli.houses import house_of, sripati_starts, whole_sign_house
from kundli.nakshatra import fraction_elapsed, nakshatra_index, nakshatra_lord, pada, sub_lord
from kundli.panchang import karana, tithi, yoga


# ---- nakshatra ----
def test_nakshatra_boundaries():
    assert nakshatra_index(0) == 0 and nakshatra_index(13.3334) == 1 and nakshatra_index(359.999) == 26
    assert [nakshatra_lord(i) for i in (0, 1, 8, 9, 26)] == ["Ketu", "Venus", "Mercury", "Ketu", "Mercury"]
    assert pada(0.1) == 1 and pada(3.4) == 2 and pada(13.3) == 4 and pada(13.4) == 1
    assert fraction_elapsed(6 + 40 / 60) == pytest.approx(0.5)


def test_sub_lord_starts_with_nakshatra_lord_and_spans_sum():
    assert sub_lord(0.0001) == "Ketu"       # Ashwini (Ketu) starts with Ketu sub
    assert sub_lord(13.3333 + 0.0001) == "Venus"
    # last sub-lord of Ashwini is Venus (cycle Ketu,Venus,Sun,Moon,Mars,Rahu,Jupiter,Saturn,Mercury -> ends Mercury)
    assert sub_lord(13.3333 - 0.0001) == "Mercury"


# ---- dignity ----
def test_dignities():
    s = {p: 0 for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]}
    assert dignity("Sun", 0, 10, {**s}) == "exalted"
    assert dignity("Sun", 6, 10, {**s, "Sun": 6}) == "debilitated"
    assert dignity("Mars", 7, 5, {**s, "Mars": 7}) == "own"
    assert dignity("Mars", 0, 5, {**s}) == "moolatrikona"   # Aries 0-12
    assert dignity("Mars", 0, 20, {**s}) == "own"           # Aries beyond MT window
    assert dignity("Moon", 1, 2, {**s, "Moon": 1}) == "exalted"


def test_relations():
    assert natural_relation("Sun", "Moon") == "friend" and natural_relation("Sun", "Saturn") == "enemy"
    assert natural_relation("Moon", "Mars") == "neutral"
    assert temporal_relation(0, 1) == "friend" and temporal_relation(0, 0) == "enemy" and temporal_relation(0, 4) == "enemy"
    assert compound_relation("Sun", "Moon", 0, 1) == "great_friend"
    assert compound_relation("Sun", "Saturn", 0, 4) == "great_enemy"
    assert compound_relation("Sun", "Mercury", 0, 1) == "friend"       # neutral + temporal friend
    assert compound_relation("Sun", "Moon", 0, 0) == "neutral"         # friend + temporal enemy


# ---- aspects ----
def test_graha_drishti():
    assert aspected_signs("Jupiter", 0) == [4, 6, 8]
    assert aspected_signs("Mars", 0) == [3, 6, 7]
    assert aspected_signs("Saturn", 0) == [2, 6, 9]
    assert aspected_signs("Sun", 3) == [9]


def test_rashi_drishti():
    assert rashi_drishti(0) == [4, 7, 10]      # Aries -> fixed signs except adjacent Taurus
    assert rashi_drishti(1) == [3, 6, 9]       # Taurus (fixed) -> movable except adjacent Aries
    assert rashi_drishti(2) == [5, 8, 11]      # Gemini (dual) -> other duals


# ---- houses ----
def test_house_of_and_sripati():
    starts = tuple(float(30 * i) for i in range(12))
    assert house_of(0.0, starts) == 1 and house_of(29.99, starts) == 1 and house_of(359.0, starts) == 12
    wrap = tuple((45.0 + 30 * i) % 360 for i in range(12))
    assert house_of(44.0, wrap) == 12 and house_of(46.0, wrap) == 1
    assert whole_sign_house(0, 11) == 2
    mad = [15.0 + 30 * i for i in range(12)]
    assert sripati_starts(mad)[0] == pytest.approx(0.0)


# ---- panchang ----
def test_panchang_formulas():
    assert tithi(0, 0.0)[0] == 1 and tithi(0, 12.0)[0] == 2 and tithi(0, 180)[0] == 16 and tithi(0, 359)[0] == 30
    assert tithi(0, 180)[2] == "krishna" and tithi(0, 168)[1] == "Purnima"
    assert karana(0, 0.1)[1] == "Kimstughna" and karana(0, 6.1)[1] == "Bava" and karana(0, 345)[1] == "Shakuni"
    assert karana(0, 351)[1] == "Chatushpada" and karana(0, 359)[1] == "Naga"
    assert yoga(0, 0)[1] == "Vishkambha" and yoga(180, 180)[0] == 1


# ---- vargas: one test per rule ----
@pytest.mark.parametrize("fn,lon,sign", [
    (V.d1, 45.0, 1),
    (V.d2, 10.0, 4), (V.d2, 20.0, 3), (V.d2, 40.0, 3), (V.d2, 50.0, 4),   # odd sign: Sun then Moon; even: reversed
    (V.d3, 5.0, 0), (V.d3, 15.0, 4), (V.d3, 25.0, 8),
    (V.d4, 1.0, 0), (V.d4, 8.0, 3), (V.d4, 16.0, 6), (V.d4, 29.0, 9),
    (V.d6, 1.0, 0), (V.d6, 31.0, 6),                                      # odd from Aries, even from Libra
    (V.d7, 1.0, 0), (V.d7, 31.0, 7),                                      # odd from sign, even from 7th
    (V.d9, 1.0, 0), (V.d9, 31.0, 9), (V.d9, 61.0, 6), (V.d9, 91.0, 3), (V.d9, 359.9, 11),
    (V.d10, 1.0, 0), (V.d10, 31.0, 9),                                     # even sign starts 9th from itself
    (V.d12, 1.0, 0), (V.d12, 3.0, 1), (V.d12, 59.0, 0),
    (V.d16, 1.0, 0), (V.d16, 31.0, 4), (V.d16, 61.0, 8),
    (V.d20, 1.0, 0), (V.d20, 31.0, 8), (V.d20, 61.0, 4),
    (V.d24, 1.0, 4), (V.d24, 31.0, 3),
    (V.d27, 1.0, 0), (V.d27, 31.0, 3), (V.d27, 61.0, 6), (V.d27, 91.0, 9),
    (V.d30, 2.0, 0), (V.d30, 7.0, 10), (V.d30, 15.0, 8), (V.d30, 20.0, 2), (V.d30, 27.0, 6),
    (V.d30, 32.0, 1), (V.d30, 40.0, 5), (V.d30, 50.0, 9), (V.d30, 55.0, 7), (V.d30, 59.0, 7),
    (V.d40, 0.5, 0), (V.d40, 30.5, 6),
    (V.d45, 0.1, 0), (V.d45, 30.1, 4), (V.d45, 60.1, 8),
    (V.d60, 0.1, 0), (V.d60, 15.2, 6),
    (V.d5, 1.0, 0), (V.d5, 7.0, 10), (V.d5, 31.0, 1), (V.d5, 37.0, 5),
    (V.d8, 1.0, 0), (V.d8, 31.0, 8), (V.d8, 61.0, 4),
    (V.d11, 1.0, 0), (V.d11, 29.9, 10),
])
def test_varga_rules(fn, lon, sign):
    assert fn(lon)[0] == sign


def test_varga_degree_in_part_scaled():
    assert V.d9(0.0)[1] == pytest.approx(0.0) and V.d9(1.66666)[1] == pytest.approx(15.0, abs=0.01)
    assert V.is_vargottama(1.0) and not V.is_vargottama(10.0)  # Aries 1deg: navamsa Aries


@pytest.mark.parametrize("name", list(V.VARGAS))
def test_all_vargas_sweep_in_range(name):
    for i in range(0, 3600, 7):
        s, d = V.VARGAS[name](i / 10.0)
        assert 0 <= s < 12 and 0 <= d <= 30.0 + 1e-9


# ---- ashtakavarga tables ----
def test_bav_tables_totals():
    for p, rows in BAV_CONTRIB.items():
        assert sum(len(v) for v in rows.values()) == BAV_TOTALS[p]
    assert sum(BAV_TOTALS.values()) == SAV_TOTAL == 337
    assert sum(VIM_YEARS.values()) == 120
