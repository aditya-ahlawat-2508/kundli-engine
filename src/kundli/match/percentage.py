"""Compatibility percentage. CONVENTION (not a classical figure): Ashtakoota total / 36 x 100. The provider's own
formula is unknown and is meant to be discovered with the oracle (docs/conventions.md)."""


def percentage(total: float, maximum: float = 36.0) -> float:
    return round(100.0 * total / maximum, 2)


__all__ = ["percentage"]
