"""Avakahada chakra: Moon-based birth attributes (varna, vashya, yoni, gana, nadi, tatva, paya, name syllable)."""
from .data.tables import (
    GANA_BY_NAK,
    NADI_CYCLE,
    NAKSHATRAS,
    NAME_SYLLABLES,
    PAYA_BY_HOUSE,
    SIGN_LORDS,
    SIGNS,
    TATVA_BY_SIGN,
    VARNA_BY_SIGN,
    YONI_BY_NAK,
)
from .nakshatra import nakshatra_index, pada


def vashya(sign: int, deg: float) -> str:
    """Chatushpad (quadruped), Manav, Jalchar, Vanchar, Keet. Sagittarius and Capricorn split at 15 degrees."""
    if sign in (0, 1):
        return "Chatushpad"
    if sign in (2, 5, 6, 10):
        return "Manav"
    if sign in (3, 11):
        return "Jalchar"
    if sign == 4:
        return "Vanchar"
    if sign == 7:
        return "Keet"
    if sign == 8:
        return "Manav" if deg < 15 else "Chatushpad"
    return "Chatushpad" if deg < 15 else "Jalchar"  # Capricorn


def avakahada(moon_lon: float, moon_house: int | None) -> dict[str, str | int | None]:
    """`moon_house` is the Moon's whole-sign house from the lagna (None when the birth time is unknown)."""
    sign, deg = int(moon_lon // 30), moon_lon % 30
    nak, pd = nakshatra_index(moon_lon), pada(moon_lon)
    syl = NAME_SYLLABLES[nak].split()[pd - 1]
    return {
        "sign": SIGNS[sign], "sign_lord": SIGN_LORDS[sign], "nakshatra": NAKSHATRAS[nak], "charan": pd,
        "varna": VARNA_BY_SIGN[sign], "vashya": vashya(sign, deg), "yoni": YONI_BY_NAK[nak],
        "gana": GANA_BY_NAK[nak], "nadi": NADI_CYCLE[nak % 6], "tatva": TATVA_BY_SIGN[sign % 4],
        "paya": PAYA_BY_HOUSE[moon_house] if moon_house else None,
        "name_syllable": syl, "name_alphabet": syl[0].upper(),
    }
