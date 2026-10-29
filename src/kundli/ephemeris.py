"""Planet positions via Swiss Ephemeris. Moshier built-in by default."""
from functools import lru_cache
from typing import Any

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


@lru_cache(maxsize=65536)
def _calc_cached(body: int, jd_ut: float, flags: int, sid: int, path: str) -> tuple[float, float, float]:
    """Cached swisseph call, keyed on everything it depends on: body, JD, flags, sidereal mode and ephemeris path
    (swisseph keeps the last two in process-global state, so they are set here from the key)."""
    swe.set_sid_mode(sid)
    if path:
        swe.set_ephe_path(path)
    xx, _ = swe.calc_ut(jd_ut, body, flags | swe.FLG_SPEED)
    return xx[0], xx[1], xx[3]


def _calc(body: int, jd_ut: float, flags: int, sid: int = 0, path: str = "") -> tuple[float, float, float]:
    """Return (lon, lat, lon_speed) in degrees; raises if swisseph signals an error."""
    return _calc_cached(body, jd_ut, flags, sid, path)


def cache_info() -> Any:
    return _calc_cached.cache_info()


def clear_cache() -> None:
    _calc_cached.cache_clear()


def planet_positions(jd_ut: float, cfg: EngineConfig) -> list[PlanetPosition]:
    """Sun..Saturn, Rahu, Ketu (+ outer planets if configured).

    Tropical and sidereal longitudes come from separate swisseph calls (the sidereal one
    via FLG_SIDEREAL with the configured ayanamsa). Ketu = Rahu + 180 exactly.
    Retrograde = negative longitudinal speed (nodes are always retrograde for mean node;
    true node is flagged by its own speed).
    """
    base = base_flags(cfg)
    sid, path = sid_mode(cfg.ayanamsa), (cfg.ephemeris_path or "") if cfg.ephemeris == "swiss_files" else ""
    swe.set_sid_mode(sid)
    bodies = dict(PLANET_IDS)
    node_body = swe.TRUE_NODE if cfg.node_type == "true" else swe.MEAN_NODE
    out: list[PlanetPosition] = []

    def make(name: str, body: int) -> PlanetPosition:
        t_lon, _, _ = _calc(body, jd_ut, base, sid, path)
        s_lon, s_lat, s_spd = _calc(body, jd_ut, base | swe.FLG_SIDEREAL, sid, path)
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


__all__ = ["ayanamsa_ut", "cache_info", "clear_cache", "planet_positions"]
