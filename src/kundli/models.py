"""Core data models."""
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict


class Place(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    admin1: str = ""
    country: str = ""
    lat: float
    lon: float
    tz: str
    population: int = 0
    source: str = "geonames"  # geonames | nominatim | manual


class BirthInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    date: date
    time: time | None  # None => time unknown (noon is used, lagna outputs are skipped)
    place: Place
    fold: int | None = None  # 0/1 to disambiguate a DST-overlap local time


class BirthMoment(BaseModel):
    """Resolved instant of birth."""

    model_config = ConfigDict(frozen=True)

    local: datetime  # naive local civil time as given
    utc: datetime  # aware UTC
    utc_offset_seconds: int
    jd_ut: float
    jd_et: float
    time_unknown: bool = False


class PlanetPosition(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    tropical_lon: float
    sidereal_lon: float
    lat: float
    speed: float  # deg/day, sidereal longitude speed
    retrograde: bool
