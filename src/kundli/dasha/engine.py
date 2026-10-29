"""Generic nested-period dasha engine (Vimshottari and Yogini share it).

A system is a cyclic sequence of (lord, years). The maha dasha at birth is chosen by the Moon's nakshatra and
the fraction already elapsed. Sub-periods of any parent have length parent * lord_years / total_years and run
in cyclic order starting from the parent's own lord.
"""
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

LEVEL_NAMES = ["maha", "antar", "pratyantar", "sookshma", "prana"]


@dataclass(frozen=True)
class System:
    name: str
    seq: tuple[tuple[str, float], ...]  # (lord, years) in cycle order

    @property
    def total(self) -> float:
        return sum(y for _, y in self.seq)

    def index(self, lord: str) -> int:
        return [lo for lo, _ in self.seq].index(lord)


def _children(sys: System, parent_idx: int, start: datetime, days: float) -> Iterator[tuple[int, datetime, float]]:
    """Sub-periods of a parent: (cycle index, start, length_days)."""
    t = start
    for k in range(len(sys.seq)):
        i = (parent_idx + k) % len(sys.seq)
        d = days * sys.seq[i][1] / sys.total
        yield i, t, d
        t = t + timedelta(days=d)


def maha_periods(sys: System, first_idx: int, elapsed_fraction: float, birth_utc: datetime,
                 year_days: float) -> list[tuple[int, datetime, float]]:
    """The nine maha periods covering one full cycle, starting before birth by the elapsed part of the first."""
    first_days = sys.seq[first_idx][1] * year_days
    start = birth_utc - timedelta(days=elapsed_fraction * first_days)
    out, t = [], start
    for k in range(len(sys.seq)):
        i = (first_idx + k) % len(sys.seq)
        d = sys.seq[i][1] * year_days
        out.append((i, t, d))
        t = t + timedelta(days=d)
    return out


def _fmt(dt: datetime, tz: ZoneInfo) -> tuple[str, str]:
    return dt.isoformat(timespec="seconds"), dt.astimezone(tz).isoformat(timespec="seconds")


def build_tree(sys: System, periods: list[tuple[int, datetime, float]], depth: int, tz: str, level: int = 0) -> list[dict]:
    """Nested dicts with UTC/local start/end for `depth` levels."""
    z = ZoneInfo(tz)
    out = []
    for i, start, days in periods:
        end = start + timedelta(days=days)
        s_utc, s_loc = _fmt(start, z)
        e_utc, e_loc = _fmt(end, z)
        node = {"level": LEVEL_NAMES[level], "lord": sys.seq[i][0], "start_utc": s_utc, "end_utc": e_utc,
                "start_local": s_loc, "end_local": e_loc, "days": days}
        if level + 1 < depth:
            node["children"] = build_tree(sys, list(_children(sys, i, start, days)), depth, tz, level + 1)
        out.append(node)
    return out


def stack_at(sys: System, periods: list[tuple[int, datetime, float]], as_of: datetime, levels: int,
             tz: str) -> list[dict]:
    """Running MD/AD/PD/SD/PrD stack at `as_of` (aware UTC). `as_of` is always passed in, never read from a clock."""
    z = ZoneInfo(tz)
    stack: list[dict] = []
    cur = periods
    for lvl in range(levels):
        hit = None
        for i, start, days in cur:
            if start <= as_of < start + timedelta(days=days):
                hit = (i, start, days)
                break
        if hit is None:
            break
        i, start, days = hit
        end = start + timedelta(days=days)
        stack.append({"level": LEVEL_NAMES[lvl], "lord": sys.seq[i][0], "start_utc": _fmt(start, z)[0],
                      "end_utc": _fmt(end, z)[0], "start_local": _fmt(start, z)[1], "end_local": _fmt(end, z)[1]})
        cur = list(_children(sys, i, start, days))
    return stack


def descend(sys: System, periods: list[tuple[int, datetime, float]], path: list[str], tz: str, depth: int = 1) -> dict:
    """Sub-periods of the period reached by following `path` (lord names: maha, then antar, then pratyantar...).
    Each lord occurs once per level inside its parent, so a path identifies one period."""
    cur = periods
    hit = None
    for lvl, name in enumerate(path):
        key = name.strip().lower()
        hit = next((p for p in cur if sys.seq[p[0]][0].lower() == key), None)
        if hit is None:
            raise ValueError(f"no {LEVEL_NAMES[lvl]} period for lord {name!r} here; "
                             f"available: {[sys.seq[p[0]][0] for p in cur]}")
        cur = list(_children(sys, *hit))
    assert hit is not None
    parent = build_tree(sys, [hit], 1, tz, len(path) - 1)[0]
    return {"parent": parent, "children": build_tree(sys, cur, depth, tz, len(path))}
