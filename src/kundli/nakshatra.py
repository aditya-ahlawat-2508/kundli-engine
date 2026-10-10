"""Nakshatra, pada, lords, KP sub-lord."""
from .data.tables import ABHIJIT, NAK_SPAN, NAKSHATRAS, VIM_ORDER, VIM_YEARS


def nakshatra_index(lon: float) -> int:
    """0..26 = floor(lon / 13deg20')."""
    return min(int((lon % 360.0) // NAK_SPAN), 26)


def nakshatra_lord(idx: int) -> str:
    """Vimshottari lord: cycles Ketu, Venus, Sun, ... every 9 nakshatras."""
    return VIM_ORDER[idx % 9]


def pada(lon: float) -> int:
    """1..4: quarter (3deg20') within nakshatra."""
    within = (lon % 360.0) - nakshatra_index(lon) * NAK_SPAN
    return min(int(within // (NAK_SPAN / 4)), 3) + 1


def fraction_elapsed(lon: float) -> float:
    """Fraction (0..1) of the nakshatra already traversed."""
    return ((lon % 360.0) - nakshatra_index(lon) * NAK_SPAN) / NAK_SPAN


def sub_lord(lon: float) -> str:
    """KP sub-lord: nakshatra split in 9 parts proportional to Vimshottari years, starting from its lord."""
    idx = nakshatra_index(lon)
    start = VIM_ORDER.index(nakshatra_lord(idx))
    frac = fraction_elapsed(lon) * 120.0  # in "years" of the 120-year cycle
    acc = 0.0
    for k in range(9):
        lord = VIM_ORDER[(start + k) % 9]
        acc += VIM_YEARS[lord]
        if frac < acc:
            return lord
    return VIM_ORDER[(start + 8) % 9]


def in_abhijit(lon: float) -> bool:
    """Optional 28th nakshatra span (not used by default 27-nakshatra logic)."""
    return ABHIJIT[0] <= (lon % 360.0) < ABHIJIT[1]


def nakshatra_name(idx: int) -> str:
    return NAKSHATRAS[idx]
