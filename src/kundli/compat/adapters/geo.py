"""Geo endpoints (V2 phase 23): place lookup from the offline GeoNames index and time-zone/DST details from the IANA rules.
They take their own small request models (no birth chart is generated)."""
from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from ...errors import PlaceNotFound
from ...geo import candidates, resolve_place
from ...service import parse_time
from ...tzinfo_lookup import timezone_details, zone_at


class GeoRequest(BaseModel):
    place: str = Field(min_length=2, max_length=200)
    limit: int = Field(default=15, ge=1, le=50)


class TimezoneRequest(BaseModel):
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    place: str | None = Field(default=None, max_length=200)
    place_choice: int | None = Field(default=None, ge=0, le=100)
    date: str = Field(max_length=32)
    time: str | None = Field(default=None, max_length=32)
    fold: int | None = Field(default=None, ge=0, le=1)


def geo_details(req: GeoRequest) -> Any:
    found = candidates(req.place, online=False)  # offline only: deterministic, no third-party call
    if not found:
        raise PlaceNotFound(req.place)
    return {"query": req.place, "count": len(found), "places": [{"index": i, **p.model_dump()} for i, p in enumerate(found[: req.limit])]}


def timezone_with_dst(req: TimezoneRequest) -> Any:
    if req.lat is not None and req.lon is not None:
        tz, lat, lon, name = zone_at(req.lat, req.lon), req.lat, req.lon, None
        if tz is None:
            raise ValueError("no time zone covers these coordinates")
    elif req.place:
        p = resolve_place(req.place, choice=req.place_choice, online=False)
        tz, lat, lon, name = p.tz, p.lat, p.lon, p.name
    else:
        raise ValueError("give lat and lon, or a place")
    return {"lat": lat, "lon": lon, "place": name, **timezone_details(tz, date.fromisoformat(req.date), parse_time(req.time), req.fold)}


SIMPLE_ADAPTERS: dict[str, tuple[type[BaseModel], Any]] = {
    "geo_details": (GeoRequest, geo_details),
    "timezone_with_dst": (TimezoneRequest, timezone_with_dst),
}
