"""Deterministic birth-input generator for oracle fixtures and engine robustness runs."""
import random
from datetime import date, timedelta
from typing import Any

PLACES = [
    ("Delhi", 28.6139, 77.2090, "Asia/Kolkata"), ("Mumbai", 19.0760, 72.8777, "Asia/Kolkata"),
    ("Kolkata", 22.5726, 88.3639, "Asia/Kolkata"), ("Chennai", 13.0827, 80.2707, "Asia/Kolkata"),
    ("Agra", 27.1767, 78.0081, "Asia/Kolkata"), ("Pune", 18.5196, 73.8554, "Asia/Kolkata"),
    ("Meerut", 28.9800, 77.7064, "Asia/Kolkata"), ("Lucknow", 26.8467, 80.9462, "Asia/Kolkata"),
    ("Bengaluru", 12.9716, 77.5946, "Asia/Kolkata"), ("Kathmandu", 27.7172, 85.3240, "Asia/Kathmandu"),
    ("Colombo", 6.9271, 79.8612, "Asia/Colombo"), ("Dhaka", 23.8103, 90.4125, "Asia/Dhaka"),
    ("Karachi", 24.8607, 67.0011, "Asia/Karachi"), ("London", 51.5074, -0.1278, "Europe/London"),
    ("New York", 40.7128, -74.0060, "America/New_York"), ("Los Angeles", 34.0522, -118.2437, "America/Los_Angeles"),
    ("Toronto", 43.6532, -79.3832, "America/Toronto"), ("Sydney", -33.8688, 151.2093, "Australia/Sydney"),
    ("Auckland", -36.8485, 174.7633, "Pacific/Auckland"),
    ("Buenos Aires", -34.6037, -58.3816, "America/Argentina/Buenos_Aires"),
    ("Sao Paulo", -23.5505, -46.6333, "America/Sao_Paulo"), ("Johannesburg", -26.2041, 28.0473, "Africa/Johannesburg"),
    ("Nairobi", -1.2921, 36.8219, "Africa/Nairobi"), ("Dubai", 25.2048, 55.2708, "Asia/Dubai"),
    ("Singapore", 1.3521, 103.8198, "Asia/Singapore"), ("Tokyo", 35.6762, 139.6503, "Asia/Tokyo"),
    ("Moscow", 55.7558, 37.6173, "Europe/Moscow"), ("Reykjavik", 64.1466, -21.9426, "Atlantic/Reykjavik"),
    ("Tromso", 69.6492, 18.9553, "Europe/Oslo"), ("Honolulu", 21.3069, -157.8583, "Pacific/Honolulu"),
]
_P = {n: (la, lo, tz) for n, la, lo, tz in PLACES}


def _case(cid: str, place: str, d: date, t: str | None, tags: list[str], fold: int | None = None,
          expect_error: str | None = None) -> dict[str, Any]:
    la, lo, tz = _P[place]
    return {"id": cid, "name": cid, "date": d.isoformat(), "time": t, "place": place, "lat": la, "lon": lo, "tz": tz,
            "fold": fold, "tags": tags, "expect_error": expect_error}


def special_cases() -> list[dict[str, Any]]:
    """Hand-picked edge cases the engine and any oracle must agree on (or both reject)."""
    return [
        _case("special-midnight", "Kolkata", date(1990, 3, 15), "00:00", ["midnight"]),
        _case("special-late-evening", "Pune", date(2003, 4, 1), "23:45", ["near-midnight"]),
        _case("special-sign-boundary", "Agra", date(2000, 4, 13), "17:21", ["sign-boundary", "sun-ingress"]),
        _case("special-pre1950-india", "Delhi", date(1943, 3, 3), "08:15", ["pre-1950", "war-time"]),
        _case("special-pre1906-lmt", "Kolkata", date(1900, 6, 1), "10:00", ["historical-tz"]),
        _case("special-dst-overlap", "New York", date(2023, 11, 5), "01:30", ["dst-overlap"], fold=0),
        _case("special-dst-gap", "New York", date(2023, 3, 12), "02:30", ["dst-gap"], expect_error="NonexistentLocalTime"),
        _case("special-polar-day", "Tromso", date(1995, 6, 21), "14:00", ["polar", "no-sunset"]),
        _case("special-polar-night", "Tromso", date(1995, 12, 21), "12:00", ["polar", "no-sunrise"]),
        _case("special-southern", "Sydney", date(1990, 12, 25), "23:10", ["southern-hemisphere"]),
        _case("special-time-unknown", "Agra", date(2004, 5, 5), None, ["time-unknown"]),
        _case("special-equator", "Nairobi", date(1988, 8, 8), "08:08", ["equator"]),
        _case("special-dateline", "Auckland", date(1975, 1, 1), "00:30", ["dateline", "year-boundary"]),
        _case("special-leap-day", "Mumbai", date(2000, 2, 29), "12:00", ["leap-day"]),
    ]


def generate_cases(n: int = 120, seed: int = 20260101) -> list[dict[str, Any]]:
    """`n` cases: the special ones first, the rest random over 1940-2024 and 30 places. Fully determined by `seed`."""
    rng = random.Random(seed)
    out = special_cases()
    start, span = date(1940, 1, 1), (date(2024, 12, 31) - date(1940, 1, 1)).days
    i = 0
    while len(out) < n:
        i += 1
        name = rng.choice(PLACES)[0]
        d = start + timedelta(days=rng.randrange(span))
        unknown = rng.random() < 0.05
        t = None if unknown else f"{rng.randrange(24):02d}:{rng.randrange(60):02d}"
        out.append(_case(f"rand-{i:03d}", name, d, t, ["random"], fold=0))
    return out[:n]
