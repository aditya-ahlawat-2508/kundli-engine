"""Request normaliser: loose request fields -> (BirthInput, EngineConfig). Field names here are engine-neutral;
provider-specific names are mapped per group in adapters once the provider's schemas are available."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..config import EngineConfig
from ..models import BirthInput
from ..service import aware, make_birth

FORBIDDEN_CONFIG = {"ephemeris_path"}


class BirthRequest(BaseModel):
    name: str = "unknown"
    date: str  # YYYY-MM-DD
    time: str | None = None  # HH:MM[:SS]; null/'unknown' = time unknown
    place: str | None = None
    place_choice: int | None = None
    fold: int | None = None
    lat: float | None = None
    lon: float | None = None
    tz: str | None = None  # IANA zone name
    config: dict[str, Any] = {}
    end_date: str | None = None  # muhurta: last date of the scan (default: 30 days from `date`)
    natal: "BirthRequest | None" = None  # muhurta: birth chart for Tarabala / Chandrabala
    direction: str | None = None  # muhurta travel: east | south | west | north
    year: int | None = None  # varshaphal year (defaults to the year of as_of)
    month: int | None = Field(default=None, ge=1, le=12)  # varshaphal month 1..12
    as_of: str | None = None  # ISO date/datetime; the engine never reads the clock
    levels: int = 5


BirthRequest.model_rebuild()


def engine_config(raw: dict[str, Any]) -> EngineConfig:
    """Client-supplied config; the filesystem path and Swiss-file mode are server-side decisions only."""
    bad = FORBIDDEN_CONFIG & set(raw) or (["ephemeris=swiss_files"] if raw.get("ephemeris") == "swiss_files" else [])
    if bad:
        raise ValueError(f"config not allowed from clients: {sorted(bad)}")
    return EngineConfig(**raw)


def to_inputs(req: BirthRequest) -> tuple[BirthInput, EngineConfig]:
    cfg = engine_config(req.config)
    birth = make_birth(req.name, req.date, req.time, req.place, req.place_choice, req.fold, req.lat, req.lon, req.tz)
    return birth, cfg


def as_of_dt(req: BirthRequest) -> datetime:
    if not req.as_of:
        raise ValueError("as_of is required for this endpoint (the engine never reads the clock)")
    return aware(req.as_of)


class MatchRequest(BaseModel):
    """Two partners; `config` applies to both (each partner's own `config` field is ignored)."""

    boy: BirthRequest
    girl: BirthRequest
    config: dict[str, Any] = {}


def to_match_inputs(req: MatchRequest) -> tuple[BirthInput, BirthInput, EngineConfig]:
    cfg = engine_config(req.config)
    return (make_birth(req.boy.name, req.boy.date, req.boy.time, req.boy.place, req.boy.place_choice, req.boy.fold,
                       req.boy.lat, req.boy.lon, req.boy.tz),
            make_birth(req.girl.name, req.girl.date, req.girl.time, req.girl.place, req.girl.place_choice,
                       req.girl.fold, req.girl.lat, req.girl.lon, req.girl.tz), cfg)
