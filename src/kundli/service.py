"""Shared helpers for the CLI and API: build input from loose parameters, load/save charts."""
import json
import os
from datetime import date, datetime, time
from pathlib import Path

from .chart import generate, to_dict
from .config import EngineConfig
from .geo import resolve_place
from .models import BirthInput, Kundli, Place


def parse_time(s: str | None) -> time | None:
    if s is None or s.strip().lower() in ("", "unknown", "none"):
        return None
    return time.fromisoformat(s if s.count(":") > 1 else s + ":00")


def make_birth(name: str, dob: str, tm: str | None, place: str | None, choice: int | None = None, fold: int | None = None,
               lat: float | None = None, lon: float | None = None, tz: str | None = None) -> BirthInput:
    """Place is resolved by text (AmbiguousPlace is raised if unclear) or given manually as lat/lon/tz."""
    if lat is not None and lon is not None and tz:
        pl = Place(name=place or f"{lat:.3f},{lon:.3f}", lat=lat, lon=lon, tz=tz, source="manual")
    elif place:
        pl = resolve_place(place, choice=choice)
    else:
        raise ValueError("give a place name or lat/lon/tz")
    return BirthInput(name=name, date=date.fromisoformat(dob), time=parse_time(tm), place=pl, fold=fold)


def aware(s: str) -> datetime:
    """ISO date or datetime -> aware UTC datetime (naive input is taken as UTC)."""
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=__import__("datetime").timezone.utc)


def load_chart(path: str | Path) -> Kundli:
    return Kundli.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def data_dir() -> Path:
    d = Path(os.environ.get("KUNDLI_DATA_DIR", Path.home() / ".kundli" / "data"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_chart(k: Kundli) -> str:
    cid = k.header["run_id"][:16]
    (data_dir() / f"{cid}.json").write_text(json.dumps(to_dict(k), sort_keys=True), encoding="utf-8")
    return cid


def get_chart(cid: str) -> Kundli | None:
    if not cid.isalnum():
        return None
    p = data_dir() / f"{cid}.json"
    return load_chart(p) if p.exists() else None


def delete_chart(cid: str) -> bool:
    p = data_dir() / f"{cid}.json"
    if cid.isalnum() and p.exists():
        p.unlink()
        return True
    return False


__all__ = ["EngineConfig", "generate", "make_birth"]
