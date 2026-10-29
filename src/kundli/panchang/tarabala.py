"""Tarabala and the daily-nakshatra facts. The Moon's transit nakshatra is counted (inclusive, 1..27) from the birth nakshatra;
count mod 9 (0 -> 9) names one of nine taras. Chandrabala: the transit Moon in the 1st/3rd/6th/7th/10th/11th sign from the natal
Moon is favourable. The classification of taras (below) is the standard scheme from memory, `# VERIFY`. Pure facts: the text for
each fact lives in the content store (keys `daily.tara.<tara>.nakshatra.<nakshatra>`)."""
from datetime import date
from typing import Any

from ..config import EngineConfig
from ..data.tables import NAK_SPAN, NAKSHATRAS
from ..ephemeris import base_flags
from ..models import Kundli
from .spans import span, sun_moon
from .sun_moon_times import local_iso, rise_args, sun_day

TARAS = ["janma", "sampat", "vipat", "kshema", "pratyari", "sadhaka", "vadha", "mitra", "ati_mitra"]
AUSPICIOUS = {"sampat", "kshema", "sadhaka", "mitra", "ati_mitra"}
INAUSPICIOUS = {"vipat", "pratyari", "vadha"}
CHANDRABALA_GOOD = (1, 3, 6, 7, 10, 11)


def tara_of(birth_nak: int, transit_nak: int) -> tuple[int, str]:
    """(inclusive count 1..27, tara name)."""
    count = (transit_nak - birth_nak) % 27 + 1
    return count, TARAS[(count % 9 or 9) - 1]


def tara_class(tara: str) -> str:
    return "auspicious" if tara in AUSPICIOUS else "inauspicious" if tara in INAUSPICIOUS else "mixed"


def daily_facts(natal: Kundli, d: date, lat: float, lon: float, tz: str, cfg: EngineConfig) -> dict[str, Any]:
    """Facts for the Vedic day of civil date `d`: the Moon's nakshatra segments (exact boundaries) with tara, class and
    Chandrabala, and the segment running at sunrise as `primary`."""
    moon = next(p for p in natal.planets if p.name == "Moon")
    ra, eph = rise_args(cfg), base_flags(cfg)
    sd = sun_day(d, lat, lon, tz, **ra)
    if sd is None:
        raise ValueError("no sunrise at this latitude on this date; the daily nakshatra day is undefined")
    t0, t1 = sd["sunrise"], sd["next_sunrise"]
    segs: list[dict[str, Any]] = []
    t = t0
    while t < t1 - 1e-7:
        s, e = span("nakshatra", t + 1e-7, cfg.ayanamsa, eph)
        end = min(e, t1)
        sun_lon, moon_lon = sun_moon((t + end) / 2.0, cfg.ayanamsa, eph)
        nak = int(moon_lon // NAK_SPAN)
        count, tara = tara_of(moon.nakshatra, nak)
        house = (int(moon_lon // 30) - moon.sign) % 12 + 1
        segs.append({"nakshatra": NAKSHATRAS[nak], "start_local": local_iso(max(s, t0), tz), "end_local": local_iso(end, tz),
                     "start_jd": max(s, t0), "end_jd": end, "count_from_birth_nakshatra": count, "tara": tara,
                     "tara_class": tara_class(tara), "moon_house_from_natal_moon": house,
                     "chandrabala": "favourable" if house in CHANDRABALA_GOOD else "unfavourable"})
        t = end + 1e-7
    return {"date": d.isoformat(), "birth_nakshatra": NAKSHATRAS[moon.nakshatra], "segments": segs, "primary": segs[0],
            "day_start_local": local_iso(t0, tz), "day_end_local": local_iso(t1, tz), "tables_verified": False,
            "note": "the primary nakshatra is the one running at sunrise; the Moon may change nakshatra during the day"}


__all__ = ["AUSPICIOUS", "CHANDRABALA_GOOD", "INAUSPICIOUS", "TARAS", "daily_facts", "tara_class", "tara_of"]
