"""Varshaphal (Tajika annual chart): solar return and month charts, Muntha, Panchavargeeya and Harsha bala, sahams,
Tajika yogas and Mudda dasha. Year lord (Varshesha), Patyayani dasha and tithi pravesha are not implemented."""
from datetime import datetime
from typing import Any

from ..models import Kundli
from ..transits import _cfg
from .harsha import harsha_bala
from .mudda_dasha import mudda_dasha
from .muntha import muntha
from .panchavargeeya import panchavargeeya
from .saham import sahams
from .solar_return import annual_chart, kundli_at, return_jd, solar_return
from .tajika_yogas import tajika_yogas


def varshaphal(natal: Kundli, year: int, month: int = 1) -> dict[str, Any]:
    """Everything for the year chart (month=1) or month chart `month`: the chart, Muntha and all strength tables."""
    annual, jd = annual_chart(natal, year, month)
    age = year - datetime.fromisoformat(natal.birth["utc"]).year
    return {"year": year, "month": month, "age": age, "jd_ut": jd, "chart": annual,
            "muntha": muntha(natal, annual, age), "panchavargeeya": panchavargeeya(annual),
            "harsha": harsha_bala(annual), "sahams": sahams(annual), "tajika_yogas": tajika_yogas(annual),
            "mudda_dasha": mudda_dasha(natal, annual, jd, _cfg(natal).mudda_dasha_basis)}


__all__ = ["annual_chart", "harsha_bala", "kundli_at", "mudda_dasha", "muntha", "panchavargeeya", "return_jd", "sahams",
           "solar_return", "tajika_yogas", "varshaphal"]
