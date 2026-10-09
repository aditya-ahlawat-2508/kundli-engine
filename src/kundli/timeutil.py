"""Local civil time -> UTC -> Julian Day, historical-timezone safe."""
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import swisseph as swe

from .errors import AmbiguousLocalTime, NonexistentLocalTime
from .models import BirthInput, BirthMoment

NOON = time(12, 0)


def _classify(naive: datetime, tz: ZoneInfo) -> str:
    """Return 'ok', 'overlap' or 'gap' for a naive local time in tz."""
    a = naive.replace(tzinfo=tz, fold=0)
    b = naive.replace(tzinfo=tz, fold=1)
    if a.utcoffset() == b.utcoffset():
        return "ok"
    # Offsets differ: in a gap fold=0 uses the pre-transition offset, so the round trip
    # through UTC does not return the same wall time. In an overlap it does.
    rt = a.astimezone(UTC).astimezone(tz).replace(tzinfo=None)
    return "overlap" if rt == naive else "gap"


def local_to_utc(local: datetime, tz_name: str, fold: int | None = None) -> tuple[datetime, int]:
    """Convert naive local civil time to (aware UTC datetime, utc offset seconds).

    Uses the IANA database including historical rules (e.g. India's 1942-45 war time,
    pre-1906 Kolkata LMT). DST overlaps raise AmbiguousLocalTime unless `fold` is given;
    DST gaps always raise NonexistentLocalTime.
    """
    if local.tzinfo is not None:
        raise ValueError("local must be naive")
    tz = ZoneInfo(tz_name)
    kind = _classify(local, tz)
    if kind == "gap":
        raise NonexistentLocalTime(f"{local} does not exist in {tz_name} (DST gap)")
    if kind == "overlap" and fold is None:
        raise AmbiguousLocalTime(f"{local} occurs twice in {tz_name}; pass fold=0 or fold=1")
    aware = local.replace(tzinfo=tz, fold=fold or 0)
    off = aware.utcoffset()
    assert off is not None
    return aware.astimezone(UTC), int(off.total_seconds())


def julian_day(utc: datetime) -> tuple[float, float]:
    """Return (jd_et, jd_ut) for an aware UTC datetime (Gregorian, delta-T via swisseph)."""
    sec = utc.second + utc.microsecond / 1e6
    jd_et, jd_ut = swe.utc_to_jd(utc.year, utc.month, utc.day, utc.hour, utc.minute, sec, swe.GREG_CAL)
    return jd_et, jd_ut


def resolve_birth(b: BirthInput) -> BirthMoment:
    """BirthInput -> BirthMoment. Unknown time uses local noon and sets time_unknown."""
    unknown = b.time is None
    local = datetime.combine(b.date, NOON if unknown else b.time)  # type: ignore[arg-type]
    utc, off = local_to_utc(local, b.place.tz, b.fold)
    jd_et, jd_ut = julian_day(utc)
    return BirthMoment(local=local, utc=utc, utc_offset_seconds=off, jd_ut=jd_ut, jd_et=jd_et, time_unknown=unknown)


def jd_to_utc(jd_ut: float) -> datetime:
    """Julian Day (UT) -> aware UTC datetime (microsecond precision)."""
    y, mo, d, h, mi, s = swe.jdut1_to_utc(jd_ut, swe.GREG_CAL)
    whole = int(s)
    return datetime(y, mo, d, h, mi, whole, tzinfo=UTC) + timedelta(microseconds=round((s - whole) * 1e6))


__all__ = ["date", "jd_to_utc", "julian_day", "local_to_utc", "resolve_birth"]
