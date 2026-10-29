"""Timezone lookups for the Geo endpoints: IANA zone for a coordinate (timezonefinder), and the UTC offset, DST state and
the year's DST transitions of a zone at a local date/time, from the historical IANA rules (zoneinfo / tzdata)."""
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .geo import _tzf
from .timeutil import _classify


def zone_at(lat: float, lon: float) -> str | None:
    """IANA zone name containing (lat, lon), or None over open ocean outside any zone."""
    return _tzf().timezone_at(lat=lat, lng=lon)


def _offset(tz: ZoneInfo, utc: datetime) -> int:
    off = utc.astimezone(tz).utcoffset()
    assert off is not None
    return int(off.total_seconds())


def transitions(tz_name: str, year: int) -> list[dict[str, Any]]:
    """UTC offset changes during calendar `year` (found by a daily scan, then bisected to the second)."""
    tz = ZoneInfo(tz_name)
    out: list[dict[str, Any]] = []
    day = datetime(year, 1, 1, tzinfo=UTC)
    prev = _offset(tz, day)
    while day.year == year:
        nxt = day + timedelta(days=1)
        cur = _offset(tz, nxt)
        if cur != prev:
            lo, hi = day, nxt
            while (hi - lo).total_seconds() > 1:
                mid = lo + (hi - lo) / 2
                lo, hi = (mid, hi) if _offset(tz, mid) == prev else (lo, mid)
            at = hi.replace(microsecond=0)
            out.append({"utc": at.isoformat(), "local_after": at.astimezone(tz).replace(tzinfo=None).isoformat(),
                        "offset_before_seconds": prev, "offset_after_seconds": cur,
                        "kind": "dst_start" if cur > prev else "dst_end_or_offset_decrease"})
        day, prev = nxt, cur
    return out


def timezone_details(tz_name: str, d: date, t: time | None = None, fold: int | None = None) -> dict[str, Any]:
    """Offset, DST and abbreviation at the local date/time (noon when no time is given). A time inside a DST gap is
    `nonexistent`; one that occurs twice is `ambiguous` (pass fold 0/1 to choose); both are reported, never guessed."""
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise ValueError(f"unknown time zone {tz_name!r}") from e
    local = datetime.combine(d, t or time(12, 0))
    kind = _classify(local, tz)
    aware = local.replace(tzinfo=tz, fold=fold or 0)
    off = aware.utcoffset()
    dst = aware.dst() or timedelta(0)
    assert off is not None
    return {"timezone": tz_name, "local": local.isoformat(), "kind": {"ok": "ok", "overlap": "ambiguous", "gap": "nonexistent"}[kind],
            "fold_used": aware.fold, "utc_offset_seconds": int(off.total_seconds()), "dst_offset_seconds": int(dst.total_seconds()),
            "is_dst": dst != timedelta(0), "standard_offset_seconds": int((off - dst).total_seconds()), "abbreviation": aware.tzname(),
            "transitions_in_year": transitions(tz_name, d.year)}


__all__ = ["timezone_details", "transitions", "zone_at"]
