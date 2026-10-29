"""Lal Kitab tables. The source books are inconsistent between editions; every table here is entered from memory and is
`# VERIFY` until one edition is chosen and cited (docs/conventions.md, docs/open_questions.md). Exalted/debilitated houses
are DERIVED from the sign exaltation table (house number = sign number counted from Aries), not typed."""
from ..data.tables import EXALTATION

# Pakka ghar ("permanent house") of each graha: primary first, then secondary houses. VERIFY (low confidence).
PAKKA_GHAR: dict[str, tuple[int, ...]] = {
    "Sun": (1,), "Moon": (4,), "Mars": (3, 8), "Mercury": (7,), "Jupiter": (2, 5, 9, 12), "Venus": (7,),
    "Saturn": (8, 10), "Rahu": (12,), "Ketu": (6,),
}

EXALTED_HOUSE = {p: s + 1 for p, (s, _) in EXALTATION.items()}
DEBILITATED_HOUSE = {p: (s + 6) % 12 + 1 for p, (s, _) in EXALTATION.items()}

PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")


def karakas(house: int) -> list[str]:
    """Grahas whose pakka ghar includes `house` (reverse lookup of the table above)."""
    return [p for p, hs in PAKKA_GHAR.items() if house in hs]


__all__ = ["DEBILITATED_HOUSE", "EXALTED_HOUSE", "PAKKA_GHAR", "PLANETS", "karakas"]
