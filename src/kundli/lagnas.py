"""Special lagnas and upagrahas."""
from .config import EngineConfig
from .data.tables import INDU_KALAS, NAK_SPAN, SIGN_LORDS, WEEKDAY_LORDS
from .houses import compute_houses
from .nakshatra import fraction_elapsed


def ghatis_since_sunrise(jd_ut: float, sunrise_jd: float) -> float:
    """1 day = 60 ghatis (24 minutes each)."""
    return (jd_ut - sunrise_jd) * 60.0


def special_lagnas(jd_ut: float, sunrise_jd: float, sun: float, moon: float, asc: float,
                   sign_of: dict[str, int]) -> dict[str, float]:
    """Longitudes (sidereal) of Hora, Ghati, Bhava, Sree and Indu lagna.

    Hora lagna = Sun + 12deg/ghati (1 sign per 2.5 ghatis); Ghati lagna = Sun + 30deg/ghati; Bhava lagna =
    Sun + 6deg/ghati (1 sign per 5 ghatis), all counted from sunrise. Sree lagna = Lagna + 360deg x fraction of
    Moon's nakshatra traversed. Indu lagna: kalas of the 9th lords from Lagna and from Moon, summed, mod 12,
    counted from the Moon's sign.
    """
    g = ghatis_since_sunrise(jd_ut, sunrise_jd)
    asc_sign, moon_sign = int(asc // 30), int(moon // 30)
    lord9_l = SIGN_LORDS[(asc_sign + 8) % 12]
    lord9_m = SIGN_LORDS[(moon_sign + 8) % 12]
    k = (INDU_KALAS[lord9_l] + INDU_KALAS[lord9_m]) % 12 or 12
    indu_sign = (moon_sign + k - 1) % 12
    return {
        "hora_lagna": (sun + 12.0 * g) % 360.0,
        "ghati_lagna": (sun + 30.0 * g) % 360.0,
        "bhava_lagna": (sun + 6.0 * g) % 360.0,
        "sree_lagna": (asc + 360.0 * fraction_elapsed(moon)) % 360.0,
        "indu_lagna": indu_sign * 30.0 + (asc % 30.0),  # sign-level result; degree carried from lagna
    }


def gulika_mandi(jd_ut: float, ev: dict, day_idx: int, lat: float, lon: float, cfg: EngineConfig) -> dict[str, float]:
    """Gulika = ascendant at the start of Saturn's portion; Mandi = at its midpoint. (VERIFY: schools differ.)

    Day (sunrise->sunset) and night (sunset->next sunrise) are each split in 8 portions; lords follow weekday
    order from the day lord (night: from the 5th lord); the 8th portion has no lord.
    """
    is_day = jd_ut < ev["sunset"]
    a, b = (ev["sunrise"], ev["sunset"]) if is_day else (ev["sunset"], ev["next_sunrise"])
    base = day_idx if is_day else (day_idx + 4) % 7
    k = (WEEKDAY_LORDS.index("Saturn") - base) % 7
    dur = (b - a) / 8.0
    t0 = a + k * dur
    return {
        "gulika": compute_houses(t0, lat, lon, cfg).asc,
        "mandi": compute_houses(t0 + dur / 2.0, lat, lon, cfg).asc,
    }


def sun_upagrahas(sun: float) -> dict[str, float]:
    """Dhuma = Sun + 133deg20'; Vyatipata = 360 - Dhuma; Parivesha = Vyatipata + 180; Indrachapa = 360 - Parivesha;
    Upaketu = Indrachapa + 16deg40'."""
    dhuma = (sun + 133 + 20 / 60) % 360.0
    vyati = (360.0 - dhuma) % 360.0
    pari = (vyati + 180.0) % 360.0
    indra = (360.0 - pari) % 360.0
    upaketu = (indra + 16 + 40 / 60) % 360.0
    return {"dhuma": dhuma, "vyatipata": vyati, "parivesha": pari, "indrachapa": indra, "upaketu": upaketu}


__all__ = ["NAK_SPAN", "gulika_mandi", "special_lagnas", "sun_upagrahas"]
