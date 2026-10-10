"""Ascendant, MC and house cusps (sidereal). Whole Sign default."""
from dataclasses import dataclass

import swisseph as swe

from .ayanamsa import sid_mode
from .config import EngineConfig

_HSYS = {"equal": b"E", "placidus": b"P", "kp": b"P", "sripati": b"O"}  # sripati built from Porphyry 'O'


@dataclass(frozen=True)
class HouseSet:
    asc: float
    mc: float
    starts: tuple[float, ...]   # 12 house-start longitudes of the configured system
    madhyas: tuple[float, ...]  # 12 bhava-madhya longitudes (Sripati: Porphyry cusps)
    system_used: str
    fallback: str | None        # reason if the requested system could not be computed


def _raw(jd_ut: float, lat: float, lon: float, hsys: bytes, cfg: EngineConfig) -> tuple[list[float], list[float]]:
    swe.set_sid_mode(sid_mode(cfg.ayanamsa))
    cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, hsys, swe.FLG_SIDEREAL)
    return list(cusps), list(ascmc)


def sripati_starts(madhyas: list[float]) -> list[float]:
    """Sripati bhava sandhis: house i starts at the midpoint of madhyas i-1 and i."""
    out = []
    for i in range(12):
        a, b = madhyas[i - 1], madhyas[i]
        out.append((a + ((b - a) % 360.0) / 2.0) % 360.0)
    return out


def compute_houses(jd_ut: float, lat: float, lon: float, cfg: EngineConfig) -> HouseSet:
    """Asc/MC plus house boundaries for cfg.house_system.

    whole_sign: houses start at 0deg of the ascendant's sign. equal: start at the ascendant degree.
    sripati: Porphyry cusps are madhyas, boundaries are midpoints. placidus/kp: Placidus cusps as starts;
    above the polar circle Placidus fails and Equal houses are used (fallback flag set).
    """
    por, ascmc = _raw(jd_ut, lat, lon, b"O", cfg)  # Porphyry never fails: gives asc/mc + madhyas
    asc, mc = ascmc[0] % 360.0, ascmc[1] % 360.0
    madhyas = tuple(c % 360.0 for c in por)
    system, fallback = cfg.house_system, None
    if system == "whole_sign":
        s0 = int(asc // 30) * 30.0
        starts = tuple((s0 + 30.0 * i) % 360.0 for i in range(12))
    elif system == "equal":
        starts = tuple((asc + 30.0 * i) % 360.0 for i in range(12))
    elif system == "sripati":
        starts = tuple(sripati_starts([*madhyas]))
    else:
        try:
            cusps, _ = _raw(jd_ut, lat, lon, _HSYS[system], cfg)
            starts = tuple(c % 360.0 for c in cusps)
        except swe.Error:
            fallback = f"{system} unavailable at latitude {lat:.2f}; used equal houses"
            system = "equal"
            starts = tuple((asc + 30.0 * i) % 360.0 for i in range(12))
    return HouseSet(asc, mc, starts, madhyas, system, fallback)


def house_of(lon: float, starts: tuple[float, ...] | list[float]) -> int:
    """1..12: the house whose span [start_i, start_{i+1}) contains lon."""
    for i in range(12):
        a, b = starts[i], starts[(i + 1) % 12]
        if (lon - a) % 360.0 < (b - a) % 360.0:
            return i + 1
    return 12


def whole_sign_house(sign: int, lagna_sign: int) -> int:
    return (sign - lagna_sign) % 12 + 1
