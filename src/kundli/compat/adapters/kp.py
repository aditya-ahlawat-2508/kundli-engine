"""KP-group adapters (V2 phase 15). `EngineConfig.kp_ayanamsa="kp"` regenerates the chart with Krishnamurti's
ayanamsa; "chart" (default) uses the chart's own ayanamsa, which is what the reference report used."""
from datetime import datetime
from typing import Any

from ...chart import generate
from ...config import EngineConfig
from ...kp import kp_chart
from ...models import BirthInput, Kundli
from ..normalize import BirthRequest

Adapter = Any


def _kp_chart(k: Kundli) -> dict[str, Any]:
    cfg = EngineConfig(**k.header["config"])
    if cfg.kp_ayanamsa == "kp" and cfg.ayanamsa != "kp":
        b = k.birth
        if b["time_unknown"]:
            raise ValueError("KP needs a known birth time")
        local = datetime.fromisoformat(b["local"])
        birth = BirthInput(name=b["name"], date=local.date(), time=local.time(), place=b["place"], fold=b.get("fold"))
        k = generate(birth, cfg.model_copy(update={"ayanamsa": "kp"}))
    return kp_chart(k)


def _planets(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    return _kp_chart(k)["planets"]


def _cusps(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    return _kp_chart(k)["cusps"]


def _chart(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    return _kp_chart(k)


def _house_sig(k: Kundli, _r: BirthRequest, a: dict[str, str]) -> Any:
    houses = _kp_chart(k)["significators"]["house"]
    return houses if "house" not in a else _pick(houses, a["house"], 1, 12, "house")


def _planet_sig(k: Kundli, _r: BirthRequest, a: dict[str, str]) -> Any:
    planets = _kp_chart(k)["significators"]["planet"]
    if "planet" not in a:
        return planets
    p = a["planet"].capitalize()
    if p not in planets:
        raise ValueError(f"unknown planet {a['planet']!r}; use one of {sorted(planets)}")
    return {p: planets[p]}


def _pick(table: dict, key: str, lo: int, hi: int, what: str) -> Any:
    try:
        n = int(key)
    except ValueError:
        raise ValueError(f"{what} must be a number {lo}..{hi}") from None
    if not lo <= n <= hi:
        raise ValueError(f"{what} must be a number {lo}..{hi}")
    return {n: table[n]}


KP_ADAPTERS: dict[str, Adapter] = {
    "kp_planets": _planets,
    "kp_house_cusps": _cusps,
    "kp_birth_chart": _chart,
    "kp_house_significator": _house_sig,
    "kp_planet_significator": _planet_sig,
}
