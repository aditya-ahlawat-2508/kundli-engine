"""Numerology (V2 phase 19): table numbers, lookups by ruling graha and the daily number. Text comes from the content store."""
from .daily import daily_number
from .lookups import fast_day, fav_lord, fav_place, fav_time, mantra, relation
from .table import CHALDEAN, PYTHAGOREAN, RULERS, SYSTEMS, name_number, numerology, reduce_digit

__all__ = ["CHALDEAN", "PYTHAGOREAN", "RULERS", "SYSTEMS", "daily_number", "fast_day", "fav_lord", "fav_place", "fav_time",
           "mantra", "name_number", "numerology", "reduce_digit", "relation"]
