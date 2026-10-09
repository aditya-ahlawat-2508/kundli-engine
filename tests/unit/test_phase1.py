from datetime import UTC, date, datetime, time

import pytest
import swisseph as swe

from kundli.ayanamsa import ayanamsa_ut
from kundli.config import EngineConfig
from kundli.ephemeris import PLANET_IDS, planet_positions
from kundli.errors import AmbiguousLocalTime, AmbiguousPlace, NonexistentLocalTime, PlaceNotFound
from kundli.geo import candidates, resolve_place
from kundli.models import BirthInput
from kundli.timeutil import jd_to_utc, local_to_utc, resolve_birth

# (label, date, time, place-name) -- places resolved offline
BIRTHS = [
    ("agra-2000", date(2000, 1, 1), time(12, 0), "Agra, India"),
    ("mumbai-1985", date(1985, 6, 15), time(5, 45), "Mumbai"),
    ("sydney-1990", date(1990, 12, 25), time(23, 10), "Sydney, Australia"),
    ("ny-2023", date(2023, 7, 4), time(9, 30), "New York City, United States"),
    ("delhi-1943", date(1943, 3, 3), time(8, 15), "Delhi, India"),
]


def _birth(d, t, q, fold=None):
    return BirthInput(name="t", date=d, time=t, place=resolve_place(q, choice=0), fold=fold)


@pytest.mark.parametrize("label,d,t,q", BIRTHS)
def test_positions_match_raw_swisseph(label, d, t, q):
    cfg = EngineConfig()
    m = resolve_birth(_birth(d, t, q))
    pos = {p.name: p for p in planet_positions(m.jd_ut, cfg)}
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    for name, body in PLANET_IDS.items():
        trop = swe.calc_ut(m.jd_ut, body, swe.FLG_MOSEPH | swe.FLG_SPEED)[0][0]
        sid = swe.calc_ut(m.jd_ut, body, swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED)[0][0]
        assert pos[name].tropical_lon == trop % 360
        assert pos[name].sidereal_lon == sid % 360
    node = swe.calc_ut(m.jd_ut, swe.TRUE_NODE, swe.FLG_MOSEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED)[0][0]
    assert pos["Rahu"].sidereal_lon == node % 360
    assert pos["Ketu"].sidereal_lon == (node + 180) % 360


@pytest.mark.parametrize("label,d,t,q", BIRTHS)
def test_sidereal_equals_tropical_minus_ayanamsa(label, d, t, q):
    m = resolve_birth(_birth(d, t, q))
    ay = ayanamsa_ut(m.jd_ut)
    for p in planet_positions(m.jd_ut, EngineConfig()):
        diff = (p.tropical_lon - p.sidereal_lon - ay + 180) % 360 - 180
        assert abs(diff) < 1 / 3600  # < 1 arcsec


def test_lahiri_calendar_reform_epoch():
    # Indian Calendar Reform Committee: Lahiri ayanamsa = 23 deg 15' 00.658" at 1956-03-21 (0h)
    jd = swe.julday(1956, 3, 21, 0.0)
    assert ayanamsa_ut(jd) == pytest.approx(23 + 15 / 60 + 0.658 / 3600, abs=10 / 3600)


def test_ayanamsas_differ():
    jd = swe.julday(2000, 1, 1, 12.0)
    assert len({ayanamsa_ut(jd, n) for n in ("lahiri", "raman", "kp", "true_chitra")}) == 4


def test_rahu_ketu_opposite_and_mean_node():
    m = resolve_birth(_birth(*BIRTHS[0][1:]))
    for node in ("mean", "true"):
        pos = {p.name: p for p in planet_positions(m.jd_ut, EngineConfig(node_type=node))}
        assert (pos["Rahu"].sidereal_lon - pos["Ketu"].sidereal_lon) % 360 == pytest.approx(180)
    assert pos["Rahu"].retrograde


def test_outer_planets_optional():
    jd = swe.julday(2000, 1, 1, 12.0)
    assert len(planet_positions(jd, EngineConfig())) == 9
    assert len(planet_positions(jd, EngineConfig(include_outer_planets=True))) == 12


