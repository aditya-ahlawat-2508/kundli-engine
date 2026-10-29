"""Numerology: radical (birth day), destiny (full date) and name numbers. Pure arithmetic. The letter table is a
convention (`EngineConfig.numerology_system`): Chaldean (1-8, default) or Pythagorean (A=1 ... I=9 repeating)."""
import re
from datetime import date

RULERS = {1: "Sun", 2: "Moon", 3: "Jupiter", 4: "Rahu", 5: "Mercury", 6: "Venus", 7: "Ketu", 8: "Saturn", 9: "Mars"}
CHALDEAN = {c: v for v, letters in {1: "AIJQY", 2: "BKR", 3: "CGLS", 4: "DMT", 5: "EHNX", 6: "UVW", 7: "OZ", 8: "FP"}.items()
            for c in letters}
PYTHAGOREAN = {c: v for v, letters in {1: "AJS", 2: "BKT", 3: "CLU", 4: "DMV", 5: "ENW", 6: "FOX", 7: "GPY", 8: "HQZ",
                                       9: "IR"}.items() for c in letters}
SYSTEMS = {"chaldean": CHALDEAN, "pythagorean": PYTHAGOREAN}


def reduce_digit(n: int) -> int:
    """Digital root 1..9 (0 stays 0)."""
    while n > 9:
        n = sum(int(c) for c in str(n))
    return n


def name_number(name: str, system: str = "chaldean") -> int:
    """Value of the letters of `name` in the chosen letter table, reduced to 1..9."""
    table = SYSTEMS[system]
    return reduce_digit(sum(table.get(c, 0) for c in re.sub(r"[^A-Za-z]", "", name).upper()))


def numerology(name: str, dob: date, system: str = "chaldean") -> dict[str, int | str]:
    radical = reduce_digit(dob.day)
    destiny = reduce_digit(sum(int(c) for c in f"{dob.day}{dob.month}{dob.year}"))
    nn = name_number(name, system)
    return {"radical": radical, "radical_ruler": RULERS[radical], "destiny": destiny,
            "destiny_ruler": RULERS[destiny], "name": nn, "name_ruler": RULERS[nn] if nn else "", "system": system}
