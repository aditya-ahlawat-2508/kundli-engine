"""Match making: Ashtakoota (36), Dashakoota (9 of 10 poruthams), obstructions, percentage and a combined result."""
from typing import Any

from ..models import Kundli
from .ashtakoota import ashtakoota, verdict
from .dashakoota import dashakoota
from .obstructions import obstructions
from .percentage import percentage
from .person import Person, person_from


def match(boy: Kundli, girl: Kundli) -> dict[str, Any]:
    """Everything computable from two finished charts. Manglik needs a birth time for both."""
    pb, pg = person_from(boy), person_from(girl)
    ak = ashtakoota(pb, pg)
    return {"ashtakoota": ak, "dashakoota": dashakoota(pb, pg), "obstructions": obstructions(boy, girl, pb, pg),
            "percentage": percentage(ak["total"]), "verdict": verdict(ak["total"]),
            "convention": "percentage = total/36*100; verdict bands in match/tables.yaml"}


__all__ = ["Person", "ashtakoota", "dashakoota", "match", "obstructions", "percentage", "person_from", "verdict"]
