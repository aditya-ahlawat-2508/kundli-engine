"""Planetary hours. Day and night are each split into 12 equal horas; lords follow the Chaldean order starting
from the weekday lord at sunrise (day) and continuing through the night."""
from zoneinfo import ZoneInfo

from ..data.tables import CHALDEAN, WEEKDAY_LORDS
from ..timeutil import jd_to_utc


def hora_table(ev: dict, day_idx: int, tz: str) -> list[dict]:
    """24 horas for the Vedic day starting at ev['sunrise'] (ev from `sun_events`, day_idx 0=Sunday)."""
    zi = ZoneInfo(tz)
    day_len = (ev["sunset"] - ev["sunrise"]) / 12.0
    night_len = (ev["next_sunrise"] - ev["sunset"]) / 12.0
    start = CHALDEAN.index(WEEKDAY_LORDS[day_idx])
    rows = []
    for n in range(24):
        a = ev["sunrise"] + n * day_len if n < 12 else ev["sunset"] + (n - 12) * night_len
        b = a + (day_len if n < 12 else night_len)
        rows.append({"number": n + 1, "lord": CHALDEAN[(start + n) % 7], "period": "day" if n < 12 else "night",
                     "start_jd": a, "end_jd": b,
                     "start_local": jd_to_utc(a).astimezone(zi).isoformat(timespec="seconds"),
                     "end_local": jd_to_utc(b).astimezone(zi).isoformat(timespec="seconds")})
    return rows


__all__ = ["hora_table"]
