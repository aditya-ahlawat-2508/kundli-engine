"""Functional nature of the grahas for a given lagna (from the houses they rule)."""
from .data.tables import SEVEN, SIGN_LORDS

NATURAL_BENEFIC = {"Moon", "Mercury", "Jupiter", "Venus"}


def lordships(lagna_sign: int) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {p: [] for p in SEVEN}
    for h in range(1, 13):
        out[SIGN_LORDS[(lagna_sign + h - 1) % 12]].append(h)
    return out


def functional_nature(lagna_sign: int) -> dict[str, str]:
    """yogakaraka | benefic | malefic | neutral for each of the seven grahas (nodes have no house lordship).

    Precedence: lord of both a kendra (4/7/10) and a trikona (5/9) = yogakaraka; trikona lord (1/5/9) = benefic;
    lord of 3/6/11 = malefic; lord of 2/8/12 = neutral; sole kendra lord (4/7/10): a natural benefic becomes
    malefic (kendradhipati dosha) and a natural malefic neutral. (Rule set v1, see docs/open_questions.md.)"""
    out = {}
    for p, hs in lordships(lagna_sign).items():
        if any(h in (4, 7, 10) for h in hs) and any(h in (5, 9) for h in hs):
            out[p] = "yogakaraka"
        elif any(h in (1, 5, 9) for h in hs):
            out[p] = "benefic"
        elif any(h in (3, 6, 11) for h in hs):
            out[p] = "malefic"
        elif any(h in (2, 8, 12) for h in hs):
            out[p] = "neutral"
        else:
            out[p] = "malefic" if p in NATURAL_BENEFIC else "neutral"
    return out
