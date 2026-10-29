"""Tajika tables. Every table is entered from the standard Tajika scheme from memory and is `# VERIFY` until checked
against a cited source and a second reviewer (docs/open_questions.md). Structural invariants are asserted in tests."""

# Hadda (Egyptian terms): per sign, five (upper bound in degrees, lord) pairs covering 0-30. VERIFY
HADDA: list[list[tuple[float, str]]] = [
    [(6, "Jupiter"), (12, "Venus"), (20, "Mercury"), (25, "Mars"), (30, "Saturn")],      # Aries
    [(8, "Venus"), (14, "Mercury"), (22, "Jupiter"), (27, "Saturn"), (30, "Mars")],      # Taurus
    [(6, "Mercury"), (12, "Jupiter"), (17, "Venus"), (24, "Mars"), (30, "Saturn")],      # Gemini
    [(7, "Mars"), (13, "Venus"), (19, "Mercury"), (26, "Jupiter"), (30, "Saturn")],      # Cancer
    [(6, "Jupiter"), (11, "Venus"), (18, "Saturn"), (24, "Mercury"), (30, "Mars")],      # Leo
    [(7, "Mercury"), (17, "Venus"), (21, "Jupiter"), (28, "Mars"), (30, "Saturn")],      # Virgo
    [(6, "Saturn"), (14, "Mercury"), (21, "Jupiter"), (28, "Venus"), (30, "Mars")],      # Libra
    [(7, "Mars"), (11, "Venus"), (19, "Mercury"), (24, "Jupiter"), (30, "Saturn")],      # Scorpio
    [(12, "Jupiter"), (17, "Venus"), (21, "Mercury"), (26, "Saturn"), (30, "Mars")],     # Sagittarius
    [(7, "Mercury"), (14, "Jupiter"), (22, "Venus"), (26, "Saturn"), (30, "Mars")],      # Capricorn
    [(7, "Mercury"), (13, "Venus"), (20, "Jupiter"), (25, "Mars"), (30, "Saturn")],      # Aquarius
    [(12, "Venus"), (16, "Jupiter"), (19, "Mercury"), (28, "Mars"), (30, "Saturn")],     # Pisces
]

# Orb (deeptamsa) in degrees per graha; the mutual orb of two grahas is half the sum of their orbs. VERIFY
DEEPTAMSA = {"Sun": 15.0, "Moon": 12.0, "Mars": 8.0, "Mercury": 7.0, "Jupiter": 9.0, "Venus": 7.0, "Saturn": 9.0}
# Speed order, fastest first (used to decide which planet applies to which). VERIFY
SPEED_ORDER = ["Moon", "Mercury", "Venus", "Sun", "Mars", "Jupiter", "Saturn"]

# Harsha sthana: the house in which each graha is "glad" (5 virupas). VERIFY
HARSHA_HOUSE = {"Sun": 9, "Moon": 3, "Mars": 6, "Mercury": 1, "Jupiter": 11, "Venus": 5, "Saturn": 12}

# Panchavargeeya: fraction of the maximum by relation to the lord of the division. Max = 30 (kshetra), 20 (uccha),
# 15 (hadda), 10 (drekkana), 5 (navamsa). VERIFY
RELATION_FRACTION = {"own": 1.0, "great_friend": 0.75, "friend": 0.5, "neutral": 0.25, "enemy": 0.125,
                     "great_enemy": 0.0625}
PANCHAVARGEEYA_MAX = {"kshetra": 30.0, "hadda": 15.0, "drekkana": 10.0, "navamsa": 5.0}

# Triplicity lords (tri-rashi), kept for the year-lord work that is not implemented yet. VERIFY
TRIRASHI = {"fire": ("Sun", "Jupiter"), "earth": ("Venus", "Moon"), "air": ("Saturn", "Mercury"),
            "water": ("Venus", "Mars")}


def hadda_lord(sign: int, deg: float) -> str:
    for upper, lord in HADDA[sign]:
        if deg < upper:
            return lord
    return HADDA[sign][-1][1]


__all__ = ["DEEPTAMSA", "HADDA", "HARSHA_HOUSE", "PANCHAVARGEEYA_MAX", "RELATION_FRACTION", "SPEED_ORDER", "TRIRASHI",
           "hadda_lord"]
