"""Core chart computation shared by every analysis module (strength, yogas, jaimini...)."""
from dataclasses import dataclass, field

from .config import EngineConfig
from .data.tables import COMBUST_ORBS, COMBUST_ORBS_RETRO, PLANETS, SIGN_LORDS
from .dignity import compound_relation, dignity
from .ephemeris import planet_positions
from .houses import HouseSet, compute_houses, house_of, sripati_starts, whole_sign_house
from .models import BirthInput, BirthMoment, PlanetPosition
from .nakshatra import nakshatra_index, nakshatra_lord, pada, sub_lord
from .panchang import sun_events, vara_index
from .timeutil import resolve_birth
from .vargas import VARGAS, is_vargottama


def angdiff(a: float, b: float) -> float:
    """Smallest angular distance in degrees (0..180)."""
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


@dataclass
class Core:
    cfg: EngineConfig
    birth: BirthInput
    moment: BirthMoment
    pos: dict[str, PlanetPosition]
    houses: HouseSet | None
    lon: dict[str, float]
    sign: dict[str, int]
    deg: dict[str, float]
    lagna_sign: int | None
    rashi_house: dict[str, int | None]
    house: dict[str, int | None]
    chalit_house: dict[str, int | None]
    dignity: dict[str, str]
    combust: dict[str, bool]
    war: dict[str, str | None]
    varga: dict[str, dict[str, int]]          # varga -> planet -> sign (includes "Lagna" when known)
    lords_of: dict[str, list[int]]            # planet -> houses it rules (whole sign)
    sun_ev: dict | None
    day_idx: int | None
    notes: list[str] = field(default_factory=list)

    def sign_of_house(self, h: int) -> int:
        assert self.lagna_sign is not None
        return (self.lagna_sign + h - 1) % 12

    def lord_of_house(self, h: int) -> str:
        return SIGN_LORDS[self.sign_of_house(h)]

    def house_from(self, p: str, ref: str) -> int:
        """House of planet p counted from planet/point ref (ref may be 'Lagna')."""
        rs = self.lagna_sign if ref == "Lagna" else self.sign[ref]
        assert rs is not None
        return (self.sign[p] - rs) % 12 + 1


def build_core(birth: BirthInput, cfg: EngineConfig) -> Core:
    m = resolve_birth(birth)
    plist = planet_positions(m.jd_ut, cfg)
    pos = {p.name: p for p in plist}
    lon = {n: p.sidereal_lon for n, p in pos.items()}
    sign = {n: int(v // 30) for n, v in lon.items()}
    deg = {n: v - sign[n] * 30.0 for n, v in lon.items()}
    notes: list[str] = []
    hs: HouseSet | None = None
    lagna_sign: int | None = None
    if m.time_unknown:
        notes.append("Birth time unknown: local noon used; lagna, houses and lagna-dependent outputs omitted. "
                     "Moon-based results may be off by up to ~6 degrees.")
    else:
        hs = compute_houses(m.jd_ut, birth.place.lat, birth.place.lon, cfg)
        lagna_sign = int(hs.asc // 30)
        if hs.fallback:
            notes.append(hs.fallback)

    rashi_house: dict[str, int | None] = {}
    house: dict[str, int | None] = {}
    chalit: dict[str, int | None] = {}
    for n in lon:
        if hs is None or lagna_sign is None:
            rashi_house[n] = house[n] = chalit[n] = None
            continue
        rashi_house[n] = whole_sign_house(sign[n], lagna_sign)
        house[n] = house_of(lon[n], hs.starts)
        chalit[n] = house_of(lon[n], sripati_starts(list(hs.madhyas)))

    dig = {n: dignity(n, sign[n], deg[n], sign) for n in PLANETS}

    # Combustion: within orb of the Sun (Mercury/Venus use smaller orb when retrograde).
    combust: dict[str, bool] = {}
    for n in PLANETS:
        if n in COMBUST_ORBS:
            orb = COMBUST_ORBS_RETRO.get(n, COMBUST_ORBS[n]) if pos[n].retrograde else COMBUST_ORBS[n]
            combust[n] = angdiff(lon[n], lon["Sun"]) < orb
        else:
            combust[n] = False

    # Graha yuddha: two of Mars..Saturn within 1 degree of longitude; the more northern (higher latitude) wins.
    war: dict[str, str | None] = dict.fromkeys(PLANETS, None)
    wp = ["Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
    for i, a in enumerate(wp):
        for b in wp[i + 1:]:
            if angdiff(lon[a], lon[b]) < 1.0:
                w, l_ = (a, b) if pos[a].lat >= pos[b].lat else (b, a)
                war[w], war[l_] = f"won vs {l_}", f"lost vs {w}"

    varga: dict[str, dict[str, int]] = {}
    for vn, fn in VARGAS.items():
        varga[vn] = {n: fn(lon[n])[0] for n in PLANETS}
        if hs is not None:
            varga[vn]["Lagna"] = fn(hs.asc)[0]

    lords_of: dict[str, list[int]] = {n: [] for n in PLANETS}
    if lagna_sign is not None:
        for h in range(1, 13):
            lords_of[SIGN_LORDS[(lagna_sign + h - 1) % 12]].append(h)

    ev = sun_events(m.jd_ut, birth.place.lat, birth.place.lon)
    day_idx = vara_index(ev["sunrise"], birth.place.tz) if ev else None
    return Core(cfg, birth, m, pos, hs, lon, sign, deg, lagna_sign, rashi_house, house, chalit, dig, combust,
                war, varga, lords_of, ev, day_idx, notes)


def relation(core: Core, a: str, b: str) -> str:
    """Compound relation of a toward b using their natal (D1) signs."""
    return compound_relation(a, b, core.sign[a], core.sign[b])


__all__ = [
    "Core",
    "angdiff",
    "build_core",
    "is_vargottama",
    "nakshatra_index",
    "nakshatra_lord",
    "pada",
    "relation",
    "sub_lord",
]
