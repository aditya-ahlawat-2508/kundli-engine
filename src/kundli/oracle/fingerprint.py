"""Find which convention variant an oracle used, by running the engine under each variant and scoring the fit.
Example: the sample report's Rahu only matches node_type='mean'."""
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..ayanamsa import AYANAMSA_MODES
from ..config import EngineConfig
from ..dasha import vimshottari
from ..ephemeris import planet_positions
from ..models import BirthInput
from ..timeutil import resolve_birth


@dataclass(frozen=True)
class Variant:
    name: str
    overrides: dict[str, Any]

    def config(self) -> EngineConfig:
        return EngineConfig(**self.overrides)


@dataclass(frozen=True)
class Fit:
    variant: Variant
    max_error: float
    mean_error: float


def position_variants() -> list[Variant]:
    return [Variant(f"{ay}/{node}", {"ayanamsa": ay, "node_type": node}) for ay in AYANAMSA_MODES for node in ("mean", "true")]


def dasha_variants() -> list[Variant]:
    return [Variant(f"year={y}", {"dasha_year_days": y}) for y in (365.25, 360.0)]


def rank(variants: Iterable[Variant], score: Callable[[Variant], tuple[float, float]]) -> list[Fit]:
    """score(variant) -> (max_error, mean_error); lower is better. Returns fits best first (ties by name)."""
    fits = [Fit(v, *score(v)) for v in variants]
    return sorted(fits, key=lambda f: (round(f.mean_error, 9), f.variant.name))


def _circ(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def fingerprint_positions(birth: BirthInput, expected_sidereal: dict[str, float],
                          variants: Iterable[Variant] | None = None) -> list[Fit]:
    """Rank ayanamsa/node variants by agreement with the oracle's sidereal longitudes (degrees)."""
    jd = resolve_birth(birth).jd_ut

    def score(v: Variant) -> tuple[float, float]:
        pos = {p.name: p.sidereal_lon for p in planet_positions(jd, v.config())}
        errs = [_circ(pos[n], lon) for n, lon in expected_sidereal.items() if n in pos]
        return (max(errs), sum(errs) / len(errs)) if errs else (float("inf"), float("inf"))

    return rank(variants or position_variants(), score)


def fingerprint_dasha(birth: BirthInput, expected_starts: list[tuple[str, str]],
                      variants: Iterable[Variant] | None = None) -> list[Fit]:
    """Rank dasha year-length variants by the error (days) of the oracle's maha dasha start dates."""
    m = resolve_birth(birth)
    from ..ephemeris import planet_positions as pp
    from ..nakshatra import nakshatra_index  # noqa: F401  (documents the dependency on the Moon's nakshatra)

    def score(v: Variant) -> tuple[float, float]:
        cfg = v.config()
        moon = next(p.sidereal_lon for p in pp(m.jd_ut, cfg) if p.name == "Moon")
        tree = vimshottari.tree(moon, m.utc, cfg.dasha_year_days, 1, birth.place.tz)
        errs = []
        for (lord, day), node in zip(expected_starts, tree, strict=False):
            got = datetime.fromisoformat(node["start_local"][:19])
            errs.append(abs((got - datetime.fromisoformat(day)).total_seconds()) / 86400.0 if node["lord"] == lord else 1e6)
        return (max(errs), sum(errs) / len(errs)) if errs else (float("inf"), float("inf"))

    return rank(variants or dasha_variants(), score)
