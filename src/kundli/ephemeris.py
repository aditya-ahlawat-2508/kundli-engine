"""Planet positions via Swiss Ephemeris. Moshier built-in by default."""
import swisseph as swe

from .ayanamsa import ayanamsa_ut, sid_mode
from .config import EngineConfig
from .models import PlanetPosition

PLANET_IDS: dict[str, int] = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
}
OUTER_IDS: dict[str, int] = {"Uranus": swe.URANUS, "Neptune": swe.NEPTUNE, "Pluto": swe.PLUTO}


def base_flags(cfg: EngineConfig) -> int:
    if cfg.ephemeris == "moshier":
        return swe.FLG_MOSEPH
    swe.set_ephe_path(cfg.ephemeris_path or "")
    return swe.FLG_SWIEPH


def _calc(body: int, jd_ut: float, flags: int) -> tuple[float, float, float]:
    """Return (lon, lat, lon_speed) in degrees; raises if swisseph signals an error."""
    xx, _ = swe.calc_ut(jd_ut, body, flags | swe.FLG_SPEED)
    return xx[0], xx[1], xx[3]


def planet_positions(jd_ut: float, cfg: EngineConfig) -> list[PlanetPosition]:
    """Sun..Saturn, Rahu, Ketu (+ outer planets if configured).

    Tropical and sidereal longitudes come from separate swisseph calls (the sidereal one
    via FLG_SIDEREAL with the configured ayanamsa). Ketu = Rahu + 180 exactly.
    Retrograde = negative longitudinal speed (nodes are always retrograde for mean node;
    true node is flagged by its own speed).
    """
    base = base_flags(cfg)
    swe.set_sid_mode(sid_mode(cfg.ayanamsa))
    bodies = dict(PLANET_IDS)
    node_body = swe.TRUE_NODE if cfg.node_type == "true" else swe.MEAN_NODE
    out: list[PlanetPosition] = []

    def make(name: str, body: int) -> PlanetPosition:
        t_lon, _, _ = _calc(body, jd_ut, base)
        s_lon, s_lat, s_spd = _calc(body, jd_ut, base | swe.FLG_SIDEREAL)
        return PlanetPosition(
            name=name, tropical_lon=t_lon % 360.0, sidereal_lon=s_lon % 360.0,
            lat=s_lat, speed=s_spd, retrograde=s_spd < 0,
        )

    for name, body in bodies.items():
        out.append(make(name, body))
    rahu = make("Rahu", node_body)
    out.append(rahu)
    out.append(PlanetPosition(
        name="Ketu",
        tropical_lon=(rahu.tropical_lon + 180.0) % 360.0,
        sidereal_lon=(rahu.sidereal_lon + 180.0) % 360.0,
        lat=-rahu.lat, speed=rahu.speed, retrograde=rahu.retrograde,
    ))
    if cfg.include_outer_planets:
        for name, body in OUTER_IDS.items():
            out.append(make(name, body))
    return out


__all__ = ["ayanamsa_ut", "planet_positions"]
