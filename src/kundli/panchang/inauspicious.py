"""Inauspicious and special day periods, derived from sunrise/sunset only.

Rahu Kaal, Yamaganda and Gulika Kaal each occupy one of the eight equal parts of the daytime; which part depends on
the weekday (tables below, `# VERIFY` until checked against a primary source). Abhijit Muhurta is the eighth of the
fifteen equal daytime muhurtas (the one centred on local apparent noon).
Dur Muhurta, Varjyam and Amrit Kaal are NOT implemented: their weekday/nakshatra tables could not be sourced
(docs/open_questions.md).
"""
from zoneinfo import ZoneInfo

from ..timeutil import jd_to_utc

# Part number (1..8) of the daytime, by weekday Sunday..Saturday. VERIFY
RAHU_KAAL_PART = [8, 2, 7, 5, 6, 4, 3]
YAMAGANDA_PART = [5, 4, 3, 2, 1, 7, 6]
GULIKA_KAAL_PART = [7, 6, 5, 4, 3, 2, 1]


def _window(a: float, b: float, tz: str) -> dict:
    zi = ZoneInfo(tz)
    return {"start_jd": a, "end_jd": b, "start_local": jd_to_utc(a).astimezone(zi).isoformat(timespec="seconds"),
            "end_local": jd_to_utc(b).astimezone(zi).isoformat(timespec="seconds")}


def inauspicious_periods(ev: dict, day_idx: int, tz: str) -> dict[str, dict]:
    day = ev["sunset"] - ev["sunrise"]
    eighth = day / 8.0

    def part(n: int) -> dict:
        return _window(ev["sunrise"] + (n - 1) * eighth, ev["sunrise"] + n * eighth, tz)

    muhurta = day / 15.0
    return {
        "rahu_kaal": part(RAHU_KAAL_PART[day_idx]),
        "yamaganda": part(YAMAGANDA_PART[day_idx]),
        "gulika_kaal": part(GULIKA_KAAL_PART[day_idx]),
        "abhijit_muhurta": _window(ev["sunrise"] + 7 * muhurta, ev["sunrise"] + 8 * muhurta, tz),
    }


__all__ = ["GULIKA_KAAL_PART", "RAHU_KAAL_PART", "YAMAGANDA_PART", "inauspicious_periods"]
