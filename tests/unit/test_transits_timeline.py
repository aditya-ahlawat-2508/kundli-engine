from datetime import UTC, date, datetime, time, timedelta

import pytest

from kundli import timeline, transits, varshaphal
from kundli.chart import current_dasha, generate
from kundli.config import EngineConfig
from kundli.geo import resolve_place
from kundli.models import BirthInput

CFG = EngineConfig()
# Published sidereal (Lahiri) ingress dates, Drik Panchang convention (UTC date; +-1 day tolerance)
SATURN = [("2020-01-24", "Capricorn"), ("2022-04-29", "Aquarius"), ("2022-07-12", "Capricorn"),
          ("2023-01-17", "Aquarius"), ("2025-03-29", "Pisces")]
JUPITER = [("2021-04-05", "Aquarius"), ("2021-09-14", "Capricorn"), ("2021-11-20", "Aquarius"),
           ("2022-04-13", "Pisces"), ("2023-04-21", "Aries"), ("2024-05-01", "Taurus"), ("2025-05-14", "Gemini")]


@pytest.mark.parametrize("planet,table", [("Saturn", SATURN), ("Jupiter", JUPITER)])
def test_ingress_dates_match_published(planet, table):
    ev = transits.ingresses(planet, datetime(2020, 1, 1, tzinfo=UTC), datetime(2025, 12, 31, tzinfo=UTC), CFG)
    got = {(e["utc"][:10], e["to_sign_name"]) for e in ev}
    for d, sign in table:
        near = {(str((datetime.fromisoformat(d) + timedelta(days=o)).date()), sign) for o in (-1, 0, 1)}
        assert got & near, f"{planet} {sign} {d} not found in {sorted(got)}"


def test_saturn_next_decade_ingresses_are_found():
    ev = transits.ingresses("Saturn", datetime(2025, 1, 1, tzinfo=UTC), datetime(2030, 12, 31, tzinfo=UTC), CFG)
    assert [e["to_sign_name"] for e in ev][:2] == ["Pisces", "Aries"] or "Aries" in [e["to_sign_name"] for e in ev]


@pytest.fixture(scope="module")
def kundli():
    return generate(BirthInput(name="x", date=date(2000, 1, 1), time=time(12, 0), place=resolve_place("Agra, India")))


def test_sade_sati_status_and_periods():
    assert transits.sade_sati_status(5, 4)["phase"] == "sade_sati_rising"       # Saturn 12th from Moon
    assert transits.sade_sati_status(5, 5)["phase"] == "sade_sati_peak"
    assert transits.sade_sati_status(5, 6)["phase"] == "sade_sati_setting"
    assert transits.sade_sati_status(5, 8)["phase"] == "dhaiya_kantaka"
    assert transits.sade_sati_status(5, 0)["phase"] == "dhaiya_ashtama" or not transits.sade_sati_status(5, 0)["active"]
    # Moon in Capricorn (9): Saturn in Sag(8) rising, Capricorn peak, Aquarius setting -> 2017..2020 etc.
    per = transits.sade_sati_periods(9, datetime(2019, 1, 1, tzinfo=UTC), datetime(2024, 1, 1, tzinfo=UTC), CFG)
    assert per and per[0]["phase"].startswith("sade_sati")
    assert any(p["phase"] == "sade_sati_peak" and p["start"].startswith("2020-01-24") for p in per)


def test_snapshot_and_dasha(kundli):
    s = transits.snapshot(kundli, datetime(2026, 10, 10, tzinfo=UTC))
    assert set(s["planets"]) >= {"Saturn", "Jupiter"} and "bav_bindus" in s["planets"]["Saturn"]
    st = current_dasha(kundli, datetime(2026, 10, 10, tzinfo=UTC), levels=5)
    assert len(st) == 5 and st[0]["lord"] == "Saturn" and st[1]["lord"] == "Ketu"
    with pytest.raises(ValueError):
        current_dasha(kundli, datetime(2026, 10, 10))


def test_next_return(kundli):
    d = transits.next_return(kundli, "Jupiter", datetime(2026, 1, 1, tzinfo=UTC))
    assert datetime(2026, 1, 1, tzinfo=UTC) < d < datetime(2040, 1, 1, tzinfo=UTC)


def test_timeline_scores_are_bounded_and_explained(kundli):
    w = timeline.load_weights()
    assert w["version"] == 1 and "career" in w["areas"]
    for area in w["areas"]:
        s = timeline.score_at(kundli, datetime(2026, 10, 10, tzinfo=UTC), area, w)
        assert 0 <= s["score"] <= 100 and s["dasha"] and "Jupiter" in s["transit"]
    t = timeline.build_timeline(kundli, datetime(2026, 10, 10, tzinfo=UTC), datetime(2028, 12, 31, tzinfo=UTC), "career")
    assert t["weights_version"] == 1 and len(t["samples"]) > 20
    assert timeline.build_timeline(kundli, datetime(2026, 10, 10, tzinfo=UTC), datetime(2028, 12, 31, tzinfo=UTC), "career") == t


def test_timeline_needs_birth_time():
    k = generate(BirthInput(name="x", date=date(2000, 1, 1), time=None, place=resolve_place("Agra, India")))
    with pytest.raises(ValueError):
        timeline.score_at(k, datetime(2026, 1, 1, tzinfo=UTC), "career")


def test_varshaphal(kundli):
    r = varshaphal.solar_return(kundli, 2026)
    natal_sun = next(p.sidereal_lon for p in kundli.planets if p.name == "Sun")
    assert abs(r["planets"]["Sun"]["longitude"] - natal_sun) < 1e-3
    assert r["muntha"]["sign"] == (kundli.lagna["sign"] + 26) % 12 and r["age"] == 26
