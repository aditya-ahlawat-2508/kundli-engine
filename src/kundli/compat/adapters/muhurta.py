"""Muhurta adapters (V2 phase 18): one endpoint per activity, all served by `muhurta.scan`. The request's `date` is the
first date, `end_date` the last (default 30 days), the place gives the location; an optional `natal` birth adds
Tarabala/Chandrabala; `direction` serves travel."""
from datetime import date, timedelta
from typing import Any

from ...chart import generate
from ...config import EngineConfig
from ...models import Kundli
from ...muhurta import activities, scan
from ..normalize import BirthRequest, to_inputs

Adapter = Any
DEFAULT_SPAN_DAYS = 30


def _run(activity: str) -> Adapter:
    def run(k: Kundli, r: BirthRequest, _a: dict[str, str]) -> Any:
        p = k.birth["place"]
        cfg = EngineConfig(**k.header["config"])
        start = date.fromisoformat(r.date)
        end = date.fromisoformat(r.end_date) if r.end_date else start + timedelta(days=DEFAULT_SPAN_DAYS - 1)
        natal = None
        if r.natal is not None:
            birth, _ = to_inputs(r.natal.model_copy(update={"config": r.config}))
            natal = generate(birth, cfg)
        return scan(activity, start, end, p["lat"], p["lon"], p["tz"], cfg, natal, r.direction)
    return run


MUHURTA_ADAPTERS: dict[str, Adapter] = {a: _run(a) for a in activities()}
