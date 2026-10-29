"""Choghadiya tables, day and night (8 equal parts each).

Day: the first part is the weekday's start in `CHOGHADIYA_START` (data/tables.py, `# VERIFY`), parts then follow
the fixed cycle Udveg, Chal, Labh, Amrit, Kaal, Shubh, Rog.
Night: the first part is the day-start of the weekday four days later (Sunday night starts with Shubh), and the
cycle then runs backwards two places per part (Shubh, Amrit, Chal, Rog, Kaal, Labh, Udveg, ...). Both rules
reproduce the commonly published Sunday-night table but are from memory: `# VERIFY`, listed in
docs/open_questions.md.
"""
from zoneinfo import ZoneInfo

from ..data.tables import CHOGHADIYA_CYCLE, CHOGHADIYA_QUALITY, CHOGHADIYA_START
from ..timeutil import jd_to_utc


def _rows(t0: float, t1: float, first: int, period: str, tz: str, stride: int = 1) -> list[dict]:
    zi = ZoneInfo(tz)
    step = (t1 - t0) / 8.0
    out = []
    for k in range(8):
        a, b = t0 + k * step, t0 + (k + 1) * step
        name = CHOGHADIYA_CYCLE[(first + stride * k) % 7]
        out.append({"part": k + 1, "name": name, "quality": CHOGHADIYA_QUALITY[name], "period": period,
                    "start_jd": a, "end_jd": b,
                    "start_local": jd_to_utc(a).astimezone(zi).isoformat(timespec="seconds"),
                    "end_local": jd_to_utc(b).astimezone(zi).isoformat(timespec="seconds")})
    return out


def choghadiya_table(ev: dict, day_idx: int, tz: str) -> dict[str, list[dict]]:
    return {"day": _rows(ev["sunrise"], ev["sunset"], CHOGHADIYA_START[day_idx], "day", tz),
            "night": _rows(ev["sunset"], ev["next_sunrise"], CHOGHADIYA_START[(day_idx + 4) % 7], "night", tz, -2)}


__all__ = ["choghadiya_table"]
