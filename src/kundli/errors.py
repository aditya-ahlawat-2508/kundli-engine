"""Domain errors."""


class KundliError(Exception):
    pass


class AmbiguousPlace(KundliError):
    """More than one plausible place matched; the caller must choose one of `candidates`."""

    def __init__(self, query: str, candidates: list):
        self.query = query
        self.candidates = candidates
        super().__init__(f"{len(candidates)} places match {query!r}; choose one")


class PlaceNotFound(KundliError):
    pass


class AmbiguousLocalTime(KundliError):
    """Local time occurs twice (DST overlap); pass fold=0 (first) or fold=1 (second)."""


class NonexistentLocalTime(KundliError):
    """Local time falls in a DST gap and never happened."""
