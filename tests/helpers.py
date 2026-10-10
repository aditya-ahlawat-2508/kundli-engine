"""Build a Core from hand-specified signs so yoga rules can be checked against hand-worked charts."""
from datetime import date, time

from kundli.config import EngineConfig
from kundli.core import Core
from kundli.data.tables import PLANETS, SIGN_LORDS
from kundli.dignity import dignity
from kundli.houses import whole_sign_house
from kundli.models import BirthInput, BirthMoment, Place, PlanetPosition

DEFAULT = {"Sun": 4, "Moon": 3, "Mars": 2, "Mercury": 2, "Jupiter": 11, "Venus": 11, "Saturn": 10, "Rahu": 0, "Ketu": 6}


def make_core(lagna: int, signs: dict[str, int], degs: dict[str, float] | None = None) -> Core:
    s = {**DEFAULT, **signs}
    s["Ketu"] = (s["Rahu"] + 6) % 12
    d = {p: 15.0 for p in PLANETS} | (degs or {})
    lon = {p: s[p] * 30.0 + d[p] for p in PLANETS}
    pos = {p: PlanetPosition(name=p, tropical_lon=lon[p], sidereal_lon=lon[p], lat=0.0, speed=1.0, retrograde=False)
           for p in PLANETS}
    place = Place(name="x", lat=0, lon=0, tz="UTC")
    birth = BirthInput(name="t", date=date(2000, 1, 1), time=time(0, 0), place=place)
    from datetime import UTC, datetime
    m = BirthMoment(local=datetime(2000, 1, 1), utc=datetime(2000, 1, 1, tzinfo=UTC), utc_offset_seconds=0,
                    jd_ut=2451544.5, jd_et=2451544.5)
    dig = {p: dignity(p, s[p], d[p], s) for p in PLANETS}
    lords_of: dict[str, list[int]] = {p: [] for p in PLANETS}
    for h in range(1, 13):
        lords_of[SIGN_LORDS[(lagna + h - 1) % 12]].append(h)
    rh = {p: whole_sign_house(s[p], lagna) for p in PLANETS}
    return Core(EngineConfig(), birth, m, pos, None, lon, s, d, lagna, rh, dict(rh), dict(rh), dig,
                dict.fromkeys(PLANETS, False), dict.fromkeys(PLANETS), {}, lords_of, None, None)
