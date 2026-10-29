"""Panchang-group adapters (V2 phase 12). Engine-neutral bodies; provider field names are mapped once the
provider's schemas arrive. Each function takes the finished Kundli (used for place, moment and config) plus the
request."""
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from ...chart import generate
from ...config import EngineConfig
from ...models import BirthInput, Kundli
from ...panchang.day import day_panchang, sunrise_jd
from ...panchang.festivals import festivals_on
from ...panchang.sun_moon_times import day_times
from ...panchang.tamil import tamil_calendar
from ...panchang.yogas_monthly import monthly_yogas
from ...timeutil import jd_to_utc
from ..normalize import BirthRequest

Adapter = Any


def _ctx(k: Kundli) -> tuple[float, float, float, str, EngineConfig, date]:
    b = k.birth
    p = b["place"]
    return (b["jd_ut"], p["lat"], p["lon"], p["tz"], EngineConfig(**k.header["config"]),
            datetime.fromisoformat(b["local"]).date())


def _moment(k: Kundli, at_sunrise: bool) -> tuple[float, float, float, str, EngineConfig, date]:
    jd, lat, lon, tz, cfg, d = _ctx(k)
    return (sunrise_jd(d, lat, lon, tz, cfg) + 1e-6 if at_sunrise else jd), lat, lon, tz, cfg, d


def _panchang(at_sunrise: bool, keys: tuple[str, ...] | None = None) -> Adapter:
    def run(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
        jd, lat, lon, tz, cfg, _d = _moment(k, at_sunrise)
        full = day_panchang(jd, lat, lon, tz, cfg)
        return full if keys is None else {x: full[x] for x in keys if x in full}
    return run


def _basic(at_sunrise: bool) -> Adapter:
    def run(k: Kundli, r: BirthRequest, a: dict[str, str]) -> Any:
        full = _panchang(at_sunrise)(k, r, a)
        el = full["elements"]
        return {"moment_local": full["moment_local"], "vara": full["vara"], "tithi": el["tithi"],
                "nakshatra": el["nakshatra"], "yoga": el["yoga"], "karana": el["karana"],
                "rise_set": full["rise_set"], "hindu_month": full.get("hindu_month"),
                "conventions": full["conventions"]}
    return run


def _planet_panchang(at_sunrise: bool) -> Adapter:
    def run(k: Kundli, r: BirthRequest, a: dict[str, str]) -> Any:
        base = _basic(at_sunrise)(k, r, a)
        k2 = generate(_birth_at(k, _moment(k, True)[0]), _ctx(k)[4]) if at_sunrise else k
        return {**base, "planets": [p.model_dump() for p in k2.planets]}
    return run


def _birth_at(k: Kundli, jd: float) -> BirthInput:
    """A BirthInput for the same place at the local time of `jd`."""
    p = k.birth["place"]
    local = jd_to_utc(jd).astimezone(ZoneInfo(p["tz"]))
    return BirthInput(name=k.birth["name"], date=local.date(), time=local.time().replace(microsecond=0), place=p)


def _chart(at_sunrise: bool) -> Adapter:
    def run(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
        if not at_sunrise:
            return {"moment_local": k.birth["local"], "lagna": k.lagna, "d1": k.vargas.get("D1"), "planets": k.planets}
        jd, *_rest = _moment(k, True)
        k2 = generate(_birth_at(k, jd), _ctx(k)[4])
        return {"moment_local": k2.birth["local"], "lagna": k2.lagna, "d1": k2.vargas.get("D1"), "planets": k2.planets}
    return run


def _hora_now(k: Kundli, r: BirthRequest, a: dict[str, str]) -> Any:
    full = _panchang(False, ("moment_local", "hora"))(k, r, a)
    jd = k.birth["jd_ut"]
    current = next((h for h in full.get("hora", []) if h["start_jd"] <= jd < h["end_jd"]), None)
    return {"moment_local": full["moment_local"], "current": current}


def _tamil(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    jd, lat, lon, tz, cfg, d = _ctx(k)
    return {**tamil_calendar(d, lat, lon, tz, cfg), "date": d.isoformat()}


def _tamil_month(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    jd, lat, lon, tz, cfg, d = _ctx(k)
    cur = tamil_calendar(d, lat, lon, tz, cfg)
    first = date.fromisoformat(cur["month_start_date"])
    days = []
    day = first
    while True:
        t = tamil_calendar(day, lat, lon, tz, cfg)
        if t["month"] != cur["month"]:
            break
        times = day_times(day, lat, lon, tz, cfg)
        full = day_panchang(times["sunrise_jd"] + 1e-6, lat, lon, tz, cfg)
        days.append({"date": day.isoformat(), "tamil_day": t["day"], "vara": full["vara"],
                     "tithi": full["elements"]["tithi"], "nakshatra": full["elements"]["nakshatra"]})
        day += timedelta(days=1)
    return {"month": cur["month"], "days": days, "rule": cur["rule"]}


def _festivals(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    _jd, lat, lon, tz, cfg, d = _ctx(k)
    return {"date": d.isoformat(), "festivals": festivals_on(d, lat, lon, tz, cfg)}


def _festivals_month(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
    _jd, lat, lon, tz, cfg, d = _ctx(k)
    out, day = [], d.replace(day=1)
    while day.month == d.month:
        out += festivals_on(day, lat, lon, tz, cfg)
        day += timedelta(days=1)
    return {"month": f"{d.year}-{d.month:02d}", "festivals": out}


def _yoga(key: str) -> Adapter:
    def run(k: Kundli, _r: BirthRequest, _a: dict[str, str]) -> Any:
        _jd, lat, lon, tz, cfg, d = _ctx(k)
        return {"month": f"{d.year}-{d.month:02d}", "yoga": key,
                "windows": monthly_yogas(d.year, d.month, lat, lon, tz, cfg, {key})[key]}
    return run


PANCHANG_ADAPTERS: dict[str, Adapter] = {
    "basic_panchang": _basic(False),
    "basic_panchang/sunrise": _basic(True),
    "advanced_panchang": _panchang(False),
    "advanced_panchang/sunrise": _panchang(True),
    "planet_panchang": _planet_panchang(False),
    "planet_panchang/sunrise": _planet_panchang(True),
    "chaughadiya_muhurta": _panchang(False, ("moment_local", "vara", "choghadiya")),
    "hora_muhurta": _hora_now,
    "hora_muhurta_dinman": _panchang(False, ("moment_local", "vara", "hora")),
    "panchang_chart": _chart(False),
    "panchang_chart/sunrise": _chart(True),
    "tamil_panchang": _tamil,
    "tamil_month_panchang": _tamil_month,
    "panchang_festival": _festivals,
    "festival-by-date": _festivals_month,
    **{k: _yoga(k) for k in ("sarvartha_siddhi", "amrit_siddhi", "ravi_yoga", "ravi_pushya", "guru_pushya",
                             "dwipushkar", "tripushkar")},
}
