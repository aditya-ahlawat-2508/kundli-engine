"""Orchestrator: BirthInput + EngineConfig -> Kundli. Pure: no clock reads, no randomness."""
import hashlib
import json
from datetime import datetime
from typing import Any

import swisseph as swe

from . import __version__
from .aspects import aspected_signs
from .avakahada import avakahada
from .ayanamsa import ayanamsa_ut
from .config import EngineConfig
from .core import Core, build_core
from .dasha import chara, vimshottari, yogini
from .data.tables import NAKSHATRAS, PLANETS, SIGNS
from .doshas import kaal_sarpa, manglik, sadhesati_events
from .ephemeris import base_flags
from .friendship import friendship_tables
from .functional import functional_nature
from .houses import sripati_starts
from .jaimini import jaimini
from .kp import kp_chart, kp_row
from .lagnas import gulika_mandi, special_lagnas, sun_upagrahas
from .models import BirthInput, Kundli, PlanetData
from .nakshatra import nakshatra_index, nakshatra_lord, pada, sub_lord
from .numerology import numerology
from .panchang import hindu_month, panchang
from .panchang.sun_moon_times import rise_args
from .remedies import gemstone_picks
from .strength.ashtakavarga import ashtakavarga
from .strength.bhavabala import bhavabala
from .strength.shadbala import ishta_kashta, shadbala
from .strength.vimshopaka import vimshopaka
from .vargas import VARGA_NAMES, VARGAS, is_vargottama
from .yogas.engine import evaluate_yogas

STORED_DASHA_DEPTH = 3  # maha/antar/pratyantar stored; deeper levels computed on demand by current_dasha()


def m_jd(birth: BirthInput) -> float:
    from .timeutil import resolve_birth
    return resolve_birth(birth).jd_ut


def run_id(birth: BirthInput, cfg: EngineConfig) -> str:
    """SHA-256 of canonical JSON of (input, config, engine_version)."""
    payload = {"input": json.loads(birth.model_dump_json()), "config": json.loads(cfg.model_dump_json()),
               "engine_version": __version__}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _planet_data(core: Core) -> list[PlanetData]:
    out = []
    for n in PLANETS:
        p = core.pos[n]
        ni = nakshatra_index(p.sidereal_lon)
        out.append(PlanetData(
            name=n, tropical_lon=p.tropical_lon, sidereal_lon=p.sidereal_lon, lat=p.lat, speed=p.speed,
            retrograde=p.retrograde, sign=core.sign[n], sign_name=SIGNS[core.sign[n]],
            degree_in_sign=core.deg[n], nakshatra=ni, nakshatra_name=NAKSHATRAS[ni],
            pada=pada(p.sidereal_lon), nakshatra_lord=nakshatra_lord(ni), sub_lord=sub_lord(p.sidereal_lon),
            house=core.house[n], rashi_house=core.rashi_house[n], bhava_chalit_house=core.chalit_house[n],
            combust=core.combust[n], dignity=core.dignity[n], vargottama=is_vargottama(p.sidereal_lon),
            war=core.war[n], lord_of_houses=core.lords_of[n],
            varga_signs={v: core.varga[v][n] for v in VARGAS},
        ))
    return out


def _aspects(core: Core) -> dict[str, Any]:
    by_sign: dict[int, list[str]] = {}
    for p in PLANETS:
        by_sign.setdefault(core.sign[p], []).append(p)
    table: dict[str, Any] = {}
    aspected_by: dict[str, list[str]] = {p: [] for p in PLANETS}
    for p in PLANETS:
        signs = aspected_signs(p, core.sign[p])
        hit = [q for s in signs for q in by_sign.get(s, []) if q != p]
        for q in hit:
            aspected_by[q].append(p)
        table[p] = {"aspects_signs": [SIGNS[s] for s in signs], "aspects_planets": sorted(hit),
                    "aspects_houses": ([(s - core.lagna_sign) % 12 + 1 for s in signs]
                                       if core.lagna_sign is not None else None)}
    for p in PLANETS:
        table[p]["aspected_by"] = sorted(aspected_by[p])
    return table


def _vargas(core: Core) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for v, fn in VARGAS.items():
        d: dict[str, Any] = {"name": VARGA_NAMES[v], "planets": {}}
        for p in PLANETS:
            s, dv = fn(core.lon[p])
            d["planets"][p] = {"sign": s, "sign_name": SIGNS[s], "degree_in_varga": dv}
        if core.houses is not None:
            s, dv = fn(core.houses.asc)
            d["lagna"] = {"sign": s, "sign_name": SIGNS[s], "degree_in_varga": dv}
        out[v] = d
    return out


