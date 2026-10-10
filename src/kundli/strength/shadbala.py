"""Shadbala (BPHS ch.27): six balas in virupas (60 virupas = 1 rupa). Seven grahas only.

Every formula is stated in the function docstring. Simplifications are listed in docs/open_questions.md.
"""
import math

import swisseph as swe

from ..ayanamsa import ayanamsa_ut, sid_mode
from ..core import Core, angdiff, relation
from ..data.tables import (
    DIG_STRONG_HOUSE,
    EXALTATION,
    MOOLATRIKONA,
    NAISARGIKA,
    OWN_SIGNS,
    SAPTAVARGA,
    SAPTAVARGAJA_POINTS,
    SEVEN,
    SHADBALA_REQUIRED,
    SIGN_LORDS,
    WEEKDAY_LORDS,
)
from ..ephemeris import PLANET_IDS, base_flags
from ..panchang import hora_lord, sun_events, vara_index

NATURAL_BENEFIC = {"Jupiter", "Venus", "Mercury"}  # Moon: benefic when waxing (decided per chart)


# ---- Sthana -----------------------------------------------------------------------------------------
def uchcha_bala(core: Core, p: str) -> float:
    """Arc from the debilitation point (0..180) / 3."""
    ex_sign, ex_deg = EXALTATION[p]
    deb = ((ex_sign + 6) % 12) * 30.0 + ex_deg
    return angdiff(core.lon[p], deb) / 3.0


def saptavargaja_bala(core: Core, p: str) -> float:
    """Sum over D1,D2,D3,D7,D9,D12,D30 of: moolatrikona 45 (D1 only), own 30, else compound relation with the
    sign lord (great friend 22.5, friend 15, neutral 7.5, enemy 3.75, great enemy 1.875)."""
    total = 0.0
    for v in SAPTAVARGA:
        s = core.varga[v][p]
        mt = MOOLATRIKONA.get(p)
        if v == "D1" and mt and s == mt[0] and mt[1] <= core.deg[p] < mt[2]:
            total += SAPTAVARGAJA_POINTS["moolatrikona"]
        elif s in OWN_SIGNS[p]:
            total += SAPTAVARGAJA_POINTS["own"]
        else:
            total += SAPTAVARGAJA_POINTS[relation(core, p, SIGN_LORDS[s])]
    return total


def ojayugma_bala(core: Core, p: str) -> float:
    """Moon and Venus: 15 each for even sign in rashi and navamsa; others: 15 each for odd sign."""
    even_planets = p in ("Moon", "Venus")
    pts = 0.0
    for s in (core.sign[p], core.varga["D9"][p]):
        is_even_sign = s % 2 == 1
        if is_even_sign == even_planets:
            pts += 15.0
    return pts


def kendradi_bala(core: Core, p: str) -> float:
    h = core.rashi_house[p]
    assert h is not None
    return 60.0 if h in (1, 4, 7, 10) else 30.0 if h in (2, 5, 8, 11) else 15.0


