"""The Moon-based facts of one partner that every koota needs, read from a finished Kundli."""
from dataclasses import dataclass

from ..avakahada import vashya
from ..data.tables import GANA_BY_NAK, NADI_CYCLE, NAKSHATRAS, SIGN_LORDS, SIGNS, VARNA_BY_SIGN, YONI_BY_NAK
from ..models import Kundli
from ..nakshatra import pada


@dataclass(frozen=True)
class Person:
    name: str
    sign: int
    nakshatra: int
    pada: int
    sign_lord: str
    varna: str
    vashya: str
    yoni: str
    gana: str
    nadi: str

    @property
    def sign_name(self) -> str:
        return SIGNS[self.sign]

    @property
    def nakshatra_name(self) -> str:
        return NAKSHATRAS[self.nakshatra]


def person_from(k: Kundli) -> Person:
    moon = next(p for p in k.planets if p.name == "Moon")
    sign, nak = moon.sign, moon.nakshatra
    return Person(name=k.birth["name"], sign=sign, nakshatra=nak, pada=pada(moon.sidereal_lon),
                  sign_lord=SIGN_LORDS[sign], varna=VARNA_BY_SIGN[sign], vashya=vashya(sign, moon.degree_in_sign),
                  yoni=YONI_BY_NAK[nak], gana=GANA_BY_NAK[nak], nadi=NADI_CYCLE[nak % 6])


__all__ = ["Person", "person_from"]
