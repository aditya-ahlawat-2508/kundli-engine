"""Divisional charts. Each varga is a pure function (sidereal_longitude) -> (sign_index, degree_in_varga).

Variants chosen are documented in docs/conventions.md. Modality: sign%3 (0 movable,1 fixed,2 dual);
element: sign%4 (0 fire,1 earth,2 air,3 water); odd sign = even index (Aries is odd).
"""
from collections.abc import Callable


def _split(lon: float) -> tuple[int, float]:
    lon %= 360.0
    s = min(int(lon // 30), 11)
    return s, lon - s * 30


def _part(deg: float, n: int) -> tuple[int, float]:
    """Part index (0..n-1) of `deg` within a sign split into n equal parts, and degree within that part
    scaled to 0..30."""
    size = 30.0 / n
    k = min(int(deg // size), n - 1)
    return k, (deg - k * size) / size * 30.0


def _odd(s: int) -> bool:
    return s % 2 == 0


def d1(lon: float) -> tuple[int, float]:
    s, d = _split(lon)
    return s, d


def d2(lon: float) -> tuple[int, float]:
    """Parashari hora: odd signs 0-15 Sun(Leo) 15-30 Moon(Cancer); even signs reversed."""
    s, d = _split(lon)
    k, dv = _part(d, 2)
    first_sun = _odd(s)
    return (4 if (k == 0) == first_sun else 3), dv


def d3(lon: float) -> tuple[int, float]:
    """Drekkana (Parashara): same sign, 5th, 9th."""
    s, d = _split(lon)
    k, dv = _part(d, 3)
    return (s + 4 * k) % 12, dv


def d4(lon: float) -> tuple[int, float]:
    s, d = _split(lon)
    k, dv = _part(d, 4)
    return (s + 3 * k) % 12, dv


_D5_ODD = [0, 10, 8, 2, 6]   # Mars, Saturn, Jupiter, Mercury, Venus lords' signs  VERIFY
_D5_EVEN = [1, 5, 11, 9, 7]  # Venus, Mercury, Jupiter, Saturn, Mars


def d5(lon: float) -> tuple[int, float]:
    s, d = _split(lon)
    k, dv = _part(d, 5)
    return (_D5_ODD if _odd(s) else _D5_EVEN)[k], dv


def d6(lon: float) -> tuple[int, float]:
    s, d = _split(lon)
    k, dv = _part(d, 6)
    return ((0 if _odd(s) else 6) + k) % 12, dv


def d7(lon: float) -> tuple[int, float]:
    s, d = _split(lon)
    k, dv = _part(d, 7)
    return ((s if _odd(s) else s + 6) + k) % 12, dv


def d8(lon: float) -> tuple[int, float]:
    """Ashtamsa: movable from Aries, fixed from Sagittarius, dual from Leo.  VERIFY"""
    s, d = _split(lon)
    k, dv = _part(d, 8)
    return ([0, 8, 4][s % 3] + k) % 12, dv


def d9(lon: float) -> tuple[int, float]:
    """Navamsa: movable from the sign, fixed from the 9th, dual from the 5th."""
    s, d = _split(lon)
    k, dv = _part(d, 9)
    return (s + [0, 8, 4][s % 3] + k) % 12, dv


def d10(lon: float) -> tuple[int, float]:
    s, d = _split(lon)
    k, dv = _part(d, 10)
    return ((s if _odd(s) else s + 8) + k) % 12, dv


def d11(lon: float) -> tuple[int, float]:
    """Rudramsa: counted from Aries.  VERIFY (schools differ)"""
    s, d = _split(lon)
    k, dv = _part(d, 11)
    return k % 12, dv


def d12(lon: float) -> tuple[int, float]:
    s, d = _split(lon)
    k, dv = _part(d, 12)
    return (s + k) % 12, dv


def d16(lon: float) -> tuple[int, float]:
    """Shodasamsa: movable from Aries, fixed from Leo, dual from Sagittarius."""
    s, d = _split(lon)
    k, dv = _part(d, 16)
    return ([0, 4, 8][s % 3] + k) % 12, dv


def d20(lon: float) -> tuple[int, float]:
    """Vimsamsa: movable from Aries, fixed from Sagittarius, dual from Leo."""
    s, d = _split(lon)
    k, dv = _part(d, 20)
    return ([0, 8, 4][s % 3] + k) % 12, dv


def d24(lon: float) -> tuple[int, float]:
    """Siddhamsa: odd signs from Leo, even from Cancer."""
    s, d = _split(lon)
    k, dv = _part(d, 24)
    return ((4 if _odd(s) else 3) + k) % 12, dv


def d27(lon: float) -> tuple[int, float]:
    """Bhamsa: fire from Aries, earth from Cancer, air from Libra, water from Capricorn."""
    s, d = _split(lon)
    k, dv = _part(d, 27)
    return ([0, 3, 6, 9][s % 4] + k) % 12, dv


_D30_ODD = [(5, 0), (10, 10), (18, 8), (25, 2), (30, 6)]  # (upper bound deg, sign): Mars Sat Jup Mer Ven
_D30_EVEN = [(5, 1), (12, 5), (20, 11), (25, 9), (30, 7)]  # Ven Mer Jup Sat Mars


def d30(lon: float) -> tuple[int, float]:
    """Trimsamsa (unequal parts, BPHS)."""
    s, d = _split(lon)
    lo = 0.0
    for hi, sign in (_D30_ODD if _odd(s) else _D30_EVEN):
        if d < hi:
            return sign, (d - lo) / (hi - lo) * 30.0
        lo = hi
    return (_D30_ODD if _odd(s) else _D30_EVEN)[-1][1], 30.0


def d40(lon: float) -> tuple[int, float]:
    s, d = _split(lon)
    k, dv = _part(d, 40)
    return ((0 if _odd(s) else 6) + k) % 12, dv


def d45(lon: float) -> tuple[int, float]:
    s, d = _split(lon)
    k, dv = _part(d, 45)
    return ([0, 4, 8][s % 3] + k) % 12, dv


def d60(lon: float) -> tuple[int, float]:
    """Shashtiamsa: counted from the sign itself.  VERIFY"""
    s, d = _split(lon)
    k, dv = _part(d, 60)
    return (s + k) % 12, dv


VARGAS: dict[str, Callable[[float], tuple[int, float]]] = {
    "D1": d1, "D2": d2, "D3": d3, "D4": d4, "D5": d5, "D6": d6, "D7": d7, "D8": d8, "D9": d9,
    "D10": d10, "D11": d11, "D12": d12, "D16": d16, "D20": d20, "D24": d24, "D27": d27,
    "D30": d30, "D40": d40, "D45": d45, "D60": d60,
}
VARGA_NAMES = {"D1": "Rashi", "D2": "Hora", "D3": "Drekkana", "D4": "Chaturthamsa", "D5": "Panchamsa",
               "D6": "Shashthamsa", "D7": "Saptamsa", "D8": "Ashtamsa", "D9": "Navamsa", "D10": "Dashamsa",
               "D11": "Rudramsa", "D12": "Dwadasamsa", "D16": "Shodasamsa", "D20": "Vimsamsa",
               "D24": "Siddhamsa", "D27": "Bhamsa", "D30": "Trimsamsa", "D40": "Khavedamsa",
               "D45": "Akshavedamsa", "D60": "Shashtiamsa"}


def varga_sign(varga: str, lon: float) -> int:
    return VARGAS[varga](lon)[0]


def is_vargottama(lon: float) -> bool:
    return d1(lon)[0] == d9(lon)[0]
