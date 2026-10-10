"""Graha drishti (Parashari) and rashi drishti (Jaimini)."""
from .data.tables import ASPECT_HOUSES


def aspected_signs(planet: str, sign: int) -> list[int]:
    """Signs aspected by `planet` standing in `sign` (houses counted inclusively: 7th = +6)."""
    return sorted((sign + h - 1) % 12 for h in ASPECT_HOUSES[planet])


def aspects_sign(planet: str, planet_sign: int, target_sign: int) -> bool:
    return target_sign in aspected_signs(planet, planet_sign)


def rashi_drishti(sign: int) -> list[int]:
    """Jaimini: movable signs aspect fixed signs except the adjacent one; fixed aspect movable except
    adjacent; dual signs aspect the other dual signs. Modality = sign % 3 (0 movable, 1 fixed, 2 dual)."""
    mod = sign % 3
    if mod == 0:
        return sorted(s for s in range(12) if s % 3 == 1 and s != (sign + 1) % 12)
    if mod == 1:
        return sorted(s for s in range(12) if s % 3 == 0 and s != (sign - 1) % 12)
    return sorted(s for s in range(12) if s % 3 == 2 and s != sign)
