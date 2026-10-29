"""Daily numerology number. CONVENTION (the provider's definition is unknown): the personal day number of a calendar date is
reduce(birth radical number + digital root of the date's day, month and year digits). Its relation to the birth number is
the natural-friendship relation of the two ruling grahas (`lookups.relation`)."""
from datetime import date
from typing import Any

from .lookups import relation
from .table import RULERS, reduce_digit


def daily_number(radical: int, on: date) -> dict[str, Any]:
    date_root = reduce_digit(sum(int(c) for c in f"{on.day}{on.month}{on.year}"))
    n = reduce_digit(radical + date_root)
    return {"date": on.isoformat(), "birth_number": radical, "date_root": date_root, "daily_number": n, "daily_ruler": RULERS[n],
            "relation_to_birth_number": relation(radical, n),
            "convention": "reduce(radical + digital root of the date digits)"}


__all__ = ["daily_number"]