def _relative_chart(core: Core, ref: str) -> dict[str, Any]:
    """Chandra (ref=Moon) or Surya (ref=Sun) chart: whole-sign houses counted from that planet's sign."""
    rs = core.sign[ref]
    return {"lagna_sign": rs, "lagna_sign_name": SIGNS[rs],
            "planets": {p: {"house": (core.sign[p] - rs) % 12 + 1, "sign": core.sign[p]} for p in PLANETS}}


def _bhava_chalit(core: Core) -> dict[str, Any]:
    hs = core.houses
    assert hs is not None
    sandhis = sripati_starts(list(hs.madhyas))
    shift = {p: {"rashi_house": core.rashi_house[p], "chalit_house": core.chalit_house[p],
                 "shifted": core.rashi_house[p] != core.chalit_house[p]} for p in PLANETS}
    return {"method": "Sripati (Porphyry cusps = bhava madhya; boundaries at midpoints)",
            "madhyas": list(hs.madhyas), "sandhis": sandhis, "planets": shift,
            "shifted_planets": sorted(p for p, v in shift.items() if v["shifted"])}


def _dashas(core: Core) -> dict[str, Any]:
    cfg, m, tz = core.cfg, core.moment, core.birth.place.tz
    moon = core.lon["Moon"]
    depth = min(cfg.dasha_levels, STORED_DASHA_DEPTH)
    return {
        "params": {"moon_lon": moon, "birth_utc": m.utc.isoformat(), "year_days": cfg.dasha_year_days, "tz": tz,
                   "levels": cfg.dasha_levels, "stored_depth": depth},
        "vimshottari": {"balance_at_birth": vimshottari.balance_at_birth(moon, cfg.dasha_year_days),
                        "mahadashas": vimshottari.tree(moon, m.utc, cfg.dasha_year_days, depth, tz)},
        "yogini": {"mahadashas": yogini.tree(moon, m.utc, cfg.dasha_year_days, depth, tz)},
    }


def current_dasha(k: Kundli, as_of: datetime, system: str = "vimshottari", levels: int | None = None) -> list[dict]:
    """Running dasha stack at `as_of` (aware datetime; never read from the clock)."""
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    par = k.dashas["params"]
    birth_utc = datetime.fromisoformat(par["birth_utc"])
    if system == "chara":
        cp = k.dashas.get("chara", {}).get("params")
        if cp is None:
            raise ValueError("Chara dasha needs a known birth time")
        return chara.stack(cp["lagna_sign"], cp["signs"], cp["degs"], birth_utc, par["year_days"], as_of,
                           levels or par["levels"], par["tz"])
    mod = {"vimshottari": vimshottari, "yogini": yogini}[system]
    return mod.stack(par["moon_lon"], birth_utc, par["year_days"], as_of, levels or par["levels"], par["tz"])


def generate(birth: BirthInput, cfg: EngineConfig | None = None) -> Kundli:
    cfg = cfg or EngineConfig()
    core = build_core(birth, cfg)
    m, hs = core.moment, core.houses
    notes = list(core.notes)
    header = {"engine": "kundli-engine", "engine_version": __version__, "run_id": run_id(birth, cfg),
              "config": json.loads(cfg.model_dump_json()), "swisseph_version": swe.version,
              "ephemeris_mode": cfg.ephemeris, "ayanamsa_degrees": ayanamsa_ut(m_jd(birth), cfg.ayanamsa)}
    header["ayanamsa_degrees"] = (core.pos["Sun"].tropical_lon - core.pos["Sun"].sidereal_lon) % 360.0
    k = Kundli(
        header=header,
        birth={"name": birth.name, "place": birth.place.model_dump(), "fold": birth.fold,
               "local": m.local.isoformat(), "utc": m.utc.isoformat(), "utc_offset_seconds": m.utc_offset_seconds,
               "jd_ut": m.jd_ut, "jd_et": m.jd_et, "time_unknown": m.time_unknown},
        lagna=None if hs is None else {
            "longitude": hs.asc, "sign": core.lagna_sign, "sign_name": SIGNS[core.lagna_sign or 0],
            "degree_in_sign": hs.asc % 30.0, "nakshatra": NAKSHATRAS[nakshatra_index(hs.asc)],
            "pada": pada(hs.asc), "lord": core.lord_of_house(1), "mc": hs.mc},
        houses=None if hs is None else {"system_requested": cfg.house_system, "system_used": hs.system_used,
                                        "fallback": hs.fallback, "starts": list(hs.starts),
                                        "madhyas": list(hs.madhyas)},
        planets=_planet_data(core),
        aspects=_aspects(core),
        vargas=_vargas(core),
        chandra_chart=_relative_chart(core, "Moon"),
        surya_chart=_relative_chart(core, "Sun"),
        dashas=_dashas(core),
        notes=notes,
    )
    sun, moon = core.lon["Sun"], core.lon["Moon"]
    k.panchang = panchang(m.jd_ut, sun, moon, birth.place.lat, birth.place.lon, birth.place.tz, **rise_args(cfg))
    k.upagrahas = {"sun_based": sun_upagrahas(sun)}
    if hs is not None:
        k.bhava_chalit = _bhava_chalit(core)
        if core.sun_ev is not None:
            k.special_lagnas = special_lagnas(m.jd_ut, core.sun_ev["sunrise"], sun, moon, hs.asc, core.sign)
            assert core.day_idx is not None
            k.upagrahas["gulika_mandi"] = gulika_mandi(m.jd_ut, core.sun_ev, core.day_idx, birth.place.lat,
                                                       birth.place.lon, cfg)
            sb = shadbala(core)
            k.shadbala = sb
            k.ishta_kashta = ishta_kashta(core, sb)
            k.bhavabala = bhavabala(core, sb)
        else:
            notes.append("No sunrise/sunset at this latitude/date: special lagnas, Gulika/Mandi, Shadbala and "
                         "bhava bala were skipped.")
            sb = None
        k.ashtakavarga = ashtakavarga(core)
        k.jaimini = jaimini(core)
        k.yogas = evaluate_yogas(core, sb)
    else:
        k.yogas = [y for y in evaluate_yogas(core, None)]
    k.vimshopaka = vimshopaka(core)
    _report_sections(k, core)
    k.notes = notes
    if cfg.include_outer_planets:
        k.outer_planets = [p.model_dump() for p in _outer(core)]
    return k


