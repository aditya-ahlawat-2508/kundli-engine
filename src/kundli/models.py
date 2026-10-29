"""Core data models."""
from datetime import date, datetime, time
from typing import Any

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


class PlanetData(BaseModel):
    """One graha in the natal chart."""

    model_config = ConfigDict(frozen=True)

    name: str
    tropical_lon: float
    sidereal_lon: float
    lat: float
    speed: float
    retrograde: bool
    sign: int
    sign_name: str
    degree_in_sign: float
    nakshatra: int
    nakshatra_name: str
    pada: int
    nakshatra_lord: str
    sub_lord: str
    house: int | None  # configured house system; None when birth time unknown
    rashi_house: int | None  # whole-sign house
    bhava_chalit_house: int | None
    combust: bool
    dignity: str
    vargottama: bool
    war: str | None  # "won vs X" / "lost vs X" (graha yuddha)
    lord_of_houses: list[int]
    varga_signs: dict[str, int]


class Kundli(BaseModel):
    """Complete, JSON-serialisable result. Contains no clock-dependent data."""

    header: dict[str, Any]
    birth: dict[str, Any]
    lagna: dict[str, Any] | None
    houses: dict[str, Any] | None
    planets: list[PlanetData]
    bhava_chalit: dict[str, Any] | None = None
    special_lagnas: dict[str, Any] | None = None
    upagrahas: dict[str, Any] | None = None
    panchang: dict[str, Any] | None = None
    aspects: dict[str, Any] = {}
    vargas: dict[str, Any] = {}
    chandra_chart: dict[str, Any] | None = None
    surya_chart: dict[str, Any] | None = None
    dashas: dict[str, Any] = {}
    shadbala: dict[str, Any] | None = None
    bhavabala: dict[str, Any] | None = None
    ashtakavarga: dict[str, Any] | None = None
    vimshopaka: dict[str, Any] | None = None
    ishta_kashta: dict[str, Any] | None = None
    yogas: list[dict[str, Any]] = []
    jaimini: dict[str, Any] | None = None
    outer_planets: list[dict[str, Any]] = []
    friendship: dict[str, Any] | None = None
    avakahada: dict[str, Any] | None = None
    kp: dict[str, Any] | None = None
    functional_nature: dict[str, str] | None = None
    gemstones: list[dict[str, Any]] | None = None
    numerology: dict[str, Any] | None = None
    doshas: dict[str, Any] | None = None
    notes: list[str] = []
