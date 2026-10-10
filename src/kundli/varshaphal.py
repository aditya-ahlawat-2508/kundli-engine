"""Varshaphal (Tajika annual chart): solar return and Muntha. Tajika yogas / year lord / tithi pravesha are not
implemented (see docs/open_questions.md)."""
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from .data.tables import PLANETS, SIGN_LORDS, SIGNS
from .houses import compute_houses
from .models import Kundli
from .timeutil import jd_to_utc
from .transits import _cfg, jd_of, sid_lon


def solar_return(k: Kundli, year: int) -> dict:
    """Moment in `year` when the sidereal Sun returns to its natal longitude (bisection to ~1 ms), the chart for that
    moment at the birth place, and the Muntha (natal lagna sign advanced one sign per completed year)."""
    cfg = _cfg(k)
    natal_sun = next(p.sidereal_lon for p in k.planets if p.name == "Sun")
    birth = datetime.fromisoformat(k.birth["utc"])
    guess = jd_of(birth.replace(year=year) if not (birth.month == 2 and birth.day == 29) else birth.replace(year=year, day=28))

    def f(jd: float) -> float:
        return (sid_lon("Sun", jd, cfg) - natal_sun + 180.0) % 360.0 - 180.0

    lo, hi = guess - 3.0, guess + 3.0
    for _ in range(50):
        mid = (lo + hi) / 2.0
        lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
    jd = (lo + hi) / 2.0
    utc = jd_to_utc(jd)
    place = k.birth["place"]
    hs = compute_houses(jd, place["lat"], place["lon"], cfg)
    lagna = int(hs.asc // 30)
    age = year - birth.year
    muntha = (k.lagna["sign"] + age) % 12 if k.lagna else None
    return {
        "year": year, "age": age, "utc": utc.astimezone(UTC).isoformat(timespec="seconds"),
        "local": utc.astimezone(ZoneInfo(place["tz"])).isoformat(timespec="seconds"),
        "lagna_sign": lagna, "lagna_sign_name": SIGNS[lagna], "lagna_longitude": hs.asc,
        "planets": {n: {"sign": int(sid_lon(n, jd, cfg) // 30), "longitude": sid_lon(n, jd, cfg)} for n in PLANETS},
        "muntha": None if muntha is None else {
            "sign": muntha, "sign_name": SIGNS[muntha], "house_in_annual_chart": (muntha - lagna) % 12 + 1,
            "lord": SIGN_LORDS[muntha]},
    }