def _report_sections(k: Kundli, core: Core) -> None:
    """Sections added for the full report: friendship, avakahada, KP, functional nature, gemstones, numerology,
    Chara dasha, Hindu month and the dosha analyses."""
    m, cfg = core.moment, core.cfg
    k.friendship = friendship_tables({p: core.sign[p] for p in PLANETS})
    k.avakahada = avakahada(core.lon["Moon"], core.rashi_house["Moon"])
    k.numerology = numerology(core.birth.name, core.birth.date, cfg.numerology_system)
    if k.panchang is not None:
        k.panchang["hindu_month"] = hindu_month(m.jd_ut, cfg.ayanamsa, base_flags(cfg))
    k.kp = {"planets": {p: kp_row(core.lon[p]) for p in PLANETS}}
    if core.lagna_sign is not None:
        k.kp = kp_chart(k)
        k.functional_nature = functional_nature(core.lagna_sign)
        k.gemstones = gemstone_picks(core.lagna_sign)
        k.dashas["chara"] = {"params": {"lagna_sign": core.lagna_sign, "signs": dict(core.sign), "degs": dict(core.deg)},
                             "mahadashas": chara.tree(core.lagna_sign, core.sign, core.deg, m.utc, cfg.dasha_year_days,
                                                      core.birth.place.tz)}
    k.doshas = {"kaal_sarpa": kaal_sarpa(k), "manglik": manglik(k), "sadhesati_events": sadhesati_events(k)}


def _outer(core: Core):
    from .ephemeris import planet_positions
    return [p for p in planet_positions(core.moment.jd_ut, core.cfg) if p.name in ("Uranus", "Neptune", "Pluto")]


# ---- serialisation boundary: the single rounding policy ---------------------------------------------
_ANGLE_HINTS = ("lon", "degree", "lat", "speed", "asc", "mc", "sandhi", "madhya", "starts", "longitude")


def _round(obj: Any, key: str, arcsec: int) -> Any:
    if isinstance(obj, float):
        k = key.lower()
        if "jd" in k:
            return round(obj, 8)
        if any(h in k for h in _ANGLE_HINTS):
            step = arcsec / 3600.0
            return round(round(obj / step) * step, 9) if step > 0 else obj
        return round(obj, 6)
    if isinstance(obj, dict):
        return {kk: _round(v, kk, arcsec) for kk, v in obj.items()}
    if isinstance(obj, list):
        return [_round(v, key, arcsec) for v in obj]
    return obj


def to_dict(k: Kundli) -> dict[str, Any]:
    """Plain dict with rounding applied (config.rounding_arcsec) - the only place values are rounded."""
    arcsec = int(k.header["config"]["rounding_arcsec"])
    return _round(json.loads(k.model_dump_json()), "", arcsec)


def to_json(k: Kundli) -> str:
    """Byte-stable JSON: sorted keys, fixed separators, ASCII-safe."""
    return json.dumps(to_dict(k), sort_keys=True, indent=1, ensure_ascii=False)
