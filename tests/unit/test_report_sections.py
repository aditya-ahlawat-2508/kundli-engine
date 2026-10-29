"""Edge cases for the modules behind the full report (the reference-report checks live in tests/reference)."""
from datetime import date, time

import pytest

from kundli.avakahada import avakahada, vashya
from kundli.chart import generate
from kundli.dasha import chara
from kundli.data.tables import NAKSHATRAS, NAME_SYLLABLES, SIGN_LORDS
from kundli.functional import functional_nature, lordships
from kundli.geo import resolve_place
from kundli.kp import kp_lords
from kundli.models import BirthInput
from kundli.numerology import name_number, numerology, reduce_digit
from kundli.remedies import gemstone_picks


def test_reduce_and_numerology():
    assert [reduce_digit(n) for n in (5, 10, 23, 99, 1985)] == [5, 1, 5, 9, 5]
    n = numerology("Test", date(2000, 1, 1))
    assert (n["radical"], n["destiny"]) == (1, 4) and n["radical_ruler"] == "Sun"
    assert name_number("") == 0 and name_number("a b-c") == name_number("ABC")


def test_kp_lords_cover_every_degree_and_follow_nakshatra_boundary():
    for i in range(3600):
        star, sub, subsub = kp_lords(i / 10)
        assert star and sub and subsub
    assert kp_lords(0.0) == ("Ketu", "Ketu", "Ketu")  # start of Ashwini: all three lords are the first (Ketu)
    assert kp_lords(13.3333)[0] == "Ketu" and kp_lords(13.3334)[0] == "Venus"


def test_avakahada_tables_are_complete():
    assert len(NAME_SYLLABLES) == len(NAKSHATRAS) == 27 and all(len(s.split()) == 4 for s in NAME_SYLLABLES)
    assert avakahada(0.0, None)["paya"] is None
    assert (vashya(8, 10), vashya(8, 20), vashya(9, 10), vashya(9, 20)) == ("Manav", "Chatushpad", "Chatushpad", "Jalchar")


@pytest.mark.parametrize("lagna", range(12))
def test_functional_nature_is_total_and_yogakaraka_is_kendra_plus_trikona(lagna):
    fn, lords = functional_nature(lagna), lordships(lagna)
    assert set(fn) == set(lords) and sum(len(h) for h in lords.values()) == 12  # the seven grahas rule all 12 houses
    for p, label in fn.items():
        if label == "yogakaraka":
            assert any(h in (4, 7, 10) for h in lords[p]) and any(h in (5, 9) for h in lords[p])


def test_gemstone_picks_follow_house_lords():
    for lagna in range(12):
        picks = gemstone_picks(lagna)
        assert [p["planet"] for p in picks] == [SIGN_LORDS[lagna], SIGN_LORDS[(lagna + 4) % 12],
                                                SIGN_LORDS[(lagna + 8) % 12]]


def test_chara_years_and_sequence():
    assert chara.sequence(9)[:3] == [9, 8, 7] and chara.sequence(0)[:3] == [0, 1, 2]
    signs = {p: 0 for p in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")}
    degs = dict.fromkeys(signs, 10.0)
    assert chara.sign_years(0, signs, degs) == 12  # lord in own sign: zero counts as 12
    assert all(1 <= chara.sign_years(s, signs, degs) <= 12 for s in range(12))


def test_report_sections_unknown_time_and_polar():
    k = generate(BirthInput(name="U", date=date(2004, 5, 5), time=None, place=resolve_place("Agra, India")))
    assert k.avakahada["paya"] is None and k.functional_nature is None and k.gemstones is None
    assert "cusps" not in k.kp and "chara" not in k.dashas and k.numerology and k.doshas["sadhesati_events"]
    polar = generate(BirthInput(name="T", date=date(1995, 6, 21), time=time(14, 0), place=resolve_place("Tromso, Norway", choice=0)))
    assert polar.kp["cusps"][0]["fallback"] and polar.panchang["hindu_month"]["name"]
