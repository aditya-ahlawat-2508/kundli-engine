"""Field-level diff between an expected (oracle) JSON document and the engine's output, with per-field-type
tolerances: longitudes 1 arcminute, clock times 1 minute, dates and dasha boundaries 1 day, text compared by
presence only, everything else exact."""
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

LON_TOL = 1 / 60  # degrees
TIME_TOL = 60.0  # seconds
DATE_TOL = 86400.0  # seconds
TEXT_KEYS = ("text", "description", "report", "prediction", "summary", "remed", "detail", "interpretation")
LON_KEYS = ("longitude", "lon", "degree", "deg", "cusp")


class FieldClass(Enum):
    LONGITUDE = "longitude"
    TIME = "time"
    DATE = "date"
    TEXT = "text"
    EXACT = "exact"


@dataclass(frozen=True)
class Mismatch:
    path: str
    expected: Any
    actual: Any
    kind: FieldClass
    delta: float | None = None


@dataclass
class DiffResult:
    compared: int = 0
    mismatches: list[Mismatch] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)  # present in expected, absent in actual
    extra: list[str] = field(default_factory=list)  # present in actual only (informational)
    by_class: dict[str, list[int]] = field(default_factory=dict)  # class -> [compared, matched]

    @property
    def match_rate(self) -> float:
        bad = len(self.mismatches) + len(self.missing)
        total = self.compared + len(self.missing)
        return 1.0 if total == 0 else (total - bad) / total


def parse_dt(s: str) -> tuple[datetime, bool] | None:
    """(datetime, has_time_part) from ISO or DD-MM-YYYY[ HH:MM[:SS]] strings; naive values are taken as UTC."""
    s = s.strip()
    for fmt, has_t in (("%d-%m-%Y %H:%M:%S", True), ("%d-%m-%Y %H:%M", True), ("%d-%m-%Y", False),
                       ("%d/%m/%Y", False)):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=UTC), has_t
        except ValueError:
            pass
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        try:
            d = datetime.fromisoformat(s)
        except ValueError:
            return None
        return (d if d.tzinfo else d.replace(tzinfo=UTC)), len(s) > 10
    return None


def classify(key: str, a: Any, b: Any, path: str = "") -> FieldClass:
    """`path` (full dotted path) lets a parent such as `mahadasha` mark its children as dasha boundaries."""
    k = key.lower()
    full = (path or key).lower()
    if isinstance(a, str) and isinstance(b, str):
        pa, pb = parse_dt(a), parse_dt(b)
        if pa and pb:
            return FieldClass.TIME if (pa[1] and pb[1] and "dasha" not in full and "dasa" not in full) else FieldClass.DATE
        if any(t in k for t in TEXT_KEYS):
            return FieldClass.TEXT
        return FieldClass.EXACT
    if (isinstance(a, float) and isinstance(b, (int, float)) and not isinstance(b, bool)
            and any(t in k for t in LON_KEYS)):
        return FieldClass.LONGITUDE
    return FieldClass.EXACT


def _flatten(x: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(x, dict):
        out: dict[str, Any] = {}
        for k, v in x.items():
            out.update(_flatten(v, f"{prefix}.{k}" if prefix else str(k)))
        return out
    if isinstance(x, list):
        out = {}
        for i, v in enumerate(x):
            out.update(_flatten(v, f"{prefix}[{i}]"))
        return out
    return {prefix: x}


def _compare(path: str, a: Any, b: Any) -> tuple[FieldClass, bool, float | None]:
    key = re.split(r"[.\[]", path)[-1] if path else ""
    last = path.rsplit(".", 1)[-1]
    kind = classify(last or key, a, b, path)
    if kind is FieldClass.TEXT:
        return kind, bool(a) == bool(b), None
    if kind is FieldClass.LONGITUDE:
        d = abs(float(a) - float(b))
        if "lon" in last.lower() and "degree" not in last.lower():
            d = min(d, 360.0 - d)
        return kind, d <= LON_TOL, d
    if kind in (FieldClass.TIME, FieldClass.DATE):
        pa, pb = parse_dt(a), parse_dt(b)
        assert pa and pb
        d = abs((pa[0] - pb[0]).total_seconds())
        return kind, d <= (TIME_TOL if kind is FieldClass.TIME else DATE_TOL), d
    if isinstance(a, float) or isinstance(b, float):
        try:
            return kind, abs(float(a) - float(b)) < 1e-9, None
        except (TypeError, ValueError):
            return kind, False, None
    return kind, a == b, None


def diff(expected: Any, actual: Any, *, ignore: tuple[str, ...] = ()) -> DiffResult:
    """Compare every leaf of `expected` with `actual`. `ignore` = path substrings to skip."""
    ea, aa = _flatten(expected), _flatten(actual)
    res = DiffResult()
    for path, ev in ea.items():
        if any(i in path for i in ignore):
            continue
        if path not in aa:
            res.missing.append(path)
            continue
        kind, ok, delta = _compare(path, ev, aa[path])
        res.compared += 1
        c = res.by_class.setdefault(kind.value, [0, 0])
        c[0] += 1
        c[1] += int(ok)
        if not ok:
            res.mismatches.append(Mismatch(path, ev, aa[path], kind, delta))
    res.extra = [p for p in aa if p not in ea and not any(i in p for i in ignore)]
    return res


def summarize(res: DiffResult) -> dict[str, Any]:
    return {"compared": res.compared, "match_rate": round(res.match_rate, 4), "mismatches": len(res.mismatches),
            "missing": len(res.missing), "by_class": {k: {"compared": v[0], "matched": v[1]} for k, v in res.by_class.items()}}
