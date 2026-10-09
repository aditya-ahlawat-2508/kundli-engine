"""Tropical -> sidereal conversion via Swiss Ephemeris ayanamsa modes."""
import swisseph as swe

AYANAMSA_MODES: dict[str, int] = {
    "lahiri": swe.SIDM_LAHIRI,
    "raman": swe.SIDM_RAMAN,
    "kp": swe.SIDM_KRISHNAMURTI,
    "true_chitra": swe.SIDM_TRUE_CITRA,
    "fagan_bradley": swe.SIDM_FAGAN_BRADLEY,
    "yukteshwar": swe.SIDM_YUKTESHWAR,
    "jn_bhasin": swe.SIDM_JN_BHASIN,
}


def sid_mode(name: str) -> int:
    try:
        return AYANAMSA_MODES[name]
    except KeyError:
        raise ValueError(f"unknown ayanamsa {name!r}") from None


def ayanamsa_ut(jd_ut: float, name: str = "lahiri") -> float:
    """Ayanamsa in degrees at jd_ut (swe_get_ayanamsa_ex_ut, nutation-corrected).

    swisseph keeps the sidereal mode in process-global state, so it is set immediately
    before every call that depends on it.
    """
    swe.set_sid_mode(sid_mode(name))
    _, ay = swe.get_ayanamsa_ex_ut(jd_ut, swe.FLG_MOSEPH)
    return ay


def to_sidereal(tropical_lon: float, jd_ut: float, name: str = "lahiri") -> float:
    """sidereal = (tropical - ayanamsa) mod 360."""
    return (tropical_lon - ayanamsa_ut(jd_ut, name)) % 360.0