def drekkana_bala(core: Core, p: str) -> float:
    """Male (Sun, Mars, Jupiter) in 1st drekkana, neutral (Mercury, Saturn) in 2nd, female (Moon, Venus) in 3rd: 15."""
    k = int(core.deg[p] // 10)
    want = {"Sun": 0, "Mars": 0, "Jupiter": 0, "Mercury": 1, "Saturn": 1, "Moon": 2, "Venus": 2}[p]
    return 15.0 if k == want else 0.0


def sthana_bala(core: Core, p: str) -> dict[str, float]:
    parts = {"uchcha": uchcha_bala(core, p), "saptavargaja": saptavargaja_bala(core, p),
             "ojayugma": ojayugma_bala(core, p), "kendradi": kendradi_bala(core, p),
             "drekkana": drekkana_bala(core, p)}
    parts["total"] = sum(parts.values())
    return parts


# ---- Dig --------------------------------------------------------------------------------------------
def dig_bala(core: Core, p: str) -> float:
    """Angular distance from the weakest point (opposite of the strongest) / 3. Strong points: Asc, MC, Desc, IC."""
    assert core.houses is not None
    asc, mc = core.houses.asc, core.houses.mc
    strong = {1: asc, 10: mc, 7: (asc + 180.0) % 360.0, 4: (mc + 180.0) % 360.0}[DIG_STRONG_HOUSE[p]]
    return angdiff(core.lon[p], (strong + 180.0) % 360.0) / 3.0


# ---- Kala -------------------------------------------------------------------------------------------
def _is_waxing(core: Core) -> bool:
    return (core.lon["Moon"] - core.lon["Sun"]) % 360.0 < 180.0


def paksha_bala(core: Core, p: str) -> float:
    """Moon-Sun elongation (folded to 0..180) / 3 for benefics; 60 minus that for malefics."""
    e = angdiff(core.lon["Moon"], core.lon["Sun"]) / 3.0
    return e if (p in NATURAL_BENEFIC or p == "Moon") else 60.0 - e


def nathonnatha_bala(core: Core, p: str) -> float:
    """Sun/Jupiter/Venus: 60 at noon falling to 0 at midnight; Moon/Mars/Saturn the reverse; Mercury 60."""
    if p == "Mercury":
        return 60.0
    ev = core.sun_ev
    assert ev is not None
    noon = (ev["sunrise"] + ev["sunset"]) / 2.0
    t = core.moment.jd_ut
    hrs_from_midnight = min(abs(t - (noon - 0.5)), abs(t - (noon + 0.5))) * 24.0
    day_strength = hrs_from_midnight / 12.0 * 60.0
    return day_strength if p in ("Sun", "Jupiter", "Venus") else 60.0 - day_strength


def tribhaga_bala(core: Core, p: str) -> float:
    """Day thirds: Mercury, Sun, Saturn; night thirds: Moon, Venus, Mars; Jupiter always 60."""
    if p == "Jupiter":
        return 60.0
    ev = core.sun_ev
    assert ev is not None
    t = core.moment.jd_ut
    if t < ev["sunset"]:
        k = min(int(3 * (t - ev["sunrise"]) / (ev["sunset"] - ev["sunrise"])), 2)
        return 60.0 if p == ["Mercury", "Sun", "Saturn"][k] else 0.0
    k = min(int(3 * (t - ev["sunset"]) / (ev["next_sunrise"] - ev["sunset"])), 2)
    return 60.0 if p == ["Moon", "Venus", "Mars"][k] else 0.0


def _sun_crossing(core: Core, target_lon: float, jd_end: float, back_days: float) -> float:
    """Most recent JD <= jd_end when the sidereal Sun was at target_lon (bisection)."""
    def f(jd: float) -> float:
        s = _sid(core, swe.SUN, jd)
        return (s - target_lon + 180.0) % 360.0 - 180.0

    lo, hi = jd_end - back_days, jd_end
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if f(mid) < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _sid(core: Core, body: int, jd: float) -> float:
    swe.set_sid_mode(sid_mode(core.cfg.ayanamsa))
    return swe.calc_ut(jd, body, base_flags(core.cfg) | swe.FLG_SIDEREAL)[0][0] % 360.0


def varsha_masa_vara_lords(core: Core) -> dict[str, str]:
    """Abda lord = weekday lord of the last Mesha sankranti; Masa lord = weekday lord of the last solar-month
    sankranti; Vara lord = weekday lord of the birth day (sunrise to sunrise). (VERIFY: classical Abda/Masa
    use ahargana; the solar-sankranti variant is used here.)"""
    jd = core.moment.jd_ut
    tz, lat, lon = core.birth.place.tz, core.birth.place.lat, core.birth.place.lon
    month_start = int(core.lon["Sun"] // 30) * 30.0
    out = {}
    for key, tgt, back in (("abda", 0.0, 367.0), ("masa", month_start, 32.0)):
        j = _sun_crossing(core, tgt, jd, back)
        ev = sun_events(j, lat, lon)
        out[key] = WEEKDAY_LORDS[vara_index(ev["sunrise"], tz)] if ev else "Sun"
    assert core.day_idx is not None
    out["vara"] = WEEKDAY_LORDS[core.day_idx]
    return out


def ayana_bala(core: Core, p: str) -> float:
    """(23.45 + declination)/46.9 x 60 for Sun, Mars, Jupiter, Venus, Mercury; (23.45 - declination)/46.9 x 60 for
    Moon, Saturn (declination of the tropical position, Sun doubled)."""
    dec = swe.calc_ut(core.moment.jd_ut, PLANET_IDS[p], base_flags(core.cfg) | swe.FLG_EQUATORIAL)[0][1]
    v = (23.45 + dec if p not in ("Moon", "Saturn") else 23.45 - dec) / 46.9 * 60.0
    v = max(0.0, min(60.0, v))
    return v * 2 if p == "Sun" else v


def kala_bala(core: Core, p: str, lords: dict[str, str], hora: str) -> dict[str, float]:
    parts = {
        "nathonnatha": nathonnatha_bala(core, p), "paksha": paksha_bala(core, p),
        "tribhaga": tribhaga_bala(core, p),
        "abda": 15.0 if lords["abda"] == p else 0.0, "masa": 30.0 if lords["masa"] == p else 0.0,
        "vara": 45.0 if lords["vara"] == p else 0.0, "hora": 60.0 if hora == p else 0.0,
        "ayana": ayana_bala(core, p),
        "yuddha": 0.0,  # VERIFY: planetary-war adjustment not applied (see open_questions)
    }
    parts["total"] = sum(parts.values())
    return parts


# ---- Cheshta ----------------------------------------------------------------------------------------
def _mean_sun_sidereal(core: Core) -> float:
    t = (core.moment.jd_ut - 2451545.0) / 36525.0
    mean_trop = (280.46646 + 36000.76983 * t + 0.0003032 * t * t) % 360.0
    return (mean_trop - ayanamsa_ut(core.moment.jd_ut, core.cfg.ayanamsa)) % 360.0


def _helio_sidereal(core: Core, p: str) -> float:
    swe.set_sid_mode(sid_mode(core.cfg.ayanamsa))
    flags = base_flags(core.cfg) | swe.FLG_SIDEREAL | swe.FLG_HELCTR
    return swe.calc_ut(core.moment.jd_ut, PLANET_IDS[p], flags)[0][0] % 360.0


def cheshta_bala(core: Core, p: str, ayana: float, paksha_moon: float) -> float:
    """Sun: Ayana bala; Moon: Paksha bala. Others: Cheshta kendra c = |Seeghra - (Madhya + True)/2| folded to
    0..180, bala = c/3. Mars/Jupiter/Saturn: seeghra = mean Sun, madhya = heliocentric longitude; Mercury/Venus:
    seeghra = heliocentric longitude, madhya = mean Sun. (VERIFY: true heliocentric longitude stands in for the
    mean planet.)"""
    if p == "Sun":
        return min(ayana, 60.0)
    if p == "Moon":
        return paksha_moon
    helio, msun = _helio_sidereal(core, p), _mean_sun_sidereal(core)
    seeghra, madhya = (msun, helio) if p in ("Mars", "Jupiter", "Saturn") else (helio, msun)
    true = core.lon[p]
    avg = (madhya + ((true - madhya + 180.0) % 360.0 - 180.0) / 2.0) % 360.0
    return angdiff(seeghra, avg) / 3.0


# ---- Drik -------------------------------------------------------------------------------------------
def aspect_value(core: Core, q: str, p: str) -> float:
    """Sphuta drishti (virupas) of q on p from the angular distance d = lon_p - lon_q. Standard curve:
    30-60: (d-30)/2; 60-90: d-45; 90-120: (120-d)/2+30; 120-150: 150-d; 150-180: (d-150)*2; 180-300: (300-d)/2.
    Special aspects (Mars 4/8, Jupiter 5/9, Saturn 3/10, by sign) count a full 60."""
    d = (core.lon[p] - core.lon[q]) % 360.0
    house_diff = (core.sign[p] - core.sign[q]) % 12 + 1
    special = {"Mars": (4, 8), "Jupiter": (5, 9), "Saturn": (3, 10)}.get(q, ())
    if house_diff in special:
        return 60.0
    if d < 30:
        return 0.0
    if d < 60:
        return (d - 30) / 2
    if d < 90:
        return d - 45
    if d < 120:
        return (120 - d) / 2 + 30
    if d < 150:
        return 150 - d
    if d < 180:
        return (d - 150) * 2
    if d < 300:
        return (300 - d) / 2
    return 0.0


def is_benefic(core: Core, q: str) -> bool:
    return q in NATURAL_BENEFIC or (q == "Moon" and _is_waxing(core))


def drik_bala(core: Core, p: str) -> float:
    """(sum of benefic aspect values received - sum of malefic) / 4."""
    total = 0.0
    for q in SEVEN:
        if q == p:
            continue
        v = aspect_value(core, q, p)
        total += v if is_benefic(core, q) else -v
    return total / 4.0


# ---- Orchestration ----------------------------------------------------------------------------------
def shadbala(core: Core) -> dict:
    if core.houses is None or core.sun_ev is None:
        raise ValueError("Shadbala needs birth time and a sunrise (not available at polar latitudes)")
    lords = varsha_masa_vara_lords(core)
    hora, _ = hora_lord(core.moment.jd_ut, core.sun_ev, core.day_idx or 0)
    pak_moon = paksha_bala(core, "Moon")
    out: dict = {"planets": {}, "lords": {**lords, "hora": hora}, "unit": "virupas"}
    for p in SEVEN:
        st, dg, ka = sthana_bala(core, p), dig_bala(core, p), kala_bala(core, p, lords, hora)
        ay = ayana_bala(core, p) if p == "Sun" else 0.0
        ch = cheshta_bala(core, p, ay, pak_moon)
        na, dr = NAISARGIKA[p], drik_bala(core, p)
        total = st["total"] + dg + ka["total"] + ch + na + dr
        req = SHADBALA_REQUIRED[p]
        out["planets"][p] = {
            "sthana": st, "dig": dg, "kala": ka, "cheshta": ch, "naisargika": na, "drik": dr,
            "total_virupas": total, "total_rupas": total / 60.0, "required_virupas": req,
            "ratio": total / req, "meets_minimum": total >= req,
        }
    ranked = sorted(SEVEN, key=lambda x: (-out["planets"][x]["ratio"], x))
    out["rank"] = ranked
    return out


def ishta_kashta(core: Core, sb: dict) -> dict:
    """Ishta = sqrt(Uchcha x Cheshta); Kashta = sqrt((60-Uchcha) x (60-Cheshta)); both capped to 60."""
    out = {}
    for p in SEVEN:
        u = min(sb["planets"][p]["sthana"]["uchcha"], 60.0)
        c = min(sb["planets"][p]["cheshta"], 60.0)
        out[p] = {"ishta": math.sqrt(u * c), "kashta": math.sqrt((60 - u) * (60 - c))}
    return out