# ---- time conversion --------------------------------------------------------------
def test_india_1943_war_time():
    utc, off = local_to_utc(datetime(1943, 3, 3, 8, 15), "Asia/Kolkata")
    assert off == 6.5 * 3600  # war time UTC+6:30 (1942-09 .. 1945-10)
    assert utc == datetime(1943, 3, 3, 1, 45, tzinfo=UTC)


def test_india_pre_1906_lmt():
    _, off = local_to_utc(datetime(1900, 1, 1, 12, 0), "Asia/Kolkata")
    assert off != 5.5 * 3600  # not IST: Kolkata/Madras local mean time regime


def test_india_modern_ist():
    _, off = local_to_utc(datetime(2004, 5, 5, 12, 0), "Asia/Kolkata")
    assert off == 5.5 * 3600


def test_us_dst_overlap_requires_fold():
    t = datetime(2023, 11, 5, 1, 30)
    with pytest.raises(AmbiguousLocalTime):
        local_to_utc(t, "America/New_York")
    u0, o0 = local_to_utc(t, "America/New_York", fold=0)
    u1, o1 = local_to_utc(t, "America/New_York", fold=1)
    assert (o0, o1) == (-4 * 3600, -5 * 3600)
    assert u1 - u0 == datetime(2023, 1, 1, 1, tzinfo=UTC) - datetime(2023, 1, 1, tzinfo=UTC)


def test_us_dst_gap_rejected():
    with pytest.raises(NonexistentLocalTime):
        local_to_utc(datetime(2023, 3, 12, 2, 30), "America/New_York")
    with pytest.raises(NonexistentLocalTime):
        local_to_utc(datetime(2023, 3, 12, 2, 30), "America/New_York", fold=1)


def test_southern_hemisphere_dst():
    _, off = local_to_utc(datetime(1990, 12, 25, 23, 10), "Australia/Sydney")
    assert off == 11 * 3600  # AEDT
    _, off = local_to_utc(datetime(1990, 6, 25, 12, 0), "Australia/Sydney")
    assert off == 10 * 3600  # AEST


def test_julian_day_roundtrip():
    m = resolve_birth(_birth(*BIRTHS[1][1:]))
    assert abs((jd_to_utc(m.jd_ut) - m.utc).total_seconds()) < 0.01
    assert swe.julday(2000, 1, 1, 12.0) == pytest.approx(2451545.0)


def test_time_unknown_uses_noon():
    m = resolve_birth(_birth(date(2000, 1, 1), None, "Agra, India"))
    assert m.time_unknown and m.local.hour == 12


# ---- geo ----------------------------------------------------------------------------
def test_geo_unique():
    p = resolve_place("Agra, India")
    assert (p.tz, round(p.lat, 1), round(p.lon, 1)) == ("Asia/Kolkata", 27.2, 78.0)


def test_geo_ambiguous_raises_with_candidates():
    with pytest.raises(AmbiguousPlace) as e:
        resolve_place("Springfield")
    assert len(e.value.candidates) > 1
    assert resolve_place("Springfield, Missouri").admin1 == "Missouri"


def test_geo_not_found_and_fallback(tmp_path):
    calls = []

    def fake(q):
        calls.append(q)
        return [{"lat": "27.17", "lon": "78.0", "name": "Zzyzx", "address": {"state": "UP", "country": "India"}}]

    assert candidates("Qwertyville", online=False) == []
    p1 = resolve_place("Qwertyville", cache_dir=tmp_path, fetch=fake)
    p2 = resolve_place("Qwertyville", cache_dir=tmp_path, fetch=fake)  # served from disk cache
    assert p1 == p2 and p1.source == "nominatim" and p1.tz == "Asia/Kolkata" and len(calls) == 1
    with pytest.raises(PlaceNotFound):
        resolve_place("Qwertyville", cache_dir=tmp_path / "x", fetch=lambda q: [])


def test_determinism():
    cfg = EngineConfig()
    m = resolve_birth(_birth(*BIRTHS[0][1:]))
    a = [p.model_dump_json() for p in planet_positions(m.jd_ut, cfg)]
    assert a == [p.model_dump_json() for p in planet_positions(m.jd_ut, cfg)]
    hash(cfg)  # frozen/hashable
