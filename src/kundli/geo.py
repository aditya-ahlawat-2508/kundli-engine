"""Place text -> candidate Places (offline GeoNames first, Nominatim fallback, disk-cached).

Never guesses: if more than one plausible candidate remains, AmbiguousPlace is raised and
the caller must pick one (pass `choice=index`).
"""
import hashlib
import json
import unicodedata
import urllib.parse
import urllib.request
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

from timezonefinder import TimezoneFinder

from .errors import AmbiguousPlace, PlaceNotFound
from .models import Place

DATA = Path(__file__).parent / "data"
DEFAULT_CACHE = Path.home() / ".cache" / "kundli" / "geocode"
USER_AGENT = "kundli-engine/0.1 (offline-first geocoder)"

Fetcher = Callable[[str], list[dict]]


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return " ".join(s.replace("-", " ").replace(".", " ").split())


@lru_cache(maxsize=1)
def _countries() -> dict[str, str]:
    return dict(line.split("\t") for line in (DATA / "countries.tsv").read_text(encoding="utf-8").splitlines())


@lru_cache(maxsize=1)
def _admin1() -> dict[str, str]:
    return dict(line.split("\t") for line in (DATA / "admin1.tsv").read_text(encoding="utf-8").splitlines())


@lru_cache(maxsize=1)
def _index() -> dict[str, list[Place]]:
    """Normalised name/alt-name -> places. Built once from the shipped TSV (pure data)."""
    idx: dict[str, list[Place]] = {}
    countries, admin1 = _countries(), _admin1()
    lines = (DATA / "cities.tsv").read_text(encoding="utf-8").splitlines()[1:]
    for line in lines:
        name, ascii_, alts, lat, lon, cc, a1, pop, tz = line.split("\t")
        place = Place(
            name=name, admin1=admin1.get(f"{cc}.{a1}", ""), country=countries.get(cc, cc),
            lat=float(lat), lon=float(lon), tz=tz, population=int(pop or 0),
        )
        for key in {_norm(name), _norm(ascii_), *(_norm(a) for a in alts.split("|") if a)}:
            idx.setdefault(key, []).append(place)
    return idx


def _hint_matches(p: Place, hints: list[str]) -> bool:
    fields = [_norm(p.country), _norm(p.admin1)]
    cc_names = {"india": ["in"], "usa": ["united states"], "us": ["united states"], "uk": ["united kingdom"]}
    for h in hints:
        h = _norm(h)
        alts = [h] + cc_names.get(h, [])
        if not any(a == f or (len(a) > 3 and a in f) for a in alts for f in fields):
            return False
    return True


def _offline(query: str) -> list[Place]:
    parts = [x.strip() for x in query.split(",") if x.strip()]
    if not parts:
        return []
    found = _index().get(_norm(parts[0]), [])
    uniq = {(p.name, p.lat, p.lon): p for p in found}.values()
    cands = [p for p in uniq if _hint_matches(p, parts[1:])]
    return sorted(cands, key=lambda p: (-p.population, p.country, p.admin1, p.name))


def _nominatim_fetch(query: str) -> list[dict]:
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": query, "format": "jsonv2", "limit": 5, "addressdetails": 1}
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


@lru_cache(maxsize=1)
def _tzf() -> TimezoneFinder:
    return TimezoneFinder()


def _online(query: str, cache_dir: Path, fetch: Fetcher) -> list[Place]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    f = cache_dir / (hashlib.sha256(_norm(query).encode()).hexdigest() + ".json")
    if f.exists():
        raw = json.loads(f.read_text(encoding="utf-8"))
    else:
        raw = fetch(query)
        f.write_text(json.dumps(raw, sort_keys=True), encoding="utf-8")
    out = []
    for r in raw:
        lat, lon = float(r["lat"]), float(r["lon"])
        tz = _tzf().timezone_at(lat=lat, lng=lon)
        if tz is None:
            continue
        addr = r.get("address", {})
        out.append(Place(
            name=r.get("name") or r.get("display_name", query).split(",")[0],
            admin1=addr.get("state", ""), country=addr.get("country", ""),
            lat=lat, lon=lon, tz=tz, source="nominatim",
        ))
    return out


def candidates(query: str, *, cache_dir: Path | None = None, fetch: Fetcher | None = None,
               online: bool = True) -> list[Place]:
    """All plausible places for `query` ("City, Region/Country"). Offline DB first."""
    found = _offline(query)
    if found or not online:
        return found
    return _online(query, cache_dir or DEFAULT_CACHE, fetch or _nominatim_fetch)


def resolve_place(query: str, *, choice: int | None = None, **kw) -> Place:
    """Return the single matching Place, or raise AmbiguousPlace / PlaceNotFound.

    `choice` indexes into the (deterministically ordered) candidate list.
    """
    cands = candidates(query, **kw)
    if not cands:
        raise PlaceNotFound(query)
    if choice is not None:
        return cands[choice]
    if len(cands) > 1:
        raise AmbiguousPlace(query, cands)
    return cands[0]
