"""Engine configuration. Frozen and hashable; echoed in every output."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AyanamsaName = Literal["lahiri", "raman", "kp", "true_chitra", "fagan_bradley", "yukteshwar", "jn_bhasin"]


class EngineConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ayanamsa: AyanamsaName = "lahiri"
    node_type: Literal["mean", "true"] = "true"
    house_system: Literal["whole_sign", "equal", "sripati", "placidus", "kp"] = "whole_sign"
    zodiac: Literal["sidereal"] = "sidereal"
    ephemeris: Literal["moshier", "swiss_files"] = "moshier"
    ephemeris_path: str | None = None  # directory with .se1 files when ephemeris="swiss_files"
    dasha_year_days: float = Field(default=365.25, description="365.25 (julian) or 360 (savana)")
    dasha_levels: int = 4
    rounding_arcsec: int = 1
    combustion_orbs: Literal["standard"] = "standard"
    language: Literal["en", "hi"] = "en"
    include_outer_planets: bool = False  # Uranus/Neptune/Pluto extras
    # Conventions added for the API-compat layer (V2). Each currently has one value = today's behaviour; the Literal
    # is widened in the phase that implements an alternative (see docs/conventions.md).
    sunrise_definition: Literal["upper_limb_refracted", "center_no_refraction"] = "upper_limb_refracted"
    observer_altitude_m: float = Field(default=0.0, ge=-500.0, le=9000.0)  # metres above sea level, for rise/set
    festival_tradition: Literal["drik_amanta", "drik_purnimanta"] = "drik_amanta"
    kp_ayanamsa: Literal["chart", "kp"] = "chart"  # KP endpoints: use the chart's ayanamsa, or Krishnamurti's
    manglik_rules: Literal["lagna_only", "lagna_moon", "lagna_moon_venus"] = "lagna_moon_venus"
    manglik_cancellations: Literal["standard_v1"] = "standard_v1"
    kalsarpa_variant: Literal["full_only", "include_partial"] = "full_only"
    solar_return_zodiac: Literal["sidereal", "tropical"] = "sidereal"  # which Sun longitude must return
    mudda_dasha_basis: Literal["annual_moon", "natal_vimshottari"] = "annual_moon"
    muhurta_ruleset_version: Literal["v1"] = "v1"
    numerology_system: Literal["chaldean", "pythagorean"] = "chaldean"
    lalkitab_edition: Literal["lagna_houses", "fixed_aries"] = "fixed_aries"  # see docs/conventions.md
    content_version: str | None = None  # hash of the frozen content store once one exists

    @field_validator("dasha_year_days")
    @classmethod
    def _year(cls, v: float) -> float:
        if v not in (365.25, 360.0):
            raise ValueError("dasha_year_days must be 365.25 or 360")
        return v
