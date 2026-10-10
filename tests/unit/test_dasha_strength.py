from datetime import UTC, datetime, timedelta

import pytest

from helpers import make_core
from kundli.dasha import vimshottari, yogini
from kundli.strength.ashtakavarga import ashtakavarga, ekadhipatya_shodhana, trikona_shodhana

B = datetime(2000, 1, 1, 6, 30, tzinfo=UTC)


@pytest.mark.parametrize("moon", [0.0, 5.5, 100.0, 200.123, 359.999])
def test_vimshottari_contiguous_120y(moon):
    t = vimshottari.tree(moon, B, 365.25, 3, "UTC")
    assert len(t) == 9
    for a, b in zip(t, t[1:], strict=False):
        assert a["end_utc"] == b["start_utc"]
    span = datetime.fromisoformat(t[-1]["end_utc"]) - datetime.fromisoformat(t[0]["start_utc"])
    assert span.total_seconds() / 86400 == pytest.approx(120 * 365.25, abs=1e-3)
    assert datetime.fromisoformat(t[0]["start_utc"]) <= B < datetime.fromisoformat(t[0]["end_utc"])
    for m in t:                                                   # children tile their parent
        ch = m["children"]
        assert ch[0]["start_utc"] == m["start_utc"] and ch[-1]["end_utc"] == m["end_utc"]
        assert ch[0]["lord"] == m["lord"]
        assert all(a["end_utc"] == b["start_utc"] for a, b in zip(ch, ch[1:], strict=False))


def test_vimshottari_balance_and_first_lord():
    # Moon at 6deg40' Aries = halfway through Ashwini (Ketu, 7y): balance 3.5y
    b = vimshottari.balance_at_birth(6 + 40 / 60, 365.25)
    assert b["lord"] == "Ketu" and b["years"] == pytest.approx(3.5)
    t = vimshottari.tree(6 + 40 / 60, B, 365.25, 1, "UTC")
    first_end = datetime.fromisoformat(t[0]["end_utc"])
    assert (first_end - B).total_seconds() / 86400 == pytest.approx(3.5 * 365.25, abs=1e-3)


def test_savana_year_changes_lengths():
    t = vimshottari.tree(0.0, B, 360.0, 1, "UTC")
    assert t[1]["days"] == pytest.approx(20 * 360.0)


def test_stack_levels_and_as_of_explicit():
    s = vimshottari.stack(100.0, B, 365.25, datetime(2026, 10, 10, tzinfo=UTC), 5, "UTC")
    assert [x["level"] for x in s] == ["maha", "antar", "pratyantar", "sookshma", "prana"]
    for hi, lo in zip(s, s[1:], strict=False):
        assert hi["start_utc"] <= lo["start_utc"] and lo["end_utc"] <= hi["end_utc"]
    assert vimshottari.stack(100.0, B, 365.25, B - timedelta(days=36500 * 2), 3, "UTC") == []


def test_yogini_cycle_36y():
    t = yogini.tree(100.0, B, 365.25, 1, "UTC")
    assert len(t) == 8
    span = datetime.fromisoformat(t[-1]["end_utc"]) - datetime.fromisoformat(t[0]["start_utc"])
    assert span.total_seconds() / 86400 == pytest.approx(36 * 365.25, abs=1e-3)
    assert yogini.start_index(0.5) == 3  # Ashwini (1): (1+3)%8=4 -> Bhramari (index 3)


# ---- ashtakavarga ----
def test_sav_is_337_for_any_chart():
    for lagna in range(12):
        core = make_core(lagna, {"Sun": lagna, "Moon": (lagna + 3) % 12, "Mars": (lagna + 5) % 12})
        av = ashtakavarga(core)
        assert av["sav_total"] == 337 and sum(av["sav"]) == 337
        assert av["bav_totals"] == {"Sun": 48, "Moon": 49, "Mars": 39, "Mercury": 54, "Jupiter": 56, "Venus": 52, "Saturn": 39}
        assert sum(av["sav_by_house"].values()) == 337


def test_shodhana_rules():
    assert trikona_shodhana([3, 2, 5, 1, 4, 6, 2, 7, 8, 3, 3, 3]) [:1] == [0]  # trikona (0,4,8): 3,4,8 -> subtract 3 -> 0,1,5
    assert trikona_shodhana([0, 2, 5, 1, 4, 6, 2, 7, 8, 3, 3, 3])[0] == 0      # zero present: unchanged
    v = [0] * 12
    v[0], v[7] = 5, 3
    assert ekadhipatya_shodhana(v, set())[0] == 2 and ekadhipatya_shodhana(v, set())[7] == 0  # both empty
    assert ekadhipatya_shodhana(v, {0, 7})[0] == 5                                              # both occupied
    assert ekadhipatya_shodhana(v, {7})[0] == 3                                                 # empty capped at occupied
