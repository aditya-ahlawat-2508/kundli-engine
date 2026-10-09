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

    @field_validator("dasha_year_days")
    @classmethod
    def _year(cls, v: float) -> float:
        if v not in (365.25, 360.0):
            raise ValueError("dasha_year_days must be 365.25 or 360")
        return v
